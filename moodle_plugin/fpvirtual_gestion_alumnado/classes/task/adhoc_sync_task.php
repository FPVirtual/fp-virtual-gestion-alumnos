<?php
// Tarea adhoc para el lanzamiento manual desde el administrador.

namespace local_fpvirtual_gestion_alumnado\task;

defined('MOODLE_INTERNAL') || die();

use local_fpvirtual_gestion_alumnado\runner;

/**
 * Ejecuta el proceso solicitado manualmente desde la página de lanzamiento.
 *
 * Se encola como tarea adhoc para no bloquear la petición HTTP con la
 * duración real del proceso.
 */
class adhoc_sync_task extends \core\task\adhoc_task {

    public function execute(): void {
        $data = $this->get_custom_data();
        $modo = in_array($data->modo ?? 'dry', runner::MODOS, true) ? $data->modo : 'dry';

        $exitcode = runner::ejecutar($modo, 'manual');

        mtrace('fpvirtual_gestion_alumnado: lanzamiento manual finalizado con código ' . $exitcode . ' (modo ' . $modo . ').');
    }
}
