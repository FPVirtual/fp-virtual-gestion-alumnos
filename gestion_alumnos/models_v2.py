"""
Modelos de dominio con Pydantic.

Reemplaza los dataclasses simples por modelos Pydantic que proporcionan:
- Validación automática de datos
- Serialización/deserialación robusta
- Documentación integrada
"""

from datetime import date
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ==========================================
# Configuración base compartida
# ==========================================
class ModeloBase(BaseModel):
    """Clase base para todos los modelos del dominio."""
    
    model_config = ConfigDict(
        # Permitir conversiones de tipos (str -> int, etc.)
        str_strip_whitespace=True,
        # Rechazar campos no definidos
        extra="forbid",
        # Permitir validación en asignación
        validate_assignment=True,
    )


# ==========================================
# Modelos de dominio
# ==========================================
class Modulo(ModeloBase):
    """
    Representa un módulo/materia de un ciclo formativo.
    
    Attributes:
        id_materia: ID único de la materia en SIGAD
        nombre: Nombre completo del módulo
        siglas: Siglas identificativas del módulo
    """
    
    model_config = ConfigDict(populate_by_name=True)
    
    id_materia: int = Field(..., alias="idMateria", gt=0)
    nombre: str = Field(..., alias="modulo", min_length=1, max_length=500)
    siglas: str = Field(..., alias="siglasModulo", min_length=1, max_length=20)
    
    def __str__(self) -> str:
        return f"{self.siglas} - {self.nombre}"


class Ciclo(ModeloBase):
    """
    Representa un ciclo formativo en un centro.
    
    Attributes:
        id_ficha: ID de la ficha en SIGAD
        codigo: Cigo oficial del ciclo
        nombre: Nombre completo del ciclo
        siglas: Siglas identificativas
        modulos: Lista de módulos del ciclo
    """
    
    model_config = ConfigDict(populate_by_name=True)
    
    id_ficha: int = Field(..., alias="idFicha", gt=0)
    codigo: str = Field(..., alias="codigoCiclo", min_length=1, max_length=20)
    nombre: str = Field(..., alias="ciclo", min_length=1, max_length=200)
    siglas: str = Field(..., alias="siglasCiclo", min_length=1, max_length=20)
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


class Centro(ModeloBase):
    """
    Representa un centro educativo.
    
    Attributes:
        codigo: Cigo oficial del centro
        nombre: Nombre del centro
        ciclos: Lista de ciclos impartidos
    """
    
    model_config = ConfigDict(populate_by_name=True)
    
    codigo: str = Field(..., alias="codigoCentro", min_length=1, max_length=20)
    nombre: str = Field(..., alias="centro", min_length=1, max_length=200)
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


class Alumno(ModeloBase):
    """
    Representa un alumno matriculado.
    
    Attributes:
        id_alumno: ID único en SIGAD
        id_tipo_documento: Tipo (1=DNI, 2=NIE, etc.)
        documento: Número de documento (DNI/NIE)
        nombre: Nombre del alumno
        apellido1: Primer apellido
        apellido2: Segundo apellido (opcional)
        email: Email registrado en SIGAD
        centros: Lista de centros donde estudia
    """
    
    model_config = ConfigDict(populate_by_name=True)
    
    id_alumno: int = Field(..., alias="idAlumno", gt=0)
    id_tipo_documento: int = Field(..., alias="idTipoDocumento", gt=0)
    documento: str = Field(
        ...,
        min_length=5,
        max_length=20,
        pattern=r"^[A-Z0-9]+$",
        description="DNI/NIE sin espacios ni guiones"
    )
    nombre: str = Field(..., min_length=1, max_length=100)
    apellido1: str = Field(..., alias="apellido1", min_length=1, max_length=100)
    apellido2: str | None = Field(None, alias="apellido2", max_length=100)
    email: str = Field(
        ...,
        pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        max_length=200
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


class Registro(ModeloBase):
    """
    Registro completo de estudiantes descargado de SIGAD.
    
    Attributes:
        fecha: Fecha de generación del registro
        hora: Hora de generación del registro
        alumnos: Lista de alumnos matriculados
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
        """
        Busca un alumno por su número de documento.
        
        Args:
            documento: DNI/NIE a buscar
            
        Returns:
            Alumno encontrado o None
        """
        doc = documento.upper()
        for alumno in self.alumnos:
            if alumno.documento == doc:
                return alumno
        return None
