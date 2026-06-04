"""Funciones utilitarias puras."""

import secrets
import string
from datetime import datetime


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
