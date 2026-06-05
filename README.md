# Gestion Alumnos v0.4.0

Aplicación para la gestión automática del alumnado en **CampusDigitalFP** (Moodle).

## Estado del Proyecto

| Métrica | Valor |
|---------|-------|
| Versión | `0.4.0` |
| Tests | **32/32 ✅** |
| Python | `3.10+` |
| Distribución | Poetry + zipapp (`.pyz`) |

## Características v0.4

- **Arquitectura modular en 4 capas**:
  1. Extracción SIGAD (API REST real)
  2. Extracción Moodle (`MoodleSource`) — API por cursos o plugin PHP snapshot
  3. Análisis (`SyncAnalyzer`) — DuckDB in-memory para comparar datasets
  4. Carga Moodle (`MoodleSink`) — API REST o moosh
- **Dual driver Moodle**: `moosh` (local/contenedor) o **API REST** (remoto)
- **Dual estrategia de extracción**: `api-course-based` (itera cursos) o `api-snapshot` (plugin PHP)
- **Dry-run por defecto**: `sync` solo analiza; `sync --apply` escribe en Moodle
- **Usuarios protegidos desde CSV**: configurable por entorno
- **Zero SQL directo**
- **Tests con mocks** (requests-mock, monkeypatch)

## Arquitectura

```
gestion_alumnos/
├── core/                  # Config, logging, exceptions, DI container
├── models/                # Pydantic models (Alumno, Registro, MoodleSnapshot, SyncReport)
├── repositories/          # Protocols + implementations
│   ├── moodle_sources/    # MoodleSource implementations (solo lectura)
│   │   ├── api_course_based_source.py
│   │   └── api_snapshot_source.py
│   ├── sigad_repository.py
│   ├── moodle_api_repository.py
│   ├── moodle_moosh_repository.py
│   └── email_repository.py
├── services/              # SyncAnalyzer, SyncApplier, SyncOrchestrator
└── templates/             # HTML empaquetados

moodle_plugin/             # Plugin PHP local_fparagon (para extracción snapshot)
archive/                   # Código legacy v0.2
```

> **Nota:** El código procedural legacy de la v0.2 ha sido movido a `archive/`. El ejecutable actual es el paquete `gestion_alumnos`.

### Capas del sistema

```
┌─────────────────────────────────────────────────────────────┐
│                        SyncOrchestrator                      │
└─────────────────────────────────────────────────────────────┘
         │              │                │              │
         ▼              ▼                ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   SIGAD      │ │ MoodleSource │ │ SyncAnalyzer │ │ MoodleSink   │
│ Repository   │ │ (abstracto)  │ │   (DuckDB)   │ │ (abstracto)  │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

### Dual Driver Moodle (Sink)

El acceso a Moodle se abstrae mediante `MoodleSink`:

| Driver | Uso | Implementación |
|--------|-----|----------------|
| `moosh` | Script dentro del contenedor Moodle | `MooshMoodleRepository` |
| `api` | Script remoto vía API REST | `APIMoodleRepository` |

```python
from gestion_alumnos.core.container import get_container

container = get_container()
orchestrator = container.sync_orchestrator(dry_run=True)
report = orchestrator.run()
```

### Dual Estrategia de Extracción (Source)

```python
# Opción A: iterar cursos (~1000 llamadas API)
export MOODLE_SOURCE_STRATEGY=api-course-based

# Opción B: plugin PHP (1 llamada, requiere despliegue)
export MOODLE_SOURCE_STRATEGY=api-snapshot
```

## Instalación

```bash
# Con Poetry (recomendado)
pip install poetry
poetry install

# O con pip
pip install -r requirements.txt
```

## Configuración

```bash
cp .env.example .env
# Editar .env con tus credenciales
```

### Variables clave

```bash
# Driver: moosh (local) o api (remoto)
MOODLE_DRIVER=moosh

# Estrategia de extracción
MOODLE_SOURCE_STRATEGY=api-course-based

# Moosh (si driver=moosh)
MOOSH_PATH=moosh
DOCKER_CONTAINER=moodle_app

# API REST (si driver=api)
MOODLE_API_URL=https://moodle.fpvirtualaragon.es/webservice/rest/server.php
MOODLE_API_TOKEN=xxx

# SIGAD
API_USER=xxx
API_PASSWORD=xxx

# SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=xxx
SMTP_PASSWORD=xxx

# Usuarios protegidos (configurable por entorno)
USUARIOS_PROTEGIDOS_CSV=gestion_alumnos/data/usuarios_protegidos.csv
```

## Uso

### Desarrollo

```bash
# Análisis dry-run (por defecto)
poetry run python -m gestion_alumnos sync --driver moosh

# Aplicar cambios reales
poetry run python -m gestion_alumnos sync --driver moosh --apply

# Generar informe
poetry run python -m gestion_alumnos report

# Verbose
poetry run python -m gestion_alumnos sync -v
```

### Preproducción

```bash
APP_ENV=preproduccion poetry run python -m gestion_alumnos sync --apply
```

### Producción (zipapp)

```bash
# Generar
poetry run python scripts/build_zipapp.py
# → dist/gestion_alumnos.pyz

# Desplegar en contenedor Moodle
docker cp dist/gestion_alumnos.pyz moodle:/opt/
docker exec moodle python3 /opt/gestion_alumnos.pyz sync --env-file /opt/.env --apply
```

## Tests

```bash
# Todos los tests
poetry run pytest

# Con cobertura
poetry run pytest --cov=gestion_alumnos

# Tests específicos
poetry run pytest tests/test_sync_analyzer.py -v
poetry run pytest tests/test_models.py -v
poetry run pytest tests/test_core_container.py -v
```

### Resultado actual

```
32 passed in 6.5s
```

| Suite | Tests | Descripción |
|-------|-------|-------------|
| `test_core_config.py` | 3 | Configuración Pydantic |
| `test_core_container.py` | 3 | DI Container |
| `test_models.py` | 10 | Modelos Pydantic |
| `test_repositories_moosh.py` | 3 | Operaciones moosh con mocks |
| `test_repositories_sigad.py` | 6 | API SIGAD con requests-mock |
| `test_sync_analyzer.py` | 6 | Análisis DuckDB (sin red) |

## Operaciones Moodle Soportadas

| Operación | Moosh | API REST | Notas |
|-----------|-------|----------|-------|
| Crear usuario | `moosh user-create` | `core_user_create_users` | ✅ |
| Actualizar usuario | `moosh user-mod` | `core_user_update_users` | ✅ |
| Suspender usuario | `moosh user-mod --suspend 1` | `core_user_update_users` | ✅ |
| Matricular en curso | `moosh course-enrol` | `enrol_manual_enrol_users` | ✅ |
| Desmatricular de curso | `moosh course-unenrol` | `enrol_manual_unenrol_users` | ✅ |
| Matricular en cohorte | `moosh cohort-enrol` | `core_cohort_add_cohort_members` | ✅ |
| Suspender matrícula | ❌ | ❌ | Requiere plugin PHP |

## Plugin PHP local_fparagon

Para usar la estrategia `api-snapshot`, instala el plugin en Moodle:

```bash
# Copiar a Moodle
cp -r moodle_plugin/local_fparagon /ruta/a/moodle/local/
# Instalar desde Administración de Moodle
```

Expone `local_fparagon_get_snapshot` que devuelve usuarios + matriculaciones en una sola llamada.

## Logging

```python
from gestion_alumnos.core.logging import get_logger

logger = get_logger(__name__)
logger.info("Procesando alumno", alumno_id=12345, documento="12345678A")
logger.markdown("## Informe de sincronización", creados=5)
```

- Desarrollo: logs legibles con colores
- Producción: logs en formato JSON
- Nivel MARKDOWN (25): entradas para informes `.md`

## Licencia

MIT
