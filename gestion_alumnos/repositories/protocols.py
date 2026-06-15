"""Protocols (interfaces) para repositorios.

Define contratos que deben cumplir las implementaciones,
permitiendo inyección de dependencias y testing.
"""

from typing import Protocol, runtime_checkable

from gestion_alumnos.models import Alumno, MoodleSnapshot, Registro


# ==========================================
# Protocols de Repositorios
# ==========================================
@runtime_checkable
class EstudianteRepository(Protocol):
    """Protocolo para repositorios de estudiantes.

    Abstrae la fuente de datos (API SIGAD, archivo JSON, etc.)
    """

    def obtener_registro(self) -> Registro:
        """Obtiene el registro completo de estudiantes.

        Returns:
            Registro con todos los alumnos matriculados.

        Raises:
            APIError: Si hay problemas con la API.
            FileNotFoundError: Si no hay datos disponibles.
        """
        ...

    def buscar_por_documento(self, documento: str) -> Alumno | None:
        """Busca un alumno por documento.

        Args:
            documento: DNI/NIE a buscar.

        Returns:
            Alumno encontrado o None.
        """
        ...


# ==========================================
# Protocols de Moodle (LEGACY - unificado)
# ==========================================
@runtime_checkable
class MoodleRepository(Protocol):
    """Protocolo unificado para operaciones de Moodle.

    Deprecado en favor de MoodleSource + MoodleSink.
    Se mantiene por compatibilidad con código existente.
    """

    def usuario_existe(self, username: str) -> bool:
        """Verifica si existe un usuario en Moodle."""
        ...

    def crear_usuario(
        self,
        username: str,
        email: str,
        nombre: str,
        apellido: str,
        password: str | None = None,
        customfields: dict[str, str] | None = None,
    ) -> int:
        """Crea un usuario en Moodle.

        Returns:
            ID del usuario creado.
        """
        ...

    def actualizar_usuario(
        self,
        username: str,
        customfields: dict[str, str] | None = None,
        **campos,
    ) -> bool:
        """Actualiza campos de un usuario.

        Args:
            customfields: Diccionario shortname -> valor con campos
                personalizados de Moodle a actualizar.
        """
        ...

    def suspender_usuario(self, username: str) -> bool:
        """Suspende un usuario."""
        ...

    def reactivar_usuario(self, username: str) -> bool:
        """Reactiva un usuario suspendido."""
        ...

    def matricular_en_curso(self, username: str, curso_id: str) -> bool:
        """Matricula un usuario en un curso."""
        ...

    def desmatricular_de_curso(self, username: str, curso_id: str) -> bool:
        """Desmatricula un usuario de un curso."""
        ...

    def matricular_en_cohorte(self, username: str, cohorte: str) -> bool:
        """Matricula un usuario en una cohorte."""
        ...

    def obtener_matriculas(self, username: str) -> list[dict]:
        """Obtiene las matrículas activas de un usuario."""
        ...

    def obtener_todos_usuarios(self) -> list[dict]:
        """Obtiene todos los usuarios de Moodle."""
        ...

    def obtener_todos_cursos(self) -> list[dict]:
        """Obtiene todos los cursos visibles de Moodle."""
        ...

    def obtener_usuarios_matriculados_en_curso(self, curso_id: str) -> list[dict]:
        """Obtiene los usuarios matriculados en un curso concreto."""
        ...


# ==========================================
# Protocols separados (nueva arquitectura)
# ==========================================
@runtime_checkable
class MoodleSource(Protocol):
    """Fuente de datos de Moodle (solo lectura).

    Abstrae CÓMO se extraen los datos de Moodle (API REST, moosh,
    plugin PHP snapshot, SQL directo, etc.).
    """

    def extract_users(self) -> list[dict]:
        """Extrae todos los usuarios relevantes de Moodle."""
        ...

    def extract_courses(self) -> list[dict]:
        """Extrae todos los cursos visibles de Moodle."""
        ...

    def extract_enrolments(self) -> list[dict]:
        """Extrae todas las matrículas usuario-curso."""
        ...

    def extract_all(self) -> MoodleSnapshot:
        """Extrae snapshot completo en una sola operación.

        Implementaciones que no soporten bulk pueden componer
        este método llamando a extract_* individualmente.
        """
        ...


@runtime_checkable
class MoodleSink(Protocol):
    """Destino de cambios en Moodle (solo escritura).

    Abstrae CÓMO se aplican las modificaciones en Moodle (API REST,
    moosh, SQL directo, etc.).
    """

    def create_user(
        self,
        username: str,
        email: str,
        nombre: str,
        apellido: str,
        password: str | None = None,
        customfields: dict[str, str] | None = None,
    ) -> int:
        """Crea un usuario. Devuelve el ID.

        Args:
            customfields: Diccionario shortname -> valor con los campos
                personalizados de Moodle (p. ej. IdSIGAD).
        """
        ...

    def update_user(
        self,
        username: str,
        customfields: dict[str, str] | None = None,
        **campos,
    ) -> bool:
        """Actualiza campos arbitrarios de un usuario.

        Args:
            customfields: Diccionario shortname -> valor con campos
                personalizados de Moodle a actualizar.
        """
        ...

    def update_user_email(self, username: str, email: str) -> bool:
        """Actualiza el email de un usuario."""
        ...

    def update_user_username(self, old_username: str, new_username: str) -> bool:
        """Cambia el username (ej: NIE → DNI)."""
        ...

    def suspend_user(self, username: str) -> bool:
        """Suspende un usuario globalmente."""
        ...

    def reactivate_user(self, username: str) -> bool:
        """Reactiva un usuario suspendido."""
        ...

    def enrol_user_to_course(self, username: str, course_id: str) -> bool:
        """Matricula un usuario en un curso."""
        ...

    def suspend_enrolment(self, username: str, course_id: str) -> bool:
        """Suspende la matrícula de un usuario en un curso."""
        ...

    def reactivate_enrolment(self, username: str, course_id: str) -> bool:
        """Reactiva una matrícula suspendida."""
        ...

    def enrol_user_to_cohort(self, username: str, cohort_name: str) -> bool:
        """Matricula un usuario en una cohorte."""
        ...

    def remove_user_from_cohort(self, username: str, cohort_name: str) -> bool:
        """Elimina un usuario de una cohorte."""
        ...


# ==========================================
# Protocols de Email
# ==========================================
@runtime_checkable
class EmailRepository(Protocol):
    """Protocolo para envío de notificaciones.

    Abstrae el servicio de email para permitir mocks en tests.
    """

    def enviar_bienvenida_nuevo_usuario(
        self,
        alumno: Alumno,
        password: str,
        matriculas: list[str],
    ) -> bool:
        """Envía email de bienvenida a nuevo usuario."""
        ...

    def enviar_actualizacion_usuario(
        self,
        alumno: Alumno,
        username_anterior: str,
    ) -> bool:
        """Envía notificación de cambio de usuario."""
        ...

    def enviar_nuevas_matriculas(
        self,
        alumno: Alumno,
        nuevas_matriculas: list[str],
    ) -> bool:
        """Envía notificación de nuevas matrículas."""
        ...

    def enviar_informe(
        self,
        destinatarios: list[str],
        asunto: str,
        contenido: str,
        adjuntos: list[str] | None = None,
    ) -> bool:
        """Envía un informe a los administradores."""
        ...

    def limite_alcanzado(self) -> bool:
        """Indica si se alcanzó el límite de emails."""
        ...
