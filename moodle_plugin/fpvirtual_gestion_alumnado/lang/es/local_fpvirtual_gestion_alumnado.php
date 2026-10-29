<?php
// Cadenas de idioma de FP Virtual Gestión Alumnado (español).

$string['pluginname'] = 'FP Virtual: gestión de alumnado';
$string['privacy:metadata:reason'] = 'Este plugin no almacena datos personales de usuarios de Moodle. La tabla de ejecuciones guarda metadatos del proceso (fechas, modos, códigos de salida) y los logs son la salida del proceso externo de gestión.';

$string['task:sync'] = 'Ejecutar el proceso de gestión de alumnado';
$string['task:cleanup'] = 'Purgar logs antiguos de gestión de alumnado';

$string['setting:enabled'] = 'Activar ejecución programada';
$string['setting:enabled_desc'] = 'Si está activado, la tarea programada lanza el proceso en el modo configurado. El lanzamiento manual está siempre disponible con independencia de este ajuste.';
$string['setting:launchmode'] = 'Modo de ejecución';
$string['setting:launchmode_desc'] = 'Modo con el que se ejecuta el proceso programado y el lanzamiento manual por defecto: dry-run solo analiza; apply escribe los cambios en Moodle.';
$string['setting:command'] = 'Comando del proceso';
$string['setting:command_desc'] = 'Comando completo que ejecuta el paquete de gestión (zipapp), p. ej. python3 /opt/gestion_alumnos.pyz. El plugin añade "sync" y, en su caso, "--apply".';
$string['setting:extraenv'] = 'Variables de entorno adicionales';
$string['setting:extraenv_desc'] = 'Un VAR=valor por línea, añadidas al entorno del proceso.';
$string['setting:timeout'] = 'Timeout (segundos)';
$string['setting:timeout_desc'] = 'Tiempo máximo de ejecución antes de matar el proceso.';
$string['setting:retentiondays'] = 'Retención de logs (días)';
$string['setting:retentiondays_desc'] = 'Las ejecuciones y logs más antiguos que este número de días se purgan diariamente.';

$string['mode:dry'] = 'Dry-run (solo análisis)';
$string['mode:apply'] = 'Aplicar (escribe cambios)';

$string['menu:status'] = 'Gestión alumnado: estado';
$string['menu:logs'] = 'Gestión alumnado: logs';
$string['menu:launch'] = 'Gestión alumnado: ejecutar ahora';

$string['msg:queued'] = 'Ejecución encolada (modo {$a}). Consulta la página de estado para ver el progreso y el resultado.';

$string['launch:heading'] = 'Lanzar el proceso de gestión de alumnado';
$string['launch:intro'] = 'Lanza desde aquí el paquete de gestión para verificar su funcionamiento (dry-run) o aplicar cambios, sin usar la línea de comandos. La ejecución se realiza en segundo plano y queda registrada en el historial.';
$string['launch:dry_desc'] = 'Analiza e informa de qué cambiaría, sin escribir nada en Moodle. Úsalo para verificar la configuración.';
$string['launch:apply_desc'] = 'Aplica los cambios detectados (altas, matrículas, emails). Comprueba antes un dry-run.';
$string['launch:button_dry'] = 'Ejecutar dry-run ahora';
$string['launch:button_apply'] = 'Ejecutar con apply ahora';
$string['launch:confirm_apply'] = 'Esto aplicará cambios en Moodle. ¿Estás seguro?';
$string['launch:currentmode'] = 'Modo programado por defecto: {$a}';

$string['status:heading'] = 'Estado del proceso';
$string['status:config'] = 'Configuración';
$string['status:cron'] = 'Tarea programada (cron)';
$string['status:cron_disabled'] = 'Tarea deshabilitada';
$string['status:cron_nextrun'] = 'Próxima ejecución';
$string['status:cron_lastrun'] = 'Última ejecución (cron)';
$string['status:cron_hint'] = 'El horario (hora y frecuencia) se ajusta en Administración del sitio > Servidor > Tareas programadas.';
$string['status:cron_missing'] = 'No se encuentra la tarea programada. Revisa la instalación del plugin.';
$string['status:lastrun'] = 'Última ejecución';
$string['status:noruns'] = 'Aún no hay ejecuciones registradas.';
$string['status:success'] = 'Correcta';
$string['status:error'] = 'Error';
$string['status:running'] = 'En curso';
$string['status:field_origen'] = 'Origen';
$string['status:field_start'] = 'Inicio';
$string['status:field_duration'] = 'Duración';
$string['status:field_result'] = 'Resultado';
$string['status:field_exitcode'] = 'Código de salida';
$string['status:summary'] = 'Resumen';
$string['status:viewlog'] = 'Ver log completo';

$string['origen:manual'] = 'Manual';
$string['origen:cron'] = 'Cron';

$string['logs:history'] = 'Historial de ejecuciones';
$string['logs:detail'] = 'Ejecución #{$a}';
$string['logs:empty'] = 'Esta ejecución no tiene log guardado.';
$string['logs:download'] = 'Descargar log';
$string['logs:back'] = 'Volver al historial';
$string['logs:view'] = 'Ver';

$string['error:nocommand'] = 'El comando del proceso no está configurado. Establécelo en los ajustes del plugin.';
$string['error:nolog'] = 'No se encuentra el fichero de log de esta ejecución.';
