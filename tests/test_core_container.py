"""Tests para el DI Container."""

from gestion_alumnos.core.config import Settings
from gestion_alumnos.core.container import DIContainer
from gestion_alumnos.repositories.moodle_api_repository import APIMoodleRepository
from gestion_alumnos.repositories.moodle_moosh_repository import MooshMoodleRepository


def test_container_resuelve_moosh_por_defecto(monkeypatch):
    monkeypatch.setenv("MOODLE_DRIVER", "moosh")
    container = DIContainer()
    repo = container.moodle_repository()
    assert isinstance(repo, MooshMoodleRepository)


def test_container_resuelve_api(monkeypatch):
    monkeypatch.setenv("MOODLE_DRIVER", "api")
    monkeypatch.setenv("MOODLE_API_URL", "https://test.moodle/api")
    monkeypatch.setenv("MOODLE_API_TOKEN", "token123")
    container = DIContainer()
    repo = container.moodle_repository()
    assert isinstance(repo, APIMoodleRepository)


def test_container_override_moodle_repo(monkeypatch):
    monkeypatch.setenv("MOODLE_DRIVER", "moosh")
    container = DIContainer()
    mock_repo = object()
    container.override_moodle_repository(mock_repo)
    assert container.moodle_repository() is mock_repo
