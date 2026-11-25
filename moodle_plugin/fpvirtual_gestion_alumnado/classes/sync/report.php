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

/**
 * Informes de una ejecución: Markdown (R19) y CSV de altas de Google Workspace (R20).
 *
 * @package    local_fpvirtual_gestion_alumnado
 * @copyright  2026 FP virtual Aragón
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class report {
    /** @var string[] Títulos de cada sección del plan. */
    public const TITLES = [
        plan::CREATE_USER => 'Altas de usuario',
        plan::RENAME_USER => 'Cambios de usuario por cambio de documento',
        plan::UPDATE_PROFILE => 'Actualización de IdSIGAD / email personal',
        plan::UPDATE_NAME => 'Cambios de nombre o apellidos',
        plan::REACTIVATE_USER => 'Usuarios reactivados',
        plan::ADD_COHORT => 'Altas en cohortes',
        plan::ENROL => 'Matrículas nuevas',
        plan::REACTIVATE_ENROL => 'Matrículas reactivadas',
        plan::SUSPEND_ENROL => 'Matrículas suspendidas',
        plan::REMOVE_COHORT => 'Bajas en cohortes',
        plan::SUSPEND_USER => 'Usuarios suspendidos (no figuran en SIGAD)',
        plan::UNENROL => 'Matrículas suspendidas eliminadas (limpieza anual)',
        plan::NOT_CREATABLE => 'Alumnos que no se pueden crear',
        plan::MISSING_COURSE => 'Cursos de SIGAD que no existen en Moodle',
        plan::MISSING_COHORT => 'Cohortes que no existen en Moodle',
        plan::RENAME_CONFLICT => 'Cambios de documento que requieren revisión manual',
        plan::OUT_OF_SCOPE => 'Alumnos cuyo usuario está protegido o excluido',
        plan::DISCARDED => 'Registros de SIGAD descartados',
    ];

    /**
     * Informe Markdown completo.
     *
     * @param plan $plan
     * @param array $meta runid, modo, origen, estado, inicio, mensaje, violaciones
     * @param result|null $result null en dry-run o si no se aplicó
     * @param array $emails estadísticas del notificador
     * @return string
     */
    public static function markdown(plan $plan, array $meta, ?result $result = null, array $emails = []): string {
        $md = [];
        $md[] = '# Informe de gestión de alumnado';
        $md[] = '';
        $md[] = '- Ejecución: #' . ($meta['runid'] ?? '?') . ' (' . ($meta['origen'] ?? '') . ')';
        $md[] = '- Modo: ' . ($meta['modo'] ?? '') . ($result ? '' : ' — **no se ha escrito nada en Moodle**');
        $md[] = '- Inicio: ' . userdate($meta['inicio'] ?? time(), '%d/%m/%Y %H:%M:%S');
        $md[] = '- Estado: **' . ($meta['estado'] ?? '') . '**';
        if (!empty($meta['mensaje'])) {
            $md[] = '- ' . $meta['mensaje'];
        }
        $md[] = '- Fichero SIGAD: ' . ($plan->stats['sigad_fecha'] ?? '—');
        $md[] = '';

        foreach (($meta['violaciones'] ?? []) as $v) {
            $md[] = '> ⚠️ ' . $v;
        }
        if (!empty($meta['violaciones'])) {
            $md[] = '';
        }

        $md[] = '## Resumen';
        $md[] = '';
        $md[] = '| Concepto | Plan | Aplicadas | Errores |';
        $md[] = '|---|---:|---:|---:|';
        foreach (plan::ACTIONS as $type) {
            $md[] = '| ' . self::TITLES[$type] . ' | ' . $plan->count($type) . ' | ' .
                ($result ? ($result->done[$type] ?? 0) : '—') . ' | ' . ($result ? ($result->failed[$type] ?? 0) : '—') . ' |';
        }
        foreach (plan::NOTICES as $type) {
            if ($plan->count($type)) {
                $md[] = '| ' . self::TITLES[$type] . ' | ' . $plan->count($type) . ' | | |';
            }
        }
        $md[] = '';
        $md[] = '| Datos | Valor |';
        $md[] = '|---|---:|';
        foreach (
            [
            'sigad_students' => 'Alumnos en SIGAD',
            'sigad_modules' => 'Matrículas en SIGAD',
            'moodle_users_in_scope' => 'Usuarios gestionados en Moodle',
            'moodle_active_enrolments' => 'Matrículas activas en cursos gestionados',
            'matched_users' => 'Alumnos emparejados',
            ] as $key => $label
        ) {
            $md[] = "| {$label} | " . ($plan->stats[$key] ?? 0) . ' |';
        }
        if ($emails) {
            $md[] = '| Emails enviados / fallidos / omitidos por límite | ' .
                ($emails['sent'] ?? 0) . ' / ' . ($emails['failed'] ?? 0) . ' / ' . ($emails['skipped'] ?? 0) . ' |';
        }
        $md[] = '';

        if ($result && $result->errors) {
            $md[] = '## Errores';
            $md[] = '';
            foreach ($result->errors as $e) {
                $md[] = '- [' . $e['type'] . '] ' . $e['username'] . ': ' . self::inline($e['message']);
            }
            $md[] = '';
        }

        foreach (array_merge(plan::NOTICES, plan::ACTIONS) as $type) {
            $ops = $plan->get($type);
            if (!$ops) {
                continue;
            }
            $md[] = '## ' . self::TITLES[$type] . ' (' . count($ops) . ')';
            $md[] = '';
            foreach ($ops as $op) {
                $md[] = '- ' . self::describe($type, $op);
            }
            $md[] = '';
        }
        return implode("\n", $md);
    }

    /**
     * Línea descriptiva de una operación.
     *
     * @param string $type
     * @param array $op
     * @return string
     */
    public static function describe(string $type, array $op): string {
        $user = $op['username'] ?? '';
        switch ($type) {
            case plan::CREATE_USER:
                return "{$user}: {$op['firstname']} {$op['lastname']} <{$op['email']}>";
            case plan::RENAME_USER:
                return "{$op['oldusername']} → {$user}";
            case plan::UPDATE_PROFILE:
                $changes = [];
                foreach ($op['fields'] as $field => $value) {
                    $changes[] = "{$field}: '" . ($op['old'][$field] ?? '') . "' → '{$value}'";
                }
                return "{$user}: " . implode(', ', $changes);
            case plan::UPDATE_NAME:
                return "{$user}: '{$op['oldfirstname']} {$op['oldlastname']}' → '{$op['firstname']} {$op['lastname']}'";
            case plan::ADD_COHORT:
            case plan::REMOVE_COHORT:
                return "{$user}: {$op['cohort']}";
            case plan::ENROL:
            case plan::REACTIVATE_ENROL:
            case plan::SUSPEND_ENROL:
            case plan::UNENROL:
                return "{$user}: {$op['shortname']}" . (isset($op['motivo']) ? " ({$op['motivo']})" : '');
            case plan::SUSPEND_USER:
                return "{$user}: {$op['firstname']} {$op['lastname']}";
            case plan::MISSING_COURSE:
            case plan::MISSING_COHORT:
                return $op['nombre'] . ($op['detalle'] !== '' ? " ({$op['detalle']})" : '');
            case plan::DISCARDED:
                return $op['motivo'];
            default:
                return trim("{$user}: " . ($op['motivo'] ?? ''), ': ');
        }
    }

    /**
     * CSV de altas para Google Workspace (formato de carga masiva de usuarios).
     *
     * @param array[] $created credenciales de {@see result::$created}
     * @return string
     */
    public static function google_csv(array $created): string {
        $rows = [[
            'First Name [Required]', 'Last Name [Required]', 'Email Address [Required]', 'Password [Required]',
            'Password Hash Function [UPLOAD ONLY]', 'Org Unit Path [Required]', 'New Primary Email [UPLOAD ONLY]',
            'Recovery Email', 'Work Secondary Email', 'New Status [UPLOAD ONLY]',
        ]];
        foreach ($created as $c) {
            $rows[] = [$c['firstname'], $c['lastname'], $c['email'], $c['password'], '', '/Alumnado', '',
                $c['emailsigad'], $c['emailsigad'], 'Active'];
        }
        $fh = fopen('php://temp', 'r+');
        foreach ($rows as $row) {
            fputcsv($fh, $row, ',', '"', '\\');
        }
        rewind($fh);
        $csv = stream_get_contents($fh);
        fclose($fh);
        return $csv;
    }

    /**
     * Texto en una línea.
     *
     * @param string $text
     * @return string
     */
    protected static function inline(string $text): string {
        return trim(preg_replace('/\s+/', ' ', strip_tags($text)));
    }
}
