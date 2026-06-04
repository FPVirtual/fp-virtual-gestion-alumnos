"""Tests para los modelos de dominio."""

import pytest

from gestion_alumnos.models import Alumno, Centro, Ciclo, Modulo, Registro


def test_modulo_str(sample_modulo):
    assert str(sample_modulo) == "IPPE1 - Itinerario personal para la empleabilidad I ( Virtual )"


def test_ciclo_str(sample_ciclo):
    assert str(sample_ciclo) == "SSC302 (12242301)"


def test_centro_str(sample_centro):
    assert str(sample_centro) == "50009348 - AVEMPACE"


def test_alumno_nombre_completo(sample_alumno):
    assert sample_alumno.nombre_completo == "Valeria Torres Medina"


def test_alumno_username_moodle(sample_alumno):
    assert sample_alumno.username_moodle == "78842153q"


def test_alumno_email_institucional(sample_alumno):
    assert sample_alumno.email_institucional == "78842153q@fpvirtualaragon.es"


def test_alumno_obtener_todos_modulos(sample_alumno):
    modulos = sample_alumno.obtener_todos_modulos()
    assert len(modulos) == 1
    assert modulos[0].siglas == "IPPE1"


def test_registro_total_alumnos(sample_registro):
    assert sample_registro.total_alumnos == 1


def test_registro_buscar_por_documento(sample_registro):
    encontrado = sample_registro.buscar_por_documento("78842153Q")
    assert encontrado is not None
    assert encontrado.nombre == "Valeria"


def test_registro_buscar_por_documento_no_existe(sample_registro):
    assert sample_registro.buscar_por_documento("00000000A") is None


def test_alumno_normaliza_documento():
    alumno = Alumno(
        idAlumno=1,
        idTipoDocumento=1,
        documento=" 12345678a ",
        nombre="Test",
        apellido1="Test",
        email="test@test.com",
        centros=[],
    )
    assert alumno.documento == "12345678A"
