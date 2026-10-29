<?php
// Tareas programadas del plugin.

defined('MOODLE_INTERNAL') || die();

$tasks = [
    [
        'classname' => 'local_fpvirtual_gestion_alumnado\\task\\sync_task',
        'blocking' => 0,
        'minute' => '0',
        'hour' => '4',
        'day' => '*',
        'month' => '*',
        'dayofweek' => '*',
    ],
    [
        'classname' => 'local_fpvirtual_gestion_alumnado\\task\\cleanup_task',
        'blocking' => 0,
        'minute' => '30',
        'hour' => '5',
        'day' => '*',
        'month' => '*',
        'dayofweek' => '*',
    ],
];
