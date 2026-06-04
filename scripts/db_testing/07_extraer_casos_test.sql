-- =====================================================
-- EXTRAER CASOS DE TEST DESDE DATOS REALES
-- =====================================================
-- Este script extrae usuarios reales de Moodle y los modifica
-- para crear casos de test representativos

-- =====================================================
-- PASO 1: SELECCIONAR USUARIOS BASE
-- =====================================================
-- Seleccionamos usuarios con matrículas recientes y completos

-- Ver últimos usuarios matriculados
SELECT 
    u.id as moodle_userid,
    u.username,
    u.firstname,
    u.lastname,
    u.email,
    u.suspended,
    FROM_UNIXTIME(u.timecreated) as fecha_creacion,
    FROM_UNIXTIME(MAX(ue.timestart)) as ultima_matricula,
    COUNT(DISTINCT c.id) as num_cursos
FROM mdl_user u
JOIN mdl_user_enrolments ue ON ue.userid = u.id
JOIN mdl_enrol e ON e.id = ue.enrolid
JOIN mdl_course c ON c.id = e.courseid
WHERE u.deleted = 0
  AND u.id > 33  -- Excluir protegidos
GROUP BY u.id, u.username, u.firstname, u.lastname, u.email, u.suspended, u.timecreated
ORDER BY MAX(ue.timestart) DESC
LIMIT 10;


-- =====================================================
-- PASO 2: OBTENER DATOS COMPLETOS DE ESOS 10 USUARIOS
-- =====================================================
-- Guardamos los datos en una tabla temporal para modificarlos

DROP TABLE IF EXISTS tmp_test_usuarios_base;

CREATE TABLE tmp_test_usuarios_base AS
SELECT 
    u.id as moodle_userid,
    u.username,
    u.firstname as moodle_nombre,
    u.lastname as moodle_apellido,
    u.email as moodle_email,
    u.suspended as moodle_suspended,
    FROM_UNIXTIME(u.timecreated) as fecha_creacion,
    GROUP_CONCAT(DISTINCT c.shortname ORDER BY c.shortname SEPARATOR ', ') as cursos_actuales
FROM mdl_user u
JOIN mdl_user_enrolments ue ON ue.userid = u.id
JOIN mdl_enrol e ON e.id = ue.enrolid
JOIN mdl_course c ON c.id = e.courseid
WHERE u.deleted = 0
  AND u.id > 33
GROUP BY u.id, u.username, u.firstname, u.lastname, u.email, u.suspended, u.timecreated
ORDER BY MAX(ue.timestart) DESC
LIMIT 10;

-- Ver los usuarios seleccionados
SELECT * FROM tmp_test_usuarios_base;


-- =====================================================
-- PASO 3: CREAR CASOS DE TEST MODIFICANDO DATOS
-- =====================================================
-- Vamos a crear 7 casos distintos basados en los usuarios reales

DROP TABLE IF EXISTS tmp_casos_test;

CREATE TABLE tmp_casos_test (
    caso_id INT PRIMARY KEY,
    caso_descripcion VARCHAR(100),
    -- Datos SIGAD (simulados/modificados)
    sigad_idalumno INT,
    sigad_documento VARCHAR(20),
    sigad_nombre VARCHAR(100),
    sigad_apellido1 VARCHAR(100),
    sigad_apellido2 VARCHAR(100),
    sigad_email VARCHAR(200),
    sigad_cursos VARCHAR(500),
    -- Datos Moodle originales (para referencia)
    moodle_userid INT,
    moodle_username VARCHAR(100),
    moodle_nombre_original VARCHAR(100),
    moodle_apellido_original VARCHAR(100),
    moodle_email_original VARCHAR(200),
    moodle_cursos_original VARCHAR(500),
    moodle_suspended INT
);

-- Insertar casos basados en usuarios reales
INSERT INTO tmp_casos_test 
SELECT 
    1 as caso_id,
    'NUEVO: No existe en Moodle' as caso_descripcion,
    99901 as sigad_idalumno,
    CONCAT('TESTNEW', moodle_userid) as sigad_documento,  -- Documento nuevo
    moodle_nombre as sigad_nombre,
    moodle_apellido as sigad_apellido1,
    '' as sigad_apellido2,
    CONCAT('testnew', moodle_userid, '@nuevo.com') as sigad_email,
    'IFC301, IFC302' as sigad_cursos,  -- Cursos nuevos
    NULL as moodle_userid,  -- No existe en Moodle
    NULL as moodle_username,
    NULL as moodle_nombre_original,
    NULL as moodle_apellido_original,
    NULL as moodle_email_original,
    NULL as moodle_cursos_original,
    NULL as moodle_suspended
FROM tmp_test_usuarios_base 
LIMIT 1;

INSERT INTO tmp_casos_test 
SELECT 
    2 as caso_id,
    'REINCORPORACION: Estaba suspendido' as caso_descripcion,
    99902 as sigad_idalumno,
    username as sigad_documento,
    moodle_nombre as sigad_nombre,
    moodle_apellido as sigad_apellido1,
    '' as sigad_apellido2,
    moodle_email as sigad_email,
    cursos_actuales as sigad_cursos,
    moodle_userid,
    username as moodle_username,
    moodle_nombre as moodle_nombre_original,
    moodle_apellido as moodle_apellido_original,
    moodle_email as moodle_email_original,
    cursos_actuales as moodle_cursos_original,
    1 as moodle_suspended  -- Estaba suspendido
FROM tmp_test_usuarios_base 
WHERE moodle_suspended = 1
LIMIT 1;

-- Si no hay suspendidos, simulamos uno
INSERT INTO tmp_casos_test 
SELECT 
    2 as caso_id,
    'REINCORPORACION: Estaba suspendido' as caso_descripcion,
    99902 as sigad_idalumno,
    username as sigad_documento,
    moodle_nombre as sigad_nombre,
    moodle_apellido as sigad_apellido1,
    '' as sigad_apellido2,
    moodle_email as sigad_email,
    cursos_actuales as sigad_cursos,
    moodle_userid,
    username as moodle_username,
    moodle_nombre as moodle_nombre_original,
    moodle_apellido as moodle_apellido_original,
    moodle_email as moodle_email_original,
    cursos_actuales as moodle_cursos_original,
    1 as moodle_suspended
FROM tmp_test_usuarios_base 
WHERE caso_id IS NULL  -- Solo si no se insertó el anterior
LIMIT 1;

INSERT INTO tmp_casos_test 
SELECT 
    3 as caso_id,
    'CAMBIO_EMAIL: Email diferente' as caso_descripcion,
    99903 as sigad_idalumno,
    username as sigad_documento,
    moodle_nombre as sigad_nombre,
    moodle_apellido as sigad_apellido1,
    '' as sigad_apellido2,
    CONCAT('nuevo.email', moodle_userid, '@cambiado.com') as sigad_email,  -- Email cambiado
    cursos_actuales as sigad_cursos,
    moodle_userid,
    username as moodle_username,
    moodle_nombre as moodle_nombre_original,
    moodle_apellido as moodle_apellido_original,
    moodle_email as moodle_email_original,
    cursos_actuales as moodle_cursos_original,
    moodle_suspended
FROM tmp_test_usuarios_base 
LIMIT 1 OFFSET 1;

INSERT INTO tmp_casos_test 
SELECT 
    4 as caso_id,
    'CAMBIO_NOMBRE: Nombre modificado' as caso_descripcion,
    99904 as sigad_idalumno,
    username as sigad_documento,
    CONCAT(moodle_nombre, 'MOD') as sigad_nombre,  -- Nombre modificado
    moodle_apellido as sigad_apellido1,
    '' as sigad_apellido2,
    moodle_email as sigad_email,
    cursos_actuales as sigad_cursos,
    moodle_userid,
    username as moodle_username,
    moodle_nombre as moodle_nombre_original,
    moodle_apellido as moodle_apellido_original,
    moodle_email as moodle_email_original,
    cursos_actuales as moodle_cursos_original,
    moodle_suspended
FROM tmp_test_usuarios_base 
LIMIT 1 OFFSET 2;

INSERT INTO tmp_casos_test 
SELECT 
    5 as caso_id,
    'CAMBIO_NIE_A_DNI: Cambio de documento' as caso_descripcion,
    99905 as sigad_idalumno,
    REPLACE(username, 'X', '0') as sigad_documento,  -- Simular cambio NIE→DNI
    moodle_nombre as sigad_nombre,
    moodle_apellido as sigad_apellido1,
    '' as sigad_apellido2,
    moodle_email as sigad_email,
    cursos_actuales as sigad_cursos,
    moodle_userid,
    username as moodle_username,
    moodle_nombre as moodle_nombre_original,
    moodle_apellido as moodle_apellido_original,
    moodle_email as moodle_email_original,
    cursos_actuales as moodle_cursos_original,
    moodle_suspended
FROM tmp_test_usuarios_base 
LIMIT 1 OFFSET 3;

INSERT INTO tmp_casos_test 
SELECT 
    6 as caso_id,
    'NUEVAS_MATRICULAS: Agregó cursos' as caso_descripcion,
    99906 as sigad_idalumno,
    username as sigad_documento,
    moodle_nombre as sigad_nombre,
    moodle_apellido as sigad_apellido1,
    '' as sigad_apellido2,
    moodle_email as sigad_email,
    CONCAT(cursos_actuales, ', IFC999, IPPE99') as sigad_cursos,  -- Cursos adicionales
    moodle_userid,
    username as moodle_username,
    moodle_nombre as moodle_nombre_original,
    moodle_apellido as moodle_apellido_original,
    moodle_email as moodle_email_original,
    cursos_actuales as moodle_cursos_original,
    moodle_suspended
FROM tmp_test_usuarios_base 
LIMIT 1 OFFSET 4;

INSERT INTO tmp_casos_test 
SELECT 
    7 as caso_id,
    'BAJA_PARCIAL: Quitó algunos cursos' as caso_descripcion,
    99907 as sigad_idalumno,
    username as sigad_documento,
    moodle_nombre as sigad_nombre,
    moodle_apellido as sigad_apellido1,
    '' as sigad_apellido2,
    moodle_email as sigad_email,
    SUBSTRING_INDEX(cursos_actuales, ',', 1) as sigad_cursos,  -- Solo primer curso
    moodle_userid,
    username as moodle_username,
    moodle_nombre as moodle_nombre_original,
    moodle_apellido as moodle_apellido_original,
    moodle_email as moodle_email_original,
    cursos_actuales as moodle_cursos_original,
    moodle_suspended
FROM tmp_test_usuarios_base 
LIMIT 1 OFFSET 5;


-- =====================================================
-- PASO 4: VER TODOS LOS CASOS CREADOS
-- =====================================================

SELECT 
    caso_id,
    caso_descripcion,
    sigad_documento,
    sigad_nombre,
    sigad_apellido1,
    sigad_email,
    sigad_cursos,
    moodle_username,
    moodle_email_original,
    moodle_cursos_original,
    CASE moodle_suspended 
        WHEN 1 THEN 'SÍ' 
        WHEN 0 THEN 'NO'
        ELSE 'N/A'
    END as estaba_suspendido
FROM tmp_casos_test
ORDER BY caso_id;


-- =====================================================
-- PASO 5: EXPORTAR A JSON (usar script Python)
-- =====================================================
-- Ejecutar el script Python para generar el JSON de test
