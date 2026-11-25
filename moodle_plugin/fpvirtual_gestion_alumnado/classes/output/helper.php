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

namespace local_fpvirtual_gestion_alumnado\output;

use html_table;
use html_writer;
use local_fpvirtual_gestion_alumnado\run_store;
use local_fpvirtual_gestion_alumnado\sync\plan;
use local_fpvirtual_gestion_alumnado\sync\report;

/**
 * Fragmentos HTML comunes de las páginas de administración.
 *
 * @package    local_fpvirtual_gestion_alumnado
 * @copyright  2026 FP virtual Aragón
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class helper {
    /**
     * Distintivo de estado de una ejecución.
     *
     * Incluye clases de Bootstrap 4 (badge-*) y 5 (text-bg-*) para Moodle 4.x y 5.x.
     *
     * @param string $status
     * @return string
     */
    public static function status_badge(string $status): string {
        $classes = [
            run_store::STATUS_SUCCESS => 'success',
            run_store::STATUS_ERROR => 'danger',
            run_store::STATUS_ABORTED => 'warning',
            run_store::STATUS_RUNNING => 'info',
        ];
        $variant = $classes[$status] ?? 'secondary';
        $sm = get_string_manager();
        $text = $sm->string_exists('status:' . $status, 'local_fpvirtual_gestion_alumnado')
            ? get_string('status:' . $status, 'local_fpvirtual_gestion_alumnado') : s($status);
        return html_writer::span($text, "badge badge-{$variant} text-bg-{$variant}");
    }

    /**
     * Resumen de una ejecución (plan, resultado y avisos) a partir de su campo summary.
     *
     * @param \stdClass $run
     * @return string
     */
    public static function summary(\stdClass $run): string {
        global $OUTPUT;

        $summary = $run->summary ? json_decode($run->summary, true) : null;
        if (!is_array($summary)) {
            return '';
        }
        $out = $OUTPUT->heading(get_string('status:summary', 'local_fpvirtual_gestion_alumnado'), 4);

        if (!empty($summary['mensaje'])) {
            $out .= $OUTPUT->notification(s($summary['mensaje']), 'warning', false);
        }
        foreach (($summary['violaciones'] ?? []) as $v) {
            $out .= $OUTPUT->notification(s($v), 'warning', false);
        }
        if (!isset($summary['plan'])) {
            // Ejecución del motor externo: resumen libre.
            return $out . html_writer::tag('pre', s(json_encode($summary, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE)));
        }

        $done = $summary['resultado']['done'] ?? null;
        $failed = $summary['resultado']['failed'] ?? [];
        $table = new html_table();
        $table->attributes['class'] = 'generaltable';
        $table->head = ['', get_string('logs:plan', 'local_fpvirtual_gestion_alumnado'), '✔', '✘'];
        foreach (array_merge(plan::ACTIONS, plan::NOTICES) as $type) {
            $count = $summary['plan'][$type] ?? 0;
            if (!$count) {
                continue;
            }
            $isaction = in_array($type, plan::ACTIONS, true);
            $table->data[] = [
                report::TITLES[$type],
                $count,
                $isaction && $done !== null ? ($done[$type] ?? 0) : '',
                $isaction && $done !== null ? ($failed[$type] ?? 0) : '',
            ];
        }
        if (!$table->data) {
            $table->data[] = [get_string('none'), '', '', ''];
        }
        $out .= html_writer::table($table);

        $emails = $summary['emails'] ?? [];
        if (array_sum($emails)) {
            $out .= html_writer::tag('p', 'Emails: ' . (int)($emails['sent'] ?? 0) . ' ✔ / ' .
                (int)($emails['failed'] ?? 0) . ' ✘ / ' . (int)($emails['skipped'] ?? 0) . ' ⏸', ['class' => 'text-muted']);
        }
        return $out;
    }
}
