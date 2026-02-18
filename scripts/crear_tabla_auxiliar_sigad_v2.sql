-- =============================================================================
-- TABLA AUXILIAR Y VISTAS PARA SINCRONIZACIÓN SIGAD <-> MOODLE
-- =============================================================================
-- Objetivo: Comparar datos de SIGAD (tabla auxiliar) con datos reales de Moodle
-- Estrategia: Crear vistas que transformen tablas Moodle al formato SIGAD
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. TABLA AUXILIAR: Últimos datos de SIGAD (solo un batch activo)
-- -----------------------------------------------------------------------------
DROP TABLE IF EXISTS mdl_aux_sigad_matriculas;

CREATE TABLE mdl_aux_sigad_matriculas (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    
    -- Datos del alumno desde SIGAD
    sigad_idalumno INT UNSIGNED NOT NULL COMMENT 'ID único en SIGAD',
    sigad_idtipodocumento TINYINT UNSIGNED COMMENT '1=DNI, 2=NIE, 3=PASAPORTE',
    sigad_documento VARCHAR(20) NOT NULL COMMENT 'DNI/NIE sin espacios',
    sigad_nombre VARCHAR(100) NOT NULL,
    sigad_apellido1 VARCHAR(100) NOT NULL,
    sigad_apellido2 VARCHAR(100) NULL,
    sigad_email VARCHAR(255) NOT NULL,
    
    -- Datos del centro/ciclo/módulo desde SIGAD
    sigad_codigocentro VARCHAR(20) NOT NULL,
    sigad_centro VARCHAR(200) NOT NULL,
    sigad_idficha INT UNSIGNED NOT NULL,
    sigad_codigociclo VARCHAR(20) NOT NULL,
    sigad_ciclo VARCHAR(200) NOT NULL,
    sigad_siglasciclo VARCHAR(20) NOT NULL,
    sigad_idmateria INT UNSIGNED NOT NULL,
    sigad_modulo VARCHAR(255) NOT NULL,
    sigad_siglasmodulo VARCHAR(50) NOT NULL,
    
    -- Metadatos
    fecha_sincronizacion DATE NOT NULL,
    hora_sincronizacion TIME NOT NULL,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Índices
    UNIQUE KEY uk_matricula (sigad_idalumno, sigad_codigocentro, sigad_idficha, sigad_idmateria),
    KEY idx_alumno (sigad_idalumno),
    KEY idx_documento (sigad_documento),
    KEY idx_centro_ciclo (sigad_codigocentro, sigad_codigociclo),
    KEY idx_materia (sigad_idmateria)
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Datos actuales de SIGAD para comparación con Moodle';


-- -----------------------------------------------------------------------------
-- 2. VISTA: Alumnos en Moodle transformados al formato SIGAD
-- -----------------------------------------------------------------------------
-- Esta vista transforma mdl_user al formato de la tabla auxiliar SIGAD
-- -----------------------------------------------------------------------------
DROP VIEW IF EXISTS v_moodle_alumnos;

CREATE VIEW v_moodle_alumnos AS
SELECT 
    u.id AS moodle_userid,
    LOWER(TRIM(u.username)) AS moodle_documento,
    u.email AS moodle_email,
    u.firstname AS moodle_nombre,
    u.lastname AS moodle_apellidos,
    -- Separar apellido1 y apellido2 (suponiendo que van separados por espacio)
    SUBSTRING_INDEX(u.lastname, ' ', 1) AS moodle_apellido1,
    CASE 
        WHEN LOCATE(' ', u.lastname) > 0 
        THEN SUBSTRING(u.lastname, LOCATE(' ', u.lastname) + 1)
        ELSE NULL 
    END AS moodle_apellido2,
    u.suspended AS moodle_suspended,
    u.deleted AS moodle_deleted,
    u.lastlogin AS moodle_lastlogin,
    -- Intentar obtener idAlumno de SIGAD desde campos personalizados si existe
    (SELECT data FROM mdl_user_info_data WHERE userid = u.id AND fieldid = 1 LIMIT 1) AS moodle_sigad_idalumno
FROM mdl_user u
WHERE u.deleted = 0
  AND LOWER(u.username) NOT LIKE 'prof%'  -- Excluir profesores
  AND LOWER(u.username) NOT LIKE 'admin%' -- Excluir admins
  AND LENGTH(TRIM(u.username)) > 0;


-- -----------------------------------------------------------------------------
-- 3. VISTA: Matrículas en cursos de Moodle transformadas al formato SIGAD
-- -----------------------------------------------------------------------------
-- Une usuarios con sus matrículas en cursos, transformando al formato SIGAD
-- -----------------------------------------------------------------------------
DROP VIEW IF EXISTS v_moodle_matriculas;

CREATE VIEW v_moodle_matriculas AS
SELECT 
    u.id AS moodle_userid,
    LOWER(TRIM(u.username)) AS moodle_documento,
    u.email AS moodle_email,
    u.firstname AS moodle_nombre,
    u.lastname AS moodle_apellidos,
    c.id AS moodle_courseid,
    c.shortname AS moodle_course_shortname,
    c.fullname AS moodle_course_fullname,
    ue.status AS moodle_enrol_status,  -- 0=activa, 1=suspendida
    ue.timestart AS moodle_enrol_start,
    ue.timeend AS moodle_enrol_end,
    e.enrol AS moodle_enrol_method,
    -- Extraer posible código de centro del curso (ajustar según convención)
    CASE 
        WHEN c.shortname LIKE '%-%' THEN SUBSTRING_INDEX(c.shortname, '-', 1)
        ELSE 'UNKNOWN'
    END AS extracted_centro,
    -- Extraer posible código de ciclo (ajustar según convención)
    CASE 
        WHEN c.shortname REGEXP '^[A-Z]{3}[0-9]{3}' THEN LEFT(c.shortname, 6)
        ELSE c.shortname
    END AS extracted_ciclo
FROM mdl_user u
INNER JOIN mdl_user_enrolments ue ON ue.userid = u.id
INNER JOIN mdl_enrol e ON e.id = ue.enrolid
INNER JOIN mdl_course c ON c.id = e.courseid
WHERE u.deleted = 0
  AND LOWER(u.username) NOT LIKE 'prof%'
  AND LOWER(u.username) NOT LIKE 'admin%';


-- -----------------------------------------------------------------------------
-- 4. VISTA: Cohortes de alumnado en Moodle
-- -----------------------------------------------------------------------------
DROP VIEW IF EXISTS v_moodle_cohortes_alumnado;

CREATE VIEW v_moodle_cohortes_alumnado AS
SELECT 
    u.id AS moodle_userid,
    LOWER(TRIM(u.username)) AS moodle_documento,
    u.email AS moodle_email,
    u.firstname AS moodle_nombre,
    u.lastname AS moodle_apellidos,
    c.id AS cohorte_id,
    c.name AS cohorte_name,
    c.idnumber AS cohorte_idnumber,
    cm.timeadded AS cohorte_fecha_matricula
FROM mdl_user u
INNER JOIN mdl_cohort_members cm ON cm.userid = u.id
INNER JOIN mdl_cohort c ON c.id = cm.cohortid
WHERE u.deleted = 0
  AND LOWER(u.username) NOT LIKE 'prof%'
  AND LOWER(c.name) LIKE '%alumn%'  -- Cohortes de alumnado
  AND u.suspended = 0;


-- -----------------------------------------------------------------------------
-- 5. VISTA: Resumen comparativo SIGAD vs Moodle (usuarios)
-- -----------------------------------------------------------------------------
DROP VIEW IF EXISTS v_comp_alumnos_sigad_vs_moodle;

CREATE VIEW v_comp_alumnos_sigad_vs_moodle AS
SELECT 
    -- Datos SIGAD
    s.sigad_idalumno,
    s.sigad_documento,
    s.sigad_nombre,
    s.sigad_apellido1,
    s.sigad_apellido2,
    s.sigad_email,
    
    -- Datos Moodle
    m.moodle_userid,
    m.moodle_documento,
    m.moodle_nombre,
    m.moodle_apellido1,
    m.moodle_apellido2,
    m.moodle_email,
    m.moodle_suspended,
    m.moodle_deleted,
    
    -- Flags de comparación
    CASE WHEN m.moodle_userid IS NULL THEN 'NO_EXISTE_EN_MOODLE'
         WHEN m.moodle_suspended = 1 THEN 'SUSPENDIDO_EN_MOODLE'
         ELSE 'ACTIVO_EN_MOODLE'
    END AS estado_en_moodle,
    
    CASE WHEN m.moodle_email <> s.sigad_email THEN 'EMAIL_DIFERENTE'
         ELSE 'EMAIL_OK'
    END AS comparacion_email,
    
    CASE WHEN m.moodle_documento <> LOWER(s.sigad_documento) THEN 'DOCUMENTO_DIFERENTE'
         ELSE 'DOCUMENTO_OK'
    END AS comparacion_documento,
    
    CASE WHEN CONCAT(m.moodle_nombre, ' ', m.moodle_apellidos) <> 
              CONCAT(s.sigad_nombre, ' ', s.sigad_apellido1, ' ', COALESCE(s.sigad_apellido2, ''))
         THEN 'NOMBRE_DIFERENTE'
         ELSE 'NOMBRE_OK'
    END AS comparacion_nombre

FROM mdl_aux_sigad_matriculas s
LEFT JOIN v_moodle_alumnos m ON m.moodle_documento = LOWER(s.sigad_documento)

UNION

-- Alumnos que están en Moodle pero NO en SIGAD (para detectar bajas)
SELECT 
    NULL AS sigad_idalumno,
    NULL AS sigad_documento,
    NULL AS sigad_nombre,
    NULL AS sigad_apellido1,
    NULL AS sigad_apellido2,
    NULL AS sigad_email,
    
    m.moodle_userid,
    m.moodle_documento,
    m.moodle_nombre,
    m.moodle_apellido1,
    m.moodle_apellido2,
    m.moodle_email,
    m.moodle_suspended,
    m.moodle_deleted,
    
    'SOLO_EN_MOODLE_NO_EN_SIGAD' AS estado_en_moodle,
    'N/A' AS comparacion_email,
    'N/A' AS comparacion_documento,
    'N/A' AS comparacion_nombre

FROM v_moodle_alumnos m
LEFT JOIN mdl_aux_sigad_matriculas s ON LOWER(s.sigad_documento) = m.moodle_documento
WHERE s.sigad_idalumno IS NULL
  AND m.moodle_suspended = 0;  -- Solo activos (los suspendidos ya están gestionados);


-- -----------------------------------------------------------------------------
-- 6. VISTA: Comparación de matrículas en módulos SIGAD vs Moodle
-- -----------------------------------------------------------------------------
DROP VIEW IF EXISTS v_comp_matriculas_sigad_vs_moodle;

CREATE VIEW v_comp_matriculas_sigad_vs_moodle AS
-- Módulos en SIGAD que deberían estar en Moodle (matrículas necesarias)
SELECT 
    'MATRICULA_NECESARIA_EN_MOODLE' AS tipo_accion,
    s.sigad_idalumno,
    s.sigad_documento,
    s.sigad_nombre,
    s.sigad_apellido1,
    s.sigad_siglasciclo,
    s.sigad_siglasmodulo,
    s.sigad_idmateria,
    m.moodle_userid,
    m.moodle_courseid,
    m.moodle_course_shortname,
    m.moodle_enrol_status,
    CASE 
        WHEN m.moodle_courseid IS NULL THEN 'CURSO_NO_EXISTE'
        WHEN m.moodle_enrol_status = 1 THEN 'MATRICULA_SUSPENDIDA'
        WHEN m.moodle_enrol_status = 0 THEN 'YA_MATRICULADO'
        ELSE 'SIN_MATRICULAR'
    END AS estado_matricula_moodle
FROM mdl_aux_sigad_matriculas s
LEFT JOIN v_moodle_alumnos ma ON ma.moodle_documento = LOWER(s.sigad_documento)
LEFT JOIN v_moodle_matriculas m ON m.moodle_userid = ma.moodle_userid 
    AND m.moodle_course_shortname LIKE CONCAT('%', s.sigad_siglasmodulo, '%')

UNION ALL

-- Matrículas en Moodle que no están en SIGAD (posibles bajas)
SELECT 
    'POSIBLE_BAJA_EN_MOODLE' AS tipo_accion,
    s.sigad_idalumno,
    s.sigad_documento,
    NULL AS sigad_nombre,
    NULL AS sigad_apellido1,
    NULL AS sigad_siglasciclo,
    NULL AS sigad_siglasmodulo,
    NULL AS sigad_idmateria,
    m.moodle_userid,
    m.moodle_courseid,
    m.moodle_course_shortname,
    m.moodle_enrol_status,
    'MATRICULA_EXISTE_EN_MOODLE' AS estado_matricula_moodle
FROM v_moodle_matriculas m
INNER JOIN v_moodle_alumnos ma ON ma.moodle_userid = m.moodle_userid
LEFT JOIN mdl_aux_sigad_matriculas s ON LOWER(s.sigad_documento) = ma.moodle_documento
    AND m.moodle_course_shortname LIKE CONCAT('%', s.sigad_siglasmodulo, '%')
WHERE s.sigad_idalumno IS NULL
  AND m.moodle_course_shortname NOT LIKE '%tutoria%'  -- Excluir cursos de tutoría
  AND m.moodle_enrol_status = 0;  -- Solo matrículas activas;


-- =============================================================================
-- 7. QUERIES PRÁCTICAS PARA DETECTAR CAMBIOS
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 7.1 ALUMNOS NUEVOS: En SIGAD pero NO en Moodle
-- -----------------------------------------------------------------------------
-- Resultado: Alumnos que deben CREARSE en Moodle
-- -----------------------------------------------------------------------------
SELECT 
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
         s.sigad_nombre, s.sigad_apellido1, s.sigad_apellido2, s.sigad_email;


-- -----------------------------------------------------------------------------
-- 7.2 ALUMNOS DADOS DE BAJA: En Moodle activos pero NO en SIGAD
-- -----------------------------------------------------------------------------
-- Resultado: Alumnos que deben SUSPENDERSE en Moodle
-- -----------------------------------------------------------------------------
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
ORDER BY m.moodle_lastlogin DESC;


-- -----------------------------------------------------------------------------
-- 7.3 ALUMNOS REACTIVAR: En Moodle suspendidos pero SÍ en SIGAD
-- -----------------------------------------------------------------------------
-- Resultado: Alumnos que deben REACTIVARSE en Moodle
-- -----------------------------------------------------------------------------
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
         s.sigad_apellido1, s.sigad_email, m.moodle_userid, m.moodle_email;


-- -----------------------------------------------------------------------------
-- 7.4 CAMBIOS DE EMAIL
-- -----------------------------------------------------------------------------
-- Resultado: Alumnos cuyo email difiere entre SIGAD y Moodle
-- -----------------------------------------------------------------------------
SELECT 
    s.sigad_idalumno,
    s.sigad_documento,
    s.sigad_nombre,
    s.sigad_apellido1,
    m.moodle_userid,
    m.moodle_email AS email_en_moodle,
    s.sigad_email AS email_en_sigad,
    CASE 
        WHEN m.moodle_email = '' THEN 'VACIO_EN_MOODLE'
        WHEN m.moodle_email IS NULL THEN 'NULL_EN_MOODLE'
        ELSE 'DIFERENTE'
    END AS tipo_diferencia
FROM mdl_aux_sigad_matriculas s
INNER JOIN v_moodle_alumnos m ON m.moodle_documento = LOWER(s.sigad_documento)
WHERE m.moodle_email <> s.sigad_email
GROUP BY s.sigad_idalumno, s.sigad_documento, s.sigad_nombre, 
         s.sigad_apellido1, m.moodle_userid, m.moodle_email, s.sigad_email;


-- -----------------------------------------------------------------------------
-- 7.5 CAMBIOS DE DOCUMENTO (DNI/NIE)
-- -----------------------------------------------------------------------------
-- Resultado: Casos donde el username de Moodle no coincide con SIGAD
-- (puede pasar cuando cambian de NIE a DNI)
-- -----------------------------------------------------------------------------
SELECT 
    s.sigad_idalumno,
    s.sigad_documento AS documento_sigad,
    m.moodle_documento AS username_moodle,
    s.sigad_nombre,
    s.sigad_apellido1,
    m.moodle_userid,
    'CAMBIO_DOCUMENTO_NECESARIO' AS accion
FROM mdl_aux_sigad_matriculas s
INNER JOIN v_moodle_alumnos m ON (
    -- Buscar por email como alternativa para detectar cambio de documento
    (m.moodle_email = s.sigad_email AND LOWER(s.sigad_documento) <> m.moodle_documento)
)
WHERE LOWER(s.sigad_documento) <> m.moodle_documento;


-- -----------------------------------------------------------------------------
-- 7.6 MATRÍCULAS NECESARIAS (módulos en SIGAD no matriculados en Moodle)
-- -----------------------------------------------------------------------------
-- Resultado: Alumnos que deben matricularse en cursos de Moodle
-- -----------------------------------------------------------------------------
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
ORDER BY s.sigad_documento, s.sigad_siglasmodulo;


-- -----------------------------------------------------------------------------
-- 7.7 BAJAS DE MÓDULOS (matriculado en Moodle pero no en SIGAD)
-- -----------------------------------------------------------------------------
-- Resultado: Matrículas que deben SUSPENDERSE
-- -----------------------------------------------------------------------------
SELECT 
    m.moodle_userid,
    m.moodle_documento,
    m.moodle_nombre,
    m.moodle_apellidos,
    m.moodle_courseid,
    m.moodle_course_shortname,
    m.moodle_course_fullname,
    m.moodle_enrol_start,
    'SUSPENDER_MATRICULA' AS accion_requerida
FROM v_moodle_matriculas m
INNER JOIN v_moodle_alumnos ma ON ma.moodle_userid = m.moodle_userid
LEFT JOIN mdl_aux_sigad_matriculas s ON LOWER(s.sigad_documento) = ma.moodle_documento
    AND (m.moodle_course_shortname LIKE CONCAT('%', s.sigad_siglasmodulo, '%')
         OR m.moodle_course_fullname LIKE CONCAT('%', s.sigad_modulo, '%'))
WHERE s.sigad_idmateria IS NULL
  AND m.moodle_enrol_status = 0  -- Solo activas
  AND m.moodle_course_shortname NOT LIKE '%tutoria%'  -- No suspender tutorías
ORDER BY m.moodle_documento, m.moodle_course_shortname;


-- -----------------------------------------------------------------------------
-- 7.8 RESUMEN EJECUTIVO DE ACCIONES PENDIENTES
-- -----------------------------------------------------------------------------
SELECT 
    'ALUMNOS_NUEVOS' AS categoria,
    COUNT(DISTINCT s.sigad_idalumno) AS cantidad
FROM mdl_aux_sigad_matriculas s
LEFT JOIN v_moodle_alumnos m ON m.moodle_documento = LOWER(s.sigad_documento)
WHERE m.moodle_userid IS NULL

UNION ALL

SELECT 
    'ALUMNOS_BAJA' AS categoria,
    COUNT(DISTINCT m.moodle_userid)
FROM v_moodle_alumnos m
LEFT JOIN mdl_aux_sigad_matriculas s ON LOWER(s.sigad_documento) = m.moodle_documento
WHERE s.sigad_idalumno IS NULL AND m.moodle_suspended = 0

UNION ALL

SELECT 
    'ALUMNOS_REACTIVAR' AS categoria,
    COUNT(DISTINCT m.moodle_userid)
FROM v_moodle_alumnos m
INNER JOIN mdl_aux_sigad_matriculas s ON LOWER(s.sigad_documento) = m.moodle_documento
WHERE m.moodle_suspended = 1

UNION ALL

SELECT 
    'EMAILS_ACTUALIZAR' AS categoria,
    COUNT(DISTINCT s.sigad_idalumno)
FROM mdl_aux_sigad_matriculas s
INNER JOIN v_moodle_alumnos m ON m.moodle_documento = LOWER(s.sigad_documento)
WHERE m.moodle_email <> s.sigad_email

UNION ALL

SELECT 
    'MATRICULAS_NUEVAS' AS categoria,
    COUNT(*)
FROM mdl_aux_sigad_matriculas s
INNER JOIN v_moodle_alumnos ma ON ma.moodle_documento = LOWER(s.sigad_documento)
LEFT JOIN v_moodle_matriculas m ON m.moodle_userid = ma.moodle_userid 
    AND (m.moodle_course_shortname LIKE CONCAT('%', s.sigad_siglasmodulo, '%'))
WHERE m.moodle_enrol_status IS NULL

UNION ALL

SELECT 
    'MATRICULAS_BAJA' AS categoria,
    COUNT(*)
FROM v_moodle_matriculas m
INNER JOIN v_moodle_alumnos ma ON ma.moodle_userid = m.moodle_userid
LEFT JOIN mdl_aux_sigad_matriculas s ON LOWER(s.sigad_documento) = ma.moodle_documento
    AND (m.moodle_course_shortname LIKE CONCAT('%', s.sigad_siglasmodulo, '%'))
WHERE s.sigad_idmateria IS NULL AND m.moodle_enrol_status = 0;


-- =============================================================================
-- 8. PROCEDIMIENTOS ALMACENADOS
-- =============================================================================

DELIMITER //

-- -----------------------------------------------------------------------------
-- Procedimiento: Generar reporte completo de sincronización
-- -----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_sigad_reporte_sincronizacion//

CREATE PROCEDURE sp_sigad_reporte_sincronizacion()
BEGIN
    SELECT 'INICIO_REPORTE' AS tipo, '' AS documento, '' AS nombre, '' AS detalle
    
    UNION ALL
    
    -- Alumnos nuevos
    SELECT 
        'NUEVO_ALUMNO' AS tipo,
        s.sigad_documento,
        CONCAT(s.sigad_nombre, ' ', s.sigad_apellido1) AS nombre,
        s.sigad_email AS detalle
    FROM mdl_aux_sigad_matriculas s
    LEFT JOIN v_moodle_alumnos m ON m.moodle_documento = LOWER(s.sigad_documento)
    WHERE m.moodle_userid IS NULL
    
    UNION ALL
    
    -- Alumnos de baja
    SELECT 
        'BAJA_ALUMNO' AS tipo,
        m.moodle_documento,
        CONCAT(m.moodle_nombre, ' ', m.moodle_apellidos) AS nombre,
        m.moodle_email AS detalle
    FROM v_moodle_alumnos m
    LEFT JOIN mdl_aux_sigad_matriculas s ON LOWER(s.sigad_documento) = m.moodle_documento
    WHERE s.sigad_idalumno IS NULL AND m.moodle_suspended = 0
    
    UNION ALL
    
    -- Cambios de email
    SELECT 
        'CAMBIO_EMAIL' AS tipo,
        s.sigad_documento,
        CONCAT(s.sigad_nombre, ' ', s.sigad_apellido1) AS nombre,
        CONCAT(m.moodle_email, ' -> ', s.sigad_email) AS detalle
    FROM mdl_aux_sigad_matriculas s
    INNER JOIN v_moodle_alumnos m ON m.moodle_documento = LOWER(s.sigad_documento)
    WHERE m.moodle_email <> s.sigad_email;
    
END//

DELIMITER ;


-- =============================================================================
-- 9. LIMPIEZA Y MANTENIMIENTO
-- =============================================================================

-- Para limpiar la tabla auxiliar e insertar nuevos datos:
-- TRUNCATE TABLE mdl_aux_sigad_matriculas;

-- Para insertar nuevos datos desde Python despues de hacer TRUNCATE:
-- (Usar el módulo sigad_db_sync.py)
