"""
Envía los correos que main.py ha dejado en pendientes/<SUBDOMAIN>/ (ver Correo.py).

- Genera el HTML de cada correo con su plantilla de templates/ (Jinja2).
- Espera PAUSA_ENTRE_CORREOS segundos entre un correo y el siguiente.
- Si el envío va bien, mueve el fichero a enviados/<SUBDOMAIN>/ (con la fecha de envío). Si falla, suma un intento y lo deja para la siguiente ejecución;
  al llegar a MAX_INTENTOS lo mueve a fallidos/<SUBDOMAIN>/.
- Como mucho envía MAX_CORREOS_POR_EJECUCION correos (límite diario de la cuenta); el resto queda pendiente.
"""
import argparse
import json
import os
import smtplib
import ssl
import sys
import time
from datetime import datetime
from email.message import EmailMessage
from html.parser import HTMLParser

# Se parsean los argumentos antes de importar Config para que --help funcione sin Config.py
parser = argparse.ArgumentParser(
    description="Envía los correos pendientes que ha generado main.py."
)
parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Genera el HTML de cada correo pendiente pero no lo envía ni toca los ficheros.",
)
parser.add_argument(
    "--solo-informes",
    action="store_true",
    help="Envía sólo los informes (0-informe-*) y deja los avisos pendientes. Lo usa el cron cuando main.py falla.",
)
args = parser.parse_args()
DRY_RUN = args.dry_run
SOLO_INFORMES = args.solo_informes

from Config import *
from Correo import dir_pendientes, dir_fallidos, dir_enviados, guarda_json, TIPO_INFORME
from jinja2 import Environment, FileSystemLoader, select_autoescape

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PAUSA_ENTRE_CORREOS = 2  # segundos
MAX_INTENTOS = 3
SMTP_TIMEOUT = 30  # segundos
# limitacion de 2.000 emails diarios en actual cuenta de gmail; en entornos que no son producción, muy pocos.
# Se puede fijar con MAX_CORREOS_POR_EJECUCION en Config.py
MAX_CORREOS_POR_EJECUCION = int(globals().get("MAX_CORREOS_POR_EJECUCION") or (1000 if SUBDOMAIN == "www" else 3))

# Plantillas de correo (Jinja2, todas heredan de templates/base.html). El logo es opcional:
# si existe templates/img/logo.png se incrusta en los correos.
LOGO_PATH = BASE_DIR + "/templates/img/logo.png"
LOGO_DISPONIBLE = os.path.isfile(LOGO_PATH)
entorno_plantillas = Environment(
    loader=FileSystemLoader(BASE_DIR + "/templates"),
    autoescape=select_autoescape(["html"]),
)


def renderiza_plantilla(nombre_plantilla, contexto):
    """
    Devuelve el HTML de templates/<nombre_plantilla> con el contexto dado (se escapan los valores).
    """
    return entorno_plantillas.get_template(nombre_plantilla).render(logo=LOGO_DISPONIBLE, **contexto)


class _ExtractorTexto(HTMLParser):
    """
    Convierte el HTML de un correo en texto plano: omite <head>, estilos y lo oculto (el preheader),
    separa los bloques con saltos de línea y añade la URL de los enlaces cuyo texto no la muestra.
    """
    OMITIDOS = {"head", "style", "script", "title"}
    BLOQUES = {"p", "br", "div", "tr", "li", "ul", "ol", "table", "h1", "h2", "h3", "pre"}
    VACIOS = {"br", "img", "meta", "link", "hr", "input"}  # no tienen etiqueta de cierre

    def __init__(self):
        super().__init__()
        self.partes = []
        self._pila = []  # por cada etiqueta abierta: si oculta su contenido
        self._enlaces = []

    def _oculto(self):
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

    def handle_data(self, data):
        if not self._oculto():
            self.partes.append(data)


def html_a_texto(html):
    """
    Versión de texto plano del correo (la usan los clientes sin HTML y muchos para la previsualización).
    """
    extractor = _ExtractorTexto()
    extractor.feed(html)
    lineas = (" ".join(linea.split()) for linea in "".join(extractor.partes).splitlines())
    return "\n".join(linea for linea in lineas if linea) + "\n"


def construye_mensaje(remitente, destinatario, asunto, html, adjuntos):
    msg = EmailMessage()
    msg['Subject'] = asunto
    msg['From'] = remitente
    msg['To'] = destinatario
    msg.set_content(html_a_texto(html))       # parte de texto plano, generada a partir del HTML
    msg.add_alternative(html, subtype='html')  # parte HTML
    # el logo se incrusta como imagen y las plantillas lo referencian como cid:logo. Se marca como "inline" y con
    # nombre para que los clientes no lo muestren como un adjunto "noname" (sólo forma parte de la cabecera)
    if LOGO_DISPONIBLE:
        with open(LOGO_PATH, 'rb') as f:
            msg.get_body(('html',)).add_related(f.read(), maintype='image', subtype='png', cid="<logo>",
                                                disposition='inline', filename='logo.png')
    for ruta in adjuntos:
        try:
            with open(ruta, 'rb') as f:
                msg.add_attachment(f.read(), maintype='application', subtype='octet-stream',
                                   filename=os.path.basename(ruta))
        except Exception as e:
            print(f"Error al adjuntar {ruta}: {e}")
    return msg


def conecta():
    # sin timeout, un servidor que no responde dejaría el proceso colgado y con el bloqueo cogido
    server = smtplib.SMTP(SMTP_HOSTS, SMTP_PORT, timeout=SMTP_TIMEOUT)
    server.starttls(context=ssl.create_default_context())
    server.login(SMTP_USER, SMTP_PASSWORD)
    return server


def bloquea_ejecucion():
    """
    Evita que dos envíos corran a la vez (p. ej. si el cron lanza otro antes de que acabe el anterior),
    lo que mandaría correos repetidos. Devuelve el fichero de bloqueo (hay que mantenerlo abierto) o None si ya
    hay otro envío en marcha. En Windows no hay fcntl y no se bloquea.
    """
    try:
        import fcntl
    except ImportError:
        return open(os.devnull)
    lock = open(os.path.join(BASE_DIR, "pendientes", f".{SUBDOMAIN}.lock"), "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lock.close()
        return None
    return lock


def mueve_a(carpeta, ruta, correo):
    """
    Guarda el correo actualizado y mueve su fichero de pendientes/ a carpeta (enviados/ o fallidos/).
    """
    os.makedirs(carpeta, exist_ok=True)
    guarda_json(ruta, correo)
    os.replace(ruta, os.path.join(carpeta, os.path.basename(ruta)))


def registra_envio(ruta, correo):
    correo["enviado"] = datetime.now().isoformat(timespec="seconds")
    mueve_a(dir_enviados(BASE_DIR, SUBDOMAIN), ruta, correo)


def registra_fallo(ruta, correo, error):
    correo["intentos"] = correo.get("intentos", 0) + 1
    correo["ultimo_error"] = str(error)
    if correo["intentos"] >= MAX_INTENTOS:
        mueve_a(dir_fallidos(BASE_DIR, SUBDOMAIN), ruta, correo)
        print(f"  -> {MAX_INTENTOS} intentos fallidos, movido a fallidos/")
    else:
        guarda_json(ruta, correo)


def main():
    carpeta = dir_pendientes(BASE_DIR, SUBDOMAIN)
    os.makedirs(carpeta, exist_ok=True)
    lock = bloquea_ejecucion()
    if lock is None:
        print("Ya hay otro envío de correos en marcha para '" + SUBDOMAIN + "'. Salgo.")
        return 0

    ficheros = sorted(f for f in os.listdir(carpeta) if f.endswith(".json"))
    if SOLO_INFORMES:
        ficheros = [f for f in ficheros if f.startswith(TIPO_INFORME)]
    print(f"Correos pendientes en {carpeta}: {len(ficheros)}")
    if len(ficheros) > MAX_CORREOS_POR_EJECUCION:
        print(f"Sólo se enviarán {MAX_CORREOS_POR_EJECUCION}; el resto queda para la siguiente ejecución.")

    enviados = 0
    fallidos = 0
    server = None
    try:
        for i, nombre in enumerate(ficheros[:MAX_CORREOS_POR_EJECUCION]):
            ruta = os.path.join(carpeta, nombre)
            if i > 0 and not DRY_RUN:
                time.sleep(PAUSA_ENTRE_CORREOS)
            try:
                with open(ruta, encoding="utf-8") as f:
                    correo = json.load(f)
            except Exception as e:
                print(f"No se puede leer {nombre}: {e}")
                fallidos += 1
                continue
            destinatario = correo["destinatario"]
            print(f"- {nombre} -> '{destinatario}' ({correo['plantilla']})")
            try:
                html = renderiza_plantilla(correo["plantilla"], correo["contexto"])
                if DRY_RUN:
                    print("  [DRY-RUN] No se envía.")
                    continue
                msg = construye_mensaje(SMTP_USER, destinatario, correo["asunto"], html, correo.get("adjuntos", []))
                # un reintento por si la conexión reutilizada ha caducado
                for intento in range(2):
                    try:
                        if server is None:
                            server = conecta()
                        server.send_message(msg)
                        break
                    except Exception:
                        try:
                            if server is not None:
                                server.close()
                        except Exception:
                            pass
                        server = None
                        if intento == 1:
                            raise
            except Exception as e:
                print(f"  Error al enviar el correo a '{destinatario}': {e}")
                fallidos += 1
                registra_fallo(ruta, correo, e)
                continue
            registra_envio(ruta, correo)
            enviados += 1
    finally:
        if server is not None:
            try:
                server.quit()
            except Exception:
                pass
        lock.close()

    print(f"Enviados: {enviados}. Con fallo: {fallidos}. "
          f"Quedan pendientes: {len([f for f in os.listdir(carpeta) if f.endswith('.json')])}.")
    return 1 if fallidos else 0


if __name__ == "__main__":
    sys.exit(main())
