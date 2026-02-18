"""
Módulo para sincronización de datos SIGAD con base de datos Moodle.

Este módulo permite:
1. Insertar datos del diccionario registro_sigad en tabla auxiliar
2. Comparar datos SIGAD contra tablas reales de Moodle (mdl_user, mdl_enrol, etc.)
3. Detectar cambios necesarios: nuevos, bajas, modificaciones, matrículas
4. Generar reportes de acciones pendientes

Uso:
    from gestion_alumnos.utils.sigad_db_sync import SigadDatabaseSync
    
    sync = SigadDatabaseSync()
    sync.truncate_and_insert(registro_sigad)
    cambios = sync.detectar_cambios_vs_moodle()
"""

import os
import pymysql
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dotenv import load_dotenv

from gestion_alumnos.logger_config import logger

# Cargar variables de entorno
load_dotenv()


class SigadDatabaseSync:
    """
    Clase para gestionar la sincronización de datos SIGAD con Moodle.
    
    La estrategia es:
    1. Limpiar tabla auxiliar e insertar datos actuales de SIGAD
    2. Usar vistas SQL que comparen tabla auxiliar vs tablas de Moodle
    3. Detectar diferencias y generar acciones a realizar
    """
    
    def __init__(self):
        """Inicializa la conexión usando variables de entorno."""
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASS'),
            'database': os.getenv('DB_NAME'),
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor
        }
        self.connection = None
        self.fecha_sync = None
        self.hora_sync = None
        
    def conectar(self) -> bool:
        """Establece conexión con la base de datos."""
        try:
            self.connection = pymysql.connect(**self.db_config)
            logger.info(f"✓ Conexión establecida con la BD: {self.db_config['database']}")
            return True
        except pymysql.Error as e:
            logger.error(f"✗ Error al conectar con la BD: {e}")
            return False
    
    def desconectar(self):
        """Cierra la conexión con la base de datos."""
        if self.connection:
            self.connection.close()
            logger.info("✓ Conexión con la BD cerrada")
    
    def truncate_tabla_auxiliar(self) -> bool:
        """
        Limpia la tabla auxiliar para insertar nuevos datos.
        
        Returns:
            True si se truncó correctamente
        """
        if not self.connection:
            if not self.conectar():
                return False
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("TRUNCATE TABLE mdl_aux_sigad_matriculas")
                self.connection.commit()
                logger.info("✓ Tabla auxiliar limpiada (TRUNCATE)")
                return True
        except pymysql.Error as e:
            logger.error(f"✗ Error al truncar tabla: {e}")
            return False
    
    def insertar_registro_sigad(self, registro_dict: Dict[str, Any]) -> int:
        """
        Inserta datos desde un diccionario registro_sigad en la tabla auxiliar.
        
        Args:
            registro_dict: Diccionario con claves 'fecha', 'hora', 'alumnos'
            
        Returns:
            Número de filas insertadas
        """
        if not self.connection:
            if not self.conectar():
                return 0
        
        # Parsear fecha y hora del registro
        try:
            fecha_str = registro_dict.get('fecha', datetime.now().strftime('%d/%m/%Y'))
            hora_str = registro_dict.get('hora', datetime.now().strftime('%H:%M:%S'))
            self.fecha_sync = datetime.strptime(fecha_str, '%d/%m/%Y').date()
            self.hora_sync = datetime.strptime(hora_str, '%H:%M:%S').time()
        except ValueError:
            self.fecha_sync = datetime.now().date()
            self.hora_sync = datetime.now().time()
        
        filas_insertadas = 0
        alumnos = registro_dict.get('alumnos', [])
        
        sql = """
            INSERT INTO mdl_aux_sigad_matriculas 
                (sigad_idalumno, sigad_idtipodocumento, sigad_documento, sigad_nombre,
                 sigad_apellido1, sigad_apellido2, sigad_email, sigad_codigocentro,
                 sigad_centro, sigad_idficha, sigad_codigociclo, sigad_ciclo, 
                 sigad_siglasciclo, sigad_idmateria, sigad_modulo, sigad_siglasmodulo,
                 fecha_sincronizacion, hora_sincronizacion)
            VALUES 
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        try:
            with self.connection.cursor() as cursor:
                for alumno in alumnos:
                    for centro in alumno.get('centros', []):
                        for ciclo in centro.get('ciclos', []):
                            for modulo in ciclo.get('modulos', []):
                                valores = (
                                    alumno.get('idAlumno'),
                                    alumno.get('idTipoDocumento'),
                                    alumno.get('documento'),
                                    alumno.get('nombre'),
                                    alumno.get('apellido1'),
                                    alumno.get('apellido2'),
                                    alumno.get('email'),
                                    centro.get('codigoCentro'),
                                    centro.get('centro'),
                                    ciclo.get('idFicha'),
                                    ciclo.get('codigoCiclo'),
                                    ciclo.get('ciclo'),
                                    ciclo.get('siglasCiclo'),
                                    modulo.get('idMateria'),
                                    modulo.get('modulo'),
                                    modulo.get('siglasModulo'),
                                    self.fecha_sync,
                                    self.hora_sync
                                )
                                cursor.execute(sql, valores)
                                filas_insertadas += 1
                
                self.connection.commit()
                logger.info(f"✓ Insertadas {filas_insertadas} filas en tabla auxiliar")
                
        except pymysql.Error as e:
            self.connection.rollback()
            logger.error(f"✗ Error al insertar datos: {e}")
            raise
        
        return filas_insertadas
    
    def truncate_and_insert(self, registro_dict: Dict[str, Any]) -> int:
        """
        Operación completa: limpia tabla auxiliar e inserta nuevos datos.
        
        Args:
            registro_dict: Diccionario registro_sigad
            
        Returns:
            Número de filas insertadas
        """
        self.truncate_tabla_auxiliar()
        return self.insertar_registro_sigad(registro_dict)
    
    def detectar_cambios_vs_moodle(self) -> Dict[str, List[Dict]]:
        """
        Detecta cambios comparando tabla auxiliar (SIGAD) vs tablas de Moodle.
        
        Returns:
            Diccionario con listas de cambios por tipo
        """
        if not self.connection:
            if not self.conectar():
                return {}
        
        cambios = {
            'alumnos_nuevos': [],           # En SIGAD, no en Moodle
            'alumnos_baja': [],             # En Moodle activos, no en SIGAD
            'alumnos_reactivar': [],        # En Moodle suspendidos, sí en SIGAD
            'cambios_email': [],            # Email diferente
            'cambios_documento': [],        # DNI/NIE cambió
            'matriculas_nuevas': [],        # Módulo en SIGAD, no matriculado en Moodle
            'matriculas_baja': [],          # Matriculado en Moodle, no en SIGAD
            'resumen': {}
        }
        
        try:
            with self.connection.cursor() as cursor:
                
                # 1. Alumnos nuevos (en SIGAD, no en Moodle)
                cursor.execute("""
                    SELECT DISTINCT
                        s.sigad_idalumno,
                        s.sigad_documento,
                        s.sigad_idtipodocumento,
                        s.sigad_nombre,
                        s.sigad_apellido1,
                        s.sigad_apellido2,
                        s.sigad_email,
                        GROUP_CONCAT(DISTINCT s.sigad_siglasciclo SEPARATOR ', ') AS ciclos
                    FROM mdl_aux_sigad_matriculas s
                    LEFT JOIN v_moodle_alumnos m ON m.moodle_documento = LOWER(s.sigad_documento)
                    WHERE m.moodle_userid IS NULL
                    GROUP BY s.sigad_idalumno, s.sigad_documento, s.sigad_idtipodocumento,
                             s.sigad_nombre, s.sigad_apellido1, s.sigad_apellido2, s.sigad_email
                """)
                cambios['alumnos_nuevos'] = cursor.fetchall()
                
                # 2. Alumnos de baja (en Moodle activos, no en SIGAD)
                cursor.execute("""
                    SELECT 
                        m.moodle_userid,
                        m.moodle_documento,
                        m.moodle_nombre,
                        m.moodle_apellidos,
                        m.moodle_email,
                        m.moodle_lastlogin
                    FROM v_moodle_alumnos m
                    LEFT JOIN mdl_aux_sigad_matriculas s ON LOWER(s.sigad_documento) = m.moodle_documento
                    WHERE s.sigad_idalumno IS NULL
                      AND m.moodle_suspended = 0
                    ORDER BY m.moodle_lastlogin DESC
                """)
                cambios['alumnos_baja'] = cursor.fetchall()
                
                # 3. Alumnos a reactivar (suspendidos en Moodle, activos en SIGAD)
                cursor.execute("""
                    SELECT 
                        s.sigad_idalumno,
                        s.sigad_documento,
                        s.sigad_nombre,
                        s.sigad_apellido1,
                        s.sigad_email,
                        m.moodle_userid,
                        m.moodle_email AS email_actual_moodle
                    FROM mdl_aux_sigad_matriculas s
                    INNER JOIN v_moodle_alumnos m ON m.moodle_documento = LOWER(s.sigad_documento)
                    WHERE m.moodle_suspended = 1
                    GROUP BY s.sigad_idalumno, s.sigad_documento, s.sigad_nombre, 
                             s.sigad_apellido1, s.sigad_email, m.moodle_userid, m.moodle_email
                """)
                cambios['alumnos_reactivar'] = cursor.fetchall()
                
                # 4. Cambios de email
                cursor.execute("""
                    SELECT 
                        s.sigad_idalumno,
                        s.sigad_documento,
                        s.sigad_nombre,
                        s.sigad_apellido1,
                        m.moodle_userid,
                        m.moodle_email AS email_en_moodle,
                        s.sigad_email AS email_en_sigad
                    FROM mdl_aux_sigad_matriculas s
                    INNER JOIN v_moodle_alumnos m ON m.moodle_documento = LOWER(s.sigad_documento)
                    WHERE m.moodle_email <> s.sigad_email
                    GROUP BY s.sigad_idalumno, s.sigad_documento, s.sigad_nombre, 
                             s.sigad_apellido1, m.moodle_userid, m.moodle_email, s.sigad_email
                """)
                cambios['cambios_email'] = cursor.fetchall()
                
                # 5. Posibles cambios de documento (NIE→DNI)
                cursor.execute("""
                    SELECT 
                        s.sigad_idalumno,
                        s.sigad_documento AS documento_sigad,
                        m.moodle_documento AS username_moodle,
                        s.sigad_nombre,
                        s.sigad_apellido1,
                        m.moodle_userid
                    FROM mdl_aux_sigad_matriculas s
                    INNER JOIN v_moodle_alumnos m ON m.moodle_email = s.sigad_email
                    WHERE LOWER(s.sigad_documento) <> m.moodle_documento
                """)
                cambios['cambios_documento'] = cursor.fetchall()
                
                # 6. Matrículas nuevas necesarias
                cursor.execute("""
                    SELECT 
                        s.sigad_idalumno,
                        s.sigad_documento,
                        s.sigad_nombre,
                        s.sigad_apellido1,
                        s.sigad_siglasciclo,
                        s.sigad_siglasmodulo,
                        s.sigad_modulo,
                        m.moodle_userid,
                        m.moodle_courseid,
                        m.moodle_course_shortname,
                        CASE 
                            WHEN m.moodle_courseid IS NULL THEN 'CREAR_CURSO'
                            WHEN m.moodle_enrol_status = 1 THEN 'REACTIVAR_MATRICULA'
                            ELSE 'MATRICULAR'
                        END AS accion_requerida
                    FROM mdl_aux_sigad_matriculas s
                    INNER JOIN v_moodle_alumnos ma ON ma.moodle_documento = LOWER(s.sigad_documento)
                    LEFT JOIN v_moodle_matriculas m ON m.moodle_userid = ma.moodle_userid 
                        AND (m.moodle_course_shortname LIKE CONCAT('%', s.sigad_siglasmodulo, '%')
                             OR m.moodle_course_fullname LIKE CONCAT('%', s.sigad_modulo, '%'))
                    WHERE (m.moodle_enrol_status IS NULL OR m.moodle_enrol_status = 1)
                    ORDER BY s.sigad_documento, s.sigad_siglasmodulo
                """)
                cambios['matriculas_nuevas'] = cursor.fetchall()
                
                # 7. Matrículas a dar de baja
                cursor.execute("""
                    SELECT 
                        m.moodle_userid,
                        m.moodle_documento,
                        m.moodle_nombre,
                        m.moodle_apellidos,
                        m.moodle_courseid,
                        m.moodle_course_shortname,
                        m.moodle_course_fullname
                    FROM v_moodle_matriculas m
                    INNER JOIN v_moodle_alumnos ma ON ma.moodle_userid = m.moodle_userid
                    LEFT JOIN mdl_aux_sigad_matriculas s ON LOWER(s.sigad_documento) = ma.moodle_documento
                        AND (m.moodle_course_shortname LIKE CONCAT('%', s.sigad_siglasmodulo, '%')
                             OR m.moodle_course_fullname LIKE CONCAT('%', s.sigad_modulo, '%'))
                    WHERE s.sigad_idmateria IS NULL
                      AND m.moodle_enrol_status = 0
                      AND m.moodle_course_shortname NOT LIKE '%tutoria%'
                    ORDER BY m.moodle_documento, m.moodle_course_shortname
                """)
                cambios['matriculas_baja'] = cursor.fetchall()
                
                # 8. Resumen ejecutivo
                cursor.execute("""
                    SELECT 
                        'ALUMNOS_NUEVOS' AS categoria,
                        COUNT(DISTINCT s.sigad_idalumno) AS cantidad
                    FROM mdl_aux_sigad_matriculas s
                    LEFT JOIN v_moodle_alumnos m ON m.moodle_documento = LOWER(s.sigad_documento)
                    WHERE m.moodle_userid IS NULL
                    
                    UNION ALL
                    
                    SELECT 
                        'ALUMNOS_BAJA',
                        COUNT(DISTINCT m.moodle_userid)
                    FROM v_moodle_alumnos m
                    LEFT JOIN mdl_aux_sigad_matriculas s ON LOWER(s.sigad_documento) = m.moodle_documento
                    WHERE s.sigad_idalumno IS NULL AND m.moodle_suspended = 0
                    
                    UNION ALL
                    
                    SELECT 
                        'ALUMNOS_REACTIVAR',
                        COUNT(DISTINCT m.moodle_userid)
                    FROM v_moodle_alumnos m
                    INNER JOIN mdl_aux_sigad_matriculas s ON LOWER(s.sigad_documento) = m.moodle_documento
                    WHERE m.moodle_suspended = 1
                    
                    UNION ALL
                    
                    SELECT 
                        'EMAILS_ACTUALIZAR',
                        COUNT(DISTINCT s.sigad_idalumno)
                    FROM mdl_aux_sigad_matriculas s
                    INNER JOIN v_moodle_alumnos m ON m.moodle_documento = LOWER(s.sigad_documento)
                    WHERE m.moodle_email <> s.sigad_email
                    
                    UNION ALL
                    
                    SELECT 
                        'MATRICULAS_NUEVAS',
                        COUNT(*)
                    FROM mdl_aux_sigad_matriculas s
                    INNER JOIN v_moodle_alumnos ma ON ma.moodle_documento = LOWER(s.sigad_documento)
                    LEFT JOIN v_moodle_matriculas m ON m.moodle_userid = ma.moodle_userid 
                        AND (m.moodle_course_shortname LIKE CONCAT('%', s.sigad_siglasmodulo, '%'))
                    WHERE m.moodle_enrol_status IS NULL
                    
                    UNION ALL
                    
                    SELECT 
                        'MATRICULAS_BAJA',
                        COUNT(*)
                    FROM v_moodle_matriculas m
                    INNER JOIN v_moodle_alumnos ma ON ma.moodle_userid = m.moodle_userid
                    LEFT JOIN mdl_aux_sigad_matriculas s ON LOWER(s.sigad_documento) = ma.moodle_documento
                        AND (m.moodle_course_shortname LIKE CONCAT('%', s.sigad_siglasmodulo, '%'))
                    WHERE s.sigad_idmateria IS NULL AND m.moodle_enrol_status = 0
                """)
                resumen = cursor.fetchall()
                cambios['resumen'] = {r['categoria']: r['cantidad'] for r in resumen}
                
        except pymysql.Error as e:
            logger.error(f"Error al detectar cambios: {e}")
            raise
        
        total_cambios = sum(len(v) for k, v in cambios.items() if k != 'resumen')
        logger.info(f"Detección completada: {total_cambios} cambios encontrados")
        
        return cambios
    
    def obtener_vista_comparativa(self, vista: str = 'v_comp_alumnos_sigad_vs_moodle') -> List[Dict]:
        """
        Obtiene datos de una vista comparativa.
        
        Args:
            vista: Nombre de la vista a consultar
            
        Returns:
            Lista de registros de la vista
        """
        if not self.connection:
            if not self.conectar():
                return []
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(f"SELECT * FROM {vista}")
                return cursor.fetchall()
        except pymysql.Error as e:
            logger.error(f"Error al consultar vista {vista}: {e}")
            return []
    
    def generar_reporte_cambios(self, cambios: Dict[str, List[Dict]]) -> str:
        """
        Genera un resumen en texto de los cambios detectados.
        
        Args:
            cambios: Diccionario con los cambios detectados
            
        Returns:
            String con el resumen formateado
        """
        lineas = [
            "=" * 70,
            "REPORTE DE SINCRONIZACIÓN SIGAD -> MOODLE",
            "=" * 70,
            f"Fecha sincronización: {self.fecha_sync} {self.hora_sync}",
            ""
        ]
        
        # Resumen ejecutivo
        lineas.append("RESUMEN EJECUTIVO:")
        lineas.append("-" * 40)
        for categoria, cantidad in cambios.get('resumen', {}).items():
            lineas.append(f"  {categoria}: {cantidad}")
        
        # Detalle por categoría
        for tipo, registros in cambios.items():
            if tipo == 'resumen' or not registros:
                continue
            
            lineas.append(f"\n{tipo.upper().replace('_', ' ')}: {len(registros)}")
            lineas.append("-" * 40)
            
            for r in registros[:10]:  # Mostrar solo los primeros 10
                if tipo == 'alumnos_nuevos':
                    lineas.append(f"  + {r['sigad_nombre']} {r['sigad_apellido1']} ({r['sigad_documento']}) - {r['sigad_email']}")
                elif tipo == 'alumnos_baja':
                    lineas.append(f"  - {r['moodle_nombre']} {r['moodle_apellidos']} ({r['moodle_documento']})")
                elif tipo == 'alumnos_reactivar':
                    lineas.append(f"  ↑ {r['sigad_nombre']} {r['sigad_apellido1']} ({r['sigad_documento']})")
                elif tipo == 'cambios_email':
                    lineas.append(f"  ~ {r['sigad_nombre']} {r['sigad_apellido1']}: {r['email_en_moodle']} -> {r['email_en_sigad']}")
                elif tipo == 'matriculas_nuevas':
                    lineas.append(f"  + {r['sigad_siglasmodulo']} -> {r['sigad_nombre']} {r['sigad_apellido1']}")
                elif tipo == 'matriculas_baja':
                    lineas.append(f"  - {r['moodle_course_shortname']} -> {r['moodle_nombre']} {r['moodle_apellidos']}")
            
            if len(registros) > 10:
                lineas.append(f"  ... y {len(registros) - 10} más")
        
        lineas.append("\n" + "=" * 70)
        return "\n".join(lineas)


# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

def sincronizar_y_detectar(registro_dict: Dict[str, Any]) -> Tuple[int, Dict]:
    """
    Función de alto nivel: limpia, inserta y detecta cambios.
    
    Args:
        registro_dict: Diccionario registro_sigad
        
    Returns:
        Tupla (filas_insertadas, cambios_detectados)
    """
    sync = SigadDatabaseSync()
    
    try:
        # Limpiar e insertar
        filas = sync.truncate_and_insert(registro_dict)
        
        # Detectar cambios vs Moodle
        cambios = sync.detectar_cambios_vs_moodle()
        
        # Generar y mostrar reporte
        reporte = sync.generar_reporte_cambios(cambios)
        logger.info("\n" + reporte)
        
        return filas, cambios
        
    except Exception as e:
        logger.error(f"Error en sincronización: {e}")
        raise
    finally:
        sync.desconectar()


def solo_detectar_cambios() -> Dict:
    """
    Detecta cambios sin insertar (asume que tabla auxiliar ya tiene datos).
    
    Returns:
        Diccionario con cambios detectados
    """
    sync = SigadDatabaseSync()
    
    try:
        cambios = sync.detectar_cambios_vs_moodle()
        reporte = sync.generar_reporte_cambios(cambios)
        logger.info("\n" + reporte)
        return cambios
    finally:
        sync.desconectar()
