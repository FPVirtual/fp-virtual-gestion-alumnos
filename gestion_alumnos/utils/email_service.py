"""
Módulo para la gestión de envío de emails.

Proporciona funcionalidades para enviar notificaciones a usuarios
y reportes a los administradores del sistema.
"""

import ssl
import smtplib
from pathlib import Path
from typing import List, Optional, Union
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from gestion_alumnos.models import Alumno
from gestion_alumnos.logger_config import logger


class EmailLimitExceeded(Exception):
    """Excepción lanzada cuando se alcanza el límite de emails diarios."""
    pass


class EmailService:
    """
    Servicio para el envío de emails.
    
    Gestiona el envío de notificaciones a usuarios y reportes
    a administradores, con control de límites diarios.
    
    Attributes:
        smtp_host: Servidor SMTP
        smtp_port: Puerto del servidor SMTP
        smtp_user: Usuario para autenticación SMTP
        smtp_password: Contraseña para autenticación SMTP
        subdomain: Subdominio del entorno (www, preproduccion, test)
        templates_path: Ruta a los templates HTML
        max_emails_diarios: Límite de emails según el entorno
        emails_enviados: Contador de emails enviados en la sesión
    """
    
    # Límites de emails según entorno
    LIMITE_PRODUCCION = 1000  # Gmail permite 2000, usamos 1000 por seguridad
    LIMITE_NO_PRODUCCION = 10
    
    # Asuntos predefinidos
    ASUNTO_NUEVO_USUARIO = "FP virtual - Aragón - Datos de acceso"
    ASUNTO_USUARIO_ACTUALIZADO = "FP virtual - Aragón - Usuario actualizado"
    ASUNTO_MATRICULAS_AÑADIDAS = "FP virtual - Aragón - Nuevas matrículas"
    ASUNTO_INFORME_EJECUCION = "Informe automatizado gestión automática usuarios moodle"
    ASUNTO_ERROR_INFORME = "ERROR - Informe automatizado gestión automática usuarios moodle"
    
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        subdomain: str,
        templates_path: str,
        report_to: str
    ):
        """
        Inicializa el servicio de email.
        
        Args:
            smtp_host: Servidor SMTP
            smtp_port: Puerto SMTP
            smtp_user: Usuario SMTP
            smtp_password: Contraseña SMTP
            subdomain: Subdominio (www, preproduccion, test)
            templates_path: Ruta base a los templates
            report_to: Lista de emails para reportes separados por espacios
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.subdomain = subdomain
        self.templates_path = Path(templates_path)
        self.report_to = report_to.split() if report_to else []
        self.emails_enviados = 0
        self.emails_no_enviados = 0
        
        # Establecer límite según entorno
        if subdomain == "www":
            self.max_emails_diarios = self.LIMITE_PRODUCCION
        else:
            self.max_emails_diarios = self.LIMITE_NO_PRODUCCION
        
        logger.info(f"EmailService inicializado - Entorno: {subdomain}, "
                   f"Límite emails: {self.max_emails_diarios}")
    
    def _cargar_template(self, nombre_template: str) -> str:
        """
        Carga un template HTML desde archivo.
        
        Args:
            nombre_template: Nombre del archivo template
            
        Returns:
            Contenido del template como string
            
        Raises:
            FileNotFoundError: Si no existe el template
        """
        template_path = self.templates_path / nombre_template
        try:
            return template_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.error(f"Template no encontrado: {template_path}")
            raise
    
    def _verificar_limite_emails(self) -> bool:
        """
        Verifica si se ha alcanzado el límite de emails.
        
        Returns:
            True si se puede enviar, False si se alcanzó el límite
        """
        if self.emails_enviados >= self.max_emails_diarios:
            logger.warning(f"Límite de emails alcanzado: {self.emails_enviados}/"
                          f"{self.max_emails_diarios}")
            return False
        return True
    
    def _enviar_email_simple(
        self,
        destinatario: str,
        asunto: str,
        html_content: str
    ) -> bool:
        """
        Envía un email HTML simple sin adjuntos.
        
        Args:
            destinatario: Email del destinatario
            asunto: Asunto del email
            html_content: Contenido HTML
            
        Returns:
            True si se envió correctamente, False en caso contrario
        """
        if not self._verificar_limite_emails():
            return False
        
        msg = EmailMessage()
        msg['Subject'] = asunto
        msg['From'] = self.smtp_user
        msg['To'] = destinatario
        msg.set_content("Tu cliente no soporta HTML.", subtype='plain')
        msg.add_alternative(html_content, subtype='html')
        
        context = ssl.create_default_context()
        
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
                self.emails_enviados += 1
                logger.info(f"Email enviado a: {destinatario}")
                return True
        except Exception as e:
            self.emails_no_enviados += 1
            logger.error(f"Error enviando email a {destinatario}: {e}")
            return False
    
    def _enviar_email_con_adjuntos(
        self,
        destinatario: str,
        asunto: str,
        html_content: str,
        adjuntos: List[Union[str, Path]]
    ) -> bool:
        """
        Envía un email HTML con archivos adjuntos.
        
        Args:
            destinatario: Email del destinatario
            asunto: Asunto del email
            html_content: Contenido HTML
            adjuntos: Lista de rutas a archivos adjuntos
            
        Returns:
            True si se envió correctamente, False en caso contrario
        """
        if not self._verificar_limite_emails():
            return False
        
        message = MIMEMultipart("alternative")
        message["From"] = self.smtp_user
        message["To"] = destinatario
        message["Subject"] = asunto
        
        # Agregar contenido HTML
        message.attach(MIMEText(html_content, "html"))
        
        # Adjuntar archivos
        for filepath in adjuntos:
            try:
                path = Path(filepath)
                with open(path, 'rb') as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename= {path.name}"
                )
                message.attach(part)
            except Exception as e:
                logger.error(f"Error adjuntando archivo {filepath}: {e}")
        
        context = ssl.create_default_context()
        
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(
                    self.smtp_user,
                    destinatario,
                    message.as_string()
                )
                self.emails_enviados += 1
                logger.info(f"Email con adjuntos enviado a: {destinatario}")
                return True
        except Exception as e:
            self.emails_no_enviados += 1
            logger.error(f"Error enviando email con adjuntos a {destinatario}: {e}")
            return False
    
    def _get_destinatario_seguro(self, email_real: Optional[str]) -> str:
        """
        Obtiene el destinatario seguro según el entorno.
        
        En producción envía al email real, en otros entornos
        redirige a una cuenta de control.
        
        Args:
            email_real: Email real del destinatario
            
        Returns:
            Email al que realmente se enviará
        """
        if self.subdomain == "www" and email_real:
            return email_real
        else:
            # En entornos no productivos, enviar a cuenta de gestión
            logger.info(f"Redirigiendo email a gestion@fpvirtualaragon.es "
                       f"(entorno: {self.subdomain})")
            return "gestion@fpvirtualaragon.es"
    
    def enviar_email_nuevo_usuario(
        self,
        alumno: Alumno,
        password: str,
        matriculado_en_texto: str
    ) -> bool:
        """
        Envía email de bienvenida a un nuevo usuario.
        
        Args:
            alumno: Objeto Alumno con los datos del usuario
            password: Contraseña generada
            matriculado_en_texto: Lista HTML de cursos matriculados
            
        Returns:
            True si se envió correctamente, False en caso contrario
        """
        try:
            template = self._cargar_template("nuevoUsuario.html")
            
            mensaje = template.format(
                nombre=alumno.nombre,
                apellidos=f"{alumno.apellido1} {alumno.apellido2 or ''}".strip(),
                subdomain=self.subdomain,
                usuario=alumno.documento.lower(),
                contrasena=password,
                matriculado_en_texto=matriculado_en_texto,
                email=f"{alumno.documento.lower()}@fpvirtualaragon.es"
            )
            
            destinatario = self._get_destinatario_seguro(alumno.email)
            
            return self._enviar_email_simple(
                destinatario,
                self.ASUNTO_NUEVO_USUARIO,
                mensaje
            )
            
        except Exception as e:
            logger.error(f"Error preparando email de nuevo usuario: {e}")
            self.emails_no_enviados += 1
            return False
    
    def enviar_email_usuario_actualizado(
        self,
        alumno: Alumno,
        old_usuario: str,
        nuevo_usuario: str
    ) -> bool:
        """
        Envía email notificando cambio de usuario (NIE→DNI).
        
        Args:
            alumno: Objeto Alumno con los datos del usuario
            old_usuario: Usuario anterior (NIE)
            nuevo_usuario: Nuevo usuario (DNI)
            
        Returns:
            True si se envió correctamente, False en caso contrario
        """
        try:
            template = self._cargar_template("nombreUsuarioActualizado.html")
            
            mensaje = template.format(
                subdomain=self.subdomain,
                usuario=nuevo_usuario,
                oldUsuario=old_usuario
            )
            
            # Para actualizaciones, usar email del dominio si está disponible
            email_destino = None
            if hasattr(alumno, 'email_dominio') and alumno.email_dominio:
                email_destino = alumno.email_dominio
            else:
                email_destino = alumno.email
                
            destinatario = self._get_destinatario_seguro(email_destino)
            
            return self._enviar_email_simple(
                destinatario,
                self.ASUNTO_USUARIO_ACTUALIZADO,
                mensaje
            )
            
        except Exception as e:
            logger.error(f"Error preparando email de usuario actualizado: {e}")
            self.emails_no_enviados += 1
            return False
    
    def enviar_email_matriculas_añadidas(
        self,
        alumno: Alumno,
        matriculado_en_texto: str
    ) -> bool:
        """
        Envía email notificando nuevas matrículas añadidas.
        
        Args:
            alumno: Objeto Alumno con los datos del usuario
            matriculado_en_texto: Lista HTML de nuevas matrículas
            
        Returns:
            True si se envió correctamente, False en caso contrario
        """
        try:
            template = self._cargar_template("matriculasAnadidas.html")
            
            mensaje = template.format(
                nombre=alumno.nombre,
                apellidos=f"{alumno.apellido1} {alumno.apellido2 or ''}".strip(),
                subdomain=self.subdomain,
                matriculado_en_texto=matriculado_en_texto
            )
            
            destinatario = self._get_destinatario_seguro(alumno.email)
            
            return self._enviar_email_simple(
                destinatario,
                self.ASUNTO_MATRICULAS_AÑADIDAS,
                mensaje
            )
            
        except Exception as e:
            logger.error(f"Error preparando email de matrículas añadidas: {e}")
            self.emails_no_enviados += 1
            return False
    
    def enviar_informe_ejecucion(
        self,
        filename_md: str,
        filename_csv: str,
        resumen: Optional[dict] = None
    ) -> bool:
        """
        Envía el informe de ejecución a la lista de REPORT_TO.
        
        Args:
            filename_md: Ruta al archivo Markdown del informe
            filename_csv: Ruta al archivo CSV con datos
            resumen: Diccionario opcional con datos de resumen
            
        Returns:
            True si se envió a todos los destinatarios, False si falló alguno
        """
        try:
            template = self._cargar_template("informeAutomatizado.html")
            
            mensaje = template.format(
                subdomain=self.subdomain,
                filename_md=filename_md,
                filename_csv=filename_csv
            )
            
            resultados = []
            for email in self.report_to:
                resultado = self._enviar_email_con_adjuntos(
                    email,
                    self.ASUNTO_INFORME_EJECUCION,
                    mensaje,
                    [filename_md, filename_csv]
                )
                resultados.append(resultado)
            
            return all(resultados) if resultados else True
            
        except Exception as e:
            logger.error(f"Error enviando informe de ejecución: {e}")
            return False
    
    def enviar_error_informe(
        self,
        filename_md: str,
        filename_csv: str,
        error: Exception,
        traceback_str: str
    ) -> bool:
        """
        Envía notificación de error en la ejecución.
        
        Args:
            filename_md: Ruta al archivo Markdown del informe
            filename_csv: Ruta al archivo CSV
            error: Excepción ocurrida
            traceback_str: Traceback del error como string
            
        Returns:
            True si se envió a todos los destinatarios, False si falló alguno
        """
        try:
            template = self._cargar_template("haFalladoElInforme.html")
            
            mensaje = template.format(
                subdomain=self.subdomain,
                filename_md=filename_md,
                filename_csv=filename_csv,
                error=str(error),
                traceback=traceback_str,
                tracebackException=traceback_str
            )
            
            resultados = []
            for email in self.report_to:
                resultado = self._enviar_email_con_adjuntos(
                    email,
                    self.ASUNTO_ERROR_INFORME,
                    mensaje,
                    [filename_md, filename_csv]
                )
                resultados.append(resultado)
            
            return all(resultados) if resultados else True
            
        except Exception as e:
            logger.error(f"Error enviando notificación de error: {e}")
            return False
    
    def obtener_estadisticas(self) -> dict:
        """
        Obtiene estadísticas de envío de emails.
        
        Returns:
            Diccionario con emails_enviados, emails_no_enviados, limite
        """
        return {
            "emails_enviados": self.emails_enviados,
            "emails_no_enviados": self.emails_no_enviados,
            "limite_diario": self.max_emails_diarios,
            "disponibles": max(0, self.max_emails_diarios - self.emails_enviados)
        }
    
    def limite_alcanzado(self) -> bool:
        """
        Indica si se ha alcanzado el límite de emails.
        
        Returns:
            True si se alcanzó el límite, False en caso contrario
        """
        return self.emails_enviados >= self.max_emails_diarios


# Función de fábrica para crear el servicio desde configuración
def crear_email_service(
    smtp_host: str,
    smtp_port: str,
    smtp_user: str,
    smtp_password: str,
    subdomain: str,
    templates_path: str,
    report_to: str
) -> EmailService:
    """
    Crea una instancia de EmailService desde valores de configuración.
    
    Args:
        smtp_host: Servidor SMTP
        smtp_port: Puerto SMTP (como string, se convertirá a int)
        smtp_user: Usuario SMTP
        smtp_password: Contraseña SMTP
        subdomain: Subdominio del entorno
        templates_path: Ruta a los templates
        report_to: Emails para reportes separados por espacios
        
    Returns:
        Instancia de EmailService configurada
    """
    return EmailService(
        smtp_host=smtp_host,
        smtp_port=int(smtp_port),
        smtp_user=smtp_user,
        smtp_password=smtp_password,
        subdomain=subdomain,
        templates_path=templates_path,
        report_to=report_to
    )
