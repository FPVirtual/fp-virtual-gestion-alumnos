import multiprocessing
import os
import queue
import smtplib
import ssl
from email.message import EmailMessage


def _construye_mensaje(remitente, destinatario, asunto, html, adjuntos, imagenes):
    msg = EmailMessage()
    msg['Subject'] = asunto
    msg['From'] = remitente
    msg['To'] = destinatario
    msg.set_content("Tu cliente no soporta HTML.")   # parte de texto plano
    msg.add_alternative(html, subtype='html')        # parte HTML
    # imágenes incrustadas: el HTML las referencia como cid:<clave>
    for cid, ruta in imagenes.items():
        try:
            with open(ruta, 'rb') as f:
                subtipo = os.path.splitext(ruta)[1].lstrip('.').lower().replace('jpg', 'jpeg')
                msg.get_body(('html',)).add_related(f.read(), maintype='image', subtype=subtipo, cid=f"<{cid}>")
        except Exception as e:
            print(f"Error al incrustar {ruta}: {e}")
    for ruta in adjuntos:
        try:
            with open(ruta, 'rb') as f:
                msg.add_attachment(f.read(), maintype='application', subtype='octet-stream',
                                   filename=os.path.basename(ruta))
        except Exception as e:
            print(f"Error al adjuntar {ruta}: {e}")
    return msg


def _conecta(host, port, user, password):
    server = smtplib.SMTP(host, port)
    server.starttls(context=ssl.create_default_context())
    server.login(user, password)
    return server


def _worker(cola, resultados, host, port, user, password):
    """
    Proceso hijo: va sacando correos de la cola y los envía reutilizando una única conexión SMTP.
    Por cada correo devuelve (destinatario, enviado). Al recibir None termina y avisa con ("fin", None).
    """
    server = None
    while True:
        item = cola.get()
        if item is None:
            break
        destinatario = item["destinatario"]
        enviado = False
        # un reintento por si la conexión reutilizada ha caducado
        for _ in range(2):
            try:
                if server is None:
                    server = _conecta(host, port, user, password)
                msg = _construye_mensaje(user, destinatario, item["asunto"], item["html"], item["adjuntos"], item["imagenes"])
                server.send_message(msg)
                enviado = True
                break
            except Exception as e:
                print(f"Error al enviar el correo a '{destinatario}': {e}")
                try:
                    if server is not None:
                        server.close()
                except Exception:
                    pass
                server = None
        resultados.put((destinatario, enviado))
    if server is not None:
        try:
            server.quit()
        except Exception:
            pass
    resultados.put(("fin", None))


class ColaCorreo:
    """
    Envía los correos desde un proceso aparte para no frenar el proceso principal.
    - enviar() sólo encola y vuelve al instante (arranca el proceso la primera vez).
    - cerrar() espera a que se vacíe la cola y devuelve la lista de destinatarios cuyo envío falló.
    Después de cerrar() se puede volver a usar enviar(): arrancará un proceso nuevo.
    """

    def __init__(self, host, port, user, password):
        self._config = (host, port, user, password)
        self._proceso = None
        self._cola = None
        self._resultados = None
        self._encolados = 0

    def enviar(self, destinatario, asunto, html, adjuntos=(), imagenes=None):
        if self._proceso is None:
            self._cola = multiprocessing.Queue()
            self._resultados = multiprocessing.Queue()
            self._proceso = multiprocessing.Process(
                target=_worker, args=(self._cola, self._resultados) + self._config, daemon=True)
            self._proceso.start()
            self._encolados = 0
        self._cola.put({"destinatario": destinatario, "asunto": asunto, "html": html, "adjuntos": list(adjuntos), "imagenes": dict(imagenes or {})})
        self._encolados += 1

    def cerrar(self):
        """
        Espera a que se envíen todos los correos encolados. Devuelve la lista de destinatarios con fallo
        (incluye los que se pierdan si el proceso muriera antes de tiempo).
        """
        if self._proceso is None:
            return []
        self._cola.put(None)
        recibidos = 0
        fallos = []
        while True:
            try:
                destinatario, enviado = self._resultados.get(timeout=1)
            except queue.Empty:
                if not self._proceso.is_alive():
                    break
                continue
            if destinatario == "fin":
                break
            recibidos += 1
            if not enviado:
                fallos.append(destinatario)
        self._proceso.join()
        fallos.extend(["(desconocido)"] * (self._encolados - recibidos))
        self._proceso = None
        return fallos
