# AGENTS.md - Guía para Agentes de IA

> Este documento está destinado a agentes de IA que trabajen en este proyecto. Contiene información esencial sobre la arquitectura, convenciones y procesos de desarrollo.

---

## 1. Visión General del Proyecto

**Nombre:** `fp-distancia-gestion-usuarios-automatica` (gestion-alumnos v0.1.0)

**Propósito:** Aplicación Python para la gestión automática de usuarios en Moodle. Se encarga de:
- Crear/eliminar usuarios en Moodle según datos de SIGAD (Sistema de Información y Gestión Académica de Aragón)
- Matricular/desmatricular alumnos en cursos según su matrícula oficial
- Sincronizar estados entre SIGAD y Moodle (reactivaciones, suspensiones)
- Enviar emails de notificación a los estudiantes
- Generar informes y CSVs para creación de cuentas Google Workspace

**Idioma principal:** Español (código, comentarios y documentación)

---

## 2. Stack Tecnológico

### Lenguaje y Runtime
- **Python 3.10+** (especificado en pyproject.toml)
- **Poetry** para gestión de dependencias

### Dependencias Principales
- `requests` - Llamadas HTTP a Web Services
- `python-dotenv` - Gestión de variables de entorno
- `pymysql` - Conexión a base de datos MySQL
- `pytest`, `pytest-cov`, `pytest-mock`, `requests-mock` - Testing
- Librerías estándar: `http.client`, `smtplib`, `json`, `subprocess`

### Infraestructura
- **Docker** - Contenedores Moodle (interactúa vía `moosh` y MySQL)
- **MySQL** - Acceso directo a base de datos de Moodle para operaciones complejas
- **Moodle** + **Moosh** - Gestión de usuarios, cursos y matrículas
- **SIGAD** - API REST de la que se obtienen los datos de estudiantes

---

## 3. Estructura del Proyecto

```
├── gestion_alumnos/           # Código fuente principal
│   ├── __init__.py
│   ├── __main__.py            # Punto de entrada vacío
│   ├── main.py                # Lógica principal de gestión (versión refactorizada v1)
│   ├── models.py              # Dataclasses modernos: Alumno, Centro, Ciclo, Modulo, Registro
│   ├── conexion.py            # Clase Conexion para llamadas HTTP (legacy)
│   ├── logger_config.py       # Configuración de logging personalizado con nivel MARKDOWN
│   ├── util.py                # Funciones utilitarias (emails, conversión LFP→LOE)
│   ├── classes/               # Clases legacy (alumno.py, centro.py, ciclo.py, modulo.py)
│   ├── scripts/               # Entry points para entornos
│   │   ├── run_dev.py         # Desarrollo (usa gestion_alumnos_v1)
│   │   ├── run_pre.py         # Preproducción (usa gestion_alumnos legacy)
│   │   ├── run_pro.py         # Producción (usa gestion_alumnos legacy)
│   │   └── run_tests.py       # Ejecutar tests con pytest
│   └── utils/                 # Utilidades modernizadas
│       ├── api_client.py      # Cliente API REST para SIGAD
│       ├── json_parser.py     # Parser de JSON a objetos modelo
│       ├── parser.py          # Parser de diccionario a modelo Registro
│       ├── moodle.py          # Operaciones sobre Moodle (get_moodle, get_alumnos_moodle)
│       ├── moosh.py           # Wrapper para ejecutar comandos moosh en Docker
│       ├── email_service.py   # Servicio de envío de emails con límites diarios
│       └── utils.py           # Funciones auxiliares
├── scripts/                   # Scripts de ejemplo y utilidades
│   ├── ejemplo_aplicar_cambios.py
│   └── ejemplo_uso_sigad_sync.py
├── tests/                     # Tests pytest
│   ├── conftest.py            # Fixtures y configuración
│   ├── test_api_client.py     # Tests del cliente API
│   ├── test_json_parser.py    # Tests del parser JSON
│   ├── test_email_service.py  # Tests del servicio de email
│   ├── test_moodle.py         # Tests de operaciones Moodle
│   ├── test_moosh.py          # Tests de comandos moosh
│   └── data/                  # Fixtures de test
│       ├── estudiantes_0001.json
│       └── test_estudiantes_data.json
├── data/                      # Datos descargados de API (JSON)
├── logs/                      # Logs de ejecución
│   ├── app_*.log             # Logs normales
│   └── informe_*.md          # Informes en Markdown
├── csvs/                      # CSVs generados (extracción de alumnado)
├── Config.py                  # Configuración sensible (ignorada por git)
├── Config-sample.py           # Plantilla de configuración
├── .env.example               # Plantilla de variables de entorno
├── .env.test                  # Configuración para tests
├── .env.preproduccion         # Configuración preproducción
├── pyproject.toml             # Configuración Poetry
├── requirements.txt           # Dependencias pip (legacy)
├── Dockerfile                 # Contenedor Docker básico
└── extrae_alumnado.sh         # Script bash para extraer datos
```

---

## 4. Configuración y Entornos

### Variables de Entorno (.env files)

El proyecto usa archivos `.env.{entorno}` para configuración:

| Entorno | Fichero | Descripción |
|---------|---------|-------------|
| Test | `.env.test` | Tests locales, datos mock |
| Preproducción | `.env.preproduccion` | Entorno de staging |
| Producción | `.env.produccion` (no en repo) | Entorno real |

**Variables importantes:**
```bash
# General
ENVIRONMENT="test|preproduccion|produccion"
SUBDOMAIN="test|preproduccion|www"
PATH="/var/fp-distancia-gestion-usuarios-automatica/"

# API SIGAD
API_BASE_URL="https://aplicaciones.aragon.es/pcrpe/services/alumnosFPDistancia"
API_USER="usuario"
API_PASSWORD="password"

# Web Services (legacy, usado en main.py)
url1="aplicaciones.aragon.es"
path1="/pcrpe/services/alumnosFPDistancia/solicitud/"
usuario1="..."
password1="..."

# Email SMTP
SMTP_HOSTS="smtp.gmail.com"
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

### Ficheros de Configuración Python

- **Config.py**: Contiene credenciales y configuración (ignorado por git)
- **Config-sample.py**: Plantilla con campos vacíos para nuevos desarrolladores

---

## 5. Comandos de Build y Test

### Instalación
```bash
# Con Poetry (recomendado)
poetry install

# O con pip
pip install -r requirements.txt
```

### Ejecutar Tests
```bash
# Usando Poetry script
poetry run test

# Directamente con pytest
APP_ENV=test poetry run pytest

# Con cobertura
poetry run pytest --cov=gestion_alumnos
```

### Ejecutar Aplicación

```bash
# Desarrollo (usa gestion_alumnos_v1 - nueva versión refactorizada)
APP_ENV=dev poetry run dev

# Preproducción (usa gestion_alumnos legacy)
APP_ENV=preproduccion poetry run pre

# Producción
APP_ENV=produccion poetry run pro
```

### Docker
```bash
docker build -t gestion-alumnos .
docker run gestion-alumnos
```

---

## 6. Convenciones de Código

### Estilo
- **Idioma:** Español para todo (nombres de funciones, variables, comentarios)
- **Docstrings:** En español, explicando el propósito
- **Formato:** Python estándar (PEP 8 implícito)

### Convenciones de Nombres
```python
# Funciones: snake_case en español
def obtener_estudiantes(): ...
def cargar_fichero_estudiantes(): ...
def reactiva_usuario(): ...

# Clases: PascalCase en español o inglés
class Alumno: ...
class Centro: ...
class Ciclo: ...
class EmailService: ...

# Variables: snake_case
alumnos_sigad = []
nombre_fichero = ""
num_alumnos_creados = 0

# Constantes: MAYÚSCULAS
BASE_URL = "..."
DATA_DIR = Path(...)
```

### Modelos de Datos (Dataclasses)

```python
# models.py - Modelo moderno con dataclasses
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

### Logging
El proyecto usa un logger personalizado (`logger_config.py`):
- Nivel MARKDOWN (25) para informes estructurados
- Logs en `logs/app_*.log`
- Informes en `logs/informe_*.md`

```python
from gestion_alumnos.logger_config import logger

logger.info("Mensaje informativo")
logger.markdown("Entrada para informe markdown")
```

### Email Service

El servicio de email utiliza variables de entorno para su configuración:

```python
from dotenv import load_dotenv
from gestion_alumnos.utils.email_service import crear_email_service_desde_env

# Cargar variables de entorno
load_dotenv(".env.produccion")

# Crear servicio desde variables de entorno
email_service = crear_email_service_desde_env()

# Usar el servicio
email_service.enviar_email_nuevo_usuario(alumno, password, matriculas)
email_service.enviar_informe_ejecucion(filename_md, filename_csv)
```

**Variables de entorno requeridas:**
- `SMTP_HOSTS` - Servidor SMTP
- `SMTP_PORT` - Puerto SMTP
- `SMTP_USER` - Usuario SMTP
- `SMTP_PASSWORD` - Contraseña SMTP

**Variables opcionales:**
- `SUBDOMAIN` - Entorno (www, preproduccion, test)
- `PATH` - Ruta base para templates
- `REPORT_TO` - Emails para informes separados por espacios

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
   - `solicitar_datos()` - Obtiene idSolicitud
   - `obtener_estudiantes()` - Descarga JSON con reintentos
   - Soporta modo test (bypass de API)

2. **main.py**: Lógica de negocio principal
   - `gestion_alumnos()` - Versión legacy completa (~1800 líneas)
   - `gestion_alumnos_v1()` - Nueva versión refactorizada (en desarrollo)

3. **json_parser.py**: Carga y parseo de JSON
   - `cargar_fichero_estudiantes()` - Lee último fichero de data/
   - Borra ficheros antiguos en producción

4. **models.py**: Modelos de datos tipados
   - `Registro` → contiene `List[Alumno]`
   - `Alumno` → contiene `List[Centro]`
   - `Centro` → contiene `List[Ciclo]`
   - `Ciclo` → contiene `List[Modulo]`

5. **email_service.py**: Servicio de envío de emails
   - Límites diarios: 1000 en producción, 10 en otros entornos
   - Templates HTML para diferentes tipos de notificación
   - Redirección automática en entornos no productivos

---

## 8. Estrategia de Testing

### Tipos de Tests
- **Unitarios:** Funciones aisladas (api_client, parser, email_service)
- **Integración:** Flujos completos con mocks
- **Fixtures:** Datos JSON en `tests/data/`

### Mocking
```python
# requests_mock para APIs
requests_mock.get(url, json={"codigo": 0, "idSolicitud": 1234})

# monkeypatch para variables de entorno
monkeypatch.setenv("API_USER", "test_user")

# mock para operaciones de sistema
mock.patch("utils.api_client.solicitar_datos")
```

### Fixtures Principales (conftest.py)
- `sample_json_dict` - Diccionario JSON de test
- `sample_registro` - Modelo Registro parseado

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
- Usar siempre variables de entorno (.env files)
- `Config-sample.py` y `.env.example` son plantillas seguras

### Datos Sensibles en el Código
- Contraseñas de ejemplo en `.env.preproduccion` (revocar si son reales)
- IPs de servidores internos (192.168.1.x)
- Tokens y credenciales SMTP

### Acceso a BD
El sistema ejecuta comandos SQL directos sobre la BD de Moodle:
```python
# Ejemplo de comando peligroso que requiere validación
command = f"""
    mysql --user="{DB_USER}" --password="{DB_PASS}" 
    --host="{DB_HOST}" -D "{DB_NAME}"  
    --execute="UPDATE mdl_user SET ..."
"""
```

---

## 10. Procesos de Negocio Importantes

### Matriculación de Alumnos
1. Descargar datos desde SIGAD vía API
2. Para cada alumno en JSON:
   - Si no existe en Moodle → crear usuario
   - Generar email del dominio @fpvirtualaragon.es
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

### Limpieza de Agosto
- En agosto (mes == 08): eliminar matrículas suspendidas permanentemente

---

## 11. Notas para Desarrolladores

### Límites Operativos
- Máximo 1000 emails/día en producción (limitación Gmail)
- Máximo 10 emails en entornos no producción
- Lista de usuarios no borrables hardcodeada (IDs 1-33, 3725, etc.)

### Casos Especiales
- Fusión de cursos de Maite (IFC301/302/303 → IFC301) - eliminar en 2026-2027
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
1. **Error de conexión a API:** Verificar `API_USER`/`API_PASSWORD` en .env
2. **No encuentra ficheros JSON:** Revisar que `data/` exista y tenga permisos
3. **Error de Docker/Moosh:** Verificar que contenedores estén corriendo
4. **Tests fallan:** Asegurar que `APP_ENV=test` y fixtures existan

---

## 12. Roadmap/Tareas Pendientes

Marcadas en `v0.1-README.md`:
- [x] Sistema de logs nuevo funcionando
- [x] Utilización de .env sin problemas
- [x] Sistema de tests
- [x] Prueba de descarga de archivos desde sigad y transformación en diccionario
- [ ] Comprobación de funcionamiento de la versión antigua sin modificar
- [ ] Prueba de matriculación de un alumno

Refactorización en curso:
- Migración de `main.py` (1800 líneas) a módulos más pequeños
- Separación de lógica de negocio de operaciones Moodle
- Modernización de clases legacy a dataclasses

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

**Última actualización:** Marzo 2026
**Autor del documento:** Agente IA
