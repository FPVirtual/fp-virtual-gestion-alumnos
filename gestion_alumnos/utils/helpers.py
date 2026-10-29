"""Funciones utilitarias puras."""

import fcntl
import secrets
import string
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


def generar_password(longitud: int = 10) -> str:
    """Genera una contraseña aleatoria segura."""
    return "".join(
        secrets.choice(string.ascii_letters + string.digits)
        for _ in range(longitud)
    )


def get_curso_academico() -> str:
    """Devuelve el curso académico actual en formato 'YYYY-YYYY+1'.

    Ejemplo: si estamos en enero 2026, devuelve '2025-2026'.
    """
    ahora = datetime.now()
    if ahora.month >= 9:
        return f"{ahora.year}-{ahora.year + 1}"
    return f"{ahora.year - 1}-{ahora.year}"


def normalizar_documento(documento: str) -> str:
    """Normaliza un DNI/NIE: mayúsculas, sin espacios."""
    return documento.strip().upper()


def es_augusto() -> bool:
    """Indica si estamos en agosto (mes de limpieza)."""
    return datetime.now().month == 8


@contextmanager
def bloqueo_ejecucion(lock_path: Path):
    """Bloqueo de ejecución concurrente mediante flock (no bloqueante).

    Portado desde ``enviar_correos.py`` de la rama ``curso2627``: evita que
    dos procesos procesen la cola de emails a la vez (envíos duplicados).

    Args:
        lock_path: Ruta del fichero de bloqueo.

    Raises:
        RuntimeError: Si otra ejecución tiene el bloqueo.
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "w") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError(
                f"Otra ejecución está en curso (bloqueo: {lock_path})"
            )
        yield
