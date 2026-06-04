"""Modelo de dominio para un centro educativo."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from gestion_alumnos.models.ciclo import Ciclo


class Centro(BaseModel):
    """Representa un centro educativo.

    Attributes:
        codigo: Código oficial del centro.
        nombre: Nombre del centro.
        ciclos: Lista de ciclos impartidos.
    """

    model_config = ConfigDict(populate_by_name=True)

    codigo: str | None = Field(None, alias="codigoCentro", min_length=1, max_length=20)
    nombre: str | None = Field(None, alias="centro", min_length=1, max_length=200)
    ciclos: list[Ciclo] = Field(default_factory=list)

    @field_validator("ciclos", mode="before")
    @classmethod
    def validar_ciclos(cls, v: list[Any]) -> list[Ciclo]:
        """Convierte diccionarios a objetos Ciclo."""
        if not isinstance(v, list):
            raise ValueError("ciclos debe ser una lista")
        return [
            Ciclo.model_validate(c) if isinstance(c, dict) else c
            for c in v
        ]

    def __str__(self) -> str:
        return f"{self.codigo} - {self.nombre}"
