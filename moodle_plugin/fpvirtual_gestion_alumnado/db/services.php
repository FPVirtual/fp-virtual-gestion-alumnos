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

/**
 * Funciones webservice del plugin.
 *
 * @package    local_fpvirtual_gestion_alumnado
 * @copyright  2026 FP virtual Aragón
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

defined('MOODLE_INTERNAL') || die();

$functions = [
    'local_fpvirtual_gestion_alumnado_get_snapshot' => [
        'classname' => 'local_fpvirtual_gestion_alumnado\\external\\get_snapshot',
        'methodname' => 'execute',
        'description' => 'Devuelve en una sola llamada un snapshot completo de usuarios '
            . '(con los campos personalizados de SIGAD) y matriculaciones de Moodle.',
        'type' => 'read',
        'ajax' => false,
    ],
];
