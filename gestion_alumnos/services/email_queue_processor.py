"""Procesador de la cola de emails.

Lee el archivo CSV de emails pendientes y los envía usando
EmailRepositoryImpl, respetando el límite diario.
"""

import time
from pathlib import Path

from gestion_alumnos.core.config import Settings
from gestion_alumnos.core.logging import get_logger
from gestion_alumnos.repositories.email_queue_repository import EmailQueueRepository
from gestion_alumnos.repositories.email_repository import EmailRepositoryImpl
from gestion_alumnos.repositories.protocols import EmailRepository
from gestion_alumnos.utils.plantillas import logo_disponible, renderizar_plantilla

logger = get_logger(__name__)


class EmailQueueProcessor:
    """Procesa la cola de emails pendientes.

    Lee el CSV generado por EmailQueueRepository y envía cada
    email usando EmailRepositoryImpl, actualizando el estado
    en el CSV tras cada envío.
    """

    def __init__(
        self,
        queue_repo: EmailQueueRepository | None = None,
        email_repo: EmailRepository | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or Settings()
        self._queue = queue_repo or EmailQueueRepository(self._settings)
        self._sender = email_repo or EmailRepositoryImpl(self._settings)

    def process_all(self, solo_informes: bool = False, dry_run: bool = False) -> dict:
        """Procesa todos los emails pendientes.

        Args:
            solo_informes: Procesa solo los informes (los avisos quedan pendientes).
            dry_run: Renderiza los emails pero no los envía ni cambia estados.

        Returns:
            Estadísticas del procesamiento: enviados, fallidos, saltados.
        """
        pendientes = self._queue.obtener_pendientes(solo_informes=solo_informes)
        if not pendientes:
            logger.info("No hay emails pendientes en la cola")
            return {"enviados": 0, "fallidos": 0, "saltados": 0}

        logger.info(f"Procesando {len(pendientes)} emails pendientes")

        stats = {"enviados": 0, "fallidos": 0, "saltados": 0}

        for job in pendientes:
            if self._sender.limite_alcanzado():
                logger.warning(
                    "Límite de emails alcanzado, saltando resto",
                    pendientes_restantes=len(pendientes) - stats["enviados"] - stats["fallidos"],
                )
                stats["saltados"] += len(pendientes) - stats["enviados"] - stats["fallidos"]
                break

            try:
                self._process_single(job, dry_run=dry_run)
                stats["enviados"] += 1
                if not dry_run and self._settings.email_pausa_segundos > 0:
                    time.sleep(self._settings.email_pausa_segundos)
            except Exception as e:
                logger.error(f"Error enviando email {job.id}: {e}")
                if dry_run:
                    stats["fallidos"] += 1
                    continue
                agotado = self._queue.registrar_fallo(
                    job.id, str(e), self._settings.email_max_intentos
                )
                if agotado:
                    stats["fallidos"] += 1

        logger.info(
            "Procesamiento completado",
            enviados=stats["enviados"],
            fallidos=stats["fallidos"],
            saltados=stats["saltados"],
        )
        return stats

    def _renderizar(self, job) -> tuple[str, list[Path] | None]:
        """Renderiza el contenido HTML de un trabajo de la cola."""
        if job.template_name == "_raw_html":
            # Email con contenido HTML crudo (informes)
            contenido = job.template_data.get("contenido_html", "")
            adjuntos = job.template_data.get("adjuntos", [])
            adjuntos_path = [Path(a) for a in adjuntos] if adjuntos else None
            return contenido, adjuntos_path

        datos = dict(job.template_data)
        matriculas = datos.pop("matriculas", None)
        if matriculas is not None:
            datos["matriculado_en"] = matriculas
        datos.setdefault("logo", logo_disponible())
        return renderizar_plantilla(job.template_name, **datos), None

    def _process_single(self, job, dry_run: bool = False) -> None:
        """Renderiza (y envía, salvo dry-run) un email individual."""
        contenido, adjuntos = self._renderizar(job)
        if dry_run:
            logger.info(
                "Dry-run: email renderizado sin enviar",
                id=job.id,
                recipient=job.recipient,
            )
            return
        self._sender._enviar(
            destinatario=job.recipient,
            asunto=job.subject,
            contenido_html=contenido,
            adjuntos=adjuntos,
        )
        self._queue.actualizar_estado(job.id, "sent")
        logger.info("Email enviado", id=job.id, recipient=job.recipient)
