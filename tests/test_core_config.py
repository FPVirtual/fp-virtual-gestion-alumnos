"""Tests para la configuración."""

import pytest

from gestion_alumnos.core.config import Settings


def test_config_default():
    settings = Settings(moodle_driver="moosh")
    assert settings.environment == "dev"
    assert settings.moodle_driver == "moosh"
    assert settings.email_limit == 10


def test_config_produccion(monkeypatch):
    monkeypatch.setenv("SUBDOMAIN", "www")
    monkeypatch.setenv("ENVIRONMENT", "produccion")
    settings = Settings()
    assert settings.is_produccion is True
    assert settings.email_limit == 1000


def test_config_api_driver(monkeypatch):
    monkeypatch.setenv("MOODLE_DRIVER", "api")
    settings = Settings()
    assert settings.moodle_driver == "api"
