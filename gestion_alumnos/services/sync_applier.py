"""Aplicador de cambios sobre Moodle.

Recibe un SyncReport y un MoodleSink, y ejecuta las operaciones
necesarias en el orden correcto, con manejo de errores por bloque.
"""

from __future__ import annotations

import secrets
import string

from gestion_alumnos.core.logging import get_logger
from gestion_alumnos.models import SyncReport
from gestion_alumnos.repositories.protocols import MoodleSink

logger = get_logger(__name__)


class SyncApplier:
    """Aplica un SyncReport sobre Moodle mediante un MoodleSink.

    Orden de aplicación:
      1. Altas (crear usuarios)
      2. Cambios de datos personales (email, nombre, username)
      3. Nuevas matrículas
      4. Matrículas eliminadas/suspendidas
      5. Bajas (suspender usuarios no existentes en SIGAD)
    """

    def __init__(
        self,
        report: SyncReport,
        sink: MoodleSink,
        course_mapping: dict[str, str] | None = None,
    ) -> None:
        self._report = report
        self._sink = sink
        self._course_mapping = course_mapping or {}

    def apply(self) -> dict:
        """Ejecuta todas las operaciones y devuelve estadísticas."""
        stats = {
            "users_created": 0,
            "users_created_errors": [],
            "emails_updated": 0,
            "emails_updated_errors": [],
            "names_updated": 0,
            "names_updated_errors": [],
            "usernames_updated": 0,
            "usernames_updated_errors": [],
            "enrolments_created": 0,
            "enrolments_created_errors": [],
            "enrolments_removed": 0,
            "enrolments_removed_errors": [],
            "users_suspended": 0,
            "users_suspended_errors": [],
        }

        self._apply_new_users(stats)
        self._apply_email_changes(stats)
        self._apply_name_changes(stats)
        self._apply_username_changes(stats)
        self._apply_new_enrolments(stats)
        self._apply_removed_enrolments(stats)
        self._apply_removed_users(stats)

        return stats

    def _apply_new_users(self, stats: dict) -> None:
        for delta in self._report.new_users:
            alumno = delta.alumno
            password = "".join(
                secrets.choice(string.ascii_letters + string.digits) for _ in range(10)
            )
            try:
                self._sink.create_user(
                    username=alumno.username_moodle,
                    email=alumno.email_institucional,
                    nombre=alumno.nombre or "",
                    apellido=alumno.nombre_completo.replace(alumno.nombre or "", "").strip(),
                    password=password,
                )
                stats["users_created"] += 1
                logger.info("Usuario creado", username=alumno.username_moodle)
            except Exception as e:
                stats["users_created_errors"].append(
                    f"{alumno.username_moodle}: {e}"
                )
                logger.error(f"Error creando usuario: {e}", username=alumno.username_moodle)

    def _apply_email_changes(self, stats: dict) -> None:
        for delta in self._report.email_changes:
            if not delta.email_sigad:
                continue
            try:
                self._sink.update_user_email(
                    delta.documento.lower(),
                    delta.email_sigad,
                )
                stats["emails_updated"] += 1
                logger.info("Email actualizado", username=delta.documento)
            except Exception as e:
                stats["emails_updated_errors"].append(f"{delta.documento}: {e}")
                logger.error(f"Error actualizando email: {e}", username=delta.documento)

    def _apply_name_changes(self, stats: dict) -> None:
        # Nota: Moodle tiene firstname + lastname, SIGAD tiene nombre + apellido1 + apellido2
        # Esta operación requiere actualizar ambos campos.
        for delta in self._report.name_changes:
            try:
                # Construimos un apellido combinado si es necesario
                apellidos = " ".join(
                    filter(None, [delta.apellido1_sigad, delta.apellido2_sigad])
                )
                self._sink.update_user(
                    delta.documento.lower(),
                    firstname=delta.nombre_sigad or "",
                    lastname=apellidos,
                )
                stats["names_updated"] += 1
                logger.info("Nombre actualizado", username=delta.documento)
            except Exception as e:
                stats["names_updated_errors"].append(f"{delta.documento}: {e}")
                logger.error(f"Error actualizando nombre: {e}", username=delta.documento)

    def _apply_username_changes(self, stats: dict) -> None:
        for delta in self._report.username_changes:
            try:
                self._sink.update_user_username(
                    delta.old_username,
                    delta.new_documento.lower(),
                )
                stats["usernames_updated"] += 1
                logger.info(
                    "Username actualizado",
                    old=delta.old_username,
                    new=delta.new_documento,
                )
            except Exception as e:
                stats["usernames_updated_errors"].append(
                    f"{delta.old_username}->{delta.new_documento}: {e}"
                )
                logger.error(f"Error actualizando username: {e}", old=delta.old_username)

    def _apply_new_enrolments(self, stats: dict) -> None:
        for delta in self._report.new_enrolments:
            course_id = self._course_mapping.get(delta.course_shortname)
            if not course_id:
                logger.warning(
                    "Curso no encontrado en mapping, omitiendo matrícula",
                    shortname=delta.course_shortname,
                )
                continue
            try:
                self._sink.enrol_user_to_course(delta.documento.lower(), course_id)
                stats["enrolments_created"] += 1
                logger.info(
                    "Matrícula creada",
                    username=delta.documento,
                    course=delta.course_shortname,
                )
            except Exception as e:
                stats["enrolments_created_errors"].append(
                    f"{delta.documento} -> {delta.course_shortname}: {e}"
                )
                logger.error(f"Error matriculando: {e}", username=delta.documento)

    def _apply_removed_enrolments(self, stats: dict) -> None:
        for delta in self._report.removed_enrolments:
            course_id = delta.course_id
            if not course_id:
                course_id = self._course_mapping.get(delta.course_shortname)
            if not course_id:
                logger.warning(
                    "Curso no encontrado para desmatriculación",
                    shortname=delta.course_shortname,
                )
                continue
            try:
                self._sink.suspend_enrolment(delta.documento.lower(), str(course_id))
                stats["enrolments_removed"] += 1
                logger.info(
                    "Matrícula suspendida",
                    username=delta.documento,
                    course=delta.course_shortname,
                )
            except NotImplementedError:
                # Fallback: desmatricular completamente si no hay soporte para suspender
                try:
                    self._sink.enrol_user_to_course(delta.documento.lower(), str(course_id))
                except Exception:
                    pass
                logger.warning(
                    "suspend_enrolment no implementado, se requiere plugin local_fparagon",
                    username=delta.documento,
                )
            except Exception as e:
                stats["enrolments_removed_errors"].append(
                    f"{delta.documento} -> {delta.course_shortname}: {e}"
                )
                logger.error(f"Error suspendiendo matrícula: {e}", username=delta.documento)

    def _apply_removed_users(self, stats: dict) -> None:
        for delta in self._report.removed_users:
            user = delta.user
            try:
                self._sink.suspend_user(user.username)
                stats["users_suspended"] += 1
                logger.info("Usuario suspendido", username=user.username)
            except Exception as e:
                stats["users_suspended_errors"].append(f"{user.username}: {e}")
                logger.error(f"Error suspendiendo usuario: {e}", username=user.username)
