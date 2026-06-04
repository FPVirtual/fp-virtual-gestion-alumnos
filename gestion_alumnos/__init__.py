"""Paquete para la gestión automática de alumnos en Moodle.

v0.3.0 — Arquitectura con Repository Pattern, DI, y soporte dual
moosh / API REST.
"""

__version__ = "0.3.0"

from gestion_alumnos.core.config import Settings, get_settings
from gestion_alumnos.core.container import DIContainer, create_container, get_container
from gestion_alumnos.core.logging import configure_logging, get_logger

__all__ = [
    "__version__",
    "Settings",
    "get_settings",
    "DIContainer",
    "create_container",
    "get_container",
    "configure_logging",
    "get_logger",
]
