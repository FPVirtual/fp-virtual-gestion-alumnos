"""Modelos de dominio del paquete gestion-alumnos."""

from gestion_alumnos.models.alumno import Alumno
from gestion_alumnos.models.centro import Centro
from gestion_alumnos.models.ciclo import Ciclo
from gestion_alumnos.models.modulo import Modulo
from gestion_alumnos.models.registro import Registro
from gestion_alumnos.models.moodle_snapshot import (
    MoodleCourseRecord,
    MoodleEnrolmentRecord,
    MoodleSnapshot,
    MoodleUserRecord,
)
from gestion_alumnos.models.sync_report import (
    EmailChangeDelta,
    EnrolmentDelta,
    NameChangeDelta,
    NewUserDelta,
    RemovedUserDelta,
    SyncReport,
    UsernameChangeDelta,
)

__all__ = [
    "Alumno",
    "Centro",
    "Ciclo",
    "Modulo",
    "Registro",
    "MoodleCourseRecord",
    "MoodleEnrolmentRecord",
    "MoodleSnapshot",
    "MoodleUserRecord",
    "EmailChangeDelta",
    "EnrolmentDelta",
    "NameChangeDelta",
    "NewUserDelta",
    "RemovedUserDelta",
    "SyncReport",
    "UsernameChangeDelta",
]
