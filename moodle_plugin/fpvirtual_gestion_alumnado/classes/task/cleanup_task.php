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

namespace local_fpvirtual_gestion_alumnado\task;

use local_fpvirtual_gestion_alumnado\run_store;

/**
 * Purga periódicamente las ejecuciones y logs más antiguos que la
 * retención configurada (retentiondays).
 *
 * @package    local_fpvirtual_gestion_alumnado
 * @copyright  2026 FP virtual Aragón
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class cleanup_task extends \core\task\scheduled_task {
    /**
     * Nombre de la tarea.
     *
     * @return string
     */
    public function get_name(): string {
        return get_string('task:cleanup', 'local_fpvirtual_gestion_alumnado');
    }

    /**
     * Ejecuta la tarea.
     */
    public function execute(): void {
        $days = (int)get_config('local_fpvirtual_gestion_alumnado', 'retentiondays');
        $days = $days > 0 ? $days : 30;

        $eliminados = run_store::purge(time() - $days * DAYSECS);
        mtrace('fpvirtual_gestion_alumnado: purgadas ' . $eliminados . ' ejecuciones antiguas (> ' . $days . ' días).');
    }

    /**
     * Se ejecuta aunque el plugin esté deshabilitado.
     *
     * @return bool
     */
    public function get_run_if_component_disabled(): bool {
        return true;
    }
}
