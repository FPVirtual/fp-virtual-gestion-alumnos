"""
Módulo para aplicar cambios detectados entre SIGAD y Moodle.

Estrategia:
- Datos personales (email, nombre, apellidos, documento): UPDATE SQL directo (rápido)
- Matrículas, altas, bajas: Comandos moosh (robusto, maneja cache de Moodle)

Uso:
    from gestion_alumnos.utils.sigad_aplicar_cambios import AplicadorCambiosSigad
    
    aplicador = AplicadorCambiosSigad(moodle_container)
    resultado = aplicador.aplicar_todos_los_cambios(cambios_detectados)
"""

import os
import re
import pymysql
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

from gestion_alumnos.logger_config import logger
from gestion_alumnos.utils.moosh import run_moosh_command, run_command


@dataclass
class ResultadoOperacion:
    """Resultado de una operación de aplicación de cambios."""
    exito: bool
    tipo: str
    documento: str
    mensaje: str
    detalles: Optional[Dict] = None


class AplicadorCambiosSigad:
    """
    Aplica cambios detectados entre SIGAD y Moodle.
    
    Usa SQL directo para datos personales (rápido) y moosh para
    operaciones complejas como matrículas y creación de usuarios.
    """
    
    def __init__(self, moodle_container: str, dry_run: bool = False):
        """
        Inicializa el aplicador de cambios.
        
        Args:
            moodle_container: Nombre del contenedor Docker de Moodle
            dry_run: Si True, solo simula las operaciones sin ejecutarlas
        """
        self.moodle = {'container_name': moodle_container}
        self.dry_run = dry_run
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASS'),
            'database': os.getenv('DB_NAME'),
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor
        }
        self.connection = None
        
        # Estadísticas
        self.estadisticas = {
            'datos_personales_actualizados': 0,
            'usuarios_creados': 0,
            'usuarios_suspendidos': 0,
            'usuarios_reactivados': 0,
            'matriculas_creadas': 0,
            'matriculas_suspendidas': 0,
            'errores': 0
        }
        
        # Resultados detallados
        self.resultados: List[ResultadoOperacion] = []
        
    def conectar_bd(self) -> bool:
        """Establece conexión con la base de datos."""
        try:
            self.connection = pymysql.connect(**self.db_config)
            return True
        except pymysql.Error as e:
            logger.error(f"Error conexión BD: {e}")
            return False
    
    def desconectar_bd(self):
        """Cierra conexión con la base de datos."""
        if self.connection:
            self.connection.close()
    
    # =================================================================
    # 1. ACTUALIZACIÓN DE DATOS PERSONALES (SQL Directo - Rápido)
    # =================================================================
    
    def actualizar_email(self, userid: int, email_nuevo: str, email_anterior: str = None) -> ResultadoOperacion:
        """
        Actualiza el email de un usuario en mdl_user.
        
        Args:
            userid: ID del usuario en Moodle
            email_nuevo: Nuevo email desde SIGAD
            email_anterior: Email actual (para logging)
            
        Returns:
            ResultadoOperacion con el estado de la operación
        """
        documento = "unknown"
        try:
            if self.dry_run:
                logger.info(f"[DRY-RUN] Actualizar email usuario {userid}: {email_anterior} -> {email_nuevo}")
                return ResultadoOperacion(True, "email_actualizado", documento, 
                                        f"Simulado: {email_anterior} -> {email_nuevo}")
            
            with self.connection.cursor() as cursor:
                # Obtener username para logging
                cursor.execute("SELECT username FROM mdl_user WHERE id = %s", (userid,))
                result = cursor.fetchone()
                documento = result['username'] if result else str(userid)
                
                # Actualizar email
                sql = "UPDATE mdl_user SET email = %s, timemodified = %s WHERE id = %s"
                cursor.execute(sql, (email_nuevo, int(datetime.now().timestamp()), userid))
                self.connection.commit()
                
                self.estadisticas['datos_personales_actualizados'] += 1
                msg = f"Email actualizado: {email_anterior} -> {email_nuevo}"
                logger.info(f"✓ {msg} (usuario: {documento})")
                
                return ResultadoOperacion(True, "email_actualizado", documento, msg,
                                        {'userid': userid, 'anterior': email_anterior, 'nuevo': email_nuevo})
                
        except Exception as e:
            logger.error(f"✗ Error actualizando email de {documento}: {e}")
            self.estadisticas['errores'] += 1
            return ResultadoOperacion(False, "email_actualizado", documento, str(e))
    
    def actualizar_nombre_completo(self, userid: int, nombre: str, apellido1: str, 
                                   apellido2: Optional[str] = None) -> ResultadoOperacion:
        """
        Actualiza nombre y apellidos en mdl_user.
        
        Args:
            userid: ID del usuario
            nombre: Nuevo nombre
            apellido1: Nuevo primer apellido
            apellido2: Nuevo segundo apellido (opcional)
        """
        try:
            lastname = f"{apellido1} {apellido2}".strip() if apellido2 else apellido1
            
            if self.dry_run:
                logger.info(f"[DRY-RUN] Actualizar nombre usuario {userid}: {nombre} {lastname}")
                return ResultadoOperacion(True, "nombre_actualizado", str(userid), 
                                        f"Simulado: {nombre} {lastname}")
            
            with self.connection.cursor() as cursor:
                sql = """UPDATE mdl_user 
                        SET firstname = %s, lastname = %s, timemodified = %s 
                        WHERE id = %s"""
                cursor.execute(sql, (nombre, lastname, int(datetime.now().timestamp()), userid))
                self.connection.commit()
                
                self.estadisticas['datos_personales_actualizados'] += 1
                msg = f"Nombre actualizado: {nombre} {lastname}"
                logger.info(f"✓ {msg} (userid: {userid})")
                
                return ResultadoOperacion(True, "nombre_actualizado", str(userid), msg)
                
        except Exception as e:
            logger.error(f"✗ Error actualizando nombre de {userid}: {e}")
            self.estadisticas['errores'] += 1
            return ResultadoOperacion(False, "nombre_actualizado", str(userid), str(e))
    
    def actualizar_documento_username(self, userid: int, documento_nuevo: str, 
                                      documento_anterior: str) -> ResultadoOperacion:
        """
        Actualiza el username (documento DNI/NIE) de un usuario.
        
        ⚠️ Operación crítica: cambia el login del usuario.
        
        Args:
            userid: ID del usuario
            documento_nuevo: Nuevo documento (nuevo username)
            documento_anterior: Documento anterior
        """
        documento_nuevo = documento_nuevo.lower().strip()
        
        try:
            if self.dry_run:
                logger.info(f"[DRY-RUN] Actualizar username {documento_anterior} -> {documento_nuevo}")
                return ResultadoOperacion(True, "username_actualizado", documento_nuevo,
                                        f"Simulado: {documento_anterior} -> {documento_nuevo}")
            
            with self.connection.cursor() as cursor:
                # Verificar que no exista otro usuario con el nuevo username
                cursor.execute("SELECT id FROM mdl_user WHERE username = %s AND id != %s",
                             (documento_nuevo, userid))
                if cursor.fetchone():
                    msg = f"Ya existe otro usuario con username {documento_nuevo}"
                    logger.error(f"✗ {msg}")
                    return ResultadoOperacion(False, "username_actualizado", documento_nuevo, msg)
                
                # Actualizar username
                sql = "UPDATE mdl_user SET username = %s, timemodified = %s WHERE id = %s"
                cursor.execute(sql, (documento_nuevo, int(datetime.now().timestamp()), userid))
                self.connection.commit()
                
                self.estadisticas['datos_personales_actualizados'] += 1
                msg = f"Username actualizado: {documento_anterior} -> {documento_nuevo}"
                logger.info(f"✓ {msg}")
                
                return ResultadoOperacion(True, "username_actualizado", documento_nuevo, msg,
                                        {'userid': userid, 'anterior': documento_anterior, 'nuevo': documento_nuevo})
                
        except Exception as e:
            logger.error(f"✗ Error actualizando username de {userid}: {e}")
            self.estadisticas['errores'] += 1
            return ResultadoOperacion(False, "username_actualizado", documento_nuevo, str(e))
    
    def procesar_cambios_datos_personales(self, cambios: Dict) -> List[ResultadoOperacion]:
        """
        Procesa todos los cambios de datos personales detectados.
        
        Args:
            cambios: Diccionario con las listas de cambios detectados
            
        Returns:
            Lista de resultados de cada operación
        """
        resultados = []
        
        if not self.conectar_bd():
            logger.error("No se pudo conectar a la BD para actualizar datos personales")
            return resultados
        
        try:
            # 1. Actualizar emails
            logger.info(f"\n📧 Procesando {len(cambios.get('cambios_email', []))} cambios de email...")
            for cambio in cambios.get('cambios_email', []):
                resultado = self.actualizar_email(
                    cambio['moodle_userid'],
                    cambio['email_en_sigad'],
                    cambio['email_en_moodle']
                )
                resultados.append(resultado)
            
            # 2. Actualizar nombres
            logger.info(f"\n📝 Procesando {len(cambios.get('cambios_nombre', []))} cambios de nombre...")
            for cambio in cambios.get('cambios_nombre', []):
                resultado = self.actualizar_nombre_completo(
                    cambio['moodle_userid'],
                    cambio['nombre_nuevo'],
                    cambio['apellido1_nuevo'],
                    cambio.get('apellido2_nuevo')
                )
                resultados.append(resultado)
            
            # 3. Actualizar documentos (username)
            logger.info(f"\n🆔 Procesando {len(cambios.get('cambios_documento', []))} cambios de documento...")
            for cambio in cambios.get('cambios_documento', []):
                resultado = self.actualizar_documento_username(
                    cambio['moodle_userid'],
                    cambio['documento_nuevo'],
                    cambio['documento_anterior']
                )
                resultados.append(resultado)
                
        finally:
            self.desconectar_bd()
        
        return resultados
    
    # =================================================================
    # 2. OPERACIONES CON MOOSH (Matrículas, Altas, Bajas)
    # =================================================================
    
    def crear_usuario(self, alumno: Dict) -> ResultadoOperacion:
        """
        Crea un nuevo usuario en Moodle usando moosh.
        
        Args:
            alumno: Dict con datos del alumno desde SIGAD
        """
        documento = alumno['sigad_documento'].lower().strip()
        email = alumno['sigad_email']
        nombre = alumno['sigad_nombre']
        apellidos = f"{alumno['sigad_apellido1']} {alumno.get('sigad_apellido2', '')}".strip()
        
        # Generar password temporal
        password = self._generar_password_temporal(documento)
        
        try:
            if self.dry_run:
                logger.info(f"[DRY-RUN] Crear usuario: {documento} ({email})")
                return ResultadoOperacion(True, "usuario_creado", documento, 
                                        f"Simulado: {nombre} {apellidos}")
            
            # moosh user-create --password pass --email email --firstname name --lastname lastname username
            cmd = (f"moosh -n user-create --password '{password}' --email '{email}' "
                   f"--firstname '{nombre}' --lastname '{apellidos}' {documento}")
            
            output = run_moosh_command(self.moodle, cmd, capture=True, timeout=30)
            
            if "Error" in output or "error" in output.lower():
                msg = f"Error creando usuario: {output}"
                logger.error(f"✗ {msg}")
                self.estadisticas['errores'] += 1
                return ResultadoOperacion(False, "usuario_creado", documento, msg)
            
            # Obtener el userid creado
            userid = self._obtener_userid_por_username(documento)
            
            self.estadisticas['usuarios_creados'] += 1
            msg = f"Usuario creado: {nombre} {apellidos} ({documento})"
            logger.info(f"✓ {msg}")
            
            return ResultadoOperacion(True, "usuario_creado", documento, msg,
                                    {'userid': userid, 'password_temporal': password})
            
        except Exception as e:
            logger.error(f"✗ Error creando usuario {documento}: {e}")
            self.estadisticas['errores'] += 1
            return ResultadoOperacion(False, "usuario_creado", documento, str(e))
    
    def suspender_usuario(self, userid: int, documento: str) -> ResultadoOperacion:
        """
        Suspende un usuario en Moodle usando moosh.
        
        Args:
            userid: ID del usuario
            documento: Documento/username para logging
        """
        try:
            if self.dry_run:
                logger.info(f"[DRY-RUN] Suspender usuario: {documento} (ID: {userid})")
                return ResultadoOperacion(True, "usuario_suspendido", documento, "Simulado")
            
            # moosh user-mod --suspend 1 userid
            cmd = f"moosh -n user-mod --suspend 1 {userid}"
            output = run_moosh_command(self.moodle, cmd, capture=True, timeout=15)
            
            self.estadisticas['usuarios_suspendidos'] += 1
            msg = f"Usuario suspendido: {documento}"
            logger.info(f"✓ {msg}")
            
            return ResultadoOperacion(True, "usuario_suspendido", documento, msg, {'userid': userid})
            
        except Exception as e:
            logger.error(f"✗ Error suspendiendo usuario {documento}: {e}")
            self.estadisticas['errores'] += 1
            return ResultadoOperacion(False, "usuario_suspendido", documento, str(e))
    
    def reactivar_usuario(self, userid: int, documento: str) -> ResultadoOperacion:
        """
        Reactiva un usuario suspendido en Moodle usando moosh.
        
        Args:
            userid: ID del usuario
            documento: Documento/username para logging
        """
        try:
            if self.dry_run:
                logger.info(f"[DRY-RUN] Reactivar usuario: {documento} (ID: {userid})")
                return ResultadoOperacion(True, "usuario_reactivado", documento, "Simulado")
            
            # moosh user-mod --suspend 0 userid
            cmd = f"moosh -n user-mod --suspend 0 {userid}"
            output = run_moosh_command(self.moodle, cmd, capture=True, timeout=15)
            
            self.estadisticas['usuarios_reactivados'] += 1
            msg = f"Usuario reactivado: {documento}"
            logger.info(f"✓ {msg}")
            
            return ResultadoOperacion(True, "usuario_reactivado", documento, msg, {'userid': userid})
            
        except Exception as e:
            logger.error(f"✗ Error reactivando usuario {documento}: {e}")
            self.estadisticas['errores'] += 1
            return ResultadoOperacion(False, "usuario_reactivado", documento, str(e))
    
    def matricular_en_curso(self, userid: int, courseid: int, documento: str, 
                           nombre_curso: str = None) -> ResultadoOperacion:
        """
        Matricula un usuario en un curso usando moosh.
        
        Args:
            userid: ID del usuario
            courseid: ID del curso
            documento: Documento/username para logging
            nombre_curso: Nombre del curso para logging
        """
        curso_str = nombre_curso or f"ID:{courseid}"
        
        try:
            if self.dry_run:
                logger.info(f"[DRY-RUN] Matricular {documento} en curso {curso_str}")
                return ResultadoOperacion(True, "matricula_creada", documento, 
                                        f"Simulado en {curso_str}")
            
            # moosh course-enrol -i courseid userid (el -i es para inscribir)
            cmd = f"moosh -n course-enrol -i {courseid} {userid}"
            output = run_moosh_command(self.moodle, cmd, capture=True, timeout=15)
            
            self.estadisticas['matriculas_creadas'] += 1
            msg = f"Matriculado {documento} en {curso_str}"
            logger.info(f"✓ {msg}")
            
            return ResultadoOperacion(True, "matricula_creada", documento, msg,
                                    {'userid': userid, 'courseid': courseid})
            
        except Exception as e:
            logger.error(f"✗ Error matriculando {documento} en {curso_str}: {e}")
            self.estadisticas['errores'] += 1
            return ResultadoOperacion(False, "matricula_creada", documento, str(e))
    
    def desmatricular_de_curso(self, userid: int, courseid: int, documento: str,
                               nombre_curso: str = None) -> ResultadoOperacion:
        """
        Desmatricula (da de baja) un usuario de un curso usando moosh.
        
        Args:
            userid: ID del usuario
            courseid: ID del curso
            documento: Documento/username para logging
            nombre_curso: Nombre del curso para logging
        """
        curso_str = nombre_curso or f"ID:{courseid}"
        
        try:
            if self.dry_run:
                logger.info(f"[DRY-RUN] Desmatricular {documento} de curso {curso_str}")
                return ResultadoOperacion(True, "matricula_suspendida", documento,
                                        f"Simulado de {curso_str}")
            
            # moosh course-unenrol courseid userid
            cmd = f"moosh -n course-unenrol {courseid} {userid}"
            output = run_moosh_command(self.moodle, cmd, capture=True, timeout=15)
            
            self.estadisticas['matriculas_suspendidas'] += 1
            msg = f"Desmatriculado {documento} de {curso_str}"
            logger.info(f"✓ {msg}")
            
            return ResultadoOperacion(True, "matricula_suspendida", documento, msg,
                                    {'userid': userid, 'courseid': courseid})
            
        except Exception as e:
            logger.error(f"✗ Error desmatriculando {documento} de {curso_str}: {e}")
            self.estadisticas['errores'] += 1
            return ResultadoOperacion(False, "matricula_suspendida", documento, str(e))
    
    def agregar_a_cohorte(self, userid: int, cohorte: str, documento: str) -> ResultadoOperacion:
        """
        Agrega un usuario a una cohorte usando moosh.
        
        Args:
            userid: ID del usuario
            cohorte: Nombre o idnumber de la cohorte
            documento: Documento/username para logging
        """
        try:
            if self.dry_run:
                logger.info(f"[DRY-RUN] Agregar {documento} a cohorte {cohorte}")
                return ResultadoOperacion(True, "cohorte_agregado", documento,
                                        f"Simulado a {cohorte}")
            
            # moosh cohort-enrol -u userid "nombre_cohorte"
            cmd = f'moosh -n cohort-enrol -u {userid} "{cohorte}"'
            output = run_moosh_command(self.moodle, cmd, capture=True, timeout=15)
            
            msg = f"Agregado {documento} a cohorte {cohorte}"
            logger.info(f"✓ {msg}")
            
            return ResultadoOperacion(True, "cohorte_agregado", documento, msg,
                                    {'userid': userid, 'cohorte': cohorte})
            
        except Exception as e:
            logger.error(f"✗ Error agregando {documento} a cohorte {cohorte}: {e}")
            self.estadisticas['errores'] += 1
            return ResultadoOperacion(False, "cohorte_agregado", documento, str(e))
    
    # =================================================================
    # 3. PROCESAMIENTO POR LOTES
    # =================================================================
    
    def procesar_altas(self, cambios: Dict) -> List[ResultadoOperacion]:
        """Procesa las altas de nuevos alumnos."""
        resultados = []
        
        logger.info(f"\n👤 Procesando {len(cambios.get('alumnos_nuevos', []))} altas de alumnos...")
        
        for alumno in cambios.get('alumnos_nuevos', []):
            # 1. Crear usuario
            resultado = self.crear_usuario(alumno)
            resultados.append(resultado)
            
            if resultado.exito and not self.dry_run:
                userid = resultado.detalles.get('userid') if resultado.detalles else None
                
                if userid:
                    # 2. Agregar a cohorte "alumnado"
                    res_cohorte = self.agregar_a_cohorte(userid, "alumnado", alumno['sigad_documento'])
                    resultados.append(res_cohorte)
                    
                    # 3. Matricular en cursos de sus módulos (esto requeriría mapeo curso-módulo)
                    # Por ahora solo loggeamos
                    logger.info(f"  → Pendiente: Matricular {alumno['sigad_documento']} en cursos de sus módulos")
        
        return resultados
    
    def procesar_bajas(self, cambios: Dict) -> List[ResultadoOperacion]:
        """Procesa las bajas de alumnos (suspende usuarios)."""
        resultados = []
        
        logger.info(f"\n🚫 Procesando {len(cambios.get('alumnos_baja', []))} bajas de alumnos...")
        
        for alumno in cambios.get('alumnos_baja', []):
            resultado = self.suspender_usuario(
                alumno['moodle_userid'],
                alumno['moodle_documento']
            )
            resultados.append(resultado)
        
        return resultados
    
    def procesar_reactivaciones(self, cambios: Dict) -> List[ResultadoOperacion]:
        """Procesa las reactivaciones de alumnos suspendidos."""
        resultados = []
        
        logger.info(f"\n✅ Procesando {len(cambios.get('alumnos_reactivar', []))} reactivaciones...")
        
        for alumno in cambios.get('alumnos_reactivar', []):
            resultado = self.reactivar_usuario(
                alumno['moodle_userid'],
                alumno['sigad_documento']
            )
            resultados.append(resultado)
        
        return resultados
    
    def procesar_matriculas_nuevas(self, cambios: Dict, mapeo_cursos: Dict[str, int] = None) -> List[ResultadoOperacion]:
        """
        Procesa las matrículas nuevas en cursos.
        
        Args:
            cambios: Diccionario de cambios
            mapeo_cursos: Dict que mapea siglasModulo -> courseid de Moodle
                         Si es None, solo se loggean las necesidades
        """
        resultados = []
        matriculas = cambios.get('matriculas_nuevas', [])
        
        logger.info(f"\n📚 Procesando {len(matriculas)} matrículas nuevas...")
        
        if not mapeo_cursos:
            logger.warning("⚠️ No se proporcionó mapeo_cursos. Solo se loggean necesidades.")
            for mat in matriculas[:10]:  # Mostrar solo primeros 10
                logger.info(f"  → Pendiente: Matricular {mat['sigad_documento']} en {mat['sigad_siglasmodulo']}")
            if len(matriculas) > 10:
                logger.info(f"  ... y {len(matriculas) - 10} más")
            return resultados
        
        # Agrupar por alumno para eficiencia
        matriculas_por_alumno = {}
        for mat in matriculas:
            doc = mat['sigad_documento']
            if doc not in matriculas_por_alumno:
                matriculas_por_alumno[doc] = []
            matriculas_por_alumno[doc].append(mat)
        
        # Procesar cada alumno
        for documento, mats in matriculas_por_alumno.items():
            for mat in mats:
                sigla = mat['sigad_siglasmodulo']
                courseid = mapeo_cursos.get(sigla)
                
                if not courseid:
                    logger.warning(f"⚠️ No se encontró mapeo para {sigla}")
                    continue
                
                resultado = self.matricular_en_curso(
                    mat['moodle_userid'],
                    courseid,
                    documento,
                    sigla
                )
                resultados.append(resultado)
        
        return resultados
    
    def procesar_bajas_matriculas(self, cambios: Dict) -> List[ResultadoOperacion]:
        """Procesa las bajas de matrículas (desmatricular de cursos)."""
        resultados = []
        matriculas = cambios.get('matriculas_baja', [])
        
        logger.info(f"\n📚 Procesando {len(matriculas)} bajas de matrículas...")
        
        for mat in matriculas:
            resultado = self.desmatricular_de_curso(
                mat['moodle_userid'],
                mat['moodle_courseid'],
                mat['moodle_documento'],
                mat['moodle_course_shortname']
            )
            resultados.append(resultado)
        
        return resultados
    
    # =================================================================
    # 4. APLICACIÓN COMPLETA
    # =================================================================
    
    def aplicar_todos_los_cambios(self, cambios: Dict, 
                                   mapeo_cursos: Dict[str, int] = None,
                                   solo_simular: bool = None) -> Dict:
        """
        Aplica todos los cambios detectados.
        
        Args:
            cambios: Diccionario con cambios detectados
            mapeo_cursos: Mapeo de siglas de módulos a courseids de Moodle
            solo_simular: Si True, solo simula (sobrescribe self.dry_run)
            
        Returns:
            Dict con estadísticas y resultados detallados
        """
        if solo_simular is not None:
            self.dry_run = solo_simular
        
        modo = "SIMULACIÓN (DRY-RUN)" if self.dry_run else "EJECUCIÓN REAL"
        logger.info(f"\n{'='*60}")
        logger.info(f"INICIANDO APLICACIÓN DE CAMBIOS - {modo}")
        logger.info(f"{'='*60}")
        
        todos_resultados = []
        
        # 1. Datos personales (SQL directo)
        resultados_dp = self.procesar_cambios_datos_personales(cambios)
        todos_resultados.extend(resultados_dp)
        
        # 2. Altas de alumnos (moosh)
        resultados_altas = self.procesar_altas(cambios)
        todos_resultados.extend(resultados_altas)
        
        # 3. Bajas de alumnos (moosh)
        resultados_bajas = self.procesar_bajas(cambios)
        todos_resultados.extend(resultados_bajas)
        
        # 4. Reactivaciones (moosh)
        resultados_react = self.procesar_reactivaciones(cambios)
        todos_resultados.extend(resultados_react)
        
        # 5. Matrículas nuevas (moosh)
        resultados_mat_nuevas = self.procesar_matriculas_nuevas(cambios, mapeo_cursos)
        todos_resultados.extend(resultados_mat_nuevas)
        
        # 6. Bajas de matrículas (moosh)
        resultados_mat_bajas = self.procesar_bajas_matriculas(cambios)
        todos_resultados.extend(resultados_mat_bajas)
        
        # Resumen final
        self.resultados = todos_resultados
        
        exitosos = sum(1 for r in todos_resultados if r.exito)
        fallidos = sum(1 for r in todos_resultados if not r.exito)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"RESUMEN DE APLICACIÓN - {modo}")
        logger.info(f"{'='*60}")
        logger.info(f"Operaciones exitosas: {exitosos}")
        logger.info(f"Operaciones fallidas: {fallidos}")
        logger.info(f"Datos personales actualizados: {self.estadisticas['datos_personales_actualizados']}")
        logger.info(f"Usuarios creados: {self.estadisticas['usuarios_creados']}")
        logger.info(f"Usuarios suspendidos: {self.estadisticas['usuarios_suspendidos']}")
        logger.info(f"Usuarios reactivados: {self.estadisticas['usuarios_reactivados']}")
        logger.info(f"Matrículas creadas: {self.estadisticas['matriculas_creadas']}")
        logger.info(f"Matrículas suspendidas: {self.estadisticas['matriculas_suspendidas']}")
        logger.info(f"Errores: {self.estadisticas['errores']}")
        logger.info(f"{'='*60}")
        
        return {
            'estadisticas': self.estadisticas,
            'resultados': todos_resultados,
            'exitosos': exitosos,
            'fallidos': fallidos,
            'modo': modo
        }
    
    # =================================================================
    # 5. UTILIDADES
    # =================================================================
    
    def _generar_password_temporal(self, documento: str) -> str:
        """Genera un password temporal basado en el documento."""
        # Formato: Primeras 3 letras del doc + @ + últimas 3 + año actual
        prefijo = documento[:3] if len(documento) >= 3 else documento
        sufijo = documento[-3:] if len(documento) >= 3 else documento
        anio = datetime.now().year
        return f"{prefijo}@{sufijo}{anio}"
    
    def _obtener_userid_por_username(self, username: str) -> Optional[int]:
        """Obtiene el userid de un usuario recién creado."""
        try:
            cmd = f"moosh -n user-list 'username = \"{username}\"'"
            output = run_moosh_command(self.moodle, cmd, capture=True, timeout=10)
            
            # Parsear output: "username (userid), email, ..."
            match = re.search(r'\((\d+)\)', output)
            if match:
                return int(match.group(1))
        except Exception as e:
            logger.error(f"Error obteniendo userid de {username}: {e}")
        return None


# =============================================================================
# FUNCIONES DE ALTO NIVEL
# =============================================================================

def aplicar_cambios_sigad(cambios: Dict, moodle_container: str, 
                          mapeo_cursos: Dict[str, int] = None,
                          dry_run: bool = True) -> Dict:
    """
    Función de alto nivel para aplicar cambios.
    
    Args:
        cambios: Diccionario con cambios detectados
        moodle_container: Nombre del contenedor Docker
        mapeo_cursos: Mapeo sigla_modulo -> courseid
        dry_run: Si True, solo simula sin ejecutar
        
    Returns:
        Dict con resultados y estadísticas
    """
    aplicador = AplicadorCambiosSigad(moodle_container, dry_run=dry_run)
    return aplicador.aplicar_todos_los_cambios(cambios, mapeo_cursos)
