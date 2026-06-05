"""Orquestador de la sincronización completa SIGAD ↔ Moodle.

Coordina las cuatro capas:
  1. Extracción SIGAD (EstudianteRepository)
  2. Extracción Moodle (MoodleSource)
  3. Análisis (SyncAnalyzer)
  4. Aplicación (SyncApplier / MoodleSink)
"""

from __future__ import annotations

from gestion_alumnos.core.config import Settings
from gestion_alumnos.core.logging import ReportLogger, get_logger
from gestion_alumnos.models import MoodleSnapshot, SyncReport
from gestion_alumnos.repositories.protocols import (
    EstudianteRepository,
    MoodleSink,
    MoodleSource,
)
from gestion_alumnos.services.sync_analyzer import SyncAnalyzer, cargar_usuarios_protegidos
from gestion_alumnos.services.sync_applier import SyncApplier

logger = get_logger(__name__)


class SyncOrchestrator:
    """Coordina el flujo completo de sincronización."""

    def __init__(
        self,
        sigad_repo: EstudianteRepository,
        moodle_source: MoodleSource,
        moodle_sink: MoodleSink,
        settings: Settings | None = None,
        dry_run: bool = True,
        report_logger: ReportLogger | None = None,
    ) -> None:
        self._sigad_repo = sigad_repo
        self._moodle_source = moodle_source
        self._moodle_sink = moodle_sink
        self._settings = settings or Settings()
        self._dry_run = dry_run
        self._report_logger = report_logger

    def run(self) -> SyncReport:
        """Ejecuta el flujo completo.

        Returns:
            SyncReport con todos los deltas detectados.
        """
        logger.info("Iniciando sincronización", dry_run=self._dry_run)

        # 1. Extraer datos de SIGAD
        logger.info("Extrayendo datos de SIGAD...")
        registro = self._sigad_repo.obtener_registro()
        logger.info(f"SIGAD: {registro.total_alumnos} alumnos")

        # 2. Extraer datos de Moodle
        logger.info("Extrayendo datos de Moodle...")
        snapshot = self._moodle_source.extract_all()
        logger.info(
            f"Moodle: {snapshot.total_users} usuarios, "
            f"{snapshot.total_enrolments} matriculaciones"
        )

        # 3. Analizar diferencias
        logger.info("Analizando diferencias...")
        protegidos = cargar_usuarios_protegidos(self._settings.usuarios_protegidos_csv)
        analyzer = SyncAnalyzer(registro, snapshot, usuarios_protegidos=protegidos)
        report = analyzer.analyze()
        logger.info(report.to_markdown())

        # 4. Aplicar cambios (solo si no es dry-run)
        if not self._dry_run and report.has_changes:
            logger.info("Aplicando cambios en Moodle...")
            course_mapping = {
                c.shortname: str(c.id)
                for c in snapshot.courses
            }
            applier = SyncApplier(report, self._moodle_sink, course_mapping)
            stats = applier.apply()
            logger.info(f"Estadísticas de aplicación: {stats}")
        elif self._dry_run:
            logger.info("Modo dry-run: no se aplicaron cambios")

        # 5. Escribir informe markdown
        if self._report_logger is not None:
            self._report_logger.write(report.to_markdown())
            logger.info(
                "Informe escrito",
                archivo=str(self._report_logger.filename),
            )

        return report
