<?php
// Funciones webservice del plugin.

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
