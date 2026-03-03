"""
Container de Dependencias (Dependency Injection).

Proporciona una forma centralizada de crear y configurar
las dependencias del sistema siguiendo el patrón DI.
"""

from functools import lru_cache
from typing import TYPE_CHECKING

from gestion_alumnos.core.config import Settings, get_settings
from gestion_alumnos.core.logging import get_logger

if TYPE_CHECKING:
    from gestion_alumnos.repositories.protocols import (
        EstudianteRepository,
        MoodleRepository,
        EmailRepository,
    )

logger = get_logger(__name__)


class DIContainer:
    """
    Contenedor de inyección de dependencias.
    
    Centraliza la creación de instancias y permite
    configurar mocks para testing.
    
    Example:
        >>> container = DIContainer()
        >>> service = container.gestion_service()
        >>> resultado = service.ejecutar_sincronizacion_completa()
    """
    
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._estudiante_repo: "EstudianteRepository | None" = None
        self._moodle_repo: "MoodleRepository | None" = None
        self._email_repo: "EmailRepository | None" = None
    
    @property
    def settings(self) -> Settings:
        """Configuración del sistema."""
        return self._settings
    
    def estudiante_repository(self) -> "EstudianteRepository":
        """Obtiene el repositorio de estudiantes (lazy loading)."""
        if self._estudiante_repo is None:
            from gestion_alumnos.repositories.sigad_repository import SIGADRepository
            self._estudiante_repo = SIGADRepository(self._settings)
        return self._estudiante_repo
    
    def moodle_repository(self) -> "MoodleRepository":
        """Obtiene el repositorio de Moodle (lazy loading)."""
        if self._moodle_repo is None:
            from gestion_alumnos.repositories.moodle_db_repository import MoodleDBRepository
            self._moodle_repo = MoodleDBRepository(self._settings)
        return self._moodle_repo
    
    def email_repository(self) -> "EmailRepository | None":
        """Obtiene el repositorio de emails (lazy loading)."""
        if self._email_repo is None:
            # Solo crear si hay configuración SMTP
            if self._settings.smtp_host and self._settings.smtp_user:
                from gestion_alumnos.repositories.email_repository import EmailRepositoryImpl
                self._email_repo = EmailRepositoryImpl(self._settings)
            else:
                logger.warning("Email no configurado, las notificaciones estarán deshabilitadas")
        return self._email_repo
    
    def gestion_service(self):
        """Obtiene el servicio de gestión configurado."""
        from gestion_alumnos.services.gestion_service import GestionAlumnosService
        
        return GestionAlumnosService(
            estudiante_repo=self.estudiante_repository(),
            moodle_repo=self.moodle_repository(),
            email_repo=self.email_repository(),
            settings=self._settings
        )
    
    # ==========================================
    # Métodos para testing (inyectar mocks)
    # ==========================================
    
    def override_estudiante_repository(
        self,
        repo: "EstudianteRepository"
    ) -> "DIContainer":
        """Reemplaza el repositorio de estudiantes (útil para tests)."""
        self._estudiante_repo = repo
        return self
    
    def override_moodle_repository(
        self,
        repo: "MoodleRepository"
    ) -> "DIContainer":
        """Reemplaza el repositorio de Moodle (útil para tests)."""
        self._moodle_repo = repo
        return self
    
    def override_email_repository(
        self,
        repo: "EmailRepository | None"
    ) -> "DIContainer":
        """Reemplaza el repositorio de emails (útil para tests)."""
        self._email_repo = repo
        return self


@lru_cache
def get_container() -> DIContainer:
    """Retorna una instancia cacheada del container."""
    return DIContainer()


def create_container(settings: Settings | None = None) -> DIContainer:
    """
    Crea un nuevo container (no cacheado).
    
    Útil para testing cuando se necesita un container
    con configuración específica.
    """
    return DIContainer(settings)
