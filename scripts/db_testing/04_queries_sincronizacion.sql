-- =====================================================
-- QUERIES PARA SINCRONIZACIÓN SIGAD ↔ MOODLE
-- =====================================================
-- Estas queries comparan datos entre la tabla auxiliar SIGAD
-- y las tablas reales de Moodle para detectar diferencias

-- =====================================================
-- PASO 1: CRUZAR DATOS SIGAD CON MOODLE
-- =====================================================

-- Actualizar tabla auxiliar con información de Moodle
UPDATE sigad_alumnos_aux aux
LEFT JOIN mdl_user u ON LOWER(u.username) = LOWER(aux.sigad_documento)
SET 
    aux.moodle_userid = u.id,
    aux.moodle_username = u.username,
    aux.moodle_existe = (u.id IS NOT NULL AND u.deleted = 0),
    aux.moodle_suspended = COALESCE(u.suspended, 0),
    aux.moodle_email_actual = u.email;


-- =====================================================
-- PASO 2: DETECTAR ACCIONES REQUERIDAS
-- =====================================================

-- 2.1 Alumnos NUEVOS (no existen en Moodle)
SELECT 
    sigad_idalumno,
    sigad_documento,
    sigad_nombre,
    sigad_apellido1,
    sigad_apellido2,
    sigad_email,
    'CREAR_USUARIO' as accion,
    CONCAT('Crear usuario: ', sigad_documento, ' - ', sigad_nombre, ' ', sigad_apellido1) as descripcion
FROM sigad_alumnos_aux
WHERE moodle_existe = FALSE
ORDER BY sigad_apellido1, sigad_apellido2, sigad_nombre;


-- 2.2 Alumnos a REACTIVAR (suspendidos en Moodle pero activos en SIGAD)
SELECT 
    sigad_idalumno,
    sigad_documento,
    sigad_nombre,
    sigad_apellido1,
    sigad_apellido2,
    moodle_userid,
    moodle_username,
    'REACTIVAR' as accion,
    CONCAT('Reactivar usuario suspendido: ', moodle_username) as descripcion
FROM sigad_alumnos_aux
WHERE moodle_existe = TRUE
  AND moodle_suspended = TRUE;


-- 2.3 Alumnos con EMAIL DIFERENTE
SELECT 
    sigad_idalumno,
    sigad_documento,
    sigad_nombre,
    sigad_apellido1,
    moodle_userid,
    sigad_email as email_sigad,
    moodle_email_actual as email_moodle,
    'ACTUALIZAR_EMAIL' as accion,
    CONCAT('Cambiar email de ', moodle_email_actual, ' a ', sigad_email) as descripcion
FROM sigad_alumnos_aux
WHERE moodle_existe = TRUE
  AND LOWER(TRIM(sigad_email)) != LOWER(TRIM(moodle_email_actual));


-- 2.4 Usuarios en Moodle que NO están en SIGAD (posibles bajas)
-- IMPORTANTE: Revisar cuidadosamente antes de suspender
SELECT 
    u.id as moodle_userid,
    u.username,
    u.firstname,
    u.lastname,
    u.email,
    FROM_UNIXTIME(u.timecreated) as fecha_creacion,
    FROM_UNIXTIME(u.lastlogin) as ultimo_acceso,
    'POSIBLE_BAJA' as accion,
    CONCAT('Usuario en Moodle no encontrado en SIGAD: ', u.username) as descripcion
FROM mdl_user u
LEFT JOIN sigad_alumnos_aux aux ON LOWER(aux.sigad_documento) = LOWER(u.username)
WHERE u.deleted = 0
  AND u.id > 33  -- Excluir usuarios protegidos básicos
  AND aux.id IS NULL
  -- Opcional: filtrar por dominio de email institucional
  AND u.email LIKE '%@fpvirtualaragon.es%'
ORDER BY u.lastlogin DESC;


-- =====================================================
-- PASO 3: VERIFICAR MATRÍCULAS
-- =====================================================

-- 3.1 Matrículas actuales de alumnos en SIGAD
SELECT 
    aux.sigad_documento,
    aux.sigad_nombre,
    aux.sigad_apellido1,
    c.shortname as curso_siglas,
    c.fullname as curso_nombre,
    ue.status as estado_matricula,
    CASE 
        WHEN ue.status = 0 THEN 'Activa'
        WHEN ue.status = 1 THEN 'Suspendida'
        ELSE 'Desconocida'
    END as estado_texto
FROM sigad_alumnos_aux aux
JOIN mdl_user u ON LOWER(u.username) = LOWER(aux.sigad_documento)
JOIN mdl_user_enrolments ue ON ue.userid = u.id
JOIN mdl_enrol e ON e.id = ue.enrolid
JOIN mdl_course c ON c.id = e.courseid
WHERE aux.moodle_existe = TRUE
ORDER BY aux.sigad_apellido1, c.shortname;


-- 3.2 Alumnos sin matrículas activas (posible problema)
SELECT 
    aux.sigad_idalumno,
    aux.sigad_documento,
    aux.sigad_nombre,
    aux.sigad_apellido1,
    aux.sigad_siglas_ciclo,
    'SIN_MATRICULAS' as alerta,
    CONCAT('Usuario existe en Moodle pero sin matrículas activas') as descripcion
FROM sigad_alumnos_aux aux
JOIN mdl_user u ON LOWER(u.username) = LOWER(aux.sigad_documento)
LEFT JOIN mdl_user_enrolments ue ON ue.userid = u.id AND ue.status = 0
WHERE aux.moodle_existe = TRUE
  AND ue.id IS NULL;


-- =====================================================
-- PASO 4: RESUMEN EJECUTIVO
-- =====================================================

-- Vista resumen de todo el proceso
SELECT 
    'TOTAL EN SIGAD' as metrica,
    COUNT(*) as cantidad,
    '' as notas
FROM sigad_alumnos_aux

UNION ALL

SELECT 
    'YA EXISTEN EN MOODLE' as metrica,
    COUNT(*),
    'No requieren creación'
FROM sigad_alumnos_aux
WHERE moodle_existe = TRUE

UNION ALL

SELECT 
    'NUEVOS A CREAR' as metrica,
    COUNT(*),
    'Requieren user-create'
FROM sigad_alumnos_aux
WHERE moodle_existe = FALSE

UNION ALL

SELECT 
    'A REACTIVAR' as metrica,
    COUNT(*),
    'Están suspendidos'
FROM sigad_alumnos_aux
WHERE moodle_existe = TRUE AND moodle_suspended = TRUE

UNION ALL

SELECT 
    'EMAIL A ACTUALIZAR' as metrica,
    COUNT(*),
    'Cambio de email detectado'
FROM sigad_alumnos_aux
WHERE moodle_existe = TRUE 
  AND LOWER(TRIM(sigad_email)) != LOWER(TRIM(moodle_email_actual))

UNION ALL

SELECT 
    'POSIBLES BAJAS' as metrica,
    COUNT(*),
    'En Moodle pero no en SIGAD'
FROM mdl_user u
LEFT JOIN sigad_alumnos_aux aux ON LOWER(aux.sigad_documento) = LOWER(u.username)
WHERE u.deleted = 0 AND u.id > 33 AND aux.id IS NULL
  AND u.email LIKE '%@fpvirtualaragon.es%'

ORDER BY cantidad DESC;
