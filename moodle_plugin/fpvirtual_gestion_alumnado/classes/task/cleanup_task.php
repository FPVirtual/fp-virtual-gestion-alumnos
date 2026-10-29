<?php
// Tarea programada de limpieza de logs e historial antiguos.

namespace local_fpvirtual_gestion_alumnado\task;

defined('MOODLE_INTERNAL') || die();

use local_fpvirtual_gestion_alumnado\run_store;

/**
 * Purga periódicamente las ejecuciones y logs más antiguos que la
 * retención configurada (retentiondays).
 */
class cleanup_task extends \core\task\scheduled_task {

    public function get_name(): string {
        return get_string('task:cleanup', 'local_fpvirtual_gestion_alumnado');
    }

    public function execute(): void {
        $days = (int)get_config('local_fpvirtual_gestion_alumnado', 'retentiondays');
        $days = $days > 0 ? $days : 30;

        $eliminados = run_store::purge(time() - $days * DAYSECS);
        mtrace('fpvirtual_gestion_alumnado: purgadas ' . $eliminados . ' ejecuciones antiguas (> ' . $days . ' días).');
    }

    public function get_run_if_component_disabled(): bool {
        return true;
    }
}
