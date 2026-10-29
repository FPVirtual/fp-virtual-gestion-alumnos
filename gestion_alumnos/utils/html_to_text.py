"""Conversión de HTML de correo a texto plano.

Portado desde la rama ``curso2627`` (``enviar_correos.py``): omite
``<head>``, estilos y contenido oculto (p. ej. el preheader), separa los
bloques con saltos de línea y añade la URL de los enlaces cuyo texto no
la muestra. Usa solo la librería estándar (``html.parser``).
"""

from html.parser import HTMLParser


class _ExtractorTexto(HTMLParser):
    """Convierte el HTML de un correo en texto plano legible."""

    OMITIDOS = {"head", "style", "script", "title"}
    BLOQUES = {"p", "br", "div", "tr", "li", "ul", "ol", "table", "h1", "h2", "h3", "pre"}
    VACIOS = {"br", "img", "meta", "link", "hr", "input"}

    def __init__(self):
        super().__init__()
        self.partes: list[str] = []
        self._pila: list[bool] = []
        self._enlaces: list[tuple[str, int]] = []

    def _oculto(self) -> bool:
        return any(self._pila)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in self.VACIOS:
            if not self._oculto():
                if tag == "br":
                    self.partes.append("\n")
                elif tag == "img" and attrs.get("alt"):
                    self.partes.append(attrs["alt"] + " ")
            return
        estilo = (attrs.get("style") or "").replace(" ", "").lower()
        self._pila.append(tag in self.OMITIDOS or "display:none" in estilo)
        if self._oculto():
            return
        if tag in self.BLOQUES:
            self.partes.append("\n")
        if tag == "li":
            self.partes.append("- ")
        if tag == "a":
            self._enlaces.append((attrs.get("href") or "", len(self.partes)))

    def handle_endtag(self, tag):
        if tag in self.VACIOS:
            return
        oculto = self._oculto()
        if self._pila:
            self._pila.pop()
        if oculto:
            return
        if tag == "a" and self._enlaces:
            href, inicio = self._enlaces.pop()
            texto = "".join(self.partes[inicio:]).strip()
            if href.startswith("http") and href.rstrip("/") not in texto:
                self.partes.append(f" ({href})")
        if tag in self.BLOQUES:
            self.partes.append("\n")

    def handle_data(self, datos):
        if not self._oculto():
            self.partes.append(datos)

    def handle_entityref(self, nombre):
        if not self._oculto():
            self.partes.append(f"&{nombre};")

    def handle_charref(self, nombre):
        if not self._oculto():
            self.partes.append(f"&#{nombre};")

    def texto(self) -> str:
        lineas = [linea.strip() for linea in "".join(self.partes).splitlines()]
        resultado: list[str] = []
        for linea in lineas:
            if linea or (resultado and resultado[-1]):
                resultado.append(linea)
        return "\n".join(resultado).strip()


def html_a_texto(contenido_html: str) -> str:
    """Devuelve el texto plano de un HTML de correo."""
    extractor = _ExtractorTexto()
    extractor.feed(contenido_html)
    extractor.close()
    return extractor.texto()
