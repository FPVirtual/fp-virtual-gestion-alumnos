"""Tests para el sistema de plantillas de email (Jinja2).

Validan la herencia de base.html (preheader oculto, pie, logo),
el autoescape de valores de SIGAD y la incrustación del logo
como imagen relacionada (cid:) en los emails enviados.
"""

from gestion_alumnos.repositories import email_repository
from gestion_alumnos.repositories.email_repository import EmailRepositoryImpl
from gestion_alumnos.utils.plantillas import logo_disponible, renderizar_plantilla

CONTEXTO_BASE = {
    "subdomain": "test",
    "nombre": "Juan",
    "apellidos": "Pérez García",
    "email": "juan@ejemplo.com",
    "usuario": "12345678a",
    "contrasena": "secreta",
    "matriculado_en": ["PROG", "BD"],
}


class TestRenderizadoPlantillas:
    """Valida la estructura común heredada de base.html."""

    def test_hereda_base_con_preheader_y_pie(self):
        html = renderizar_plantilla(
            "nuevoUsuario.html", logo=True, **CONTEXTO_BASE
        )
        assert "display:none" in html  # preheader oculto
        assert "Preheader" in html or "preheader" in html
        assert "FP virtual Aragón" in html  # pie
        assert "Bienvenido/a a FP virtual Aragón" in html  # título

    def test_preheader_es_personalizado(self):
        html = renderizar_plantilla(
            "matriculasAnadidas.html", logo=True, **CONTEXTO_BASE
        )
        assert (
            "se han añadido nuevas matrículas a su cuenta"
            in html
        )

    def test_logo_incrustado_cuando_disponible(self):
        html = renderizar_plantilla("nuevoUsuario.html", logo=True, **CONTEXTO_BASE)
        assert 'src="cid:logo"' in html

    def test_fallback_texto_cuando_no_hay_logo(self):
        html = renderizar_plantilla("nuevoUsuario.html", logo=False, **CONTEXTO_BASE)
        assert 'src="cid:logo"' not in html
        assert ">FP virtual Aragón</span>" in html

    def test_logo_empaquetado_existe(self):
        assert logo_disponible() is True


class TestAutoescapeJinja:
    """El autoescape de Jinja2 protege contra inyección HTML."""

    def test_escapa_nombre_con_script(self):
        contexto = {**CONTEXTO_BASE, "nombre": "Juan <script>alert(1)</script>"}
        html = renderizar_plantilla("nuevoUsuario.html", logo=True, **contexto)
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html

    def test_escapa_matriculas(self):
        contexto = {**CONTEXTO_BASE, "matriculado_en": ["<b>PROG</b>"]}
        html = renderizar_plantilla("matriculasAnadidas.html", logo=True, **contexto)
        assert "<li>&lt;b&gt;PROG&lt;/b&gt;</li>" in html

    def test_matriculas_como_lista(self):
        html = renderizar_plantilla("nuevoUsuario.html", logo=True, **CONTEXTO_BASE)
        assert "<li>PROG</li>" in html
        assert "<li>BD</li>" in html


class FakeSMTP:
    """Mock de smtplib.SMTP que captura el mensaje enviado."""

    ultimo_mensaje = None

    def __init__(self, *args, **kwargs):
        pass

    def starttls(self, context=None):
        pass

    def login(self, user, password):
        pass

    def send_message(self, msg):
        FakeSMTP.ultimo_mensaje = msg

    def quit(self):
        pass

    def close(self):
        pass


class TestLogoIncrustado:
    """El logo se adjunta como imagen relacionada con cid <logo>."""

    def test_envio_adjunta_logo(self, monkeypatch, settings_test):
        monkeypatch.setattr(
            email_repository.smtplib, "SMTP", FakeSMTP
        )
        repo = EmailRepositoryImpl(settings_test)
        html = renderizar_plantilla("nuevoUsuario.html", logo=True, **CONTEXTO_BASE)
        assert repo._enviar("dest@ejemplo.com", "Asunto", html)

        msg = FakeSMTP.ultimo_mensaje
        imagenes = [
            p
            for p in msg.walk()
            if p.get_content_type() == "image/png"
        ]
        assert len(imagenes) == 1
        assert imagenes[0]["Content-ID"] == "<logo>"
        assert imagenes[0].get_filename() == "logo.png"
        assert imagenes[0].get_payload(decode=True).startswith(b"\x89PNG")
