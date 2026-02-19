#!/usr/bin/env python3
"""
Ejemplo de uso del archivo único con configuración embebida.
Esto demuestra cómo usar el script sin archivos .env externos.
"""

# Ejemplo 1: Uso como módulo importado
import sys
sys.path.insert(0, '/ruta/al/archivo/unico')

from gestion_alumnos_single import Config, gestion_alumnos_v1

# Configurar todo por código
config = {
    "ENVIRONMENT": "preproduccion",
    "SUBDOMAIN": "preproduccion",
    "BASE_PATH": "/tmp/mi-proyecto",
    "API_BASE_URL": "https://aplicaciones.aragon.es/pcrpe/services/alumnosFPDistancia",
    "API_USER": "mi_usuario",
    "API_PASSWORD": "mi_password",
    "SMTP_HOSTS": "smtp.gmail.com",
    "SMTP_PORT": "587",
    "SMTP_USER": "mi_email@gmail.com",
    "SMTP_PASSWORD": "mi_app_password",
    "DB_HOST": "192.168.1.110",
    "DB_NAME": "fpvirtual_pre",
    "DB_USER": "admin",
    "DB_PASS": "password_db",
}

Config.load_from_dict(config)
gestion_alumnos_v1()


# =============================================================================
# Ejemplo 2: Configuración embebida en el propio archivo (sin variables externas)
# =============================================================================

"""
Si quieres distribuir el script con la configuración incluida, modifica
el builder para incluir este código al final de HEADER:

DEFAULT_CONFIG_EMBEDDED = '''
# === CONFIGURACIÓN EMBEBIDA (descomenta para usar) ===
Config.ENVIRONMENT = "preproduccion"
Config.SUBDOMAIN = "preproduccion"
Config.BASE_PATH = "/var/gestion-alumnos"
Config.API_BASE_URL = "https://aplicaciones.aragon.es/..."
Config.API_USER = "usuario"
Config.API_PASSWORD = "password"
Config.SMTP_HOSTS = "smtp.gmail.com"
Config.SMTP_USER = "email"
Config.SMTP_PASSWORD = "pass"
Config.DB_HOST = "192.168.1.110"
Config.DB_NAME = "moodle_db"
Config.DB_USER = "admin"
Config.DB_PASS = "password"
refresh_globals()
'''

Luego en el builder, después de escribir HEADER, añade:
    f.write(DEFAULT_CONFIG_EMBEDDED)
"""


# =============================================================================
# Ejemplo 3: Uso con archivo .env embebido como string
# =============================================================================

EMBEDDED_ENV = """
# Este contenido se puede incluir al final del archivo generado
# y cargarse con load_dotenv(stream=io.StringIO(EMBEDDED_ENV))

ENVIRONMENT=produccion
SUBDOMAIN=www
PATH=/var/fp-distancia-gestion-usuarios-automatica

API_BASE_URL=https://aplicaciones.aragon.es/pcrpe/services/alumnosFPDistancia
API_USER=usuario_real
API_PASSWORD=password_real

SMTP_HOSTS=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=notificaciones@fpvirtualaragon.es
SMTP_PASSWORD=app_password

DB_HOST=192.168.1.110
DB_NAME=www_fpvirtualaragon_es
DB_USER=admin
DB_PASS=db_password

REPORT_TO=admin@fpvirtualaragon.es soporte@fpvirtualaragon.es
"""

# Para usarlo:
# load_dotenv(stream=io.StringIO(EMBEDDED_ENV))
