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
use local_fpvirtual_gestion_alumnado\sigad\dataset;

/**
 * Ejecuta un {@see plan} con las APIs internas de Moodle.
 *
 * Nunca escribe con SQL: usa user_create_user/user_update_user,
 * profile_save_data, las APIs de cohortes y los plugins de matriculación,
 * de modo que se disparan los eventos y se purgan las cachés.
 *
 * Cada operación es independiente: un error se registra y no detiene el resto.
 *
 * @package    local_fpvirtual_gestion_alumnado
 * @copyright  2026 FP virtual Aragón
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class applier {
    /** @var config */
    protected config $config;

    /** @var dataset|null Datos de SIGAD (para las notificaciones). */
    protected ?dataset $sigad;

    /** @var notifier_interface|null */
    protected ?notifier_interface $notifier;

    /** @var callable(string): void */
    protected $log;

    /** @var result */
    protected result $result;

    /** @var array<int, \stdClass> Instancias de matrícula manual por curso. */
    protected array $manualinstances = [];

    /** @var array<int, \stdClass> Instancias de matrícula por id. */
    protected array $instances = [];

    /** @var int|null Rol de estudiante. */
    protected ?int $studentroleid = null;

    /**
     * Constructor.
     *
     * @param config $config
     * @param dataset|null $sigad
     * @param notifier_interface|null $notifier
     * @param callable|null $log
     */
    public function __construct(
        config $config,
        ?dataset $sigad = null,
        ?notifier_interface $notifier = null,
        ?callable $log = null
    ) {
        global $CFG;
        require_once($CFG->dirroot . '/user/lib.php');
        require_once($CFG->dirroot . '/user/profile/lib.php');
        require_once($CFG->dirroot . '/cohort/lib.php');
        require_once($CFG->libdir . '/enrollib.php');

        $this->config = $config;
        $this->sigad = $sigad;
        $this->notifier = $notifier;
        $this->log = $log ?? fn(string $m) => null;
    }

    /**
     * Aplica el plan.
     *
     * @param plan $plan
     * @return result
     */
    public function apply(plan $plan): result {
        $this->result = new result();
        $newenrolments = [];

        foreach (plan::ACTIONS as $type) {
            foreach ($plan->get($type) as $op) {
                try {
                    $this->{'op_' . $type}($op);
                    $this->result->ok($type);
                    if ($type === plan::ENROL || $type === plan::REACTIVATE_ENROL) {
                        $newenrolments[$op['username']][] = $op['modulo'] ?? $op['shortname'];
                    }
                } catch (\Throwable $e) {
                    $this->result->error($type, $op['username'] ?? '', $e->getMessage());
                    ($this->log)("ERROR {$type} " . ($op['username'] ?? '') . ': ' . $e->getMessage());
                }
            }
            ($this->log)(sprintf(
                '%s: %d correctas, %d errores',
                $type,
                $this->result->done[$type] ?? 0,
                $this->result->failed[$type] ?? 0
            ));
        }

        $this->notify_enrolments($newenrolments);
        return $this->result;
    }

    /**
     * Id de usuario de una operación (los usuarios nuevos se resuelven por username).
     *
     * @param array $op
     * @return int
     */
    protected function userid(array $op): int {
        if (!empty($op['userid'])) {
            return (int)$op['userid'];
        }
        if (isset($this->result->userids[$op['username']])) {
            return $this->result->userids[$op['username']];
        }
        throw new \moodle_exception('error:usernotcreated', config::COMPONENT, '', $op['username']);
    }

    /**
     * R5: alta de usuario.
     *
     * @param array $op
     */
    protected function op_create_user(array $op): void {
        global $CFG;

        $password = self::generate_password();
        $user = (object)[
            'username' => $op['username'],
            'auth' => 'manual',
            'confirmed' => 1,
            'mnethostid' => $CFG->mnet_localhost_id,
            'firstname' => $op['firstname'],
            'lastname' => $op['lastname'],
            'email' => $op['username'] . '@' . $this->config->str('emaildomain'),
            'city' => 'Aragón',
            'country' => 'ES',
            'maildigest' => 2,
            'password' => $password,
        ];
        $userid = user_create_user($user, true, true);

        $this->save_profile($userid, array_filter([
            'idsigad' => $op['idsigad'] ? (string)$op['idsigad'] : null,
            'tipodocumento' => $op['idtipodocumento'] ? (string)$op['idtipodocumento'] : null,
            'emailsigad' => $op['email'],
            'consentimiento' => '0',
        ], fn($v) => $v !== null), false);
        set_user_preference('auth_forcepasswordchange', 1, $userid);

        $this->result->userids[$op['username']] = $userid;
        $this->result->created[] = [
            'username' => $op['username'],
            'firstname' => $op['firstname'],
            'lastname' => $op['lastname'],
            'email' => $user->email,
            'emailsigad' => $op['email'],
            'password' => $password,
        ];

        if ($this->notifier) {
            $student = $this->student($op['username']) ?? [];
            $modules = array_values(array_map(
                fn($m) => $m['centro'] . ' - ' . $m['ciclo'] . ' - ' . $m['modulo'],
                $student['modules'] ?? []
            ));
            $this->notifier->welcome($op + ['institutionalemail' => $user->email], $password, $modules);
        }
    }

    /**
     * R12: cambio de username.
     *
     * @param array $op
     */
    protected function op_rename_user(array $op): void {
        global $DB, $CFG;

        if ($DB->record_exists('user', ['username' => $op['username'], 'mnethostid' => $CFG->mnet_localhost_id])) {
            throw new \moodle_exception('error:usernametaken', config::COMPONENT, '', $op['username']);
        }
        user_update_user((object)['id' => $this->userid($op), 'username' => $op['username']], false, true);
        if ($this->notifier) {
            $this->notifier->username_changed($op);
        }
    }

    /**
     * R12/R13: campos de perfil.
     *
     * @param array $op
     */
    protected function op_update_profile(array $op): void {
        $this->save_profile($this->userid($op), $op['fields'], true);
    }

    /**
     * R14: nombre y apellidos.
     *
     * @param array $op
     */
    protected function op_update_name(array $op): void {
        user_update_user((object)[
            'id' => $this->userid($op), 'firstname' => $op['firstname'], 'lastname' => $op['lastname'],
        ], false, true);
    }

    /**
     * R11: reactivar cuenta.
     *
     * @param array $op
     */
    protected function op_reactivate_user(array $op): void {
        user_update_user((object)['id' => $this->userid($op), 'suspended' => 0], false, true);
    }

    /**
     * R6: alta en cohorte.
     *
     * @param array $op
     */
    protected function op_add_cohort(array $op): void {
        cohort_add_member((int)$op['cohortid'], $this->userid($op));
    }

    /**
     * R7: matrícula manual como estudiante.
     *
     * @param array $op
     */
    protected function op_enrol(array $op): void {
        $instance = $this->manual_instance((int)$op['courseid']);
        enrol_get_plugin('manual')->enrol_user($instance, $this->userid($op), $this->student_role());
    }

    /**
     * R8: reactivar matrícula.
     *
     * @param array $op
     */
    protected function op_reactivate_enrol(array $op): void {
        $this->update_enrolment($op, ENROL_USER_ACTIVE);
    }

    /**
     * R9/R10: suspender matrícula (conserva el progreso).
     *
     * @param array $op
     */
    protected function op_suspend_enrol(array $op): void {
        $this->update_enrolment($op, ENROL_USER_SUSPENDED);
    }

    /**
     * R10/R15: baja de cohorte.
     *
     * @param array $op
     */
    protected function op_remove_cohort(array $op): void {
        cohort_remove_member((int)$op['cohortid'], $this->userid($op));
    }

    /**
     * R10: suspender cuenta y cerrar sus sesiones.
     *
     * @param array $op
     */
    protected function op_suspend_user(array $op): void {
        $userid = $this->userid($op);
        user_update_user((object)['id' => $userid, 'suspended' => 1], false, true);
        if (method_exists(\core\session\manager::class, 'destroy_user_sessions')) {
            \core\session\manager::destroy_user_sessions($userid); // Moodle 4.5+.
        } else {
            \core\session\manager::kill_user_sessions($userid);
        }
    }

    /**
     * R16: eliminar matrícula suspendida.
     *
     * @param array $op
     */
    protected function op_unenrol(array $op): void {
        $instance = $this->instance((int)$op['enrolid']);
        enrol_get_plugin($instance->enrol)->unenrol_user($instance, $this->userid($op));
    }

    /**
     * Cambia el estado de una matrícula existente.
     *
     * @param array $op
     * @param int $status
     */
    protected function update_enrolment(array $op, int $status): void {
        $instance = $this->instance((int)$op['enrolid']);
        enrol_get_plugin($instance->enrol)->update_user_enrol($instance, $this->userid($op), $status);
    }

    /**
     * Guarda campos de perfil y opcionalmente dispara user_updated.
     *
     * @param int $userid
     * @param array $fields clave lógica (config::PROFILE_FIELDS) => valor
     * @param bool $event
     */
    protected function save_profile(int $userid, array $fields, bool $event): void {
        $shortnames = $this->config->profile_fields();
        $data = (object)['id' => $userid];
        foreach ($fields as $field => $value) {
            // Clave lógica => shortname configurado; los opcionales vacíos no se escriben.
            if (isset($shortnames[$field])) {
                $data->{'profile_field_' . $shortnames[$field]} = $value;
            }
        }
        profile_save_data($data);
        if ($event) {
            \core\event\user_updated::create_from_userid($userid)->trigger();
        }
    }

    /**
     * Instancia de matrícula manual activa de un curso.
     *
     * @param int $courseid
     * @return \stdClass
     */
    protected function manual_instance(int $courseid): \stdClass {
        if (!isset($this->manualinstances[$courseid])) {
            $manual = array_filter(enrol_get_instances($courseid, true), fn($i) => $i->enrol === 'manual');
            if (!$manual) {
                throw new \moodle_exception('error:nomanualenrol', config::COMPONENT, '', $courseid);
            }
            $this->manualinstances[$courseid] = reset($manual);
        }
        return $this->manualinstances[$courseid];
    }

    /**
     * Instancia de matrícula por id.
     *
     * @param int $enrolid
     * @return \stdClass
     */
    protected function instance(int $enrolid): \stdClass {
        global $DB;
        return $this->instances[$enrolid] ??= $DB->get_record('enrol', ['id' => $enrolid], '*', MUST_EXIST);
    }

    /**
     * Id del rol de estudiante.
     *
     * @return int
     */
    protected function student_role(): int {
        if ($this->studentroleid === null) {
            $roles = get_archetype_roles('student');
            if (!$roles) {
                throw new \moodle_exception('error:nostudentrole', config::COMPONENT);
            }
            $this->studentroleid = (int)reset($roles)->id;
        }
        return $this->studentroleid;
    }

    /**
     * Datos de SIGAD de un alumno.
     *
     * @param string $username
     * @return array|null
     */
    protected function student(string $username): ?array {
        return $this->sigad ? $this->sigad->student($username) : null;
    }

    /**
     * Aviso de nuevas matrículas a alumnos que ya existían (los nuevos lo reciben en la bienvenida).
     *
     * @param array<string, string[]> $byusername
     */
    protected function notify_enrolments(array $byusername): void {
        if (!$this->notifier) {
            return;
        }
        foreach ($byusername as $username => $modules) {
            if (isset($this->result->userids[$username])) {
                continue;
            }
            $student = $this->student($username);
            if ($student) {
                $this->notifier->new_enrolments($student, $modules);
            }
        }
    }

    /**
     * Contraseña inicial aleatoria que cumple la política de contraseñas del sitio.
     *
     * Se prefiere alfanumérica sin caracteres ambiguos (fácil de teclear); si la
     * política exige otros caracteres se usa el generador de Moodle, que la respeta.
     * user_create_user() valida la política y rechaza las que no la cumplen.
     *
     * @param int $length
     * @return string
     */
    public static function generate_password(int $length = 10): string {
        global $CFG;

        $chars = 'abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789';
        $length = max($length, (int)($CFG->minpasswordlength ?? 0));
        $password = '';
        for ($i = 0; $i < $length; $i++) {
            $password .= $chars[random_int(0, strlen($chars) - 1)];
        }
        $errmsg = '';
        if (!check_password_policy($password, $errmsg)) {
            $password = generate_password($length);
        }
        return $password;
    }
}
