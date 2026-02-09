from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Modulo:
    idMateria: int
    modulo: str
    siglasModulo: str


@dataclass
class Ciclo:
    idFicha: int
    codigoCiclo: str
    ciclo: str
    siglasCiclo: str
    modulos: List[Modulo]


@dataclass
class Centro:
    codigoCentro: str
    centro: str
    ciclos: List[Ciclo]


@dataclass
class Alumno:
    idAlumno: int
    idTipoDocumento: int
    documento: str
    nombre: str
    apellido1: str
    apellido2: Optional[str]
    email: str
    centros: List[Centro]


@dataclass
class Registro:
    fecha: str
    hora: str
    alumnos: List[Alumno]