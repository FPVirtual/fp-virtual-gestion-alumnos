# AGENTS.md — Guía para Agentes de IA (v0.4)

> **Rama:** `v0.3-estructura-paquete-con-logs`  
> **Versión:** `0.4.1`  
> **Tests:** `62/62 ✅`  
> **Propósito:** Paquete Python autocontenido para gestión de alumnos Moodle. Cero SQL directo.  
> **Arquitectura:** Repository Pattern + Dependency Injection + Pydantic Settings + structlog + DuckDB  
> **Última actualización:** Junio 2026

---

## Índice de Contenidos

- [1. Visión General](#1-visión-general)
- [2. Stack Tecnológico](#2-stack-tecnológico)
- [3. Estructura del Proyecto](#3-estructura-del-proyecto)
- [4. Configuración](#4-configuración)
- [5. Convenciones de Código](#5-convenciones-de-código)
- [6. Arquitectura del Sistema](#6-arquitectura-del-sistema)
- [7. Repositorios y Fuentes](#7-repositorios-y-fuentes)
- [8. Motor de Análisis (DuckDB)](#8-motor-de-análisis-duckdb)
- [9. Testing](#9-testing)
- [10. Zipapp y Distribución](#10-zipapp-y-distribución)
- [11. Seguridad](#11-seguridad)
- [12. Estado Actual (v0.4.0)](#12-estado-actual-v040)
- [13. Próximos Pasos Sugeridos](#13-próximos-pasos-sugeridos)

---

## 1. Visión General

**Nombre:** `gestion-alumnos` v0.4.0

**Propósito:** Sincronizar alumnos entre SIGAD (Sistema de Información de Aragón) y Moodle (CampusDigitalFP). La arquitectura se ha modularizado en **cuatro capas independientes**:

1. **Extracción SIGAD** (`EstudianteRepository`) — API REST real, 100% funcional.
2. **Extracción Moodle** (`MoodleSource`) — abstracta, múltiples implementaciones:
   - `APICourseBasedMoodleSource` — itera ~1000 cursos vía API REST
   - `APISnapshotMoodleSource` — consume plugin PHP `local_fparagon` (1 llamada)
3. **Análisis** (`SyncAnalyzer`) — puro, sin dependencias de red. Usa DuckDB in-memory para comparar datasets y detectar deltas.
4. **Carga Moodle** (`MoodleSink`) — abstracta, implementada por `APIMoodleRepository` y `MooshMoodleRepository`.

El orquestador (`SyncOrchestrator`) **no sabe** qué implementaciones usa; las recibe inyectadas por el `DIContainer`.

**Idioma:** Español (código, comentarios, docstrings, nombres de funciones/variables).

---

## 2. Stack Tecnológico

- **Python 3.10+**
- **Poetry** — gestión de dependencias y empaquetado
- **zipapp** — distribución como archivo `.pyz` autocontenido
- **Pydantic v2 + pydantic-settings** — modelos y configuración con validación automática
- **structlog** — logging estructurado
- **requests** — llamadas HTTP a API SIGAD y API REST Moodle
- **smtplib** — envío de emails
- **DuckDB + pandas** — motor analítico in-memory para comparación de datasets
- **pytest + requests-mock** — testing

**Dependencias prohibidas:**
- ❌ `pymysql` — no hay acceso directo a BD
- ❌ `sqlalchemy` — no hay ORM ni SQL
- ❌ Comandos `mysql` vía `subprocess` — todo pasa por moosh, API REST o plugin PHP

**Dependencias nuevas en v0.4:**
- ✅ `duckdb>=1.1.0` — análisis de deltas
- ✅ `pandas>=2.0.0` — carga de datos en DuckDB

---

## 3. Estructura del Proyecto

```
gestion_alumnos/
├── __init__.py            # __version__, exports públicos
├── __main__.py            # python -m gestion_alumnos
├── cli.py                 # argparse: sync, extract, report, --driver, --apply
├── core/                  # Componentes fundamentales
│   ├── __init__.py
│   ├── config.py          # Pydantic Settings centralizada
│   ├── container.py       # DI Container: resuelve implementaciones
│   ├── exceptions.py      # Jerarquía de excepciones
│   └── logging.py         # structlog + nivel MARKDOWN (25)
├── models/                # Modelos Pydantic
│   ├── __init__.py
│   ├── alumno.py
│   ├── centro.py
│   ├── ciclo.py
│   ├── modulo.py
│   ├── registro.py
│   ├── moodle_snapshot.py    # MoodleUserRecord, MoodleEnrolmentRecord, MoodleSnapshot
│   └── sync_report.py        # SyncReport, NewUserDelta, EmailChangeDelta, ...
├── repositories/          # Repository Pattern
│   ├── __init__.py
│   ├── protocols.py       # Protocols: EstudianteRepository, MoodleRepository, MoodleSource, MoodleSink, EmailRepository
│   ├── sigad_repository.py
│   ├── moodle_moosh_repository.py
│   ├── moodle_api_repository.py
│   ├── email_repository.py
│   └── moodle_sources/    # Implementaciones de MoodleSource (solo lectura)
│       ├── __init__.py
│       ├── base.py
│       ├── api_course_based_source.py
│       └── api_snapshot_source.py
├── services/              # Lógica de negocio
│   ├── __init__.py
│   ├── gestion_service.py # LEGACY — orquestador antiguo (deprecado)
│   ├── sync_analyzer.py   # Motor de comparación DuckDB
│   ├── sync_applier.py    # Aplicador de cambios sobre MoodleSink
│   └── sync_orchestrator.py  # Orquestador de las 4 capas
├── templates/             # HTML empaquetados
│   ├── haFalladoElInforme.html
│   ├── informeAutomatizado.html
│   ├── matriculasAnadidas.html
│   ├── nombreUsuarioActualizado.html
│   └── nuevoUsuario.html
├── utils/
│   ├── __init__.py
│   └── helpers.py
└── data/
    └── usuarios_protegidos.csv   # IDs de usuarios no borrables (configurable por entorno)

moodle_plugin/             # Especificación del plugin PHP local_fparagon
└── local_fparagon/
    ├── db/
    │   └── services.php
    ├── classes/
    │   └── external/
    │       └── get_snapshot.php
    ├── version.php
    └── lang/
        └── en/
            └── local_fparagon.php

archive/                   # Código legacy v0.2 (main.py, Util.py, Conexion.py, classes/)
```

---

## 4. Configuración

### Variables de Entorno (`.env`)

```bash
# Entorno
ENVIRONMENT=dev|test|preproduccion|produccion
SUBDOMAIN=test|preproduccion|www

# Driver de Moodle (determina implementación de SINK)
MOODLE_DRIVER=moosh          # o "api"

# Estrategia de extracción de Moodle (determina implementación de SOURCE)
MOODLE_SOURCE_STRATEGY=api-course-based   # o "api-snapshot" (requiere plugin PHP)

# API SIGAD
API_BASE_URL=https://aplicaciones.aragon.es/pcrpe/services/alumnosFPDistancia
API_USER=...
API_PASSWORD=...
API_TIMEOUT=30
API_MAX_RETRIES=5

# Moosh (solo si MOODLE_DRIVER=moosh)
MOOSH_PATH=moosh
DOCKER_CONTAINER=

# API REST Moodle (solo si MOODLE_DRIVER=api)
MOODLE_API_URL=https://.../webservice/rest/server.php
MOODLE_API_TOKEN=...

# Email SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...
SMTP_USE_TLS=true

# Modo de envío de emails
EMAIL_MODE=direct   # "direct" = SMTP inmediato | "queue" = CSV para procesamiento externo

# Reportes
REPORT_TO="email1@ejemplo.com email2@ejemplo.com"
MAX_EMAILS_DIARIOS=10

# Seguridad — CSV de usuarios protegidos (uno por entorno si es necesario)
USUARIOS_PROTEGIDOS_CSV=gestion_alumnos/data/usuarios_protegidos.csv

# Rutas
BASE_PATH=/var/fp-distancia-gestion-usuarios-automatica/
```

**No hay variables de base de datos.** No se usa MySQL.

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

# Variables: snake_case
alumnos_sigad = []
nombre_fichero = ""

# Constantes: MAYÚSCULAS
BASE_URL = "..."
```

### Logging con structlog
```python
from gestion_alumnos.core.logging import get_logger

logger = get_logger(__name__)
logger.info("Procesando alumno", alumno_id=12345, documento="12345678A")
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

### Capas modulares (v0.4)

```
┌─────────────────────────────────────────────────────────────────┐
│                        SyncOrchestrator                          │
│  (coordina: SIGAD → MoodleSource → SyncAnalyzer → SyncApplier)  │
└─────────────────────────────────────────────────────────────────┘
         │              │                │              │
         ▼              ▼                ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   SIGAD      │ │ MoodleSource │ │ SyncAnalyzer │ │ MoodleSink   │
│ Repository   │ │ (abstracto)  │ │   (DuckDB)   │ │ (abstracto)  │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
                        ▲                                    ▲
         ┌──────────────┴──────────────┐        ┌────────────┴────────────┐
         │                             │        │                         │
┌─────────────────┐   ┌─────────────────┐  ┌──────────┐          ┌──────────┐
│ APICourseBased  │   │  APISnapshot    │  │   API    │          │  Moosh   │
│ MoodleSource    │   │  MoodleSource   │  │  Sink    │          │  Sink    │
└─────────────────┘   └─────────────────┘  └──────────┘          └──────────┘
```

### Protocolos separados

```python
# SOURCE: solo lectura
class MoodleSource(Protocol):
    def extract_users(self) -> list[dict]: ...
    def extract_courses(self) -> list[dict]: ...
    def extract_enrolments(self) -> list[dict]: ...
    def extract_all(self) -> MoodleSnapshot: ...

# SINK: solo escritura
class MoodleSink(Protocol):
    def create_user(self, username, email, nombre, apellido, password) -> int: ...
    def update_user(self, username, **campos) -> bool: ...
    def suspend_user(self, username) -> bool: ...
    def enrol_user_to_course(self, username, course_id) -> bool: ...
    def suspend_enrolment(self, username, course_id) -> bool: ...
    # ...
```

---

## 7. Repositorios y Fuentes

### EmailQueueRepository

Implementa el mismo protocolo `EmailRepository` que `EmailRepositoryImpl`, pero en lugar de enviar emails por SMTP los **encola en un CSV** (`csvs/email_queue.csv`).

```python
# Modo directo (por defecto)
EMAIL_MODE=direct  →  EmailRepositoryImpl

# Modo cola
EMAIL_MODE=queue   →  EmailQueueRepository
```

Ventajas del modo cola:
- Evita bloqueos por límites SMTP diarios
- Permite reejecutar emails fallidos
- Separa la generación de notificaciones del envío

### EmailQueueProcessor

Servicio que lee el CSV de emails pendientes y los envía usando `EmailRepositoryImpl`:

```python
from gestion_alumnos.services.email_queue_processor import EmailQueueProcessor

processor = EmailQueueProcessor()
stats = processor.process_all()  # {"enviados": N, "fallidos": M, "saltados": K}
```

Responde al comando CLI `process-emails`.

### SigadRepository (`EstudianteRepository`)
- `obtener_registro()` — descarga JSON con reintentos o carga desde `tests/data/`
- `buscar_por_documento(documento)` — búsqueda en registro
- Modo test: bypass de API, carga desde archivo local

### MoodleSource implementations

#### `APICourseBasedMoodleSource`
- `extract_users()` → `core_user_get_users` (1 llamada)
- `extract_courses()` → `core_course_get_courses` (1 llamada)
- `extract_enrolments()` → `core_enrol_get_enrolled_users` × N cursos (~1000 llamadas)
- **Pros:** Funciona en cualquier Moodle con API REST
- **Contras:** Lento para muchos cursos

#### `APISnapshotMoodleSource` (requiere plugin PHP)
- `extract_all()` → `local_fparagon_get_snapshot` (1 llamada)
- **Pros:** Instantáneo, una sola llamada
- **Contras:** Requiere instalar plugin `local_fparagon` en Moodle

### MoodleSink implementations

Ambos repositorios (`APIMoodleRepository`, `MooshMoodleRepository`) implementan `MoodleSink`.

| Operación | Moosh | API REST | Notas |
|-----------|-------|----------|-------|
| `create_user` | `moosh user-create` | `core_user_create_users` | ✅ |
| `update_user` | `moosh user-mod` | `core_user_update_users` | ✅ |
| `suspend_user` | `moosh user-mod --suspend 1` | `core_user_update_users suspended=1` | ✅ |
| `enrol_user_to_course` | `moosh course-enrol` | `enrol_manual_enrol_users` | ✅ |
| `suspend_enrolment` | ❌ No soportado | ❌ No soportado | Requiere plugin PHP |
| `remove_user_from_cohort` | ❌ Parcial | ❌ Parcial | Requiere plugin PHP |

### EmailQueueRepository

Métodos adicionales (no en el protocolo base):

| Método | Descripción |
|--------|-------------|
| `obtener_pendientes()` | Lista de `EmailJob` con status `pending` |
| `actualizar_estado(id, status, error)` | Actualiza estado en el CSV |
| `obtener_estadisticas()` | Conteos de pending/sent/failed |

Formato del CSV (`csvs/email_queue.csv`):
```csv
id,template_name,recipient,subject,template_data,status,created_at,sent_at,error
uuid-1,nuevoUsuario.html,juan@ejemplo.com,FP virtual...,{"nombre":"Juan",...},pending,2026-06-05T10:00:00,,
```

---

## 8. Motor de Análisis (DuckDB)

`SyncAnalyzer` recibe `Registro` (SIGAD) + `MoodleSnapshot` y devuelve `SyncReport`.

### Tablas DuckDB internas
```sql
sigad_users(documento, id_tipo_documento, nombre, apellido1, apellido2, email)
sigad_enrolments(documento, codigo_centro, siglas_ciclo, id_materia, siglas_modulo)

moodle_users(id, username, email, firstname, lastname, suspended)
moodle_enrolments(username, course_id, shortname, status)
```

### Deltas detectados
| Delta | SQL Pattern |
|-------|-------------|
| Altas | `LEFT JOIN moodle_users ON lower(username)=documento WHERE moodle.id IS NULL` |
| Bajas | `LEFT JOIN sigad_users ON documento=lower(username) WHERE sigad.documento IS NULL` |
| Cambio email | `JOIN ... WHERE lower(sigad.email) <> lower(moodle.email)` |
| Cambio nombre | `JOIN ... WHERE sigad.nombre <> moodle.firstname ...` |
| Cambio username | `JOIN por email WHERE username cambia` (NIE→DNI) |
| Nueva matrícula | `LEFT JOIN sigad_enrolments → moodle_enrolments WHERE moodle.course IS NULL` |
| Matrícula eliminada | `LEFT JOIN moodle_enrolments → sigad_enrolments WHERE sigad.modulo IS NULL` |

---

## 9. Testing

### Estrategia
- **Unitarios:** `SyncAnalyzer` con datos fake en DuckDB (sin red).
- **Integración:** Fuentes de Moodle con mocks de requests.
- **Conformidad de Protocols:** Verificar que implementaciones cumplen `MoodleSource`/`MoodleSink`.

### Ejecutar tests

```bash
# Todos
pytest tests/ -v

# Solo analizador (puro, sin red)
pytest tests/test_sync_analyzer.py -v

# Solo modelos
pytest tests/test_models.py -v
```

### Fixtures principales (`conftest.py`)
- `settings_test` — Configuración de test
- `sample_alumno`, `sample_registro` — Datos de ejemplo
- `mock_moosh` — Mock de subprocess para moosh

---

## 10. Zipapp y Distribución

### Generar zipapp

```bash
python scripts/build_zipapp.py
# Resultado: dist/gestion_alumnos.pyz
```

### Ejecutar zipapp

```bash
# Local
python3 dist/gestion_alumnos.pyz --env-file .env.produccion sync --apply

# Dentro del contenedor Moodle
docker cp dist/gestion_alumnos.pyz moodle:/opt/
docker exec moodle python3 /opt/gestion_alumnos.pyz sync --apply
```

---

## 11. Seguridad

### Credenciales
- **NUNCA** commitear `.env` con credenciales reales.
- Usar `.env.example` como plantilla.
- En producción, usar variables de entorno del sistema o Docker secrets.

### Usuarios protegidos
Ya no están hardcodeados. Se cargan desde un **CSV configurable**:
```bash
USUARIOS_PROTEGIDOS_CSV=gestion_alumnos/data/usuarios_protegidos.csv
```

Formato del CSV:
```csv
user_id
1
2
3
...
```

Esto permite tener un CSV diferente por entorno (test, preproducción, producción).

### Validación de inputs
- `documento` (DNI/NIE): regex `[0-9]{8}[A-Z]` o `[XYZ][0-9]{7}[A-Z]`
- `email`: formato válido
- `username`: minúsculas, sin espacios

---

## 12. Estado Actual (v0.4.1)

| Componente | Estado | Tests |
|-----------|--------|-------|
| Core (config, logging, DI) | ✅ | 9/9 |
| Modelos Pydantic | ✅ | 10/10 |
| SIGAD Repository | ✅ | 6/6 |
| Moosh Repository | ✅ | 3/3 |
| API Repository | ✅ Implementado | Pendiente tests de integración |
| Email Repository (SMTP directo) | ✅ Implementado | Pendiente tests |
| **EmailQueueRepository (CSV)** | ✅ **Nuevo** | **15/15** |
| **EmailQueueProcessor** | ✅ **Nuevo** | Incluido en tests de cola |
| **SyncAnalyzer (DuckDB)** | ✅ | **6/6** |
| MoodleSource (API Course-based) | ✅ | — |
| MoodleSource (API Snapshot) | ✅ | Requiere plugin PHP |
| SyncApplier | 🟡 Implementado | Pendiente tests |
| SyncOrchestrator | ✅ | — |
| CLI (`--apply`, `--source-strategy`, `report`, `process-emails`) | ✅ | — |
| ReportLogger (informes `.md`) | ✅ **Nuevo** | **6/6** |
| Zipapp | ✅ | Funcional |

**Total tests: 84/84 ✅**

---

## 13. Próximos Pasos Sugeridos

1. **Desplegar plugin PHP** `local_fparagon` en Moodle (producción + preproducción)
2. **Tests de integración** para `APICourseBasedMoodleSource` y `APISnapshotMoodleSource`
3. **Tests end-to-end** del `SyncOrchestrator` con mocks completos
4. **Mejorar `SyncApplier`** con batching de matrículas y reintentos
5. ~~**Generar informes Markdown** del `SyncReport`~~ ✅ Completado (`ReportLogger` + `SyncReport.to_markdown()`)
6. ~~**Cola de emails en CSV**~~ ✅ Completado (`EmailQueueRepository` + `EmailQueueProcessor`)
7. **Tag `v0.4.1`** y merge a `main`

---

**Autor:** Agente IA  
**Rama:** `v0.4-arquitectura-modular-duckdb`  
**Commit:** `TBD`
