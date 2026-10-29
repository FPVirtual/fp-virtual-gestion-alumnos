<?php
// Proveedor de privacidad del plugin.

namespace local_fpvirtual_gestion_alumnado\privacy;

defined('MOODLE_INTERNAL') || die();

/**
 * El plugin no almacena datos personales de usuarios de Moodle:
 * la tabla de ejecuciones guarda metadatos del proceso (fechas,
 * modos, códigos de salida) y los logs son salida del proceso Python.
 */
class provider implements \core_privacy\local\metadata\null_provider {

    public static function get_reason(): string {
        return 'privacy:metadata:reason';
    }
}
