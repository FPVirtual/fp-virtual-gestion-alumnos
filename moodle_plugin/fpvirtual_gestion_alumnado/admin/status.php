<?php
// Página de estado: última ejecución, configuración y próxima ejecución cron.

require_once(__DIR__ . '/../../../config.php');

$component = 'local_fpvirtual_gestion_alumnado';

require_login();
$context = context_system::instance();
require_capability($component . ':viewstatus', $context);

$PAGE->set_context($context);
$PAGE->set_url(new moodle_url('/local/fpvirtual_gestion_alumnado/admin/status.php'));
$PAGE->set_title(get_string('menu:status', $component));
$PAGE->set_heading(get_string('menu:status', $component));

echo $OUTPUT->header();
echo $OUTPUT->heading(get_string('status:heading', $component));

// --- Configuración relevante.
$configtable = new html_table();
$configtable->attributes['class'] = 'generaltable';
$configtable->data = [
    [get_string('setting:enabled', $component), get_config($component, 'enabled') ? get_string('yes') : get_string('no')],
    [get_string('setting:launchmode', $component), get_string('mode:' . ((string)get_config($component, 'launchmode') ?: 'dry'), $component)],
    [get_string('setting:command', $component), s((string)get_config($component, 'command'))],
    [get_string('setting:timeout', $component), (int)get_config($component, 'timeout') . ' s'],
];

echo $OUTPUT->heading(get_string('status:config', $component), 3);
echo html_writer::table($configtable);

// --- Tarea programada: estado y próxima ejecución.
echo $OUTPUT->heading(get_string('status:cron', $component), 3);
$synctask = \core\task\manager::get_scheduled_task($component . '\task\sync_task');
if ($synctask) {
    $crontable = new html_table();
    $crontable->attributes['class'] = 'generaltable';
    $nextrun = $synctask->get_next_run_time();
    $crontable->data = [
        [get_string('status:cron_disabled', $component), $synctask->get_disabled() ? get_string('yes') : get_string('no')],
        [get_string('status:cron_nextrun', $component), $nextrun ? userdate($nextrun) : '—'],
        [get_string('status:cron_lastrun', $component), $synctask->get_last_run_time() ? userdate($synctask->get_last_run_time()) : '—'],
    ];
    echo html_writer::table($crontable);
    echo html_writer::tag('p', get_string('status:cron_hint', $component), ['class' => 'text-muted']);
} else {
    echo $OUTPUT->notification(get_string('status:cron_missing', $component), \core\output\notification::NOTIFY_WARNING);
}

// --- Última ejecución registrada.
echo $OUTPUT->heading(get_string('status:lastrun', $component), 3);
$run = \local_fpvirtual_gestion_alumnado\run_store::latest();
if (!$run) {
    echo html_writer::tag('p', get_string('status:noruns', $component));
} else {
    $estados = [
        'success' => ['text' => get_string('status:success', $component), 'class' => 'badge badge-success'],
        'error' => ['text' => get_string('status:error', $component), 'class' => 'badge badge-danger'],
        'running' => ['text' => get_string('status:running', $component), 'class' => 'badge badge-warning'],
    ];
    $estado = $estados[$run->status] ?? $estados['running'];

    $runtable = new html_table();
    $runtable->attributes['class'] = 'generaltable';
    $duracion = $run->timeend ? format_time($run->timeend - $run->timestart) : '—';
    $runtable->data = [
        ['ID', $run->id],
        [get_string('status:field_origen', $component), get_string('origen:' . $run->origen, $component)],
        [get_string('setting:launchmode', $component), get_string('mode:' . $run->modo, $component)],
        [get_string('status:field_start', $component), userdate($run->timestart)],
        [get_string('status:field_duration', $component), $duracion],
        [get_string('status:field_result', $component), html_writer::span($estado['text'], $estado['class'])],
        [get_string('status:field_exitcode', $component), $run->exitcode === null ? '—' : $run->exitcode],
    ];
    echo html_writer::table($runtable);

    if (!empty($run->summary)) {
        $resumen = json_decode($run->summary);
        if ($resumen !== null) {
            echo $OUTPUT->heading(get_string('status:summary', $component), 4);
            echo html_writer::tag('pre', s(json_encode($resumen, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE)));
        }
    }

    $logurl = new moodle_url('/local/fpvirtual_gestion_alumnado/admin/logs.php', ['runid' => $run->id]);
    echo html_writer::div(html_writer::link($logurl, get_string('status:viewlog', $component)), 'mt-2');
}

// --- Enlaces.
$logsurl = new moodle_url('/local/fpvirtual_gestion_alumnado/admin/logs.php');
$launchurl = new moodle_url('/local/fpvirtual_gestion_alumnado/admin/launch.php');
$links = html_writer::link($logsurl, get_string('menu:logs', $component));
if (has_capability($component . ':launch', $context)) {
    $links .= ' | ' . html_writer::link($launchurl, get_string('menu:launch', $component));
}
echo html_writer::div($links, 'mt-3');

echo $OUTPUT->footer();
