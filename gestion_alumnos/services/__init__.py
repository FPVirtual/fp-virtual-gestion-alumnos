"""
Services: Lógica de negocio del sistema.

Los servicios orquestan las operaciones del sistema utilizando
los repositorios definidos en protocols.
"""

from .gestion_service import GestionAlumnosService
from .sync_service import SyncService

__all__ = [
    "GestionAlumnosService",
    "SyncService",
]
