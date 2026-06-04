"""Modelo de dominio para un alumno matriculado."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from gestion_alumnos.models.centro import Centro
from gestion_alumnos.models.modulo import Modulo


class Alumno(BaseModel):
    """Representa un alumno matriculado.

    Attributes:
        id_alumno: ID único en SIGAD.
        id_tipo_documento: Tipo (1=DNI, 2=NIE, etc.).
        documento: Número de documento (DNI/NIE).
        nombre: Nombre del alumno.
        apellido1: Primer apellido.
        apellido2: Segundo apellido (opcional).
        email: Email registrado en SIGAD.
        centros: Lista de centros donde estudia.
    """

    model_config = ConfigDict(populate_by_name=True)

    id_alumno: int = Field(..., alias="idAlumno", gt=0)
    id_tipo_documento: int = Field(..., alias="idTipoDocumento", gt=0)
    documento: str = Field(
        ...,
        min_length=5,
        max_length=20,
        pattern=r"^[A-Z0-9]+$",
        description="DNI/NIE sin espacios ni guiones",
    )
    nombre: str = Field(..., min_length=1, max_length=100)
    apellido1: str = Field(..., alias="apellido1", min_length=1, max_length=100)
    apellido2: str | None = Field(None, alias="apellido2", max_length=100)
    email: str = Field(
        ...,
        pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        max_length=200,
    )
    centros: list[Centro] = Field(default_factory=list)

    @field_validator("documento")
    @classmethod
    def normalizar_documento(cls, v: str) -> str:
        """Convierte el documento a mayúsculas."""
        return v.upper()

    @field_validator("email")
    @classmethod
    def normalizar_email(cls, v: str) -> str:
        """Convierte el email a minúsculas."""
        return v.lower()

    @field_validator("centros", mode="before")
    @classmethod
    def validar_centros(cls, v: list[Any]) -> list[Centro]:
        """Convierte diccionarios a objetos Centro."""
        if not isinstance(v, list):
            raise ValueError("centros debe ser una lista")
        return [
            Centro.model_validate(c) if isinstance(c, dict) else c
            for c in v
        ]

    @property
    def nombre_completo(self) -> str:
        """Nombre completo del alumno."""
        partes = [self.nombre, self.apellido1]
        if self.apellido2:
            partes.append(self.apellido2)
        return " ".join(partes)

    @property
    def username_moodle(self) -> str:
        """Username para Moodle (documento en minúsculas)."""
        return self.documento.lower()

    @property
    def email_institucional(self) -> str:
        """Email institucional generado."""
        return f"{self.username_moodle}@fpvirtualaragon.es"

    def obtener_todos_modulos(self) -> list[Modulo]:
        """Obtiene todos los módulos de todos los ciclos y centros."""
        modulos = []
        for centro in self.centros:
            for ciclo in centro.ciclos:
                modulos.extend(ciclo.modulos)
        return modulos

    def __str__(self) -> str:
        return f"{self.nombre_completo} ({self.documento})"
