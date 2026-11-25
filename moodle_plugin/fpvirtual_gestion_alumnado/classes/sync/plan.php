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
 * Plan de sincronización: operaciones calculadas por el analizador.
 *
 * Es un objeto de datos serializable a JSON. En modo dry se informa; en
 * modo apply lo ejecuta el {@see applier} en el orden de {@see plan::ACTIONS}.
 *
 * @package    local_fpvirtual_gestion_alumnado
 * @copyright  2026 FP virtual Aragón
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class plan {
    // Acciones (escriben en Moodle), en orden de ejecución.
    /** Alta de usuario (R5). */
    public const CREATE_USER = 'create_user';
    /** Cambio de username por cambio de documento (R12). */
    public const RENAME_USER = 'rename_user';
    /** Actualización de campos de perfil IdSIGAD / emailsigad (R12, R13). */
    public const UPDATE_PROFILE = 'update_profile';
    /** Actualización de nombre y apellidos (R14). */
    public const UPDATE_NAME = 'update_name';
    /** Reactivación de cuenta suspendida (R11). */
    public const REACTIVATE_USER = 'reactivate_user';
    /** Alta en cohorte (R6). */
    public const ADD_COHORT = 'add_cohort';
    /** Nueva matrícula (R7). */
    public const ENROL = 'enrol';
    /** Reactivación de matrícula suspendida (R8). */
    public const REACTIVATE_ENROL = 'reactivate_enrol';
    /** Suspensión de matrícula (R9, R10). */
    public const SUSPEND_ENROL = 'suspend_enrol';
    /** Baja de cohorte (R10, R15). */
    public const REMOVE_COHORT = 'remove_cohort';
    /** Suspensión de cuenta (R10). */
    public const SUSPEND_USER = 'suspend_user';
    /** Limpieza de matrículas suspendidas (R16). */
    public const UNENROL = 'unenrol';

    /** @var string[] Acciones en orden de ejecución. */
    public const ACTIONS = [
        self::CREATE_USER, self::RENAME_USER, self::UPDATE_PROFILE, self::UPDATE_NAME,
        self::REACTIVATE_USER, self::ADD_COHORT, self::ENROL, self::REACTIVATE_ENROL,
        self::SUSPEND_ENROL, self::REMOVE_COHORT, self::SUSPEND_USER, self::UNENROL,
    ];

    // Avisos (no escriben; requieren revisión humana).
    /** Alumno de SIGAD sin datos obligatorios. */
    public const NOT_CREATABLE = 'not_creatable';
    /** Curso de SIGAD inexistente en Moodle. */
    public const MISSING_COURSE = 'missing_course';
    /** Cohorte inexistente en Moodle. */
    public const MISSING_COHORT = 'missing_cohort';
    /** Cambio de documento que no se puede aplicar automáticamente. */
    public const RENAME_CONFLICT = 'rename_conflict';
    /** Alumno de SIGAD cuyo username pertenece a un usuario fuera de ámbito. */
    public const OUT_OF_SCOPE = 'out_of_scope';
    /** Registro de SIGAD descartado. */
    public const DISCARDED = 'discarded';

    /** @var string[] Tipos de aviso. */
    public const NOTICES = [
        self::NOT_CREATABLE, self::MISSING_COURSE, self::MISSING_COHORT,
        self::RENAME_CONFLICT, self::OUT_OF_SCOPE, self::DISCARDED,
    ];

    /** @var array<string, array[]> Operaciones por tipo. */
    protected array $ops = [];

    /** @var array Métricas del análisis (tamaños de SIGAD y Moodle). */
    public array $stats = [];

    /**
     * Añade una operación.
     *
     * @param string $type
     * @param array $data
     */
    public function add(string $type, array $data): void {
        if (!in_array($type, self::ACTIONS, true) && !in_array($type, self::NOTICES, true)) {
            throw new \coding_exception('Tipo de operación desconocido: ' . $type);
        }
        $this->ops[$type][] = $data;
    }

    /**
     * Operaciones de un tipo.
     *
     * @param string $type
     * @return array[]
     */
    public function get(string $type): array {
        return $this->ops[$type] ?? [];
    }

    /**
     * Número de operaciones de un tipo.
     *
     * @param string $type
     * @return int
     */
    public function count(string $type): int {
        return count($this->ops[$type] ?? []);
    }

    /**
     * Conteo de todas las acciones y avisos.
     *
     * @return int[]
     */
    public function counts(): array {
        $counts = [];
        foreach (array_merge(self::ACTIONS, self::NOTICES) as $type) {
            $counts[$type] = $this->count($type);
        }
        return $counts;
    }

    /**
     * Número total de acciones (escrituras).
     *
     * @return int
     */
    public function total_actions(): int {
        return array_sum(array_map(fn($t) => $this->count($t), self::ACTIONS));
    }

    /**
     * Guardas de seguridad (R17): motivos para no aplicar el plan.
     *
     * @param config $config
     * @return string[] vacío si el plan es aplicable
     */
    public function check_limits(config $config): array {
        $violations = [];

        $max = $config->int('maxusersuspensions');
        if ($max > 0 && $this->count(self::SUSPEND_USER) > $max) {
            $violations[] = "Se suspenderían {$this->count(self::SUSPEND_USER)} usuarios (máximo {$max}).";
        }

        $pct = $config->int('maxenrolsuspendpercent');
        $base = (int)($this->stats['moodle_active_enrolments'] ?? 0);
        if ($pct > 0) {
            // Mínimo de 20 para que instalaciones pequeñas no bloqueen por redondeo.
            $limit = max(20, (int)ceil($base * $pct / 100));
            if ($this->count(self::SUSPEND_ENROL) > $limit) {
                $violations[] = "Se suspenderían {$this->count(self::SUSPEND_ENROL)} matrículas " .
                    "de {$base} activas (máximo {$pct} % = {$limit}).";
            }
        }
        return $violations;
    }

    /**
     * Representación serializable.
     *
     * @return array
     */
    public function to_array(): array {
        return ['stats' => $this->stats, 'counts' => $this->counts(), 'operations' => $this->ops];
    }

    /**
     * Reconstruye un plan desde {@see to_array()}.
     *
     * @param array $data
     * @return self
     */
    public static function from_array(array $data): self {
        $plan = new self();
        $plan->stats = $data['stats'] ?? [];
        foreach (($data['operations'] ?? []) as $type => $ops) {
            foreach ($ops as $op) {
                $plan->add($type, $op);
            }
        }
        return $plan;
    }
}
