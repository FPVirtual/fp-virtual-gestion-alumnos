"""Tests para el DI Container."""

from gestion_alumnos.core.config import Settings
from gestion_alumnos.core.container import DIContainer, create_container
from gestion_alumnos.repositories.moodle_api_repository import APIMoodleRepository
from gestion_alumnos.repositories.moodle_moosh_repository import MooshMoodleRepository


def test_container_resuelve_moosh_por_defecto():
    settings = Settings(moodle_driver="moosh")
    container = create_container(settings)
    repo = container.moodle_repository()
    assert isinstance(repo, MooshMoodleRepository)


def test_container_resuelve_api():
    settings = Settings(
        moodle_driver="api",
        moodle_api_url="https://test.moodle/api",
        moodle_api_token="token123",
    )
    container = create_container(settings)
    repo = container.moodle_repository()
    assert isinstance(repo, APIMoodleRepository)


def test_container_override_moodle_repo():
    settings = Settings(moodle_driver="moosh")
    container = create_container(settings)
    mock_repo = object()
    container.override_moodle_repository(mock_repo)
    assert container.moodle_repository() is mock_repo
