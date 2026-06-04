"""Script para generar el zipapp del paquete.

Uso:
    python scripts/build_zipapp.py

Genera ``dist/gestion_alumnos.pyz``.
"""

import shutil
import subprocess
import sys
import zipapp
from pathlib import Path


def main() -> int:
    """Genera el zipapp."""
    raiz = Path(__file__).resolve().parent.parent
    dist_dir = raiz / "dist"
    build_dir = raiz / "build_zipapp"
    paquete_src = raiz / "gestion_alumnos"

    # Limpiar build anterior
    if build_dir.exists():
        shutil.rmtree(build_dir)
    dist_dir.mkdir(exist_ok=True)

    # Copiar paquete al directorio de build
    shutil.copytree(paquete_src, build_dir / "gestion_alumnos")

    # Crear __main__.py en la raíz del build si no existe
    main_py = build_dir / "__main__.py"
    if not main_py.exists():
        main_py.write_text(
            "from gestion_alumnos.cli import main\n"
            "import sys\n"
            "sys.exit(main())\n",
            encoding="utf-8",
        )

    # Generar zipapp
    pyz_path = dist_dir / "gestion_alumnos.pyz"
    zipapp.create_archive(
        build_dir,
        pyz_path,
        interpreter="/usr/bin/env python3",
        compressed=True,
    )

    print(f"✓ Zipapp generado: {pyz_path}")
    print(f"  Tamaño: {pyz_path.stat().st_size / 1024:.1f} KB")

    # Limpiar build
    shutil.rmtree(build_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
