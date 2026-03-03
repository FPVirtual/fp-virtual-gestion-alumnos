"""
Ejemplo de uso de la nueva arquitectura del sistema.

Este archivo muestra cómo usar las nuevas características:
- Configuración con Pydantic Settings
- Inyección de dependencias
- Repository Pattern
- Servicios de negocio
"""

from gestion_alumnos.core.config import get_settings, Settings
from gestion_alumnos.core.container import get_container, create_container
from gestion_alumnos.core.logging import configure_logging, get_logger
from gestion_alumnos.models_v2 import Alumno, Registro

logger = get_logger(__name__)


def ejemplo_1_configuracion():
    """Ejemplo 1: Acceder a la configuración del sistema."""
    print("\n" + "=" * 60)
    print("EJEMPLO 1: Configuración")
    print("=" * 60)
    
    # Obtener configuración (lee automáticamente .env)
    settings = get_settings()
    
    print(f"Entorno: {settings.environment}")
    print(f"Subdominio: {settings.subdomain}")
    print(f"Es producción: {settings.is_produccion}")
    print(f"Es test: {settings.is_test}")
    print(f"Límite emails: {settings.email_limit}")
    
    # Crear configuración personalizada (útil para tests)
    custom_settings = Settings(
        environment="test",
        api_user="test_user",
        api_password="test_pass"
    )
    print(f"\nConfiguración personalizada:")
    print(f"  Usuario API: {custom_settings.api_user}")


def ejemplo_2_modelos():
    """Ejemplo 2: Crear y validar modelos."""
    print("\n" + "=" * 60)
    print("EJEMPLO 2: Modelos Pydantic")
    print("=" * 60)
    
    # Crear un alumno desde diccionario (como viene del JSON)
    datos_alumno = {
        "idAlumno": 12345,
        "idTipoDocumento": 1,
        "documento": "12345678A",
        "nombre": "María",
        "apellido1": "García",
        "apellido2": "López",
        "email": "maria@ejemplo.com",
        "centros": []
    }
    
    alumno = Alumno.model_validate(datos_alumno)
    
    print(f"Alumno creado: {alumno.nombre_completo}")
    print(f"Username Moodle: {alumno.username_moodle}")
    print(f"Email institucional: {alumno.email_institucional}")
    
    # Validación automática
    try:
        datos_invalidos = {
            "idAlumno": 123,
            "idTipoDocumento": 1,
            "documento": "",  # Vacío - debería fallar
            "nombre": "Test",
            "apellido1": "Test",
            "email": "no-es-email",
            "centros": []
        }
        Alumno.model_validate(datos_invalidos)
    except Exception as e:
        print(f"\nValidación correcta: {type(e).__name__}")


def ejemplo_3_container():
    """Ejemplo 3: Usar el container de dependencias."""
    print("\n" + "=" * 60)
    print("EJEMPLO 3: Container de Dependencias")
    print("=" * 60)
    
    # Obtener container global (cacheado)
    container = get_container()
    
    # Acceder a repositorios (lazy loading)
    estudiante_repo = container.estudiante_repository()
    print(f"Repositorio estudiantes: {type(estudiante_repo).__name__}")
    
    # Obtener servicio configurado
    gestion_service = container.gestion_service()
    print(f"Servicio de gestión: {type(gestion_service).__name__}")


def ejemplo_4_mocks_testing():
    """Ejemplo 4: Cómo hacer mocks para testing."""
    print("\n" + "=" * 60)
    print("EJEMPLO 4: Mocks para Testing")
    print("=" * 60)
    
    from unittest.mock import Mock
    from gestion_alumnos.core.container import create_container
    
    # Crear container nuevo (no cacheado)
    container = create_container()
    
    # Crear mock del repositorio de estudiantes
    mock_repo = Mock()
    mock_repo.obtener_registro.return_value = Registro(
        fecha="01/01/2025",
        hora="12:00:00",
        alumnos=[
            Alumno(
                idAlumno=1,
                idTipoDocumento=1,
                documento="TEST123",
                nombre="Test",
                apellido1="User",
                email="test@test.com",
                centros=[]
            )
        ]
    )
    
    # Reemplazar el repositorio
    container.override_estudiante_repository(mock_repo)
    
    # Ahora el servicio usará el mock
    service = container.gestion_service()
    
    # Verificar que se usó el mock
    registro = service._estudiante_repo.obtener_registro()
    print(f"Alumnos mock: {registro.total_alumnos}")
    print(f"Nombre: {registro.alumnos[0].nombre}")


def ejemplo_5_excepciones():
    """Ejemplo 5: Manejo de excepciones personalizadas."""
    print("\n" + "=" * 60)
    print("EJEMPLO 5: Excepciones")
    print("=" * 60)
    
    from gestion_alumnos.core.exceptions import (
        APIError,
        ConfiguracionError,
        MoodleError
    )
    
    # Crear excepciones con contexto
    try:
        raise APIError(
            mensaje="Error de conexión",
            status_code=500,
            respuesta="Internal Server Error"
        )
    except APIError as e:
        print(f"APIError: {e.mensaje}")
        print(f"  Status: {e.status_code}")
    
    try:
        raise MoodleError(
            mensaje="Usuario no existe",
            comando="user-create test",
            codigo_salida=1
        )
    except MoodleError as e:
        print(f"\nMoodleError: {e.mensaje}")
        print(f"  Comando: {e.comando}")


def ejemplo_6_logging():
    """Ejemplo 6: Logging estructurado."""
    print("\n" + "=" * 60)
    print("EJEMPLO 6: Logging Estructurado")
    print("=" * 60)
    
    # Configurar logging
    configure_logging(
        environment="dev",
        log_level="DEBUG"
    )
    
    # Obtener logger
    logger = get_logger("ejemplo")
    
    # Diferentes niveles
    logger.debug("Mensaje de debug")
    logger.info("Mensaje informativo")
    logger.warning("Mensaje de advertencia")
    
    # Con contexto adicional
    logger.info(
        "Procesando alumno",
        alumno_id=12345,
        documento="12345678A"
    )


def main():
    """Ejecutar todos los ejemplos."""
    print("\n" + "🚀" * 30)
    print("EJEMPLOS DE LA NUEVA ARQUITECTURA")
    print("🚀" * 30)
    
    ejemplo_1_configuracion()
    ejemplo_2_modelos()
    ejemplo_3_container()
    ejemplo_4_mocks_testing()
    ejemplo_5_excepciones()
    ejemplo_6_logging()
    
    print("\n" + "=" * 60)
    print("✅ Ejemplos completados")
    print("=" * 60)


if __name__ == "__main__":
    main()
