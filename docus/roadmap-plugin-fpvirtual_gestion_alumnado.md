# Roadmap — Plugin Moodle `fpvirtual_gestion_alumnado`

> **Fecha:** 2026-10-29
> **Estado:** ⬜ No iniciado (especificación previa; el directorio
> `moodle_plugin/` está vacío en el repo).
> **Objetivo:** Implementar y desplegar el plugin PHP que complementa al
> zipapp Python: por un lado expone el *snapshot* vía webservice (lo que hoy
> ya consume `APISnapshotMoodleSource`), y por otro da a los administradores
> de Moodle una interfaz para **lanzar el proceso de sincronización en
> dry-run o real**, **programar su ejecución por cron** y **consultar logs y
> estado de la última ejecución**.
> **Relacionado:** [`conexion_moodle_api.md`](conexion_moodle_api.md) (sección 6),
> [`roadmap-portacion-curso2627.md`](roadmap-portacion-curso2627.md) (completado).

---

## 0. Decisión de alcance y nombre

| Decisión | Detalle |
|----------|---------|
| **Nombre** | `fpvirtual_gestion_alumnado` (sustituye al provisional `local_fparagon`) |
| **Tipo de plugin** | `local` (no añade bloques ni módulos; es servicio interno) |
| **Componente frankenstyle** | `local_fpvirtual_gestion_alumnado` — Moodle exige el prefijo `local_` en clases, funciones webservice y tablas: `local_fpvirtual_gestion_alumnado_*` |
| **Directorio en Moodle** | `local/fpvirtual_gestion_alumnado/` |
| **Directorio en el repo** | `moodle_plugin/fpvirtual_gestion_alumnado/` (renombrar el esqueleto actual `moodle_plugin/local_fparagon/`) |
| **Función webservice** | `local_fpvirtual_gestion_alumnado_get_snapshot` (sustituye a `local_fparagon_get_snapshot`) |

> ⚠️ **Impacto en el cliente Python:** hay que actualizar el nombre de la
> función en `gestion_alumnos/repositories/moodle_sources/api_snapshot_source.py`,
> sus tests (`tests/test_moodle_sources.py`) y la documentación
> (`conexion_moodle_api.md`, `flujos.md`, `AGENTS.md`). Se hace en la Fase 1.

### Filosofía del plugin — límites estrictos

> ⚠️ **El plugin NO contiene los procesos de la parte API/sincronización.**
> Toda la lógica de negocio vive en el paquete Python `gestion_alumnos`
> (extracción SIGAD, análisis de deltas, aplicación de cambios en Moodle,
> envío de emails). El plugin **nunca** duplica ni reimplementa esa
> lógica, ni accede a SIGAD, ni aplica cambios por su cuenta. Sus únicas
> responsabilidades son:
>
> 1. **Servir datos**: exponer el *snapshot* de Moodle vía webservice
>    (`local_fpvirtual_gestion_alumnado_get_snapshot`) para que el Python
>    lo consuma.
> 2. **Orquestar ejecuciones**: lanzar el proceso Python ya empaquetado
>    (zipapp) en modo dry-run o real, manualmente o por cron — siempre
>    delegando en el binario/configuración existentes.
> 3. **Auditar**: registrar resultado y logs de cada ejecución y
>    mostrar estado e historial en el admin.

En resumen: el plugin es **servidor del snapshot + panel de control y
auditoría** del proceso; el cerebro sigue siendo el zipapp Python.

---

## Fase 1 — Renombrado, esqueleto y función webservice snapshot ⬜

Base sobre la que se construye todo lo demás. Al terminar, la estrategia
`api-snapshot` deja de estar limitada por "plugin no instalado".

| # | Tarea | Entregable |
|---|-------|------------|
| 1.1 | Renombrar `moodle_plugin/local_fparagon/` → `moodle_plugin/fpvirtual_gestion_alumnado/` | Estructura de directorios final |
| 1.2 | `version.php` (version, requires, maturity) + `lang/en|es/local_fpvirtual_gestion_alumnado.php` | Plugin instalable (aunque vacío) |
| 1.3 | `db/services.php` declarando `local_fpvirtual_gestion_alumnado_get_snapshot` + clase `external/get_snapshot.php` implementando `external_api` | Función webservice registrable en el servicio externo |
| 1.4 | Implementar la query del snapshot: usuarios (id, username, email, firstname, lastname, suspended, cohortes, custom fields `IdSIGAD`/`emailsigad`/`consentimientoCDD`) + matrículas (usuario ↔ curso, shortname, estado) | Misma forma que `MoodleSnapshot` espera el Python (claves `usuarios` / `matriculas`) |
| 1.5 | **Actualizar el cliente Python**: renombrar la función en `api_snapshot_source.py`, tests y docs | Sin referencias a `local_fparagon` en el repo |
| 1.6 | Desplegar en **preproducción**, añadir la función al servicio web externo y verificar con `test_preproduccion_api.py` o curl | Estrategia `api-snapshot` operativa en pre |

**Criterio de aceptación:** `sync --source-strategy api-snapshot --driver api`
contra preproducción extrae el snapshot completo en una llamada y el
orquestador genera el informe igual que con `api-course-based`.

---

## Fase 2 — Configuración de administración (settings) ⬜

Página de configuración del plugin (`Administración del sitio > Plugins >
Local > FP Virtual Gestión Alumnado`) con los ajustes que condicionan el
resto de fases:

| # | Ajuste | Tipo | Descripción |
|---|--------|------|-------------|
| 2.1 | `enabled` | checkbox | Activa/desactiva el lanzamiento programado y manual |
| 2.2 | `modo_lanzamiento` | select | `dry` (por defecto) / `apply` — modo en el que se ejecuta el proceso desde Moodle |
| 2.3 | `comando` | text | Ruta del intérprete/zipapp, p. ej. `python3 /opt/gestion_alumnos.pyz` |
| 2.4 | `env_extra` | textarea (opcional) | Variables de entorno adicionales por línea (`VAR=valor`) para la ejecución |
| 2.5 | `timeout` | int | Segundos máximos de ejecución (por defecto 600) |
| 2.6 | `retener_logs` | int | Días de retención de logs/historial (por defecto 30) |

**Criterio de aceptación:** los ajustes se persisten con `admin_setting_*`,
aparecen en el árbol de administración y se validan (comando no vacío,
timeout > 0).

---

## Fase 3 — Lanzamiento manual: botón "Ejecutar ahora" con dry-run ⬜

Permite a un admin **verificar el funcionamiento** sin esperar al cron y
sin aplicar cambios.

| # | Tarea | Detalle |
|---|-------|---------|
| 3.1 | Página `admin/launch.php` con botón "Ejecutar ahora (dry-run)" y, solo si el modo global es `dry`, botón opcional "Ejecutar con apply" (confirmación explícita) | Página bajo la categoría del plugin |
| 3.2 | Ejecución vía `core\task\adhoc_task` (no bloquea la petición HTTP) o `proc_open` con captura de stdout/stderr y `timeout` de 2.5 | El proceso Python se lanza con `sync` (o `sync --apply`) usando el comando y entorno configurados |
| 3.3 | Tras lanzar, redirigir a la página de **estado/logs** (Fase 4) con mensaje "ejecución en curso" | El estado se resuelve en la siguiente visita |
| 3.4 | Registrar la ejecución en el historial (inicio, fin, modo, código de salida) incluso si el proceso muere por timeout | Nada de ejecuciones invisibles |

**Criterio de aceptación:** un admin sin acceso SSH lanza un dry-run desde
la web y en menos de 1 minuto ve en Moodle el resultado y la salida del
proceso.

---

## Fase 4 — Programación por cron (scheduled task) ⬜

Configuración de **cuándo** se lanza el proceso, usando el sistema nativo de
tareas programadas de Moodle (los admins ya saben gestionarlo y se ve en
`Administración del sitio > Tareas programadas`).

| # | Tarea | Detalle |
|---|-------|---------|
| 4.1 | `classes/task/sync_task.php` extendiendo `\core\task\scheduled_task` | Ejecuta el mismo pipeline que el lanzamiento manual, en el modo configurado (2.2); respeta `enabled` (2.1) |
| 4.2 | `db/tasks.php` con schedule por defecto razonable (p. ej. diaria 04:00) | La *hora y frecuencia concretas* se configuran desde la interfaz nativa de tareas programadas de Moodle (minuto/hora/día/mes/día de semana) — no hace falta reinventar el cron en settings |
| 4.3 | Mensaje en la página de settings indicando dónde ajustar el horario (`/admin/task.php`) y el estado actual de la tarea (habilitada, próxima ejecución, última ejecución) | Visibilidad inmediata de la programación |
| 4.4 | `get_run_if_component_disabled()` y logging vía `mtrace`/log del task | Ejecuciones trazadas en el log estándar de Moodle |

**Criterio de aceptación:** tras instalar, la tarea aparece en la lista de
tareas programadas; al cambiar su horario en el admin nativo, el cron de
Moodle la lanza a esa hora en el modo configurado.

---

## Fase 5 — Logs, historial y estado de la última ejecución ⬜

La parte de **auditoría**: que cualquier admin vea de un vistazo si el
proceso va bien y pueda revisar el detalle.

| # | Tarea | Detalle |
|---|-------|---------|
| 5.1 | Tabla `{prefix}local_fpgestion_runs` (`db/install.xml`): id, tiempo inicio/fin, origen (`manual`/`cron`), modo (`dry`/`apply`), exit code, resumen (JSON: altas/bajas/cambios detectados, emails enviados), ruta al log completo | Historial persistido, purgable por retención (2.6) |
| 5.2 | Guardar el stdout/stderr completo en `dataroot/fpvirtual_gestion_alumnado/logs/<runid>.log` | Log accesible desde la web |
| 5.3 | Página `admin/status.php` — **estado de la última ejecución**: fecha, origen, modo, duración, ✓/✗ resultado, contadores del resumen, enlace al log; más **próxima ejecución programada** (de la scheduled task) | Visión de un vistazo |
| 5.4 | Página `admin/logs.php` — historial paginado con filtros (fecha, modo, resultado) y descarga/visualización del log de cada ejecución | Auditoría completa |
| 5.5 | Capacidades: `local/fpvirtual_gestion_alumnado:viewstatus` (todos los admins de forma predeterminada) y `local/fpvirtual_gestion_alumnado:launch` (solo managers/administradores) | Control de acceso |
| 5.6 | `classes/privacy/provider.php` (null provider o metadata+delete según se almacene datos personales en logs) | Cumplimiento de la Privacy API de Moodle |
| 5.7 | Limpieza automática de logs y runs antiguos según `retener_logs` (en la scheduled task o en `task\cleanup_task` diaria) | No acumular datos indefinidamente |

**Criterio de aceptación:** tras un dry-run manual y una ejecución cron, la
página de estado muestra ambas con su resultado correcto; un admin puede
leer el log completo de cualquiera sin salir de Moodle.

---

## Fase 6 — Tests, CI y documentación ⬜

| # | Tarea | Detalle |
|---|-------|---------|
| 6.1 | Tests PHPUnit del external function (dataset sintético con generadores de Moodle) y de las páginas admin (estado con runs de ejemplo) | Cobertura del lado PHP |
| 6.2 | CI con `moodle-plugin-ci` (phpunit, phpcs, mustache, grunt si aplica) en GitHub Actions | Calidad en cada push del plugin |
| 6.3 | Actualizar `docus/conexion_moodle_api.md` (sección 6), `flujos.md` y `AGENTS.md` con el nombre definitivo y las nuevas capacidades del plugin | Documentación coherente con la implementación |
| 6.4 | README del plugin (`moodle_plugin/fpvirtual_gestion_alumnado/README.md`): instalación, permisos, configuración del cron y troubleshooting | Autónomo para quien despliegue |

---

## Fase 7 — Despliegue y activación ⬜

| # | Tarea | Detalle |
|---|-------|---------|
| 7.1 | Desplegar en **preproducción**, completar la instalación (`Notificaciones`) y asignar capacidades | Validación en entorno real |
| 7.2 | Añadir `local_fpvirtual_gestion_alumnado_get_snapshot` al servicio web externo y pasar `MOODLE_SOURCE_STRATEGY=api-snapshot` | Extracción en 1 llamada |
| 7.3 | Probar cadena completa: botón dry-run desde Moodle → informe → log; esperar ejecución cron programada | Verificación end-to-end |
| 7.4 | Desplegar en **producción** con `modo_lanzamiento=dry` inicial; tras un periodo de observación, pasar a `apply` | Activación progresiva |
| 7.5 | Quitar `api-course-based` como estrategia por defecto documentada si el snapshot se consolida | Simplificación (opcional) |

---

## Resumen de dependencias

```
Fase 1 (webservice) ── independiente, desbloquea api-snapshot
Fase 2 (settings)   ── base de 3, 4 y 5
Fase 3 (manual)  ┐
Fase 4 (cron)    ├─ comparten el pipeline de ejecución: conviene un
Fase 5 (logs)    ┘   único "runner" interno (classes/runner.php) que
                     usan las tres, con inyección de origen (manual/cron)
Fase 6 (tests/CI) ── en paralelo desde la Fase 2
Fase 7 (despliegue) ── cierra
```

## Esfuerzo estimado

| Fase | Esfuerzo | Riesgo principal |
|------|----------|------------------|
| 1 — Webservice | Medio | Queries del snapshot con cohortes/custom fields |
| 2 — Settings | Bajo | — |
| 3 — Lanzamiento manual | Medio | Timeout de PHP vs. duración real del sync → mitigar con adhoc task |
| 4 — Cron | Bajo | — (usa el mecanismo nativo de Moodle) |
| 5 — Logs y estado | Medio | Diseño de la tabla de runs y purga |
| 6 — Tests/CI | Medio | Entorno de CI para plugins Moodle |
| 7 — Despliegue | Bajo | Coordinación con los entornos |

## Próximo paso inmediato

Comenzar por la **Fase 1 (tareas 1.1–1.5)**: es la única que desbloquea
funcionalidad que el Python ya sabe consumir, y el renombrado conviene
hacerlo antes de escribir código nuevo para no arrastrar `local_fparagon`.
