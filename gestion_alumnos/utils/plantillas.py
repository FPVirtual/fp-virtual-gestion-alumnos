"""Utilidades para el renderizado seguro de plantillas de email.

Las plantillas HTML del paquete usan placeholders ``{nombre}`` renderizados
con ``str.format``. Este módulo centraliza ese renderizado y **escapa** los
valores para evitar inyección HTML con datos procedentes de SIGAD.

Cuando un valor debe llegar como HTML ya procesado (p. ej. una lista de
matrículas separada por ``<br/>``), envuélvelo en :class:`HTMLSeguro`.
"""

import html
from importlib import resources


class HTMLSeguro(str):
    """Marca contenido HTML ya escapado para que no se vuelva a escapar."""


def escapar_kwargs(kwargs: dict) -> dict:
    """Escapa los valores de tipo str para su interpolación en HTML."""
    return {
        clave: (
            valor
            if isinstance(valor, HTMLSeguro)
            else html.escape(str(valor), quote=True)
            if isinstance(valor, str)
            else valor
        )
        for clave, valor in kwargs.items()
    }


def renderizar_plantilla(nombre_plantilla: str, **kwargs) -> str:
    """Carga una plantilla del paquete y sustituye sus placeholders escapados.

    Args:
        nombre_plantilla: Nombre del fichero en ``gestion_alumnos/templates``.
        kwargs: Valores a interpolar. Los strings se escapan con
            ``html.escape`` salvo que sean :class:`HTMLSeguro`.

    Returns:
        HTML renderizado y seguro.
    """
    ruta = resources.files("gestion_alumnos.templates") / nombre_plantilla
    contenido = ruta.read_text(encoding="utf-8")
    return contenido.format(**escapar_kwargs(kwargs))


def matriculas_a_html(matriculas: list[str]) -> HTMLSeguro:
    """Convierte una lista de matrículas en HTML seguro separado por <br/>."""
    return HTMLSeguro("<br/>".join(html.escape(m) for m in matriculas))
