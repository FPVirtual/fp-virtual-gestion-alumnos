"""MoodleSource que consume el plugin PHP local_fparagon.

Requiere que esté instalado el plugin `local_fparagon` en Moodle,
que expone la función REST `local_fparagon_get_snapshot`.

Con una sola llamada obtiene usuarios, cursos y matriculaciones.
"""

from __future__ import annotations

from gestion_alumnos.core.config import Settings
from gestion_alumnos.core.exceptions import MoodleError
from gestion_alumnos.core.logging import get_logger
from gestion_alumnos.models import (
    MoodleCourseRecord,
    MoodleEnrolmentRecord,
    MoodleSnapshot,
    MoodleUserRecord,
)
from gestion_alumnos.repositories.moodle_api_repository import APIMoodleRepository
from gestion_alumnos.repositories.moodle_sources.base import BaseMoodleSource

logger = get_logger(__name__)


class APISnapshotMoodleSource(BaseMoodleSource):
    """Fuente de Moodle optimizada vía plugin PHP snapshot."""

    def __init__(self, repo: APIMoodleRepository | None = None, settings: Settings | None = None) -> None:
        self._repo = repo or APIMoodleRepository(settings)

    def extract_users(self) -> list[dict]:
        """Fallback: extrae vía API estándar si el snapshot no está disponible."""
        return self._repo.obtener_todos_usuarios()

    def extract_courses(self) -> list[dict]:
        """Fallback: extrae vía API estándar."""
        return self._repo.obtener_todos_cursos()

    def extract_enrolments(self) -> list[dict]:
        """Fallback: lanza error indicando que se use la fuente por cursos."""
        raise NotImplementedError(
            "APISnapshotMoodleSource no soporta extract_enrolments individual. "
            "Usa extract_all() para obtener todo de golpe."
        )

    def extract_all(self) -> MoodleSnapshot:
        """Llama al plugin PHP y devuelve snapshot completo."""
        try:
            result = self._repo._call("local_fparagon_get_snapshot", {})
        except MoodleError as e:
            if "functionnotavailable" in str(e).lower() or "invalidparameter" in str(e).lower():
                raise MoodleError(
                    mensaje="Plugin local_fparagon no instalado o función no disponible. "
                            "Despliega el plugin en Moodle o usa APICourseBasedMoodleSource.",
                    detalles=str(e),
                ) from e
            raise

        if not isinstance(result, dict):
            raise MoodleError(mensaje="Respuesta inesperada de local_fparagon_get_snapshot")

        users_raw = result.get("usuarios", [])
        enrolments_raw = result.get("matriculas", [])

        return MoodleSnapshot(
            users=[
                MoodleUserRecord(
                    id=u.get("id", 0),
                    username=u.get("username", ""),
                    email=u.get("email"),
                    firstname=u.get("firstname"),
                    lastname=u.get("lastname"),
                    suspended=u.get("suspended", 0),
                )
                for u in users_raw
            ],
            courses=[],  # el snapshot del plugin puede no incluir cursos; no se usan en el analyzer
            enrolments=[
                MoodleEnrolmentRecord(
                    user_id=e.get("userid", e.get("user_id", 0)),
                    course_id=e.get("courseid", e.get("course_id", 0)),
                    shortname=e.get("shortname", ""),
                    status=e.get("status", 0),
                )
                for e in enrolments_raw
            ],
        )
