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

use local_fpvirtual_gestion_alumnado\runner;

/**
 * Ejecución programada vía cron de Moodle.
 *
 * El horario concreto (hora, frecuencia) se ajusta desde
 * Administración del sitio > Tareas programadas.
 *
 * @package    local_fpvirtual_gestion_alumnado
 * @copyright  2026 FP virtual Aragón
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class sync_task extends \core\task\scheduled_task {
    /**
     * Nombre de la tarea.
     *
     * @return string
     */
    public function get_name(): string {
        return get_string('task:sync', 'local_fpvirtual_gestion_alumnado');
    }

    /**
     * Ejecuta la tarea.
     */
    public function execute(): void {
        if (!get_config('local_fpvirtual_gestion_alumnado', 'enabled')) {
            mtrace('fpvirtual_gestion_alumnado: ejecución por cron deshabilitada en la configuración.');
            return;
        }

        $modo = (string)get_config('local_fpvirtual_gestion_alumnado', 'launchmode') ?: 'dry';
        $exitcode = runner::ejecutar($modo, 'cron');

        mtrace('fpvirtual_gestion_alumnado: ejecución finalizada con código ' . $exitcode . ' (modo ' . $modo . ').');
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
