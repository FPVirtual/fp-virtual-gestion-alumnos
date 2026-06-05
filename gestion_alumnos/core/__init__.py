"""Componentes fundamentales del sistema.

Incluye configuración, logging, excepciones e inyección de dependencias.
"""

from gestion_alumnos.core.config import Settings, get_settings
from gestion_alumnos.core.container import DIContainer, create_container, get_container
from gestion_alumnos.core.exceptions import (
    APIError,
    APIRateLimitError,
    APITimeoutError,
    ConfiguracionError,
    EmailError,
    EmailLimitExceeded,
    GestionAlumnosError,
    MoodleError,
    RepositorioError,
    ValidacionError,
)
from gestion_alumnos.core.logging import ReportLogger, configure_logging, get_logger

__all__ = [
    "Settings",
    "get_settings",
    "DIContainer",
    "create_container",
    "get_container",
    "ReportLogger",
    "configure_logging",
    "get_logger",
    "GestionAlumnosError",
    "ConfiguracionError",
    "APIError",
    "APIRateLimitError",
    "APITimeoutError",
    "MoodleError",
    "EmailError",
    "EmailLimitExceeded",
    "ValidacionError",
    "RepositorioError",
]
