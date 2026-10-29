<?php
// Tarea programada (cron) que lanza el proceso de gestión de alumnado.

namespace local_fpvirtual_gestion_alumnado\task;

defined('MOODLE_INTERNAL') || die();

use local_fpvirtual_gestion_alumnado\runner;

/**
 * Ejecución programada vía cron de Moodle.
 *
 * El horario concreto (hora, frecuencia) se ajusta desde
 * Administración del sitio > Tareas programadas.
 */
class sync_task extends \core\task\scheduled_task {

    public function get_name(): string {
        return get_string('task:sync', 'local_fpvirtual_gestion_alumnado');
    }

    public function execute(): void {
        if (!get_config('local_fpvirtual_gestion_alumnado', 'enabled')) {
            mtrace('fpvirtual_gestion_alumnado: ejecución por cron deshabilitada en la configuración.');
            return;
        }

        $modo = (string)get_config('local_fpvirtual_gestion_alumnado', 'launchmode') ?: 'dry';
        $exitcode = runner::ejecutar($modo, 'cron');

        mtrace('fpvirtual_gestion_alumnado: ejecución finalizada con código ' . $exitcode . ' (modo ' . $modo . ').');
    }

    public function get_run_if_component_disabled(): bool {
        return true;
    }
}
