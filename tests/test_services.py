"""
Tests para los servicios usando mocks e inyección de dependencias.
"""

from unittest.mock import Mock, MagicMock, patch
import pytest

from gestion_alumnos.models_v2 import Alumno, Registro
from gestion_alumnos.services.gestion_service import (
    GestionAlumnosService,
    ResultadoSync
)


class TestGestionAlumnosService:
    """Tests para el servicio de gestión."""
    
    @pytest.fixture
    def mock_repos(self):
        """Crea mocks de los repositorios."""
        estudiante_repo = Mock()
        moodle_repo = Mock()
        email_repo = Mock()
        
        return {
            "estudiante": estudiante_repo,
            "moodle": moodle_repo,
            "email": email_repo
        }
    
    @pytest.fixture
    def sample_alumno(self):
        """Crea un alumno de ejemplo."""
        return Alumno(
            idAlumno=1,
            idTipoDocumento=1,
            documento="12345678A",
            nombre="Juan",
            apellido1="Pérez",
            apellido2="García",
            email="juan@test.com",
            centros=[]
        )
    
    def test_crear_nuevo_usuario(self, mock_repos, sample_alumno):
        """Test de creación de nuevo usuario."""
        service = GestionAlumnosService(
            estudiante_repo=mock_repos["estudiante"],
            moodle_repo=mock_repos["moodle"],
            email_repo=mock_repos["email"]
        )
        
        resultado = ResultadoSync()
        
        # Configurar mocks
        mock_repos["moodle"].crear_usuario.return_value = 1234
        mock_repos["email"].limite_alcanzado.return_value = False
        mock_repos["email"].enviar_bienvenida_nuevo_usuario.return_value = True
        
        # Ejecutar
        service._crear_nuevo_usuario(sample_alumno, resultado)
        
        # Verificar
        assert resultado.nuevos_creados == 1
        mock_repos["moodle"].crear_usuario.assert_called_once()
        mock_repos["moodle"].matricular_en_cohorte.assert_called_with(
            "12345678a", "alumnado"
        )
    
    def test_sincronizacion_completa(self, mock_repos, sample_alumno):
        """Test de sincronización completa."""
        # Configurar registro de SIGAD
        registro = Registro(
            fecha="01/01/2025",
            hora="12:00:00",
            alumnos=[sample_alumno]
        )
        
        mock_repos["estudiante"].obtener_registro.return_value = registro
        mock_repos["moodle"].obtener_todos_usuarios.return_value = []
        mock_repos["moodle"].crear_usuario.return_value = 1234
        mock_repos["email"].limite_alcanzado.return_value = True  # Skip emails
        
        # Crear servicio
        service = GestionAlumnosService(
            estudiante_repo=mock_repos["estudiante"],
            moodle_repo=mock_repos["moodle"],
            email_repo=mock_repos["email"]
        )
        
        # Ejecutar
        resultado = service.ejecutar_sincronizacion_completa()
        
        # Verificar
        assert resultado.alumnos_procesados == 1
        assert resultado.nuevos_creados == 1
        assert resultado.exito is True
    
    def test_procesar_bajas(self, mock_repos, sample_alumno):
        """Test de procesamiento de bajas."""
        # Usuario en Moodle pero no en SIGAD
        usuarios_moodle = {
            "99999999Z": {
                "id": 100,
                "username": "99999999Z",
                "suspended": 0
            }
        }
        
        mock_repos["moodle"].es_usuario_protegido.return_value = False
        mock_repos["moodle"].suspender_usuario.return_value = True
        
        service = GestionAlumnosService(
            estudiante_repo=mock_repos["estudiante"],
            moodle_repo=mock_repos["moodle"]
        )
        
        registro = Registro(
            fecha="01/01/2025",
            hora="12:00:00",
            alumnos=[sample_alumno]  # Solo el sample_alumno
        )
        
        resultado = ResultadoSync()
        service._procesar_bajas(registro, usuarios_moodle, resultado)
        
        # 99999999Z no está en SIGAD, debería suspenderse
        assert resultado.suspendidos == 1
        mock_repos["moodle"].suspender_usuario.assert_called_with("99999999Z")
    
    def test_no_suspender_usuarios_protegidos(self, mock_repos, sample_alumno):
        """Test que no se suspendan usuarios protegidos."""
        usuarios_moodle = {
            "admin": {
                "id": 1,  # ID protegido
                "username": "admin",
                "suspended": 0
            }
        }
        
        mock_repos["moodle"].es_usuario_protegido.return_value = True
        
        service = GestionAlumnosService(
            estudiante_repo=mock_repos["estudiante"],
            moodle_repo=mock_repos["moodle"]
        )
        
        registro = Registro(
            fecha="01/01/2025",
            hora="12:00:00",
            alumnos=[]  # Sin alumnos
        )
        
        resultado = ResultadoSync()
        service._procesar_bajas(registro, usuarios_moodle, resultado)
        
        # No debería suspender usuarios protegidos
        assert resultado.suspendidos == 0
        mock_repos["moodle"].suspender_usuario.assert_not_called()


class TestContainerDI:
    """Tests para el container de inyección de dependencias."""
    
    def test_container_lazy_loading(self):
        """Test que las dependencias se cargan lazy."""
        from gestion_alumnos.core.container import DIContainer
        
        container = DIContainer()
        
        # Al inicio no hay repos cargados
        assert container._estudiante_repo is None
        assert container._moodle_repo is None
        
        # Al acceder se cargan
        repo = container.estudiante_repository()
        assert container._estudiante_repo is not None
    
    def test_container_override(self):
        """Test de reemplazo de dependencias para tests."""
        from gestion_alumnos.core.container import DIContainer
        
        container = DIContainer()
        
        # Crear mock
        mock_repo = Mock()
        mock_repo.obtener_registro.return_value = Registro(
            fecha="01/01/2025",
            hora="12:00:00",
            alumnos=[]
        )
        
        # Reemplazar
        container.override_estudiante_repository(mock_repo)
        
        # Verificar que se usa el mock
        assert container.estudiante_repository() is mock_repo
