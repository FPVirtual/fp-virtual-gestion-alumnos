"""Tests de integración para MoodleSource implementations.

Validan que APICourseBasedMoodleSource y APISnapshotMoodleSource
compongan correctamente MoodleSnapshot a partir de datos crudos.
No realizan llamadas de red reales; usan mocks del APIMoodleRepository.
"""

from unittest.mock import MagicMock

import pytest

from gestion_alumnos.core.exceptions import MoodleError
from gestion_alumnos.models import (
    MoodleCourseRecord,
    MoodleEnrolmentRecord,
    MoodleUserRecord,
)
from gestion_alumnos.repositories.moodle_sources import (
    APICourseBasedMoodleSource,
    APISnapshotMoodleSource,
)


@pytest.fixture
def mock_repo():
    """Mock de APIMoodleRepository con respuestas configurables."""
    return MagicMock()


class TestAPICourseBasedMoodleSource:
    """Valida extracción iterando cursos."""

    def test_extract_users(self, mock_repo):
        mock_repo.obtener_todos_usuarios.return_value = [
            {"id": 101, "username": "user1", "email": "u1@e.com", "firstname": "A", "lastname": "B", "suspended": 0},
            {"id": 102, "username": "user2", "email": "u2@e.com", "firstname": "C", "lastname": "D", "suspended": 0},
        ]
        source = APICourseBasedMoodleSource(repo=mock_repo)
        users = source.extract_users()
        assert len(users) == 2
        assert users[0]["username"] == "user1"

    def test_extract_courses(self, mock_repo):
        mock_repo.obtener_todos_cursos.return_value = [
            {"id": 1, "shortname": "C1", "fullname": "Curso 1", "categoryid": 10},
            {"id": 2, "shortname": "C2", "fullname": "Curso 2", "categoryid": 10},
        ]
        source = APICourseBasedMoodleSource(repo=mock_repo)
        courses = source.extract_courses()
        assert len(courses) == 2
        assert courses[1]["shortname"] == "C2"

    def test_extract_enrolments(self, mock_repo):
        mock_repo.obtener_todos_cursos.return_value = [
            {"id": 1, "shortname": "C1"},
            {"id": 2, "shortname": "C2"},
        ]
        mock_repo.obtener_usuarios_matriculados_en_curso.side_effect = lambda cid: [
            {"id": 101 + int(cid)},
        ]

        source = APICourseBasedMoodleSource(repo=mock_repo)
        enrolments = source.extract_enrolments()

        assert len(enrolments) == 2
        assert enrolments[0]["courseid"] == "1"
        assert enrolments[0]["userid"] == 102
        assert enrolments[1]["shortname"] == "C2"

    def test_extract_enrolments_skips_empty_course_id(self, mock_repo):
        mock_repo.obtener_todos_cursos.return_value = [
            {"id": 1, "shortname": "C1"},
            {"id": None, "shortname": "BAD"},
        ]
        mock_repo.obtener_usuarios_matriculados_en_curso.return_value = []

        source = APICourseBasedMoodleSource(repo=mock_repo)
        enrolments = source.extract_enrolments()

        # Solo debe procesar el curso con id válido
        assert len(enrolments) == 0  # el curso 1 no tiene matriculados
        calls = mock_repo.obtener_usuarios_matriculados_en_curso.call_args_list
        assert len(calls) == 1
        assert calls[0][0][0] == "1"

    def test_extract_enrolments_ignores_course_errors(self, mock_repo):
        mock_repo.obtener_todos_cursos.return_value = [
            {"id": 1, "shortname": "C1"},
            {"id": 2, "shortname": "C2"},
        ]
        mock_repo.obtener_usuarios_matriculados_en_curso.side_effect = [
            [{"id": 101}],
            Exception("Timeout"),
        ]

        source = APICourseBasedMoodleSource(repo=mock_repo)
        enrolments = source.extract_enrolments()

        assert len(enrolments) == 1
        assert enrolments[0]["courseid"] == "1"

    def test_extract_all_returns_snapshot(self, mock_repo):
        mock_repo.obtener_todos_usuarios.return_value = [
            {"id": 101, "username": "u1", "email": "a@b.com", "firstname": "A", "lastname": "B", "suspended": 0},
        ]
        mock_repo.obtener_todos_cursos.return_value = [
            {"id": 1, "shortname": "C1", "fullname": "Curso", "categoryid": 10},
        ]
        mock_repo.obtener_usuarios_matriculados_en_curso.return_value = [
            {"id": 101},
        ]

        source = APICourseBasedMoodleSource(repo=mock_repo)
        snapshot = source.extract_all()

        assert snapshot.total_users == 1
        assert len(snapshot.courses) == 1
        assert snapshot.total_enrolments == 1
        assert isinstance(snapshot.users[0], MoodleUserRecord)
        assert isinstance(snapshot.courses[0], MoodleCourseRecord)
        assert isinstance(snapshot.enrolments[0], MoodleEnrolmentRecord)


class TestAPISnapshotMoodleSource:
    """Valida extracción vía plugin PHP snapshot."""

    def test_extract_users_fallback(self, mock_repo):
        mock_repo.obtener_todos_usuarios.return_value = [
            {"id": 101, "username": "u1"},
        ]
        source = APISnapshotMoodleSource(repo=mock_repo)
        users = source.extract_users()
        assert len(users) == 1

    def test_extract_courses_fallback(self, mock_repo):
        mock_repo.obtener_todos_cursos.return_value = [
            {"id": 1, "shortname": "C1"},
        ]
        source = APISnapshotMoodleSource(repo=mock_repo)
        courses = source.extract_courses()
        assert len(courses) == 1

    def test_extract_enrolments_raises(self, mock_repo):
        source = APISnapshotMoodleSource(repo=mock_repo)
        with pytest.raises(NotImplementedError):
            source.extract_enrolments()

    def test_extract_all_with_plugin(self, mock_repo):
        mock_repo._call.return_value = {
            "usuarios": [
                {"id": 101, "username": "u1", "email": "a@b.com", "firstname": "A", "lastname": "B", "suspended": 0},
            ],
            "matriculas": [
                {"userid": 101, "courseid": 1, "shortname": "C1", "status": 0},
            ],
        }
        source = APISnapshotMoodleSource(repo=mock_repo)
        snapshot = source.extract_all()

        assert snapshot.total_users == 1
        assert snapshot.total_enrolments == 1
        assert len(snapshot.courses) == 0  # snapshot no incluye cursos
        assert isinstance(snapshot.users[0], MoodleUserRecord)
        assert isinstance(snapshot.enrolments[0], MoodleEnrolmentRecord)
        mock_repo._call.assert_called_once_with("local_fparagon_get_snapshot", {})

    def test_extract_all_plugin_not_installed(self, mock_repo):
        mock_repo._call.side_effect = MoodleError(
            mensaje="error: functionnotavailable",
            comando="local_fparagon_get_snapshot",
        )
        source = APISnapshotMoodleSource(repo=mock_repo)
        with pytest.raises(MoodleError) as exc_info:
            source.extract_all()
        assert "local_fparagon no instalado" in str(exc_info.value)

    def test_extract_all_unexpected_response(self, mock_repo):
        mock_repo._call.return_value = ["not", "a", "dict"]
        source = APISnapshotMoodleSource(repo=mock_repo)
        with pytest.raises(MoodleError) as exc_info:
            source.extract_all()
        assert "Respuesta inesperada" in str(exc_info.value)

    def test_extract_all_empty_response(self, mock_repo):
        mock_repo._call.return_value = {"usuarios": [], "matriculas": []}
        source = APISnapshotMoodleSource(repo=mock_repo)
        snapshot = source.extract_all()
        assert snapshot.total_users == 0
        assert snapshot.total_enrolments == 0
