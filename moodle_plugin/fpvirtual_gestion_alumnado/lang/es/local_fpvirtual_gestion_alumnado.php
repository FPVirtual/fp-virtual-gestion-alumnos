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
 * Cadenas de idioma (español).
 *
 * @package    local_fpvirtual_gestion_alumnado
 * @copyright  2026 FP virtual Aragón
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

defined('MOODLE_INTERNAL') || die();

$string['pluginname'] = 'FP Virtual: gestión de alumnado';
$string['privacy:metadata:reason'] = 'El plugin no guarda datos personales en tablas propias. Los artefactos de cada ejecución (informe, plan, copia del fichero de SIGAD y CSV de altas) se guardan en el directorio de datos y se eliminan automáticamente al cumplirse la retención configurada.';

$string['fpvirtual_gestion_alumnado:usewebservice'] = 'Consultar el snapshot de usuarios y matrículas vía servicio web';
$string['fpvirtual_gestion_alumnado:viewstatus'] = 'Ver el estado y el historial de la gestión de alumnado';
$string['fpvirtual_gestion_alumnado:launch'] = 'Lanzar manualmente la gestión de alumnado';

$string['task:sync'] = 'Sincronizar el alumnado con SIGAD';
$string['task:cleanup'] = 'Purgar ejecuciones antiguas de la gestión de alumnado';

// Secciones de ajustes.
$string['heading:run'] = 'Ejecución';
$string['heading:run_desc'] = 'Cuándo y cómo se ejecuta la sincronización. El horario de la tarea programada se ajusta en Administración del sitio > Servidor > Tareas programadas.';
$string['heading:sigad'] = 'Conexión con SIGAD';
$string['heading:sigad_desc'] = 'Servicio del que se descarga el alumnado matriculado. Se pide el curso académico vigente (de enero a agosto, el que empezó el año anterior).';
$string['heading:rules'] = 'Reglas de sincronización';
$string['heading:rules_desc'] = 'Qué usuarios, cursos y cohortes gestiona la sincronización.';
$string['heading:guards'] = 'Límites de seguridad';
$string['heading:guards_desc'] = 'Si el plan los supera, no se aplica ningún cambio y la ejecución queda como «Detenida por seguridad». Siempre se aborta si SIGAD no devuelve alumnos.';
$string['heading:notify'] = 'Notificaciones';
$string['heading:notify_desc'] = 'Correos al alumnado (bienvenida, cambio de usuario, nuevas matrículas) y a los responsables (informe). Se envían con la configuración de correo de Moodle.';
$string['heading:external'] = 'Motor externo (transición)';
$string['heading:external_desc'] = 'Solo se usa si el motor es «Comando externo» (paquete Python anterior).';

// Ajustes.
$string['setting:enabled'] = 'Activar ejecución programada';
$string['setting:enabled_desc'] = 'Si está activado, la tarea programada ejecuta la sincronización en el modo configurado. El lanzamiento manual está siempre disponible.';
$string['setting:launchmode'] = 'Modo de ejecución';
$string['setting:launchmode_desc'] = 'Dry-run solo analiza e informa; Aplicar escribe los cambios en Moodle.';
$string['setting:engine'] = 'Motor';
$string['setting:engine_desc'] = 'Integrado (recomendado): la sincronización se ejecuta dentro de Moodle. Comando externo: lanza el paquete Python anterior.';
$string['engine:php'] = 'Integrado en Moodle';
$string['engine:external'] = 'Comando externo (Python)';
$string['setting:retentiondays'] = 'Retención del historial (días)';
$string['setting:retentiondays_desc'] = 'Las ejecuciones y sus artefactos (con datos personales) se eliminan pasado este número de días.';
$string['setting:sigad_baseurl'] = 'URL base del servicio';
$string['setting:sigad_baseurl_desc'] = 'Se añaden /solicitud/{curso} y /fichero/{idSolicitud}.';
$string['setting:sigad_user'] = 'Usuario';
$string['setting:sigad_user_desc'] = 'Usuario del servicio de SIGAD.';
$string['setting:sigad_password'] = 'Contraseña';
$string['setting:sigad_password_desc'] = 'Se guarda cifrada.';
$string['setting:sigad_timeout'] = 'Timeout por petición (s)';
$string['setting:sigad_timeout_desc'] = 'Tiempo máximo de cada petición a SIGAD.';
$string['setting:sigad_initialwait'] = 'Espera inicial (s)';
$string['setting:sigad_initialwait_desc'] = 'Espera entre la solicitud y la primera descarga del fichero.';
$string['setting:sigad_maxretries'] = 'Intentos de descarga';
$string['setting:sigad_maxretries_desc'] = 'Número de intentos mientras SIGAD genera el fichero.';
$string['setting:sigad_retrydelay'] = 'Espera entre intentos (s)';
$string['setting:sigad_retrydelay_desc'] = 'Segundos entre intentos de descarga.';
$string['setting:emaildomain'] = 'Dominio del email institucional';
$string['setting:emaildomain_desc'] = 'El email principal de los usuarios nuevos es {documento}@{dominio}.';
$string['setting:excludedprefixes'] = 'Prefijos excluidos';
$string['setting:excludedprefixes_desc'] = 'Los usuarios cuyo nombre empieza por alguno de estos prefijos (separados por comas) nunca se modifican (p. ej. profesorado).';
$string['setting:protectedusers'] = 'Usuarios protegidos';
$string['setting:protectedusers_desc'] = 'IDs de usuario que nunca se modifican, separados por comas o líneas. El invitado, los administradores y las cuentas con autenticación de servicio web están siempre protegidos.';
$string['setting:excludedcourses'] = 'Cursos excluidos';
$string['setting:excludedcourses_desc'] = 'Nombres cortos de cursos cuyas matrículas no se tocan. Solo se gestionan los cursos {centro}-{ciclo}-{idMateria}; las tutorías quedan fuera.';
$string['setting:cohortalumnado'] = 'Cohorte general del alumnado';
$string['setting:cohortalumnado_desc'] = 'Cohorte a la que pertenece todo alumno activo. Además se gestionan las cohortes {centro}-{ciclo}.';
$string['setting:syncnames'] = 'Sincronizar nombre y apellidos';
$string['setting:syncnames_desc'] = 'Actualiza nombre y apellidos en Moodle cuando difieren de SIGAD.';
$string['setting:cleanupenabled'] = 'Limpieza anual de matrículas suspendidas';
$string['setting:cleanupenabled_desc'] = 'Durante el mes indicado se eliminan las matrículas manuales suspendidas en cursos gestionados.';
$string['setting:cleanupmonth'] = 'Mes de la limpieza';
$string['setting:cleanupmonth_desc'] = 'Número de mes (1-12).';
$string['setting:maxusersuspensions'] = 'Máximo de usuarios suspendidos por ejecución';
$string['setting:maxusersuspensions_desc'] = '0 para no limitar.';
$string['setting:maxenrolsuspendpercent'] = 'Máximo de matrículas suspendidas (%)';
$string['setting:maxenrolsuspendpercent_desc'] = 'Porcentaje de las matrículas activas en cursos gestionados (mínimo absoluto: 20). 0 para no limitar.';
$string['setting:notifyenabled'] = 'Enviar correos al alumnado';
$string['setting:notifyenabled_desc'] = 'Si se desactiva, solo se envía el informe a los responsables.';
$string['setting:notifyredirect'] = 'Redirigir los correos del alumnado a';
$string['setting:notifyredirect_desc'] = 'Si se indica una dirección, todos los correos al alumnado se envían a ella (para preproducción y pruebas). Vacío en producción.';
$string['setting:dailyemaillimit'] = 'Límite diario de correos';
$string['setting:dailyemaillimit_desc'] = 'Correos al alumnado por día, sumando todas las ejecuciones. 0 para no limitar.';
$string['setting:emailpause'] = 'Pausa entre correos (s)';
$string['setting:emailpause_desc'] = 'Evita saturar el servidor de correo.';
$string['setting:reportto'] = 'Destinatarios del informe';
$string['setting:reportto_desc'] = 'Emails, separados por comas o líneas, que reciben el informe de cada ejecución.';
$string['setting:helpcourseid'] = 'ID del curso de ayuda';
$string['setting:helpcourseid_desc'] = 'Se enlaza en el correo de bienvenida.';
$string['setting:supporturl'] = 'URL de soporte';
$string['setting:supporturl_desc'] = 'Enlace de ayuda e incidencias de los correos. Vacío: {wwwroot}/soporte/.';
$string['setting:command'] = 'Comando del proceso';
$string['setting:command_desc'] = 'Comando completo del paquete Python, p. ej. python3 /opt/gestion_alumnos.pyz. Se le añade "sync" y, en su caso, "--apply".';
$string['setting:extraenv'] = 'Variables de entorno adicionales';
$string['setting:extraenv_desc'] = 'Un VAR=valor por línea.';
$string['setting:timeout'] = 'Timeout del comando (s)';
$string['setting:timeout_desc'] = 'Tiempo máximo antes de detener el comando externo.';

$string['mode:dry'] = 'Dry-run (solo análisis)';
$string['mode:apply'] = 'Aplicar (escribe cambios)';

$string['menu:status'] = 'Gestión alumnado: estado';
$string['menu:logs'] = 'Gestión alumnado: historial';
$string['menu:launch'] = 'Gestión alumnado: ejecutar ahora';

$string['msg:queued'] = 'Ejecución encolada (modo {$a}). Se iniciará en la próxima ejecución del cron; consulta el estado para ver el resultado.';

$string['launch:heading'] = 'Lanzar la sincronización del alumnado';
$string['launch:intro'] = 'Lanza la sincronización para verificarla (dry-run) o aplicar cambios. Se ejecuta en segundo plano y queda registrada en el historial con su informe.';
$string['launch:dry_desc'] = 'Analiza e informa de qué cambiaría, sin escribir nada en Moodle.';
$string['launch:apply_desc'] = 'Aplica los cambios (altas, matrículas, suspensiones, correos). Revisa antes un dry-run.';
$string['launch:button_dry'] = 'Ejecutar dry-run ahora';
$string['launch:button_apply'] = 'Ejecutar y aplicar ahora';
$string['launch:confirm_apply'] = 'Esto aplicará cambios en Moodle. ¿Estás seguro?';
$string['launch:currentmode'] = 'Modo programado por defecto: {$a}';

$string['status:heading'] = 'Estado de la sincronización';
$string['status:config'] = 'Configuración';
$string['status:cron'] = 'Tarea programada (cron)';
$string['status:cron_disabled'] = 'Tarea deshabilitada';
$string['status:cron_nextrun'] = 'Próxima ejecución';
$string['status:cron_lastrun'] = 'Última ejecución (cron)';
$string['status:cron_hint'] = 'El horario se ajusta en Administración del sitio > Servidor > Tareas programadas.';
$string['status:cron_missing'] = 'No se encuentra la tarea programada. Revisa la instalación del plugin.';
$string['status:lastrun'] = 'Última ejecución';
$string['status:noruns'] = 'Aún no hay ejecuciones registradas.';
$string['status:success'] = 'Correcta';
$string['status:error'] = 'Con errores';
$string['status:aborted'] = 'Detenida por seguridad';
$string['status:running'] = 'En curso';
$string['status:field_origen'] = 'Origen';
$string['status:field_start'] = 'Inicio';
$string['status:field_duration'] = 'Duración';
$string['status:field_result'] = 'Resultado';
$string['status:field_exitcode'] = 'Código de salida';
$string['status:summary'] = 'Resumen';
$string['status:viewlog'] = 'Ver el detalle de la ejecución';

$string['origen:manual'] = 'Manual';
$string['origen:cron'] = 'Cron';
$string['origen:cli'] = 'Línea de comandos';

$string['logs:history'] = 'Historial de ejecuciones';
$string['logs:detail'] = 'Ejecución #{$a}';
$string['logs:empty'] = 'Esta ejecución no tiene log guardado.';
$string['logs:download'] = 'Descargar log';
$string['logs:back'] = 'Volver al historial';
$string['logs:view'] = 'Ver';
$string['logs:artifacts'] = 'Ficheros de la ejecución';
$string['logs:plan'] = 'Plan';
$string['artifact:log'] = 'Log';
$string['artifact:report'] = 'Informe (Markdown)';
$string['artifact:plan'] = 'Plan (JSON)';
$string['artifact:csv'] = 'CSV de altas de Google (contiene contraseñas)';
$string['artifact:sigad'] = 'Copia del fichero de SIGAD';

$string['error:nocommand'] = 'El comando del proceso no está configurado. Establécelo en los ajustes del plugin.';
$string['error:nolog'] = 'No se encuentra el fichero de esta ejecución.';
$string['error:sigad'] = 'Error de SIGAD: {$a}';
$string['error:sigadfile'] = 'No se puede leer el fichero de SIGAD: {$a}';
$string['error:usernotcreated'] = 'El usuario {$a} no se pudo crear en esta ejecución.';
$string['error:usernametaken'] = 'El nombre de usuario {$a} ya existe en Moodle.';
$string['error:nomanualenrol'] = 'El curso {$a} no tiene un método de matriculación manual activo.';
$string['error:nostudentrole'] = 'No existe ningún rol con arquetipo de estudiante.';
