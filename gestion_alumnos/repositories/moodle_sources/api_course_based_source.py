"""MoodleSource que extrae datos iterando cursos vía API REST.

Estrategia:
  1. Obtiene todos los cursos (1 llamada: core_course_get_courses)
  2. Para cada curso, obtiene usuarios matriculados (N llamadas:
     core_enrol_get_enrolled_users)
  3. Invierte la relación para obtener matrículas usuario-curso.

Coste: ~1 + N_cursos llamadas HTTP.
"""

from __future__ import annotations

from gestion_alumnos.core.config import Settings
from gestion_alumnos.core.logging import get_logger
from gestion_alumnos.models import MoodleSnapshot
from gestion_alumnos.repositories.moodle_api_repository import APIMoodleRepository
from gestion_alumnos.repositories.moodle_sources.base import BaseMoodleSource

logger = get_logger(__name__)


class APICourseBasedMoodleSource(BaseMoodleSource):
    """Fuente de Moodle basada en API REST iterando por cursos."""

    def __init__(self, repo: APIMoodleRepository | None = None, settings: Settings | None = None) -> None:
        self._repo = repo or APIMoodleRepository(settings)

    def extract_users(self) -> list[dict]:
        """Devuelve todos los usuarios de Moodle."""
        return self._repo.obtener_todos_usuarios()

    def extract_courses(self) -> list[dict]:
        """Devuelve todos los cursos visibles de Moodle."""
        return self._repo.obtener_todos_cursos()

    def extract_enrolments(self) -> list[dict]:
        """Itera todos los cursos y acumula matrículas."""
        cursos = self.extract_courses()
        total_cursos = len(cursos)
        logger.info(f"Obteniendo matriculaciones de {total_cursos} cursos")

        enrolments: list[dict] = []
        for idx, curso in enumerate(cursos, 1):
            course_id_raw = curso.get("id")
            if course_id_raw is None:
                continue
            course_id = str(course_id_raw)
            shortname = curso.get("shortname", "")
            if not course_id:
                continue
            try:
                usuarios = self._repo.obtener_usuarios_matriculados_en_curso(course_id)
                for u in usuarios:
                    enrolments.append({
                        "userid": u.get("id"),
                        "courseid": course_id,
                        "shortname": shortname,
                        "status": 0,  # API core_enrol_get_enrolled_users solo devuelve activos
                    })
                if idx % 100 == 0:
                    logger.debug(f"Procesados {idx}/{total_cursos} cursos")
            except Exception as e:
                logger.warning(f"Error obteniendo matriculados del curso {course_id}: {e}")

        logger.info(f"Matriculaciones extraídas: {len(enrolments)}")
        return enrolments

    def extract_all(self) -> MoodleSnapshot:
        """Compone snapshot sin llamar dos veces a los extractores."""
        users_raw = self.extract_users()
        courses_raw = self.extract_courses()
        enrolments_raw = self.extract_enrolments()

        from gestion_alumnos.models import (
            MoodleCourseRecord,
            MoodleEnrolmentRecord,
            MoodleUserRecord,
        )

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
            courses=[
                MoodleCourseRecord(
                    id=c.get("id", 0),
                    shortname=c.get("shortname", ""),
                    fullname=c.get("fullname"),
                    categoryid=c.get("categoryid", 0),
                )
                for c in courses_raw
            ],
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
