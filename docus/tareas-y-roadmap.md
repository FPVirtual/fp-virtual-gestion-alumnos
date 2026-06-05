# Tareas y Roadmap — v0.4.1

> **Rama:** `v0.3-estructura-paquete-con-logs`  
> **Versión actual:** `0.4.1`  
> **Tests:** `62/62 ✅`  
> **Zipapp:** `dist/gestion_alumnos.pyz ✅`

---

## Índice de Contenidos

- [Estado General](#estado-general)
- [Fase 0 — Análisis y Preparación](#fase-0--análisis-y-preparación)
- [Fase 1 — Infraestructura del Paquete](#fase-1--infraestructura-del-paquete)
- [Fase 2 — Core](#fase-2--core)
- [Fase 3 — Modelos Pydantic](#fase-3--modelos-pydantic)
- [Fase 4 — Repositorios](#fase-4--repositorios)
- [Fase 5 — Servicio de Gestión](#fase-5--servicio-de-gestión)
- [Fase 6 — Tests](#fase-6--tests)
- [Fase 7 — Zipapp y Distribución](#fase-7--zipapp-y-distribución)
- [Fase 8 — Documentación](#fase-8--documentación)
- [Principios de Diseño](#principios-de-diseño)
- [Próximos Pasos Sugeridos](#próximos-pasos-sugeridos)

---

## Estado General

| Fase | Estado | Tests |
|------|--------|-------|
| 0 — Análisis | ✅ Completa | — |
| 1 — Infraestructura | ✅ Completa | — |
| 2 — Core (logging, config, DI) | ✅ Completa | 9/9 |
| 3 — Modelos Pydantic | ✅ Completa | 10/10 |
| 4 — Repositorios | ✅ Completa | 6/6 SIGAD + 3/3 Moosh |
| 5 — Pipeline de sincronización | ✅ Completa | 6/6 SyncAnalyzer |
| 6 — Report logging | ✅ Completa | 6/6 ReportLogger |
| 7 — Cola de emails | ✅ Completa | 15/15 EmailQueue |
| 8 — Tests | ✅ Completa | 62/62 |
| 9 — Zipapp | ✅ Completa | Funcional |
| 10 — Documentación | ✅ Completa | — |

---

## Fase 0 — Análisis y Preparación ✅

| # | Tarea | Estado | Detalle |
|---|-------|--------|---------|
| 0.1 | Auditar `main.py` para identificar accesos directos a MySQL | ✅ | Identificados: `subprocess` con `mysql`, `pymysql`, variables `DB_HOST`, `DB_PASS` |
| 0.2 | Mapeo SQL → moosh / API REST | ✅ | Tabla de mapeo en documentación |
| 0.3 | Revisar `Config.py` para config mínima | ✅ | Eliminados campos BD; añadido `moodle_driver` |
| 0.4 | Revisar tests existentes | ✅ | Tests legacy no migrados; creados nuevos desde cero |
| 0.5 | Revisar código de v0.2 reutilizable | ✅ | `core/logging.py`, `core/exceptions.py`, `core/config.py`, `models_v2.py`, `protocols.py` |

---

## Fase 1 — Infraestructura del Paquete ✅

| # | Tarea | Estado | Detalle |
|---|-------|--------|---------|
| 1.1 | Crear `pyproject.toml` con Poetry | ✅ | Poetry, pytest, ruff, mypy configurados |
| 1.2 | Crear estructura de directorios | ✅ | `gestion_alumnos/{core,models,repositories,services,utils,templates}` |
| 1.3 | Crear `__init__.py` con `__version__` | ✅ | Exporta `Settings`, `DIContainer`, `get_logger` |
| 1.4 | Crear `__main__.py` | ✅ | `python -m gestion_alumnos` |
| 1.5 | Mover templates HTML al paquete | ✅ | 5 templates en `gestion_alumnos/templates/` |
| 1.6 | Configurar `.gitignore` | ✅ | `.venv/`, `dist/`, `__pycache__`, `.env` |

---

## Fase 2 — Core ✅

| # | Tarea | Estado | Detalle |
|---|-------|--------|---------|
| 2.1 | `core/logging.py` (v0.2) | ✅ | structlog + nivel MARKDOWN (25) |
| 2.2 | `core/exceptions.py` (v0.2) | ✅ | `GestionAlumnosError`, `APIError`, `MoodleError`, `EmailError` |
| 2.3 | `core/config.py` (adaptado) | ✅ | Pydantic Settings sin BD, con `moodle_driver: Literal["moosh", "api"]` |
| 2.4 | `core/container.py` (adaptado) | ✅ | DI Container con `override_*` para tests |
| 2.5 | `core/__init__.py` | ✅ | Exports convenientes |

---

## Fase 3 — Modelos Pydantic ✅

| # | Tarea | Estado | Tests |
|---|-------|--------|-------|
| 3.1 | Dividir `models_v2.py` en módulos | ✅ | `alumno.py`, `centro.py`, `ciclo.py`, `modulo.py`, `registro.py` |
| 3.2 | Validar aliases JSON | ✅ | `populate_by_name=True` |
| 3.3 | Propiedades calculadas | ✅ | `username_moodle`, `email_institucional`, `nombre_completo` |
| 3.4 | `__str__` en cada modelo | ✅ | 10/10 tests pasan |

---

## Fase 4 — Repositorios ✅

| # | Tarea | Estado | Tests |
|---|-------|--------|-------|
| 4.1 | `protocols.py` (v0.2) | ✅ | `EstudianteRepository`, `MoodleRepository`, `EmailRepository` |
| 4.2 | `sigad_repository.py` | ✅ | 6/6 tests: API, modo test, reintentos, credenciales, búsqueda, estructura |
| 4.3 | `moodle_moosh_repository.py` | ✅ | 3/3 tests: existe, crear, error |
| 4.4 | `moodle_api_repository.py` | ✅ | Implementado (pendiente tests específicos) |
| 4.5 | `email_repository.py` | ✅ | SMTP + templates + límites diarios |
| 4.6 | Conformidad de Protocols | ✅ | `isinstance` verificado en `test_core_container.py` |

### Mapeo de operaciones Moodle

| Operación | Protocolo | Moosh | API REST |
|-----------|-----------|-------|----------|
| Listar usuarios | `obtener_todos_usuarios()` | `moosh user-list` | `core_user_get_users` |
| Obtener usuario | `obtener_por_username()` | `moosh user-get` | `core_user_get_users_by_field` |
| Crear usuario | `crear_usuario()` | `moosh user-create` | `core_user_create_users` |
| Actualizar usuario | `actualizar_usuario()` | `moosh user-mod` | `core_user_update_users` |
| Suspender usuario | `suspender_usuario()` | `moosh user-mod --suspend 1` | `core_user_update_users` (suspend=1) |
| Reactivar usuario | `reactivar_usuario()` | `moosh user-mod --suspend 0` | `core_user_update_users` (suspend=0) |
| Matricular en curso | `matricular_en_curso()` | `moosh course-enrol` | `enrol_manual_enrol_users` |
| Desmatricular de curso | `desmatricular_de_curso()` | `moosh course-unenrol` | `enrol_manual_unenrol_users` |
| Matricular en cohorte | `matricular_en_cohorte()` | `moosh cohort-enrol` | `core_cohort_add_cohort_members` |
| Obtener matrículas | `obtener_matriculas()` | `moosh course-list-enrolled` | `core_enrol_get_users_courses` |

---

## Fase 5 — Pipeline de Sincronización ✅

| # | Tarea | Estado | Detalle |
|---|-------|--------|---------|
| 5.1 | `SyncOrchestrator` | ✅ | Orquesta 4 capas: SIGAD → MoodleSource → SyncAnalyzer → SyncApplier |
| 5.2 | `SyncAnalyzer` (DuckDB) | ✅ | 7 deltas detectados vía SQL JOINs |
| 5.3 | `SyncApplier` | ✅ | Aplica cambios en MoodleSink con manejo de errores |
| 5.4 | Protocolos MoodleSource / MoodleSink | ✅ | Separación lectura/escritura |
| 5.5 | `cli.py` con argparse | ✅ | `sync`, `report`, `extract`, `process-emails`, `--apply`, `--driver`, `--source-strategy` |

## Fase 6 — Report Logging ✅

| # | Tarea | Estado | Detalle |
|---|-------|--------|---------|
| 6.1 | `ReportLogger` | ✅ | Escribe informes `.md` con timestamp en `logs/` |
| 6.2 | `SyncReport.to_markdown()` | ✅ | Resumen + detalle de cada delta |
| 6.3 | Integración en `SyncOrchestrator` | ✅ | Informe automático al finalizar sync |
| 6.4 | Tests `test_core_logging.py` | ✅ | 6/6 |

## Fase 7 — Cola de Emails ✅

| # | Tarea | Estado | Detalle |
|---|-------|--------|---------|
| 7.1 | `EmailJob` (modelo) | ✅ | Serialización CSV con Pydantic |
| 7.2 | `EmailQueueRepository` | ✅ | Implementa `EmailRepository` encolando en CSV |
| 7.3 | `EmailQueueProcessor` | ✅ | Lee CSV y envía por SMTP respetando límites |
| 7.4 | `email_mode` en config | ✅ | `direct` o `queue` |
| 7.5 | Comando CLI `process-emails` | ✅ | `python -m gestion_alumnos process-emails` |
| 7.6 | Tests `test_email_queue.py` | ✅ | 15/15 |

---

## Fase 8 — Tests ✅

| # | Tarea | Estado | Tests |
|---|-------|--------|-------|
| 8.1 | `pytest` en `pyproject.toml` | ✅ | Configurado |
| 8.2 | `tests/conftest.py` | ✅ | Fixtures: `settings_test`, `sample_*`, `mock_moosh` |
| 8.3 | Tests `core/config.py` | ✅ | `test_core_config.py` — 3/3 |
| 8.4 | Tests `core/container.py` | ✅ | `test_core_container.py` — 3/3 |
| 8.5 | Tests `core/logging.py` | ✅ | `test_core_logging.py` — 6/6 |
| 8.6 | Tests `moodle_moosh_repository.py` | ✅ | `test_repositories_moosh.py` — 3/3 |
| 8.7 | Tests `moodle_api_repository.py` | ⬜ | Pendiente |
| 8.8 | Tests `sigad_repository.py` | ✅ | `test_repositories_sigad.py` — 6/6 |
| 8.9 | Tests `email_repository.py` | ⬜ | Pendiente |
| 8.10 | Tests `email_queue` | ✅ | `test_email_queue.py` — 15/15 |
| 8.11 | Tests `sync_analyzer.py` | ✅ | `test_sync_analyzer.py` — 6/6 |
| 8.12 | Tests conformidad Protocols | ✅ | Verificado en `test_core_container.py` |

**Resultado: 62/62 tests pasan** ✅

```bash
pytest tests/ -v
```

---

## Fase 9 — Zipapp y Distribución ✅

| # | Tarea | Estado | Detalle |
|---|-------|--------|---------|
| 7.1 | Verificar `python -m zipapp` | ✅ | Funciona |
| 7.2 | `scripts/build_zipapp.py` | ✅ | Automatizado |
| 7.3 | Probar zipapp `--help` | ✅ | `python dist/gestion_alumnos.pyz --help` |
| 7.4 | Documentar despliegue | ✅ | En README.md |
| 7.5 | `Dockerfile` | ❌ Descartado | Se movió a `archive/`; el despliegue es via zipapp, no imagen Docker |

### Generar y usar zipapp

```bash
# Generar
python scripts/build_zipapp.py
# → dist/gestion_alumnos.pyz (79.8 KB)

# Ejecutar
python dist/gestion_alumnos.pyz sync --driver moosh --env-file .env

# En contenedor Moodle
docker cp dist/gestion_alumnos.pyz moodle:/opt/
docker exec moodle python3 /opt/gestion_alumnos.pyz sync
```

---

## Fase 10 — Documentación ✅

| # | Tarea | Estado | Detalle |
|---|-------|--------|---------|
| 10.1 | `README.md` | ✅ | Instalación, uso, arquitectura, zipapp, email queue |
| 10.2 | `docus/AGENTS.md` | ✅ | Convenciones, estructura, DI, Protocols |
| 10.3 | `docus/flujos.md` | ✅ | Diagramas Mermaid de todos los flujos |
| 10.4 | `docus/sync_analyzer.md` | ✅ | Análisis de deltas con queries SQL y ejemplos |
| 10.5 | `docus/tareas-y-roadmap.md` | ✅ | Estado de fases y próximos pasos |
| 10.6 | `.env.example` | ✅ | Sin credenciales BD, con `MOODLE_DRIVER` y `EMAIL_MODE` |
| 10.7 | Limpiar código legacy | ✅ | `main.py`, `Util.py`, `Conexion.py`, `classes/` y `templates/` raíz movidos a `archive/` |
| 10.8 | Tag `v0.4.1` | ⬜ | Pendiente release |

---

## Principios de Diseño

1. **Moodle es una abstracción.** `MoodleRepository` Protocol con dos implementaciones.
2. **Cero SQL directo.** Ni `pymysql`, ni comandos `mysql`.
3. **Logging estructurado con structlog.** Nivel MARKDOWN (25) para informes.
4. **Configuración por Pydantic Settings.** Validación automática.
5. **Inyección de Dependencias.** Container resuelve implementaciones según config.
6. **Paquete autocontenido.** Zipapp funciona con Python 3.10+.
7. **Tests con mocks.** Cada repositorio testeado aisladamente.
8. **Idioma español.** Todo el código y documentación.

---

## Próximos Pasos Sugeridos

1. **Desplegar plugin PHP** `local_fparagon` en Moodle (producción + preproducción)
2. **Tests de integración** para `APICourseBasedMoodleSource` y `APISnapshotMoodleSource`
3. **Tests end-to-end** del `SyncOrchestrator` con mocks completos
4. **Mejorar `SyncApplier`** con batching de matrículas y reintentos
5. ~~**Generar informes Markdown**~~ ✅ Completado (`ReportLogger`)
6. ~~**Cola de emails en CSV**~~ ✅ Completado (`EmailQueueRepository` + `EmailQueueProcessor`)
7. **Tag `v0.4.1`** y merge a `main`

---

**Última actualización:** Junio 2026  
**Commit:** limpieza de código legacy + requirements.txt
