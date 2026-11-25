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
 * Compara SIGAD con Moodle y calcula el {@see plan} (sin escribir nada).
 *
 * Implementa las reglas R2–R16 del roadmap (docus/roadmap-v0.4-plugin-php.md).
 *
 * @package    local_fpvirtual_gestion_alumnado
 * @copyright  2026 FP virtual Aragón
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class analyzer {

    /** @var dataset */
    protected dataset $sigad;

    /** @var moodle_state */
    protected moodle_state $moodle;

    /** @var config */
    protected config $config;

    /** @var int Momento de referencia (limpieza mensual R16). */
    protected int $now;

    /** @var plan */
    protected plan $plan;

    /** @var array<int, bool> ids de usuario de Moodle emparejados con SIGAD. */
    protected array $matched = [];

    /** @var array<string, bool> Avisos de curso/cohorte inexistente ya emitidos. */
    protected array $missing = [];

    /** @var array<string, int[]> email personal => usuarios en ámbito sin IdSIGAD ni emparejar. */
    protected array $emailindex = [];

    /** @var array<string, int> email personal => número de alumnos de SIGAD que lo usan. */
    protected array $sigademails = [];

    /**
     * Constructor.
     *
     * @param dataset $sigad
     * @param moodle_state $moodle
     * @param config $config
     * @param int|null $now
     */
    public function __construct(dataset $sigad, moodle_state $moodle, config $config, ?int $now = null) {
        $this->sigad = $sigad;
        $this->moodle = $moodle;
        $this->config = $config;
        $this->now = $now ?? time();
    }

    /**
     * Calcula el plan.
     *
     * @return plan
     */
    public function analyze(): plan {
        $this->plan = new plan();
        $this->matched = [];
        $this->missing = [];

        foreach ($this->sigad->discarded as $motivo) {
            $this->plan->add(plan::DISCARDED, ['motivo' => $motivo]);
        }

        $pending = [];
        foreach ($this->sigad->students as $student) {
            $userid = $this->match($student);
            if ($userid === false) {
                continue;
            }
            if ($userid === null) {
                $pending[] = $student;
                continue;
            }
            $this->sync_existing($student, $userid);
        }

        // Alumnos sin usuario: renombrado por email (usuarios antiguos sin IdSIGAD) o alta.
        $this->build_email_indexes();
        foreach ($pending as $student) {
            $userid = $this->match_by_email($student);
            if ($userid !== null) {
                $this->sync_existing($student, $userid);
            } else {
                $this->create($student);
            }
        }

        $this->removals();
        $this->monthly_cleanup();

        $this->plan->stats = [
            'sigad_fecha' => trim($this->sigad->fecha . ' ' . $this->sigad->hora),
            'sigad_students' => $this->sigad->count(),
            'sigad_modules' => $this->sigad->count_modules(),
            'moodle_users_in_scope' => count($this->moodle->inscope),
            'moodle_active_enrolments' => $this->moodle->activemanagedenrolments,
            'matched_users' => count($this->matched),
        ];
        return $this->plan;
    }

    /**
     * Empareja un alumno con su usuario de Moodle (R1, R12).
     *
     * @param array $student
     * @return int|null|false id de usuario, null si no existe, false si no se gestiona
     */
    protected function match(array $student) {
        $userid = $this->moodle->byusername[$student['username']] ?? null;
        if ($userid !== null) {
            if (!isset($this->moodle->inscope[$userid])) {
                $this->plan->add(plan::OUT_OF_SCOPE, [
                    'username' => $student['username'], 'userid' => $userid,
                    'motivo' => 'El usuario existe pero está protegido o excluido de la sincronización.',
                ]);
                return false;
            }
            return $userid;
        }

        $candidates = $student['idsigad'] ? ($this->moodle->byidsigad[$student['idsigad']] ?? []) : [];
        if (count($candidates) > 1) {
            $this->plan->add(plan::RENAME_CONFLICT, [
                'username' => $student['username'], 'idsigad' => $student['idsigad'],
                'motivo' => 'Varios usuarios de Moodle comparten el IdSIGAD: ' .
                    implode(', ', array_map(fn($id) => $this->moodle->users[$id]['username'], $candidates)),
            ]);
            return false;
        }
        return $candidates ? $candidates[0] : null;
    }

    /**
     * Índices para el emparejamiento por email (tras emparejar por username/IdSIGAD).
     */
    protected function build_email_indexes(): void {
        $this->emailindex = [];
        $this->sigademails = [];
        foreach ($this->moodle->inscope as $id => $unused) {
            $user = $this->moodle->users[$id];
            if (!isset($this->matched[$id]) && $user['idsigad'] === null && $user['emailsigad'] !== '') {
                $this->emailindex[\core_text::strtolower($user['emailsigad'])][] = $id;
            }
        }
        foreach ($this->sigad->students as $student) {
            if ($student['email'] !== null) {
                $email = \core_text::strtolower($student['email']);
                $this->sigademails[$email] = ($this->sigademails[$email] ?? 0) + 1;
            }
        }
    }

    /**
     * Respaldo de R12 para usuarios sin IdSIGAD: emparejar por email personal único.
     *
     * @param array $student
     * @return int|null
     */
    protected function match_by_email(array $student): ?int {
        if ($student['email'] === null) {
            return null;
        }
        $email = \core_text::strtolower($student['email']);
        $found = array_values(array_filter($this->emailindex[$email] ?? [], fn($id) => !isset($this->matched[$id])));
        if (!$found) {
            return null;
        }
        if (count($found) === 1 && ($this->sigademails[$email] ?? 0) === 1) {
            return $found[0];
        }
        $this->plan->add(plan::RENAME_CONFLICT, [
            'username' => $student['username'],
            'motivo' => 'Posible cambio de documento por email, pero el email no es único.',
        ]);
        return null;
    }

    /**
     * Sincroniza un alumno que ya tiene usuario en Moodle.
     *
     * @param array $student
     * @param int $userid
     */
    protected function sync_existing(array $student, int $userid): void {
        $this->matched[$userid] = true;
        $user = $this->moodle->users[$userid];
        $ref = ['userid' => $userid, 'username' => $student['username']];

        // R12: cambio de documento.
        if ($user['username'] !== $student['username']) {
            $this->plan->add(plan::RENAME_USER, $ref + [
                'oldusername' => $user['username'], 'email' => $student['email'],
                'nombre' => $student['nombre'], 'apellidos' => $student['apellidos'],
            ]);
        }

        // R11: reactivación.
        if ($user['suspended']) {
            $this->plan->add(plan::REACTIVATE_USER, $ref);
        }

        // R12 (relleno de IdSIGAD) y R13 (email personal).
        $fields = [];
        if ($student['idsigad'] && $user['idsigad'] !== $student['idsigad']) {
            $fields[moodle_state::FIELD_IDSIGAD] = (string)$student['idsigad'];
        }
        if ($student['email'] !== null
                && \core_text::strtolower($student['email']) !== \core_text::strtolower($user['emailsigad'])) {
            $fields[moodle_state::FIELD_EMAILSIGAD] = $student['email'];
        }
        if ($fields) {
            $old = [
                moodle_state::FIELD_IDSIGAD => (string)$user['idsigad'],
                moodle_state::FIELD_EMAILSIGAD => $user['emailsigad'],
            ];
            $this->plan->add(plan::UPDATE_PROFILE, $ref + ['fields' => $fields, 'old' => array_intersect_key($old, $fields)]);
        }

        // R14: nombre y apellidos.
        if ($this->config->bool('syncnames') && $student['nombre'] !== null && $student['apellido1'] !== null
                && ($student['nombre'] !== $user['firstname'] || $student['apellidos'] !== $user['lastname'])) {
            $this->plan->add(plan::UPDATE_NAME, $ref + [
                'firstname' => $student['nombre'], 'lastname' => $student['apellidos'],
                'oldfirstname' => $user['firstname'], 'oldlastname' => $user['lastname'],
            ]);
        }

        $this->sync_cohorts($student, $ref, $this->moodle->cohortmembers[$userid] ?? []);
        $this->sync_enrolments($student, $ref, $this->moodle->enrolments[$userid] ?? []);
    }

    /**
     * Alta de un alumno nuevo (R5) con sus cohortes y matrículas.
     *
     * @param array $student
     */
    protected function create(array $student): void {
        if ($student['missing']) {
            $this->plan->add(plan::NOT_CREATABLE, [
                'username' => $student['username'],
                'motivo' => 'Faltan datos en SIGAD: ' . implode(', ', $student['missing']),
            ]);
            return;
        }
        $this->plan->add(plan::CREATE_USER, [
            'userid' => null,
            'username' => $student['username'],
            'documento' => $student['documento'],
            'idsigad' => $student['idsigad'],
            'idtipodocumento' => $student['idtipodocumento'],
            'firstname' => $student['nombre'],
            'lastname' => $student['apellidos'],
            'email' => $student['email'],
        ]);
        $ref = ['userid' => null, 'username' => $student['username']];
        $this->sync_cohorts($student, $ref, []);
        $this->sync_enrolments($student, $ref, []);
    }

    /**
     * R6 y R15: cohorte general + cohortes de ciclo.
     *
     * @param array $student
     * @param array $ref referencia al usuario (userid/username)
     * @param array<string, bool> $current cohortes gestionadas actuales
     */
    protected function sync_cohorts(array $student, array $ref, array $current): void {
        $expected = array_merge([$this->config->str('cohortalumnado')], $student['cohorts']);
        foreach ($expected as $name) {
            if (isset($current[$name])) {
                continue;
            }
            if (!isset($this->moodle->cohorts[$name])) {
                $this->missing_notice(plan::MISSING_COHORT, $name);
                continue;
            }
            $this->plan->add(plan::ADD_COHORT, $ref + ['cohort' => $name, 'cohortid' => $this->moodle->cohorts[$name]]);
        }
        foreach (array_keys($current) as $name) {
            if (!in_array($name, $expected, true)) {
                $this->plan->add(plan::REMOVE_COHORT, $ref + ['cohort' => $name, 'cohortid' => $this->moodle->cohorts[$name]]);
            }
        }
    }

    /**
     * R7, R8 y R9: matrículas en cursos gestionados.
     *
     * @param array $student
     * @param array $ref
     * @param array<string, array[]> $current matrículas actuales por shortname
     */
    protected function sync_enrolments(array $student, array $ref, array $current): void {
        foreach ($student['modules'] as $shortname => $module) {
            $courseid = $this->moodle->courses[$shortname] ?? null;
            if ($courseid === null) {
                $this->missing_notice(plan::MISSING_COURSE, $shortname, $module['centro'] . ' · ' .
                    $module['ciclo'] . ' · ' . $module['modulo']);
                continue;
            }
            $op = $ref + ['courseid' => $courseid, 'shortname' => $shortname, 'modulo' => $module['modulo']];
            $enrolments = $current[$shortname] ?? [];
            if (!$enrolments) {
                $this->plan->add(plan::ENROL, $op);
                continue;
            }
            if (array_filter($enrolments, fn($e) => $e['active'])) {
                continue;
            }
            $manual = array_values(array_filter($enrolments, fn($e) => $e['enrol'] === 'manual'));
            if ($manual) {
                $this->plan->add(plan::REACTIVATE_ENROL, $op + ['ueid' => $manual[0]['ueid'], 'enrolid' => $manual[0]['enrolid']]);
            } else {
                $this->plan->add(plan::ENROL, $op);
            }
        }

        foreach ($current as $shortname => $enrolments) {
            if (!isset($student['modules'][$shortname])) {
                $this->suspend_enrolments($ref, $shortname, $enrolments, 'No figura en SIGAD');
            }
        }
    }

    /**
     * Suspende las matrículas manuales activas de un curso.
     *
     * @param array $ref
     * @param string $shortname
     * @param array[] $enrolments
     * @param string $motivo
     */
    protected function suspend_enrolments(array $ref, string $shortname, array $enrolments, string $motivo): void {
        foreach ($enrolments as $e) {
            if ($e['active'] && $e['enrol'] === 'manual') {
                $this->plan->add(plan::SUSPEND_ENROL, $ref + [
                    'courseid' => $e['courseid'], 'shortname' => $shortname,
                    'ueid' => $e['ueid'], 'enrolid' => $e['enrolid'], 'motivo' => $motivo,
                ]);
            }
        }
    }

    /**
     * R10: usuarios en ámbito, activos, que no están en SIGAD.
     */
    protected function removals(): void {
        foreach ($this->moodle->inscope as $userid => $unused) {
            $user = $this->moodle->users[$userid];
            if (isset($this->matched[$userid]) || $user['suspended']) {
                continue;
            }
            $ref = ['userid' => $userid, 'username' => $user['username']];
            foreach (($this->moodle->enrolments[$userid] ?? []) as $shortname => $enrolments) {
                $this->suspend_enrolments($ref, $shortname, $enrolments, 'Baja: no figura en SIGAD');
            }
            foreach (array_keys($this->moodle->cohortmembers[$userid] ?? []) as $name) {
                $this->plan->add(plan::REMOVE_COHORT, $ref + ['cohort' => $name, 'cohortid' => $this->moodle->cohorts[$name]]);
            }
            $this->plan->add(plan::SUSPEND_USER, $ref + [
                'firstname' => $user['firstname'], 'lastname' => $user['lastname'],
            ]);
        }
    }

    /**
     * R16: en el mes de limpieza, eliminar matrículas manuales suspendidas.
     */
    protected function monthly_cleanup(): void {
        if (!$this->config->bool('cleanupenabled') || (int)date('n', $this->now) !== $this->config->int('cleanupmonth')) {
            return;
        }
        $reactivated = array_flip(array_column($this->plan->get(plan::REACTIVATE_ENROL), 'ueid'));
        foreach ($this->moodle->enrolments as $userid => $courses) {
            foreach ($courses as $shortname => $enrolments) {
                foreach ($enrolments as $e) {
                    if ($e['enrol'] === 'manual' && $e['status'] === ENROL_USER_SUSPENDED && !isset($reactivated[$e['ueid']])) {
                        $this->plan->add(plan::UNENROL, [
                            'userid' => $userid, 'username' => $this->moodle->users[$userid]['username'],
                            'courseid' => $e['courseid'], 'shortname' => $shortname,
                            'ueid' => $e['ueid'], 'enrolid' => $e['enrolid'],
                        ]);
                    }
                }
            }
        }
    }

    /**
     * Aviso de curso o cohorte inexistente (uno por elemento, con número de afectados).
     *
     * @param string $type
     * @param string $name
     * @param string $detail
     */
    protected function missing_notice(string $type, string $name, string $detail = ''): void {
        $key = $type . '|' . $name;
        if (!isset($this->missing[$key])) {
            $this->missing[$key] = true;
            $this->plan->add($type, ['nombre' => $name, 'detalle' => $detail]);
        }
    }
}
