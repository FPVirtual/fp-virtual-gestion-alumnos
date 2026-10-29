<?php
// Página de historial de ejecuciones y visualización/descarga de logs.

require_once(__DIR__ . '/../../../config.php');

$component = 'local_fpvirtual_gestion_alumnado';

require_login();
$context = context_system::instance();
require_capability($component . ':viewstatus', $context);

$runid = optional_param('runid', 0, PARAM_INT);
$page = optional_param('page', 0, PARAM_INT);
$download = optional_param('download', 0, PARAM_BOOL);

$PAGE->set_context($context);
$PAGE->set_url(new moodle_url('/local/fpvirtual_gestion_alumnado/admin/logs.php'));
$PAGE->set_title(get_string('menu:logs', $component));
$PAGE->set_heading(get_string('menu:logs', $component));

// --- Descarga del log de una ejecución.
if ($runid && $download) {
    $run = \local_fpvirtual_gestion_alumnado\run_store::get($runid);
    if (!$run || empty($run->logfile) || !is_file($run->logfile)) {
        throw new moodle_exception('error:nolog', $component);
    }
    send_file($run->logfile, 'run_' . $runid . '.log', true);
}

echo $OUTPUT->header();

// --- Detalle de una ejecución.
if ($runid) {
    $run = \local_fpvirtual_gestion_alumnado\run_store::get($runid);
    if (!$run) {
        throw new moodle_exception('invalidrecord', 'error');
    }

    echo $OUTPUT->heading(get_string('logs:detail', $component, $runid), 3);
    $meta = new html_table();
    $meta->attributes['class'] = 'generaltable';
    $meta->data = [
        [get_string('status:field_start', $component), userdate($run->timestart)],
        [get_string('status:field_origen', $component), get_string('origen:' . $run->origen, $component)],
        [get_string('setting:launchmode', $component), get_string('mode:' . $run->modo, $component)],
        [get_string('status:field_result', $component), $run->status],
    ];
    echo html_writer::table($meta);

    $contenido = \local_fpvirtual_gestion_alumnado\run_store::read_log($run);
    if ($contenido === '') {
        echo html_writer::tag('p', get_string('logs:empty', $component));
    } else {
        echo html_writer::tag('pre', s($contenido), ['style' => 'max-height: 60vh; overflow: auto;']);
    }

    $downloadurl = new moodle_url($PAGE->url, ['runid' => $runid, 'download' => 1]);
    $listurl = new moodle_url($PAGE->url);
    echo html_writer::div(
        html_writer::link($downloadurl, get_string('logs:download', $component))
        . ' | ' . html_writer::link($listurl, get_string('logs:back', $component)),
        'mt-2'
    );

    echo $OUTPUT->footer();
    exit;
}

// --- Historial paginado.
echo $OUTPUT->heading(get_string('logs:history', $component), 3);

$perpage = 50;
$total = \local_fpvirtual_gestion_alumnado\run_store::count();
$runs = \local_fpvirtual_gestion_alumnado\run_store::recent($perpage, $page * $perpage);

if (!$runs) {
    echo html_writer::tag('p', get_string('status:noruns', $component));
} else {
    $table = new html_table();
    $table->attributes['class'] = 'generaltable';
    $table->head = [
        'ID',
        get_string('status:field_start', $component),
        get_string('status:field_origen', $component),
        get_string('setting:launchmode', $component),
        get_string('status:field_result', $component),
        get_string('status:field_duration', $component),
        '',
    ];
    foreach ($runs as $run) {
        $detailurl = new moodle_url($PAGE->url, ['runid' => $run->id]);
        $duracion = $run->timeend ? format_time($run->timeend - $run->timestart) : '—';
        $table->data[] = [
            $run->id,
            userdate($run->timestart),
            get_string('origen:' . $run->origen, $component),
            get_string('mode:' . $run->modo, $component),
            $run->status,
            $duracion,
            html_writer::link($detailurl, get_string('logs:view', $component)),
        ];
    }
    echo html_writer::table($table);
    echo $OUTPUT->paging_bar($total, $page, $perpage, $PAGE->url);
}

$statusurl = new moodle_url('/local/fpvirtual_gestion_alumnado/admin/status.php');
echo html_writer::div(html_writer::link($statusurl, get_string('menu:status', $component)), 'mt-3');

echo $OUTPUT->footer();
