-- =====================================================
-- CARGAR CASOS DE TEST MANUALES DESDE CSV
-- =====================================================
-- Archivo fuente: 02_plantilla_casos_test.csv
-- Descripción: Inserta casos de test en tabla auxiliar y 
--              crea/actualiza usuarios en Moodle para testing
--
-- ⚠️  ADVERTENCIA: Ejecutar SOLO en entorno de test/preproducción
-- =====================================================

-- Desactivar autocommit para poder hacer rollback
SET autocommit = 0;
START TRANSACTION;

-- Verificar entorno
SELECT 
    DATABASE() as base_datos_actual,
    CASE 
        WHEN DATABASE() LIKE '%test%' THEN '✅ OK - BD de test'
        WHEN DATABASE() LIKE '%pre%' THEN '✅ OK - BD de preproducción'
        ELSE '⚠️  ATENCIÓN - Parece ser BD de producción'
    END as verificacion;


-- =====================================================
-- PASO 1: LIMPIAR DATOS ANTERIORES DE TEST
-- =====================================================

DELETE FROM sigad_alumnos_aux WHERE import_batch LIKE 'MANUAL_TEST_%';

SELECT '✅ Tabla auxiliar limpiada de tests anteriores' as paso;


-- =====================================================
-- PASO 2: INSERTAR CASOS EN TABLA AUXILIAR (DATOS SIGAD)
-- =====================================================

INSERT INTO sigad_alumnos_aux (
    sigad_idalumno,
    sigad_documento,
    sigad_nombre,
    sigad_apellido1,
    sigad_apellido2,
    sigad_email,
    sigad_siglas_ciclo,
    sigad_modulos,
    import_batch,
    import_estado,
    observaciones
)
VALUES 
-- CASO 1: NUEVO - No existe en Moodle
(
    29128936,                           -- sigad_idalumno
    '29128936B',                        -- sigad_documento
    'ALBA',                             -- sigad_nombre
    'SERRANO',                          -- sigad_apellido1
    'HERRANZ',                          -- sigad_apellido2
    'aserranohb@fpvirtualaragon.es',    -- sigad_email
    'IFC303',                           -- sigad_siglas_ciclo
    JSON_ARRAY(
        '50010314-IFC303-16805',
        '50010314-IFC303-16809',
        '50010314-IFC303-5179',
        '50010314-IFC303-5182',
        '50010314-IFC303-682t',
        'ayuda'
    ),                                  -- sigad_modulos
    'MANUAL_TEST_2026',                 -- import_batch
    'PENDIENTE',                        -- import_estado
    'CASO 1: Nuevo usuario - No existe en Moodle'
),

-- CASO 2: REINCORPORACION - Estaba suspendido
(
    73012900,                           -- sigad_idalumno
    '73012900K',                        -- sigad_documento
    'Alicia',                           -- sigad_nombre
    'García del Castillo',              -- sigad_apellido1
    '',                                 -- sigad_apellido2
    'agarciadck@fpvirtualaragon.es',    -- sigad_email
    'IFC303',                           -- sigad_siglas_ciclo
    JSON_ARRAY(
        '50010314-IFC303-5179',
        '50010314-IFC303-5182',
        '50010314-IFC303-682t',
        'ayuda'
    ),                                  -- sigad_modulos
    'MANUAL_TEST_2026',                 -- import_batch
    'PENDIENTE',                        -- import_estado
    'CASO 2: Reincorporación - Usuario existe pero suspendido'
),

-- CASO 3a: CAMBIO_EMAIL - Email diferente (primera fila)
(
    90003,                              -- sigad_idalumno
    '34567890C',                        -- sigad_documento
    'Lucía',                            -- sigad_nombre
    'Fernández',                        -- sigad_apellido1
    'Sánchez',                          -- sigad_apellido2
    'lucia.nuevo.email@cambiado.com',   -- sigad_email (NUEVO)
    'SSC302',                           -- sigad_siglas_ciclo
    NULL,                               -- sigad_modulos
    'MANUAL_TEST_2026',                 -- import_batch
    'PENDIENTE',                        -- import_estado
    'CASO 3: Cambio de email - Email diferente en SIGAD'
),

-- CASO 3b: CAMBIO_EMAIL - Email diferente (segunda fila - datos reales)
(
    73050337,                           -- sigad_idalumno
    '73050337Z',                        -- sigad_documento
    'DAVID',                            -- sigad_nombre
    'ALQUÉZAR',                         -- sigad_apellido1
    'GASCÓN',                           -- sigad_apellido2
    'dalquezargz.nuevo.email@cambiado.com', -- sigad_email (NUEVO)
    'IFC302',                           -- sigad_siglas_ciclo
    JSON_ARRAY(
        '50020125-IFC302-16771',
        '50020125-IFC302-16773',
        '50020125-IFC302-16787',
        '50020125-IFC302-16801',
        '50020125-IFC302-5289',
        '50020125-IFC302-5291',
        '50020125-IFC302-681t',
        'ayuda'
    ),                                  -- sigad_modulos
    'MANUAL_TEST_2026',                 -- import_batch
    'PENDIENTE',                        -- import_estado
    'CASO 3: Cambio de email - Email diferente en SIGAD'
),

-- CASO 4: CAMBIO_NOMBRE - Nombre modificado
(
    90004,                              -- sigad_idalumno
    '45678901D',                        -- sigad_documento
    'María Elena',                      -- sigad_nombre (ACTUALIZADO)
    'Rodríguez',                        -- sigad_apellido1
    'Gómez',                            -- sigad_apellido2
    'maria.rodriguez@ejemplo.com',      -- sigad_email
    'IFC303',                           -- sigad_siglas_ciclo
    NULL,                               -- sigad_modulos
    'MANUAL_TEST_2026',                 -- import_batch
    'PENDIENTE',                        -- import_estado
    'CASO 4: Cambio de nombre - Nombre cambió en SIGAD'
),

-- CASO 5: CAMBIO_NIE_A_DNI - Cambio documento
(
    90005,                              -- sigad_idalumno
    '56789012E',                        -- sigad_documento (DNI nuevo en SIGAD)
    'Pedro',                            -- sigad_nombre
    'López',                            -- sigad_apellido1
    'Hernández',                        -- sigad_apellido2
    'pedro.lopez@ejemplo.com',          -- sigad_email
    'IFC301',                           -- sigad_siglas_ciclo
    NULL,                               -- sigad_modulos
    'MANUAL_TEST_2026',                 -- import_batch
    'PENDIENTE',                        -- import_estado
    'CASO 5: Cambio NIE→DNI - Username Moodle es NIE pero SIGAD tiene DNI'
),

-- CASO 6: NUEVAS_MATRICULAS - Agregó cursos
(
    90006,                              -- sigad_idalumno
    '67890123F',                        -- sigad_documento
    'Sofía',                            -- sigad_nombre
    'Martín',                           -- sigad_apellido1
    'Díaz',                             -- sigad_apellido2
    'sofia.martin@ejemplo.com',         -- sigad_email
    'IFC301;LM;ED;SI',                  -- sigad_siglas_ciclo (4 cursos)
    NULL,                               -- sigad_modulos
    'MANUAL_TEST_2026',                 -- import_batch
    'PENDIENTE',                        -- import_estado
    'CASO 6: Nuevas matrículas - Tenía 2 cursos, ahora tiene 4'
),

-- CASO 7: BAJA_PARCIAL - Quitó cursos
(
    90007,                              -- sigad_idalumno
    '78901234G',                        -- sigad_documento
    'Javier',                           -- sigad_nombre
    'Sánchez',                          -- sigad_apellido1
    'Moreno',                           -- sigad_apellido2
    'javier.sanchez@ejemplo.com',       -- sigad_email
    'PROG',                             -- sigad_siglas_ciclo (solo 1 curso)
    NULL,                               -- sigad_modulos
    'MANUAL_TEST_2026',                 -- import_batch
    'PENDIENTE',                        -- import_estado
    'CASO 7: Baja parcial - Tenía 5 cursos, ahora solo 1'
);

SELECT '✅ Casos insertados en tabla auxiliar' as paso;


-- =====================================================
-- PASO 3: CREAR/ACTUALIZAR USUARIOS EN MOODLE (mdl_user)
-- =====================================================

-- Primero creamos una tabla temporal con los usuarios de test
DROP TABLE IF EXISTS tmp_casos_test_usuarios;

CREATE TEMPORARY TABLE tmp_casos_test_usuarios AS
SELECT * FROM (
    -- CASO 2: Usuario que existe pero está suspendido
    SELECT 
        2 as caso_id,
        12591 as user_id,
        '73012900k' as username,
        'agarciadck@fpvirtualaragon.es' as email,
        'Alicia' as firstname,
        'García del Castillo' as lastname,
        1 as suspended  -- Está suspendido
    UNION ALL
    -- CASO 3a: Email diferente en Moodle
    SELECT 
        3 as caso_id,
        12346 as user_id,
        '34567890c' as username,
        'lucia.antiguo@ejemplo.com' as email,  -- Email antiguo
        'Lucía' as firstname,
        'Fernández' as lastname,
        0 as suspended
    UNION ALL
    -- CASO 3b: Email diferente (datos reales)
    SELECT 
        3 as caso_id,
        8496 as user_id,
        '73050337z' as username,
        -- Email original (no el nuevo)
        CONCAT('dalquezargz', '@fpvirtualaragon.es') as email,
        'DAVID' as firstname,
        'ALQUÉZAR GASCÓN' as lastname,
        0 as suspended
    UNION ALL
    -- CASO 4: Nombre modificado
    SELECT 
        4 as caso_id,
        12347 as user_id,
        '45678901d' as username,
        'maria.rodriguez@ejemplo.com' as email,
        'María' as firstname,  -- Sin "Elena"
        'Rodríguez Gómez' as lastname,
        0 as suspended
    UNION ALL
    -- CASO 5: Username NIE (cambiará a DNI)
    SELECT 
        5 as caso_id,
        12348 as user_id,
        'X1234567L' as username,  -- NIE en Moodle
        'pedro.lopez@ejemplo.com' as email,
        'Pedro' as firstname,
        'López Hernández' as lastname,
        0 as suspended
    UNION ALL
    -- CASO 6: Nuevas matrículas (tiene menos cursos en Moodle)
    SELECT 
        6 as caso_id,
        12349 as user_id,
        '67890123f' as username,
        'sofia.martin@ejemplo.com' as email,
        'Sofía' as firstname,
        'Martín Díaz' as lastname,
        0 as suspended
    UNION ALL
    -- CASO 7: Baja parcial (tiene más cursos en Moodle)
    SELECT 
        7 as caso_id,
        12350 as user_id,
        '78901234g' as username,
        'javier.sanchez@ejemplo.com' as email,
        'Javier' as firstname,
        'Sánchez Moreno' as lastname,
        0 as suspended
) as usuarios;

-- Insertar usuarios que no existen (evitando duplicados)
INSERT INTO mdl_user (
    id,
    auth,
    confirmed,
    policyagreed,
    deleted,
    suspended,
    mnethostid,
    username,
    password,
    email,
    firstname,
    lastname,
    timecreated,
    timemodified
)
SELECT 
    t.user_id,
    'manual' as auth,
    1 as confirmed,
    0 as policyagreed,
    0 as deleted,
    t.suspended,
    1 as mnethostid,
    t.username,
    -- Hash de contraseña temporal (cambiar en producción)
    '$2y$10$XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX' as password,
    t.email,
    t.firstname,
    t.lastname,
    UNIX_TIMESTAMP() as timecreated,
    UNIX_TIMESTAMP() as timemodified
FROM tmp_casos_test_usuarios t
LEFT JOIN mdl_user u ON u.id = t.user_id
WHERE u.id IS NULL;

SELECT CONCAT('✅ Usuarios creados: ', ROW_COUNT()) as paso;

-- Actualizar usuarios existentes para casos específicos

-- CASO 2: Suspender usuario
UPDATE mdl_user u
JOIN tmp_casos_test_usuarios t ON t.user_id = u.id
SET u.suspended = 1
WHERE t.caso_id = 2 AND t.suspended = 1;

SELECT '✅ Caso 2: Usuario suspendido' as paso;

-- CASO 3a: Poner email antiguo
UPDATE mdl_user u
JOIN tmp_casos_test_usuarios t ON t.user_id = u.id
SET u.email = t.email
WHERE t.caso_id = 3 AND u.id = 12346;

-- CASO 3b: Poner email antiguo (David)
UPDATE mdl_user u
JOIN tmp_casos_test_usuarios t ON t.user_id = u.id
SET u.email = t.email
WHERE t.user_id = 8496;

SELECT '✅ Caso 3: Emails actualizados a versión antigua' as paso;

-- CASO 4: Nombre sin "Elena"
UPDATE mdl_user u
JOIN tmp_casos_test_usuarios t ON t.user_id = u.id
SET u.firstname = t.firstname,
    u.lastname = t.lastname
WHERE t.caso_id = 4;

SELECT '✅ Caso 4: Nombre actualizado' as paso;

-- CASO 5: Username como NIE
UPDATE mdl_user u
JOIN tmp_casos_test_usuarios t ON t.user_id = u.id
SET u.username = t.username
WHERE t.caso_id = 5;

SELECT '✅ Caso 5: Username cambiado a NIE' as paso;


-- =====================================================
-- PASO 4: ACTUALIZAR CRUCE TABLA AUXILIAR ↔ MOODLE
-- =====================================================

UPDATE sigad_alumnos_aux aux
LEFT JOIN mdl_user u ON (
    -- Match por documento (varios formatos)
    LOWER(u.username) = LOWER(aux.sigad_documento)
    OR LOWER(u.username) = LOWER(CONCAT('X', aux.sigad_documento))  -- NIE
)
SET 
    aux.moodle_userid = u.id,
    aux.moodle_username = u.username,
    aux.moodle_existe = (u.id IS NOT NULL AND u.deleted = 0),
    aux.moodle_suspended = COALESCE(u.suspended, 0),
    aux.moodle_email_actual = u.email
WHERE aux.import_batch LIKE 'MANUAL_TEST_%';

-- Actualizar específicamente caso 5 (match por NIE→DNI)
UPDATE sigad_alumnos_aux aux
JOIN mdl_user u ON LOWER(u.username) = 'x1234567l'
SET 
    aux.moodle_userid = u.id,
    aux.moodle_username = u.username,
    aux.moodle_existe = 1,
    aux.moodle_suspended = u.suspended,
    aux.moodle_email_actual = u.email
WHERE aux.sigad_documento = '56789012E' 
  AND aux.import_batch LIKE 'MANUAL_TEST_%';

SELECT '✅ Cruce tabla auxiliar ↔ Moodle completado' as paso;


-- =====================================================
-- PASO 5: CREAR MATRÍCULAS PARA CASOS 6 Y 7
-- =====================================================

-- Nota: Este paso requiere conocer los courseid reales
-- Se deja como comentario para adaptación manual

/*
-- Ejemplo para CASO 6: Matricular en 2 cursos (estado actual en Moodle)
INSERT INTO mdl_user_enrolments (enrolid, userid, timestart, timeend, modifierid, timecreated, timemodified, status)
SELECT e.id, 12349, UNIX_TIMESTAMP(), 0, 2, UNIX_TIMESTAMP(), UNIX_TIMESTAMP(), 0
FROM mdl_enrol e
JOIN mdl_course c ON c.id = e.courseid
WHERE c.shortname IN ('IFC301', 'LM')
ON DUPLICATE KEY UPDATE status = 0;

-- Ejemplo para CASO 7: Matricular en 5 cursos (más de los que tiene en SIGAD)
INSERT INTO mdl_user_enrolments (enrolid, userid, timestart, timeend, modifierid, timecreated, timemodified, status)
SELECT e.id, 12350, UNIX_TIMESTAMP(), 0, 2, UNIX_TIMESTAMP(), UNIX_TIMESTAMP(), 0
FROM mdl_enrol e
JOIN mdl_course c ON c.id = e.courseid
WHERE c.shortname IN ('PROG', 'BD', 'LM', 'ED', 'SI')
ON DUPLICATE KEY UPDATE status = 0;
*/

SELECT '⚠️  Paso 5: Matrículas - Requiere adaptación manual con courseids reales' as paso;


-- =====================================================
-- VERIFICACIÓN FINAL
-- =====================================================

SELECT 
    '========================================' as separador,
    'CASOS CARGADOS - VERIFICACIÓN' as titulo,
    '========================================' as separador2;

SELECT 
    CASE 
        WHEN aux.sigad_documento = '29128936B' THEN 'CASO 1'
        WHEN aux.sigad_documento = '73012900K' THEN 'CASO 2'
        WHEN aux.sigad_documento = '34567890C' THEN 'CASO 3a'
        WHEN aux.sigad_documento = '73050337Z' THEN 'CASO 3b'
        WHEN aux.sigad_documento = '45678901D' THEN 'CASO 4'
        WHEN aux.sigad_documento = '56789012E' THEN 'CASO 5'
        WHEN aux.sigad_documento = '67890123F' THEN 'CASO 6'
        WHEN aux.sigad_documento = '78901234G' THEN 'CASO 7'
    END as caso,
    aux.sigad_documento,
    aux.sigad_nombre,
    aux.sigad_email as email_sigad,
    aux.moodle_userid,
    aux.moodle_username,
    aux.moodle_email_actual as email_moodle,
    aux.moodle_existe,
    aux.moodle_suspended,
    CASE 
        WHEN aux.moodle_existe = 0 THEN '🔵 NUEVO'
        WHEN aux.moodle_suspended = 1 THEN '🟡 REACTIVAR'
        WHEN aux.moodle_email_actual != aux.sigad_email THEN '🟠 CAMBIO EMAIL'
        ELSE '🟢 VERIFICAR MATRÍCULAS'
    END as accion_detectada
FROM sigad_alumnos_aux aux
WHERE aux.import_batch LIKE 'MANUAL_TEST_%'
ORDER BY 
    CASE 
        WHEN aux.sigad_documento = '29128936B' THEN 1
        WHEN aux.sigad_documento = '73012900K' THEN 2
        WHEN aux.sigad_documento = '34567890C' THEN 3
        WHEN aux.sigad_documento = '73050337Z' THEN 4
        WHEN aux.sigad_documento = '45678901D' THEN 5
        WHEN aux.sigad_documento = '56789012E' THEN 6
        WHEN aux.sigad_documento = '67890123F' THEN 7
        WHEN aux.sigad_documento = '78901234G' THEN 8
    END;


-- =====================================================
-- INSTRUCCIONES
-- =====================================================

SELECT 
    '========================================' as separador,
    'INSTRUCCIONES' as titulo,
    '========================================' as separador2
UNION ALL
SELECT 
    '1. Verificar usuarios creados', 
    'SELECT * FROM mdl_user WHERE id BETWEEN 12346 AND 12350;',
    ''
UNION ALL
SELECT 
    '2. Ejecutar sincronización',
    'Probar gestion_alumnos.main_v2.py o queries de 04_queries_sincronizacion.sql',
    ''
UNION ALL
SELECT 
    '3. Verificar resultados',
    'Comprobar que se detectan todos los casos correctamente',
    ''
UNION ALL
SELECT 
    '4. RESTAURAR (ROLLBACK)',
    'Ejecutar: ROLLBACK; para deshacer TODOS los cambios',
    '';


-- ⚠️  NO HACER COMMIT AÚN
-- Después de probar, ejecutar: ROLLBACK;
-- Si todo está correcto: COMMIT;
