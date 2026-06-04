"""Protocols (interfaces) para repositorios.

Define contratos que deben cumplir las implementaciones,
permitiendo inyección de dependencias y testing.
"""

from typing import Protocol, runtime_checkable

from gestion_alumnos.models import Alumno, Registro


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


@runtime_checkable
class MoodleRepository(Protocol):
    """Protocolo para operaciones sobre Moodle.

    Abstrae las operaciones de matriculación, creación de usuarios,
    etc. independientemente de si usamos moosh, WS o BD directa.
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
    ) -> int:
        """Crea un usuario en Moodle.

        Returns:
            ID del usuario creado.
        """
        ...

    def actualizar_usuario(self, username: str, **campos) -> bool:
        """Actualiza campos de un usuario."""
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
