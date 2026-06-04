# Tareas y Roadmap — v0.3 Estructura Paquete con Logs

> **Rama:** `v0.3-estructura-paquete-con-logs`  
> **Objetivo:** Reestructurar el proyecto como paquete Python con Poetry, eliminar dependencia directa a MySQL, y permitir generar un `zipapp` para despliegue directo en el contenedor Moodle.  
> **Principio clave:** El servicio de Moodle es una abstracción (`MoodleRepository` Protocol) con dos implementaciones intercambiables: **moosh** (ejecución local/contenedor) y **API REST** (ejecución remota).

---

## Fase 0 — Análisis y Preparación

| # | Tarea | Estado | Detalle |
|---|-------|--------|---------|
| 0.1 | Auditar `main.py` para identificar todos los puntos donde se accede directamente a MySQL | ⬜ | Buscar `subprocess` con `mysql`, `pymysql`, `DB_HOST`, `DB_PASS`, etc. |
| 0.2 | Listar todas las operaciones que hacen SQL directo y su equivalente en `moosh` o API REST | ⬜ | Crear tabla de mapeo: operación SQL → comando moosh / endpoint API |
| 0.3 | Revisar `Config.py` / `Config-sample.py` para definir configuración mínima necesaria | ⬜ | Identificar variables que siguen siendo necesarias sin MySQL directo |
| 0.4 | Revisar `tests/` existentes para entender qué funcionalidad ya está testeada | ⬜ | Decidir qué tests se migran, qué se descarta y qué se reescribe |
| 0.5 | **Revisar código de v0.2 para identificar componentes reutilizables** | ⬜ | `core/logging.py`, `core/exceptions.py`, `core/config.py`, `models_v2.py`, `repositories/protocols.py` |

---

## Fase 1 — Infraestructura del Paquete (Poetry + Estructura)

| # | Tarea | Estado | Detalle |
|---|-------|--------|---------|
| 1.1 | Crear `pyproject.toml` con Poetry | ⬜ | Definir metadata, dependencias mínimas, scripts de entrada, y configuración de build para zipapp |
| 1.2 | Crear estructura de directorios del paquete `gestion_alumnos/` | ⬜ | Ver estructura propuesta abajo |
| 1.3 | Crear `__init__.py` con `__version__` | ⬜ | Exportar API pública mínima |
| 1.4 | Crear `__main__.py` para ejecutar como `python -m gestion_alumnos` | ⬜ | Punto de entrada cuando se usa zipapp |
| 1.5 | Mover/Adaptar templates HTML al paquete (`gestion_alumnos/templates/`) | ⬜ | Usar `importlib.resources` para acceder a templates empaquetados |
| 1.6 | Configurar `.gitignore` para entornos Poetry (`dist/`, `.venv/`, `*.egg-info`, `__pycache__`) | ⬜ | Actualizar `.gitignore` existente |

### Estructura propuesta del paquete

```
gestion_alumnos/
├── __init__.py              # __version__, exports públicos
├── __main__.py              # python -m gestion_alumnos
├── cli.py                   # argparse: sync, extract, report
├── core/                    # 🆕 Componentes fundamentales (traídos de v0.2)
│   ├── __init__.py
│   ├── config.py            # Pydantic Settings centralizada
│   ├── container.py         # DI Container para inyectar implementaciones
│   ├── exceptions.py        # Jerarquía de excepciones personalizadas
│   └── logging.py           # Logging estructurado con structlog + nivel MARKDOWN
├── models/                  # Modelos Pydantic (basados en v0.2)
│   ├── __init__.py
│   ├── alumno.py
│   ├── centro.py
│   ├── ciclo.py
│   ├── modulo.py
│   └── registro.py
├── repositories/            # 🆕 Repository Pattern (basado en v0.2)
│   ├── __init__.py
│   ├── protocols.py         # Protocols: EstudianteRepository, MoodleRepository, EmailRepository
│   ├── sigad_repository.py  # Implementación API REST SIGAD
│   ├── moodle_moosh_repository.py   # Implementación Moodle via moosh
│   ├── moodle_api_repository.py     # Implementación Moodle via API REST
│   └── email_repository.py  # Implementación SMTP
├── services/                # Lógica de negocio
│   ├── __init__.py
│   └── gestion_service.py   # Orquestador del flujo completo con DI
├── templates/               # HTML empaquetados (importlib.resources)
│   ├── haFalladoElInforme.html
│   ├── informeAutomatizado.html
│   ├── matriculasAnadidas.html
│   ├── nombreUsuarioActualizado.html
│   └── nuevoUsuario.html
└── utils/
    ├── __init__.py
    └── helpers.py           # Funciones puras (fechas, conversiones)
```

---

## Fase 2 — Core: Logging, Config, Excepciones (reutilizar v0.2)

| # | Tarea | Estado | Detalle |
|---|-------|--------|---------|
| 2.1 | **Traer `core/logging.py` desde v0.2** | ⬜ | structlog + nivel MARKDOWN (25) para informes |
| 2.2 | **Traer `core/exceptions.py` desde v0.2** | ⬜ | `GestionAlumnosError`, `APIError`, `MoodleError`, `EmailError`, etc. |
| 2.3 | **Traer y adaptar `core/config.py` desde v0.2** | ⬜ | Pydantic Settings, eliminar campos de BD MySQL, añadir campo `moodle_driver: Literal["moosh", "api"]` |
| 2.4 | **Traer `core/container.py` desde v0.2** | ⬜ | DI Container que resuelve `MoodleRepository` según `config.moodle_driver` |
| 2.5 | Crear `core/__init__.py` con exports convenientes | ⬜ | `get_settings()`, `get_container()`, `get_logger()` |

### Configuración añadida para v0.3

```python
class Settings(BaseSettings):
    # ... campos existentes de v0.2 ...
    
    # 🆕 Driver de Moodle (determina qué implementación se inyecta)
    moodle_driver: Literal["moosh", "api"] = Field(
        default="moosh",
        description="Driver para operaciones Moodle: 'moosh' (local) o 'api' (remoto)"
    )
    
    # 🆕 Configuración API REST de Moodle (solo si moodle_driver == "api")
    moodle_api_url: str | None = Field(
        default=None,
        description="URL base de la API REST de Moodle"
    )
    moodle_api_token: str | None = Field(
        default=None,
        description="Token de la API REST de Moodle"
    )
    
    # 🆕 Configuración moosh (solo si moodle_driver == "moosh")
    moosh_path: str = Field(
        default="moosh",
        description="Ruta al ejecutable moosh"
    )
    docker_container: str | None = Field(
        default=None,
        description="Nombre del contenedor Docker (si moosh está dentro de un contenedor)"
    )
```

---

## Fase 3 — Modelos (reutilizar/adaptar v0.2)

| # | Tarea | Estado | Detalle |
|---|-------|--------|---------|
| 3.1 | **Traer `models_v2.py` desde v0.2** y dividir en módulos | ⬜ | `Alumno`, `Centro`, `Ciclo`, `Modulo`, `Registro` como Pydantic models |
| 3.2 | Validar que los aliases JSON (`idAlumno`, `codigoCentro`, etc.) funcionan | ⬜ | `populate_by_name=True` |
| 3.3 | Añadir propiedades calculadas: `username_moodle`, `email_institucional`, `nombre_completo` | ⬜ | |
| 3.4 | Añadir `__str__` a cada modelo | ⬜ | |

---

## Fase 4 — Repositorios: Protocols + Implementaciones

| # | Tarea | Estado | Detalle |
|---|-------|--------|---------|
| 4.1 | **Traer `repositories/protocols.py` desde v0.2** | ⬜ | `EstudianteRepository`, `AlumnoRepository`, `MoodleRepository`, `EmailRepository` |
| 4.2 | **Crear `repositories/sigad_repository.py`** | ⬜ | Implementación de `EstudianteRepository` vía API REST SIGAD (basado en `Conexion.py` / `api_client.py`) |
| 4.3 | **Crear `repositories/moodle_moosh_repository.py`** | ⬜ | Implementación de `MoodleRepository` usando `subprocess.run(["moosh", ...])` |
| 4.4 | **Crear `repositories/moodle_api_repository.py`** | ⬜ | Implementación de `MoodleRepository` usando `requests` contra API REST de Moodle |
| 4.5 | **Crear `repositories/email_repository.py`** | ⬜ | Implementación de `EmailRepository` con SMTP + templates + límites diarios |
| 4.6 | Verificar que ambas implementaciones de `MoodleRepository` cumplen el mismo Protocol | ⬜ | Tests de conformidad |

### Mapeo de operaciones Moodle

| Operación de negocio | Protocolo (`MoodleRepository`) | Moosh | API REST |
|---------------------|-------------------------------|-------|----------|
| Listar usuarios | `obtener_todos_usuarios()` | `moosh user-list` | `core_user_get_users` |
| Obtener usuario | `obtener_por_username()` | `moosh user-get` | `core_user_get_users_by_field` |
| Crear usuario | `crear_usuario()` | `moosh user-create` | `core_user_create_users` |
| Actualizar usuario | `actualizar_usuario()` | `moosh user-mod` | `core_user_update_users` |
| Suspender usuario | `suspender_usuario()` | `moosh user-mod --suspend 1` | `core_user_update_users` (suspend=1) |
| Reactivar usuario | `reactivar_usuario()` | `moosh user-mod --suspend 0` | `core_user_update_users` (suspend=0) |
| Listar cursos | `obtener_cursos()` | `moosh course-list` | `core_course_get_courses` |
| Matricular en curso | `matricular_en_curso()` | `moosh course-enrol` | `enrol_manual_enrol_users` |
| Desmatricular de curso | `desmatricular_de_curso()` | `moosh course-unenrol` | `enrol_manual_unenrol_users` |
| Listar cohortes | `obtener_cohortes()` | `moosh cohort-list` | `core_cohort_get_cohorts` |
| Añadir a cohorte | `matricular_en_cohorte()` | `moosh cohort-enrol` | `core_cohort_add_cohort_members` |
| Obtener matrículas | `obtener_matriculas()` | `moosh course-list-enrolled` | `core_enrol_get_users_courses` |

---

## Fase 5 — Servicio de Gestión (Orquestador)

| # | Tarea | Estado | Detalle |
|---|-------|--------|---------|
| 5.1 | **Crear `services/gestion_service.py`** | ⬜ | Orquestador puro que recibe repositorios inyectados vía DI Container |
| 5.2 | Implementar flujo: descargar SIGAD → parsear → comparar con Moodle | ⬜ | |
| 5.3 | Implementar sub-flujo: crear usuarios nuevos | ⬜ | Generar password, email institucional, notificar |
| 5.4 | Implementar sub-flujo: matricular en cursos según módulos SIGAD | ⬜ | |
| 5.5 | Implementar sub-flujo: suspender bajas (Moodle \\ SIGAD) | ⬜ | |
| 5.6 | Implementar sub-flujo: reactivar usuarios que vuelven | ⬜ | |
| 5.7 | Implementar sub-flujo: actualizar emails/username cambiados | ⬜ | |
| 5.8 | Implementar sub-flujo: limpieza de agosto | ⬜ | Eliminar matrículas suspendidas permanentemente |
| 5.9 | Implementar generación de informe Markdown + CSV | ⬜ | Usar logger.markdown() |
| 5.10 | Implementar envío de emails de notificación | ⬜ | Con límite diario |
| 5.11 | Crear `cli.py` con argparse | ⬜ | Modos: `sync`, `extract`, `report`, `--driver moosh|api` |
| 5.12 | Crear `__main__.py` | ⬜ | `python -m gestion_alumnos sync --driver moosh` |

---

## Fase 6 — Tests

| # | Tarea | Estado | Detalle |
|---|-------|--------|---------|
| 6.1 | Configurar `pytest` en `pyproject.toml` | ⬜ | `[tool.pytest.ini_options]` |
| 6.2 | Crear `tests/conftest.py` con fixtures base | ⬜ | Config de test, mocks de moosh, mocks de API Moodle, datos JSON |
| 6.3 | Tests para `core/config.py` | ⬜ | Monkeypatch de `os.environ` |
| 6.4 | Tests para `core/container.py` | ⬜ | Verificar que resuelve `MoodleRepository` según `moodle_driver` |
| 6.5 | Tests unitarios para `repositories/moodle_moosh_repository.py` | ⬜ | Mock de `subprocess.run` |
| 6.6 | Tests unitarios para `repositories/moodle_api_repository.py` | ⬜ | Mock de `requests` |
| 6.7 | Tests unitarios para `repositories/sigad_repository.py` | ⬜ | Mock de `requests` |
| 6.8 | Tests unitarios para `repositories/email_repository.py` | ⬜ | Mock de `smtplib` |
| 6.9 | Tests de integración para `services/gestion_service.py` | ⬜ | Mocks de todos los repos, flujo completo |
| 6.10 | Tests de conformidad de Protocols | ⬜ | `isinstance(repo, MoodleRepository)` para ambas implementaciones |

---

## Fase 7 — Zipapp y Distribución

| # | Tarea | Estado | Detalle |
|---|-------|--------|---------|
| 7.1 | Verificar que `python -m zipapp gestion_alumnos/` funciona | ⬜ | `python3 -m zipapp gestion_alumnos -p "/usr/bin/env python3" -o dist/gestion_alumnos.pyz` |
| 7.2 | Crear `scripts/build_zipapp.py` para automatizar | ⬜ | Incluir templates y recursos |
| 7.3 | Probar zipapp con `--help` | ⬜ | Verificar carga de templates via `importlib.resources` |
| 7.4 | Documentar despliegue en contenedor Moodle | ⬜ | `docker cp` + `docker exec` |
| 7.5 | Opcional: `Dockerfile` mínimo de validación | ⬜ | |

---

## Fase 8 — Documentación y Cierre

| # | Tarea | Estado | Detalle |
|---|-------|--------|---------|
| 8.1 | Actualizar `README.md` | ⬜ | Instalación Poetry, uso zipapp, modo moosh vs API |
| 8.2 | Actualizar/completar `AGENTS.md` | ⬜ | Convenciones, estructura, uso de DI y Protocols |
| 8.3 | Crear `.env.example` actualizado | ⬜ | Sin credenciales BD, con `MOODLE_DRIVER` |
| 8.4 | Limpiar código legacy no migrado | ⬜ | `main.py` raíz, `Util.py`, `Conexion.py`, `classes/` raíz |
| 8.5 | Commit final y tag `v0.3.0` | ⬜ | |

---

## Principios de Diseño para esta Versión

1. **Moodle es una abstracción.** `MoodleRepository` Protocol con dos implementaciones (`MooshMoodleRepository`, `APIMoodleRepository`). El orquestador no sabe cuál usa.
2. **Cero SQL directo.** Ni `pymysql`, ni comandos `mysql`, ni SQL embebido.
3. **Logging estructurado con structlog.** Traído de v0.2. Nivel MARKDOWN (25) para informes.
4. **Configuración por Pydantic Settings.** Traído de v0.2. Validación automática.
5. **Inyección de Dependencias.** Traído de v0.2. Container resuelve implementaciones según config.
6. **El paquete debe ser autocontenido.** Un `zipapp` funciona con solo Python 3.10+.
7. **Templates empaquetados.** `importlib.resources` para leer HTML desde dentro del zipapp.
8. **Tests con mocks.** Cada implementación de repositorio se testea con mocks.
9. **Idioma español.** Código, comentarios, docstrings.

---

## Notas Técnicas

### Cambio de driver en runtime
```python
from gestion_alumnos.core.container import create_container
from gestion_alumnos.repositories.moodle_api_repository import APIMoodleRepository

container = create_container()
container.override_moodle_repository(APIMoodleRepository())

service = container.gestion_service()
```

### Zipapp y recursos estáticos
```python
from importlib import resources
template = resources.files("gestion_alumnos.templates") / "nuevoUsuario.html"
```

### Moosh dentro del contenedor
Si el script corre **dentro** del contenedor Moodle, `moosh` está en `$PATH` y `docker_container` es `None`.
Si corre **fuera**, `docker_container` indica el contenedor y los comandos se prefijan con `docker exec {container} moosh ...`.

### API REST de Moodle
Documentación de referencia: `https://docs.moodle.org/dev/Web_service_API_functions`
Funciones clave: `core_user_get_users`, `core_user_create_users`, `core_user_update_users`, `enrol_manual_enrol_users`, `core_course_get_courses`.
