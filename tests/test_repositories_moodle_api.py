"""Tests unitarios para APIMoodleRepository.

Validan la construcción de llamadas REST, el mapeo a funciones de Moodle
y el manejo de errores usando mocks de red. No realizan peticiones reales.
"""

from unittest.mock import MagicMock, patch

import pytest

from gestion_alumnos.core.config import Settings
from gestion_alumnos.core.exceptions import MoodleError
from gestion_alumnos.repositories.moodle_api_repository import APIMoodleRepository


@pytest.fixture
def settings_api():
    """Settings con driver API y credenciales completas."""
    return Settings(
        moodle_driver="api",
        moodle_api_url="https://test.moodle/webservice/rest/server.php",
        moodle_api_token="token123",
    )


@pytest.fixture
def repo(settings_api):
    """Repositorio API con credenciales válidas."""
    return APIMoodleRepository(settings=settings_api)


def _mock_response(json_data, status_code=200):
    """Crea una respuesta HTTP mock."""
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data
    response.raise_for_status.return_value = None
    return response


class TestConstruccion:
    """Valida requisitos de configuración y construcción de llamadas."""

    def test_falla_si_falta_url(self):
        settings = Settings(
            moodle_driver="api",
            moodle_api_url=None,
            moodle_api_token="token123",
        )
        with pytest.raises(MoodleError, match="Faltan MOODLE_API_URL"):
            APIMoodleRepository(settings=settings)

    def test_falla_si_falta_token(self):
        settings = Settings(
            moodle_driver="api",
            moodle_api_url="https://test.moodle/api",
            moodle_api_token=None,
        )
        with pytest.raises(MoodleError, match="Faltan MOODLE_API_URL"):
            APIMoodleRepository(settings=settings)

    def test_llamada_base_incluye_token_funcion_y_formato(self, repo):
        with patch.object(repo._session, "post") as mock_post:
            mock_post.return_value = _mock_response({"sitename": "Test"})
            repo._call("core_webservice_get_site_info")

            mock_post.assert_called_once()
            url, kwargs = mock_post.call_args
            assert url[0] == "https://test.moodle/webservice/rest/server.php"
            data = kwargs["data"]
            assert data["wstoken"] == "token123"
            assert data["wsfunction"] == "core_webservice_get_site_info"
            assert data["moodlewsrestformat"] == "json"
            assert kwargs["timeout"] == 60

    def test_maneja_respuesta_de_error_de_moodle(self, repo):
        with patch.object(repo._session, "post") as mock_post:
            mock_post.return_value = _mock_response({
                "exception": "moodle_exception",
                "errorcode": "accessexception",
                "message": "Acceso denegado",
            })
            with pytest.raises(MoodleError, match="API Moodle error"):
                repo._call("core_course_get_courses")


class TestUsuarios:
    """Valida operaciones sobre usuarios."""

    def test_crear_usuario_llama_funcion_correcta(self, repo):
        with patch.object(repo._session, "post") as mock_post:
            mock_post.return_value = _mock_response([{"id": 42}])
            user_id = repo.crear_usuario(
                username="alumno1",
                email="alumno1@ejemplo.com",
                nombre="Ana",
                apellido="García",
            )

            assert user_id == 42
            data = mock_post.call_args.kwargs["data"]
            assert data["wsfunction"] == "core_user_create_users"
            assert data["users[0][username]"] == "alumno1"
            assert data["users[0][auth]"] == "manual"

    def test_crear_usuario_incluye_customfields(self, repo):
        with patch.object(repo._session, "post") as mock_post:
            mock_post.return_value = _mock_response([{"id": 42}])
            repo.crear_usuario(
                username="alumno1",
                email="alumno1@ejemplo.com",
                nombre="Ana",
                apellido="García",
                customfields={"IdSIGAD": "12345", "consentimientoCDD": "1"},
            )

            data = mock_post.call_args.kwargs["data"]
            assert data["users[0][customfields][0][shortname]"] == "IdSIGAD"
            assert data["users[0][customfields][0][type]"] == "text"
            assert data["users[0][customfields][0][value]"] == "12345"
            assert data["users[0][customfields][1][shortname]"] == "consentimientoCDD"
            assert data["users[0][customfields][1][type]"] == "checkbox"

    def test_actualizar_usuario_busca_id_y_llama_update(self, repo):
        with patch.object(repo._session, "post") as mock_post:
            mock_post.side_effect = [
                _mock_response([{"id": 7, "username": "alumno1"}]),
                _mock_response({"id": 7}),
            ]
            result = repo.actualizar_usuario("alumno1", email="nuevo@ejemplo.com")

            assert result is True
            assert mock_post.call_count == 2
            data = mock_post.call_args.kwargs["data"]
            assert data["wsfunction"] == "core_user_update_users"
            assert data["users[0][id]"] == 7
            assert data["users[0][email]"] == "nuevo@ejemplo.com"

    def test_suspender_usuario_marca_suspended_1(self, repo):
        with patch.object(repo._session, "post") as mock_post:
            mock_post.side_effect = [
                _mock_response([{"id": 7, "username": "alumno1"}]),
                _mock_response({"id": 7}),
            ]
            repo.suspender_usuario("alumno1")
            data = mock_post.call_args.kwargs["data"]
            assert data["users[0][suspended]"] == "1"

    def test_reactivar_usuario_marca_suspended_0(self, repo):
        with patch.object(repo._session, "post") as mock_post:
            mock_post.side_effect = [
                _mock_response([{"id": 7, "username": "alumno1"}]),
                _mock_response({"id": 7}),
            ]
            repo.reactivar_usuario("alumno1")
            data = mock_post.call_args.kwargs["data"]
            assert data["users[0][suspended]"] == "0"

    def test_usuario_existe_busca_por_username(self, repo):
        with patch.object(repo._session, "post") as mock_post:
            mock_post.return_value = _mock_response([{"id": 7}])
            assert repo.usuario_existe("alumno1") is True
            data = mock_post.call_args.kwargs["data"]
            assert data["wsfunction"] == "core_user_get_users_by_field"
            assert data["field"] == "username"
            assert data["values[0]"] == "alumno1"

    def test_obtener_todos_usuarios_usa_criterio_vacio(self, repo):
        with patch.object(repo._session, "post") as mock_post:
            mock_post.return_value = _mock_response({"users": [{"id": 1}]})
            result = repo.obtener_todos_usuarios()
            assert len(result) == 1
            data = mock_post.call_args.kwargs["data"]
            assert data["wsfunction"] == "core_user_get_users"


class TestCursosYMatriculas:
    """Valida operaciones sobre cursos y matrículas."""

    def test_obtener_todos_cursos_llama_funcion_correcta(self, repo):
        with patch.object(repo._session, "post") as mock_post:
            mock_post.return_value = _mock_response([{"id": 1, "shortname": "C1"}])
            result = repo.obtener_todos_cursos()
            data = mock_post.call_args.kwargs["data"]
            assert data["wsfunction"] == "core_course_get_courses"
            assert len(result) == 1

    def test_obtener_usuarios_matriculados_en_curso(self, repo):
        with patch.object(repo._session, "post") as mock_post:
            mock_post.return_value = _mock_response([{"id": 7}])
            result = repo.obtener_usuarios_matriculados_en_curso("5")
            data = mock_post.call_args.kwargs["data"]
            assert data["wsfunction"] == "core_enrol_get_enrolled_users"
            assert data["courseid"] == "5"
            assert len(result) == 1

    def test_matricular_en_curso_usa_roleid_estudiante(self, repo):
        with patch.object(repo._session, "post") as mock_post:
            mock_post.side_effect = [
                _mock_response([{"id": 7, "username": "alumno1"}]),
                _mock_response({}),
            ]
            result = repo.matricular_en_curso("alumno1", "10")
            assert result is True
            data = mock_post.call_args.kwargs["data"]
            assert data["wsfunction"] == "enrol_manual_enrol_users"
            assert data["enrolments[0][roleid]"] == "5"
            assert data["enrolments[0][userid]"] == 7
            assert data["enrolments[0][courseid]"] == "10"

    def test_desmatricular_de_curso(self, repo):
        with patch.object(repo._session, "post") as mock_post:
            mock_post.side_effect = [
                _mock_response([{"id": 7, "username": "alumno1"}]),
                _mock_response({}),
            ]
            result = repo.desmatricular_de_curso("alumno1", "10")
            assert result is True
            data = mock_post.call_args.kwargs["data"]
            assert data["wsfunction"] == "enrol_manual_unenrol_users"

    def test_obtener_matriculas_de_usuario(self, repo):
        with patch.object(repo._session, "post") as mock_post:
            mock_post.side_effect = [
                _mock_response([{"id": 7, "username": "alumno1"}]),
                _mock_response([{"id": 10, "shortname": "C1"}]),
            ]
            result = repo.obtener_matriculas("alumno1")
            assert len(result) == 1
            assert result[0]["shortname"] == "C1"
            data = mock_post.call_args.kwargs["data"]
            assert data["wsfunction"] == "core_enrol_get_users_courses"


class TestCohortes:
    """Valida operaciones sobre cohortes."""

    def test_matricular_en_cohorte_busca_y_anade(self, repo):
        with patch.object(repo._session, "post") as mock_post:
            mock_post.side_effect = [
                _mock_response([{"id": 7, "username": "alumno1"}]),
                _mock_response({"cohorts": [{"id": 3, "name": "Grupo A"}]}),
                _mock_response({}),
            ]
            result = repo.matricular_en_cohorte("alumno1", "Grupo A")
            assert result is True

            calls = mock_post.call_args_list
            assert calls[1].kwargs["data"]["wsfunction"] == "core_cohort_search_cohorts"

            data = calls[2].kwargs["data"]
            assert data["wsfunction"] == "core_cohort_add_cohort_members"
            assert data["members[0][cohorttype][value]"] == 3
            assert data["members[0][usertype][value]"] == 7

    def test_remove_user_from_cohorte_elimina_miembro(self, repo):
        with patch.object(repo._session, "post") as mock_post:
            mock_post.side_effect = [
                _mock_response([{"id": 7, "username": "alumno1"}]),
                _mock_response({"cohorts": [{"id": 3, "name": "Grupo A"}]}),
                _mock_response({}),
            ]
            result = repo.remove_user_from_cohort("alumno1", "Grupo A")
            assert result is True
            data = mock_post.call_args.kwargs["data"]
            assert data["wsfunction"] == "core_cohort_delete_cohort_members"
            assert data["members[0][cohortid]"] == 3
            assert data["members[0][userid]"] == 7

    def test_remove_user_from_cohorte_detecta_funcion_no_disponible(self, repo):
        with patch.object(repo._session, "post") as mock_post:
            mock_post.side_effect = [
                _mock_response([{"id": 7, "username": "alumno1"}]),
                _mock_response({"cohorts": [{"id": 3, "name": "Grupo A"}]}),
                MoodleError(mensaje="error: functionnotavailable"),
            ]
            with pytest.raises(NotImplementedError, match="core_cohort_delete_cohort_members"):
                repo.remove_user_from_cohort("alumno1", "Grupo A")


class TestSinkAlias:
    """Valida alias de la interfaz MoodleSink."""

    def test_create_user_delega_a_crear_usuario(self, repo):
        with patch.object(repo._session, "post") as mock_post:
            mock_post.return_value = _mock_response([{"id": 99}])
            user_id = repo.create_user("alumno1", "a@e.com", "A", "B")
            assert user_id == 99
            data = mock_post.call_args.kwargs["data"]
            assert data["wsfunction"] == "core_user_create_users"

    def test_update_user_email_delega_a_actualizar(self, repo):
        with patch.object(repo._session, "post") as mock_post:
            mock_post.side_effect = [
                _mock_response([{"id": 7, "username": "alumno1"}]),
                _mock_response({"id": 7}),
            ]
            result = repo.update_user_email("alumno1", "nuevo@e.com")
            assert result is True
            data = mock_post.call_args.kwargs["data"]
            assert data["wsfunction"] == "core_user_update_users"
            assert data["users[0][email]"] == "nuevo@e.com"

    def test_enrol_user_to_course_delega_a_matricular(self, repo):
        with patch.object(repo._session, "post") as mock_post:
            mock_post.side_effect = [
                _mock_response([{"id": 7, "username": "alumno1"}]),
                _mock_response({}),
            ]
            result = repo.enrol_user_to_course("alumno1", "10")
            assert result is True
            data = mock_post.call_args.kwargs["data"]
            assert data["wsfunction"] == "enrol_manual_enrol_users"

    def test_suspend_enrolment_no_implementado(self, repo):
        with pytest.raises(NotImplementedError, match="suspend_enrolment"):
            repo.suspend_enrolment("alumno1", "10")

    def test_reactivate_enrolment_no_implementado(self, repo):
        with pytest.raises(NotImplementedError, match="reactivate_enrolment"):
            repo.reactivate_enrolment("alumno1", "10")
