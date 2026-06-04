"""Servicio principal de gestión de alumnos.

Orquesta la sincronización completa entre SIGAD y Moodle.
"""

from typing import TYPE_CHECKING

from gestion_alumnos.core.config import Settings
from gestion_alumnos.core.logging import get_logger

if TYPE_CHECKING:
    from gestion_alumnos.repositories.protocols import (
        EmailRepository,
        EstudianteRepository,
        MoodleRepository,
    )

logger = get_logger(__name__)


class ResultadoSync:
    """Resultado de una sincronización."""

    def __init__(self) -> None:
        self.alumnos_sigad = 0
        self.alumnos_moodle = 0
        self.nuevos_creados = 0
        self.suspendidos = 0
        self.reactivados = 0
        self.emails_actualizados = 0
        self.usernames_actualizados = 0
        self.matriculas_creadas = 0
        self.matriculas_suspendidas = 0
        self.emails_enviados = 0
        self.emails_fallidos = 0
        self.errores: list[str] = []

    def to_markdown(self) -> str:
        """Genera un resumen en Markdown."""
        return f"""
## Resumen de Sincronización

| Métrica | Valor |
|---------|-------|
| Alumnos en SIGAD | {self.alumnos_sigad} |
| Alumnos en Moodle | {self.alumnos_moodle} |
| Nuevos creados | {self.nuevos_creados} |
| Suspendidos | {self.suspendidos} |
| Reactivados | {self.reactivados} |
| Emails actualizados | {self.emails_actualizados} |
| Usernames actualizados | {self.usernames_actualizados} |
| Matrículas creadas | {self.matriculas_creadas} |
| Matrículas suspendidas | {self.matriculas_suspendidas} |
| Emails enviados | {self.emails_enviados} |
| Emails fallidos | {self.emails_fallidos} |
| Errores | {len(self.errores)} |
"""


class GestionAlumnosService:
    """Orquesta la sincronización entre SIGAD y Moodle."""

    def __init__(
        self,
        estudiante_repo: "EstudianteRepository",
        moodle_repo: "MoodleRepository",
        email_repo: "EmailRepository | None",
        settings: Settings | None = None,
    ) -> None:
        self._estudiante_repo = estudiante_repo
        self._moodle_repo = moodle_repo
        self._email_repo = email_repo
        self._settings = settings or Settings()
        self._resultado = ResultadoSync()

    def ejecutar_sincronizacion_completa(self) -> ResultadoSync:
        """Ejecuta el flujo completo de sincronización.

        Returns:
            ResultadoSync con estadísticas de la operación.
        """
        logger.info("Iniciando sincronización completa")
        self._resultado = ResultadoSync()

        # 1. Obtener datos de SIGAD
        registro = self._estudiante_repo.obtener_registro()
        self._resultado.alumnos_sigad = registro.total_alumnos
        logger.info(f"Alumnos en SIGAD: {registro.total_alumnos}")

        # 2. Obtener usuarios de Moodle
        usuarios_moodle = self._moodle_repo.obtener_todos_usuarios()
        self._resultado.alumnos_moodle = len(usuarios_moodle)
        logger.info(f"Alumnos en Moodle: {len(usuarios_moodle)}")

        # 3. Crear/actualizar usuarios
        for alumno in registro.alumnos:
            self._procesar_alumno(alumno)

        # 4. Suspender bajas
        self._suspender_bajas(registro, usuarios_moodle)

        # 5. Generar informe
        logger.markdown(self._resultado.to_markdown())
        return self._resultado

    def _procesar_alumno(self, alumno) -> None:
        """Procesa un alumno: crea, actualiza o matricula."""
        username = alumno.username_moodle

        if not self._moodle_repo.usuario_existe(username):
            self._crear_usuario(alumno)
        else:
            self._actualizar_usuario(alumno)

        # Matricular en módulos
        for modulo in alumno.obtener_todos_modulos():
            try:
                self._moodle_repo.matricular_en_curso(username, modulo.siglas)
                self._resultado.matriculas_creadas += 1
                logger.info(
                    "Matriculado en curso",
                    username=username,
                    curso=modulo.siglas,
                )
            except Exception as e:
                logger.warning(
                    f"No se pudo matricular en {modulo.siglas}: {e}",
                    username=username,
                )

    def _crear_usuario(self, alumno) -> None:
        """Crea un nuevo usuario en Moodle."""
        import secrets
        import string

        password = "".join(
            secrets.choice(string.ascii_letters + string.digits) for _ in range(10)
        )
        try:
            user_id = self._moodle_repo.crear_usuario(
                username=alumno.username_moodle,
                email=alumno.email_institucional,
                nombre=alumno.nombre,
                apellido=f"{alumno.apellido1} {alumno.apellido2 or ''}".strip(),
                password=password,
            )
            self._resultado.nuevos_creados += 1
            logger.info(
                "Usuario creado",
                username=alumno.username_moodle,
                user_id=user_id,
            )

            # Matricular en cohorte general
            self._moodle_repo.matricular_en_cohorte(
                alumno.username_moodle, "alumnado"
            )

            # Enviar email de bienvenida
            if self._email_repo and not self._email_repo.limite_alcanzado():
                modulos = [m.siglas for m in alumno.obtener_todos_modulos()]
                try:
                    self._email_repo.enviar_bienvenida_nuevo_usuario(
                        alumno, password, modulos
                    )
                    self._resultado.emails_enviados += 1
                except Exception as e:
                    self._resultado.emails_fallidos += 1
                    logger.error(f"Error enviando email: {e}")
        except Exception as e:
            self._resultado.errores.append(
                f"Error creando {alumno.username_moodle}: {e}"
            )
            logger.error(f"Error creando usuario: {e}", username=alumno.username_moodle)

    def _actualizar_usuario(self, alumno) -> None:
        """Actualiza un usuario existente si hay cambios."""
        # Aquí se compararía el alumno SIGAD con el usuario Moodle
        # y se actualizarían email, username, etc. si cambiaron.
        # Por simplicidad, se deja como stub.
        pass

    def _suspender_bajas(self, registro, usuarios_moodle: list[dict]) -> None:
        """Suspende usuarios que están en Moodle pero no en SIGAD."""
        documentos_sigad = {a.documento.lower() for a in registro.alumnos}
        for usuario in usuarios_moodle:
            username = usuario.get("username", "").lower()
            user_id = usuario.get("id", 0)
            if user_id in {1, 2, 3}:  # protegidos básicos
                continue
            if username not in documentos_sigad:
                try:
                    self._moodle_repo.suspender_usuario(username)
                    self._resultado.suspendidos += 1
                    logger.info("Usuario suspendido", username=username)
                except Exception as e:
                    logger.warning(f"No se pudo suspender {username}: {e}")
