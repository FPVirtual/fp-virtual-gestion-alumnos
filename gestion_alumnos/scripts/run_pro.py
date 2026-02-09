# scripts/run_pre.py
import sys
from pathlib import Path

proyecto_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(proyecto_root))

import os
import errno
from dotenv import load_dotenv
from gestion_alumnos.logger_config import logger   # logger global MarkdownLogger
from gestion_alumnos.main import gestion_alumnos

proyecto_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(proyecto_root))

logger.info("## Inicio de la ejecución del script GESTION ALUMNOS ##")

env = os.getenv("APP_ENV", "produccion")
dotenv_file = Path(f".env.{env}").resolve()
ok = load_dotenv(dotenv_path=dotenv_file, override=True)

if ok:
    logger.info("✅ Cargado %s", dotenv_file.name)
else:
    raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), dotenv_file)


if __name__ == "__main__":
    gestion_alumnos()