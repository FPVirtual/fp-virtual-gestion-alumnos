"""
Implementación de MoodleRepository usando acceso directo a BD.

Utiliza MySQL directamente para operaciones complejas que no
se pueden hacer fácilmente con moosh o Web Services.
"""

import subprocess
from typing import Any

import pymysql
from pymysql.cursors import DictCursor

from gestion_alumnos.core.config import Settings
from gestion_alumnos.core.exceptions import MoodleError
from gestion_alumnos.core.logging import get_logger

logger = get_logger(__name__)


class MoodleDBRepository:
    """
    Repositorio de Moodle usando conexión directa a BD y moosh.
    
    Combina SQL directo para consultas complejas con moosh
    para operaciones de gestión de usuarios.
    """
    
    # IDs de usuarios protegidos (no se pueden eliminar)
    USUARIOS_PROTEGIDOS = frozenset({
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
        16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28,
        29, 30, 31, 32, 33, 3725, 3729, 3730, 7152, 7490,
        7491, 11720, 12270, 12272
    })
    
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        self._connection = None
    
    def _get_connection(self) -> pymysql.Connection:
        """Obtiene o crea la conexión a la base de datos."""
        if self._connection is None or not self._connection.open:
            self._connection = pymysql.connect(
                host=self._settings.db_host,
                port=self._settings.db_port,
                user=self._settings.db_user,
                password=self._settings.db_password,
                database=self._settings.db_name,
                cursorclass=DictCursor,
                charset="utf8mb4"
            )
        return self._connection
    
    def _execute_query(
        self,
        query: str,
        params: tuple | None = None,
        fetch: bool = True
    ) -> list[dict] | int:
        """Ejecuta una query SQL y retorna resultados."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                if fetch:
                    return cursor.fetchall()
                conn.commit()
                return cursor.rowcount
        except pymysql.Error as e:
            logger.error(f"Error SQL: {e}")
            raise MoodleError(f"Error en base de datos: {e}")
    
    def _run_moosh(
        self,
        comando: str,
        capture: bool = True,
        timeout: int | None = None
    ) -> str:
        """Ejecuta un comando moosh en el contenedor Docker."""
        if timeout is None:
            timeout = self._settings.moosh_timeout
        
        container = self._settings.docker_container
        full_command = f"docker exec {container} moosh {comando}"
        
        try:
            logger.debug(f"Ejecutando: {full_command}")
            result = subprocess.run(
                full_command,
                shell=True,
                capture_output=capture,
                text=True,
                timeout=timeout
            )
            
            if result.returncode != 0:
                raise MoodleError(
                    f"Moosh error: {result.stderr}",
                    comando=comando,
                    codigo_salida=result.returncode
                )
            
            return result.stdout
            
        except subprocess.TimeoutExpired:
            raise MoodleError(
                f"Timeout ejecutando moosh después de {timeout}s",
                comando=comando
            )
        except subprocess.SubprocessError as e:
            raise MoodleError(f"Error ejecutando moosh: {e}", comando=comando)
    
    # ==========================================
    # Implementación del protocolo
    # ==========================================
    
    def usuario_existe(self, username: str) -> bool:
        """Verifica si existe un usuario en Moodle."""
        query = "SELECT id FROM mdl_user WHERE username = %s AND deleted = 0"
        result = self._execute_query(query, (username,))
        return len(result) > 0
    
    def crear_usuario(
        self,
        username: str,
        email: str,
        nombre: str,
        apellido: str,
        password: str | None = None
    ) -> int:
        """Crea un usuario usando moosh."""
        # Generar contraseña si no se proporciona
        if password is None:
            password = self._generar_password()
        
        comando = (
            f'user-create --password "{password}" '
            f'--email {email} '
            f'--firstname "{nombre}" '
            f'--lastname "{apellido}" '
            f'{username}'
        )
        
        output = self._run_moosh(comando)
        
        # Extraer ID del usuario creado del output
        # Output típico: "User created with id: 1234"
        try:
            user_id = int(output.strip().split(":")[-1].strip())
            logger.info(f"Usuario creado: {username} (ID: {user_id})")
            return user_id
        except (ValueError, IndexError):
            logger.warning(f"No se pudo extraer ID del output: {output}")
            return 0
    
    def actualizar_usuario(self, username: str, **campos) -> bool:
        """Actualiza campos de un usuario."""
        if not campos:
            return False
        
        set_clause = ", ".join([f"{k} = %s" for k in campos.keys()])
        query = f"UPDATE mdl_user SET {set_clause} WHERE username = %s"
        params = tuple(campos.values()) + (username,)
        
        filas = self._execute_query(query, params, fetch=False)
        return filas > 0
    
    def suspender_usuario(self, username: str) -> bool:
        """Suspende un usuario (suspended = 1)."""
        query = "UPDATE mdl_user SET suspended = 1 WHERE username = %s"
        filas = self._execute_query(query, (username,), fetch=False)
        
        if filas > 0:
            logger.info(f"Usuario suspendido: {username}")
        return filas > 0
    
    def reactivar_usuario(self, username: str) -> bool:
        """Reactiva un usuario suspendido."""
        query = "UPDATE mdl_user SET suspended = 0 WHERE username = %s"
        filas = self._execute_query(query, (username,), fetch=False)
        
        if filas > 0:
            logger.info(f"Usuario reactivado: {username}")
        return filas > 0
    
    def matricular_en_curso(self, username: str, curso_id: str) -> bool:
        """Matricula un usuario en un curso usando moosh."""
        comando = f"course-enrol -c {curso_id} {username}"
        
        try:
            self._run_moosh(comando)
            logger.info(f"Usuario {username} matriculado en curso {curso_id}")
            return True
        except MoodleError as e:
            logger.error(f"Error matriculando: {e}")
            return False
    
    def desmatricular_de_curso(self, username: str, curso_id: str) -> bool:
        """Desmatricula un usuario de un curso."""
        # Usar SQL directo ya que moosh no tiene comando directo
        query = """
            UPDATE mdl_user_enrolments ue
            JOIN mdl_enrol e ON ue.enrolid = e.id
            JOIN mdl_user u ON ue.userid = u.id
            SET ue.status = 1
            WHERE u.username = %s AND e.courseid = %s
        """
        filas = self._execute_query(query, (username, curso_id), fetch=False)
        return filas > 0
    
    def matricular_en_cohorte(self, username: str, cohorte: str) -> bool:
        """Matricula un usuario en una cohorte usando moosh."""
        comando = f"cohort-enrol -c {cohorte} {username}"
        
        try:
            self._run_moosh(comando)
            logger.info(f"Usuario {username} matriculado en cohorte {cohorte}")
            return True
        except MoodleError as e:
            logger.error(f"Error matriculando en cohorte: {e}")
            return False
    
    def obtener_matriculas(self, username: str) -> list[dict]:
        """Obtiene las matrículas activas de un usuario."""
        query = """
            SELECT c.id, c.shortname, c.fullname, ue.status
            FROM mdl_course c
            JOIN mdl_enrol e ON e.courseid = c.id
            JOIN mdl_user_enrolments ue ON ue.enrolid = e.id
            JOIN mdl_user u ON ue.userid = u.id
            WHERE u.username = %s AND ue.status = 0
        """
        return self._execute_query(query, (username,))
    
    def obtener_todos_usuarios(self) -> list[dict]:
        """Obtiene todos los usuarios no eliminados."""
        query = """
            SELECT id, username, email, firstname, lastname, 
                   suspended, deleted, lastlogin
            FROM mdl_user
            WHERE deleted = 0
        """
        return self._execute_query(query)
    
    def es_usuario_protegido(self, user_id: int) -> bool:
        """Verifica si un usuario está en la lista de protegidos."""
        return user_id in self.USUARIOS_PROTEGIDOS
    
    def _generar_password(self, longitud: int = 10) -> str:
        """Genera una contraseña aleatoria segura."""
        import secrets
        import string
        
        caracteres = string.ascii_letters + string.digits + "!@#$%^&*"
        while True:
            password = "".join(secrets.choice(caracteres) for _ in range(longitud))
            # Asegurar que tenga al menos una mayúscula, minúscula y dígito
            if (any(c.isupper() for c in password)
                and any(c.islower() for c in password)
                and any(c.isdigit() for c in password)):
                return password
