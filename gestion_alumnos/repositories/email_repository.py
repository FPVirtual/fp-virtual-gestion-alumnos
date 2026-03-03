"""
Implementación del repositorio de emails.
"""

import ssl
import smtplib
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

from gestion_alumnos.core.config import Settings
from gestion_alumnos.core.exceptions import EmailError, EmailLimitExceeded
from gestion_alumnos.core.logging import get_logger
from gestion_alumnos.models_v2 import Alumno

logger = get_logger(__name__)


class EmailRepositoryImpl:
    """
    Implementación del servicio de email usando SMTP.
    
    Gestiona el envío de notificaciones con control de límites
diarios y redirección según el entorno.
    """
    
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        self._emails_enviados = 0
        self._emails_no_enviados = 0
        
        # Límite según entorno
        self._limite = 1000 if self._settings.subdomain == "www" else 10
    
    def _verificar_limite(self) -> None:
        """Verifica que no se haya alcanzado el límite."""
        if self._emails_enviados >= self._limite:
            raise EmailLimitExceeded(
                f"Límite de {self._limite} emails alcanzado",
            )
    
    def _get_destinatario(self, email_real: str) -> str:
        """Obtiene el destinatario según el entorno."""
        if self._settings.subdomain == "www":
            return email_real
        # En test/pre, redirigir a cuenta de gestión
        return "gestion@fpvirtualaragon.es"
    
    def _enviar(
        self,
        destinatario: str,
        asunto: str,
        contenido_html: str,
        adjuntos: list[Path] | None = None
    ) -> bool:
        """Envía un email."""
        try:
            self._verificar_limite()
            
            destinatario = self._get_destinatario(destinatario)
            
            if adjuntos:
                msg = MIMEMultipart("alternative")
                msg.attach(MIMEText(contenido_html, "html"))
                
                for filepath in adjuntos:
                    with open(filepath, "rb") as f:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={filepath.name}"
                    )
                    msg.attach(part)
            else:
                msg = EmailMessage()
                msg.set_content("Tu cliente no soporta HTML.", subtype="plain")
                msg.add_alternative(contenido_html, subtype="html")
            
            msg["Subject"] = asunto
            msg["From"] = self._settings.smtp_user
            msg["To"] = destinatario
            
            context = ssl.create_default_context()
            with smtplib.SMTP(self._settings.smtp_host, self._settings.smtp_port) as server:
                if self._settings.smtp_use_tls:
                    server.starttls(context=context)
                server.login(
                    self._settings.smtp_user,
                    self._settings.smtp_password
                )
                server.send_message(msg)
            
            self._emails_enviados += 1
            logger.info(f"Email enviado a: {destinatario}")
            return True
            
        except EmailLimitExceeded:
            raise
        except Exception as e:
            self._emails_no_enviados += 1
            logger.error(f"Error enviando email: {e}")
            raise EmailError(f"Error enviando email: {e}", destinatario=destinatario)
    
    def enviar_bienvenida_nuevo_usuario(
        self,
        alumno: Alumno,
        password: str,
        matriculas: list[str]
    ) -> bool:
        """Envía email de bienvenida."""
        asunto = "FP virtual - Aragón - Datos de acceso"
        
        # HTML simple (en producción usar template)
        matriculas_html = "<ul>" + "".join(
            f"<li>{m}</li>" for m in matriculas
        ) + "</ul>"
        
        contenido = f"""
        <h2>Bienvenido a FP Virtual Aragón</h2>
        <p>Hola {alumno.nombre},</p>
        <p>Tu cuenta ha sido creada con éxito.</p>
        <p><strong>Usuario:</strong> {alumno.username_moodle}</p>
        <p><strong>Contraseña:</strong> {password}</p>
        <p><strong>Matriculado en:</strong></p>
        {matriculas_html}
        <p>Accede en: https://{self._settings.subdomain}.fpvirtualaragon.es</p>
        """
        
        return self._enviar(alumno.email, asunto, contenido)
    
    def enviar_actualizacion_usuario(
        self,
        alumno: Alumno,
        username_anterior: str
    ) -> bool:
        """Envía notificación de cambio de usuario."""
        asunto = "FP virtual - Aragón - Usuario actualizado"
        
        contenido = f"""
        <h2>Actualización de cuenta</h2>
        <p>Tu usuario ha sido actualizado:</p>
        <p><strong>Anterior:</strong> {username_anterior}</p>
        <p><strong>Nuevo:</strong> {alumno.username_moodle}</p>
        """
        
        return self._enviar(alumno.email, asunto, contenido)
    
    def enviar_nuevas_matriculas(
        self,
        alumno: Alumno,
        nuevas_matriculas: list[str]
    ) -> bool:
        """Envía notificación de nuevas matrículas."""
        asunto = "FP virtual - Aragón - Nuevas matrículas"
        
        matriculas_html = "<ul>" + "".join(
            f"<li>{m}</li>" for m in nuevas_matriculas
        ) + "</ul>"
        
        contenido = f"""
        <h2>Nuevas matrículas</h2>
        <p>Hola {alumno.nombre},</p>
        <p>Has sido matriculado en nuevos módulos:</p>
        {matriculas_html}
        """
        
        return self._enviar(alumno.email, asunto, contenido)
    
    def enviar_informe(
        self,
        destinatarios: list[str],
        asunto: str,
        contenido: str,
        adjuntos: list[str] | None = None
    ) -> bool:
        """Envía un informe a administradores."""
        adjuntos_path = [Path(a) for a in adjuntos] if adjuntos else None
        
        resultados = []
        for destinatario in destinatarios:
            try:
                resultados.append(
                    self._enviar(destinatario, asunto, contenido, adjuntos_path)
                )
            except EmailError:
                resultados.append(False)
        
        return all(resultados)
    
    def limite_alcanzado(self) -> bool:
        """Indica si se alcanzó el límite de emails."""
        return self._emails_enviados >= self._limite
    
    def obtener_estadisticas(self) -> dict:
        """Retorna estadísticas de envío."""
        return {
            "enviados": self._emails_enviados,
            "fallidos": self._emails_no_enviados,
            "limite": self._limite,
            "disponibles": max(0, self._limite - self._emails_enviados),
        }
