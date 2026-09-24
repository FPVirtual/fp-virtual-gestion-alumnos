"""
Bandeja de salida de correos en disco, compartida por main.py (que deja los correos) y
enviar_correos.py (que los envía).

Cada correo es un fichero JSON en pendientes/<SUBDOMAIN>/ con la plantilla y su contexto, no el HTML:
el HTML se genera al enviar. Los ficheros de informe empiezan por "0-" y los avisos a alumnos por "1-",
así que al ordenarlos por nombre se envían antes los informes y, dentro de cada tipo, por orden de creación.
"""
import json
import os
import uuid
from datetime import datetime

TIPO_INFORME = "0-informe"
TIPO_AVISO = "1-aviso"


def dir_pendientes(base_dir, subdomain):
    return os.path.join(base_dir, "pendientes", subdomain)


def dir_fallidos(base_dir, subdomain):
    return os.path.join(base_dir, "fallidos", subdomain)


def dir_enviados(base_dir, subdomain):
    return os.path.join(base_dir, "enviados", subdomain)


def guarda_json(ruta, datos):
    """
    Escribe el JSON de forma atómica (fichero temporal + rename) para que enviar_correos.py nunca lea uno a medias.
    """
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    os.replace(tmp, ruta)


def guarda_correo_pendiente(base_dir, subdomain, tipo, destinatario, asunto, plantilla, contexto, adjuntos=()):
    """
    Deja un correo en pendientes/<subdomain>/ y devuelve la ruta del fichero.
    contexto debe ser serializable a JSON; adjuntos son rutas absolutas que deben existir al enviar.
    """
    carpeta = dir_pendientes(base_dir, subdomain)
    os.makedirs(carpeta, exist_ok=True)
    ahora = datetime.now()
    nombre = f"{tipo}-{ahora:%Y%m%d-%H%M%S-%f}-{uuid.uuid4().hex[:8]}.json"
    ruta = os.path.join(carpeta, nombre)
    guarda_json(ruta, {
        "creado": ahora.isoformat(timespec="seconds"),
        "destinatario": destinatario,
        "asunto": asunto,
        "plantilla": plantilla,
        "contexto": contexto,
        "adjuntos": list(adjuntos),
        "intentos": 0,
    })
    return ruta
