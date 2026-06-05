"""Modelos para el resultado del análisis de sincronización.

Representan los deltas detectados entre SIGAD y Moodle.
"""

from pydantic import BaseModel, ConfigDict, Field

from gestion_alumnos.models.alumno import Alumno
from gestion_alumnos.models.moodle_snapshot import MoodleUserRecord


class NewUserDelta(BaseModel):
    """Alumno que existe en SIGAD pero no en Moodle (alta)."""

    alumno: Alumno


class RemovedUserDelta(BaseModel):
    """Usuario que existe en Moodle pero no en SIGAD (baja)."""

    user: MoodleUserRecord


class EmailChangeDelta(BaseModel):
    """Cambio de email entre SIGAD y Moodle."""

    documento: str
    email_sigad: str | None
    email_moodle: str | None


class NameChangeDelta(BaseModel):
    """Cambio de nombre o apellidos entre SIGAD y Moodle."""

    documento: str
    nombre_sigad: str | None
    apellido1_sigad: str | None
    apellido2_sigad: str | None
    firstname_moodle: str | None
    lastname_moodle: str | None


class UsernameChangeDelta(BaseModel):
    """Cambio de documento/username (ej: NIE → DNI).

    Se detecta cruzando por email cuando el username no coincide.
    """

    old_username: str
    new_documento: str
    email: str | None


class EnrolmentDelta(BaseModel):
    """Cambio en matrícula de un usuario en un curso."""

    documento: str
    course_shortname: str
    course_id: int | None = None


class SyncReport(BaseModel):
    """Reporte completo de diferencias entre SIGAD y Moodle."""

    model_config = ConfigDict(populate_by_name=True)

    new_users: list[NewUserDelta] = Field(default_factory=list)
    removed_users: list[RemovedUserDelta] = Field(default_factory=list)
    email_changes: list[EmailChangeDelta] = Field(default_factory=list)
    name_changes: list[NameChangeDelta] = Field(default_factory=list)
    username_changes: list[UsernameChangeDelta] = Field(default_factory=list)
    new_enrolments: list[EnrolmentDelta] = Field(default_factory=list)
    removed_enrolments: list[EnrolmentDelta] = Field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        """Indica si hay algún cambio detectado."""
        return any([
            self.new_users,
            self.removed_users,
            self.email_changes,
            self.name_changes,
            self.username_changes,
            self.new_enrolments,
            self.removed_enrolments,
        ])

    def to_markdown(self) -> str:
        """Genera informe completo en Markdown con resumen y detalle."""
        lines: list[str] = [
            "# Informe de Sincronización SIGAD ↔ Moodle",
            "",
            "## Resumen",
            "",
            f"| Delta | Cantidad |",
            f"|-------|----------|",
            f"| Altas (nuevos en SIGAD) | {len(self.new_users)} |",
            f"| Bajas (en Moodle, no en SIGAD) | {len(self.removed_users)} |",
            f"| Cambios de email | {len(self.email_changes)} |",
            f"| Cambios de nombre/apellidos | {len(self.name_changes)} |",
            f"| Cambios de username (DNI/NIE) | {len(self.username_changes)} |",
            f"| Nuevas matrículas | {len(self.new_enrolments)} |",
            f"| Matrículas eliminadas | {len(self.removed_enrolments)} |",
        ]

        # Altas
        if self.new_users:
            lines.extend(["", "## Altas: nuevos usuarios en SIGAD", ""])
            for delta in self.new_users:
                a = delta.alumno
                mods = [m.siglas for c in a.centros for m in c.modulos]
                lines.append(f"- `{a.documento}` — {a.nombre} {a.apellido1} {a.apellido2 or ''} — cursos: {', '.join(mods)}")

        # Bajas
        if self.removed_users:
            lines.extend(["", "## Bajas: usuarios en Moodle no presentes en SIGAD", ""])
            for delta in self.removed_users:
                u = delta.user
                lines.append(f"- `{u.username}` — {u.firstname} {u.lastname} — id: {u.id}")

        # Cambios de email
        if self.email_changes:
            lines.extend(["", "## Cambios de email", ""])
            for delta in self.email_changes:
                lines.append(f"- `{delta.documento}`: {delta.email_moodle or 'N/A'} → {delta.email_sigad or 'N/A'}")

        # Cambios de nombre
        if self.name_changes:
            lines.extend(["", "## Cambios de nombre/apellidos", ""])
            for delta in self.name_changes:
                lines.append(
                    f"- `{delta.documento}`: "
                    f"{delta.firstname_moodle or ''} {delta.lastname_moodle or ''} → "
                    f"{delta.nombre_sigad or ''} {delta.apellido1_sigad or ''} {delta.apellido2_sigad or ''}"
                )

        # Cambios de username
        if self.username_changes:
            lines.extend(["", "## Cambios de username (DNI/NIE)", ""])
            for delta in self.username_changes:
                lines.append(f"- `{delta.old_username}` → `{delta.new_documento}` — email: {delta.email or 'N/A'}")

        # Nuevas matrículas
        if self.new_enrolments:
            lines.extend(["", "## Nuevas matrículas", ""])
            for delta in self.new_enrolments:
                lines.append(f"- `{delta.documento}` → `{delta.course_shortname}`")

        # Matrículas eliminadas
        if self.removed_enrolments:
            lines.extend(["", "## Matrículas eliminadas", ""])
            for delta in self.removed_enrolments:
                lines.append(f"- `{delta.documento}` → `{delta.course_shortname}`")

        if not self.has_changes:
            lines.extend(["", "*No se detectaron diferencias entre SIGAD y Moodle.*"])

        return "\n".join(lines)
