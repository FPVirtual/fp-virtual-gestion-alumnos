<?php
// This file is part of Moodle - http://moodle.org/
//
// Moodle is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// Moodle is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with Moodle.  If not, see <http://www.gnu.org/licenses/>.

namespace local_fpvirtual_gestion_alumnado\sync;

use local_fpvirtual_gestion_alumnado\config;

/**
 * Envía los correos al alumnado y a los responsables (R18, R19).
 *
 * El envío es síncrono, a través de la configuración de correo de Moodle
 * (email_to_user), con pausa entre mensajes y límite diario. No se usa la
 * cola de tareas adhoc para que la contraseña inicial no quede guardada en
 * la base de datos. Los fallos se cuentan y aparecen en el informe.
 *
 * @package    local_fpvirtual_gestion_alumnado
 * @copyright  2026 FP virtual Aragón
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class notifier implements notifier_interface {

    /** @var string Ajuste interno con el contador diario: "AAAAMMDD:N". */
    public const DAILY_COUNTER = 'emailcounter';

    /** @var config */
    protected config $config;

    /** @var callable(string): void */
    protected $log;

    /** @var callable(int): void */
    protected $sleep;

    /** @var int[] Contadores: sent, failed, skipped. */
    public array $stats = ['sent' => 0, 'failed' => 0, 'skipped' => 0];

    /** @var string[] Errores de envío. */
    public array $errors = [];

    /**
     * Constructor.
     *
     * @param config $config
     * @param callable|null $log
     * @param callable|null $sleep
     */
    public function __construct(config $config, ?callable $log = null, ?callable $sleep = null) {
        $this->config = $config;
        $this->log = $log ?? fn(string $m) => null;
        $this->sleep = $sleep ?? fn(int $s) => $s > 0 ? sleep($s) : null;
    }

    /**
     * {@inheritdoc}
     *
     * @param array $user
     * @param string $password
     * @param string[] $modules
     */
    public function welcome(array $user, string $password, array $modules): void {
        $this->send_to_student($user['email'], 'FP virtual Aragón - Datos de acceso', 'email_welcome', [
            'nombre' => $user['firstname'],
            'apellidos' => $user['lastname'],
            'username' => $user['username'],
            'password' => $password,
            'institutionalemail' => $user['institutionalemail'],
            'modules' => $modules,
            'hasmodules' => !empty($modules),
        ]);
    }

    /**
     * {@inheritdoc}
     *
     * @param array $op
     */
    public function username_changed(array $op): void {
        global $DB;
        // El email institucional de Moodle no cambia con el renombrado.
        $institutional = $op['userid'] ? (string)$DB->get_field('user', 'email', ['id' => $op['userid']]) : '';
        $this->send_to_student($op['email'] ?? null, 'FP virtual Aragón - Usuario actualizado', 'email_username_changed', [
            'nombre' => $op['nombre'] ?? '',
            'apellidos' => $op['apellidos'] ?? '',
            'username' => $op['username'],
            'oldusername' => $op['oldusername'],
            'institutionalemail' => $institutional,
        ]);
    }

    /**
     * {@inheritdoc}
     *
     * @param array $student
     * @param string[] $modules
     */
    public function new_enrolments(array $student, array $modules): void {
        $this->send_to_student($student['email'], 'FP virtual Aragón - Nuevas matrículas', 'email_new_enrolments', [
            'nombre' => $student['nombre'] ?? '',
            'apellidos' => $student['apellidos'],
            'modules' => $modules,
        ]);
    }

    /**
     * Envía el informe de una ejecución a los responsables (sin límite diario).
     *
     * @param array $context contexto de email_report
     * @param string|null $attachment ruta absoluta dentro de dataroot
     * @param string $attachname
     * @return int correos enviados
     */
    public function send_report(array $context, ?string $attachment = null, string $attachname = ''): int {
        $sent = 0;
        $subject = 'Informe de gestión de alumnado: ' . ($context['estado'] ?? '');
        foreach ($this->config->list('reportto') as $to) {
            if ($this->deliver($to, $subject, 'email_report', $context, $attachment, $attachname)) {
                $sent++;
            }
        }
        return $sent;
    }

    /**
     * Envío a un alumno: respeta activación, redirección y límite diario.
     *
     * @param string|null $to
     * @param string $subject
     * @param string $template
     * @param array $context
     */
    protected function send_to_student(?string $to, string $subject, string $template, array $context): void {
        if (!$this->config->bool('notifyenabled')) {
            return;
        }
        if ($to === null || !validate_email($to)) {
            $this->stats['failed']++;
            $this->errors[] = "Email no válido para {$template}: " . ($context['username'] ?? $context['nombre'] ?? '');
            return;
        }
        if (!$this->reserve_daily_slot()) {
            $this->stats['skipped']++;
            return;
        }
        $redirect = $this->config->str('notifyredirect');
        if ($redirect !== '') {
            $subject = "[{$to}] {$subject}";
            $to = $redirect;
        }
        if ($this->deliver($to, $subject, $template, $context)) {
            $this->stats['sent']++;
        } else {
            $this->stats['failed']++;
            $this->errors[] = "Fallo al enviar {$template} a {$to}";
        }
        ($this->sleep)($this->config->int('emailpause'));
    }

    /**
     * Renderiza y envía un correo.
     *
     * @param string $to
     * @param string $subject
     * @param string $template
     * @param array $context
     * @param string|null $attachment
     * @param string $attachname
     * @return bool
     */
    protected function deliver(string $to, string $subject, string $template, array $context,
            ?string $attachment = null, string $attachname = ''): bool {
        global $OUTPUT;

        $html = $OUTPUT->render_from_template(config::COMPONENT . '/' . $template, $context + $this->common_context());
        $text = html_to_text($html);

        $recipient = \core_user::get_noreply_user();
        $recipient->id = -99;
        $recipient->email = $to;
        $recipient->mailformat = FORMAT_HTML;
        $recipient->firstname = $context['nombre'] ?? '';
        $recipient->lastname = $context['apellidos'] ?? '';

        try {
            $ok = email_to_user($recipient, \core_user::get_noreply_user(), $subject, $text, $html,
                $attachment ?? '', $attachname, true);
        } catch (\Throwable $e) {
            $ok = false;
        }
        ($this->log)(($ok ? 'Email enviado: ' : 'Email FALLIDO: ') . "{$template} → {$to}");
        return (bool)$ok;
    }

    /**
     * Reserva un envío del cupo diario.
     *
     * @return bool false si ya se alcanzó el límite
     */
    protected function reserve_daily_slot(): bool {
        $limit = $this->config->int('dailyemaillimit');
        if ($limit <= 0) {
            return true;
        }
        $today = date('Ymd');
        [$day, $count] = array_pad(explode(':', (string)get_config(config::COMPONENT, self::DAILY_COUNTER)), 2, 0);
        $count = $day === $today ? (int)$count : 0;
        if ($count >= $limit) {
            return false;
        }
        set_config(self::DAILY_COUNTER, $today . ':' . ($count + 1), config::COMPONENT);
        return true;
    }

    /**
     * Variables comunes a todas las plantillas.
     *
     * @return array
     */
    protected function common_context(): array {
        global $CFG;
        $support = $this->config->str('supporturl');
        return [
            'siteurl' => $CFG->wwwroot,
            'supporturl' => $support !== '' ? $support : $CFG->wwwroot . '/soporte/',
            'forgoturl' => $CFG->wwwroot . '/login/forgot_password.php',
            'helpcourseurl' => (new \moodle_url('/course/view.php', ['id' => $this->config->int('helpcourseid')]))->out(false),
        ];
    }
}
