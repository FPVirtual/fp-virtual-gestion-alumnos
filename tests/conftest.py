import os
import json
from dotenv import load_dotenv
from pathlib import Path
import pytest
from gestion_alumnos.models import Registro

# Si se ha marcado entorno «test», cargamos .env.test
if os.getenv("APP_ENV") == "test":
    load_dotenv(dotenv_path=".env.test", override=True)

# Ruta base al fichero de prueba
TEST_FILE = Path(__file__).parent / "data" / "estudiantes_0001.json"

@pytest.fixture
def sample_json_dict() -> dict:
    """Diccionario python del JSON de test."""
    with TEST_FILE.open(encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture
def sample_registro(sample_json_dict) -> Registro:
    """Modelo Registro ya parseado."""
    from utils.parser import parse_json
    return parse_json(sample_json_dict)