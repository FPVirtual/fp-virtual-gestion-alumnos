import re

def es_nie_valido(nie: str) -> bool:
    """
    Devuelve True si el formato del string corresponde a un NIE válido.
    Formato: Letra inicial X, Y o Z + 7 dígitos + letra final (A-Z)
    """
    nie = nie.upper().strip()
    patron = r'^[XYZ]\d{7}[A-Z]$'
    return bool(re.match(patron, nie))

def es_dni_valido(dni: str) -> bool:
    """
    Devuelve True si el string tiene formato y letra de control válidos de un DNI español.
    Formato válido: 8 dígitos seguidos de una letra mayúscula (sin espacios ni guiones).
    """
    dni = dni.upper().strip()
    patron = r'^\d{8}[A-Z]$'
    return bool(re.match(patron, dni))