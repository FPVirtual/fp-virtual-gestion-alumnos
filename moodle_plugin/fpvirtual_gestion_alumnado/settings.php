<?php
// Configuración del plugin y entradas en el árbol de administración.

defined('MOODLE_INTERNAL') || die();

if ($hassiteconfig) {
    $component = 'local_fpvirtual_gestion_alumnado';

    $settings = new admin_settingpage($component, get_string('pluginname', $component));

    $settings->add(new admin_setting_configcheckbox(
        $component . '/enabled',
        get_string('setting:enabled', $component),
        get_string('setting:enabled_desc', $component),
        0
    ));

    $settings->add(new admin_setting_configselect(
        $component . '/launchmode',
        get_string('setting:launchmode', $component),
        get_string('setting:launchmode_desc', $component),
        'dry',
        [
            'dry' => get_string('mode:dry', $component),
            'apply' => get_string('mode:apply', $component),
        ]
    ));

    $settings->add(new admin_setting_configtext(
        $component . '/command',
        get_string('setting:command', $component),
        get_string('setting:command_desc', $component),
        'python3 /opt/gestion_alumnos.pyz',
        PARAM_RAW,
        1333
    ));

    $settings->add(new admin_setting_configtextarea(
        $component . '/extraenv',
        get_string('setting:extraenv', $component),
        get_string('setting:extraenv_desc', $component),
        ''
    ));

    $settings->add(new admin_setting_configtext(
        $component . '/timeout',
        get_string('setting:timeout', $component),
        get_string('setting:timeout_desc', $component),
        600,
        PARAM_INT
    ));

    $settings->add(new admin_setting_configtext(
        $component . '/retentiondays',
        get_string('setting:retentiondays', $component),
        get_string('setting:retentiondays_desc', $component),
        30,
        PARAM_INT
    ));

    $ADMIN->add('localplugins', $settings);

    $ADMIN->add('localplugins', new admin_externalpage(
        $component . '_status',
        get_string('menu:status', $component),
        new moodle_url('/local/fpvirtual_gestion_alumnado/admin/status.php'),
        $component . ':viewstatus'
    ));

    $ADMIN->add('localplugins', new admin_externalpage(
        $component . '_logs',
        get_string('menu:logs', $component),
        new moodle_url('/local/fpvirtual_gestion_alumnado/admin/logs.php'),
        $component . ':viewstatus'
    ));

    $ADMIN->add('localplugins', new admin_externalpage(
        $component . '_launch',
        get_string('menu:launch', $component),
        new moodle_url('/local/fpvirtual_gestion_alumnado/admin/launch.php'),
        $component . ':launch'
    ));
}
