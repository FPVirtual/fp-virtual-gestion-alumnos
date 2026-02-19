# Guía de Migración a Archivo Único

Este documento describe los cambios necesarios en el código actual para permitir el empaquetado como archivo Python único.

## Resumen de Cambios Necesarios

### 1. Config.py → Clase Config

**Estado actual:** Variables globales importadas desde `Config.py`

**Cambio requerido:** Convertir a clase con métodos de carga

```python
# ANTES (Config.py)
ENVIRONMENT = "test"
SUBDOMAIN = "test"
PATH = "/var/fp-distancia-gestion-usuarios-automatica"
# ... más variables

# DESPUÉS (embebido en archivo único)
class Config:
    ENVIRONMENT = "test"
    SUBDOMAIN = "test" 
    BASE_PATH = "/var/fp-distancia-gestion-usuarios-automatica"
    # ... más variables
    
    @classmethod
    def load_from_args(cls, args):
        # Carga desde argparse
        pass
    
    @classmethod
    def load_from_dict(cls, config_dict):
        # Carga desde diccionario
        pass
```

### 2. Actualizar imports en main.py

**Estado actual:**
```python
from Config import *                                    # ← Eliminar
from gestion_alumnos.conexion import *                 # ← Ya estará embebido
from gestion_alumnos.classes.alumno import *           # ← Ya estará embebido
from gestion_alumnos.classes.centro import *           # ← Ya estará embebido
from gestion_alumnos.classes.ciclo import *            # ← Ya estará embebido
from gestion_alumnos.classes.modulo import *           # ← Ya estará embebido
from utils import api_client, utils, json_parser       # ← Ya estará embebido
```

**Cambio requerido:**
```python
# Eliminar todas estas líneas - los módulos ya están embebidos
# Usar variables globales actualizadas desde Config
```

### 3. Actualizar referencias a variables de Config

**Estado actual:**
```python
# main.py línea 99
filename_md = PATH + "/logs/" + SUBDOMAIN + "/html/" + datetimeForFilename + SUBDOMAIN + ".md"
```

**Cambio requerido:** Usar `Config.PATH` en lugar de `PATH` global

```python
filename_md = Config.BASE_PATH + "/logs/" + Config.SUBDOMAIN + "/html/" + datetimeForFilename + Config.SUBDOMAIN + ".md"
```

Alternativa: Mantener variables globales sincronizadas:
```python
# Al inicio de main() después de load_from_args()
def refresh_globals():
    global PATH, SUBDOMAIN, ENVIRONMENT, API_BASE_URL, API_USER, API_PASSWORD
    global SMTP_HOSTS, SMTP_PORT, SMTP_USER, SMTP_PASSWORD
    global DB_USER, DB_PASS, DB_HOST, DB_NAME, REPORT_TO
    
    PATH = Config.BASE_PATH
    SUBDOMAIN = Config.SUBDOMAIN
    ENVIRONMENT = Config.ENVIRONMENT
    # ... etc
```

### 4. Eliminar imports relativos en todos los módulos

**Archivos a modificar:**
- `gestion_alumnos/main.py`
- `gestion_alumnos/utils/api_client.py`
- `gestion_alumnos/utils/json_parser.py`
- `gestion_alumnos/utils/moodle.py`
- `gestion_alumnos/utils/moosh.py`
- `gestion_alumnos/utils/email_service.py`
- `gestion_alumnos/utils/parser.py`
- `gestion_alumnos/utils/utils.py`

**Ejemplo de cambio en api_client.py:**
```python
# ANTES
from gestion_alumnos.models import Registro, Alumno
from gestion_alumnos.logger_config import logger

# DESPUÉS (eliminar - ya están en el mismo namespace)
# No se necesita import, los modelos ya están definidos arriba
```

### 5. Modificar utils/api_client.py para aceptar config

**Estado actual:** Usa variables de entorno directamente
```python
def obtener_estudiantes(idSolicitud: str) -> Optional[Registro]:
    BASE_URL = os.getenv("API_BASE_URL")
    user = os.getenv("API_USER")
    password = os.getenv("API_PASSWORD")
```

**Opción A:** Usar `Config` directamente
```python
def obtener_estudiantes(idSolicitud: str) -> Optional[Registro]:
    BASE_URL = Config.API_BASE_URL
    user = Config.API_USER
    password = Config.API_PASSWORD
```

**Opción B:** Aceptar parámetros opcionales (más flexible)
```python
def obtener_estudiantes(
    idSolicitud: str,
    base_url: str = None,
    user: str = None,
    password: str = None
) -> Optional[Registro]:
    BASE_URL = base_url or Config.API_BASE_URL
    user = user or Config.API_USER
    password = password or Config.API_PASSWORD
```

### 6. Modificar utils/email_service.py

**Estado actual:**
```python
def crear_email_service_desde_env():
    smtp_hosts = os.getenv('SMTP_HOSTS')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    # ...
```

**Cambio:** Usar `Config`
```python
def crear_email_service_desde_config():
    smtp_hosts = Config.SMTP_HOSTS
    smtp_port = int(Config.SMTP_PORT)
    smtp_user = Config.SMTP_USER
    smtp_password = Config.SMTP_PASSWORD
    # ...
```

## Instrucciones de Migración Paso a Paso

### Paso 1: Ejecutar el builder

```bash
python3 build_single_file.py
```

Esto generará `dist/gestion_alumnos_single.py` con todos los módulos concatenados.

### Paso 2: Probar el archivo generado

```bash
# Modo test (sin necesidad de credenciales reales)
python3 dist/gestion_alumnos_single.py --environment test --mock-data

# Con archivo .env existente
python3 dist/gestion_alumnos_single.py --env-file .env.test
```

### Paso 3: Verificar errores de importación

Si hay errores del tipo `NameError: name 'X' is not defined`:

1. Identificar qué variable/módulo falta
2. Verificar que esté en el orden correcto en `MODULES_ORDER`
3. Verificar que no se haya eliminado un import necesario

### Paso 4: Ajustar según necesidades

Para distribuir con configuración embebida (sin archivos .env):

1. Editar el builder para incluir configuración hardcodeada
2. O usar el modo programático desde otro script

```python
# Ejemplo de uso programático
from dist.gestion_alumnos_single import Config, gestion_alumnos_v1

Config.load_from_dict({
    "ENVIRONMENT": "produccion",
    "API_USER": "usuario",
    "API_PASSWORD": "password",
    # ... resto de config
})

gestion_alumnos_v1()
```

## Opciones de Configuración

### Opción A: Archivo .env externo (más seguro)
```bash
python3 gestion_alumnos_single.py --env-file .env.produccion
```

### Opción B: Variables de entorno del sistema
```bash
export API_USER="usuario"
export API_PASSWORD="password"
python3 gestion_alumnos_single.py --environment produccion
```

### Opción C: Todo por CLI
```bash
python3 gestion_alumnos_single.py \
  --environment produccion \
  --api-user usuario \
  --api-password password \
  --db-host 192.168.1.110
```

### Opción D: Embebida en el script (para distribución controlada)

Modificar el builder para incluir al final del HEADER:

```python
# Configuración embebida - MODIFICAR ANTES DE DISTRIBUIR
Config.ENVIRONMENT = "produccion"
Config.API_USER = "tu_usuario"
Config.API_PASSWORD = "tu_password"
# ... etc
refresh_globals()
```

## Ventajas del Archivo Único

1. **Portabilidad:** Un solo archivo Python, sin dependencias de estructura de directorios
2. **Distribución simple:** `scp gestion_alumnos_single.py servidor:/opt/`
3. **Ejecución directa:** No requiere instalación de paquete
4. **Docker simple:** COPY de un solo archivo
5. **Versionado:** Cada versión es un archivo autocontenido

## Limitaciones

1. **Tamaño:** El archivo será grande (~2000+ líneas)
2. **Debug:** Más difícil de debuggear (line numbers no coinciden)
3. **IDE:** Sin autocompletado de imports cruzados
4. **Tests:** Tests existentes necesitan adaptación

## Alternativa Recomendada: Zipapp

Si el archivo único es problemático, considera usar **zipapp**:

```bash
# Crear un .pyz ejecutable
python3 -m zipapp gestion_alumnos -p "/usr/bin/env python3" -o gestion_alumnos.pyz

# Ejecutar
python3 gestion_alumnos.pyz --env-file .env.produccion
```

Esto mantiene la estructura de módulos pero empaqueta todo en un solo archivo ejecutable.
