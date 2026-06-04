-- =====================================================
-- EXTRAER DATOS MANUALMENTE PARA CREAR CASOS DE TEST
-- =====================================================
-- Instrucciones:
-- 1. Ejecutar estas queries en DBeaver
-- 2. Copiar los resultados (Ctrl+C o botón Copiar)
-- 3. Pegar en Excel o editor de texto
-- 4. Guardar como CSV
-- 5. Modificar los datos para crear los 7 casos
-- =====================================================

-- =====================================================
-- QUERY 1: Seleccionar 10 usuarios base
-- =====================================================
-- Copiar el resultado completo (incluyendo headers)

SELECT 
    u.id as moodle_userid,
    u.username as documento_actual,
    u.firstname as nombre,
    u.lastname as apellido1,
    '' as apellido2,
    u.email as email_actual,
    u.suspended as esta_suspendido,
    FROM_UNIXTIME(u.timecreated) as fecha_creacion,
    GROUP_CONCAT(DISTINCT c.shortname ORDER BY c.shortname SEPARATOR ', ') as cursos_actuales
FROM mdl_user u
JOIN mdl_user_enrolments ue ON ue.userid = u.id
JOIN mdl_enrol e ON e.id = ue.enrolid
JOIN mdl_course c ON c.id = e.courseid
WHERE u.deleted = 0
  AND u.id > 1000  -- Excluir protegidos
GROUP BY u.id, u.username, u.firstname, u.lastname, u.email, u.suspended, u.timecreated
ORDER BY MAX(ue.timestart) DESC
LIMIT 10;


-- =====================================================
-- QUERY 2: Buscar usuarios suspendidos (para caso 2)
-- =====================================================
-- Si hay suspendidos, copiar uno. Si no, usaremos uno normal

SELECT 
    u.id,
    u.username,
    u.firstname,
    u.lastname,
    u.email,
    u.suspended,
    FROM_UNIXTIME(u.lastlogin) as ultimo_acceso
FROM mdl_user u
WHERE u.deleted = 0
  AND u.suspended = 1
  AND u.id > 1000
ORDER BY u.lastlogin DESC
LIMIT 5;


-- =====================================================
-- QUERY 3: Ver cursos disponibles
-- =====================================================
-- Para saber qué cursos podemos usar en los casos de test

SELECT 
    id,
    shortname as siglas,
    fullname as nombre,
    visible as activo
FROM mdl_course
WHERE id > 1
  AND visible = 1
ORDER BY shortname
LIMIT 20;


-- =====================================================
-- QUERY 4: Ver cohortes disponibles
-- =====================================================

SELECT id, name, idnumber
FROM mdl_cohort
ORDER BY name;


-- =====================================================
-- QUERY 5: Verificar usuario específico (para consulta)
-- =====================================================
-- Reemplaza '12345678a' por el username que quieras verificar

SELECT 
    u.*,
    FROM_UNIXTIME(u.timecreated) as creado,
    FROM_UNIXTIME(u.timemodified) as modificado,
    FROM_UNIXTIME(u.lastlogin) as ultimo_login
FROM mdl_user u
WHERE u.username = '12345678a';


-- =====================================================
-- QUERY 6: Ver matrículas de usuario específico
-- =====================================================
-- Reemplaza '12345678a' por el username

SELECT 
    c.shortname as curso,
    c.fullname,
    e.enrol as metodo,
    CASE ue.status 
        WHEN 0 THEN 'Activa'
        WHEN 1 THEN 'Suspendida'
    END as estado,
    FROM_UNIXTIME(ue.timestart) as fecha_inicio
FROM mdl_user u
JOIN mdl_user_enrolments ue ON ue.userid = u.id
JOIN mdl_enrol e ON e.id = ue.enrolid
JOIN mdl_course c ON c.id = e.courseid
WHERE u.username = '12345678a'
ORDER BY c.shortname;
