"""Clase base para implementaciones de MoodleSource.

Proporciona un `extract_all()` por defecto que compone los tres métodos
individuales, permitiendo que las fuentes que SÍ soporten bulk lo
sobrescriban.
"""

from __future__ import annotations

from gestion_alumnos.models import MoodleCourseRecord, MoodleEnrolmentRecord, MoodleSnapshot, MoodleUserRecord
from gestion_alumnos.repositories.protocols import MoodleSource


class BaseMoodleSource(MoodleSource):
    """Base con implementación por defecto de `extract_all()`."""

    def extract_all(self) -> MoodleSnapshot:
        """Compone un snapshot llamando a los tres extractores individuales.

        Implementaciones que soporten bulk (ej: plugin PHP) pueden
        sobrescribir este método para hacer una sola llamada.
        """
        users_raw = self.extract_users()
        courses_raw = self.extract_courses()
        enrolments_raw = self.extract_enrolments()

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
