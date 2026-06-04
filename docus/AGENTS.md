# AGENTS.md — Guía para Agentes de IA (v0.3)

> **Rama:** `v0.3-estructura-paquete-con-logs`  
> **Versión:** `0.3.0`  
> **Tests:** `26/26 ✅`  
> **Propósito:** Paquete Python autocontenido para gestión de alumnos Moodle. Cero SQL directo.  
> **Arquitectura:** Repository Pattern + Dependency Injection + Pydantic Settings + structlog  
> **Última actualización:** Junio 2026

---

## 1. Visión General

**Nombre:** `gestion-alumnos` v0.3.0

**Propósito:** Sincronizar alumnos entre SIGAD (Sistema de Información de Aragón) y Moodle (CampusDigitalFP). El acceso a Moodle se abstrae mediante el protocolo `MoodleRepository`, con dos implementaciones intercambiables:
- **`MooshMoodleRepository`** — usa `moosh` vía subprocess (para ejecución local o dentro del contenedor Moodle).
- **`APIMoodleRepository`** — usa la API REST de Moodle vía `requests` (para ejecución remota).

El orquestador (`GestionService`) **no sabe** cuál implementación usa; la recibe inyectada por el `DIContainer` según la configuración (`moodle_driver`).

**Idioma:** Español (código, comentarios, docstrings, nombres de funciones/variables).

---

## 2. Stack Tecnológico

- **Python 3.10+**
- **Poetry** — gestión de dependencias y empaquetado
- **zipapp** — distribución como archivo `.pyz` autocontenido
- **Pydantic v2 + pydantic-settings** — modelos y configuración con validación automática
- **structlog** — logging estructurado (traído de v0.2)
- **requests** — llamadas HTTP a API SIGAD y API REST Moodle
- **smtplib** — envío de emails
- **pytest + requests-mock** — testing

**Dependencias prohibidas en esta versión:**
- ❌ `pymysql` — no hay acceso directo a BD
- ❌ `sqlalchemy` — no hay ORM ni SQL
- ❌ Comandos `mysql` vía `subprocess` — todo pasa por moosh o API REST

---

## 3. Estructura del Proyecto

```
gestion_alumnos/
├── __init__.py            # __version__, exports públicos
├── __main__.py            # python -m gestion_alumnos
├── cli.py                 # argparse: sync, extract, report, --driver
├── core/                  # Componentes fundamentales (traídos de v0.2)
│   ├── __init__.py
│   ├── config.py          # Pydantic Settings centralizada
│   ├── container.py       # DI Container: resuelve implementaciones
│   ├── exceptions.py      # Jerarquía de excepciones
│   └── logging.py         # structlog + nivel MARKDOWN (25)
├── models/                # Modelos Pydantic (basados en v0.2)
│   ├── __init__.py
│   ├── alumno.py
│   ├── centro.py
│   ├── ciclo.py
│   ├── modulo.py
│   └── registro.py
├── repositories/          # Repository Pattern (basado en v0.2)
│   ├── __init__.py
│   ├── protocols.py       # Protocols: EstudianteRepository, MoodleRepository, EmailRepository
│   ├── sigad_repository.py
│   ├── moodle_moosh_repository.py   # Implementación via moosh
│   ├── moodle_api_repository.py     # Implementación via API REST
│   └── email_repository.py
├── services/              # Lógica de negocio
│   ├── __init__.py
│   └── gestion_service.py # Orquestador puro con DI
├── templates/             # HTML empaquetados (importlib.resources)
│   ├── haFalladoElInforme.html
│   ├── informeAutomatizado.html
│   ├── matriculasAnadidas.html
│   ├── nombreUsuarioActualizado.html
│   └── nuevoUsuario.html
└── utils/
    ├── __init__.py
    └── helpers.py         # Funciones puras
```

---

## 4. Configuración

### Variables de Entorno (`.env`)

```bash
# Entorno
ENVIRONMENT=dev|test|preproduccion|produccion
SUBDOMAIN=test|preproduccion|www

# Driver de Moodle (determina implementación inyectada)
MOODLE_DRIVER=moosh          # o "api"

# API SIGAD
API_BASE_URL=https://aplicaciones.aragon.es/pcrpe/services/alumnosFPDistancia
API_USER=...
API_PASSWORD=...
API_TIMEOUT=30
API_MAX_RETRIES=5

# Moosh (solo si MOODLE_DRIVER=moosh)
MOOSH_PATH=moosh             # o ruta absoluta
DOCKER_CONTAINER=            # nombre del contenedor si moosh está dentro de uno

# API REST Moodle (solo si MOODLE_DRIVER=api)
MOODLE_API_URL=https://.../webservice/rest/server.php
MOODLE_API_TOKEN=...

# Email SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...
SMTP_USE_TLS=true

# Reportes
REPORT_TO="email1@ejemplo.com email2@ejemplo.com"
MAX_EMAILS_DIARIOS=10        # 1000 en producción

# Rutas
BASE_PATH=/var/fp-distancia-gestion-usuarios-automatica/
```

**No hay variables de base de datos.** No se usa MySQL.

### Pydantic Settings (`core/config.py`)

```python
from gestion_alumnos.core.config import Settings

settings = Settings()
print(settings.environment)      # "dev", "test", "preproduccion", "produccion"
print(settings.is_produccion)    # bool
print(settings.moodle_driver)    # "moosh" o "api"
print(settings.email_limit)      # 1000 (prod) o 10 (otros)
```

---

## 5. Convenciones de Código

### Idioma
- **Todo en español:** funciones, clases, variables, constantes, docstrings, comentarios.
- Ejemplo: `obtener_estudiantes()`, `matricular_en_curso()`, `num_alumnos_creados`.

### Nombres
```python
# Funciones: snake_case en español
def obtener_alumnos_moodle(): ...
def suspender_matriculas(): ...

# Clases: PascalCase
class Alumno: ...
class MooshMoodleRepository: ...
class APIMoodleRepository: ...

# Variables: snake_case
alumnos_sigad = []
nombre_fichero = ""

# Constantes: MAYÚSCULAS
BASE_URL = "..."
USUARIOS_PROTEGIDOS = frozenset({1, 2, 3, ...})
```

### Docstrings
```python
def funcion(param: str) -> int:
    """Breve descripción en español.

    Args:
        param: Descripción del parámetro.

    Returns:
        Descripción del retorno.
    """
```

### Logging con structlog
```python
from gestion_alumnos.core.logging import get_logger

logger = get_logger(__name__)

# Logs con contexto estructurado
logger.info(
    "Procesando alumno",
    alumno_id=12345,
    documento="12345678A",
    operacion="crear"
)

# Nivel MARKDOWN para informes
logger.markdown("## Sección de informe", alumnos_creados=5)
```

### Manejo de Errores
```python
from gestion_alumnos.core.exceptions import APIError, MoodleError, EmailError

try:
    raise MoodleError(
        mensaje="Usuario no encontrado",
        comando="moosh user-get 12345678a",
        codigo_salida=1
    )
except MoodleError as e:
    logger.error("Error de Moodle", comando=e.comando, codigo=e.codigo_salida)
```

---

## 6. Arquitectura del Sistema

### Repository Pattern + Dependency Injection

```python
# 1. Definir el protocolo (en repositories/protocols.py)
class MoodleRepository(Protocol):
    def crear_usuario(self, username: str, email: str, ...) -> int: ...
    def suspender_usuario(self, username: str) -> bool: ...
    # ...

# 2. Implementar con moosh
class MooshMoodleRepository:
    def crear_usuario(self, username, email, ...):
        subprocess.run(["moosh", "user-create", ...])

# 3. Implementar con API
class APIMoodleRepository:
    def crear_usuario(self, username, email, ...):
        requests.post(f"{self.api_url}?wstoken=...&wsfunction=core_user_create_users", ...)

# 4. El orquestador no sabe cuál usa
class GestionService:
    def __init__(
        self,
        sigad_repo: EstudianteRepository,
        moodle_repo: MoodleRepository,
        email_repo: EmailRepository,
    ):
        self._sigad = sigad_repo
        self._moodle = moodle_repo
        self._email = email_repo

# 5. El container inyecta la implementación correcta
from gestion_alumnos.core.container import get_container

container = get_container()  # Lee settings.moodle_driver y crea la implementación adecuada
service = container.gestion_service()
```

### Cambio de implementación en runtime

```python
from gestion_alumnos.core.container import create_container
from gestion_alumnos.repositories.moodle_api_repository import APIMoodleRepository

container = create_container()
container.override_moodle_repository(APIMoodleRepository())
service = container.gestion_service()
```

### Flujo Principal

```
┌─────────────┐     HTTP      ┌─────────────────────┐
│ API SIGAD   │ ────────────> │ sigad_repository.py │
└─────────────┘               └──────────┬──────────┘
                                         │
                                         ▼
                              ┌─────────────────────┐
                              │ data/estudiantes_*.json│
                              └──────────┬──────────┘
                                         │
                                         ▼
                              ┌─────────────────────┐
                              │ models/Registro     │
                              └──────────┬──────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
                    ▼                    ▼                    ▼
            ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
            │ Crear users  │   │ Matricular   │   │ Suspender    │
            │ (moosh/api)  │   │ (moosh/api)  │   │ (moosh/api)  │
            └──────────────┘   └──────────────┘   └──────────────┘
```

---

## 7. Repositorios

### SigadRepository (`EstudianteRepository`)
- `obtener_registro()` — descarga JSON con reintentos o carga desde `tests/data/`
- `buscar_por_documento(documento)` — búsqueda en registro
- Modo test: bypass de API, carga desde archivo local

### MooshMoodleRepository (`MoodleRepository`)
Ejecuta `moosh` como subprocess. Si `docker_container` está configurado, usa `docker exec {container} moosh ...`.

```python
result = subprocess.run(
    ["moosh", "user-create", "--password", password, "--email", email, username],
    capture_output=True,
    text=True,
    timeout=30
)
```

### APIMoodleRepository (`MoodleRepository`)
Usa `requests` contra la API REST de Moodle.

```python
params = {
    "wstoken": self._token,
    "wsfunction": "core_user_create_users",
    "moodlewsrestformat": "json",
    "users[0][username]": username,
    # ...
}
response = self._session.post(self._api_url, params=params)
```

### EmailRepository (`EmailRepository`)
- Templates HTML cargados con `importlib.resources`
- Límites diarios: 1000 en producción, 10 en otros entornos
- Redirección automática en entornos no productivos

---

## 8. Testing

### Estrategia
- **Unitarios:** Cada servicio aislado con mocks.
- **Integración:** Flujo completo con mocks de todos los repos.
- **Conformidad de Protocols:** Verificar que ambas implementaciones cumplen `MoodleRepository`.

### Ejecutar tests

```bash
# Todos
pytest tests/ -v

# Solo SIGAD
pytest tests/test_repositories_sigad.py -v

# Solo modelos
pytest tests/test_models.py -v
```

### Mock de moosh en tests

```python
@pytest.fixture
def mock_moosh(monkeypatch):
    def fake_run(cmd, **kwargs):
        class FakeResult:
            returncode = 0
            stdout = "mocked output"
            stderr = ""
        return FakeResult()
    monkeypatch.setattr(subprocess, "run", fake_run)
```

### Mock de API Moodle en tests

```python
@pytest.fixture
def mock_moodle_api(requests_mock):
    requests_mock.post(
        "https://test.moodle/webservice/rest/server.php",
        json=[{"id": 123, "username": "testuser"}]
    )
```

### Fixtures principales (`conftest.py`)
- `settings_test` — Configuración de test
- `sample_alumno`, `sample_registro` — Datos de ejemplo
- `mock_moosh` — Mock de subprocess para moosh

---

## 9. Zipapp y Distribución

### Generar zipapp

```bash
# Script automatizado
python scripts/build_zipapp.py

# Resultado
dist/gestion_alumnos.pyz
```

### Ejecutar zipapp

```bash
# Local
python3 dist/gestion_alumnos.pyz --env-file .env.produccion sync

# Dentro del contenedor Moodle
docker cp dist/gestion_alumnos.pyz moodle:/opt/
docker exec moodle python3 /opt/gestion_alumnos.pyz sync
```

### Recursos dentro del zipapp

Los templates HTML se cargan con `importlib.resources`:
```python
from importlib import resources
template = resources.files("gestion_alumnos.templates") / "nuevoUsuario.html"
```

---

## 10. Seguridad

### Credenciales
- **NUNCA** commitear `.env` con credenciales reales.
- Usar `.env.example` como plantilla.
- En producción, usar variables de entorno del sistema o Docker secrets.

### Usuarios protegidos
Lista hardcodeada de IDs no borrables (admin, cuentas de sistema):
```python
USUARIOS_PROTEGIDOS = frozenset({
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
    16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28,
    29, 30, 31, 32, 33, 3725, 3729, 3730, 7152, 7490,
    7491, 11720, 12270, 12272
})
```

### Validación de inputs
- `documento` (DNI/NIE): regex `[0-9]{8}[A-Z]` o `[XYZ][0-9]{7}[A-Z]`
- `email`: formato válido
- `username`: minúsculas, sin espacios

---

## 11. Estado Actual (v0.3.0)

| Componente | Estado | Tests |
|-----------|--------|-------|
| Core (config, logging, DI) | ✅ | 6/6 |
| Modelos Pydantic | ✅ | 10/10 |
| SIGAD Repository | ✅ | 6/6 |
| Moosh Repository | ✅ | 3/3 |
| API Repository | ✅ Implementado | Pendiente tests |
| Email Repository | ✅ Implementado | Pendiente tests |
| Gestion Service | 🟡 Stub | Pendiente integración |
| CLI | ✅ | — |
| Zipapp | ✅ | Funcional |

**Total tests: 26/26 ✅**

---

## 12. Próximos Pasos Sugeridos

1. **Completar lógica de negocio** en `gestion_service.py`
2. **Tests de integración** para `GestionAlumnosService`
3. **Tests para `APIMoodleRepository`**
4. **Limpiar código legacy** (`main.py`, `Util.py`, `Conexion.py`, `classes/`)
5. **Tag `v0.3.0`** y merge a `main`

---

**Autor:** Agente IA  
**Rama:** `v0.3-estructura-paquete-con-logs`  
**Commit:** `2fd963c`
