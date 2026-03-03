"""
Repositories: Abstracciones para acceso a datos.

Implementa el patrón Repository para desacoplar la lógica de negocio
de los detalles de acceso a datos (API, BD, etc.).
"""

from .protocols import (
    AlumnoRepository,
    MoodleRepository,
    EmailRepository,
    EstudianteRepository,
)
from .sigad_repository import SIGADRepository
from .moodle_db_repository import MoodleDBRepository

__all__ = [
    # Protocols
    "AlumnoRepository",
    "MoodleRepository",
    "EmailRepository",
    "EstudianteRepository",
    # Implementaciones
    "SIGADRepository",
    "MoodleDBRepository",
]
