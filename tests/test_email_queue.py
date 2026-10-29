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
            settings = Settings(
                csv_dir=Path(tmpdir), environment="test", email_pausa_segundos=0
            )
            queue = EmailQueueRepository(settings)
            sender = MagicMock()
            sender.limite_alcanzado.return_value = False
            processor = EmailQueueProcessor(queue_repo=queue, email_repo=sender, settings=settings)
            stats = processor.process_all()
            assert stats == {"enviados": 0, "fallidos": 0, "saltados": 0}

    def test_process_sends_pending(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = Settings(
                csv_dir=Path(tmpdir), environment="test", email_pausa_segundos=0
            )
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
            processor = EmailQueueProcessor(queue_repo=queue, email_repo=sender, settings=settings)
            stats = processor.process_all()

            assert stats["enviados"] == 1
            assert stats["fallidos"] == 0
            sender._enviar.assert_called_once()

    def test_respects_limit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = Settings(
                csv_dir=Path(tmpdir), environment="test", email_pausa_segundos=0
            )
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
            processor = EmailQueueProcessor(queue_repo=queue, email_repo=sender, settings=settings)
            stats = processor.process_all()

            assert stats["enviados"] == 2
            assert stats["saltados"] == 3


class TestEmailJobReintentos:
    """Valida la lógica de reintentos antes de marcar como fallido."""

    def test_registrar_intento_queda_pendiente(self):
        job = EmailJob(template_name="t", recipient="r", subject="s")
        agotado = job.registrar_intento("SMTP error", max_intentos=3)
        assert agotado is False
        assert job.status == "pending"
        assert job.intentos == 1
        assert job.error == "SMTP error"

    def test_registrar_intento_agotado(self):
        job = EmailJob(template_name="t", recipient="r", subject="s")
        job.registrar_intento("error 1", max_intentos=2)
        agotado = job.registrar_intento("error 2", max_intentos=2)
        assert agotado is True
        assert job.status == "failed"
        assert job.intentos == 2

    def test_csv_roundtrip_con_intentos_y_tipo(self):
        job = EmailJob(
            template_name="t",
            recipient="r",
            subject="s",
            intentos=2,
            tipo="informe",
        )
        restored = EmailJob.from_csv_row(job.to_csv_row())
        assert restored.intentos == 2
        assert restored.tipo == "informe"

    def test_csv_antiguo_sin_nuevas_columnas(self):
        fila = {
            "id": "uuid-1",
            "template_name": "t",
            "recipient": "r",
            "subject": "s",
            "template_data": "{}",
            "status": "pending",
            "created_at": "2026-01-01T00:00:00+00:00",
            "sent_at": "",
            "error": "",
        }
        job = EmailJob.from_csv_row(fila)
        assert job.intentos == 0
        assert job.tipo == "aviso"


class TestPrioridadInformes:
    """Los informes se procesan antes que los avisos."""

    @pytest.fixture
    def repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = Settings(csv_dir=Path(tmpdir), environment="test")
            yield EmailQueueRepository(settings)

    def test_informes_antes_que_avisos(self, repo, alumno_sample):
        repo.enviar_bienvenida_nuevo_usuario(alumno_sample, "pass", ["PROG"])
        repo.enviar_informe(
            destinatarios=["admin@ejemplo.com"],
            asunto="Informe",
            contenido="<h1>Resumen</h1>",
        )
        repo.enviar_nuevas_matriculas(alumno_sample, ["BD"])

        pendientes = repo.obtener_pendientes()
        assert pendientes[0].tipo == "informe"
        assert pendientes[0].subject == "Informe"
        assert [p.tipo for p in pendientes].count("informe") == 1

    def test_solo_informes(self, repo, alumno_sample):
        repo.enviar_bienvenida_nuevo_usuario(alumno_sample, "pass", ["PROG"])
        repo.enviar_informe(
            destinatarios=["admin@ejemplo.com"],
            asunto="Informe",
            contenido="<h1>Resumen</h1>",
        )
        solo = repo.obtener_pendientes(solo_informes=True)
        assert len(solo) == 1
        assert solo[0].tipo == "informe"


class TestProcesamientoSeguro:
    """Valida el escape HTML en el render y los reintentos del procesador."""

    @pytest.fixture
    def entorno(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = Settings(
                csv_dir=Path(tmpdir),
                environment="test",
                email_pausa_segundos=0,
                email_max_intentos=2,
            )
            queue = EmailQueueRepository(settings)
            sender = MagicMock()
            sender.limite_alcanzado.return_value = False
            processor = EmailQueueProcessor(queue_repo=queue, email_repo=sender, settings=settings)
            yield queue, sender, processor

    def test_render_escapa_html_de_sigad(self, entorno):
        queue, sender, processor = entorno
        alumno = Alumno(
            idAlumno=1,
            idTipoDocumento=1,
            documento="12345678A",
            nombre="Juan <script>alert(1)</script>",
            apellido1="Pérez",
            email="juan@ejemplo.com",
            centros=[],
        )
        queue.enviar_bienvenida_nuevo_usuario(alumno, "pass", ["PROG"])
        processor.process_all()

        _, kwargs = sender._enviar.call_args
        html_enviado = kwargs["contenido_html"]
        assert "<script>alert(1)</script>" not in html_enviado
        assert "&lt;script&gt;" in html_enviado

    def test_dry_run_no_envia_ni_cambia_estado(self, entorno):
        queue, sender, processor = entorno
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
        stats = processor.process_all(dry_run=True)

        assert stats["enviados"] == 1
        sender._enviar.assert_not_called()
        assert len(queue.obtener_pendientes()) == 1

    def test_reintento_antes_de_marcar_fallido(self, entorno):
        queue, sender, processor = entorno
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
        sender._enviar.side_effect = Exception("SMTP caído")

        # Primer proceso: falla pero queda pendiente (1 < 2 intentos)
        stats = processor.process_all()
        assert stats["fallidos"] == 0
        pendientes = queue.obtener_pendientes()
        assert len(pendientes) == 1
        assert pendientes[0].intentos == 1

        # Segundo proceso: se agotan los intentos → failed
        stats = processor.process_all()
        assert stats["fallidos"] == 1
        assert len(queue.obtener_pendientes()) == 0
        assert queue.obtener_estadisticas()["fallidos"] == 1
