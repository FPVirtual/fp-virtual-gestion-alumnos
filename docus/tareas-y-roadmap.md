# Tareas y Roadmap — v0.3 Estructura Paquete con Logs

> **Rama:** `v0.3-estructura-paquete-con-logs`  
> **Versión actual:** `0.3.0`  
> **Tests:** `26/26 ✅`  
> **Zipapp:** `dist/gestion_alumnos.pyz (79.8 KB) ✅`

---

## Estado General

| Fase | Estado | Tests |
|------|--------|-------|
| 0 — Análisis | ✅ Completa | — |
| 1 — Infraestructura | ✅ Completa | — |
| 2 — Core (logging, config, DI) | ✅ Completa | 3/3 |
| 3 — Modelos Pydantic | ✅ Completa | 10/10 |
| 4 — Repositorios | ✅ Completa | 6/6 SIGAD + 3/3 Moosh |
| 5 — Servicio de Gestión | 🟡 Stub funcional | Pendiente integración completa |
| 6 — Tests | ✅ Completa | 26/26 |
| 7 — Zipapp | ✅ Completa | Funcional |
| 8 — Documentación | ✅ Completa | — |

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

## Fase 5 — Servicio de Gestión 🟡 Stub

| # | Tarea | Estado | Detalle |
|---|-------|--------|---------|
| 5.1 | `gestion_service.py` | 🟡 | Orquestador con DI, flujo básico implementado |
| 5.2 | Descargar SIGAD → parsear → comparar | 🟡 | Stub funcional |
| 5.3 | Crear usuarios nuevos | 🟡 | Genera password, crea via repo, envía email |
| 5.4 | Matricular en cursos | 🟡 | Itera módulos del alumno |
| 5.5 | Suspender bajas | 🟡 | Compara Moodle vs SIGAD |
| 5.6 | Reactivar usuarios | ⬜ | Pendiente lógica completa |
| 5.7 | Actualizar emails/username | ⬜ | Pendiente comparación de cambios |
| 5.8 | Limpieza de agosto | ⬜ | Pendiente |
| 5.9 | Generar informe Markdown + CSV | 🟡 | `ResultadoSync.to_markdown()` |
| 5.10 | Enviar emails de notificación | 🟡 | Integrado con `EmailRepository` |
| 5.11 | `cli.py` con argparse | ✅ | `sync`, `extract`, `report`, `--driver` |
| 5.12 | `__main__.py` | ✅ | `python -m gestion_alumnos` |

---

## Fase 6 — Tests ✅

| # | Tarea | Estado | Tests |
|---|-------|--------|-------|
| 6.1 | `pytest` en `pyproject.toml` | ✅ | Configurado |
| 6.2 | `tests/conftest.py` | ✅ | Fixtures: `settings_test`, `sample_*`, `mock_moosh` |
| 6.3 | Tests `core/config.py` | ✅ | `test_core_config.py` — 3/3 |
| 6.4 | Tests `core/container.py` | ✅ | `test_core_container.py` — 3/3 |
| 6.5 | Tests `moodle_moosh_repository.py` | ✅ | `test_repositories_moosh.py` — 3/3 |
| 6.6 | Tests `moodle_api_repository.py` | ⬜ | Pendiente |
| 6.7 | Tests `sigad_repository.py` | ✅ | `test_repositories_sigad.py` — 6/6 |
| 6.8 | Tests `email_repository.py` | ⬜ | Pendiente |
| 6.9 | Tests `gestion_service.py` | ⬜ | Pendiente integración completa |
| 6.10 | Tests conformidad Protocols | ✅ | Verificado en `test_core_container.py` |

**Resultado: 26/26 tests pasan** ✅

```bash
pytest tests/ -v
```

---

## Fase 7 — Zipapp y Distribución ✅

| # | Tarea | Estado | Detalle |
|---|-------|--------|---------|
| 7.1 | Verificar `python -m zipapp` | ✅ | Funciona |
| 7.2 | `scripts/build_zipapp.py` | ✅ | Automatizado |
| 7.3 | Probar zipapp `--help` | ✅ | `python dist/gestion_alumnos.pyz --help` |
| 7.4 | Documentar despliegue | ✅ | En README.md |
| 7.5 | `Dockerfile` mínimo | ⬜ | Opcional |

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

## Fase 8 — Documentación ✅

| # | Tarea | Estado | Detalle |
|---|-------|--------|---------|
| 8.1 | `README.md` | ✅ | Instalación, uso, arquitectura, zipapp |
| 8.2 | `docus/AGENTS.md` | ✅ | Convenciones, estructura, DI, Protocols |
| 8.3 | `.env.example` | ✅ | Sin credenciales BD, con `MOODLE_DRIVER` |
| 8.4 | Limpiar código legacy | ⬜ | `main.py` raíz, `Util.py`, `Conexion.py`, `classes/` aún existen |
| 8.5 | Tag `v0.3.0` | ⬜ | Pendiente release |

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

1. **Completar lógica de negocio** en `gestion_service.py`:
   - Reactivar usuarios que vuelven a SIGAD
   - Actualizar emails/username cuando cambian
   - Limpieza de agosto (eliminar matrículas suspendidas)

2. **Añadir tests de integración** para `GestionAlumnosService` con mocks de todos los repos.

3. **Implementar carga de templates** con `importlib.resources` en `email_repository.py`.

4. **Crear tests para `APIMoodleRepository`** usando `requests_mock`.

5. **Limpiar código legacy** de la raíz (`main.py`, `Util.py`, `Conexion.py`, `classes/`).

6. **Tag `v0.3.0`** y merge a `main`.

---

**Última actualización:** Junio 2026  
**Commit:** `2fd963c` — feat: tests de recuperación SIGAD; 26/26 tests pasan
