"""Tests para el sistema de cola de emails.

Validan la encolación en CSV, el procesamiento y la
recuperación de estado.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from gestion_alumnos.core.config import Settings
from gestion_alumnos.models import Alumno
from gestion_alumnos.models.email_queue import EmailJob
from gestion_alumnos.repositories.email_queue_repository import EmailQueueRepository
from gestion_alumnos.services.email_queue_processor import EmailQueueProcessor


@pytest.fixture
def alumno_sample():
    return Alumno(
        idAlumno=1,
        idTipoDocumento=1,
        documento="12345678A",
        nombre="Juan",
        apellido1="Pérez",
        apellido2="García",
        email="juan@ejemplo.com",
        centros=[],
    )


class TestEmailJob:
    """Valida serialización y estado del modelo EmailJob."""

    def test_default_values(self):
        job = EmailJob(
            template_name="nuevoUsuario.html",
            recipient="test@ejemplo.com",
            subject="Test",
        )
        assert job.status == "pending"
        assert job.sent_at is None
        assert job.error is None
        assert len(job.id) == 36  # UUID

    def test_mark_sent(self):
        job = EmailJob(template_name="t", recipient="r", subject="s")
        job.mark_sent()
        assert job.status == "sent"
        assert job.sent_at is not None
        assert job.error is None

    def test_mark_failed(self):
        job = EmailJob(template_name="t", recipient="r", subject="s")
        job.mark_failed("SMTP timeout")
        assert job.status == "failed"
        assert job.sent_at is not None
        assert job.error == "SMTP timeout"

    def test_csv_roundtrip(self):
        job = EmailJob(
            template_name="nuevoUsuario.html",
            recipient="test@ejemplo.com",
            subject="Bienvenida",
            template_data={"nombre": "Juan", "subdomain": "test"},
        )
        row = job.to_csv_row()
        restored = EmailJob.from_csv_row(row)
        assert restored.template_name == job.template_name
        assert restored.recipient == job.recipient
        assert restored.template_data == job.template_data

    def test_csv_roundtrip_with_special_chars(self):
        job = EmailJob(
            template_name="t.html",
            recipient="test@ejemplo.com",
            subject="Test",
            template_data={"texto": "Hola, \"mundo\" — con ñ y ü"},
        )
        row = job.to_csv_row()
        restored = EmailJob.from_csv_row(row)
        assert restored.template_data["texto"] == "Hola, \"mundo\" — con ñ y ü"


class TestEmailQueueRepository:
    """Valida encolación y gestión de la cola CSV."""

    @pytest.fixture
    def repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = Settings(csv_dir=Path(tmpdir), environment="test")
            yield EmailQueueRepository(settings)

    def test_encolar_bienvenida(self, repo, alumno_sample):
        repo.enviar_bienvenida_nuevo_usuario(alumno_sample, "secret123", ["PROG"])
        pendientes = repo.obtener_pendientes()
        assert len(pendientes) == 1
        assert pendientes[0].template_name == "nuevoUsuario.html"
        assert pendientes[0].recipient == "juan@ejemplo.com"
        assert pendientes[0].template_data["usuario"] == "12345678a"

    def test_encolar_actualizacion(self, repo, alumno_sample):
        repo.enviar_actualizacion_usuario(alumno_sample, "viejo_user")
        pendientes = repo.obtener_pendientes()
        assert len(pendientes) == 1
        assert pendientes[0].template_name == "nombreUsuarioActualizado.html"

    def test_encolar_matriculas(self, repo, alumno_sample):
        repo.enviar_nuevas_matriculas(alumno_sample, ["BD", "PROG"])
        pendientes = repo.obtener_pendientes()
        assert len(pendientes) == 1
        assert pendientes[0].template_name == "matriculasAnadidas.html"

    def test_actualizar_estado(self, repo, alumno_sample):
        repo.enviar_bienvenida_nuevo_usuario(alumno_sample, "pass", ["PROG"])
        job = repo.obtener_pendientes()[0]
        repo.actualizar_estado(job.id, "sent")
        assert len(repo.obtener_pendientes()) == 0

    def test_estadisticas(self, repo, alumno_sample):
        repo.enviar_bienvenida_nuevo_usuario(alumno_sample, "pass", ["PROG"])
        stats = repo.obtener_estadisticas()
        assert stats["pendientes"] == 1
        assert stats["enviados"] == 0
        assert stats["fallidos"] == 0
        assert stats["limite"] == 10

    def test_limite_alcanzado(self, repo, alumno_sample):
        for i in range(10):
            a = Alumno(
                idAlumno=i,
                idTipoDocumento=1,
                documento=f"DOC{i:02d}",
                nombre="Test",
                apellido1="Test",
                email=f"test{i}@ejemplo.com",
                centros=[],
            )
            repo.enviar_bienvenida_nuevo_usuario(a, "pass", ["PROG"])
        assert repo.limite_alcanzado() is True
        assert repo.enviar_bienvenida_nuevo_usuario(alumno_sample, "pass", ["PROG"]) is True  # sigue encolando

    def test_enviar_informe(self, repo):
        repo.enviar_informe(
            destinatarios=["admin1@ejemplo.com", "admin2@ejemplo.com"],
            asunto="Informe diario",
            contenido="<h1>Resumen</h1>",
        )
        pendientes = repo.obtener_pendientes()
        assert len(pendientes) == 2
        assert pendientes[0].subject == "Informe diario"


class TestEmailQueueProcessor:
    """Valida el procesamiento de la cola."""

    def test_process_empty_queue(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = Settings(csv_dir=Path(tmpdir), environment="test")
            queue = EmailQueueRepository(settings)
            sender = MagicMock()
            sender.limite_alcanzado.return_value = False
            processor = EmailQueueProcessor(queue_repo=queue, email_repo=sender)
            stats = processor.process_all()
            assert stats == {"enviados": 0, "fallidos": 0, "saltados": 0}

    def test_process_sends_pending(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = Settings(csv_dir=Path(tmpdir), environment="test")
            queue = EmailQueueRepository(settings)
            alumno = Alumno(
                idAlumno=1,
                idTipoDocumento=1,
                documento="12345678A",
                nombre="Juan",
                apellido1="Pérez",
                email="juan@ejemplo.com",
                centros=[],
            )
            queue.enviar_bienvenida_nuevo_usuario(alumno, "pass", ["PROG"])

            sender = MagicMock()
            sender.limite_alcanzado.return_value = False
            processor = EmailQueueProcessor(queue_repo=queue, email_repo=sender)
            stats = processor.process_all()

            assert stats["enviados"] == 1
            assert stats["fallidos"] == 0
            sender._enviar.assert_called_once()

    def test_respects_limit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = Settings(csv_dir=Path(tmpdir), environment="test")
            queue = EmailQueueRepository(settings)
            for i in range(5):
                a = Alumno(
                    idAlumno=i,
                    idTipoDocumento=1,
                    documento=f"DOC{i:02d}",
                    nombre="Test",
                    apellido1="Test",
                    email=f"test{i}@ejemplo.com",
                    centros=[],
                )
                queue.enviar_bienvenida_nuevo_usuario(a, "pass", ["PROG"])

            sender = MagicMock()
            # Solo permite 2 envíos
            sender.limite_alcanzado.side_effect = [False, False, True]
            processor = EmailQueueProcessor(queue_repo=queue, email_repo=sender)
            stats = processor.process_all()

            assert stats["enviados"] == 2
            assert stats["saltados"] == 3
