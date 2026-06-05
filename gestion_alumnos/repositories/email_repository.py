"""Implementación del repositorio de emails."""

import smtplib
import ssl
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from importlib import resources
from pathlib import Path

from gestion_alumnos.core.config import Settings
from gestion_alumnos.core.exceptions import EmailError, EmailLimitExceeded
from gestion_alumnos.core.logging import get_logger
from gestion_alumnos.models import Alumno

logger = get_logger(__name__)


class EmailRepositoryImpl:
    """Implementación del servicio de email usando SMTP.

    Gestiona el envío de notificaciones con control de límites
    diarios y redirección según el entorno.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        self._emails_enviados = 0
        self._emails_no_enviados = 0
        self._limite = 1000 if self._settings.subdomain == "www" else 10

    def _cargar_template(self, template_nombre: str, **kwargs: str) -> str:
        """Carga una template HTML del paquete y reemplaza placeholders."""
        template_path = resources.files("gestion_alumnos.templates") / template_nombre
        contenido = template_path.read_text(encoding="utf-8")
        return contenido.format(**kwargs)

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
        return "gestion@fpvirtualaragon.es"

    def _enviar(
        self,
        destinatario: str,
        asunto: str,
        contenido_html: str,
        adjuntos: list[Path] | None = None,
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
                        f"attachment; filename={filepath.name}",
                    )
                    msg.attach(part)
            else:
                msg = MIMEMultipart("alternative")
                msg.attach(MIMEText(contenido_html, "html"))
            msg["Subject"] = asunto
            msg["From"] = self._settings.smtp_user
            msg["To"] = destinatario
            context = ssl.create_default_context()
            with smtplib.SMTP(
                self._settings.smtp_host, self._settings.smtp_port
            ) as server:
                if self._settings.smtp_use_tls:
                    server.starttls(context=context)
                server.login(
                    self._settings.smtp_user,
                    self._settings.smtp_password,
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
            raise EmailError(
                f"Error enviando email: {e}", destinatario=destinatario
            )

    def enviar_bienvenida_nuevo_usuario(
        self,
        alumno: Alumno,
        password: str,
        matriculas: list[str],
    ) -> bool:
        """Envía email de bienvenida usando template HTML."""
        asunto = "FP virtual - Aragón - Datos de acceso"
        matriculado_en_texto = "<br/>".join(matriculas)
        contenido = self._cargar_template(
            "nuevoUsuario.html",
            nombre=alumno.nombre or "",
            apellidos=f"{alumno.apellido1 or ''} {alumno.apellido2 or ''}".strip(),
            subdomain=self._settings.subdomain,
            usuario=alumno.username_moodle,
            contrasena=password,
            matriculado_en_texto=matriculado_en_texto,
            email=alumno.email or "",
        )
        return self._enviar(alumno.email, asunto, contenido)

    def enviar_actualizacion_usuario(
        self,
        alumno: Alumno,
        username_anterior: str,
    ) -> bool:
        """Envía notificación de cambio de usuario usando template HTML."""
        asunto = "FP virtual - Aragón - Usuario actualizado"
        contenido = self._cargar_template(
            "nombreUsuarioActualizado.html",
            subdomain=self._settings.subdomain,
            usuario=alumno.username_moodle,
            oldUsuario=username_anterior,
        )
        return self._enviar(alumno.email, asunto, contenido)

    def enviar_nuevas_matriculas(
        self,
        alumno: Alumno,
        nuevas_matriculas: list[str],
    ) -> bool:
        """Envía notificación de nuevas matrículas usando template HTML."""
        asunto = "FP virtual - Aragón - Nuevas matrículas"
        matriculado_en_texto = "<br/>".join(nuevas_matriculas)
        contenido = self._cargar_template(
            "matriculasAnadidas.html",
            nombre=alumno.nombre or "",
            apellidos=f"{alumno.apellido1 or ''} {alumno.apellido2 or ''}".strip(),
            subdomain=self._settings.subdomain,
            matriculado_en_texto=matriculado_en_texto,
        )
        return self._enviar(alumno.email, asunto, contenido)

    def enviar_informe(
        self,
        destinatarios: list[str],
        asunto: str,
        contenido: str,
        adjuntos: list[str] | None = None,
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

    def enviar_informe_automatizado(
        self,
        destinatarios: list[str],
        filename_md: str,
        filename_csv: str,
    ) -> bool:
        """Envía el informe automatizado diario usando template HTML."""
        asunto = "Informe automatizado gestión automática usuarios moodle"
        contenido = self._cargar_template(
            "informeAutomatizado.html",
            subdomain=self._settings.subdomain,
            filename_md=filename_md,
            filename_csv=filename_csv,
        )
        return self.enviar_informe(
            destinatarios, asunto, contenido, [filename_md, filename_csv]
        )

    def enviar_error_informe(
        self,
        destinatarios: list[str],
        filename_md: str,
        filename_csv: str,
        error: str,
        traceback_str: str,
    ) -> bool:
        """Envía notificación de fallo en el informe usando template HTML."""
        asunto = "FP virtual - Aragón - Ha fallado el informe"
        contenido = self._cargar_template(
            "haFalladoElInforme.html",
            subdomain=self._settings.subdomain,
            filename_md=filename_md,
            filename_csv=filename_csv,
            error=error,
            traceback=traceback_str,
            tracebackException=traceback_str,
        )
        return self.enviar_informe(
            destinatarios, asunto, contenido, [filename_md, filename_csv]
        )

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
