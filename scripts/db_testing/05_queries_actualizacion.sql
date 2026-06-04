-- =====================================================
-- QUERIES DE ACTUALIZACIÓN (EJECUTAR CON PRECAUCIÓN)
-- =====================================================
-- ⚠️  ADVERTENCIA: Estas queries MODIFICAN datos
-- 
-- Recomendaciones:
-- 1. Hacer backup antes de ejecutar
-- 2. Probar primero en preproducción
-- 3. Ejecutar en transacción para poder hacer rollback
-- 4. Verificar resultados antes de COMMIT
--
-- Para ejecutar con seguridad en DBeaver:
-- SET autocommit = 0;  -- Desactivar autocommit
-- [ejecutar queries]
-- ROLLBACK;  -- Si algo falló, deshacer
-- COMMIT;    -- Solo si todo está correcto
-- =====================================================

-- =====================================================
-- TRANSACCIÓN DE EJEMPLO (plantilla)
-- =====================================================
/*
START TRANSACTION;

-- Aquí van las queries de actualización

-- Verificar resultados
SELECT ...

-- Si todo OK:
COMMIT;

-- Si algo falló:
-- ROLLBACK;
*/


-- =====================================================
-- ACTUALIZACIÓN 1: Reactivar usuarios suspendidos
-- =====================================================
-- Descripción: Usuarios que estaban suspendidos y vuelven a SIGAD

-- Verificar cuáles se reactivarían (sin ejecutar)
SELECT 
    u.id,
    u.username,
    u.firstname,
    u.lastname,
    u.suspended
FROM mdl_user u
JOIN sigad_alumnos_aux aux ON LOWER(u.username) = LOWER(aux.sigad_documento)
WHERE u.suspended = 1
  AND aux.moodle_suspended = 1;

-- Ejecutar reactivación (descomentar para usar)
-- UPDATE mdl_user u
-- JOIN sigad_alumnos_aux aux ON LOWER(u.username) = LOWER(aux.sigad_documento)
-- SET u.suspended = 0, u.timemodified = UNIX_TIMESTAMP()
-- WHERE u.suspended = 1;


-- =====================================================
-- ACTUALIZACIÓN 2: Actualizar emails
-- =====================================================
-- Descripción: Sincronizar email de SIGAD con Moodle

-- Verificar cambios (preview)
SELECT 
    u.id,
    u.username,
    u.email as email_actual,
    aux.sigad_email as email_nuevo
FROM mdl_user u
JOIN sigad_alumnos_aux aux ON LOWER(u.username) = LOWER(aux.sigad_documento)
WHERE LOWER(TRIM(u.email)) != LOWER(TRIM(aux.sigad_email));

-- Ejecutar actualización (descomentar para usar)
-- UPDATE mdl_user u
-- JOIN sigad_alumnos_aux aux ON LOWER(u.username) = LOWER(aux.sigad_documento)
-- SET 
--     u.email = aux.sigad_email,
--     u.timemodified = UNIX_TIMESTAMP()
-- WHERE LOWER(TRIM(u.email)) != LOWER(TRIM(aux.sigad_email));


-- =====================================================
-- ACTUALIZACIÓN 3: Suspender usuarios no en SIGAD
-- =====================================================
-- ⚠️  MUY PELIGROSO - Revisar lista cuidadosamente

-- Lista de usuarios que se suspenderían
SELECT 
    u.id,
    u.username,
    u.firstname,
    u.lastname,
    u.email,
    FROM_UNIXTIME(u.lastlogin) as ultimo_acceso
FROM mdl_user u
LEFT JOIN sigad_alumnos_aux aux ON LOWER(aux.sigad_documento) = LOWER(u.username)
WHERE u.deleted = 0
  AND u.suspended = 0
  AND u.id > 33  -- Excluir protegidos
  AND aux.id IS NULL
  -- Filtros adicionales de seguridad:
  AND u.email LIKE '%@fpvirtualaragon.es%'  -- Solo dominio institucional
  AND (u.lastlogin IS NULL OR u.lastlogin < UNIX_TIMESTAMP() - (90 * 24 * 60 * 60))  -- Sin acceso en 90 días
ORDER BY u.lastlogin;

-- Ejecutar suspensión (DESCOMENTAR CON MUCHO CUIDADO)
-- UPDATE mdl_user u
-- LEFT JOIN sigad_alumnos_aux aux ON LOWER(aux.sigad_documento) = LOWER(u.username)
-- SET 
--     u.suspended = 1,
--     u.timemodified = UNIX_TIMESTAMP()
-- WHERE u.deleted = 0
--   AND u.suspended = 0
--   AND u.id > 33
--   AND aux.id IS NULL
--   AND u.email LIKE '%@fpvirtualaragon.es%'
--   AND (u.lastlogin IS NULL OR u.lastlogin < UNIX_TIMESTAMP() - (90 * 24 * 60 * 60));


-- =====================================================
-- ACTUALIZACIÓN 4: Marcar procesados en tabla auxiliar
-- =====================================================
-- Después de ejecutar cambios, marcar registros como procesados

-- Marcar como PROCESADOS
-- UPDATE sigad_alumnos_aux
-- SET 
--     import_estado = 'PROCESADO',
--     fecha_procesamiento = NOW(),
--     observaciones = 'Sincronizado correctamente'
-- WHERE import_estado = 'PENDIENTE'
--   AND moodle_existe = TRUE;


-- =====================================================
-- VERIFICACIONES POST-ACTUALIZACIÓN
-- =====================================================

-- 1. Verificar que no queden usuarios duplicados
SELECT username, COUNT(*) as repeticiones
FROM mdl_user
WHERE deleted = 0
GROUP BY username
HAVING COUNT(*) > 1;

-- 2. Verificar emails duplicados
SELECT email, COUNT(*) as repeticiones
FROM mdl_user
WHERE deleted = 0
GROUP BY email
HAVING COUNT(*) > 1;

-- 3. Contar usuarios suspendidos vs activos
SELECT 
    CASE 
        WHEN suspended = 0 THEN 'Activos'
        WHEN suspended = 1 THEN 'Suspendidos'
    END as estado,
    COUNT(*) as cantidad
FROM mdl_user
WHERE deleted = 0
GROUP BY suspended;

-- 4. Verificar últimas modificaciones
SELECT 
    username,
    firstname,
    lastname,
    FROM_UNIXTIME(timemodified) as ultima_modificacion
FROM mdl_user
WHERE timemodified > UNIX_TIMESTAMP() - (24 * 60 * 60)  -- Últimas 24h
ORDER BY timemodified DESC
LIMIT 20;
