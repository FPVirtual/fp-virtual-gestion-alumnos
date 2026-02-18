"""
Tests para el servicio de email.

Estos tests verifican el funcionamiento de EmailService
sin enviar emails reales (usando mocks).
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from gestion_alumnos.utils.email_service import EmailService, crear_email_service_desde_env
from gestion_alumnos.models import Alumno, Centro, Ciclo, Modulo


@pytest.fixture
def email_service(tmp_path):
    """Fixture que crea un EmailService de prueba."""
    # Crear templates de prueba
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    
    # Crear template de prueba
    (templates_dir / "nuevoUsuario.html").write_text(
        "<p>Bienvenido {nombre} {apellidos}</p>"
    )
    (templates_dir / "nombreUsuarioActualizado.html").write_text(
        "<p>Usuario cambiado de {oldUsuario} a {usuario}</p>"
    )
    (templates_dir / "matriculasAnadidas.html").write_text(
        "<p>Nuevas matrículas: {matriculado_en_texto}</p>"
    )
    (templates_dir / "informeAutomatizado.html").write_text(
        "<p>Informe: {filename_md}</p>"
    )
    (templates_dir / "haFalladoElInforme.html").write_text(
        "<p>Error: {error}</p>"
    )
    
    return EmailService(
        smtp_host="smtp.test.com",
        smtp_port=587,
        smtp_user="test@test.com",
        smtp_password="password",
        subdomain="test",
        templates_path=str(templates_dir),
        report_to="admin1@test.com admin2@test.com"
    )


@pytest.fixture
def alumno_ejemplo():
    """Fixture que crea un alumno de ejemplo."""
    return Alumno(
        idAlumno=12345,
        idTipoDocumento=1,
        documento="12345678A",
        nombre="María",
        apellido1="García",
        apellido2="López",
        email="maria@test.com",
        centros=[]
    )


class TestEmailService:
    """Tests para la clase EmailService."""
    
    def test_inicializacion(self, email_service):
        """Test de inicialización correcta."""
        assert email_service.smtp_host == "smtp.test.com"
        assert email_service.smtp_port == 587
        assert email_service.subdomain == "test"
        assert email_service.max_emails_diarios == 10  # Límite para entorno no prod
        assert email_service.emails_enviados == 0
    
    def test_inicializacion_produccion(self, tmp_path):
        """Test de inicialización en producción."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        
        service = EmailService(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="user@gmail.com",
            smtp_password="pass",
            subdomain="www",
            templates_path=str(templates_dir),
            report_to="admin@test.com"
        )
        
        assert service.subdomain == "www"
        assert service.max_emails_diarios == 1000  # Límite producción
    
    def test_cargar_template_existente(self, email_service):
        """Test de carga de template existente."""
        template = email_service._cargar_template("nuevoUsuario.html")
        assert "Bienvenido" in template
    
    def test_cargar_template_no_existente(self, email_service):
        """Test de error al cargar template inexistente."""
        with pytest.raises(FileNotFoundError):
            email_service._cargar_template("noExiste.html")
    
    def test_verificar_limite_emails(self, email_service):
        """Test de verificación de límites."""
        assert email_service._verificar_limite_emails() is True
        
        # Simular que se alcanzó el límite
        email_service.emails_enviados = 10
        assert email_service._verificar_limite_emails() is False
    
    def test_get_destinatario_seguro_produccion(self, tmp_path):
        """Test de destinatario en producción."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        
        service = EmailService(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="user@gmail.com",
            smtp_password="pass",
            subdomain="www",
            templates_path=str(templates_dir),
            report_to="admin@test.com"
        )
        
        # En producción debe devolver el email real
        assert service._get_destinatario_seguro("real@email.com") == "real@email.com"
    
    def test_get_destinatario_seguro_no_produccion(self, email_service):
        """Test de destinatario en entorno no productivo."""
        # En entorno de test debe redirigir
        assert email_service._get_destinatario_seguro("real@email.com") == "gestion@fpvirtualaragon.es"
    
    @patch('gestion_alumnos.utils.email_service.smtplib.SMTP')
    def test_enviar_email_simple(self, mock_smtp, email_service):
        """Test de envío de email simple."""
        # Configurar mock
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = Mock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = Mock(return_value=False)
        
        resultado = email_service._enviar_email_simple(
            destinatario="test@test.com",
            asunto="Test",
            html_content="<p>Test</p>"
        )
        
        assert resultado is True
        assert email_service.emails_enviados == 1
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
    
    @patch('gestion_alumnos.utils.email_service.smtplib.SMTP')
    def test_enviar_email_con_adjuntos(self, mock_smtp, email_service, tmp_path):
        """Test de envío de email con adjuntos."""
        # Crear archivos de prueba
        archivo_md = tmp_path / "test.md"
        archivo_csv = tmp_path / "test.csv"
        archivo_md.write_text("# Test")
        archivo_csv.write_text("col1,col2")
        
        # Configurar mock
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = Mock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = Mock(return_value=False)
        
        resultado = email_service._enviar_email_con_adjuntos(
            destinatario="test@test.com",
            asunto="Test",
            html_content="<p>Test</p>",
            adjuntos=[str(archivo_md), str(archivo_csv)]
        )
        
        assert resultado is True
        assert email_service.emails_enviados == 1
    
    @patch('gestion_alumnos.utils.email_service.smtplib.SMTP')
    def test_enviar_email_nuevo_usuario(self, mock_smtp, email_service, alumno_ejemplo):
        """Test de envío de email a nuevo usuario."""
        # Configurar mock
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = Mock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = Mock(return_value=False)
        
        resultado = email_service.enviar_email_nuevo_usuario(
            alumno=alumno_ejemplo,
            password="Pass1234",
            matriculado_en_texto="<b>Ciclo</b> - Modulo"
        )
        
        assert resultado is True
        assert email_service.emails_enviados == 1
    
    @patch('gestion_alumnos.utils.email_service.smtplib.SMTP')
    def test_enviar_email_usuario_actualizado(self, mock_smtp, email_service, alumno_ejemplo):
        """Test de envío de email de usuario actualizado."""
        # Configurar mock
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = Mock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = Mock(return_value=False)
        
        resultado = email_service.enviar_email_usuario_actualizado(
            alumno=alumno_ejemplo,
            old_usuario="X1234567L",
            nuevo_usuario="12345678A"
        )
        
        assert resultado is True
        assert email_service.emails_enviados == 1
    
    @patch('gestion_alumnos.utils.email_service.smtplib.SMTP')
    def test_enviar_email_matriculas_añadidas(self, mock_smtp, email_service, alumno_ejemplo):
        """Test de envío de email de matrículas añadidas."""
        # Configurar mock
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = Mock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = Mock(return_value=False)
        
        resultado = email_service.enviar_email_matriculas_añadidas(
            alumno=alumno_ejemplo,
            matriculado_en_texto="<b>Ciclo</b> - Modulo"
        )
        
        assert resultado is True
        assert email_service.emails_enviados == 1
    
    @patch('gestion_alumnos.utils.email_service.smtplib.SMTP')
    def test_enviar_informe_ejecucion(self, mock_smtp, email_service, tmp_path):
        """Test de envío de informe a administradores."""
        # Crear archivos de prueba
        archivo_md = tmp_path / "test.md"
        archivo_csv = tmp_path / "test.csv"
        archivo_md.write_text("# Informe")
        archivo_csv.write_text("datos")
        
        # Configurar mock
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = Mock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = Mock(return_value=False)
        
        resultado = email_service.enviar_informe_ejecucion(
            filename_md=str(archivo_md),
            filename_csv=str(archivo_csv)
        )
        
        # Debe enviar a 2 destinatarios (definidos en report_to)
        assert resultado is True
        assert email_service.emails_enviados == 2
    
    def test_limite_alcanzado(self, email_service):
        """Test de detección de límite alcanzado."""
        assert email_service.limite_alcanzado() is False
        
        email_service.emails_enviados = 10
        assert email_service.limite_alcanzado() is True
    
    def test_obtener_estadisticas(self, email_service):
        """Test de obtención de estadísticas."""
        email_service.emails_enviados = 5
        email_service.emails_no_enviados = 2
        
        stats = email_service.obtener_estadisticas()
        
        assert stats["emails_enviados"] == 5
        assert stats["emails_no_enviados"] == 2
        assert stats["limite_diario"] == 10
        assert stats["disponibles"] == 5


class TestCrearEmailServiceDesdeEnv:
    """Tests para la función de fábrica desde variables de entorno."""
    
    def test_crear_email_service_desde_env_exito(self, tmp_path, monkeypatch):
        """Test de creación exitosa desde variables de entorno."""
        # Configurar variables de entorno
        monkeypatch.setenv("SMTP_HOSTS", "smtp.test.com")
        monkeypatch.setenv("SMTP_PORT", "587")
        monkeypatch.setenv("SMTP_USER", "user@test.com")
        monkeypatch.setenv("SMTP_PASSWORD", "pass")
        monkeypatch.setenv("SUBDOMAIN", "preproduccion")
        monkeypatch.setenv("PATH", str(tmp_path))
        monkeypatch.setenv("REPORT_TO", "admin@test.com")
        
        # Crear directorio de templates
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        
        service = crear_email_service_desde_env()
        
        assert isinstance(service, EmailService)
        assert service.smtp_port == 587
        assert service.smtp_host == "smtp.test.com"
        assert service.subdomain == "preproduccion"
    
    def test_crear_email_service_desde_env_faltan_variables(self, monkeypatch):
        """Test de error cuando faltan variables de entorno."""
        # Limpiar variables de entorno SMTP
        monkeypatch.delenv("SMTP_HOSTS", raising=False)
        monkeypatch.delenv("SMTP_PORT", raising=False)
        monkeypatch.delenv("SMTP_USER", raising=False)
        monkeypatch.delenv("SMTP_PASSWORD", raising=False)
        
        with pytest.raises(ValueError, match="Faltan variables de entorno"):
            crear_email_service_desde_env()
