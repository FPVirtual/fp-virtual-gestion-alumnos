# Changelog

## [Unreleased]

### Added

- **Portación de mejoras desde `curso2627`** (línea legacy), ver `docus/roadmap-portacion-curso2627.md`:
  - **SMTP con timeout** configurable (`SMTP_TIMEOUT`, por defecto 30s) para evitar que el proceso se quede colgado.
  - **Texto plano real** en los correos: se genera a partir del HTML (portado de `enviar_correos.py`) con `set_content` + `add_alternative`.
  - **Pausa entre envíos** configurable (`EMAIL_PAUSA_SEGUNDOS`, por defecto 2s).
  - **Reintentos de envío**: `EmailJob.intentos` y `EMAIL_MAX_INTENTOS` (por defecto 3); un email fallido queda `pending` hasta agotar los intentos.
  - **Prioridad de informes**: `EmailJob.tipo` (`aviso`/`informe`); los informes se procesan antes que los avisos.
  - **`process-emails --solo-informes`** y **`process-emails --dry-run`**; el comando sale con código 1 si hay fallos.
  - **Bloqueo de ejecución concurrente** (`flock`) en `process-emails`.
  - **`BIENVENIDA_TO` configurable** como destinatario de bienvenidas fuera de `www`.
  - **Reactivación de suspendidos**: nuevo `ReactivationDelta` (usuario Moodle `suspended=1` presente en SIGAD) que reactiva la cuenta y la devuelve a la cohorte `alumnado`.
  - **Parada forzosa si SIGAD devuelve 0 alumnos**: se aborta la sincronización antes de tocar Moodle (evita suspensiones masivas).
  - **Aviso de cambio de usuario mejorado**: plantilla con saludo personalizado, párrafo "su correo no cambia este curso" y enlace a soporte.
- **Emails conectados al flujo de sincronización**: `SyncApplier` recibe un `EmailRepository` (según `EMAIL_MODE`) y notifica altas (bienvenida), cambios de username y nuevas matrículas; los errores de email nunca bloquean la sync.
- **Escape HTML en plantillas de email**: `gestion_alumnos/utils/plantillas.py` escapa los valores de SIGAD al renderizar (mitiga inyección HTML hasta la migración a Jinja2).
- **Custom fields en alta de usuarios**: al crear un usuario en Moodle se rellenan automáticamente los campos personalizados:
  - `IdSIGAD` → `idAlumno` de SIGAD.
  - `tipoDocumento` → `idTipoDocumento` de SIGAD.
  - `emailsigad` → email personal del JSON de SIGAD.
  - `consentimientoCDD` → `0` por defecto.
- **Soporte de custom fields en `MoodleSink.create_user`** y en `MoodleRepository.crear_usuario` para drivers API REST y moosh.
- **Soporte de custom fields en `update_user`/`actualizar_usuario`** para permitir actualizar `emailsigad` y otros campos personalizados.
- **Campo `id_sigad` en `MoodleUserRecord`** para extraer el custom field `IdSIGAD` del snapshot de Moodle.
- **Campo `email_sigad` en `MoodleUserRecord`** para extraer el custom field `emailsigad` del snapshot de Moodle.
- **Nuevos tests** (21): reintentos de cola, prioridad de informes, escape HTML, dry-run, reactivaciones, guard de colisión en renombres, guarda de SIGAD vacío, notificaciones del applier, fallback de desmatriculación y apellido con nombre incluido.

### Changed

- **Límite de emails consolidado**: `Settings.email_limit` es la única fuente (usa `MAX_EMAILS_DIARIOS` en `www`, 10 en otros entornos); eliminada la lógica duplicada en los repositorios.
- **Delta 5 (cambio de username/DNI/NIE)**: ahora se detecta cruzando por `IdSIGAD` y se omite si el username nuevo ya existe en Moodle (evita colisiones).
- **Delta 3 (cambio de email)**: ahora compara el email personal de SIGAD con el custom field `emailsigad` de Moodle. El email institucional (`documento@fpvirtualaragon.es`) del campo principal de Moodle no se sincroniza ni compara.
- **`SyncApplier._apply_email_changes`**: actualiza el custom field `emailsigad` mediante `update_user(customfields={...})` en lugar de modificar el `email` principal de Moodle.
- **`MoodleSink`**: nuevo método `unenrol_user_from_course` y aliases `suspend_user`/`reactivate_user`/`enrol_user_to_cohort` en los drivers API y moosh (antes el applier los llamaba y habrían fallado en ejecución real).
- **`SyncReport.to_markdown`**: incluye la sección de reactivaciones.
- **MoodleSource**: `BaseMoodleSource`, `APICourseBasedMoodleSource` y `APISnapshotMoodleSource` extraen `IdSIGAD` y `emailsigad` de los custom fields de Moodle.
- **Documentación actualizada**:
  - `docus/sync_analyzer.md`
  - `docus/AGENTS.md`
  - `docus/flujos.md`
  - `docus/tareas-y-roadmap.md`
  - `docus/sistema_testing.md`

### Fixed

- **Fallback de desmatriculación**: cuando `suspend_enrolment` no está disponible se usa `unenrol_user_from_course` (antes llamaba a `enrol_user_to_course`, rematriculando al alumno).
- **Apellido en el alta**: se construye desde `apellido1`/`apellido2` (antes con `replace` del nombre, que corrompía apellidos como "Marín" para "María").
- **Enlace al curso de ayuda** corregido a `id=654` (antes `id=2`) y etiqueta `<b>` sin cerrar en `nuevoUsuario.html`.
- **SQL interpolado** en `_find_removed_users`: los IDs protegidos pasan a consultarse desde una tabla DuckDB en lugar de un f-string.
- Robustez en `SyncAnalyzer` al cargar DataFrames con columnas totalmente nulas en DuckDB, asegurando tipos de columna (`string` para nombre/apellidos/email).

