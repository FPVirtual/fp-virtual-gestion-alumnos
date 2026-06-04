"""Fixtures globales para pytest."""

import pytest

from gestion_alumnos.core.config import Settings
from gestion_alumnos.models import Alumno, Centro, Ciclo, Modulo, Registro


@pytest.fixture
def settings_test(monkeypatch):
    """Configuración de test."""
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("SUBDOMAIN", "test")
    monkeypatch.setenv("MOODLE_DRIVER", "moosh")
    monkeypatch.setenv("API_USER", "test_user")
    monkeypatch.setenv("API_PASSWORD", "test_pass")
    return Settings()


@pytest.fixture
def sample_modulo():
    return Modulo(
        idMateria=18599,
        modulo="Itinerario personal para la empleabilidad I ( Virtual )",
        siglasModulo="IPPE1",
    )


@pytest.fixture
def sample_ciclo(sample_modulo):
    return Ciclo(
        idFicha=22,
        codigoCiclo="12242301",
        ciclo="Educación Infantil (Formación Profesional)",
        siglasCiclo="SSC302",
        modulos=[sample_modulo],
    )


@pytest.fixture
def sample_centro(sample_ciclo):
    return Centro(
        codigoCentro="50009348",
        centro="AVEMPACE",
        ciclos=[sample_ciclo],
    )


@pytest.fixture
def sample_alumno(sample_centro):
    return Alumno(
        idAlumno=16839,
        idTipoDocumento=1,
        documento="78842153Q",
        nombre="Valeria",
        apellido1="Torres",
        apellido2="Medina",
        email="valeria.torres.medina@ejemplo.com",
        centros=[sample_centro],
    )


@pytest.fixture
def sample_registro(sample_alumno):
    return Registro(
        fecha="15/12/2025",
        hora="11:42:28",
        alumnos=[sample_alumno],
    )


@pytest.fixture
def mock_moosh(monkeypatch):
    """Mock para subprocess.run con moosh."""
    import subprocess

    def fake_run(cmd, **kwargs):
        class FakeResult:
            returncode = 0
            stdout = "123\n"
            stderr = ""
        return FakeResult()

    monkeypatch.setattr(subprocess, "run", fake_run)
