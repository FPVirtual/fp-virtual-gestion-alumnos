# Gestion Alumnos v0.3.0

Aplicación para la gestión automática del alumnado en **CampusDigitalFP** (Moodle).

## Estado del Proyecto

| Métrica | Valor |
|---------|-------|
| Versión | `0.3.0` |
| Tests | **26/26 ✅** |
| Python | `3.10+` |
| Distribución | Poetry + zipapp (`.pyz`) |

## Características v0.3

- **Paquete Python con Poetry**
- **Logging estructurado** con structlog + nivel MARKDOWN para informes
- **Repository Pattern + Dependency Injection**
- **Dual driver Moodle**: `moosh` (local/contenedor) o **API REST** (remoto)
- **Distribución via zipapp** (`.pyz` autocontenido)
- **Zero SQL directo**
- **Tests con mocks** (requests-mock, monkeypatch)

## Arquitectura

```
gestion_alumnos/
├── core/          # Config, logging, exceptions, DI container
├── models/        # Pydantic models (Alumno, Centro, Ciclo, Modulo, Registro)
├── repositories/  # Protocols + implementations (SIGAD, Moosh, API, Email)
├── services/      # GestionAlumnosService (orquestador)
└── templates/     # HTML empaquetados

archive/           # Código legacy v0.2 (main.py, Util.py, Conexion.py, classes/)
```

> **Nota:** El código procedural legacy de la v0.2 (`main.py`, `Util.py`, `Conexion.py`, `classes/`, etc.) ha sido movido a `archive/` para conservar la historia sin interferir con el paquete actual. El ejecutable actual es el paquete `gestion_alumnos`.

### Dual Driver Moodle

El acceso a Moodle se abstrae mediante el protocolo `MoodleRepository`:

| Driver | Uso | Implementación |
|--------|-----|----------------|
| `moosh` | Script dentro del contenedor Moodle | `MooshMoodleRepository` |
| `api` | Script remoto vía API REST | `APIMoodleRepository` |

El `DIContainer` resuelve automáticamente la implementación según `MOODLE_DRIVER`:

```python
from gestion_alumnos.core.container import get_container

container = get_container()
service = container.gestion_service()  # Usa moosh o API según .env
```

Cambio en runtime:

```python
from gestion_alumnos.core.container import create_container
from gestion_alumnos.repositories.moodle_api_repository import APIMoodleRepository

container = create_container()
container.override_moodle_repository(APIMoodleRepository())
service = container.gestion_service()
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

# Moosh (si driver=moosh)
MOOSH_PATH=moosh
DOCKER_CONTAINER=moodle_app  # o vacío si está en PATH

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
```

## Uso

### Desarrollo

```bash
# Sincronización completa
poetry run python -m gestion_alumnos sync --driver moosh

# Con verbose
poetry run python -m gestion_alumnos sync -v
```

### Preproducción

```bash
APP_ENV=preproduccion poetry run python -m gestion_alumnos sync
```

### Producción (zipapp)

```bash
# Generar
poetry run python scripts/build_zipapp.py
# → dist/gestion_alumnos.pyz (79.8 KB)

# Desplegar en contenedor Moodle
docker cp dist/gestion_alumnos.pyz moodle:/opt/
docker exec moodle python3 /opt/gestion_alumnos.pyz sync --env-file /opt/.env
```

## Tests

```bash
# Todos los tests
poetry run pytest

# Con cobertura
poetry run pytest --cov=gestion_alumnos

# Tests específicos
poetry run pytest tests/test_repositories_sigad.py -v
poetry run pytest tests/test_models.py -v
poetry run pytest tests/test_core_container.py -v
```

### Resultado actual

```
26 passed in 6.13s
```

| Suite | Tests | Descripción |
|-------|-------|-------------|
| `test_core_config.py` | 3 | Configuración Pydantic |
| `test_core_container.py` | 3 | DI Container (resolución moosh/api) |
| `test_models.py` | 10 | Modelos Pydantic |
| `test_repositories_moosh.py` | 3 | Operaciones moosh con mocks |
| `test_repositories_sigad.py` | 6 | API SIGAD con requests-mock |

## Operaciones Moodle Soportadas

| Operación | Moosh | API REST |
|-----------|-------|----------|
| Crear usuario | `moosh user-create` | `core_user_create_users` |
| Suspender usuario | `moosh user-mod --suspend 1` | `core_user_update_users` |
| Reactivar usuario | `moosh user-mod --suspend 0` | `core_user_update_users` |
| Matricular en curso | `moosh course-enrol` | `enrol_manual_enrol_users` |
| Desmatricular de curso | `moosh course-unenrol` | `enrol_manual_unenrol_users` |
| Matricular en cohorte | `moosh cohort-enrol` | `core_cohort_add_cohort_members` |

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
