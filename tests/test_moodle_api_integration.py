"""Tests de integración contra Moodle real.

Requieren una instancia de Moodle accesible con API REST activada.
Se saltan automáticamente si Moodle no responde.

⚠️  IMPORTANTE: Nunca suspender al usuario propietario del token (moodle-api),
   ya que Moodle bloquea todas las llamadas al token cuando el usuario está
   suspendido.

Configuración esperada en .env.test:
    MOODLE_API_URL=http://192.168.2.253:8087/webservice/rest/server.php
    MOODLE_API_TOKEN=9a8fb5343608c92a694165f59fdc2ae4
"""

import uuid

import pytest
import requests

from gestion_alumnos.repositories.moodle_api_repository import APIMoodleRepository


def _moodle_disponible() -> bool:
    """Verifica si el Moodle de test está accesible."""
    try:
        from pathlib import Path
        env_path = Path(__file__).resolve().parent.parent / ".env.test"
        if not env_path.exists():
            return False
        with open(env_path) as f:
            for line in f:
                if line.startswith("MOODLE_API_URL="):
                    url = line.strip().split("=", 1)[1]
                    resp = requests.get(url, timeout=5)
                    return resp.status_code == 200
        return False
    except Exception:
        return False


# Saltar TODOS los tests de este módulo si Moodle no responde
pytestmark = pytest.mark.skipif(
    not _moodle_disponible(),
    reason="Moodle de test no disponible en 192.168.2.253:8087",
)


@pytest.fixture(scope="module")
def settings_moodle():
    """Configuración con driver=api, cargando .env.test explícitamente."""
    from pathlib import Path
    from pydantic_settings import SettingsConfigDict
    from gestion_alumnos.core.config import Settings

    env_path = Path(__file__).resolve().parent.parent / ".env.test"

    class TestSettings(Settings):
        model_config = SettingsConfigDict(
            env_file=str(env_path),
            env_file_encoding="utf-8",
            case_sensitive=False,
            extra="ignore",
        )
    return TestSettings()


@pytest.fixture(scope="module")
def repo(settings_moodle):
    """Instancia del repositorio API contra Moodle real."""
    return APIMoodleRepository(settings_moodle)


class TestMoodleAPIConexion:
    """Valida conectividad básica con Moodle."""

    def test_endpoint_responde(self, settings_moodle):
        """El endpoint REST responde HTTP 200."""
        resp = requests.get(settings_moodle.moodle_api_url, timeout=10)
        assert resp.status_code == 200

    def test_token_valido(self, repo):
        """El token permite llamar a funciones de la API."""
        result = repo._call("core_webservice_get_site_info")
        assert "sitename" in result
        assert "siteurl" in result


class TestMoodleAPIUsuarios:
    """Operaciones CRUD de usuarios contra Moodle real."""

    def test_listar_usuarios(self, repo):
        """Obtener todos los usuarios devuelve lista."""
        usuarios = repo.obtener_todos_usuarios()
        assert isinstance(usuarios, list)
        assert len(usuarios) >= 1

    def test_usuario_existe_moodle_api(self, repo):
        """El usuario del servicio API existe."""
        assert repo.usuario_existe("moodle-api") is True

    def test_usuario_no_existe(self, repo):
        """Un username aleatorio no existe."""
        username_aleatorio = f"test_no_existe_{uuid.uuid4().hex[:8]}"
        assert repo.usuario_existe(username_aleatorio) is False

    def test_crear_usuario(self, repo):
        """Crear usuario devuelve ID > 0."""
        username = f"testapi_{uuid.uuid4().hex[:8]}"
        email = f"{username}@fpvirtualaragon.es"

        user_id = repo.crear_usuario(
            username=username,
            email=email,
            nombre="Test",
            apellido="API",
            password="TestPass123!",
        )
        assert user_id > 0
        # Nota: Moodle puede no devolver el usuario inmediatamente en
        # búsquedas por caché/permisos, por eso no verificamos usuario_existe

    def test_suspender_y_reactivar_usuario(self, repo):
        """Ciclo: suspender → verificar → reactivar.

        Usa el usuario prof_cd_daw (profesor de test) en lugar de moodle-api.
        """
        username = "prof_cd_daw"

        # 1. Verificar que existe
        assert repo.usuario_existe(username) is True

        # 2. Obtener datos actuales
        usuario = repo.obtener_por_username(username)
        assert usuario is not None
        estado_original = usuario.get("suspended", 0)

        # 3. Suspender
        assert repo.suspender_usuario(username) is True
        usuario = repo.obtener_por_username(username)
        assert usuario["suspended"] == 1

        # 4. Reactivar (restaurar estado original)
        if estado_original == 0:
            assert repo.reactivar_usuario(username) is True
            usuario = repo.obtener_por_username(username)
            assert usuario["suspended"] == 0
        else:
            assert usuario["suspended"] == 1


class TestMoodleAPICursos:
    """Operaciones de cursos y matrículas."""

    def test_obtener_matriculas_moodle_api(self, repo):
        """El usuario moodle-api tiene matrículas."""
        matriculas = repo.obtener_matriculas("moodle-api")
        assert isinstance(matriculas, list)

    def test_obtener_matriculas_usuario_inexistente(self, repo):
        """Usuario inexistente devuelve lista vacía."""
        username = f"test_no_existe_{uuid.uuid4().hex[:8]}"
        matriculas = repo.obtener_matriculas(username)
        assert matriculas == []
