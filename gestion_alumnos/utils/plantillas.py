"""Renderizado de plantillas de email con Jinja2.

Las plantillas HTML del paquete usan sintaxis Jinja2 (``{{ variable }}``,
``{% bloques %}``) sobre ``base.html``, que define la estructura común:
cabecera con logo incrustado, preheader oculto, contenido y pie.

El autoescape de Jinja2 escapa automáticamente los valores procedentes de
SIGAD, por lo que no hace falta envolver valores en HTML preprocesado.
"""

from functools import lru_cache
from importlib import resources

from jinja2 import DictLoader, Environment, select_autoescape


def logo_disponible() -> bool:
    """Indica si existe el logo empaquetado en ``templates/img/logo.png``."""
    return (resources.files("gestion_alumnos.templates") / "img" / "logo.png").is_file()


@lru_cache(maxsize=1)
def _entorno() -> Environment:
    """Construye (una sola vez) el entorno Jinja2 con las plantillas del paquete.

    Se usa ``DictLoader`` cargado vía ``importlib.resources`` para que el
    render funcione tanto en desarrollo como dentro del zipapp.
    """
    directorio = resources.files("gestion_alumnos.templates")
    plantillas = {
        entrada.name: entrada.read_text(encoding="utf-8")
        for entrada in directorio.iterdir()
        if entrada.name.endswith(".html")
    }
    env = Environment(
        loader=DictLoader(plantillas),
        autoescape=select_autoescape(["html"]),
    )
    return env


def renderizar_plantilla(nombre_plantilla: str, **kwargs) -> str:
    """Renderiza una plantilla Jinja2 del paquete.

    Args:
        nombre_plantilla: Nombre del fichero en ``gestion_alumnos/templates``.
        kwargs: Valores del contexto. Los strings se escapan automáticamente
            por el autoescape de Jinja2.

    Returns:
        HTML renderizado y seguro.
    """
    plantilla = _entorno().get_template(nombre_plantilla)
    return plantilla.render(**kwargs)
