"""Modelo de dominio para un módulo/materia."""

from pydantic import BaseModel, ConfigDict, Field


class Modulo(BaseModel):
    """Representa un módulo/materia de un ciclo formativo.

    Attributes:
        id_materia: ID único de la materia en SIGAD.
        nombre: Nombre completo del módulo.
        siglas: Siglas identificativas del módulo.
    """

    model_config = ConfigDict(populate_by_name=True)

    id_materia: int = Field(..., alias="idMateria", gt=0)
    nombre: str = Field(..., alias="modulo", min_length=1, max_length=500)
    siglas: str = Field(..., alias="siglasModulo", min_length=1, max_length=20)

    def __str__(self) -> str:
        return f"{self.siglas} - {self.nombre}"
