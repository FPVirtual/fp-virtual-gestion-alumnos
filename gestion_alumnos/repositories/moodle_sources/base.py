"""Clase base para implementaciones de MoodleSource.

Proporciona un `extract_all()` por defecto que compone los tres métodos
individuales, permitiendo que las fuentes que SÍ soporten bulk lo
sobrescriban.
"""

from __future__ import annotations

from gestion_alumnos.models import MoodleCourseRecord, MoodleEnrolmentRecord, MoodleSnapshot, MoodleUserRecord
from gestion_alumnos.repositories.protocols import MoodleSource


def _extract_customfield(user_dict: dict, shortname: str) -> str | None:
    """Extrae el valor de un custom field por su shortname.

    Args:
        user_dict: Diccionario devuelto por Moodle (puede contener
            `customfields`).
        shortname: Shortname del campo personalizado.

    Returns:
        El valor del campo como string, o None si no está disponible.
    """
    customfields = user_dict.get("customfields") or []
    for field in customfields:
        if field.get("shortname") == shortname:
            value = field.get("value")
            return str(value) if value is not None else None
    return None


def _extract_id_sigad(user_dict: dict) -> int | None:
    """Extrae el valor numérico del custom field IdSIGAD de un usuario."""
    value = _extract_customfield(user_dict, "IdSIGAD")
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _extract_email_sigad(user_dict: dict) -> str | None:
    """Extrae el valor del custom field emailsigad de un usuario."""
    return _extract_customfield(user_dict, "emailsigad")


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
                    id_sigad=_extract_id_sigad(u),
                    email_sigad=_extract_email_sigad(u),
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
