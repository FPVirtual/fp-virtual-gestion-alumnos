# Changelog

## [Unreleased]

### Added

- **Custom fields en alta de usuarios**: al crear un usuario en Moodle se rellenan automáticamente los campos personalizados:
  - `IdSIGAD` → `idAlumno` de SIGAD.
  - `tipoDocumento` → `idTipoDocumento` de SIGAD.
  - `emailsigad` → email personal del JSON de SIGAD.
  - `consentimientoCDD` → `0` por defecto.
- **Soporte de custom fields en `MoodleSink.create_user`** y en `MoodleRepository.crear_usuario` para drivers API REST y moosh.
- **Soporte de custom fields en `update_user`/`actualizar_usuario`** para permitir actualizar `emailsigad` y otros campos personalizados.
- **Campo `id_sigad` en `MoodleUserRecord`** para extraer el custom field `IdSIGAD` del snapshot de Moodle.
- **Campo `email_sigad` en `MoodleUserRecord`** para extraer el custom field `emailsigad` del snapshot de Moodle.
- **Nuevos tests**:
  - `test_username_change_detected_by_idsigad`
  - `test_username_change_not_detected_when_idsigad_matches`
  - `test_moosh_crear_usuario_con_customfields`
  - `test_moosh_actualizar_usuario_con_customfields`

### Changed

- **Delta 5 (cambio de username/DNI/NIE)**: ahora se detecta cruzando por `IdSIGAD` en lugar de por coincidencia de email. Esto permite identificar correctamente a alumnos que cambian de documento manteniendo el mismo identificador de SIGAD.
- **Delta 3 (cambio de email)**: ahora compara el email personal de SIGAD con el custom field `emailsigad` de Moodle. El email institucional (`documento@fpvirtualaragon.es`) del campo principal de Moodle no se sincroniza ni compara.
- **`SyncApplier._apply_email_changes`**: actualiza el custom field `emailsigad` mediante `update_user(customfields={...})` en lugar de modificar el `email` principal de Moodle.
- **MoodleSource**: `BaseMoodleSource`, `APICourseBasedMoodleSource` y `APISnapshotMoodleSource` extraen `IdSIGAD` y `emailsigad` de los custom fields de Moodle.
- **Documentación actualizada**:
  - `docus/sync_analyzer.md`
  - `docus/AGENTS.md`
  - `docus/flujos.md`
  - `docus/tareas-y-roadmap.md`
  - `docus/sistema_testing.md`

### Fixed

- Robustez en `SyncAnalyzer` al cargar DataFrames vacíos en DuckDB, asegurando los tipos de columna correctos (`id_sigad` como entero, `email_sigad` como string).
