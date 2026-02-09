from __future__ import annotations
from typing import Dict, Any
from models import Registro, Alumno, Centro, Ciclo, Modulo


# ----------- builders recursivos -----------
def _build_modulo(data: Dict[str, Any]) -> Modulo:
    return Modulo(
        idMateria=data["idMateria"],
        modulo=data["modulo"],
        siglasModulo=data["siglasModulo"],
    )


def _build_ciclo(data: Dict[str, Any]) -> Ciclo:
    return Ciclo(
        idFicha=data["idFicha"],
        codigoCiclo=data["codigoCiclo"],
        ciclo=data["ciclo"],
        siglasCiclo=data["siglasCiclo"],
        modulos=[_build_modulo(m) for m in data["modulos"]],
    )


def _build_centro(data: Dict[str, Any]) -> Centro:
    return Centro(
        codigoCentro=data["codigoCentro"],
        centro=data["centro"],
        ciclos=[_build_ciclo(c) for c in data["ciclos"]],
    )


def _build_alumno(data: Dict[str, Any]) -> Alumno:
    return Alumno(
        idAlumno=data["idAlumno"],
        idTipoDocumento=data["idTipoDocumento"],
        documento=data["documento"],
        nombre=data["nombre"],
        apellido1=data["apellido1"],
        apellido2=data.get("apellido2"),
        email=data["email"],
        centros=[_build_centro(c) for c in data["centros"]],
    )


# ----------- API pública -----------
def parse_json(raw: Dict[str, Any]) -> Registro:
    """Convierte el diccionario leído del JSON en objetos Python."""
    return Registro(
        fecha=raw["fecha"],
        hora=raw["hora"],
        alumnos=[_build_alumno(a) for a in raw["alumnos"]],
    )