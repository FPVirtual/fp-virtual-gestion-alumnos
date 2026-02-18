"""
Utilidades para el módulo de gestión de alumnos.

Este paquete contiene utilidades compartidas como:
- email_service: Servicio de envío de emails
- api_client: Cliente para la API de SIGAD
- json_parser: Parser de datos JSON
"""

from gestion_alumnos.utils.email_service import EmailService, crear_email_service_desde_env

__all__ = [
    "EmailService",
    "crear_email_service_desde_env",
]
