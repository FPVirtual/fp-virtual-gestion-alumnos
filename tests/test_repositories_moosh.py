"""Tests para MooshMoodleRepository."""

import subprocess

import pytest

from gestion_alumnos.core.config import Settings
from gestion_alumnos.core.exceptions import MoodleError
from gestion_alumnos.repositories.moodle_moosh_repository import MooshMoodleRepository


def test_moosh_usuario_existe(mock_moosh, settings_test):
    repo = MooshMoodleRepository(settings_test)
    assert repo.usuario_existe("testuser") is True


def test_moosh_crear_usuario(mock_moosh, settings_test):
    repo = MooshMoodleRepository(settings_test)
    user_id = repo.crear_usuario("testuser", "test@test.com", "Nombre", "Apellido")
    assert user_id == 123


def test_moosh_crear_usuario_con_customfields(mock_moosh, settings_test):
    repo = MooshMoodleRepository(settings_test)
    customfields = {
        "IdSIGAD": "99999",
        "tipoDocumento": "1",
        "consentimientoCDD": "0",
    }
    user_id = repo.crear_usuario(
        "testuser", "test@test.com", "Nombre", "Apellido",
        customfields=customfields,
    )
    assert user_id == 123


def test_moosh_actualizar_usuario_con_customfields(mock_moosh, settings_test):
    repo = MooshMoodleRepository(settings_test)
    result = repo.actualizar_usuario(
        "testuser",
        customfields={"emailsigad": "nuevo@ejemplo.com"},
    )
    assert result is True


def test_moosh_error_comando(monkeypatch, settings_test):
    def fake_run(cmd, **kwargs):
        class FakeResult:
            returncode = 1
            stdout = ""
            stderr = "ERROR"
        return FakeResult()

    monkeypatch.setattr(subprocess, "run", fake_run)
    repo = MooshMoodleRepository(settings_test)
    with pytest.raises(MoodleError):
        repo.crear_usuario("testuser", "test@test.com", "Nombre", "Apellido")
