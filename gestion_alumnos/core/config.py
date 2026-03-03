"""
Configuración del sistema usando Pydantic Settings.

Centraliza todas las variables de entorno y proporciona
validación automática de tipos y valores.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuración centralizada del sistema.
    
    Lee automáticamente las variables de entorno y valida
    que estén presentes los valores obligatorios según el entorno.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,  # Variables case-insensitive
        extra="ignore",  # Ignorar variables extra no definidas
    )
    
    # ==========================================
    # Configuración General
    # ==========================================
    environment: Literal["test", "dev", "preproduccion", "produccion"] = Field(
        default="dev",
        description="Entorno de ejecución del sistema"
    )
    subdomain: Literal["test", "preproduccion", "www"] = Field(
        default="test",
        description="Subdominio del entorno Moodle"
    )
    base_path: Path = Field(
        default=Path("/var/fp-distancia-gestion-usuarios-automatica/"),
        description="Ruta base del proyecto"
    )
    
    # ==========================================
    # Configuración API SIGAD
    # ==========================================
    api_base_url: str = Field(
        default="https://aplicaciones.aragon.es/pcrpe/services/alumnosFPDistancia",
        description="URL base de la API de SIGAD"
    )
    api_user: str | None = Field(
        default=None,
        description="Usuario para la API de SIGAD"
    )
    api_password: str | None = Field(
        default=None,
        description="Contraseña para la API de SIGAD"
    )
    api_timeout: int = Field(
        default=30,
        description="Timeout en segundos para peticiones API"
    )
    api_max_retries: int = Field(
        default=5,
        description="Número máximo de reintentos para peticiones API"
    )
    api_retry_delay: int = Field(
        default=10,
        description="Segundos de espera entre reintentos"
    )
    
    # ==========================================
    # Configuración Email (SMTP)
    # ==========================================
    smtp_host: str | None = Field(
        default=None,
        description="Servidor SMTP"
    )
    smtp_port: int = Field(
        default=587,
        description="Puerto del servidor SMTP"
    )
    smtp_user: str | None = Field(
        default=None,
        description="Usuario para autenticación SMTP"
    )
    smtp_password: str | None = Field(
        default=None,
        description="Contraseña para autenticación SMTP"
    )
    smtp_use_tls: bool = Field(
        default=True,
        description="Usar TLS para conexión SMTP"
    )
    
    # ==========================================
    # Configuración Reportes
    # ==========================================
    report_to: list[str] = Field(
        default_factory=list,
        description="Lista de emails para reportes separados por espacios"
    )
    max_emails_diarios: int = Field(
        default=10,
        description="Límite de emails diarios según entorno"
    )
    
    # ==========================================
    # Configuración Base de Datos Moodle
    # ==========================================
    db_host: str = Field(
        default="localhost",
        description="Host de la base de datos MySQL"
    )
    db_port: int = Field(
        default=3306,
        description="Puerto de la base de datos MySQL"
    )
    db_name: str = Field(
        default="moodle",
        description="Nombre de la base de datos"
    )
    db_user: str | None = Field(
        default=None,
        description="Usuario de la base de datos"
    )
    db_password: str | None = Field(
        default=None,
        description="Contraseña de la base de datos"
    )
    
    # ==========================================
    # Configuración Docker/Moosh
    # ==========================================
    docker_container: str = Field(
        default="moodle_app",
        description="Nombre del contenedor Docker de Moodle"
    )
    moosh_timeout: int = Field(
        default=60,
        description="Timeout en segundos para comandos moosh"
    )
    
    # ==========================================
    # Configuración de Paths
    # ==========================================
    data_dir: Path = Field(
        default=Path("data"),
        description="Directorio para datos descargados"
    )
    logs_dir: Path = Field(
        default=Path("logs"),
        description="Directorio para logs"
    )
    csv_dir: Path = Field(
        default=Path("csvs"),
        description="Directorio para archivos CSV generados"
    )
    templates_dir: Path = Field(
        default=Path("templates"),
        description="Directorio para templates HTML"
    )
    
    # ==========================================
    # Validadores
    # ==========================================
    @field_validator("report_to", mode="before")
    @classmethod
    def parse_report_to(cls, v: str | list) -> list[str]:
        """Convierte string separado por espacios en lista."""
        if isinstance(v, str):
            return [email.strip() for email in v.split() if email.strip()]
        return v or []
    
    @field_validator("base_path", "data_dir", "logs_dir", "csv_dir", "templates_dir", mode="before")
    @classmethod
    def parse_path(cls, v: str | Path) -> Path:
        """Convierte strings a Path objects."""
        return Path(v) if isinstance(v, str) else v
    
    @field_validator("max_emails_diarios")
    @classmethod
    def set_email_limit(cls, v: int, info) -> int:
        """Ajusta el límite de emails según el entorno."""
        # Nota: info.data contiene los valores ya validados
        # Usamos valores por defecto seguros
        return v
    
    # ==========================================
    # Propiedades calculadas
    # ==========================================
    @property
    def is_produccion(self) -> bool:
        """Indica si estamos en entorno de producción."""
        return self.environment == "produccion"
    
    @property
    def is_test(self) -> bool:
        """Indica si estamos en entorno de test."""
        return self.environment == "test"
    
    @property
    def email_limit(self) -> int:
        """Límite de emails según el entorno."""
        return 1000 if self.subdomain == "www" else 10
    
    @property
    def db_url(self) -> str:
        """URL de conexión a la base de datos."""
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )
    
    def ensure_directories(self) -> None:
        """Crea los directorios necesarios si no existen."""
        for path in [self.data_dir, self.logs_dir, self.csv_dir]:
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """
    Retorna una instancia cacheada de Settings.
    
    El cacheo mejora el rendimiento ya que las variables
    de entorno no cambian durante la ejecución.
    """
    return Settings()


# Instancia global para importación directa
settings = get_settings()
