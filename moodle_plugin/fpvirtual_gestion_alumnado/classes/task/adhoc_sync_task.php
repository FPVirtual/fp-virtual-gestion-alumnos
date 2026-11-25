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
 * Ejecuta el proceso solicitado manualmente desde la página de lanzamiento.
 *
 * Se encola como tarea adhoc para no bloquear la petición HTTP con la
 * duración real del proceso.
 *
 * @package    local_fpvirtual_gestion_alumnado
 * @copyright  2026 FP virtual Aragón
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class adhoc_sync_task extends \core\task\adhoc_task {
    /**
     * Ejecuta la tarea.
     */
    public function execute(): void {
        $data = $this->get_custom_data();
        $modo = in_array($data->modo ?? 'dry', runner::MODOS, true) ? $data->modo : 'dry';

        $exitcode = runner::ejecutar($modo, 'manual');

        mtrace('fpvirtual_gestion_alumnado: lanzamiento manual finalizado con código ' . $exitcode . ' (modo ' . $modo . ').');
    }
}
