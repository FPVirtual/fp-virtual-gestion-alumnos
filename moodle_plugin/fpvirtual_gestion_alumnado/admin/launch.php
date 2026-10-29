<?php
// Página de lanzamiento manual del proceso (dry-run o apply).

require_once(__DIR__ . '/../../../config.php');

$component = 'local_fpvirtual_gestion_alumnado';

require_login();
$context = context_system::instance();
require_capability($component . ':launch', $context);

$PAGE->set_context($context);
$PAGE->set_url(new moodle_url('/local/fpvirtual_gestion_alumnado/admin/launch.php'));
$PAGE->set_title(get_string('menu:launch', $component));
$PAGE->set_heading(get_string('menu:launch', $component));

$statusurl = new moodle_url('/local/fpvirtual_gestion_alumnado/admin/status.php');

if (data_submitted() && confirm_sesskey()) {
    $modo = optional_param('modo', 'dry', PARAM_ALPHA);
    if (!in_array($modo, \local_fpvirtual_gestion_alumnado\runner::MODOS, true)) {
        $modo = 'dry';
    }

    $task = new \local_fpvirtual_gestion_alumnado\task\adhoc_sync_task();
    $task->set_custom_data((object)['modo' => $modo]);
    $task->set_component($component);
    \core\task\manager::queue_adhoc_task($task);

    redirect($statusurl, get_string('msg:queued', $component, $modo), null, \core\output\notification::NOTIFY_SUCCESS);
}

echo $OUTPUT->header();

$modoactual = (string)get_config($component, 'launchmode') ?: 'dry';
$comando = trim((string)get_config($component, 'command'));

echo $OUTPUT->heading(get_string('launch:heading', $component));
echo html_writer::tag('p', get_string('launch:intro', $component));

if ($comando === '') {
    echo $OUTPUT->notification(get_string('error:nocommand', $component), \core\output\notification::NOTIFY_WARNING);
}

// Botón dry-run.
echo html_writer::start_tag('form', ['method' => 'post', 'action' => $PAGE->url->out()]);
echo html_writer::empty_tag('input', ['type' => 'hidden', 'name' => 'sesskey', 'value' => sesskey()]);
echo html_writer::empty_tag('input', ['type' => 'hidden', 'name' => 'modo', 'value' => 'dry']);
echo html_writer::tag('p', html_writer::tag('strong', get_string('mode:dry', $component)) . ' — '
    . get_string('launch:dry_desc', $component));
echo html_writer::empty_tag('input', [
    'type' => 'submit',
    'value' => get_string('launch:button_dry', $component),
    'class' => 'btn btn-primary',
]);
echo html_writer::end_tag('form');

echo html_writer::empty_tag('hr');

// Botón apply (siempre disponible para verificación manual; confirmación del navegador).
echo html_writer::start_tag('form', [
    'method' => 'post',
    'action' => $PAGE->url->out(),
    'onsubmit' => 'return confirm("' . get_string('launch:confirm_apply', $component) . '");',
]);
echo html_writer::empty_tag('input', ['type' => 'hidden', 'name' => 'sesskey', 'value' => sesskey()]);
echo html_writer::empty_tag('input', ['type' => 'hidden', 'name' => 'modo', 'value' => 'apply']);
echo html_writer::tag('p', html_writer::tag('strong', get_string('mode:apply', $component)) . ' — '
    . get_string('launch:apply_desc', $component));
echo html_writer::empty_tag('input', [
    'type' => 'submit',
    'value' => get_string('launch:button_apply', $component),
    'class' => 'btn btn-danger',
]);
echo html_writer::end_tag('form');

echo html_writer::tag('p', get_string('launch:currentmode', $component, $modoactual), ['class' => 'text-muted']);

echo html_writer::div(html_writer::link($statusurl, get_string('menu:status', $component)), 'mt-3');

echo $OUTPUT->footer();
