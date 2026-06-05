"""Procesador de la cola de emails.

Lee el archivo CSV de emails pendientes y los envía usando
EmailRepositoryImpl, respetando el límite diario.
"""

from pathlib import Path

from gestion_alumnos.core.config import Settings
from gestion_alumnos.core.logging import get_logger
from gestion_alumnos.repositories.email_queue_repository import EmailQueueRepository
from gestion_alumnos.repositories.email_repository import EmailRepositoryImpl
from gestion_alumnos.repositories.protocols import EmailRepository

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

    def process_all(self) -> dict:
        """Procesa todos los emails pendientes.

        Returns:
            Estadísticas del procesamiento: enviados, fallidos, saltados.
        """
        pendientes = self._queue.obtener_pendientes()
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
                self._process_single(job)
                stats["enviados"] += 1
            except Exception as e:
                logger.error(f"Error enviando email {job.id}: {e}")
                self._queue.actualizar_estado(job.id, "failed", str(e))
                stats["fallidos"] += 1

        logger.info(
            "Procesamiento completado",
            enviados=stats["enviados"],
            fallidos=stats["fallidos"],
            saltados=stats["saltados"],
        )
        return stats

    def _process_single(self, job) -> None:
        """Envía un email individual y actualiza su estado."""
        from importlib import resources

        if job.template_name == "_raw_html":
            # Email con contenido HTML crudo (informes)
            contenido = job.template_data.get("contenido_html", "")
            adjuntos = job.template_data.get("adjuntos", [])
            adjuntos_path = [Path(a) for a in adjuntos] if adjuntos else None
            self._sender._enviar(
                destinatario=job.recipient,
                asunto=job.subject,
                contenido_html=contenido,
                adjuntos=adjuntos_path,
            )
        else:
            # Email con template HTML
            template_path = resources.files("gestion_alumnos.templates") / job.template_name
            contenido = template_path.read_text(encoding="utf-8")
            contenido = contenido.format(**job.template_data)
            self._sender._enviar(
                destinatario=job.recipient,
                asunto=job.subject,
                contenido_html=contenido,
            )

        self._queue.actualizar_estado(job.id, "sent")
        logger.info("Email enviado", id=job.id, recipient=job.recipient)
