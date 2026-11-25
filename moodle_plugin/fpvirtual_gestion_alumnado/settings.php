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
 * Ajustes del plugin y entradas en el árbol de administración.
 *
 * Los valores por defecto viven en \local_fpvirtual_gestion_alumnado\config::DEFAULTS.
 *
 * @package    local_fpvirtual_gestion_alumnado
 * @copyright  2026 FP virtual Aragón
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

defined('MOODLE_INTERNAL') || die();

if ($hassiteconfig) {
    $component = 'local_fpvirtual_gestion_alumnado';
    $d = \local_fpvirtual_gestion_alumnado\config::DEFAULTS;
    $str = fn(string $id) => get_string($id, $component);

    // Atajos para declarar ajustes con su cadena y descripción.
    $text = function (string $name, string $param = PARAM_RAW_TRIMMED, int $size = 30) use ($component, $d, $str) {
        return new admin_setting_configtext(
            "{$component}/{$name}",
            $str("setting:{$name}"),
            $str("setting:{$name}_desc"),
            $d[$name],
            $param,
            $size
        );
    };
    $check = function (string $name) use ($component, $d, $str) {
        return new admin_setting_configcheckbox(
            "{$component}/{$name}",
            $str("setting:{$name}"),
            $str("setting:{$name}_desc"),
            $d[$name]
        );
    };
    $heading = fn(string $id) => new admin_setting_heading(
        "{$component}/heading_{$id}",
        $str("heading:{$id}"),
        $str("heading:{$id}_desc")
    );

    $settings = new admin_settingpage($component, $str('pluginname'));

    // Ejecución.
    $settings->add($heading('run'));
    $settings->add($check('enabled'));
    $settings->add(new admin_setting_configselect(
        "{$component}/launchmode",
        $str('setting:launchmode'),
        $str('setting:launchmode_desc'),
        $d['launchmode'],
        ['dry' => $str('mode:dry'), 'apply' => $str('mode:apply')]
    ));
    $settings->add(new admin_setting_configselect(
        "{$component}/engine",
        $str('setting:engine'),
        $str('setting:engine_desc'),
        $d['engine'],
        ['php' => $str('engine:php'), 'external' => $str('engine:external')]
    ));
    $settings->add($text('retentiondays', PARAM_INT, 5));

    // SIGAD.
    $settings->add($heading('sigad'));
    $settings->add($text('sigad_baseurl', PARAM_URL, 70));
    $settings->add($text('sigad_user'));
    $settings->add(new admin_setting_encryptedpassword(
        "{$component}/sigad_password",
        $str('setting:sigad_password'),
        $str('setting:sigad_password_desc')
    ));
    $settings->add($text('sigad_timeout', PARAM_INT, 5));
    $settings->add($text('sigad_initialwait', PARAM_INT, 5));
    $settings->add($text('sigad_maxretries', PARAM_INT, 5));
    $settings->add($text('sigad_retrydelay', PARAM_INT, 5));

    // Reglas.
    $settings->add($heading('rules'));
    $settings->add($text('emaildomain'));
    $settings->add($text('excludedprefixes'));
    $settings->add(new admin_setting_configtextarea(
        "{$component}/protectedusers",
        $str('setting:protectedusers'),
        $str('setting:protectedusers_desc'),
        $d['protectedusers'],
        PARAM_RAW_TRIMMED
    ));
    $settings->add($text('excludedcourses'));
    $settings->add($text('cohortalumnado'));
    $settings->add($check('syncnames'));
    $settings->add($check('cleanupenabled'));
    $settings->add($text('cleanupmonth', PARAM_INT, 3));

    // Guardas.
    $settings->add($heading('guards'));
    $settings->add($text('maxusersuspensions', PARAM_INT, 6));
    $settings->add($text('maxenrolsuspendpercent', PARAM_INT, 4));

    // Notificaciones.
    $settings->add($heading('notify'));
    $settings->add($check('notifyenabled'));
    $settings->add($text('notifyredirect', PARAM_RAW_TRIMMED, 40));
    $settings->add($text('dailyemaillimit', PARAM_INT, 6));
    $settings->add($text('emailpause', PARAM_INT, 4));
    $settings->add(new admin_setting_configtextarea(
        "{$component}/reportto",
        $str('setting:reportto'),
        $str('setting:reportto_desc'),
        $d['reportto'],
        PARAM_RAW_TRIMMED
    ));
    $settings->add($text('helpcourseid', PARAM_INT, 6));
    $settings->add($text('supporturl', PARAM_URL, 60));

    // Motor externo (transición).
    $settings->add($heading('external'));
    $settings->add($text('command', PARAM_RAW, 70));
    $settings->add(new admin_setting_configtextarea(
        "{$component}/extraenv",
        $str('setting:extraenv'),
        $str('setting:extraenv_desc'),
        $d['extraenv']
    ));
    $settings->add($text('timeout', PARAM_INT, 6));

    $ADMIN->add('localplugins', $settings);

    foreach (['status' => 'viewstatus', 'logs' => 'viewstatus', 'launch' => 'launch'] as $page => $cap) {
        $ADMIN->add('localplugins', new admin_externalpage(
            "{$component}_{$page}",
            $str("menu:{$page}"),
            new moodle_url("/local/fpvirtual_gestion_alumnado/admin/{$page}.php"),
            "local/fpvirtual_gestion_alumnado:{$cap}"
        ));
    }
}
