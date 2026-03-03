"""
Configuración de logging estructurado con structlog.

Proporciona logs en formato JSON para facilitar el análisis
y monitoreo del sistema.
"""

import logging
import sys
from pathlib import Path
from typing import Any

import structlog


def configure_logging(
    environment: str = "dev",
    logs_dir: Path = Path("logs"),
    log_level: str = "INFO"
) -> None:
    """
    Configura el logging estructurado del sistema.
    
    En desarrollo: logs legibles en consola
    En producción: logs en formato JSON para análisis
    
    Args:
        environment: Entorno de ejecución (test, dev, preproduccion, produccion)
        logs_dir: Directorio para archivos de log
        log_level: Nivel mínimo de logging
    """
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Configurar logging estándar
    level = getattr(logging, log_level.upper())
    
    # Handlers
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Archivo de log
    file_handler = logging.FileHandler(
        logs_dir / f"app_{environment}.log",
        encoding="utf-8"
    )
    file_handler.setLevel(level)
    
    # Configuración base
    logging.basicConfig(
        format="%(message)s",
        level=level,
        handlers=[console_handler, file_handler]
    )
    
    # Configurar structlog
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.filter_by_level,
    ]
    
    if environment == "produccion":
        # Producción: JSON
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ]
    else:
        # Desarrollo: legible
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(nombre: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Obtiene un logger estructurado.
    
    Args:
        nombre: Nombre del logger (usa __name__ por defecto)
        
    Returns:
        Logger configurado con structlog
    """
    if nombre is None:
        nombre = "gestion_alumnos"
    return structlog.get_logger(nombre)


# Nivel personalizado para informes markdown
def markdown(self, message: str, **kwargs: Any) -> None:
    """
    Nivel de log para entradas de informe markdown.
    
    Permite separar los logs normales de las entradas
    que van al informe markdown.
    """
    self.log(25, message, **kwargs)  # 25 está entre INFO (20) y WARNING (30)


# Registrar el nuevo nivel
structlog.stdlib.BoundLogger.markdown = markdown  # type: ignore
