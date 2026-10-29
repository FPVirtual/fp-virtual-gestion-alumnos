<?php
// Función webservice que devuelve el snapshot completo de Moodle
// (usuarios con custom fields de SIGAD + matriculaciones) en una llamada.

namespace local_fpvirtual_gestion_alumnado\external;

defined('MOODLE_INTERNAL') || die();

require_once($CFG->libdir . '/externallib.php');

use context_system;
use external_api;
use external_function_parameters;
use external_multiple_structure;
use external_single_structure;
use external_value;

/**
 * Snapshot de Moodle para el proceso Python de gestión de alumnado.
 *
 * El plugin NO implementa la sincronización: solo sirve los datos
 * que el paquete Python (gestion_alumnos) consume vía API REST.
 */
class get_snapshot extends external_api {

    /** Shortnames de los campos de perfil que interesan a SIGAD. */
    private const CAMPOS_SIGAD = ['IdSIGAD', 'emailsigad', 'consentimientoCDD'];

    /**
     * Parámetros de la función (no recibe ninguno).
     */
    public static function execute_parameters(): external_function_parameters {
        return new external_function_parameters([]);
    }

    /**
     * Devuelve usuarios y matrículas de Moodle.
     *
     * @return array con claves 'usuarios' y 'matriculas'
     */
    public static function execute(): array {
        global $DB;

        $context = context_system::instance();
        self::validate_context($context);
        require_capability('local/fpvirtual_gestion_alumnado:usewebservice', $context);

        return [
            'usuarios' => self::obtener_usuarios($DB),
            'matriculas' => self::obtener_matriculas($DB),
        ];
    }

    /**
     * Usuarios no eliminados, con sus campos personalizados de SIGAD.
     *
     * @param \moodle_database $db
     * @return array
     */
    private static function obtener_usuarios(\moodle_database $db): array {
        [$insql, $params] = $db->get_in_or_equal(self::CAMPOS_SIGAD, SQL_PARAMS_NAMED, 'cf');

        $sql = "SELECT u.id, u.username, u.email, u.firstname, u.lastname, u.suspended,
                       f.shortname AS cf_shortname, d.data AS cf_value
                  FROM {user} u
             LEFT JOIN {user_info_data} d ON d.userid = u.id
             LEFT JOIN {user_info_field} f ON f.id = d.fieldid AND f.shortname $insql
                 WHERE u.deleted = 0
              ORDER BY u.id";
        $rows = $db->get_records_sql($sql, $params);

        $usuarios = [];
        foreach ($rows as $row) {
            $id = (int)$row->id;
            if (!isset($usuarios[$id])) {
                $usuarios[$id] = [
                    'id' => $id,
                    'username' => $row->username,
                    'email' => $row->email,
                    'firstname' => $row->firstname,
                    'lastname' => $row->lastname,
                    'suspended' => (int)$row->suspended,
                    'customfields' => [],
                ];
            }
            if ($row->cf_shortname !== null) {
                $usuarios[$id]['customfields'][] = [
                    'shortname' => $row->cf_shortname,
                    'value' => (string)$row->cf_value,
                ];
            }
        }

        return array_values($usuarios);
    }

    /**
     * Matrículas de usuario en curso con shortname y estado.
     *
     * @param \moodle_database $db
     * @return array
     */
    private static function obtener_matriculas(\moodle_database $db): array {
        $sql = "SELECT ue.userid, e.courseid, c.shortname, ue.status
                  FROM {user_enrolments} ue
                  JOIN {enrol} e ON e.id = ue.enrolid
                  JOIN {course} c ON c.id = e.courseid
              ORDER BY ue.userid, e.courseid";
        $rows = $db->get_records_sql($sql);

        $matriculas = [];
        foreach ($rows as $row) {
            $matriculas[] = [
                'userid' => (int)$row->userid,
                'courseid' => (int)$row->courseid,
                'shortname' => $row->shortname,
                'status' => (int)$row->status,
            ];
        }

        return $matriculas;
    }

    /**
     * Estructura de retorno de la función.
     */
    public static function execute_returns(): external_single_structure {
        $campo = new external_single_structure([
            'shortname' => new external_value(PARAM_ALPHANUMEXT, 'Shortname del campo personalizado'),
            'value' => new external_value(PARAM_RAW, 'Valor del campo personalizado'),
        ]);

        $usuario = new external_single_structure([
            'id' => new external_value(PARAM_INT, 'ID del usuario'),
            'username' => new external_value(PARAM_RAW, 'Username'),
            'email' => new external_value(PARAM_RAW, 'Email', VALUE_OPTIONAL),
            'firstname' => new external_value(PARAM_RAW, 'Nombre', VALUE_OPTIONAL),
            'lastname' => new external_value(PARAM_RAW, 'Apellidos', VALUE_OPTIONAL),
            'suspended' => new external_value(PARAM_INT, '1 si el usuario está suspendido'),
            'customfields' => new external_multiple_structure($campo, 'Campos personalizados de SIGAD'),
        ]);

        $matricula = new external_single_structure([
            'userid' => new external_value(PARAM_INT, 'ID del usuario'),
            'courseid' => new external_value(PARAM_INT, 'ID del curso'),
            'shortname' => new external_value(PARAM_RAW, 'Shortname del curso'),
            'status' => new external_value(PARAM_INT, '0 = activa, 1 = suspendida'),
        ]);

        return new external_single_structure([
            'usuarios' => new external_multiple_structure($usuario, 'Usuarios de Moodle'),
            'matriculas' => new external_multiple_structure($matricula, 'Matrículas usuario-curso'),
        ]);
    }
}
