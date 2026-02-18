"""
Gestion Alumnos - Módulo para gestión automática de usuarios en Moodle.

Este paquete proporciona funcionalidades para:
- Sincronizar alumnos desde SIGAD a Moodle
- Gestionar matrículas en cursos
- Enviar notificaciones por email
- Generar informes de ejecución
"""

__version__ = "0.1.0"

from gestion_alumnos.utils.email_service import EmailService, crear_email_service
from gestion_alumnos.models import Alumno, Centro, Ciclo, Modulo, Registro

__all__ = [
    "EmailService",
    "crear_email_service",
    "Alumno",
    "Centro",
    "Ciclo",
    "Modulo",
    "Registro",
]
