"""Repositorios del sistema.

Implementan los protocols definidos en protocols.py.
"""

from gestion_alumnos.repositories.email_repository import EmailRepositoryImpl
from gestion_alumnos.repositories.moodle_api_repository import APIMoodleRepository
from gestion_alumnos.repositories.moodle_moosh_repository import MooshMoodleRepository
from gestion_alumnos.repositories.sigad_repository import SIGADRepository

__all__ = [
    "SIGADRepository",
    "MooshMoodleRepository",
    "APIMoodleRepository",
    "EmailRepositoryImpl",
]
