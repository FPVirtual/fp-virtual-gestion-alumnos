-- =====================================================
-- PREPARAR BASE DE DATOS PARA TESTING CONTROLADO
-- =====================================================
-- ⚠️  ADVERTENCIA: Este script modifica datos reales
-- 
-- USO RECOMENDADO:
-- 1. Ejecutar SOLO en preproducción o backup
-- 2. Hacer backup ANTES de ejecutar
-- 3. Ejecutar dentro de transacción (autocommit OFF)
-- 4. Probar casos
-- 5. Hacer ROLLBACK para restaurar datos
--
-- Este script selecciona usuarios reales y los modifica
-- temporalmente para crear casos de test específicos
-- =====================================================

-- =====================================================
-- PASO 0: CONFIGURACIÓN DE SEGURIDAD
-- =====================================================

-- Desactivar autocommit (obligatorio)
SET autocommit = 0;
START TRANSACTION;

-- Verificar que estamos en BD de test/preproducción
SELECT 
    DATABASE() as base_datos_actual,
    CASE 
        WHEN DATABASE() LIKE '%test%' THEN '✅ OK - BD de test'
        WHEN DATABASE() LIKE '%pre%' THEN '✅ OK - BD de preproducción'
        ELSE '⚠️  ATENCIÓN - Parece ser BD de producción'
    END as verificacion;

-- =====================================================
-- PASO 1: SELECCIONAR USUARIOS PARA MODIFICAR
-- =====================================================
-- Elegimos 7 usuarios que vamos a transformar en casos de test

DROP TABLE IF EXISTS tmp_usuarios_test_seleccionados;

CREATE TABLE tmp_usuarios_test_seleccionados AS
SELECT 
    ROW_NUMBER() OVER (ORDER BY u.id) as caso_id,
    u.id as user_id,
    u.username,
    u.firstname,
    u.lastname,
    u.email,
    u.suspended,
    GROUP_CONCAT(DISTINCT c.shortname ORDER BY c.shortname SEPARATOR ', ') as cursos_actuales
FROM mdl_user u
JOIN mdl_user_enrolments ue ON ue.userid = u.id
JOIN mdl_enrol e ON e.id = ue.enrolid
JOIN mdl_course c ON c.id = e.courseid
WHERE u.deleted = 0
  AND u.id > 1000  -- Excluir usuarios protegidos
  AND u.suspended = 0
GROUP BY u.id, u.username, u.firstname, u.lastname, u.email, u.suspended
ORDER BY RAND()  -- Aleatorio para no siempre usar los mismos
LIMIT 7;

-- Ver selección
SELECT * FROM tmp_usuarios_test_seleccionados;


-- =====================================================
-- PASO 2: CREAR BACKUP DE DATOS ORIGINALES
-- =====================================================

DROP TABLE IF EXISTS tmp_backup_datos_originales;

CREATE TABLE tmp_backup_datos_originales AS
SELECT 
    s.caso_id,
    s.user_id,
    s.username as username_original,
    s.firstname as firstname_original,
    s.lastname as lastname_original,
    s.email as email_original,
    s.suspended as suspended_original,
    s.cursos_actuales as cursos_original
FROM tmp_usuarios_test_seleccionados s;

-- =====================================================
-- PASO 3: APLICAR MODIFICACIONES PARA CASOS DE TEST
-- =====================================================

-- CASO 1: NO MODIFICAMOS - Lo usamos como base para crear usuario nuevo
-- Este caso se simula insertando en tabla auxiliar, no modificando Moodle


-- CASO 2: SUSPENDER USUARIO (simular reincorporación)
UPDATE mdl_user u
JOIN tmp_usuarios_test_seleccionados s ON s.user_id = u.id
SET u.suspended = 1
WHERE s.caso_id = 2;

SELECT '✅ Caso 2: Usuario suspendido para probar reactivación' as accion;


-- CASO 3: CAMBIAR EMAIL
UPDATE mdl_user u
JOIN tmp_usuarios_test_seleccionados s ON s.user_id = u.id
SET u.email = CONCAT('email_antiguo_', s.user_id, '@viejo.com')
WHERE s.caso_id = 3;

SELECT '✅ Caso 3: Email cambiado en Moodle para probar actualización' as accion;


-- CASO 4: CAMBIAR NOMBRE
UPDATE mdl_user u
JOIN tmp_usuarios_test_seleccionados s ON s.user_id = u.id
SET u.firstname = CONCAT('NombreAntiguo', s.user_id)
WHERE s.caso_id = 4;

SELECT '✅ Caso 4: Nombre cambiado en Moodle para probar actualización' as accion;


-- CASO 5: CAMBIAR USERNAME (simular NIE→DNI)
-- ⚠️  Nota: Cambiar username puede romper login, hacer solo en test
UPDATE mdl_user u
JOIN tmp_usuarios_test_seleccionados s ON s.user_id = u.id
SET u.username = CONCAT('X', SUBSTRING(s.username, 2))  -- Simular NIE
WHERE s.caso_id = 5;

SELECT '✅ Caso 5: Username cambiado a formato NIE para probar actualización' as accion;


-- CASO 6: AGREGAR MATRÍCULAS ADICIONALES
-- Ya está matriculado, no modificamos nada en Moodle
-- Las nuevas matrículas se detectarán comparando con sigad_alumnos_aux


-- CASO 7: DESMATRICULAR DE ALGUNOS CURSOS
-- Suspendemos algunas matrículas pero no todas
UPDATE mdl_user_enrolments ue
JOIN tmp_usuarios_test_seleccionados s ON s.user_id = ue.userid
JOIN (
    SELECT enrolid, userid
    FROM mdl_user_enrolments
    WHERE userid IN (SELECT user_id FROM tmp_usuarios_test_seleccionados WHERE caso_id = 7)
    ORDER BY RAND()
    LIMIT 2  -- Desmatricular de 2 cursos aleatorios
) sub ON sub.enrolid = ue.enrolid AND sub.userid = ue.userid
SET ue.status = 1  -- 1 = Suspendida
WHERE s.caso_id = 7;

SELECT '✅ Caso 7: Algunas matrículas suspendidas para probar desmatriculación parcial' as accion;


-- =====================================================
-- PASO 4: INSERTAR EN TABLA AUXILIAR LOS CASOS
-- =====================================================

-- Primero limpiar tabla auxiliar si existe
DELETE FROM sigad_alumnos_aux WHERE import_batch LIKE 'TEST_%';

-- Insertar datos simulados de SIGAD
INSERT INTO sigad_alumnos_aux (
    sigad_idalumno,
    sigad_documento,
    sigad_nombre,
    sigad_apellido1,
    sigad_apellido2,
    sigad_email,
    sigad_siglas_ciclo,
    import_batch,
    import_estado
)
SELECT 
    90000 + s.caso_id as sigad_idalumno,
    CASE 
        WHEN s.caso_id = 5 THEN SUBSTRING(s.username, 2)  -- Para caso 5, DNI nuevo
        ELSE s.username 
    END as sigad_documento,
    CASE 
        WHEN s.caso_id = 4 THEN CONCAT(s.firstname, 'Actualizado')  -- Nombre actualizado
        ELSE s.firstname 
    END as sigad_nombre,
    s.lastname as sigad_apellido1,
    '' as sigad_apellido2,
    CASE 
        WHEN s.caso_id = 3 THEN CONCAT('nuevo.email.', s.user_id, '@ejemplo.com')  -- Email nuevo
        ELSE s.email 
    END as sigad_email,
    CASE s.caso_id
        WHEN 6 THEN CONCAT(s.cursos_actuales, ', NUEVO1, NUEVO2')  -- Más cursos
        WHEN 7 THEN SUBSTRING_INDEX(s.cursos_actuales, ',', 1)  -- Menos cursos
        ELSE s.cursos_actuales
    END as sigad_siglas_ciclo,
    'TEST_CONTROLADO_' || DATE_FORMAT(NOW(), '%Y%m%d_%H%i%s') as import_batch,
    'PENDIENTE' as import_estado
FROM tmp_usuarios_test_seleccionados s
UNION ALL
-- Caso 1: Usuario completamente nuevo
SELECT 
    90001 as sigad_idalumno,
    'TEST99999X' as sigad_documento,
    'Usuario' as sigad_nombre,
    'NuevoTest' as sigad_apellido1,
    '' as sigad_apellido2,
    'usuario.nuevo.test@ejemplo.com' as sigad_email,
    'IFC301, IFC302' as sigad_siglas_ciclo,
    'TEST_CONTROLADO_' || DATE_FORMAT(NOW(), '%Y%m%d_%H%i%s') as import_batch,
    'PENDIENTE' as import_estado;


-- Actualizar cruce con Moodle
UPDATE sigad_alumnos_aux aux
LEFT JOIN mdl_user u ON LOWER(u.username) = LOWER(aux.sigad_documento)
SET 
    aux.moodle_userid = u.id,
    aux.moodle_username = u.username,
    aux.moodle_existe = (u.id IS NOT NULL AND u.deleted = 0),
    aux.moodle_suspended = COALESCE(u.suspended, 0),
    aux.moodle_email_actual = u.email
WHERE aux.import_batch LIKE 'TEST_%';


-- =====================================================
-- PASO 5: VERIFICAR CASOS CREADOS
-- =====================================================

SELECT 
    'CASOS CREADOS EN TABLA AUXILIAR' as titulo,
    '' as separador;

SELECT 
    caso_id,
    sigad_documento,
    sigad_nombre,
    sigad_email,
    sigad_siglas_ciclo,
    moodle_existe,
    moodle_suspended,
    CASE 
        WHEN moodle_existe = 0 THEN 'NUEVO'
        WHEN moodle_suspended = 1 THEN 'REACTIVAR'
        WHEN moodle_email_actual != sigad_email THEN 'CAMBIO_EMAIL'
        ELSE 'VERIFICAR'
    END as accion_detectada
FROM sigad_alumnos_aux
WHERE import_batch LIKE 'TEST_%'
ORDER BY caso_id;


-- =====================================================
-- RESUMEN EJECUTIVO
-- =====================================================

SELECT 
    'RESUMEN DE MODIFICACIONES' as seccion,
    '' as detalle
UNION ALL
SELECT 
    'Usuarios modificados',
    (SELECT COUNT(*) FROM tmp_usuarios_test_seleccionados)
UNION ALL
SELECT 
    'Caso 2 - Suspendidos para reactivar',
    '1 usuario'
UNION ALL
SELECT 
    'Caso 3 - Email cambiado',
    '1 usuario'
UNION ALL
SELECT 
    'Caso 4 - Nombre cambiado',
    '1 usuario'
UNION ALL
SELECT 
    'Caso 5 - Username cambiado (NIE→DNI)',
    '1 usuario'
UNION ALL
SELECT 
    'Caso 7 - Matrículas parciales suspendidas',
    '2 matrículas'
UNION ALL
SELECT 
    'Total en tabla auxiliar',
    (SELECT COUNT(*) FROM sigad_alumnos_aux WHERE import_batch LIKE 'TEST_%');


-- =====================================================
-- INSTRUCCIONES FINALES
-- =====================================================

SELECT 
    'INSTRUCCIONES' as titulo,
    '' as instruccion
UNION ALL
SELECT 
    '1. Probar sincronización',
    'Ejecutar gestion_alumnos.main_v2.py o queries de 04_queries_sincronizacion.sql'
UNION ALL
SELECT 
    '2. Verificar resultados',
    'Comprobar que se detectan los casos correctamente'
UNION ALL
SELECT 
    '3. Restaurar datos (IMPORTANTE)',
    'EJECUTAR: ROLLBACK; para deshacer TODOS los cambios'
UNION ALL
SELECT 
    '4. Confirmar rollback',
    'Verificar que los usuarios volvieron a su estado original';


-- ⚠️  NO HACER COMMIT AÚN
-- Después de probar, ejecutar: ROLLBACK;
