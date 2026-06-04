"""Implementación de MoodleRepository usando API REST.

Usa ``requests`` contra la API REST de Moodle con token de servicio.
"""

import requests

from gestion_alumnos.core.config import Settings
from gestion_alumnos.core.exceptions import MoodleError
from gestion_alumnos.core.logging import get_logger
from gestion_alumnos.repositories.protocols import MoodleRepository

logger = get_logger(__name__)


class APIMoodleRepository(MoodleRepository):
    """Repositorio de Moodle usando API REST.

    Documentación: https://docs.moodle.org/dev/Web_service_API_functions
    """

    USUARIOS_PROTEGIDOS = frozenset({
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
        16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28,
        29, 30, 31, 32, 33, 3725, 3729, 3730, 7152, 7490,
        7491, 11720, 12270, 12272,
    })

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/json",
            "User-Agent": "gestion-alumnos/0.3.0",
        })
        if not self._settings.moodle_api_url or not self._settings.moodle_api_token:
            raise MoodleError(
                mensaje="Faltan MOODLE_API_URL o MOODLE_API_TOKEN para driver=api"
            )

    def _call(self, wsfunction: str, params: dict | None = None) -> dict | list:
        """Realiza una llamada a la API REST de Moodle.

        Args:
            wsfunction: Nombre de la función del webservice.
            params: Parámetros adicionales.

        Returns:
            Respuesta JSON parseada.

        Raises:
            MoodleError: Si la API retorna error.
        """
        data = {
            "wstoken": self._settings.moodle_api_token,
            "wsfunction": wsfunction,
            "moodlewsrestformat": "json",
        }
        if params:
            data.update(params)
        try:
            logger.debug(f"API Moodle: {wsfunction}")
            response = self._session.post(
                self._settings.moodle_api_url,
                data=data,
                timeout=60,
            )
            response.raise_for_status()
            result = response.json()
            if isinstance(result, dict) and "exception" in result:
                raise MoodleError(
                    mensaje=f"API Moodle error: {result.get('message')}",
                    comando=wsfunction,
                    detalles=result,
                )
            return result
        except requests.RequestException as e:
            raise MoodleError(
                mensaje=f"Error de conexión con API Moodle: {e}",
                comando=wsfunction,
            )

    def usuario_existe(self, username: str) -> bool:
        """Verifica si existe un usuario en Moodle."""
        result = self._call(
            "core_user_get_users_by_field",
            {"field": "username", "values[0]": username},
        )
        return bool(result)

    def crear_usuario(
        self,
        username: str,
        email: str,
        nombre: str,
        apellido: str,
        password: str | None = None,
    ) -> int:
        """Crea un usuario en Moodle.

        Returns:
            ID del usuario creado.
        """
        params = {
            "users[0][username]": username,
            "users[0][email]": email,
            "users[0][firstname]": nombre,
            "users[0][lastname]": apellido,
            "users[0][auth]": "manual",
        }
        if password:
            params["users[0][password]"] = password
        result = self._call("core_user_create_users", params)
        if isinstance(result, list) and len(result) > 0:
            return result[0].get("id", 0)
        return 0

    def actualizar_usuario(self, username: str, **campos) -> bool:
        """Actualiza campos de un usuario."""
        # Primero obtenemos el ID por username
        users = self._call(
            "core_user_get_users_by_field",
            {"field": "username", "values[0]": username},
        )
        if not users:
            raise MoodleError(mensaje=f"Usuario no encontrado: {username}")
        user_id = users[0]["id"]
        params = {"users[0][id]": user_id}
        for idx, (campo, valor) in enumerate(campos.items()):
            params[f"users[0][{campo}]"] = str(valor)
        self._call("core_user_update_users", params)
        return True

    def suspender_usuario(self, username: str) -> bool:
        """Suspende un usuario."""
        return self.actualizar_usuario(username, suspended="1")

    def reactivar_usuario(self, username: str) -> bool:
        """Reactiva un usuario suspendido."""
        return self.actualizar_usuario(username, suspended="0")

    def matricular_en_curso(self, username: str, curso_id: str) -> bool:
        """Matricula un usuario en un curso."""
        users = self._call(
            "core_user_get_users_by_field",
            {"field": "username", "values[0]": username},
        )
        if not users:
            raise MoodleError(mensaje=f"Usuario no encontrado: {username}")
        user_id = users[0]["id"]
        params = {
            "enrolments[0][roleid]": "5",  # estudiante
            "enrolments[0][userid]": user_id,
            "enrolments[0][courseid]": curso_id,
        }
        self._call("enrol_manual_enrol_users", params)
        return True

    def desmatricular_de_curso(self, username: str, curso_id: str) -> bool:
        """Desmatricula un usuario de un curso."""
        users = self._call(
            "core_user_get_users_by_field",
            {"field": "username", "values[0]": username},
        )
        if not users:
            raise MoodleError(mensaje=f"Usuario no encontrado: {username}")
        user_id = users[0]["id"]
        params = {
            "enrolments[0][userid]": user_id,
            "enrolments[0][courseid]": curso_id,
        }
        self._call("enrol_manual_unenrol_users", params)
        return True

    def matricular_en_cohorte(self, username: str, cohorte: str) -> bool:
        """Matricula un usuario en una cohorte."""
        users = self._call(
            "core_user_get_users_by_field",
            {"field": "username", "values[0]": username},
        )
        if not users:
            raise MoodleError(mensaje=f"Usuario no encontrado: {username}")
        user_id = users[0]["id"]
        # Obtener ID de la cohorte por nombre
        cohorts = self._call("core_cohort_search_cohorts", {"query": cohorte})
        cohort_id = None
        if isinstance(cohorts, dict) and "cohorts" in cohorts:
            for c in cohorts["cohorts"]:
                if c.get("name") == cohorte or c.get("idnumber") == cohorte:
                    cohort_id = c["id"]
                    break
        if not cohort_id:
            raise MoodleError(mensaje=f"Cohorte no encontrada: {cohorte}")
        params = {
            "members[0][cohorttype][type]": "id",
            "members[0][cohorttype][value]": cohort_id,
            "members[0][usertype][type]": "id",
            "members[0][usertype][value]": user_id,
        }
        self._call("core_cohort_add_cohort_members", params)
        return True

    def obtener_matriculas(self, username: str) -> list[dict]:
        """Obtiene las matrículas activas de un usuario."""
        users = self._call(
            "core_user_get_users_by_field",
            {"field": "username", "values[0]": username},
        )
        if not users:
            return []
        user_id = users[0]["id"]
        result = self._call(
            "core_enrol_get_users_courses", {"userid": user_id}
        )
        if isinstance(result, list):
            return [{"id": c["id"], "shortname": c["shortname"]} for c in result]
        return []

    def obtener_todos_usuarios(self) -> list[dict]:
        """Obtiene todos los usuarios de Moodle."""
        # Usar core_user_get_users con criterio vacío para obtener todos
        result = self._call(
            "core_user_get_users",
            {
                "criteria[0][key]": "",
                "criteria[0][value]": "",
            },
        )
        if isinstance(result, dict) and "users" in result:
            return result["users"]
        return []

    def obtener_por_username(self, username: str) -> dict | None:
        """Obtiene un usuario por su username."""
        result = self._call(
            "core_user_get_users_by_field",
            {"field": "username", "values[0]": username},
        )
        if isinstance(result, list) and len(result) > 0:
            return result[0]
        return None
