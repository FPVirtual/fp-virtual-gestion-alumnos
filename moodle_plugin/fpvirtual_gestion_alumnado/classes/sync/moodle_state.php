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
 * Estado actual de Moodle relevante para la sincronización (solo lectura).
 *
 * Se lee con SQL a través de $DB (recordsets) y se indexa en memoria para
 * que el análisis sea O(n) e independiente del motor de base de datos
 * (las colaciones de MariaDB comparan sin distinguir mayúsculas; las de
 * PostgreSQL no).
 *
 * @package    local_fpvirtual_gestion_alumnado
 * @copyright  2026 FP virtual Aragón
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class moodle_state {

    /** @var string Campo de perfil con el identificador de SIGAD. */
    public const FIELD_IDSIGAD = 'IdSIGAD';

    /** @var string Campo de perfil con el email personal de SIGAD. */
    public const FIELD_EMAILSIGAD = 'emailsigad';

    /** @var array[] Usuarios no borrados por id: id, username, firstname, lastname, suspended, idsigad, emailsigad. */
    public array $users = [];

    /** @var int[] username (minúsculas) => id, de todos los usuarios no borrados. */
    public array $byusername = [];

    /** @var array<int, int[]> IdSIGAD => ids de usuario. */
    public array $byidsigad = [];

    /** @var array<int, bool> ids de usuario dentro del ámbito gestionado (R2). */
    public array $inscope = [];

    /** @var int[] shortname => courseid de todos los cursos. */
    public array $courses = [];

    /** @var array<int, array<string, array[]>> userid => shortname => matrículas en cursos gestionados. */
    public array $enrolments = [];

    /** @var int[] nombre de cohorte => id. */
    public array $cohorts = [];

    /** @var array<int, array<string, bool>> userid => nombre de cohorte gestionada => true. */
    public array $cohortmembers = [];

    /** @var int Matrículas activas en cursos gestionados de usuarios en ámbito. */
    public int $activemanagedenrolments = 0;

    /** @var config */
    protected config $config;

    /**
     * Constructor.
     *
     * @param config $config
     */
    public function __construct(config $config) {
        $this->config = $config;
    }

    /**
     * Carga el estado completo desde la base de datos.
     *
     * @param config $config
     * @return self
     */
    public static function load(config $config): self {
        $state = new self($config);
        $state->load_users();
        $state->load_courses();
        $state->load_enrolments();
        $state->load_cohorts();
        return $state;
    }

    /**
     * ¿El curso se sincroniza matrícula a matrícula? (R3, R4)
     *
     * Solo cursos {codigoCentro}-{siglasCiclo}-{idMateria} con idMateria
     * numérico: las tutorías (…-NNt) y el curso de ayuda quedan fuera.
     *
     * @param string $shortname
     * @return bool
     */
    public function is_managed_course(string $shortname): bool {
        return preg_match('/^\d+-[^-\s]+-\d+$/', $shortname) === 1
            && !in_array($shortname, $this->config->list('excludedcourses'), true);
    }

    /**
     * ¿La cohorte la gestiona la sincronización? (R6)
     *
     * @param string $name
     * @return bool
     */
    public function is_managed_cohort(string $name): bool {
        return $name === $this->config->str('cohortalumnado') || preg_match('/^\d+-[^-\s]+$/', $name) === 1;
    }

    /**
     * Usuarios (R2): no borrados, de esta instalación, fuera de protegidos, cuentas de
     * servicio web y prefijos excluidos.
     */
    protected function load_users(): void {
        global $DB, $CFG;

        $fields = $DB->get_records_list('user_info_field', 'shortname',
            [self::FIELD_IDSIGAD, self::FIELD_EMAILSIGAD], '', 'shortname, id');
        $idsigadfield = isset($fields[self::FIELD_IDSIGAD]) ? (int)$fields[self::FIELD_IDSIGAD]->id : 0;
        $emailfield = isset($fields[self::FIELD_EMAILSIGAD]) ? (int)$fields[self::FIELD_EMAILSIGAD]->id : 0;

        $sql = "SELECT u.id, u.username, u.auth, u.firstname, u.lastname, u.suspended,
                       ids.data AS idsigad, em.data AS emailsigad
                  FROM {user} u
             LEFT JOIN {user_info_data} ids ON ids.userid = u.id AND ids.fieldid = :f1
             LEFT JOIN {user_info_data} em ON em.userid = u.id AND em.fieldid = :f2
                 WHERE u.deleted = 0 AND u.mnethostid = :host";
        $rs = $DB->get_recordset_sql($sql, ['f1' => $idsigadfield, 'f2' => $emailfield, 'host' => $CFG->mnet_localhost_id]);

        $protected = array_flip($this->config->protected_user_ids());
        $prefixes = array_map('core_text::strtolower', $this->config->list('excludedprefixes'));

        foreach ($rs as $r) {
            $id = (int)$r->id;
            $username = \core_text::strtolower($r->username);
            $idsigad = is_numeric($r->idsigad) && (int)$r->idsigad > 0 ? (int)$r->idsigad : null;
            $this->users[$id] = [
                'id' => $id,
                'username' => $username,
                'firstname' => (string)$r->firstname,
                'lastname' => (string)$r->lastname,
                'suspended' => (int)$r->suspended,
                'idsigad' => $idsigad,
                'emailsigad' => trim((string)$r->emailsigad),
            ];
            $this->byusername[$username] = $id;

            // Cuentas protegidas y de servicio web nunca se gestionan.
            $excluded = isset($protected[$id]) || $r->auth === 'webservice';
            foreach ($prefixes as $prefix) {
                $excluded = $excluded || str_starts_with($username, $prefix);
            }
            if (!$excluded) {
                $this->inscope[$id] = true;
                if ($idsigad) {
                    $this->byidsigad[$idsigad][] = $id;
                }
            }
        }
        $rs->close();
    }

    /**
     * Cursos por shortname.
     */
    protected function load_courses(): void {
        global $DB;

        $rs = $DB->get_recordset_select('course', 'id <> :site', ['site' => SITEID], '', 'id, shortname');
        foreach ($rs as $r) {
            $this->courses[(string)$r->shortname] = (int)$r->id;
        }
        $rs->close();
    }

    /**
     * Matrículas de usuarios en ámbito en cursos gestionados.
     */
    protected function load_enrolments(): void {
        global $DB;

        $sql = "SELECT ue.id, ue.userid, ue.status, ue.enrolid, e.enrol, e.status AS instancestatus,
                       e.courseid, c.shortname
                  FROM {user_enrolments} ue
                  JOIN {enrol} e ON e.id = ue.enrolid
                  JOIN {course} c ON c.id = e.courseid
                 WHERE c.id <> :site";
        $rs = $DB->get_recordset_sql($sql, ['site' => SITEID]);
        foreach ($rs as $r) {
            $userid = (int)$r->userid;
            if (!isset($this->inscope[$userid]) || !$this->is_managed_course((string)$r->shortname)) {
                continue;
            }
            $active = (int)$r->status === ENROL_USER_ACTIVE && (int)$r->instancestatus === ENROL_INSTANCE_ENABLED;
            $this->enrolments[$userid][(string)$r->shortname][] = [
                'ueid' => (int)$r->id,
                'enrolid' => (int)$r->enrolid,
                'enrol' => (string)$r->enrol,
                'courseid' => (int)$r->courseid,
                'status' => (int)$r->status,
                'active' => $active,
            ];
            if ($active) {
                $this->activemanagedenrolments++;
            }
        }
        $rs->close();
    }

    /**
     * Cohortes gestionadas y sus miembros en ámbito.
     */
    protected function load_cohorts(): void {
        global $DB;

        $managed = [];
        foreach ($DB->get_records('cohort', null, 'id', 'id, name') as $c) {
            if ($this->is_managed_cohort((string)$c->name)) {
                $this->cohorts[(string)$c->name] = (int)$c->id;
                $managed[(int)$c->id] = (string)$c->name;
            }
        }
        if (!$managed) {
            return;
        }
        [$insql, $params] = $DB->get_in_or_equal(array_keys($managed), SQL_PARAMS_NAMED);
        $rs = $DB->get_recordset_select('cohort_members', "cohortid $insql", $params, '', 'id, cohortid, userid');
        foreach ($rs as $r) {
            if (isset($this->inscope[(int)$r->userid])) {
                $this->cohortmembers[(int)$r->userid][$managed[(int)$r->cohortid]] = true;
            }
        }
        $rs->close();
    }
}
