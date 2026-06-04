"""Implementación de EstudianteRepository para SIGAD.

Obtiene datos de estudiantes desde la API de SIGAD con manejo
de reintentos, caching y modo test.
"""

import json
import time
from pathlib import Path

import requests

from gestion_alumnos.core.config import Settings
from gestion_alumnos.core.exceptions import APIError, APITimeoutError
from gestion_alumnos.core.logging import get_logger
from gestion_alumnos.models import Registro

logger = get_logger(__name__)


class SIGADRepository:
    """Repositorio de estudiantes que consume la API de SIGAD.

    Soporta:
    - Modo test: usa archivos JSON locales.
    - Modo producción: consume API REST con reintentos.
    - Caché de archivos descargados.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        """Inicializa el repositorio.

        Args:
            settings: Configuración del sistema (usa global si None).
        """
        self._settings = settings or Settings()
        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/json",
            "User-Agent": "fpdistancia-client/2.0",
        })
        self._settings.data_dir.mkdir(parents=True, exist_ok=True)

    def obtener_registro(self) -> Registro:
        """Obtiene el registro completo de estudiantes.

        En modo test: carga desde archivo local.
        En otros modos: descarga desde API SIGAD.

        Returns:
            Registro con todos los alumnos matriculados.

        Raises:
            APIError: Si hay errores en la comunicación.
            FileNotFoundError: Si no hay datos disponibles.
        """
        if self._settings.is_test:
            return self._cargar_desde_test()
        return self._descargar_desde_api()

    def buscar_por_documento(self, documento: str) -> Alumno | None:
        """Busca un alumno por documento en el registro más reciente."""
        registro = self.obtener_registro()
        return registro.buscar_por_documento(documento)

    def _cargar_desde_test(self) -> Registro:
        """Carga datos desde archivo de test."""
        test_file = (
            Path(__file__).resolve().parent.parent / "tests" / "data" /
            "test_estudiantes_data.json"
        )
        if not test_file.exists():
            raise FileNotFoundError(f"Archivo de test no encontrado: {test_file}")
        logger.info("Modo test: cargando datos desde archivo local")
        with open(test_file, "r", encoding="utf-8") as f:
            datos = json.load(f)
        registro = Registro.model_validate(datos)
        logger.info(f"Datos de test cargados: {registro.total_alumnos} alumnos")
        return registro

    def _descargar_desde_api(self) -> Registro:
        """Descarga datos desde API SIGAD con reintentos."""
        if not self._settings.api_user or not self._settings.api_password:
            raise APIError("Faltan credenciales API (API_USER, API_PASSWORD)")
        id_solicitud = self._solicitar_datos()
        time.sleep(3)
        datos = self._obtener_estudiantes_con_reintentos(id_solicitud)
        self._guardar_copia_local(datos, id_solicitud)
        return Registro.model_validate(datos)

    def _solicitar_datos(self) -> int:
        """Realiza la solicitud inicial y devuelve el idSolicitud."""
        anio_actual = time.localtime().tm_year
        url = f"{self._settings.api_base_url}/solicitud/{anio_actual}"
        headers = {
            "usuario": self._settings.api_user,
            "password": self._settings.api_password,
        }
        try:
            logger.info(f"Solicitando datos a SIGAD: {url}")
            response = self._session.get(
                url, headers=headers, timeout=self._settings.api_timeout
            )
            response.raise_for_status()
            data = response.json()
            if data.get("codigo") != 0:
                raise APIError(
                    f"Error en solicitud: {data.get('mensaje', 'Desconocido')}",
                    respuesta=str(data),
                )
            id_solicitud = data["idSolicitud"]
            logger.info(f"Solicitud aceptada, idSolicitud: {id_solicitud}")
            return id_solicitud
        except requests.Timeout:
            raise APITimeoutError(f"Timeout en solicitud a {url}")
        except requests.RequestException as e:
            raise APIError(f"Error de conexión: {e}")

    def _obtener_estudiantes_con_reintentos(self, id_solicitud: int) -> dict:
        """Obtiene los estudiantes con lógica de reintentos."""
        url = f"{self._settings.api_base_url}/fichero/{id_solicitud}"
        headers = {
            "usuario": self._settings.api_user,
            "password": self._settings.api_password,
        }
        max_retries = self._settings.api_max_retries
        delay = self._settings.api_retry_delay
        for intento in range(1, max_retries + 1):
            try:
                logger.debug(
                    f"Intento {intento}/{max_retries}: descargando estudiantes"
                )
                response = self._session.get(
                    url, headers=headers, timeout=self._settings.api_timeout
                )
                response.raise_for_status()
                data = response.json()
                codigo = data.get("codigo")
                if codigo == 0:
                    estudiantes = json.loads(data["estudiantes"])
                    total = len(estudiantes.get("alumnos", []))
                    logger.info(f"Datos recibidos: {total} estudiantes")
                    return estudiantes
                if codigo == -1 and intento < max_retries:
                    logger.debug(f"Fichero no listo, esperando {delay}s...")
                    time.sleep(delay)
                    continue
                raise APIError(
                    f"Error descargando estudiantes: {data.get('mensaje')}",
                    respuesta=str(data),
                )
            except requests.Timeout:
                if intento == max_retries:
                    raise APITimeoutError(
                        f"Timeout después de {max_retries} intentos"
                    )
                time.sleep(delay)
            except requests.RequestException as e:
                raise APIError(f"Error de conexión: {e}")
        raise APIError(
            "No se pudo obtener los datos después de todos los reintentos"
        )

    def _guardar_copia_local(self, datos: dict, id_solicitud: int) -> None:
        """Guarda una copia local del JSON descargado."""
        fichero = self._settings.data_dir / f"estudiantes_{id_solicitud}.json"
        with open(fichero, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        logger.info(f"Copia local guardada: {fichero}")
        if self._settings.is_produccion:
            self._limpiar_archivos_antiguos(fichero)

    def _limpiar_archivos_antiguos(self, fichero_actual: Path) -> None:
        """Elimina archivos JSON antiguos excepto el actual."""
        for f in self._settings.data_dir.glob("*.json"):
            if f != fichero_actual:
                f.unlink(missing_ok=True)
                logger.debug(f"Archivo antiguo eliminado: {f}")
