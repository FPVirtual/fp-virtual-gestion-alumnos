<?php
// Language strings for FP Virtual Gestión Alumnado (English).

$string['pluginname'] = 'FP Virtual: gestión de alumnado';
$string['privacy:metadata:reason'] = 'This plugin does not store personal data of Moodle users. The runs table stores process metadata (times, modes, exit codes) and the logs are the output of the external management process.';

$string['task:sync'] = 'Run student management process';
$string['task:cleanup'] = 'Purge old student management logs';

$string['setting:enabled'] = 'Enable scheduled run';
$string['setting:enabled_desc'] = 'If enabled, the scheduled task runs the process in the configured mode. Manual launch is always available regardless of this setting.';
$string['setting:launchmode'] = 'Run mode';
$string['setting:launchmode_desc'] = 'Mode used by scheduled and default manual runs: dry-run only analyses; apply writes changes to Moodle.';
$string['setting:command'] = 'Process command';
$string['setting:command_desc'] = 'Full command that runs the management package (zipapp), e.g. python3 /opt/gestion_alumnos.pyz. The plugin appends "sync" and, if applicable, "--apply".';
$string['setting:extraenv'] = 'Extra environment variables';
$string['setting:extraenv_desc'] = 'One VAR=value per line, added to the process environment.';
$string['setting:timeout'] = 'Timeout (seconds)';
$string['setting:timeout_desc'] = 'Maximum execution time before the process is killed.';
$string['setting:retentiondays'] = 'Log retention (days)';
$string['setting:retentiondays_desc'] = 'Executions and logs older than this are purged daily.';

$string['mode:dry'] = 'Dry-run (analysis only)';
$string['mode:apply'] = 'Apply (writes changes)';

$string['menu:status'] = 'Student management: status';
$string['menu:logs'] = 'Student management: logs';
$string['menu:launch'] = 'Student management: run now';

$string['msg:queued'] = 'Execution queued (mode {$a}). Check the status page for progress and result.';

$string['launch:heading'] = 'Run the student management process';
$string['launch:intro'] = 'Launch the management package from here to verify its operation (dry-run) or apply changes, without using the command line. The execution runs in the background and its result is recorded in the history.';
$string['launch:dry_desc'] = 'Analyses and reports what would change, without writing anything to Moodle. Use it to verify the configuration.';
$string['launch:apply_desc'] = 'Applies the detected changes (user creation, enrolments, emails). Check a dry-run first.';
$string['launch:button_dry'] = 'Run dry-run now';
$string['launch:button_apply'] = 'Run with apply now';
$string['launch:confirm_apply'] = 'This will apply changes to Moodle. Are you sure?';
$string['launch:currentmode'] = 'Default scheduled mode: {$a}';

$string['status:heading'] = 'Process status';
$string['status:config'] = 'Configuration';
$string['status:cron'] = 'Scheduled task (cron)';
$string['status:cron_disabled'] = 'Task disabled';
$string['status:cron_nextrun'] = 'Next run';
$string['status:cron_lastrun'] = 'Last run (cron)';
$string['status:cron_hint'] = 'The schedule (time and frequency) is adjusted in Site administration > Server > Scheduled tasks.';
$string['status:cron_missing'] = 'Scheduled task not found. Check the plugin installation.';
$string['status:lastrun'] = 'Last execution';
$string['status:noruns'] = 'No executions recorded yet.';
$string['status:success'] = 'Success';
$string['status:error'] = 'Error';
$string['status:running'] = 'Running';
$string['status:field_origen'] = 'Origin';
$string['status:field_start'] = 'Started';
$string['status:field_duration'] = 'Duration';
$string['status:field_result'] = 'Result';
$string['status:field_exitcode'] = 'Exit code';
$string['status:summary'] = 'Summary';
$string['status:viewlog'] = 'View full log';

$string['origen:manual'] = 'Manual';
$string['origen:cron'] = 'Cron';

$string['logs:history'] = 'Execution history';
$string['logs:detail'] = 'Execution #{$a}';
$string['logs:empty'] = 'This execution has no stored log.';
$string['logs:download'] = 'Download log';
$string['logs:back'] = 'Back to history';
$string['logs:view'] = 'View';

$string['error:nocommand'] = 'The process command is not configured. Set it in the plugin settings.';
$string['error:nolog'] = 'Log file not found for this execution.';
