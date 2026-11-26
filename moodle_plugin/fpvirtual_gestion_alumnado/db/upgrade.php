<?php
// This file is part of Moodle - https://moodle.org/
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
// along with Moodle.  If not, see <https://www.gnu.org/licenses/>.

/**
 * Actualizaciones del plugin.
 *
 * @package    local_fpvirtual_gestion_alumnado
 * @copyright  2026 FP virtual Aragón
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

/**
 * Ejecuta las actualizaciones pendientes.
 *
 * @param int $oldversion
 * @return bool
 */
function xmldb_local_fpvirtual_gestion_alumnado_upgrade($oldversion) {
    if ($oldversion < 2026112600) {
        // Shortnames de los campos de perfil configurables (antes fijos en el código
        // con nombres que no existen en producción: IdSIGAD, emailsigad...).
        $component = 'local_fpvirtual_gestion_alumnado';
        $defaults = \local_fpvirtual_gestion_alumnado\config::DEFAULTS;
        foreach (array_keys(\local_fpvirtual_gestion_alumnado\config::PROFILE_FIELDS) as $field) {
            if (get_config($component, "field_{$field}") === false) {
                set_config("field_{$field}", $defaults["field_{$field}"], $component);
            }
        }
        upgrade_plugin_savepoint(true, 2026112600, 'local', 'fpvirtual_gestion_alumnado');
    }

    return true;
}
