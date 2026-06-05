"""Interfaz de línea de comandos."""

import argparse
import sys
from pathlib import Path

from gestion_alumnos.core.config import Settings
from gestion_alumnos.core.container import get_container
from gestion_alumnos.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


def crear_parser() -> argparse.ArgumentParser:
    """Crea el parser de argumentos."""
    parser = argparse.ArgumentParser(
        prog="gestion-alumnos",
        description="Gestión automática de alumnos en Moodle",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Archivo .env con variables de entorno",
    )
    parser.add_argument(
        "--driver",
        choices=["moosh", "api"],
        default=None,
        help="Driver de Moodle (sobrescribe MOODLE_DRIVER)",
    )
    parser.add_argument(
        "--source-strategy",
        choices=["api-course-based", "api-snapshot"],
        default=None,
        help="Estrategia de extracción de Moodle (sobrescribe MOODLE_SOURCE_STRATEGY)",
    )
    parser.add_argument(
        "--subdomain",
        choices=["test", "preproduccion", "www"],
        default=None,
        help="Subdominio (sobrescribe SUBDOMAIN)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Mostrar logs de debug",
    )

    subparsers = parser.add_subparsers(dest="comando", help="Comandos disponibles")

    # sync
    sync_parser = subparsers.add_parser("sync", help="Sincronizar alumnos SIGAD -> Moodle")
    sync_parser.add_argument(
        "--desde-fichero",
        type=Path,
        default=None,
        help="Procesar desde un JSON local en lugar de la API",
    )
    sync_parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplicar cambios en Moodle (por defecto solo analiza en dry-run)",
    )

    # extract
    subparsers.add_parser("extract", help="Extraer alumnado a CSV")

    # report
    subparsers.add_parser("report", help="Generar informe sin modificar datos")

    # process-emails
    subparsers.add_parser("process-emails", help="Procesar cola de emails pendientes")

    return parser


def main(args: list[str] | None = None) -> int:
    """Punto de entrada principal.

    Returns:
        Código de salida (0 = éxito, 1 = error).
    """
    parser = crear_parser()
    ns = parser.parse_args(args)

    if not ns.comando:
        parser.print_help()
        return 1

    # Sobrescribir env_file si se proporciona
    if ns.env_file:
        import os
        os.environ["ENV_FILE"] = str(ns.env_file)

    # Sobrescribir driver si se proporciona
    if ns.driver:
        import os
        os.environ["MOODLE_DRIVER"] = ns.driver

    # Sobrescribir source strategy si se proporciona
    if ns.source_strategy:
        import os
        os.environ["MOODLE_SOURCE_STRATEGY"] = ns.source_strategy

    # Sobrescribir subdomain si se proporciona
    if ns.subdomain:
        import os
        os.environ["SUBDOMAIN"] = ns.subdomain

    # Configurar logging
    settings = Settings()
    configure_logging(
        environment=settings.environment,
        logs_dir=settings.logs_dir,
        log_level="DEBUG" if ns.verbose else "INFO",
    )

    logger.info(
        "Iniciando gestion-alumnos",
        version="0.3.0",
        entorno=settings.environment,
        driver=settings.moodle_driver,
        source_strategy=settings.moodle_source_strategy,
        subdomain=settings.subdomain,
    )

    try:
        container = get_container()

        if ns.comando == "sync":
            dry_run = not ns.apply
            orchestrator = container.sync_orchestrator(dry_run=dry_run)
            report = orchestrator.run()
            logger.info("Sincronización completada", changes=report.has_changes, dry_run=dry_run)
            return 0

        elif ns.comando == "extract":
            logger.info("Extracción aún no implementada")
            return 0

        elif ns.comando == "report":
            orchestrator = container.sync_orchestrator(dry_run=True)
            report = orchestrator.run()
            logger.info("Informe generado", changes=report.has_changes)
            print(report.to_markdown())
            if orchestrator._report_logger and orchestrator._report_logger.filename:
                print(f"\n📄 Informe guardado en: {orchestrator._report_logger.filename}")
            return 0

        elif ns.comando == "process-emails":
            from gestion_alumnos.services.email_queue_processor import EmailQueueProcessor

            processor = EmailQueueProcessor()
            stats = processor.process_all()
            print(f"\n📧 Emails procesados: {stats['enviados']} enviados, {stats['fallidos']} fallidos, {stats['saltados']} saltados")
            return 0

        else:
            parser.print_help()
            return 1

    except Exception as e:
        logger.error(f"Error fatal: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
