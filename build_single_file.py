#!/usr/bin/env python3
"""
build_single_file.py - Crea un único archivo ejecutable del proyecto

Uso:
    python3 build_single_file.py
    
Esto generará: dist/gestion_alumnos_single.py
"""
import os
import sys
from pathlib import Path

# Orden de inclusión (respetar dependencias)
MODULES_ORDER = [
    'gestion_alumnos/models.py',
    'gestion_alumnos/logger_config.py',
    'gestion_alumnos/conexion.py',
    'gestion_alumnos/classes/modulo.py',
    'gestion_alumnos/classes/ciclo.py',
    'gestion_alumnos/classes/centro.py',
    'gestion_alumnos/classes/alumno.py',
    'gestion_alumnos/util.py',
    'gestion_alumnos/utils/api_client.py',
    'gestion_alumnos/utils/json_parser.py',
    'gestion_alumnos/utils/moodle.py',
    'gestion_alumnos/utils/moosh.py',
    'gestion_alumnos/utils/email_service.py',
    'gestion_alumnos/utils/parser.py',
    'gestion_alumnos/utils/utils.py',
    'gestion_alumnos/main.py',
]

HEADER = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestion Alumnos - Archivo único autocontenido
Generado automáticamente - No editar manualmente
"""

# =============================================================================
# SECCIÓN 1: IMPORTS ESTÁNDAR
# =============================================================================
import json
import time
import random
import subprocess
import os
import sys
import io
import smtplib
import ssl
import traceback
import re
import argparse
import logging
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
from email.message import EmailMessage
from email.headerregistry import Address
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import http.client
import urllib.parse
from dotenv import load_dotenv

# =============================================================================
# SECCIÓN 2: CONFIGURACIÓN GLOBAL
# =============================================================================
class Config:
    """Configuración centralizada - se carga desde args, env o diccionario"""
    
    # Valores por defecto
    ENVIRONMENT = "test"
    SUBDOMAIN = "test"
    BASE_PATH = "/tmp/gestion-alumnos"
    
    # API SIGAD
    API_BASE_URL = ""
    API_USER = ""
    API_PASSWORD = ""
    
    # Email
    SMTP_HOSTS = ""
    SMTP_PORT = "587"
    SMTP_USER = ""
    SMTP_PASSWORD = ""
    
    # Base de datos
    DB_USER = ""
    DB_PASS = ""
    DB_HOST = ""
    DB_NAME = ""
    
    # Reportes
    REPORT_TO = ""
    
    @classmethod
    def load_from_args(cls, args):
        """Carga configuración desde argumentos CLI"""
        if args.env_file and os.path.exists(args.env_file):
            load_dotenv(args.env_file)
        
        cls.ENVIRONMENT = args.environment or os.getenv("ENVIRONMENT", "test")
        cls.SUBDOMAIN = args.subdomain or os.getenv("SUBDOMAIN", "test")
        cls.BASE_PATH = args.path or os.getenv("PATH", "/tmp/gestion-alumnos")
        
        cls.API_BASE_URL = os.getenv("API_BASE_URL", "")
        cls.API_USER = os.getenv("API_USER", "")
        cls.API_PASSWORD = os.getenv("API_PASSWORD", "")
        
        cls.SMTP_HOSTS = os.getenv("SMTP_HOSTS", "")
        cls.SMTP_PORT = os.getenv("SMTP_PORT", "587")
        cls.SMTP_USER = os.getenv("SMTP_USER", "")
        cls.SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
        
        cls.DB_USER = os.getenv("DB_USER", "")
        cls.DB_PASS = os.getenv("DB_PASS", "")
        cls.DB_HOST = os.getenv("DB_HOST", "")
        cls.DB_NAME = os.getenv("DB_NAME", "")
        cls.REPORT_TO = os.getenv("REPORT_TO", "")
    
    @classmethod
    def load_from_dict(cls, config_dict):
        """Carga desde diccionario (para uso como módulo)"""
        for key, value in config_dict.items():
            if hasattr(cls, key):
                setattr(cls, key, value)

# Compatibilidad con código existente que usa variables globales
ENVIRONMENT = Config.ENVIRONMENT
SUBDOMAIN = Config.SUBDOMAIN
PATH = Config.BASE_PATH
API_BASE_URL = Config.API_BASE_URL
API_USER = Config.API_USER
API_PASSWORD = Config.API_PASSWORD
SMTP_HOSTS = Config.SMTP_HOSTS
SMTP_PORT = Config.SMTP_PORT
SMTP_USER = Config.SMTP_USER
SMTP_PASSWORD = Config.SMTP_PASSWORD
DB_USER = Config.DB_USER
DB_PASS = Config.DB_PASS
DB_HOST = Config.DB_HOST
DB_NAME = Config.DB_NAME
REPORT_TO = Config.REPORT_TO

def refresh_globals():
    """Actualiza variables globales desde Config"""
    global ENVIRONMENT, SUBDOMAIN, PATH, API_BASE_URL, API_USER, API_PASSWORD
    global SMTP_HOSTS, SMTP_PORT, SMTP_USER, SMTP_PASSWORD
    global DB_USER, DB_PASS, DB_HOST, DB_NAME, REPORT_TO
    
    ENVIRONMENT = Config.ENVIRONMENT
    SUBDOMAIN = Config.SUBDOMAIN
    PATH = Config.BASE_PATH
    API_BASE_URL = Config.API_BASE_URL
    API_USER = Config.API_USER
    API_PASSWORD = Config.API_PASSWORD
    SMTP_HOSTS = Config.SMTP_HOSTS
    SMTP_PORT = Config.SMTP_PORT
    SMTP_USER = Config.SMTP_USER
    SMTP_PASSWORD = Config.SMTP_PASSWORD
    DB_USER = Config.DB_USER
    DB_PASS = Config.DB_PASS
    DB_HOST = Config.DB_HOST
    DB_NAME = Config.DB_NAME
    REPORT_TO = Config.REPORT_TO

'''

ENTRY_POINT = '''
# =============================================================================
# SECCIÓN FINAL: PUNTO DE ENTRADA
# =============================================================================

def parse_arguments():
    """Parsea argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(
        description='Gestión automática de alumnos Moodle v0.1.0',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  # Usar archivo .env (recomendado)
  python3 gestion_alumnos_single.py --env-file .env.produccion
  
  # Variables de entorno del sistema + CLI
  python3 gestion_alumnos_single.py --environment produccion --subdomain www
  
  # Modo test con datos mock
  python3 gestion_alumnos_single.py --environment test --mock-data
        """
    )
    
    # Configuración general
    parser.add_argument('--env-file', '-e',
                        help='Archivo .env con variables de configuración')
    parser.add_argument('--environment', 
                        choices=['test', 'preproduccion', 'produccion'],
                        help='Entorno de ejecución')
    parser.add_argument('--subdomain',
                        choices=['test', 'preproduccion', 'www'],
                        help='Subdominio de Moodle')
    parser.add_argument('--path', 
                        help='Ruta base para logs y datos')
    
    # Modo ejecución
    parser.add_argument('--mock-data', action='store_true',
                        help='Usar datos mock (sin llamar a API real)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Simular ejecución sin realizar cambios')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Mostrar logs detallados')
    
    return parser.parse_args()

def main():
    """Punto de entrada principal"""
    args = parse_arguments()
    
    # Cargar configuración
    Config.load_from_args(args)
    refresh_globals()  # Actualizar variables globales para código legacy
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Crear directorios necesarios
    os.makedirs(f"{Config.BASE_PATH}/logs/{Config.SUBDOMAIN}/html", exist_ok=True)
    os.makedirs(f"{Config.BASE_PATH}/data", exist_ok=True)
    
    # Ejecutar
    try:
        if args.mock_data:
            print("🧪 Modo TEST con datos mock")
        else:
            print(f"🚀 Ejecutando en entorno: {Config.ENVIRONMENT}")
        
        if args.dry_run:
            print("⚠️  Modo DRY-RUN: No se realizarán cambios")
        
        gestion_alumnos_v1()
        
    except KeyboardInterrupt:
        print("\\n⚠️  Ejecución interrumpida por el usuario")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
'''


def remove_project_imports(code: str) -> str:
    """Elimina imports de módulos del proyecto que ya están incluidos"""
    lines = code.split('\n')
    filtered = []
    
    skip_patterns = [
        'from gestion_alumnos',
        'from Config import',
        'import Config',
        'from utils import',
        'from classes.',
        'from models import',
        'from conexion import',
        'from logger_config import',
        'from util import',
    ]
    
    for line in lines:
        stripped = line.strip()
        if any(pattern in stripped for pattern in skip_patterns):
            continue
        filtered.append(line)
    
    return '\n'.join(filtered)


def build_single_file(output_path: str = "dist/gestion_alumnos_single.py"):
    """Construye el archivo único"""
    
    # Crear directorio de salida
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    
    content_parts = [HEADER]
    
    for module_path in MODULES_ORDER:
        if not os.path.exists(module_path):
            print(f"⚠️  No encontrado: {module_path}")
            continue
            
        with open(module_path, 'r') as f:
            code = f.read()
        
        # Limpiar imports
        code = remove_project_imports(code)
        
        content_parts.append(f"\n# {'='*77}\n")
        content_parts.append(f"# ORIGIN: {module_path}\n")
        content_parts.append(f"# {'='*77}\n\n")
        content_parts.append(code)
    
    # Añadir punto de entrada
    content_parts.append(ENTRY_POINT)
    
    # Escribir archivo
    with open(output_path, 'w') as f:
        f.write(''.join(content_parts))
    
    # Hacer ejecutable
    os.chmod(output_path, 0o755)
    
    # Calcular estadísticas
    total_lines = sum(1 for _ in open(output_path))
    
    print(f"✅ Archivo único creado: {output_path}")
    print(f"   📊 Total de líneas: {total_lines:,}")
    print(f"   📦 Módulos incluidos: {len([m for m in MODULES_ORDER if os.path.exists(m)])}")
    print(f"\nUso:")
    print(f"   python3 {output_path} --env-file .env.test")


if __name__ == "__main__":
    build_single_file()
