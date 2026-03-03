"""
Punto de entrada principal v2 - Usando arquitectura moderna.

Implementa el flujo de gestión de alumnos usando:
- Inyección de dependencias
- Repository Pattern
- Programación orientada a protocolos
- Logging estructurado
"""

import sys
import traceback
from datetime import datetime

from gestion_alumnos.core.config import get_settings
from gestion_alumnos.core.container import get_container
from gestion_alumnos.core.logging import configure_logging, get_logger
from gestion_alumnos.core.exceptions import GestionAlumnosError

logger = get_logger(__name__)


def main() -> int:
    """
    Función principal de ejecución.
    
    Returns:
        0 si la ejecución fue exitosa, 1 en caso de error
    """
    # Configurar logging
    settings = get_settings()
    configure_logging(
        environment=settings.environment,
        logs_dir=settings.logs_dir,
        log_level="DEBUG" if settings.is_test else "INFO"
    )
    
    # Asegurar directorios
    settings.ensure_directories()
    
    logger.info("=" * 60)
    logger.info(f"GESTIÓN DE ALUMNOS v2.0 - {settings.environment.upper()}")
    logger.info(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    logger.info("=" * 60)
    
    try:
        # Crear container de dependencias
        container = get_container()
        
        # Obtener servicio de gestión
        gestion_service = container.gestion_service()
        
        # Ejecutar sincronización
        resultado = gestion_service.ejecutar_sincronizacion_completa()
        
        # Log de resultados
        logger.info("-" * 60)
        logger.info("RESULTADO DE LA SINCRONIZACIÓN")
        logger.info("-" * 60)
        logger.info(f"Alumnos procesados: {resultado.alumnos_procesados}")
        logger.info(f"Nuevos usuarios: {resultado.nuevos_creados}")
        logger.info(f"Reactivados: {resultado.reactivados}")
        logger.info(f"Suspendidos: {resultado.suspendidos}")
        logger.info(f"Emails actualizados: {resultado.emails_actualizados}")
        logger.info(f"Nuevas matrículas: {resultado.nuevas_matriculas}")
        
        if resultado.errores:
            logger.warning(f"Errores encontrados: {len(resultado.errores)}")
            for error in resultado.errores:
                logger.warning(f"  - {error}")
        
        if resultado.exito:
            logger.info("✅ Sincronización completada exitosamente")
            return 0
        else:
            logger.error("❌ Sincronización completada con errores")
            return 1
            
    except GestionAlumnosError as e:
        logger.error(f"Error del sistema: {e.mensaje}")
        if e.detalles:
            logger.debug(f"Detalles: {e.detalles}")
        return 1
        
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        logger.debug(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
