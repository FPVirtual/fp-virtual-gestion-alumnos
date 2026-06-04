"""Modelo de dominio para el registro completo de estudiantes."""

from datetime import date
from typing import Any

from pydantic import BaseModel, Field, field_validator

from gestion_alumnos.models.alumno import Alumno


class Registro(BaseModel):
    """Registro completo de estudiantes descargado de SIGAD.

    Attributes:
        fecha: Fecha de generación del registro (DD/MM/AAAA).
        hora: Hora de generación del registro (HH:MM:SS).
        alumnos: Lista de alumnos matriculados.
    """

    fecha: str = Field(..., pattern=r"^\d{2}/\d{2}/\d{4}$")
    hora: str = Field(..., pattern=r"^\d{2}:\d{2}:\d{2}$")
    alumnos: list[Alumno] = Field(default_factory=list)

    @field_validator("alumnos", mode="before")
    @classmethod
    def validar_alumnos(cls, v: list[Any]) -> list[Alumno]:
        """Convierte diccionarios a objetos Alumno."""
        if not isinstance(v, list):
            raise ValueError("alumnos debe ser una lista")
        return [
            Alumno.model_validate(a) if isinstance(a, dict) else a
            for a in v
        ]

    @property
    def total_alumnos(self) -> int:
        """Número total de alumnos en el registro."""
        return len(self.alumnos)

    @property
    def fecha_datetime(self) -> date:
        """Fecha como objeto datetime.date."""
        dia, mes, anio = map(int, self.fecha.split("/"))
        return date(anio, mes, dia)

    def buscar_por_documento(self, documento: str) -> Alumno | None:
        """Busca un alumno por su número de documento.

        Args:
            documento: DNI/NIE a buscar.

        Returns:
            Alumno encontrado o None.
        """
        doc = documento.upper()
        for alumno in self.alumnos:
            if alumno.documento == doc:
                return alumno
        return None
