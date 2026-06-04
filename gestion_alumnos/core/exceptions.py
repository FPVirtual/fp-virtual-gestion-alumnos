"""
Excepciones personalizadas del sistema.

Define una jerarquía clara de excepciones para facilitar
el manejo de errores específicos del dominio.
"""


class GestionAlumnosError(Exception):
    """Excepción base para todos los errores del sistema."""
    
    def __init__(self, mensaje: str, detalles: dict | None = None) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.detalles = detalles or {}


class ConfiguracionError(GestionAlumnosError):
    """Error en la configuración del sistema (variables de entorno, etc.)."""
    pass


class APIError(GestionAlumnosError):
    """Error en la comunicación con APIs externas (SIGAD)."""
    
    def __init__(
        self,
        mensaje: str,
        status_code: int | None = None,
        respuesta: str | None = None,
        detalles: dict | None = None
    ) -> None:
        super().__init__(mensaje, detalles)
        self.status_code = status_code
        self.respuesta = respuesta


class APIRateLimitError(APIError):
    """Error cuando se alcanza el límite de peticiones de la API."""
    pass


class APITimeoutError(APIError):
    """Error cuando la API no responde en el tiempo esperado."""
    pass


class MoodleError(GestionAlumnosError):
    """Error en operaciones con Moodle (moosh, base de datos)."""
    
    def __init__(
        self,
        mensaje: str,
        comando: str | None = None,
        codigo_salida: int | None = None,
        detalles: dict | None = None
    ) -> None:
        super().__init__(mensaje, detalles)
        self.comando = comando
        self.codigo_salida = codigo_salida


class EmailError(GestionAlumnosError):
    """Error en el envío de emails."""
    
    def __init__(
        self,
        mensaje: str,
        destinatario: str | None = None,
        detalles: dict | None = None
    ) -> None:
        super().__init__(mensaje, detalles)
        self.destinatario = destinatario


class EmailLimitExceeded(EmailError):
    """Se ha alcanzado el límite diario de emails."""
    pass


class ValidacionError(GestionAlumnosError):
    """Error en la validación de datos."""
    pass


class RepositorioError(GestionAlumnosError):
    """Error en operaciones de repositorio (acceso a datos)."""
    pass
