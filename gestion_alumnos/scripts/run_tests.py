#!/usr/bin/env python3
"""
Entry-point para ejecutar los tests con:
    poetry run test
Carga el .env que corresponda según APP_ENV y lanza pytest.
"""
import os
import sys
import pytest
from pathlib import Path
from dotenv import load_dotenv


def main() -> int:
    """Configura entorno y ejecuta pytest."""
    # 1. archivo .env a usar
    env = os.getenv("APP_ENV", "test")
    dotenv_file = Path(f".env.{env}").resolve()

    # 2. cargar variables (override=True para forzar valores del fichero)
    if dotenv_file.exists():
        load_dotenv(dotenv_path=dotenv_file, override=True)
    else:
        sys.stderr.write(f"⚠️  No se encontró {dotenv_file}\n")

    # 3. pasar el control a pytest
    return pytest.main(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())