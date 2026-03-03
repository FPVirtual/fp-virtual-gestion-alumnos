"""
Core module: Configuración, excepciones y utilidades base.

Este módulo contiene los componentes fundamentales del sistema
que son independientes de la lógica de negocio específica.
"""

from .config import Settings, get_settings
from .exceptions import (
    GestionAlumnosError,
    APIError,
    ConfiguracionError,
    EmailError,
    MoodleError,
)
from .logging import get_logger, configure_logging

__all__ = [
    "Settings",
    "get_settings",
    "GestionAlumnosError",
    "APIError",
    "ConfiguracionError",
    "EmailError",
    "MoodleError",
    "get_logger",
    "configure_logging",
]
