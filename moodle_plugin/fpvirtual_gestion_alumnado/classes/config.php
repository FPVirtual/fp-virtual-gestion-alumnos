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

namespace local_fpvirtual_gestion_alumnado;

/**
 * Configuración del plugin con valores por defecto y tipos normalizados.
 *
 * Única fuente de verdad de los ajustes: el resto de clases reciben una
 * instancia (inyectable en tests con {@see config::from_array()}).
 *
 * @package    local_fpvirtual_gestion_alumnado
 * @copyright  2026 FP virtual Aragón
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class config {
    /** @var string Componente. */
    public const COMPONENT = 'local_fpvirtual_gestion_alumnado';

    /**
     * @var bool[] Campos de perfil que usa la sincronización (clave lógica => obligatorio).
     *
     * El shortname real de cada uno es el ajuste field_{clave}. Los opcionales se
     * pueden dejar vacíos y entonces no se escriben.
     */
    public const PROFILE_FIELDS = [
        'idsigad' => true,
        'emailsigad' => true,
        'tipodocumento' => false,
        'consentimiento' => false,
    ];

    /** @var array Valores por defecto de cada ajuste. */
    public const DEFAULTS = [
        // Ejecución.
        'enabled' => 0,
        'launchmode' => 'dry',
        'engine' => 'php',
        'command' => 'python3 /opt/gestion_alumnos.pyz',
        'extraenv' => '',
        'timeout' => 600,
        'retentiondays' => 30,
        // SIGAD.
        'sigad_baseurl' => 'https://aplicaciones.aragon.es/pcrpe/services/alumnosFPDistancia',
        'sigad_user' => '',
        'sigad_password' => '',
        'sigad_timeout' => 60,
        'sigad_initialwait' => 10,
        'sigad_maxretries' => 10,
        'sigad_retrydelay' => 10,
        // Reglas de sincronización.
        'emaildomain' => 'fpvirtualaragon.es',
        'excludedprefixes' => 'prof',
        'protectedusers' => '',
        'excludedcourses' => 'ayuda',
        'cohortalumnado' => 'alumnado',
        'syncnames' => 1,
        // Shortnames de los campos de perfil (mdl_user_info_field).
        'field_idsigad' => 'id_sigad',
        'field_emailsigad' => 'email_sigad',
        'field_tipodocumento' => 'tipo_documento',
        'field_consentimiento' => 'consentimiento_cdd',
        'cleanupenabled' => 1,
        'cleanupmonth' => 8,
        // Guardas.
        'maxusersuspensions' => 200,
        'maxenrolsuspendpercent' => 5,
        // Notificaciones.
        'notifyenabled' => 1,
        'notifyredirect' => '',
        'dailyemaillimit' => 1000,
        'emailpause' => 1,
        'reportto' => '',
        'helpcourseid' => 654,
        'supporturl' => '',
    ];

    /** @var array Valores efectivos. */
    protected array $values;

    /**
     * Constructor.
     *
     * @param array $values valores efectivos (se completan con los por defecto)
     */
    protected function __construct(array $values) {
        $this->values = array_merge(self::DEFAULTS, array_filter($values, fn($v) => $v !== null));
    }

    /**
     * Carga la configuración guardada en Moodle.
     *
     * @return self
     */
    public static function load(): self {
        $stored = array_intersect_key((array)get_config(self::COMPONENT), self::DEFAULTS);
        // La contraseña de SIGAD se guarda cifrada (admin_setting_encryptedpassword).
        if (!empty($stored['sigad_password']) && preg_match('/^(sodium|openssl):/', $stored['sigad_password'])) {
            $stored['sigad_password'] = \core\encryption::decrypt($stored['sigad_password']);
        }
        return new self($stored);
    }

    /**
     * Construye una configuración a partir de un array (tests, CLI).
     *
     * @param array $values
     * @return self
     */
    public static function from_array(array $values = []): self {
        return new self($values);
    }

    /**
     * Valor crudo de un ajuste.
     *
     * @param string $name
     * @return mixed
     */
    public function get(string $name) {
        if (!array_key_exists($name, self::DEFAULTS)) {
            throw new \coding_exception('Ajuste desconocido: ' . $name);
        }
        return $this->values[$name];
    }

    /**
     * Valor entero de un ajuste.
     *
     * @param string $name
     * @return int
     */
    public function int(string $name): int {
        return (int)$this->get($name);
    }

    /**
     * Valor booleano de un ajuste.
     *
     * @param string $name
     * @return bool
     */
    public function bool(string $name): bool {
        return !empty($this->get($name));
    }

    /**
     * Valor de texto (recortado) de un ajuste.
     *
     * @param string $name
     * @return string
     */
    public function str(string $name): string {
        return trim((string)$this->get($name));
    }

    /**
     * Lista de valores separados por comas, espacios o saltos de línea.
     *
     * @param string $name
     * @return string[]
     */
    public function list(string $name): array {
        $parts = preg_split('/[\s,;]+/', $this->str($name), -1, PREG_SPLIT_NO_EMPTY);
        return array_values(array_unique($parts));
    }

    /**
     * IDs de usuarios protegidos (nunca se modifican), incluidos invitado y administradores.
     *
     * @return int[]
     */
    public function protected_user_ids(): array {
        global $CFG;

        $ids = array_map('intval', array_filter($this->list('protectedusers'), 'is_numeric'));
        $ids[] = (int)($CFG->siteguest ?? 1);
        foreach (explode(',', (string)($CFG->siteadmins ?? '')) as $admin) {
            if (is_numeric($admin)) {
                $ids[] = (int)$admin;
            }
        }
        return array_values(array_unique($ids));
    }

    /**
     * Shortname configurado de un campo de perfil ('' si no se usa).
     *
     * @param string $field clave lógica de PROFILE_FIELDS
     * @return string
     */
    public function field(string $field): string {
        return $this->str('field_' . $field);
    }

    /**
     * Shortnames configurados no vacíos (clave lógica => shortname).
     *
     * @return string[]
     */
    public function profile_fields(): array {
        $fields = [];
        foreach (array_keys(self::PROFILE_FIELDS) as $field) {
            if ($this->field($field) !== '') {
                $fields[$field] = $this->field($field);
            }
        }
        return $fields;
    }

    /**
     * Problemas con los campos de perfil configurados: obligatorios sin configurar
     * o shortnames que no existen en mdl_user_info_field.
     *
     * @return string[] mensajes; vacío si todo es correcto
     */
    public function profile_field_problems(): array {
        global $DB;

        $problems = [];
        foreach (self::PROFILE_FIELDS as $field => $required) {
            if ($required && $this->field($field) === '') {
                $problems[] = "El ajuste field_{$field} es obligatorio y está vacío.";
            }
        }
        $configured = $this->profile_fields();
        if ($configured) {
            // Comparación exacta en PHP: profile_save_data() usa el shortname tal cual
            // y la colación de MariaDB no distingue mayúsculas.
            $existing = $DB->get_fieldset_sql('SELECT shortname FROM {user_info_field}');
            foreach ($configured as $field => $shortname) {
                if (!in_array($shortname, $existing, true)) {
                    $problems[] = "El campo de perfil '{$shortname}' (ajuste field_{$field}) no existe en Moodle.";
                }
            }
        }
        return $problems;
    }
}
