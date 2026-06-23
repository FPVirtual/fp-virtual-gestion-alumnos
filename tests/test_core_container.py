"""Tests para el DI Container."""

import pytest

from gestion_alumnos.core.config import Settings
from gestion_alumnos.core.container import DIContainer, create_container
from gestion_alumnos.core.exceptions import MoodleError
from gestion_alumnos.repositories.moodle_api_repository import APIMoodleRepository
from gestion_alumnos.repositories.moodle_moosh_repository import MooshMoodleRepository
from gestion_alumnos.repositories.moodle_sources import (
    APICourseBasedMoodleSource,
    APISnapshotMoodleSource,
)


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


def test_container_falla_si_api_driver_sin_credenciales():
    settings = Settings(
        moodle_driver="api",
        moodle_api_url=None,
        moodle_api_token=None,
    )
    container = create_container(settings)
    with pytest.raises(MoodleError, match="Faltan MOODLE_API_URL"):
        container.moodle_repository()


def test_container_resuelve_api_snapshot_source():
    settings = Settings(
        moodle_driver="api",
        moodle_source_strategy="api-snapshot",
        moodle_api_url="https://test.moodle/api",
        moodle_api_token="token123",
    )
    container = create_container(settings)
    source = container.moodle_source()
    assert isinstance(source, APISnapshotMoodleSource)


def test_container_resuelve_api_course_based_source_por_defecto():
    settings = Settings(
        moodle_driver="api",
        moodle_api_url="https://test.moodle/api",
        moodle_api_token="token123",
    )
    container = create_container(settings)
    source = container.moodle_source()
    assert isinstance(source, APICourseBasedMoodleSource)
