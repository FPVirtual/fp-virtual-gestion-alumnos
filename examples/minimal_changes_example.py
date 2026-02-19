#!/usr/bin/env python3
"""
Ejemplo de modificaciones mínimas para soportar archivo único.
Este código muestra qué cambios son necesarios en los archivos existentes.
"""

# =============================================================================
# EJEMPLO 1: Config.py → Modo compatible con archivo único
# =============================================================================

"""
ARCHIVO: Config.py (modificado)

ANTES:
------
ENVIRONMENT = os.getenv("ENVIRONMENT", "test")
SUBDOMAIN = os.getenv("SUBDOMAIN", "test")
PATH = os.getenv("PATH", "/var/fp-distancia-gestion-usuarios-automatica")
...

DESPUÉS:
--------
"""
import os

class _Config:
    """Configuración interna - usa vars de entorno por defecto"""
    ENVIRONMENT = os.getenv("ENVIRONMENT", "test")
    SUBDOMAIN = os.getenv("SUBDOMAIN", "test")
    PATH = os.getenv("PATH", "/var/fp-distancia-gestion-usuarios-automatica")
    
    # API
    API_BASE_URL = os.getenv("API_BASE_URL", "")
    API_USER = os.getenv("API_USER", "")
    API_PASSWORD = os.getenv("API_PASSWORD", "")
    
    # SMTP
    SMTP_HOSTS = os.getenv("SMTP_HOSTS", "")
    SMTP_PORT = os.getenv("SMTP_PORT", "587")
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    
    # DB
    DB_USER = os.getenv("DB_USER", "")
    DB_PASS = os.getenv("DB_PASS", "")
    DB_HOST = os.getenv("DB_HOST", "")
    DB_NAME = os.getenv("DB_NAME", "")
    REPORT_TO = os.getenv("REPORT_TO", "")

# Variables globales para compatibilidad con código existente
ENVIRONMENT = _Config.ENVIRONMENT
SUBDOMAIN = _Config.SUBDOMAIN
PATH = _Config.PATH
API_BASE_URL = _Config.API_BASE_URL
API_USER = _Config.API_USER
API_PASSWORD = _Config.API_PASSWORD
SMTP_HOSTS = _Config.SMTP_HOSTS
SMTP_PORT = _Config.SMTP_PORT
SMTP_USER = _Config.SMTP_USER
SMTP_PASSWORD = _Config.SMTP_PASSWORD
DB_USER = _Config.DB_USER
DB_PASS = _Config.DB_PASS
DB_HOST = _Config.DB_HOST
DB_NAME = _Config.DB_NAME
REPORT_TO = _Config.REPORT_TO


def update_globals():
    """Actualiza variables globales desde _Config (útil después de cambiar config)"""
    global ENVIRONMENT, SUBDOMAIN, PATH, API_BASE_URL, API_USER, API_PASSWORD
    global SMTP_HOSTS, SMTP_PORT, SMTP_USER, SMTP_PASSWORD
    global DB_USER, DB_PASS, DB_HOST, DB_NAME, REPORT_TO
    
    ENVIRONMENT = _Config.ENVIRONMENT
    SUBDOMAIN = _Config.SUBDOMAIN
    PATH = _Config.PATH
    API_BASE_URL = _Config.API_BASE_URL
    API_USER = _Config.API_USER
    API_PASSWORD = _Config.API_PASSWORD
    SMTP_HOSTS = _Config.SMTP_HOSTS
    SMTP_PORT = _Config.SMTP_PORT
    SMTP_USER = _Config.SMTP_USER
    SMTP_PASSWORD = _Config.SMTP_PASSWORD
    DB_USER = _Config.DB_USER
    DB_PASS = _Config.DB_PASS
    DB_HOST = _Config.DB_HOST
    DB_NAME = _Config.DB_NAME
    REPORT_TO = _Config.REPORT_TO


# =============================================================================
# EJEMPLO 2: main.py → Modo compatible con archivo único
# =============================================================================

"""
ARCHIVO: main.py (cambios mínimos)

ANTES:
------
from Config import *
from gestion_alumnos.conexion import *
from gestion_alumnos.classes.alumno import *
...

def gestion_alumnos():
    global filename_md
    filename_md = PATH + "/logs/" + SUBDOMAIN + "/html/" + ...


DESPUÉS:
--------
"""

def gestion_alumnos_compatible(env_file=None, **kwargs):
    """
    Versión compatible que puede recibir configuración por parámetros.
    
    Args:
        env_file: Ruta a archivo .env (opcional)
        **kwargs: Cualquier variable de configuración para sobreescribir
    """
    from dotenv import load_dotenv
    
    # 1. Cargar desde archivo si se proporciona
    if env_file and os.path.exists(env_file):
        load_dotenv(env_file)
        # Recargar _Config desde entorno
        for key in dir(_Config):
            if not key.startswith('_') and key.isupper():
                env_val = os.getenv(key)
                if env_val is not None:
                    setattr(_Config, key, env_val)
    
    # 2. Aplicar overrides por parámetros
    for key, value in kwargs.items():
        if hasattr(_Config, key):
            setattr(_Config, key, value)
    
    # 3. Actualizar variables globales
    update_globals()
    
    # 4. Ahora el código original funciona sin cambios
    global filename_md
    filename_md = PATH + "/logs/" + SUBDOMAIN + "/html/" + datetime.now().strftime("%Y%m%d_%H%M%S") + SUBDOMAIN + ".md"
    
    # ... resto del código sin cambios ...


# =============================================================================
# EJEMPLO 3: api_client.py → Modo compatible
# =============================================================================

"""
ARCHIVO: utils/api_client.py (cambios mínimos)

ANTES:
------
import os
from gestion_alumnos.models import Registro, Alumno
from gestion_alumnos.logger_config import logger

BASE_URL = os.getenv("API_BASE_URL")
user = os.getenv("API_USER")
password = os.getenv("API_PASSWORD")


DESPUÉS:
--------
"""

def get_api_config():
    """Obtiene config de API desde múltiples fuentes posibles"""
    # Opción 1: Usar _Config si existe (modo archivo único)
    if '_Config' in globals():
        return {
            'base_url': _Config.API_BASE_URL,
            'user': _Config.API_USER,
            'password': _Config.API_PASSWORD,
        }
    
    # Opción 2: Fallback a variables de entorno (modo normal)
    import os
    return {
        'base_url': os.getenv("API_BASE_URL"),
        'user': os.getenv("API_USER"),
        'password': os.getenv("API_PASSWORD"),
    }


def obtener_estudiantes_compatible(idSolicitud: str) -> Optional['Registro']:
    """Versión compatible que no depende de imports globales"""
    config = get_api_config()
    
    if not config['base_url']:
        raise ValueError("API_BASE_URL no configurado")
    
    # ... resto de la función usando config['base_url'], etc.
    pass


# =============================================================================
# EJEMPLO 4: Punto de entrada universal
# =============================================================================

def main_universal():
    """
    Punto de entrada que funciona en ambos modos:
    - Como parte del proyecto estructurado
    - Como archivo único empaquetado
    """
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--env-file', help='Archivo .env')
    parser.add_argument('--environment', choices=['test', 'preproduccion', 'produccion'])
    parser.add_argument('--mock-data', action='store_true')
    args = parser.parse_args()
    
    # Preparar kwargs desde CLI
    kwargs = {}
    if args.environment:
        kwargs['ENVIRONMENT'] = args.environment
        kwargs['SUBDOMAIN'] = args.environment if args.environment != 'produccion' else 'www'
    
    # Ejecutar
    gestion_alumnos_compatible(env_file=args.env_file, **kwargs)


if __name__ == "__main__":
    main_universal()
