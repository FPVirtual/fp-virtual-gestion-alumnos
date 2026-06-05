"""Container de Dependencias (Dependency Injection).

Proporciona una forma centralizada de crear y configurar
las dependencias del sistema siguiendo el patrón DI.
"""

from functools import lru_cache
from typing import TYPE_CHECKING

from gestion_alumnos.core.config import Settings, get_settings
from gestion_alumnos.core.logging import ReportLogger, get_logger

if TYPE_CHECKING:
    from gestion_alumnos.repositories.protocols import (
        EmailRepository,
        EstudianteRepository,
        MoodleRepository,
        MoodleSink,
        MoodleSource,
    )

logger = get_logger(__name__)


class DIContainer:
    """Contenedor de inyección de dependencias.

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
        self._moodle_source: "MoodleSource | None" = None
        self._moodle_sink: "MoodleSink | None" = None
        self._report_logger: ReportLogger | None = None

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
        """Obtiene el repositorio de Moodle según el driver configurado."""
        if self._moodle_repo is None:
            if self._settings.moodle_driver == "api":
                from gestion_alumnos.repositories.moodle_api_repository import APIMoodleRepository
                self._moodle_repo = APIMoodleRepository(self._settings)
            else:
                from gestion_alumnos.repositories.moodle_moosh_repository import MooshMoodleRepository
                self._moodle_repo = MooshMoodleRepository(self._settings)
        return self._moodle_repo

    def email_repository(self) -> "EmailRepository | None":
        """Obtiene el repositorio de emails (lazy loading)."""
        if self._email_repo is None:
            if self._settings.smtp_host and self._settings.smtp_user:
                from gestion_alumnos.repositories.email_repository import EmailRepositoryImpl
                self._email_repo = EmailRepositoryImpl(self._settings)
            else:
                logger.warning(
                    "Email no configurado, las notificaciones estarán deshabilitadas"
                )
        return self._email_repo

    def gestion_service(self):
        """Obtiene el servicio de gestión configurado."""
        from gestion_alumnos.services.gestion_service import GestionAlumnosService

        return GestionAlumnosService(
            estudiante_repo=self.estudiante_repository(),
            moodle_repo=self.moodle_repository(),
            email_repo=self.email_repository(),
            settings=self._settings,
        )

    def moodle_source(self) -> "MoodleSource":
        """Obtiene la fuente de datos de Moodle según configuración."""
        if self._moodle_source is None:
            strategy = getattr(self._settings, "moodle_source_strategy", "api-course-based")
            if strategy == "api-snapshot":
                from gestion_alumnos.repositories.moodle_sources import APISnapshotMoodleSource
                self._moodle_source = APISnapshotMoodleSource(settings=self._settings)
            else:
                from gestion_alumnos.repositories.moodle_sources import APICourseBasedMoodleSource
                self._moodle_source = APICourseBasedMoodleSource(settings=self._settings)
        return self._moodle_source

    def moodle_sink(self) -> "MoodleSink":
        """Obtiene el sink de Moodle (mismo driver que el repo legacy)."""
        if self._moodle_sink is None:
            # El sink reutiliza la implementación del repositorio unificado
            self._moodle_sink = self.moodle_repository()
        return self._moodle_sink

    def report_logger(self) -> ReportLogger:
        """Obtiene el logger de informes markdown."""
        if self._report_logger is None:
            self._report_logger = ReportLogger(
                logs_dir=self._settings.logs_dir,
                environment=self._settings.environment,
            )
        return self._report_logger

    def sync_orchestrator(self, dry_run: bool = True):
        """Obtiene el orquestador de sincronización completa."""
        from gestion_alumnos.services.sync_orchestrator import SyncOrchestrator

        return SyncOrchestrator(
            sigad_repo=self.estudiante_repository(),
            moodle_source=self.moodle_source(),
            moodle_sink=self.moodle_sink(),
            settings=self._settings,
            dry_run=dry_run,
            report_logger=self.report_logger(),
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

    def override_moodle_source(
        self,
        source: "MoodleSource"
    ) -> "DIContainer":
        """Reemplaza la fuente de Moodle (útil para tests)."""
        self._moodle_source = source
        return self

    def override_moodle_sink(
        self,
        sink: "MoodleSink"
    ) -> "DIContainer":
        """Reemplaza el sink de Moodle (útil para tests)."""
        self._moodle_sink = sink
        return self

    def override_report_logger(
        self,
        report_logger: ReportLogger | None
    ) -> "DIContainer":
        """Reemplaza el logger de informes (útil para tests)."""
        self._report_logger = report_logger
        return self


@lru_cache
def get_container() -> DIContainer:
    """Retorna una instancia cacheada del container."""
    return DIContainer()


def create_container(settings: Settings | None = None) -> DIContainer:
    """Crea un nuevo container (no cacheado).

    Útil para testing cuando se necesita un container
    con configuración específica.
    """
    return DIContainer(settings)
