# logger_config.py
import logging
import sys
from pathlib import Path
from datetime import datetime

# 1️⃣ Nivel de log personalizado para Markdown
MARKDOWN_LEVEL = 25  # Entre INFO (20) y WARNING (30)


class MarkdownLogger(logging.Logger):
    """Logger con método markdown() exclusivo"""
    def markdown(self, message, *args, **kwargs):
        self.log(MARKDOWN_LEVEL, message, *args, **kwargs)


class MarkdownFilter(logging.Filter):
    """Filtro que solo pasa los logs de nivel MARKDOWN"""
    def filter(self, record):
        return record.levelno == MARKDOWN_LEVEL


class MarkdownFormatter(logging.Formatter):
    """Convierte solo los mensajes markdown a formato MD"""
    def format(self, record):
        return f"- 📝 **Informe:** {record.getMessage()}\n"


def _running_under_pytest() -> bool:
    """True si el proceso lo ha arrancado pytest"""
    return "pytest" in sys.modules or any("pytest" in arg for arg in sys.argv)


def setup_logger(name: str = "gestion-alumnos") -> MarkdownLogger:
    # Registrar la clase de logger personalizada
    logging.setLoggerClass(MarkdownLogger)

    project_root = Path(__file__).parent.resolve()
    log_dir = project_root / "logs"
    log_dir.mkdir(mode=0o755, exist_ok=True)

    timestamp = datetime.now().strftime("%d-%m-%Y_%H%M%S")
    suffix = "_test" if _running_under_pytest() else ""

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Handler de archivo normal (DEBUG y superior)
    main_handler = logging.FileHandler(
        log_dir / f"app{suffix}_{timestamp}.log", encoding="utf-8"
    )
    main_handler.setLevel(logging.DEBUG)
    main_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(main_handler)

    # Handler EXCLUSIVO para markdown
    md_handler = logging.FileHandler(
        log_dir / f"informe{suffix}_{timestamp}.md", mode="w", encoding="utf-8"
    )
    md_handler.setLevel(MARKDOWN_LEVEL)
    md_handler.addFilter(MarkdownFilter())
    md_handler.setFormatter(MarkdownFormatter())
    logger.addHandler(md_handler)

    # Handler de consola (INFO y superior, excepto markdown)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.addFilter(lambda r: r.levelno != MARKDOWN_LEVEL)
    logger.addHandler(console_handler)

    return logger


# ------------------------------------------------------------------
# Logger ÚNICO global (configurado solo la primera vez)
# ------------------------------------------------------------------
logger = setup_logger("gestion-alumnos")
   
    
