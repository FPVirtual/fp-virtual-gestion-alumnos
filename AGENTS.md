<!-- From: /home/darioaxel/Proyectos/fp-virtual-gestion-alumnos/AGENTS.md -->
# AGENTS.md - Guía para Agentes de IA

> Este documento está destinado a agentes de IA que trabajen en este proyecto. Contiene información esencial sobre la arquitectura, convenciones y procesos de desarrollo. **Última actualización:** Mayo 2026.

---

## 1. Visión General del Proyecto

**Nombre:** `gestion-alumnos` (versión 0.1.0)

**Propósito:** Aplicación Python para la gestión automática de usuarios en Moodle (plataforma CampusDigitalFP). Se encarga de:
- Crear/eliminar usuarios en Moodle según datos de SIGAD (Sistema de Información y Gestión Académica de Aragón)
- Matricular/desmatricular alumnos en cursos según su matrícula oficial
- Sincronizar estados entre SIGAD y Moodle (reactivaciones, suspensiones)
- Enviar emails de notificación a los estudiantes
- Generar informes y CSVs para creación de cuentas Google Workspace

**Idioma principal:** Español (código, comentarios y documentación)

---

## 2. Stack Tecnológico

### Lenguaje y Runtime
- **Python 3.10+** (especificado en `pyproject.toml`)
- **Poetry** para gestión de dependencias

### Dependencias Principales
- `pydantic` (^2.10.0) y `pydantic-settings` (^2.7.0) — Validación y configuración
- `structlog` (^25.1.0) — Logging estructurado
- `requests` (^2.32.5) y `httpx` (^0.28.0) — Clientes HTTP
- `pymysql` (^1.1.1) — Conexión a base de datos MySQL
- `python-dotenv` (^1.2.1) — Gestión de variables de entorno
- `aiohttp` (^3.11.0) — Email async
- `cryptography` (^46.0.3), `certifi`, `idna` — Utilidades criptográficas y SSL

### Dependencias de Desarrollo
- `pytest` (^9.0.2), `pytest-asyncio`, `pytest-cov`, `pytest-mock` — Testing
- `requests-mock` (^1.12.1), `respx` (^0.22.0) — Mocking de HTTP
- `mypy` (^1.14.0) — Type checking
- `ruff` (^0.9.0) — Linter y formateador
- `pre-commit` (^4.1.0) — Hooks de git

### Infraestructura
- **Docker** — Contenedores Moodle (interactúa vía `moosh` y MySQL)
- **MySQL** — Acceso directo a BD de Moodle para operaciones complejas
- **Moodle + Moosh** — Gestión de usuarios, cursos y matrículas
- **SIGAD** — API REST de la que se obtienen los datos de estudiantes

---

## 3. Estructura del Proyecto

El proyecto mantiene **dos arquitecturas en paralelo**:

### Arquitectura Moderna (v2) — Patrones Enterprise

```
gestion_alumnos/
├── core/                       # Componentes fundamentales
│   ├── config.py              # Pydantic Settings - Config centralizada
│   ├── container.py           # DI Container - Inyección de dependencias
│   ├── exceptions.py          # Jerarquía de excepciones personalizadas
│   └── logging.py             # Logging estructurado con structlog
├── models_v2.py               # Modelos Pydantic con validación
├── repositories/              # Repository Pattern
│   ├── protocols.py           # Interfaces (Protocols Python)
│   ├── sigad_repository.py    # Implementación API SIGAD
│   ├── moodle_db_repository.py # Implementación Moodle
│   └── email_repository.py    # Implementación Email
├── services/                  # Lógica de negocio
│   └── gestion_service.py     # Servicio principal con DI
├── main_v2.py                 # Punto de entrada moderno
└── scripts/
    ├── run_dev.py             # Desarrollo (carga .env.dev)
    ├── run_pre.py             # Preproducción (carga .env.preproduccion)
    ├── run_pro.py             # Producción (carga .env.produccion)
    └── run_tests.py           # Ejecutar tests con pytest
```

### Arquitectura Legacy (v1) — Mantenida para compatibilidad

```
gestion_alumnos/
├── main.py                    # Lógica principal (versión refactorizada v1)
├── models.py                  # Dataclasses: Alumno, Centro, Ciclo, Modulo, Registro
├── conexion.py                # Clase Conexion para llamadas HTTP (legacy)
├── logger_config.py           # Configuración de logging personalizado con nivel MARKDOWN
├── util.py                    # Funciones utilitarias (emails, conversión LFP→LOE)
├── classes/                   # Clases legacy (alumno.py, centro.py, ciclo.py, modulo.py)
└── utils/                     # Utilidades modernizadas
    ├── api_client.py          # Cliente API REST para SIGAD
    ├── json_parser.py         # Parser de JSON a objetos modelo
    ├── parser.py              # Parser de diccionario a modelo Registro
    ├── moodle.py              # Operaciones sobre Moodle
    ├── moosh.py               # Wrapper para ejecutar comandos moosh en Docker
    ├── email_service.py       # Servicio de envío de emails con límites diarios
    └── utils.py               # Funciones auxiliares
```

### Directorios de proyecto

```
├── data/                      # Datos descargados de API (JSON)
├── logs/                      # Logs de ejecución
│   ├── app_*.log             # Logs normales
│   └── informe_*.md          # Informes en Markdown
├── tests/                     # Tests pytest
│   ├── conftest.py            # Fixtures y configuración
│   └── data/                  # Fixtures de test (JSON)
├── scripts/                   # Scripts de ejemplo, SQL y utilidades
│   └── db_testing/            # Scripts SQL para exploración Moodle
├── examples/                  # Ejemplos de uso de la nueva arquitectura
├── csvs/                      # CSVs generados (extracción de alumnado)
└── templates/                 # Templates HTML para emails
```

---

## 4. Configuración y Entornos

### Variables de Entorno (.env files)

El proyecto usa archivos `.env.{entorno}` para configuración:

| Entorno | Fichero | Descripción |
|---------|---------|-------------|
| Test | `.env.test` | Tests locales, datos mock |
| Desarrollo | `.env.dev` | Desarrollo local |
| Preproducción | `.env.preproduccion` | Entorno de staging |
| Producción | `.env.produccion` (no en repo) | Entorno real |

**Variables importantes:**
```bash
# General
ENVIRONMENT="test|dev|preproduccion|produccion"
SUBDOMAIN="test|preproduccion|www"

# API SIGAD
API_BASE_URL="https://aplicaciones.aragon.es/pcrpe/services/alumnosFPDistancia"
API_USER="usuario"
API_PASSWORD="password"

# Email SMTP
SMTP_HOST="smtp.gmail.com"
SMTP_PORT="587"
SMTP_USER="..."
SMTP_PASSWORD="..."

# Base de datos Moodle
DB_USER="admin"
DB_PASS="..."
DB_HOST="192.168.1.110"
DB_NAME="www_fpvirtualaragon_es"

# Reportes
REPORT_TO="email1@ejemplo.com email2@ejemplo.com"
```

### Configuración Pydantic (v2)

```python
from gestion_alumnos.core.config import get_settings

settings = get_settings()
print(settings.environment)      # "dev", "test", "preproduccion", "produccion"
print(settings.is_produccion)    # bool
print(settings.email_limit)      # 1000 (prod) o 10 (otros)
```

### Ficheros de Configuración Python Legacy

- **Config.py**: Contiene credenciales y configuración (ignorado por git)
- **Config-sample.py**: Plantilla con campos vacíos para nuevos desarrolladores

---

## 5. Comandos de Build y Test

### Instalación

```bash
# Con Poetry (recomendado)
poetry install

# O con pip (legacy)
pip install -r requirements.txt
```

### Ejecutar Tests

```bash
# Usando Poetry script (carga automáticamente .env.test)
poetry run test

# Directamente con pytest
APP_ENV=test poetry run pytest

# Con cobertura
poetry run pytest --cov=gestion_alumnos

# Test específico
poetry run pytest tests/test_api_client.py::test_solicitar_datos_ok -v
```

### Ejecutar Aplicación

```bash
# Desarrollo (usa main_v2 o gestion_alumnos_v1 según script)
APP_ENV=dev poetry run dev

# Preproducción
APP_ENV=preproduccion poetry run pre

# Producción
APP_ENV=produccion poetry run pro
```

### Lint y Type Checking

```bash
# Formateo y linting
poetry run ruff check .
poetry run ruff format .

# Type checking
poetry run mypy gestion_alumnos
```

### Docker

```bash
docker build -t gestion-alumnos .
docker run gestion-alumnos
```

---

## 6. Convenciones de Código

### Estilo
- **Idioma:** Español para todo (nombres de funciones, variables, comentarios, docstrings)
- **Formato:** Python estándar (PEP 8 implícito)
- **Linter:** Ruff
- **Type hints:** Obligatorios en código nuevo (v2)

### Convenciones de Nombres

```python
# Funciones: snake_case en español
def obtener_estudiantes(): ...
def cargar_fichero_estudiantes(): ...
def reactiva_usuario(): ...

# Clases: PascalCase en español o inglés
class Alumno: ...
class Centro: ...
class EmailService: ...
class GestionAlumnosService: ...

# Variables: snake_case
alumnos_sigad = []
nombre_fichero = ""
num_alumnos_creados = 0

# Constantes: MAYÚSCULAS
BASE_URL = "..."
DATA_DIR = Path(...)
```

### Modelos de Datos

**Legacy (dataclasses)** en `models.py`:
```python
@dataclass
class Alumno:
    idAlumno: int
    idTipoDocumento: int
    documento: str
    nombre: str
    apellido1: str
    apellido2: Optional[str]
    email: str
    centros: List[Centro]
```

**Moderno (Pydantic v2)** en `models_v2.py`:
```python
class Alumno(ModeloBase):
    id_alumno: int = Field(..., alias="idAlumno", gt=0)
    documento: str = Field(..., pattern=r"^[A-Z0-9]+$")
    # Propiedades calculadas
    @property
    def username_moodle(self) -> str:
        return self.documento.lower()
```

### Logging

El proyecto usa **dos sistemas de logging**:

1. **Legacy** (`logger_config.py`): Logger personalizado con nivel MARKDOWN (25)
   ```python
   from gestion_alumnos.logger_config import logger
   logger.info("Mensaje informativo")
   logger.markdown("Entrada para informe markdown")
   ```

2. **Moderno** (`core/logging.py`): Logging estructurado con structlog
   ```python
   from gestion_alumnos.core.logging import get_logger
   logger = get_logger(__name__)
   logger.info("Procesando alumno", alumno_id=12345, documento="12345678A")
   ```

---

## 7. Arquitectura del Sistema

### Flujo de Datos Principal

```
┌─────────────┐     HTTP GET     ┌─────────────────┐
│ API SIGAD   │ ───────────────> │  api_client.py  │
│  (WS 1+2)   │                  │                 │
└─────────────┘                  └────────┬────────┘
                                          │
                                          ▼
                              ┌──────────────────────┐
                              │ data/estudiantes_*.json│
                              └──────────┬───────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │   json_parser.py     │
                              │   parse_json()       │
                              └──────────┬───────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │  Registro/Alumno     │
                              │  (modelos)           │
                              └──────────┬───────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
                    ▼                    ▼                    ▼
            ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
            │  Crear users  │   │ Matricular    │   │  Suspender    │
            │  (moosh/mysql)│   │ en cursos     │   │  si no están  │
            │               │   │               │   │  en SIGAD     │
            └───────────────┘   └───────────────┘   └───────────────┘
```

### Componentes Clave

1. **api_client.py**: Cliente REST para obtener datos de estudiantes desde SIGAD
   - `solicitar_datos()` — Obtiene idSolicitud
   - `obtener_estudiantes()` — Descarga JSON con reintentos
   - Soporta modo test (bypass de API)

2. **main.py / main_v2.py**: Lógica de negocio principal
   - `gestion_alumnos()` — Versión legacy
   - `gestion_alumnos_v1()` — Versión refactorizada v1
   - `main_v2.py` — Punto de entrada con arquitectura moderna

3. **json_parser.py**: Carga y parseo de JSON
   - `cargar_fichero_estudiantes()` — Lee último fichero de `data/`
   - Borra ficheros antiguos en producción

4. **services/gestion_service.py**: Servicio principal (v2)
   - Orquesta la sincronización completa
   - Usa repositorios inyectados
   - Retorna `ResultadoSync` con estadísticas

5. **email_service.py**: Servicio de envío de emails
   - Límites diarios: 1000 en producción, 10 en otros entornos
   - Templates HTML para diferentes tipos de notificación
   - Redirección automática en entornos no productivos

### Patrones de Diseño (v2)

| Patrón | Implementación | Beneficio |
|--------|----------------|-----------|
| **Repository** | `repositories/` + `protocols.py` | Desacoplamiento de datos |
| **Dependency Injection** | `core/container.py` | Testing y configuración |
| **Pydantic Models** | `models_v2.py` | Validación automática |
| **Pydantic Settings** | `core/config.py` | Config centralizada |
| **Structured Logging** | `core/logging.py` | Logs analizables |
| **Custom Exceptions** | `core/exceptions.py` | Manejo de errores específico |

---

## 8. Estrategia de Testing

### Tipos de Tests
- **Unitarios:** Funciones aisladas (api_client, parser, email_service)
- **Integración:** Flujos completos con mocks
- **Fixtures:** Datos JSON en `tests/data/`

### Estructura de Tests

```
tests/
├── conftest.py              # Fixtures globales (sample_json_dict, sample_registro)
├── test_api_client.py       # Tests del cliente API (requests_mock)
├── test_core_config.py      # Tests de configuración Pydantic
├── test_email_service.py    # Tests del servicio de email
├── test_json_parser.py      # Tests del parser JSON
├── test_moodle.py           # Tests de operaciones Moodle
├── test_moosh.py            # Tests de comandos moosh
├── test_repositories.py     # Tests de repositorios (v2)
├── test_services.py         # Tests de servicios con mocks e inyección de dependencias
└── test_verificacion_log.py # Tests de verificación de logs
```

### Mocking

```python
# requests_mock para APIs
requests_mock.get(url, json={"codigo": 0, "idSolicitud": 1234})

# monkeypatch para variables de entorno
monkeypatch.setenv("API_USER", "test_user")

# mock para operaciones de sistema
mock.patch("utils.api_client.solicitar_datos")

# Inyección de dependencias en tests (v2)
container = DIContainer()
mock_repo = Mock()
mock_repo.obtener_registro.return_value = Registro(...)
container.override_estudiante_repository(mock_repo)
```

### Fixtures Principales (`conftest.py`)
- `sample_json_dict` — Diccionario JSON de test
- `sample_registro` — Modelo Registro parseado

### Ejecutar Tests Específicos

```bash
# Test específico
poetry run pytest tests/test_api_client.py::test_solicitar_datos_ok -v

# Con cobertura detallada
poetry run pytest --cov=gestion_alumnos --cov-report=html
```

---

## 9. Seguridad

### Gestión de Credenciales
- **NUNCA** commitear `Config.py` con datos reales
- Usar siempre variables de entorno (`.env` files)
- `Config-sample.py` y `.env.example` son plantillas seguras
- `.env.*` están en `.gitignore`

### Datos Sensibles en el Código
- IPs de servidores internos (192.168.1.x)
- Tokens y credenciales SMTP
- Contraseñas de base de datos

### Acceso a BD
El sistema ejecuta comandos SQL directos sobre la BD de Moodle mediante `subprocess.run()` con `shell=True`. Esto requiere validación cuidadosa de inputs:
```python
command = f"""
    mysql --user="{DB_USER}" --password="{DB_PASS}" 
    --host="{DB_HOST}" -D "{DB_NAME}"  
    --execute="UPDATE mdl_user SET ..."
"""
```

### Usuarios Protegidos
Lista de usuarios no borrables hardcodeada en `main.py`:
```python
usuarios_moodle_no_borrables = [1, 2, 3, ..., 33, 3725, 3729, 3730, 7152, 7490, 7491, 11720, 12270, 12272]
```

---

## 10. Procesos de Negocio Importantes

### Matriculación de Alumnos
1. Descargar datos desde SIGAD vía API (o usar fichero de test)
2. Para cada alumno en JSON:
   - Si no existe en Moodle → crear usuario
   - Generar email del dominio `@fpvirtualaragon.es`
   - Matricular en cohorte "alumnado"
   - Matricular en cursos según módulos en SIGAD

### Sincronización de Bajas
1. Comparar alumnos Moodle vs SIGAD
2. Si alumno está en Moodle pero no en SIGAD:
   - Suspender matrículas en cursos
   - Mantener en cohortes (preserva progreso)
   - Suspender usuario

### Actualización de Emails
- Si email SIGAD cambia → actualizar en Moodle
- Si DNI/NIE cambia (NIE→DNI) → actualizar username

### Reactivaciones
- Alumno suspendido en Moodle que vuelve a aparecer en SIGAD → reactivar

### Limpieza de Agosto
- En agosto (`mes == 08`): eliminar matrículas suspendidas permanentemente

---

## 11. Notas para Desarrolladores

### Límites Operativos
- Máximo 1000 emails/día en producción (limitación Gmail)
- Máximo 10 emails en entornos no producción
- Lista de usuarios no borrables hardcodeada

### Casos Especiales
- Fusión de cursos de Maite (IFC301/302/303 → IFC301) — eliminar en 2026-2027
- Cursos de tutoría terminados en 't' se ignoran en ciertas operaciones
- Conversión de códigos LFP (Ley Formación Profesional) a LOE (antigua)

### Debugging
```python
# Activar logs detallados
logger.setLevel(logging.DEBUG)

# Modo test sin API
ENVIRONMENT=test poetry run dev
```

### Troubleshooting Común
1. **Error de conexión a API:** Verificar `API_USER`/`API_PASSWORD` en `.env`
2. **No encuentra ficheros JSON:** Revisar que `data/` exista y tenga permisos
3. **Error de Docker/Moosh:** Verificar que contenedores estén corriendo
4. **Tests fallan:** Asegurar que `APP_ENV=test` y fixtures existan

---

## 12. Roadmap / Estado Actual

Marcadas en `v0.1-README.md`:
- [x] Sistema de logs nuevo funcionando
- [x] Utilización de `.env` sin problemas
- [x] Sistema de tests
- [x] Prueba de descarga de archivos desde SIGAD y transformación en diccionario
- [ ] Comprobación de funcionamiento de la versión antigua sin modificar
- [ ] Prueba de matriculación de un alumno

Refactorización en curso:
- Migración de `main.py` a módulos más pequeños
- Separación de lógica de negocio de operaciones Moodle
- Modernización de clases legacy a dataclasses/Pydantic
- Implementación completa de arquitectura v2 con DI y Repository Pattern

---

## 13. Estructura de Datos

### JSON de Estudiantes (API SIGAD)

```json
{
  "fecha": "15/12/2025",
  "hora": "11:42:28",
  "alumnos": [
    {
      "idAlumno": 16839,
      "idTipoDocumento": 1,
      "documento": "78842153Q",
      "nombre": "Valeria",
      "apellido1": "Torres",
      "apellido2": "Medina",
      "email": "valeria.torres.medina@ejemplo.com",
      "centros": [
        {
          "codigoCentro": "50009348",
          "centro": "AVEMPACE",
          "ciclos": [
            {
              "idFicha": 22,
              "codigoCiclo": "12242301",
              "ciclo": "Educación Infantil (Formación Profesional)",
              "siglasCiclo": "SSC302",
              "modulos": [
                {
                  "idMateria": 18599,
                  "modulo": "Itinerario personal para la empleabilidad I ( Virtual )",
                  "siglasModulo": "IPPE1"
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

---

**Autor del documento:** Agente IA  
**Última actualización:** Mayo 2026
