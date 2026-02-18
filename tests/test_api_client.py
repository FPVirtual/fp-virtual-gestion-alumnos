import json
import os
import pytest
from unittest import mock
from datetime import datetime

from gestion_alumnos.utils.api_client import solicitar_datos, obtener_estudiantes, main


###############################################################################
# Fixtures
###############################################################################
@pytest.fixture
def fake_creds(monkeypatch):
    """Exporta credenciales falsas para los tests que las necesiten."""
    monkeypatch.setenv("API_USER", "test_user")
    monkeypatch.setenv("API_PASSWORD", "test_pass")


@pytest.fixture
def fake_estudiantes_dict():
    return {"alumnos": [{"id": 1, "nombre": "Alumno 1"}, {"id": 2, "nombre": "Alumno 2"}]}


###############################################################################
# Tests de solicitar_datos
###############################################################################
def test_solicitar_datos_ok(fake_creds, requests_mock):
    """La primera llamada devuelve idSolicitud sin problemas."""
    requests_mock.get(
        f"https://aplicaciones.aragon.es/pcrpe/services/alumnosFPDistancia/solicitud/{datetime.now().year}",
        json={"codigo": 0, "idSolicitud": 1234},
    )
    data = solicitar_datos("test_user", "test_pass")
    assert data == {"codigo": 0, "idSolicitud": 1234}


def test_solicitar_datos_error(fake_creds, requests_mock):
    """La API devuelve codigo != 0 → ValueError."""
    requests_mock.get(
        "https://aplicaciones.aragon.es/pcrpe/services/alumnosFPDistancia"
        f"/solicitud/{datetime.now().year}",
        json={"codigo": 99, "mensaje": "Credenciales inválidas"},
    )
    with pytest.raises(ValueError, match="Credenciales inválidas"):
        solicitar_datos("test_user", "test_pass")


###############################################################################
# Tests de obtener_estudiantes
###############################################################################
def test_obtener_estudiantes_ok(fake_creds, requests_mock, fake_estudiantes_dict):
    """El fichero está listo en el primer intento."""
    requests_mock.get(
        "https://aplicaciones.aragon.es/pcrpe/services/alumnosFPDistancia/fichero/1234",
        json={"codigo": 0, "estudiantes": json.dumps(fake_estudiantes_dict)},
    )
    data = obtener_estudiantes("test_user", "test_pass", 1234, reintentos=2, espera=0.01)
    assert data == fake_estudiantes_dict


def test_obtener_estudiantes_reintento_exito(fake_creds, requests_mock, fake_estudiantes_dict):
    """Dos intentos: primero -1, segundo 0 → éxito."""
    url = "https://aplicaciones.aragon.es/pcrpe/services/alumnosFPDistancia/fichero/1234"
    # 1ª respuesta: no listo
    requests_mock.get(url, [{"json": {"codigo": -1, "mensaje": "No listo"}},
                           {"json": {"codigo": 0, "estudiantes": json.dumps(fake_estudiantes_dict)}}])
    data = obtener_estudiantes("test_user", "test_pass", 1234, reintentos=3, espera=0.01)
    assert data == fake_estudiantes_dict


def test_obtener_estudiantes_reintento_agotado(fake_creds, requests_mock):
    """Siempre codigo -1 → TimeoutError."""
    url = "https://aplicaciones.aragon.es/pcrpe/services/alumnosFPDistancia/fichero/1234"
    requests_mock.get(url, json={"codigo": -1, "mensaje": "Aún procesando"})
    with pytest.raises(TimeoutError, match="Se agotaron los reintentos"):
        obtener_estudiantes("test_user", "test_pass", 1234, reintentos=2, espera=0.01)


def test_obtener_estudiantes_error_definitivo(fake_creds, requests_mock):
    """codigo 99 → ValueError."""
    url = "https://aplicaciones.aragon.es/pcrpe/services/alumnosFPDistancia/fichero/1234"
    requests_mock.get(url, json={"codigo": 99, "mensaje": "Error interno"})
    with pytest.raises(ValueError, match="Error interno"):
        obtener_estudiantes("test_user", "test_pass", 1234)


###############################################################################
# Test del flujo completo (main)
###############################################################################
def test_main_exito(fake_creds, requests_mock, fake_estudiantes_dict, tmp_path, monkeypatch):
    """Flujo completo: solicitar id, reintento, guardar json."""
    # Parchamos DATA_DIR para que use tmp_path en lugar de la ruta real
    monkeypatch.setattr("gestion_alumnos.utils.api_client.DATA_DIR", tmp_path)
    # 1) solicitar id
    requests_mock.get(
        f"https://aplicaciones.aragon.es/pcrpe/services/alumnosFPDistancia"
        f"/solicitud/{datetime.now().year}",
        json={"codigo": 0, "idSolicitud": 5555},
    )
    # 2) obtener fichero (necesita 2 intentos)
    url_fich = "https://aplicaciones.aragon.es/pcrpe/services/alumnosFPDistancia/fichero/5555"
    requests_mock.get(url_fich, [{"json": {"codigo": -1, "mensaje": "No listo"}},
                                {"json": {"codigo": 0,
                                        "estudiantes": json.dumps(fake_estudiantes_dict)}}])
    main()
    # Comprobaciones
    saved = tmp_path / "estudiantes_5555.json"
    assert saved.exists()
    assert json.loads(saved.read_text()) == fake_estudiantes_dict


def test_main_sin_credenciales(monkeypatch, caplog):
    """Sin API_USER / API_PASSWORD debe terminar sin llamar a la API."""
    monkeypatch.delenv("API_USER", raising=False)
    monkeypatch.delenv("API_PASSWORD", raising=False)
    with mock.patch("gestion_alumnos.utils.api_client.solicitar_datos") as mock_sol:
        main()
    mock_sol.assert_not_called()
    assert "Faltan API_USER y/o API_PASSWORD" in caplog.text