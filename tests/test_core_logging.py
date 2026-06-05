"""Tests para el sistema de logging e informes."""

import tempfile
from pathlib import Path

import pytest

from gestion_alumnos.core.logging import ReportLogger


class TestReportLogger:
    """Valida la generación de informes markdown con timestamp."""

    def test_creates_markdown_file(self):
        """Debe crear un archivo .md con el patrón informe_env_timestamp."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ReportLogger(logs_dir=Path(tmpdir), environment="test")
            logger.write("## Test content")
            logger.close()

            assert logger.filename is not None
            assert logger.filename.suffix == ".md"
            assert "informe_test_" in logger.filename.name
            assert logger.filename.exists()

    def test_file_contains_header(self):
        """El archivo debe incluir encabezado con entorno y fecha."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ReportLogger(logs_dir=Path(tmpdir), environment="preproduccion")
            logger.write("## Test")
            logger.close()

            content = logger.filename.read_text(encoding="utf-8")
            assert "# Informe de Sincronización" in content
            assert "**Entorno:** preproduccion" in content
            assert "**Fecha:**" in content
            assert "---" in content

    def test_appends_content(self):
        """Múltiples write() deben acumular contenido."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ReportLogger(logs_dir=Path(tmpdir), environment="test")
            logger.write("## Primera sección")
            logger.write("## Segunda sección")
            logger.close()

            content = logger.filename.read_text(encoding="utf-8")
            assert "## Primera sección" in content
            assert "## Segunda sección" in content

    def test_creates_logs_dir_if_missing(self):
        """Debe crear el directorio de logs si no existe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = Path(tmpdir) / "sub" / "logs"
            assert not nested.exists()

            logger = ReportLogger(logs_dir=nested, environment="test")
            logger.write("## Test")
            logger.close()

            assert nested.exists()

    def test_close_idempotent(self):
        """Cerrar múltiples veces no debe fallar."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ReportLogger(logs_dir=Path(tmpdir), environment="test")
            logger.write("## Test")
            logger.close()
            logger.close()  # No debe lanzar excepción

    def test_write_without_content(self):
        """Escribir string vacío no debe romper."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ReportLogger(logs_dir=Path(tmpdir), environment="test")
            logger.write("")
            logger.close()

            content = logger.filename.read_text(encoding="utf-8")
            assert "# Informe de Sincronización" in content
