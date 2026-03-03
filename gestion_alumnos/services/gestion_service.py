"""
Servicio principal de gestión de alumnos.

Orquesta las operaciones de:
- Obtención de datos desde SIGAD
- Sincronización con Moodle
- Envío de notificaciones
- Generación de informes
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from gestion_alumnos.core.config import Settings
from gestion_alumnos.core.logging import get_logger
from gestion_alumnos.models_v2 import Alumno, Registro

if TYPE_CHECKING:
    from gestion_alumnos.repositories.protocols import (
        EstudianteRepository,
        MoodleRepository,
        EmailRepository,
    )

logger = get_logger(__name__)


@dataclass
class ResultadoSync:
    """Resultado de una operación de sincronización."""
    
    alumnos_procesados: int = 0
    nuevos_creados: int = 0
    reactivados: int = 0
    suspendidos: int = 0
    emails_actualizados: int = 0
    nuevas_matriculas: int = 0
    errores: list[str] = field(default_factory=list)
    
    @property
    def exito(self) -> bool:
        """Indica si no hubo errores críticos."""
        return len(self.errores) == 0


class GestionAlumnosService:
    """
    Servicio principal para la gestión de alumnos.
    
    Esta clase implementa la lógica de negocio coordinando
    entre los diferentes repositorios.
    
    Args:
        estudiante_repo: Repositorio de estudiantes (SIGAD)
        moodle_repo: Repositorio de Moodle
        email_repo: Repositorio de emails
        settings: Configuración del sistema
    """
    
    def __init__(
        self,
        estudiante_repo: "EstudianteRepository",
        moodle_repo: "MoodleRepository",
        email_repo: "EmailRepository | None" = None,
        settings: Settings | None = None
    ) -> None:
        self._estudiante_repo = estudiante_repo
        self._moodle_repo = moodle_repo
        self._email_repo = email_repo
        self._settings = settings or Settings()
    
    def ejecutar_sincronizacion_completa(self) -> ResultadoSync:
        """
        Ejecuta el proceso completo de sincronización.
        
        Flujo:
        1. Obtiene estudiantes desde SIGAD
        2. Obtiene usuarios actuales de Moodle
        3. Procesa altas, bajas y actualizaciones
        4. Envía notificaciones si corresponde
        
        Returns:
            ResultadoSync con estadísticas de la operación
        """
        logger.info("Iniciando sincronización completa")
        resultado = ResultadoSync()
        
        try:
            # 1. Obtener datos de SIGAD
            registro_sigad = self._estudiante_repo.obtener_registro()
            resultado.alumnos_procesados = registro_sigad.total_alumnos
            
            logger.info(f"Estudiantes en SIGAD: {registro_sigad.total_alumnos}")
            
            # 2. Obtener usuarios de Moodle
            usuarios_moodle = {
                u["username"]: u
                for u in self._moodle_repo.obtener_todos_usuarios()
            }
            
            logger.info(f"Usuarios en Moodle: {len(usuarios_moodle)}")
            
            # 3. Procesar cada alumno de SIGAD
            for alumno in registro_sigad.alumnos:
                self._procesar_alumno(alumno, usuarios_moodle, resultado)
            
            # 4. Procesar bajas (usuarios en Moodle pero no en SIGAD)
            self._procesar_bajas(registro_sigad, usuarios_moodle, resultado)
            
            logger.info("Sincronización completada exitosamente")
            
        except Exception as e:
            logger.error(f"Error en sincronización: {e}")
            resultado.errores.append(str(e))
        
        return resultado
    
    def _procesar_alumno(
        self,
        alumno: Alumno,
        usuarios_moodle: dict,
        resultado: ResultadoSync
    ) -> None:
        """Procesa un alumno individual."""
        username = alumno.username_moodle
        
        if username not in usuarios_moodle:
            # Nuevo alumno -> Crear usuario
            self._crear_nuevo_usuario(alumno, resultado)
        else:
            # Usuario existente -> Verificar actualizaciones
            usuario_mdl = usuarios_moodle[username]
            self._actualizar_usuario_existente(alumno, usuario_mdl, resultado)
    
    def _crear_nuevo_usuario(
        self,
        alumno: Alumno,
        resultado: ResultadoSync
    ) -> None:
        """Crea un nuevo usuario en Moodle."""
        try:
            # 1. Crear usuario
            password = self._generar_password_temporal()
            
            self._moodle_repo.crear_usuario(
                username=alumno.username_moodle,
                email=alumno.email_institucional,
                nombre=alumno.nombre,
                apellido=alumno.apellido1,
                password=password
            )
            
            # 2. Matricular en cohorte
            self._moodle_repo.matricular_en_cohorte(
                alumno.username_moodle,
                "alumnado"
            )
            
            # 3. Matricular en cursos según módulos
            modulos = alumno.obtener_todos_modulos()
            for modulo in modulos:
                self._matricular_en_modulo(alumno.username_moodle, modulo)
            
            # 4. Enviar email de bienvenida
            if self._email_repo and not self._email_repo.limite_alcanzado():
                self._email_repo.enviar_bienvenida_nuevo_usuario(
                    alumno,
                    password,
                    [m.siglas for m in modulos]
                )
            
            resultado.nuevos_creados += 1
            logger.info(f"Nuevo usuario creado: {alumno.username_moodle}")
            
        except Exception as e:
            logger.error(f"Error creando usuario {alumno.username_moodle}: {e}")
            resultado.errores.append(f"Error creando {alumno.username_moodle}: {e}")
    
    def _actualizar_usuario_existente(
        self,
        alumno: Alumno,
        usuario_mdl: dict,
        resultado: ResultadoSync
    ) -> None:
        """Actualiza un usuario existente si es necesario."""
        # 1. Verificar si está suspendido -> Reactivar
        if usuario_mdl.get("suspended"):
            self._moodle_repo.reactivar_usuario(alumno.username_moodle)
            resultado.reactivados += 1
            logger.info(f"Usuario reactivado: {alumno.username_moodle}")
        
        # 2. Verificar cambio de email
        if usuario_mdl.get("email") != alumno.email_institucional:
            self._moodle_repo.actualizar_usuario(
                alumno.username_moodle,
                email=alumno.email_institucional
            )
            resultado.emails_actualizados += 1
            logger.info(f"Email actualizado: {alumno.username_moodle}")
        
        # 3. Verificar nuevas matrículas
        matriculas_actuales = {
            m["shortname"]
            for m in self._moodle_repo.obtener_matriculas(alumno.username_moodle)
        }
        
        modulos = alumno.obtener_todos_modulos()
        nuevas_matriculas = []
        
        for modulo in modulos:
            if modulo.siglas not in matriculas_actuales:
                if self._matricular_en_modulo(alumno.username_moodle, modulo):
                    nuevas_matriculas.append(modulo.siglas)
        
        if nuevas_matriculas:
            resultado.nuevas_matriculas += len(nuevas_matriculas)
            
            # Notificar nuevas matrículas
            if self._email_repo and not self._email_repo.limite_alcanzado():
                self._email_repo.enviar_nuevas_matriculas(
                    alumno,
                    nuevas_matriculas
                )
    
    def _procesar_bajas(
        self,
        registro_sigad: Registro,
        usuarios_moodle: dict,
        resultado: ResultadoSync
    ) -> None:
        """Suspende usuarios que no están en SIGAD."""
        documentos_sigad = {
            a.username_moodle for a in registro_sigad.alumnos
        }
        
        for username, usuario in usuarios_moodle.items():
            if username not in documentos_sigad:
                # Verificar que no sea usuario protegido
                if not self._moodle_repo.es_usuario_protegido(usuario["id"]):
                    if not usuario.get("suspended"):
                        self._moodle_repo.suspender_usuario(username)
                        resultado.suspendidos += 1
                        logger.info(f"Usuario suspendido (baja): {username}")
    
    def _matricular_en_modulo(
        self,
        username: str,
        modulo: Any
    ) -> bool:
        """Matricula un usuario en el curso de un módulo."""
        # Aquí iría la lógica de mapeo módulo -> curso_id
        # Por ahora, asumimos que las siglas corresponden al curso
        curso_id = modulo.siglas
        return self._moodle_repo.matricular_en_curso(username, curso_id)
    
    def _generar_password_temporal(self) -> str:
        """Genera una contraseña temporal segura."""
        import secrets
        import string
        
        caracteres = string.ascii_letters + string.digits + "!@#$%^&*"
        while True:
            pwd = "".join(secrets.choice(caracteres) for _ in range(12))
            if (any(c.isupper() for c in pwd)
                and any(c.islower() for c in pwd)
                and any(c.isdigit() for c in pwd)):
                return pwd
