"""Modelos de dominio del sistema.

Todos los modelos usan Pydantic para validación automática.
"""

from gestion_alumnos.models.alumno import Alumno
from gestion_alumnos.models.centro import Centro
from gestion_alumnos.models.ciclo import Ciclo
from gestion_alumnos.models.modulo import Modulo
from gestion_alumnos.models.registro import Registro

__all__ = [
    "Alumno",
    "Centro",
    "Ciclo",
    "Modulo",
    "Registro",
]
