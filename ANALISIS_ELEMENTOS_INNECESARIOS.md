# Análisis de Elementos Innecesarios o No Usados

> **Fecha de análisis:** 21 de febrero de 2026  
> **Proyecto:** fp-distancia-gestion-usuarios-automatica (gestion-alumnos v0.1.0)  
> **Generado por:** Revisión automática del código

---

## 📋 Resumen Ejecutivo

| Categoría | Cantidad | Prioridad |
|-----------|----------|-----------|
| Archivos vacíos | 2 | 🔴 Alta |
| Imports rotos/incorrectos | 5 | 🔴 Alta |
| Código duplicado | 5 | 🟡 Media |
| Código muerto (no usado) | 7 | 🟡 Media |
| Dependencias sospechosas | 15+ | 🟢 Baja |

---

## 1. 🔴 Código Roto/No Funcional (Prioridad Alta)

### 1.1 Archivos Vacíos

| Archivo | Líneas | Problema | Acción Recomendada |
|---------|--------|----------|-------------------|
| `gestion_alumnos/__main__.py` | 0 | Archivo completamente vacío | Completar con punto de entrada o eliminar |
| `gestion_alumnos/classes/__init__.py` | 0 | Archivo vacío | Añadir imports o eliminar directorio classes/ |

### 1.2 Imports Rotos o Incorrectos

| Archivo | Línea | Import Problemático | Corrección |
|---------|-------|---------------------|------------|
| `classes/alumno.py` | 3 | `from gestion_alumnos.util import crea_emails_dominio` | La función es `creaEmailsDominio` (camelCase) |
| `utils/parser.py` | 3 | `from models import Registro` | `from gestion_alumnos.models import Registro` |
| `utils/json_parser.py` | 6 | `from models import Registro` | `from gestion_alumnos.models import Registro` |
| `main.py` | 12 | `from utils import api_client, json_parser` | `from gestion_alumnos.utils import api_client, json_parser` |
| `scripts/run_dev.py` | 12 | `from gestion_alumnos.main import gestion_alumnos_v1` | La función no existe; usar `gestion_alumnos` |

### 1.3 Referencias a Funciones Inexistentes

```python
# En scripts/run_dev.py:
from gestion_alumnos.main import gestion_alumnos_v1  # ❌ No existe
gestion_alumnos_v1()  # ❌ Solo existe gestion_alumnos()

# En build_single_file.py:
gestion_alumnos_v1()  # ❌ Referenciado en ENTRY_POINT
```

---

## 2. 🟡 Código Duplicado/Redundante

### 2.1 Modelos Duplicados (Legacy vs Modernos)

**Problema:** Existen dos implementaciones completas de los modelos de datos:

| Modelo | Implementación Legacy (clases/) | Implementación Moderna (models.py) |
|--------|--------------------------------|-----------------------------------|
| Alumno | `classes/alumno.py` (47 líneas, dataclass) | `models.py` líneas 30-38 (dataclass) |
| Centro | `classes/centro.py` (30 líneas, clase) | `models.py` líneas 22-26 (dataclass) |
| Ciclo | `classes/ciclo.py` (37 líneas, clase) | `models.py` líneas 13-19 (dataclass) |
| Módulo | `classes/modulo.py` (22 líneas, clase) | `models.py` líneas 6-11 (dataclass) |

**Recomendación:** Eliminar `gestion_alumnos/classes/` y mantener solo `models.py`.

**Archivos afectados que necesitan actualización:**
- `utils/json_parser.py` - usa imports de `classes`
- `main.py` - usa imports de `classes`
- `examples/minimal_changes_example.py` - usa imports de `classes`
- `build_single_file.py` - incluye `classes/alumno.py` en MODULES_ORDER

### 2.2 Funciones Duplicadas

| Función | Ubicación | Líneas | Problema |
|---------|-----------|--------|----------|
| `alta_nueva` | `utils/alumnado.py` | 30-91 | Definición completa con SQLAlchemy |
| `alta_nueva` | `utils/alumnado.py` | 152-184 | Segunda definición diferente (pipeline) |

**Nota:** La segunda definición sobrescribe a la primera. Son funciones con el mismo nombre pero comportamiento diferente.

### 2.3 Scripts de Ejecución Casi Idénticos

| Archivo | Diferencia |
|---------|------------|
| `scripts/run_pre.py` | `env = os.getenv("APP_ENV", "preproduccion")` |
| `scripts/run_pro.py` | `env = os.getenv("APP_ENV", "produccion")` |

**Recomendación:** Consolidar en un único script con argumento de entorno.

### 2.4 Código Redundante en Scripts

```python
# scripts/run_dev.py líneas 5-6 y 14-15:
proyecto_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(proyecto_root))  # Duplicado
```

---

## 3. 🟠 Código No Usado (Muerto)

### 3.1 Archivos Completos No Referenciados

| Archivo | Líneas | Descripción | Estado |
|---------|--------|-------------|--------|
| `utils/temp_alumnado_loader.py` | 52 | Clase `TempAlumnadoLoader` para cargar datos temporales | ❌ No referenciado en ningún lado |
| `utils/utils.py` | 18 | Funciones de validación DNI/NIE | ❌ No referenciado |
| `utils/verificacion_log.py` | 70 | Función `extraer_resumen_final` | ⚠️ Solo usada en tests |
| `utils/email_service_example.py` | 268 | Ejemplos de uso de EmailService | 📚 Documentación/ejemplos |
| `conexion.py` | 30 | Clase `Conexion` con `http.client` | ❌ Reemplazado por `api_client.py` que usa `requests` |

### 3.2 Funciones No Usadas dentro de Archivos

| Archivo | Función | Líneas | Estado |
|---------|---------|--------|--------|
| `utils/alumnado.py` | `gest_reincorporaciones()` | 6-17 | Incompleta (solo `return 0`) |
| `utils/alumnado.py` | `hash_moodle_password()` | 20-27 | ✅ Usada, pero dependencia `bcrypt` puede ser innecesaria |
| `utils/alumnado.py` | `matricular_en_cohorte()` | 94-148 | ⚠️ Incompleta (usa variables no importadas) |
| `utils/json_parser.py` | `procesaJsonEstudiantes()` | 47-125 | ❌ Reemplazada por `cargar_fichero_estudiantes()` + `parse_json()` |

### 3.3 Variables Globales No Usadas

```python
# En gestion_alumnos/main.py:
filename_md = ""   # Línea 14 - inicializada pero no usada
filename_csv = ""  # Línea 15 - inicializada pero no usada

# Código comentado (líneas 28-29):
# moodle = get_moodle(os.getenv("SUBDOMAIN"))[0]
# alumnos_moodle = get_alumnos_moodle_no_borrados(moodle)
```

---

## 4. 🔵 Imports No Usados o Innecesarios

### 4.1 Imports con `*` No Específicos

```python
# gestion_alumnos/main.py:
from gestion_alumnos.classes.alumno import *    # Importa todo, ¿se usa todo?
from gestion_alumnos.classes.centro import *    # ¿Realmente necesario?
from gestion_alumnos.classes.ciclo import *     # ¿Realmente necesario?
from gestion_alumnos.classes.modulo import *    # ¿Realmente necesario?
from gestion_alumnos.conexion import *          # Reemplazado por api_client
```

**Recomendación:** Usar imports específicos en lugar de `*`.

### 4.2 Imports en Código No Usado

```python
# utils/alumnado.py:
import bcrypt    # Usado, pero ¿es necesario bcrypt completo?
from requests import Session  # Importado pero no usado en funciones principales

# Funciones usan SQLAlchemy pero no están importadas correctamente:
# - MoodleUser
# - UserInfoData
# - Cohort
# - CohortMember
# - IntegrityError
# - select, and_
```

---

## 5. 🟣 Hardcoded Values y Configuración

### 5.1 IDs Hardcodeados

```python
# gestion_alumnos/main.py línea 26:
usuarios_moodle_no_borrables = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 
    11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 
    26, 27, 28, 29, 30, 31, 32, 33, 3725, 3729, 3730, 7152, 7490, 
    7491, 11720, 12270, 12272]  # 41 IDs
```

**Recomendación:** Mover a archivo de configuración.

### 5.2 Configuración en build_single_file.py

```python
# MODULES_ORDER incluye classes/alumno.py pero no los otros classes/
# Esto es inconsistente
MODULES_ORDER = [
    ...
    'gestion_alumnos/classes/modulo.py',
    'gestion_alumnos/classes/ciclo.py',
    'gestion_alumnos/classes/centro.py',
    'gestion_alumnos/classes/alumno.py',  # Solo este en orden específico
    ...
]
```

---

## 6. 🟤 Dependencias Potencialmente Innecesarias

### 6.1 Dependencias No Referenciadas en Código

Las siguientes dependencias en `pyproject.toml` no parecen ser importadas directamente:

| Paquete | Versión | Uso Detectado |
|---------|---------|---------------|
| `asn1crypto` | ^1.5.1 | ❌ No encontrado |
| `chardet` | ^5.2.0 | ❌ No encontrado |
| `cryptography` | ^46.0.3 | ❌ No encontrado (posible dependencia transitiva) |
| `distro-info` | ^1.0 | ❌ No encontrado |
| `httplib2` | ^0.31.0 | ❌ No encontrado (usa `requests`) |
| `keyring` | ^25.7.0 | ❌ No encontrado |
| `keyrings-alt` | ^5.0.2 | ❌ No encontrado |
| `launchpadlib` | ^2.1.0 | ❌ No encontrado |
| `lazr-restfulclient` | ^0.14.6 | ❌ No encontrado |
| `lazr-uri` | ^1.0.7 | ❌ No encontrado |
| `netifaces` | ^0.11.0 | ❌ No encontrado |
| `notify2` | ^0.3.1 | ❌ No encontrado |
| `pam` | ^0.2.0 | ❌ No encontrado |
| `pexpect` | ^4.9.0 | ❌ No encontrado |
| `pillow` | ^12.0.0 | ❌ No encontrado |
| `py3dns` | ^4.0.2 | ❌ No encontrado |
| `pycurl` | ^7.45.7 | ❌ No encontrado (usa `requests`) |

### 6.2 Comando para Verificar Dependencias Reales

```bash
# Mostrar árbol de dependencias
poetry show --tree

# Ver qué archivos importan cada paquete
pip install pipdeptree
pipdeptree --packages <nombre-paquete>
```

---

## 7. 📁 Archivos de Documentación

### 7.1 Posible Consolidación

Los siguientes archivos de documentación podrían consolidarse:

```
scripts/analisis_rendimiento.md         → Consolidar en AGENTS.md
scripts/estimacion_tiempos_realista.md  → Consolidar en AGENTS.md  
scripts/README_SIGAD_SYNC.md            → Mantener (específico)
MIGRACION_SINGLE_FILE.md               → Mantener (específico)
v0.1-README.md                         → Consolidar en README.md
AGENTS.md                              ✅ Principal para agentes
README.md                              ✅ Principal para usuarios
```

---

## 8. 📊 Estadísticas de Código

### 8.1 Distribución por Directorio

```
gestion_alumnos/
├── __init__.py              24 líneas  ✅ Usado
├── __main__.py               0 líneas  ❌ Vacío
├── main.py                  64 líneas  ✅ Principal
├── models.py                44 líneas  ✅ Recomendado
├── conexion.py              29 líneas  ❌ Legacy (http.client)
├── util.py                 950 líneas  ✅ Usado (conversionLFPaLOE)
├── logger_config.py         81 líneas  ✅ Usado
├── classes/                136 líneas  ❌ Legacy (duplicado)
│   ├── alumno.py           47 líneas
│   ├── centro.py           30 líneas
│   ├── ciclo.py            37 líneas
│   └── modulo.py           22 líneas
└── utils/                2,907 líneas  
    ├── __init__.py         15 líneas   ✅ Usado
    ├── api_client.py      160 líneas   ✅ Usado
    ├── json_parser.py     124 líneas   ✅ Usado (parcialmente)
    ├── moodle.py           75 líneas   ✅ Usado
    ├── moosh.py            52 líneas   ✅ Usado
    ├── parser.py           52 líneas   ✅ Usado
    ├── email_service.py   562 líneas   ✅ Usado
    ├── email_service_example.py 268 líneas  📚 Ejemplos
    ├── alumnado.py        186 líneas   ⚠️ Incompleto
    ├── temp_alumnado_loader.py 52 líneas  ❌ No usado
    ├── verificacion_log.py  69 líneas  ⚠️ Solo tests
    ├── utils.py            18 líneas   ❌ No usado
    ├── sigad_db_sync.py   539 líneas   ✅ Usado
    └── sigad_aplicar_cambios.py 736 líneas  ✅ Usado

tests/                      ~500 líneas  ✅ Suite de tests completa
examples/                   ~326 líneas  📚 Ejemplos y documentación
scripts/                    ~300 líneas  ✅ Scripts auxiliares útiles
```

---

## 9. ✅ Recomendaciones Prioritarias

### Prioridad 1: Arreglar Código Roto (🔴 Alta)

1. [ ] Corregir import en `classes/alumno.py`: cambiar `crea_emails_dominio` → `creaEmailsDominio`
2. [ ] Corregir imports absolutos en `utils/parser.py` y `utils/json_parser.py`
3. [ ] Corregir import en `main.py`: `from utils import` → `from gestion_alumnos.utils import`
4. [ ] Crear función `gestion_alumnos_v1` en `main.py` o actualizar `run_dev.py`
5. [ ] Completar o eliminar `__main__.py`

### Prioridad 2: Consolidar Modelos (🟡 Media)

1. [ ] Eliminar directorio `gestion_alumnos/classes/`
2. [ ] Actualizar `utils/json_parser.py` para usar `models.py`
3. [ ] Actualizar `main.py` para usar `models.py`
4. [ ] Actualizar `build_single_file.py` MODULES_ORDER

### Prioridad 3: Eliminar Código Muerto (🟡 Media)

1. [ ] Eliminar `conexion.py` (reemplazado por `api_client.py`)
2. [ ] Eliminar `utils/temp_alumnado_loader.py`
3. [ ] Eliminar `utils/utils.py` (o mover funciones útiles a `util.py`)
4. [ ] Eliminar función `procesaJsonEstudiantes` de `json_parser.py`
5. [ ] Consolidar o eliminar `utils/alumnado.py` (funciones incompletas)

### Prioridad 4: Revisar Dependencias (🟢 Baja)

1. [ ] Ejecutar `poetry show --tree` para identificar dependencias transitivas
2. [ ] Eliminar paquetes no usados del `pyproject.toml`
3. [ ] Considerar mover `bcrypt` a dependencias opcionales si solo se usa en código muerto

---

## 10. 🔄 Acciones Post-Limpieza

Después de realizar la limpieza:

```bash
# 1. Verificar que los tests siguen pasando
APP_ENV=test poetry run pytest

# 2. Verificar imports
python -c "import gestion_alumnos; print('✅ Imports OK')"

# 3. Verificar scripts de ejecución
poetry run dev --help  # o equivalente

# 4. Actualizar build_single_file.py si es necesario
python build_single_file.py
```

---

*Este análisis fue generado automáticamente. Se recomienda revisar manualmente antes de aplicar cambios.*
