"""Tests para SIGADRepository.

Verifica:
- Descarga de datos desde API SIGAD con requests_mock
- Parseo correcto a modelo Registro
- Modo test desde archivo local
- Lógica de reintentos
"""

import json

import pytest
import requests_mock

from gestion_alumnos.core.config import Settings
from gestion_alumnos.core.exceptions import APIError
from gestion_alumnos.models import Registro
from gestion_alumnos.repositories.sigad_repository import SIGADRepository


class TestSIGADRepository:
    """Tests de integración para SIGADRepository."""

    def test_obtener_registro_desde_api(self, monkeypatch):
        """Test completo: solicitud + descarga + parseo."""
        monkeypatch.setenv("ENVIRONMENT", "dev")
        monkeypatch.setenv("API_USER", "test_user")
        monkeypatch.setenv("API_PASSWORD", "test_pass")

        settings = Settings()
        repo = SIGADRepository(settings)

        anio_actual = __import__("time").localtime().tm_year
        base_url = settings.api_base_url
        datos_estudiantes = {
            "fecha": "15/12/2025",
            "hora": "11:42:28",
            "alumnos": [
                {
                    "idAlumno": 16839,
                    "idTipoDocumento": 1,
                    "documento": "78842153Q",
                    "nombre": "Valeria",
                    "apellido1": "Torres",
                    "apellido2": "Medina",
                    "email": "valeria.torres.medina@ejemplo.com",
                    "centros": [
                        {
                            "codigoCentro": "50009348",
                            "centro": "AVEMPACE",
                            "ciclos": [
                                {
                                    "idFicha": 22,
                                    "codigoCiclo": "12242301",
                                    "ciclo": "Educación Infantil (Formación Profesional)",
                                    "siglasCiclo": "SSC302",
                                    "modulos": [
                                        {
                                            "idMateria": 18599,
                                            "modulo": "Itinerario personal para la empleabilidad I ( Virtual )",
                                            "siglasModulo": "IPPE1"
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        with requests_mock.Mocker() as m:
            # 1. Mock solicitud inicial
            m.get(
                f"{base_url}/solicitud/{anio_actual}",
                json={"codigo": 0, "mensaje": "OK", "idSolicitud": 1047},
            )
            # 2. Mock descarga de estudiantes
            m.get(
                f"{base_url}/fichero/1047",
                json={
                    "codigo": 0,
                    "mensaje": "OK",
                    "estudiantes": json.dumps(datos_estudiantes),
                },
            )

            registro = repo.obtener_registro()

        assert isinstance(registro, Registro)
        assert registro.total_alumnos == 1
        assert registro.fecha == "15/12/2025"

        alumno = registro.alumnos[0]
        assert alumno.nombre == "Valeria"
        assert alumno.documento == "78842153Q"
        assert alumno.username_moodle == "78842153q"
        assert alumno.email_institucional == "78842153q@fpvirtualaragon.es"

        # Validar estructura anidada
        assert len(alumno.centros) == 1
        assert alumno.centros[0].nombre == "AVEMPACE"
        assert len(alumno.centros[0].ciclos) == 1
        assert alumno.centros[0].ciclos[0].siglas == "SSC302"
        assert len(alumno.centros[0].ciclos[0].modulos) == 1
        assert alumno.centros[0].ciclos[0].modulos[0].siglas == "IPPE1"

        # Validar utilidad de búsqueda
        encontrado = registro.buscar_por_documento("78842153Q")
        assert encontrado is not None
        assert encontrado.nombre == "Valeria"
        assert registro.buscar_por_documento("00000000A") is None

    def test_obtener_registro_desde_test(self, monkeypatch):
        """Test modo test: carga desde archivo local."""
        monkeypatch.setenv("ENVIRONMENT", "test")

        settings = Settings()
        repo = SIGADRepository(settings)
        registro = repo.obtener_registro()

        assert isinstance(registro, Registro)
        assert registro.total_alumnos == 2

        # Validar primer alumno
        a1 = registro.alumnos[0]
        assert a1.nombre == "Valeria"
        assert a1.documento == "78842153Q"

        # Validar segundo alumno
        a2 = registro.alumnos[1]
        assert a2.nombre == "Juan"
        assert a2.documento == "12345678A"
        assert len(a2.obtener_todos_modulos()) == 2

    def test_reintentos_api(self, monkeypatch):
        """Test de reintentos cuando la API retorna código -1."""
        monkeypatch.setenv("ENVIRONMENT", "dev")
        monkeypatch.setenv("API_USER", "test_user")
        monkeypatch.setenv("API_PASSWORD", "test_pass")

        settings = Settings(api_retry_delay=0)
        repo = SIGADRepository(settings)
        anio_actual = __import__("time").localtime().tm_year
        base_url = settings.api_base_url

        datos_estudiantes = {
            "fecha": "15/12/2025",
            "hora": "11:42:28",
            "alumnos": []
        }

        with requests_mock.Mocker() as m:
            # Solicitud inicial
            m.get(
                f"{base_url}/solicitud/{anio_actual}",
                json={"codigo": 0, "mensaje": "OK", "idSolicitud": 1048},
            )
            # Primera descarga: aún no listo (-1)
            m.get(
                f"{base_url}/fichero/1048",
                [
                    {"json": {"codigo": -1, "mensaje": "No listo"}},
                    {
                        "json": {
                            "codigo": 0,
                            "mensaje": "OK",
                            "estudiantes": json.dumps(datos_estudiantes),
                        }
                    },
                ],
            )

            registro = repo.obtener_registro()
            assert registro.total_alumnos == 0

    def test_error_credenciales(self, monkeypatch):
        """Test error cuando faltan credenciales."""
        monkeypatch.setenv("ENVIRONMENT", "dev")
        monkeypatch.delenv("API_USER", raising=False)
        monkeypatch.delenv("API_PASSWORD", raising=False)

        settings = Settings()
        repo = SIGADRepository(settings)

        with pytest.raises(APIError, match="Faltan credenciales"):
            repo.obtener_registro()

    def test_buscar_por_documento(self, monkeypatch):
        """Test del método buscar_por_documento."""
        monkeypatch.setenv("ENVIRONMENT", "test")

        settings = Settings()
        repo = SIGADRepository(settings)
        resultado = repo.buscar_por_documento("12345678A")

        assert resultado is not None
        assert resultado.nombre == "Juan"
        assert resultado.apellido1 == "Pérez"

    def test_estructura_completa_json(self, monkeypatch):
        """Valida que el JSON de test tiene la estructura esperada por SIGAD."""
        monkeypatch.setenv("ENVIRONMENT", "test")

        settings = Settings()
        repo = SIGADRepository(settings)
        registro = repo.obtener_registro()

        # Verificar campos obligatorios del JSON original
        assert hasattr(registro, "fecha")
        assert hasattr(registro, "hora")
        assert hasattr(registro, "alumnos")

        for alumno in registro.alumnos:
            assert hasattr(alumno, "id_alumno")
            assert hasattr(alumno, "documento")
            assert hasattr(alumno, "nombre")
            assert hasattr(alumno, "apellido1")
            assert hasattr(alumno, "email")
            assert hasattr(alumno, "centros")

            for centro in alumno.centros:
                assert hasattr(centro, "codigo")
                assert hasattr(centro, "nombre")
                assert hasattr(centro, "ciclos")

                for ciclo in centro.ciclos:
                    assert hasattr(ciclo, "id_ficha")
                    assert hasattr(ciclo, "codigo")
                    assert hasattr(ciclo, "nombre")
                    assert hasattr(ciclo, "siglas")
                    assert hasattr(ciclo, "modulos")

                    for modulo in ciclo.modulos:
                        assert hasattr(modulo, "id_materia")
                        assert hasattr(modulo, "nombre")
                        assert hasattr(modulo, "siglas")
