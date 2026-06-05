"""Repositorio de cola de emails.

Implementa el protocolo EmailRepository pero en lugar de enviar
emails directamente, los encola en un archivo CSV para procesamiento
externo. Esto evita bloqueos por límites de envío y permite
recuperación ante fallos.
"""

import csv
from pathlib import Path
from typing import Literal

from gestion_alumnos.core.config import Settings
from gestion_alumnos.core.logging import get_logger
from gestion_alumnos.models import Alumno
from gestion_alumnos.models.email_queue import EmailJob

logger = get_logger(__name__)


class EmailQueueRepository:
    """Encola emails en un archivo CSV en lugar de enviarlos directamente.

    Implementa el mismo protocolo que EmailRepositoryImpl para que
    pueda inyectarse de forma transparente en GestionAlumnosService
    y SyncApplier.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        self._csv_path = self._settings.csv_dir / "email_queue.csv"
        self._limite = 1000 if self._settings.subdomain == "www" else 10

    def _ensure_csv_dir(self) -> None:
        self._csv_path.parent.mkdir(parents=True, exist_ok=True)

    def _append_job(self, job: EmailJob) -> None:
        """Añade un trabajo al final del CSV."""
        self._ensure_csv_dir()
        file_exists = self._csv_path.exists()
        with open(self._csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=EmailJob.csv_header())
            if not file_exists:
                writer.writeheader()
            writer.writerow(job.to_csv_row())
        logger.info(
            "Email encolado",
            id=job.id,
            template=job.template_name,
            recipient=job.recipient,
        )

    def _count_pending(self) -> int:
        """Cuenta emails pendientes en la cola."""
        if not self._csv_path.exists():
            return 0
        count = 0
        with open(self._csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("status") == "pending":
                    count += 1
        return count

    # ------------------------------------------------------------------
    # Implementación del protocolo EmailRepository
    # ------------------------------------------------------------------

    def enviar_bienvenida_nuevo_usuario(
        self,
        alumno: Alumno,
        password: str,
        matriculas: list[str],
    ) -> bool:
        """Encola email de bienvenida."""
        matriculado_en_texto = "<br/>".join(matriculas)
        job = EmailJob(
            template_name="nuevoUsuario.html",
            recipient=alumno.email or "",
            subject="FP virtual - Aragón - Datos de acceso",
            template_data={
                "nombre": alumno.nombre or "",
                "apellidos": f"{alumno.apellido1 or ''} {alumno.apellido2 or ''}".strip(),
                "subdomain": self._settings.subdomain,
                "usuario": alumno.username_moodle,
                "contrasena": password,
                "matriculado_en_texto": matriculado_en_texto,
                "email": alumno.email or "",
            },
        )
        self._append_job(job)
        return True

    def enviar_actualizacion_usuario(
        self,
        alumno: Alumno,
        username_anterior: str,
    ) -> bool:
        """Encola notificación de cambio de usuario."""
        job = EmailJob(
            template_name="nombreUsuarioActualizado.html",
            recipient=alumno.email or "",
            subject="FP virtual - Aragón - Usuario actualizado",
            template_data={
                "subdomain": self._settings.subdomain,
                "usuario": alumno.username_moodle,
                "oldUsuario": username_anterior,
            },
        )
        self._append_job(job)
        return True

    def enviar_nuevas_matriculas(
        self,
        alumno: Alumno,
        nuevas_matriculas: list[str],
    ) -> bool:
        """Encola notificación de nuevas matrículas."""
        matriculado_en_texto = "<br/>".join(nuevas_matriculas)
        job = EmailJob(
            template_name="matriculasAnadidas.html",
            recipient=alumno.email or "",
            subject="FP virtual - Aragón - Nuevas matrículas",
            template_data={
                "nombre": alumno.nombre or "",
                "apellidos": f"{alumno.apellido1 or ''} {alumno.apellido2 or ''}".strip(),
                "subdomain": self._settings.subdomain,
                "matriculado_en_texto": matriculado_en_texto,
            },
        )
        self._append_job(job)
        return True

    def enviar_informe(
        self,
        destinatarios: list[str],
        asunto: str,
        contenido: str,
        adjuntos: list[str] | None = None,
    ) -> bool:
        """Encola informe a administradores."""
        for destinatario in destinatarios:
            job = EmailJob(
                template_name="_raw_html",
                recipient=destinatario,
                subject=asunto,
                template_data={
                    "contenido_html": contenido,
                    "adjuntos": adjuntos or [],
                },
            )
            self._append_job(job)
        return True

    def limite_alcanzado(self) -> bool:
        """Indica si se alcanzó el límite de emails pendientes."""
        return self._count_pending() >= self._limite

    # ------------------------------------------------------------------
    # Métodos adicionales para gestión de la cola
    # ------------------------------------------------------------------

    def obtener_pendientes(self) -> list[EmailJob]:
        """Devuelve todos los trabajos pendientes."""
        if not self._csv_path.exists():
            return []
        pendientes: list[EmailJob] = []
        with open(self._csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                job = EmailJob.from_csv_row(row)
                if job.status == "pending":
                    pendientes.append(job)
        return pendientes

    def actualizar_estado(
        self,
        job_id: str,
        status: Literal["pending", "sent", "failed"],
        error: str | None = None,
    ) -> None:
        """Actualiza el estado de un trabajo en el CSV.

        Reescribe el archivo completo. Dado que el CSV es pequeño
        (cientos de filas como mucho), esto es aceptable.
        """
        if not self._csv_path.exists():
            return

        jobs: list[EmailJob] = []
        with open(self._csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                job = EmailJob.from_csv_row(row)
                if job.id == job_id:
                    job.status = status
                    if status == "sent":
                        job.mark_sent()
                    elif status == "failed" and error:
                        job.mark_failed(error)
                jobs.append(job)

        with open(self._csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=EmailJob.csv_header())
            writer.writeheader()
            for job in jobs:
                writer.writerow(job.to_csv_row())

    def obtener_estadisticas(self) -> dict:
        """Retorna estadísticas de la cola."""
        if not self._csv_path.exists():
            return {
                "pendientes": 0,
                "enviados": 0,
                "fallidos": 0,
                "limite": self._limite,
                "disponibles": self._limite,
            }
        counts = {"pending": 0, "sent": 0, "failed": 0}
        with open(self._csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                status = row.get("status", "pending")
                counts[status] = counts.get(status, 0) + 1
        pendientes = counts["pending"]
        return {
            "pendientes": pendientes,
            "enviados": counts["sent"],
            "fallidos": counts["failed"],
            "limite": self._limite,
            "disponibles": max(0, self._limite - pendientes),
        }
