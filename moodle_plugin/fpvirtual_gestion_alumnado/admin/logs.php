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
// along with Moodle.  If not, see <https://www.gnu.org/licenses/>.

/**
 * Página de historial de ejecuciones y visualización/descarga de logs.
 *
 * @package    local_fpvirtual_gestion_alumnado
 * @copyright  2026 FP virtual Aragón
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

require_once(__DIR__ . '/../../../config.php');
require_once($CFG->libdir . '/filelib.php');

$component = 'local_fpvirtual_gestion_alumnado';

require_login();
$context = context_system::instance();
require_capability('local/fpvirtual_gestion_alumnado:viewstatus', $context);

$runid = optional_param('runid', 0, PARAM_INT);
$page = optional_param('page', 0, PARAM_INT);
$download = optional_param('download', 0, PARAM_BOOL);
$file = optional_param('file', 'log', PARAM_ALPHA);
$runstore = \local_fpvirtual_gestion_alumnado\run_store::class;

$PAGE->set_context($context);
$PAGE->set_url(new moodle_url('/local/fpvirtual_gestion_alumnado/admin/logs.php'));
$PAGE->set_title(get_string('menu:logs', $component));
$PAGE->set_heading(get_string('menu:logs', $component));

// Descarga del log de una ejecución.
if ($runid && $download) {
    $run = $runstore::get($runid);
    $artifact = $runstore::ARTIFACTS[$file] ?? null;
    if ($artifact && $artifact[2]) {
        require_capability('local/fpvirtual_gestion_alumnado:launch', $context);
    }
    $path = $run ? $runstore::artifact($run, $file) : null;
    if (!$path) {
        throw new moodle_exception('error:nolog', $component);
    }
    send_file($path, 'run_' . $runid . '_' . $artifact[0], 0, 0, false, true, $artifact[1]);
}

echo $OUTPUT->header();

// Detalle de una ejecución.
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
        [
            get_string('status:field_result', $component),
            \local_fpvirtual_gestion_alumnado\output\helper::status_badge($run->status),
        ],
    ];
    echo html_writer::table($meta);

    echo \local_fpvirtual_gestion_alumnado\output\helper::summary($run);

    // Ficheros descargables.
    echo $OUTPUT->heading(get_string('logs:artifacts', $component), 4);
    $links = [];
    foreach ($runstore::ARTIFACTS as $key => [$filename, $mime, $restricted]) {
        if ($restricted && !has_capability('local/fpvirtual_gestion_alumnado:launch', $context)) {
            continue;
        }
        if ($runstore::artifact($run, $key)) {
            $url = new moodle_url($PAGE->url, ['runid' => $runid, 'download' => 1, 'file' => $key]);
            $links[] = html_writer::link($url, get_string('artifact:' . $key, $component));
        }
    }
    echo html_writer::alist($links);

    // Informe renderizado.
    $reportfile = $runstore::artifact($run, 'report');
    if ($reportfile) {
        echo html_writer::div(
            format_text(file_get_contents($reportfile), FORMAT_MARKDOWN, ['context' => $context]),
            'border rounded p-3 mb-3',
            ['style' => 'max-height: 70vh; overflow: auto;']
        );
    }

    $contenido = $runstore::read_log($run);
    if ($contenido === '') {
        echo html_writer::tag('p', get_string('logs:empty', $component));
    } else {
        echo html_writer::tag('details', html_writer::tag('summary', get_string('artifact:log', $component))
            . html_writer::tag('pre', s($contenido), ['style' => 'max-height: 60vh; overflow: auto;']));
    }

    echo html_writer::div(html_writer::link(new moodle_url($PAGE->url), get_string('logs:back', $component)), 'mt-2');

    echo $OUTPUT->footer();
    exit;
}

// Historial paginado.
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
            \local_fpvirtual_gestion_alumnado\output\helper::status_badge($run->status),
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
