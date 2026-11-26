<?php
// This file is part of Moodle - https://moodle.org/
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
//
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// GNU General Public License for more details.
//
// along with Moodle.  If not, see <http://www.gnu.org/licenses/>.

/**
 * Language strings (English).
 *
 * @package    local_fpvirtual_gestion_alumnado
 * @copyright  2026 FP virtual Aragón
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

defined('MOODLE_INTERNAL') || die();

$string['artifact:csv'] = 'Google accounts CSV (contains passwords)';
$string['artifact:log'] = 'Log';
$string['artifact:plan'] = 'Plan (JSON)';
$string['artifact:report'] = 'Report (Markdown)';
$string['artifact:sigad'] = 'Copy of the SIGAD file';
$string['engine:external'] = 'External command (Python)';
$string['engine:php'] = 'Built into Moodle';
$string['error:nocommand'] = 'The process command is not configured. Set it in the plugin settings.';
$string['error:nolog'] = 'The file of this run was not found.';
$string['error:nomanualenrol'] = 'Course {$a} has no enabled manual enrolment method.';
$string['error:nostudentrole'] = 'There is no role with the student archetype.';
$string['error:sigad'] = 'SIGAD error: {$a}';
$string['error:sigadfile'] = 'Cannot read the SIGAD file: {$a}';
$string['error:usernametaken'] = 'Username {$a} already exists in Moodle.';
$string['error:usernotcreated'] = 'User {$a} could not be created in this run.';
$string['fpvirtual_gestion_alumnado:launch'] = 'Launch student management manually';
$string['fpvirtual_gestion_alumnado:usewebservice'] = 'Read the users and enrolments snapshot through web services';
$string['fpvirtual_gestion_alumnado:viewstatus'] = 'View student management status and history';
$string['heading:external'] = 'External engine (transition)';
$string['heading:external_desc'] = 'Only used when the engine is "External command" (former Python package).';
$string['heading:guards'] = 'Safety limits';
$string['heading:guards_desc'] = 'If the plan exceeds them, no change is applied and the run is marked as "Stopped for safety". The run always aborts if SIGAD returns no students.';
$string['heading:notify'] = 'Notifications';
$string['heading:notify_desc'] = 'Emails to students (welcome, username change, new enrolments) and to managers (report), sent through the Moodle mail settings.';
$string['heading:rules'] = 'Synchronisation rules';
$string['heading:rules_desc'] = 'Which users, courses and cohorts are managed.';
$string['heading:run'] = 'Execution';
$string['heading:run_desc'] = 'When and how the synchronisation runs. The scheduled task timing is set in Site administration > Server > Scheduled tasks.';
$string['heading:sigad'] = 'SIGAD connection';
$string['heading:sigad_desc'] = 'Service that provides the enrolled students. The current academic year is requested (January to August: the one that started the previous year).';
$string['launch:apply_desc'] = 'Applies the changes (accounts, enrolments, suspensions, emails). Review a dry-run first.';
$string['launch:button_apply'] = 'Run and apply now';
$string['launch:button_dry'] = 'Run dry-run now';
$string['launch:confirm_apply'] = 'This will apply changes to Moodle. Are you sure?';
$string['launch:currentmode'] = 'Default scheduled mode: {$a}';
$string['launch:dry_desc'] = 'Analyses and reports what would change, without writing anything to Moodle.';
$string['launch:heading'] = 'Launch student synchronisation';
$string['launch:intro'] = 'Launch the synchronisation to check it (dry-run) or apply changes. It runs in the background and is recorded in the history with its report.';
$string['logs:artifacts'] = 'Run files';
$string['logs:back'] = 'Back to history';
$string['logs:detail'] = 'Run #{$a}';
$string['logs:download'] = 'Download log';
$string['logs:empty'] = 'This run has no saved log.';
$string['logs:history'] = 'Run history';
$string['logs:plan'] = 'Plan';
$string['logs:view'] = 'View';
$string['menu:launch'] = 'Student management: run now';
$string['menu:logs'] = 'Student management: history';
$string['menu:status'] = 'Student management: status';
$string['mode:apply'] = 'Apply (writes changes)';
$string['mode:dry'] = 'Dry-run (analysis only)';
$string['msg:queued'] = 'Run queued (mode {$a}). It will start on the next cron run; check the status page for the result.';
$string['origen:cli'] = 'Command line';
$string['origen:cron'] = 'Cron';
$string['origen:manual'] = 'Manual';
$string['pluginname'] = 'FP Virtual: student management';
$string['privacy:metadata:reason'] = 'The plugin does not store personal data in its own tables. The artefacts of each run (report, plan, copy of the SIGAD file and accounts CSV) are stored in the data directory and deleted automatically after the configured retention period.';
$string['setting:cleanupenabled'] = 'Yearly cleanup of suspended enrolments';
$string['setting:cleanupenabled_desc'] = 'During the given month, suspended manual enrolments in managed courses are removed.';
$string['setting:cleanupmonth'] = 'Cleanup month';
$string['setting:cleanupmonth_desc'] = 'Month number (1-12).';
$string['setting:cohortalumnado'] = 'General students cohort';
$string['setting:cohortalumnado_desc'] = 'Cohort every active student belongs to. {centre}-{cycle} cohorts are managed as well.';
$string['setting:command'] = 'Process command';
$string['setting:command_desc'] = 'Full command of the Python package, e.g. python3 /opt/gestion_alumnos.pyz. "sync" and, when applying, "--apply" are appended.';
$string['setting:dailyemaillimit'] = 'Daily email limit';
$string['setting:dailyemaillimit_desc'] = 'Student emails per day across all runs. 0 for no limit.';
$string['setting:emaildomain'] = 'Institutional email domain';
$string['setting:emaildomain_desc'] = 'The main email of new users is {document}@{domain}.';
$string['setting:emailpause'] = 'Pause between emails (s)';
$string['setting:emailpause_desc'] = 'Avoids flooding the mail server.';
$string['setting:enabled'] = 'Enable scheduled run';
$string['setting:enabled_desc'] = 'When enabled, the scheduled task runs the synchronisation in the configured mode. Manual launch is always available.';
$string['setting:engine'] = 'Engine';
$string['setting:engine_desc'] = 'Built-in (recommended): the synchronisation runs inside Moodle. External command: launches the former Python package.';
$string['setting:excludedcourses'] = 'Excluded courses';
$string['setting:excludedcourses_desc'] = 'Course short names whose enrolments are never changed. Only {centre}-{cycle}-{subjectid} courses are managed; tutorials are excluded.';
$string['setting:excludedprefixes'] = 'Excluded prefixes';
$string['setting:excludedprefixes_desc'] = 'Users whose username starts with any of these comma-separated prefixes are never modified (e.g. teachers).';
$string['setting:extraenv'] = 'Extra environment variables';
$string['setting:extraenv_desc'] = 'One VAR=value per line.';
$string['setting:field_consentimiento'] = 'Profile field: data-sharing consent';
$string['setting:field_consentimiento_desc'] = 'Short name of the profile field set to 0 when a user is created. Leave empty to not write it.';
$string['setting:field_emailsigad'] = 'Profile field: SIGAD personal email';
$string['setting:field_emailsigad_desc'] = 'Short name of the profile field holding the personal email from SIGAD. Required.';
$string['setting:field_idsigad'] = 'Profile field: SIGAD identifier';
$string['setting:field_idsigad_desc'] = 'Short name of the profile field holding the student identifier in SIGAD (used to detect document changes). Required.';
$string['setting:field_tipodocumento'] = 'Profile field: document type';
$string['setting:field_tipodocumento_desc'] = 'Short name of the profile field holding the SIGAD document type. Leave empty to not write it.';
$string['setting:helpcourseid'] = 'Help course ID';
$string['setting:helpcourseid_desc'] = 'Linked from the welcome email.';
$string['setting:launchmode'] = 'Run mode';
$string['setting:launchmode_desc'] = 'Dry-run only analyses and reports; Apply writes the changes to Moodle.';
$string['setting:maxenrolsuspendpercent'] = 'Maximum enrolment suspensions (%)';
$string['setting:maxenrolsuspendpercent_desc'] = 'Percentage of active enrolments in managed courses (absolute minimum: 20). 0 for no limit.';
$string['setting:maxusersuspensions'] = 'Maximum user suspensions per run';
$string['setting:maxusersuspensions_desc'] = '0 for no limit.';
$string['setting:notifyenabled'] = 'Email students';
$string['setting:notifyenabled_desc'] = 'When disabled, only the report is sent to managers.';
$string['setting:notifyredirect'] = 'Redirect student emails to';
$string['setting:notifyredirect_desc'] = 'If set, every student email is sent to this address instead (for staging and testing). Leave empty in production.';
$string['setting:protectedusers'] = 'Protected users';
$string['setting:protectedusers_desc'] = 'User IDs that are never modified, separated by commas or lines. The guest, site administrators and web service accounts are always protected.';
$string['setting:reportto'] = 'Report recipients';
$string['setting:reportto_desc'] = 'Emails, separated by commas or lines, that receive the report of every run.';
$string['setting:retentiondays'] = 'History retention (days)';
$string['setting:retentiondays_desc'] = 'Runs and their artefacts (with personal data) are deleted after this number of days.';
$string['setting:sigad_baseurl'] = 'Service base URL';
$string['setting:sigad_baseurl_desc'] = '/solicitud/{year} and /fichero/{requestid} are appended.';
$string['setting:sigad_initialwait'] = 'Initial wait (s)';
$string['setting:sigad_initialwait_desc'] = 'Wait between the request and the first file download.';
$string['setting:sigad_maxretries'] = 'Download attempts';
$string['setting:sigad_maxretries_desc'] = 'Number of attempts while SIGAD builds the file.';
$string['setting:sigad_password'] = 'Password';
$string['setting:sigad_password_desc'] = 'Stored encrypted.';
$string['setting:sigad_retrydelay'] = 'Delay between attempts (s)';
$string['setting:sigad_retrydelay_desc'] = 'Seconds between download attempts.';
$string['setting:sigad_timeout'] = 'Request timeout (s)';
$string['setting:sigad_timeout_desc'] = 'Maximum time of each SIGAD request.';
$string['setting:sigad_user'] = 'User';
$string['setting:sigad_user_desc'] = 'SIGAD service user.';
$string['setting:supporturl'] = 'Support URL';
$string['setting:supporturl_desc'] = 'Help and incidents link in emails. Empty: {wwwroot}/soporte/.';
$string['setting:syncnames'] = 'Synchronise first and last names';
$string['setting:syncnames_desc'] = 'Updates names in Moodle when they differ from SIGAD.';
$string['setting:timeout'] = 'Command timeout (s)';
$string['setting:timeout_desc'] = 'Maximum time before stopping the external command.';
$string['status:aborted'] = 'Stopped for safety';
$string['status:config'] = 'Settings';
$string['status:cron'] = 'Scheduled task (cron)';
$string['status:cron_disabled'] = 'Task disabled';
$string['status:cron_hint'] = 'Timing is set in Site administration > Server > Scheduled tasks.';
$string['status:cron_lastrun'] = 'Last run (cron)';
$string['status:cron_missing'] = 'The scheduled task was not found. Check the plugin installation.';
$string['status:cron_nextrun'] = 'Next run';
$string['status:error'] = 'With errors';
$string['status:field_duration'] = 'Duration';
$string['status:field_exitcode'] = 'Exit code';
$string['status:field_origen'] = 'Origin';
$string['status:field_result'] = 'Result';
$string['status:field_start'] = 'Start';
$string['status:heading'] = 'Synchronisation status';
$string['status:lastrun'] = 'Last run';
$string['status:noruns'] = 'No runs recorded yet.';
$string['status:running'] = 'Running';
$string['status:success'] = 'Successful';
$string['status:summary'] = 'Summary';
$string['status:viewlog'] = 'View run details';
$string['task:cleanup'] = 'Purge old student management runs';
$string['task:sync'] = 'Synchronise students with SIGAD';
