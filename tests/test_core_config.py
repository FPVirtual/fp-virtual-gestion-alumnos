"""
Tests para el módulo de configuración.
"""

import pytest
from pathlib import Path

from gestion_alumnos.core.config import Settings


class TestSettings:
    """Tests para la clase Settings."""
    
    def test_default_values(self):
        """Test que los valores por defecto sean correctos."""
        settings = Settings()
        
        assert settings.environment == "dev"
        assert settings.subdomain == "test"
        assert settings.smtp_port == 587
        assert settings.db_port == 3306
    
    def test_environment_detection(self):
        """Test de detección de entornos."""
        # Producción
        prod = Settings(environment="produccion", subdomain="www")
        assert prod.is_produccion is True
        assert prod.is_test is False
        
        # Test
        test = Settings(environment="test")
        assert test.is_test is True
        assert test.is_produccion is False
    
    def test_email_limit_by_environment(self):
        """Test que el límite de emails varía según el entorno."""
        prod = Settings(subdomain="www")
        assert prod.email_limit == 1000
        
        dev = Settings(subdomain="test")
        assert dev.email_limit == 10
    
    def test_report_to_parsing(self):
        """Test del parsing de emails de reporte."""
        settings = Settings(report_to="a@b.com c@d.com")
        assert settings.report_to == ["a@b.com", "c@d.com"]
    
    def test_path_parsing(self):
        """Test de conversión de strings a Path."""
        settings = Settings(data_dir="/tmp/data")
        assert isinstance(settings.data_dir, Path)
        assert settings.data_dir == Path("/tmp/data")


class TestSettingsValidation:
    """Tests de validación de Settings."""
    
    def test_valid_environment_values(self):
        """Test que solo se acepten valores válidos para environment."""
        # Valores válidos
        for env in ["test", "dev", "preproduccion", "produccion"]:
            settings = Settings(environment=env)
            assert settings.environment == env
        
        # Valor inválido debería fallar
        with pytest.raises(Exception):
            Settings(environment="invalido")
