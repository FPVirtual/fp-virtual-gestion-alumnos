-- =====================================================
-- QUERIES DE MODIFICACIÓN MANUAL
-- =====================================================
-- ⚠️  EJECUTAR CON EXTREMA PRECAUCIÓN
-- 
-- INSTRUCCIONES:
-- 1. Asegúrate de estar en BD de test/preproducción
-- 2. Desactiva autocommit: SET autocommit = 0;
-- 3. Inicia transacción: START TRANSACTION;
-- 4. Ejecuta las queries que necesites
-- 5. Verifica resultados con queries de 03_queries_verificacion_manual.sql
-- 6. Si todo OK: COMMIT;
-- 7. Si algo falla: ROLLBACK;
-- =====================================================

-- =====================================================
-- PASO 0: PREPARAR ENTORNO SEGURO
-- =====================================================

SET autocommit = 0;
START TRANSACTION;

-- Verificar BD
SELECT 
    DATABASE() as base_datos,
    CASE 
        WHEN DATABASE() LIKE '%test%' THEN '✅ OK'
        WHEN DATABASE() LIKE '%pre%' THEN '✅ OK'
        ELSE '⚠️  ¡ATENCIÓN! Parece producción'
    END as verificacion;


-- =====================================================
-- MODIFICACIÓN 1: Crear usuario nuevo (Caso 1)
-- =====================================================
-- Si quieres probar creación real:

-- INSERT INTO mdl_user (
--     username, email, firstname, lastname,
--     confirmed, suspended, deleted, timecreated
-- ) VALUES (
--     '12345678a',
--     'ana.garcia.nueva@ejemplo.com',
--     'Ana',
--     'García',
--     1, 0, 0, UNIX_TIMESTAMP()
-- );
-- 
-- SELECT LAST_INSERT_ID() as nuevo_userid;


-- =====================================================
-- MODIFICACIÓN 2: Suspender usuario (Caso 2)
-- =====================================================
-- Cambiar usuario a suspendido:

-- UPDATE mdl_user
-- SET suspended = 1,
--     timemodified = UNIX_TIMESTAMP()
-- WHERE username = '23456789b';


-- =====================================================
-- MODIFICACIÓN 3: Cambiar email (Caso 3)
-- =====================================================
-- Modificar email para probar actualización:

-- UPDATE mdl_user
-- SET email = 'lucia.antiguo@ejemplo.com',
--     timemodified = UNIX_TIMESTAMP()
-- WHERE username = '34567890c';


-- =====================================================
-- MODIFICACIÓN 4: Cambiar nombre (Caso 4)
-- =====================================================

-- UPDATE mdl_user
-- SET firstname = 'María',
--     timemodified = UNIX_TIMESTAMP()
-- WHERE username = '45678901d';


-- =====================================================
-- MODIFICACIÓN 5: Cambiar username (Caso 5 - NIE→DNI)
-- =====================================================
-- ⚠️  Peligroso: puede romper login del usuario

-- UPDATE mdl_user
-- SET username = 'X1234567L',
--     timemodified = UNIX_TIMESTAMP()
-- WHERE username = '56789012e';


-- =====================================================
-- MODIFICACIÓN 6: Agregar matrícula (Caso 6)
-- =====================================================
-- Necesitas saber el enrolid del curso:

-- -- Primero buscar enrolid del curso:
-- SELECT id as enrolid, courseid 
-- FROM mdl_enrol 
-- WHERE courseid = (SELECT id FROM mdl_course WHERE shortname = 'LM' LIMIT 1)
-- LIMIT 1;
-- 
-- -- Luego insertar matrícula:
-- INSERT INTO mdl_user_enrolments (
--     enrolid, userid, timestart, status
-- ) VALUES (
--     ENROL_ID_AQUI,
--     (SELECT id FROM mdl_user WHERE username = '67890123f'),
--     UNIX_TIMESTAMP(),
--     0
-- );


-- =====================================================
-- MODIFICACIÓN 7: Suspender matrícula (Caso 7)
-- =====================================================
-- Desmatricular de algunos cursos (sin eliminar):

-- UPDATE mdl_user_enrolments ue
-- JOIN mdl_user u ON u.id = ue.userid
-- JOIN mdl_enrol e ON e.id = ue.enrolid
-- JOIN mdl_course c ON c.id = e.courseid
-- SET ue.status = 1  -- 1 = Suspendida
-- WHERE u.username = '78901234g'
--   AND c.shortname IN ('BD', 'LM');  -- Cursos a "desmatricular"


-- =====================================================
-- VERIFICACIÓN POST-MODIFICACIÓN
-- =====================================================

-- Ver últimos cambios
SELECT 
    username,
    firstname,
    lastname,
    email,
    suspended,
    FROM_UNIXTIME(timemodified) as ultima_modificacion
FROM mdl_user
WHERE timemodified > UNIX_TIMESTAMP() - 3600  -- Última hora
ORDER BY timemodified DESC;


-- =====================================================
-- DECISIÓN FINAL
-- =====================================================

-- Si todo está correcto:
-- COMMIT;

-- Si algo falló o es solo prueba:
-- ROLLBACK;

-- Verificar estado de la transacción
SELECT 
    @@autocommit as autocommit_activo,
    CASE @@autocommit 
        WHEN 0 THEN 'En transacción - puedes hacer ROLLBACK'
        ELSE 'Autocommit activo - cambios son permanentes'
    END as estado;
