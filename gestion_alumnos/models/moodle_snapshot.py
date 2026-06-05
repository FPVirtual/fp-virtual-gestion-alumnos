"""Modelos planos para datos extraídos de Moodle.

Representan la estructura de Moodle de forma normalizada,
sin jerarquías, para facilitar la comparación con SIGAD en DuckDB.
"""

from pydantic import BaseModel, ConfigDict, Field


class MoodleUserRecord(BaseModel):
    """Usuario de Moodle normalizado."""

    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(..., ge=0)
    username: str = Field(..., min_length=1)
    email: str | None = Field(None)
    firstname: str | None = Field(None)
    lastname: str | None = Field(None)
    suspended: int = Field(0, ge=0, le=1)


class MoodleCourseRecord(BaseModel):
    """Curso de Moodle normalizado."""

    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(..., ge=0)
    shortname: str = Field(..., min_length=1)
    fullname: str | None = Field(None)
    categoryid: int = Field(0, ge=0)


class MoodleEnrolmentRecord(BaseModel):
    """Matrícula de un usuario en un curso de Moodle.

    Attributes:
        user_id: ID del usuario en Moodle.
        course_id: ID del curso en Moodle.
        shortname: shortname del curso (para evitar JOINs innecesarios).
        status: 0 = activa, 1 = suspendida.
    """

    model_config = ConfigDict(populate_by_name=True)

    user_id: int = Field(..., alias="userid", ge=0)
    course_id: int = Field(..., alias="courseid", ge=0)
    shortname: str = Field(..., min_length=1)
    status: int = Field(0, ge=0, le=1)


class MoodleSnapshot(BaseModel):
    """Snapshot completo de Moodle para análisis.

    Contiene todos los datos necesarios para comparar con SIGAD
    sin necesidad de más llamadas a la red.
    """

    users: list[MoodleUserRecord] = Field(default_factory=list)
    courses: list[MoodleCourseRecord] = Field(default_factory=list)
    enrolments: list[MoodleEnrolmentRecord] = Field(default_factory=list)

    @property
    def total_users(self) -> int:
        return len(self.users)

    @property
    def total_enrolments(self) -> int:
        return len(self.enrolments)
