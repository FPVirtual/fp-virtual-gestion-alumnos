"""Modelo de dominio para un ciclo formativo."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from gestion_alumnos.models.modulo import Modulo


class Ciclo(BaseModel):
    """Representa un ciclo formativo en un centro.

    Attributes:
        id_ficha: ID de la ficha en SIGAD.
        codigo: Código oficial del ciclo.
        nombre: Nombre completo del ciclo.
        siglas: Siglas identificativas.
        modulos: Lista de módulos del ciclo.
    """

    model_config = ConfigDict(populate_by_name=True)

    id_ficha: int = Field(0, alias="idFicha", ge=0)
    codigo: str | None = Field(None, alias="codigoCiclo", min_length=1, max_length=20)
    nombre: str | None = Field(None, alias="ciclo", min_length=1, max_length=200)
    siglas: str | None = Field(None, alias="siglasCiclo", min_length=1, max_length=20)
    modulos: list[Modulo] = Field(default_factory=list)

    @field_validator("modulos", mode="before")
    @classmethod
    def validar_modulos(cls, v: list[Any]) -> list[Modulo]:
        """Convierte diccionarios a objetos Modulo."""
        if not isinstance(v, list):
            raise ValueError("modulos debe ser una lista")
        return [
            Modulo.model_validate(m) if isinstance(m, dict) else m
            for m in v
        ]

    def __str__(self) -> str:
        return f"{self.siglas} ({self.codigo})"
