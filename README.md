# Gestion Alumnos v0.3.0

Aplicación para la gestión automática del alumnado en **CampusDigitalFP** (Moodle).

## Características v0.3

- **Paquete Python con Poetry**
- **Logging estructurado** con structlog + nivel MARKDOWN para informes
- **Repository Pattern + Dependency Injection**
- **Dual driver Moodle**: `moosh` (local/contenedor) o **API REST** (remoto)
- **Distribución via zipapp** (`.pyz` autocontenido)
- **Zero SQL directo**

## Instalación

```bash
# Con Poetry
poetry install

# O con pip
pip install -r requirements.txt
```

## Uso

### Desarrollo

```bash
poetry run dev
# o
python -m gestion_alumnos sync --driver moosh
```

### Preproducción

```bash
APP_ENV=preproduccion poetry run pre
```

### Producción (zipapp)

```bash
# Generar
poetry run python scripts/build_zipapp.py

# Desplegar en contenedor Moodle
docker cp dist/gestion_alumnos.pyz moodle:/opt/
docker exec moodle python3 /opt/gestion_alumnos.pyz sync --env-file /opt/.env
```

## Configuración

Copia `.env.example` a `.env` y ajusta:

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
```

## Tests

```bash
poetry run pytest
```

## Arquitectura

```
gestion_alumnos/
├── core/          # Config, logging, exceptions, DI container
├── models/        # Pydantic models (Alumno, Centro, Ciclo, Modulo, Registro)
├── repositories/  # Protocols + implementations (SIGAD, Moosh, API, Email)
├── services/      # GestionAlumnosService (orquestador)
└── templates/     # HTML empaquetados
```

### Cambio de driver en runtime

```python
from gestion_alumnos.core.container import create_container
from gestion_alumnos.repositories.moodle_api_repository import APIMoodleRepository

container = create_container()
container.override_moodle_repository(APIMoodleRepository())
service = container.gestion_service()
```

## Licencia

MIT
