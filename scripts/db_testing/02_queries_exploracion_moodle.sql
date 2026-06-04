-- =====================================================
-- QUERIES PARA EXPLORACIÓN DE DATOS EN MOODLE (DBeaver)
-- =====================================================
-- Copia y pega estas queries en DBeaver para explorar
-- los datos del backup antes de sincronizar

-- =====================================================
-- 1. EXPLORAR USUARIOS
-- =====================================================

-- 1.1 Contar usuarios totales
SELECT COUNT(*) as total_usuarios FROM mdl_user WHERE deleted = 0;

-- 1.2 Usuarios suspendidos
SELECT COUNT(*) as suspendidos FROM mdl_user WHERE suspended = 1 AND deleted = 0;

-- 1.3 Usuarios por dominio de email
SELECT 
    SUBSTRING_INDEX(email, '@', -1) as dominio,
    COUNT(*) as cantidad
FROM mdl_user 
WHERE deleted = 0
GROUP BY dominio
ORDER BY cantidad DESC;

-- 1.4 Buscar un usuario específico por DNI/NIE
-- (reemplaza '12345678A' por el documento a buscar)
SELECT 
    id,
    username,
    email,
    firstname,
    lastname,
    suspended,
    lastlogin,
    FROM_UNIXTIME(timecreated) as fecha_creacion
FROM mdl_user 
WHERE username = '12345678a'  -- Moodle guarda username en minúsculas
   OR username = '12345678A'
   OR email LIKE '%12345678A%';

-- 1.5 Usuarios protegidos (no se deben eliminar)
SELECT id, username, firstname, lastname, email
FROM mdl_user 
WHERE id IN (1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,
             21,22,23,24,25,26,27,28,29,30,31,32,33,3725,3729,3730,
             7152,7490,7491,11720,12270,12272)
ORDER BY id;


-- =====================================================
-- 2. EXPLORAR COHORTES
-- =====================================================

-- 2.1 Listar todas las cohortes
SELECT id, name, idnumber, description
FROM mdl_cohort
ORDER BY name;

-- 2.2 Buscar cohorte "alumnado" (donde se matriculan nuevos)
SELECT id, name, idnumber, description
FROM mdl_cohort
WHERE idnumber = 'alumnado'
   OR name LIKE '%alumnado%'
   OR name LIKE '%Alumnado%';

-- 2.3 Contar miembros por cohorte
SELECT 
    c.id,
    c.name,
    c.idnumber,
    COUNT(cm.id) as num_miembros
FROM mdl_cohort c
LEFT JOIN mdl_cohort_members cm ON cm.cohortid = c.id
GROUP BY c.id, c.name, c.idnumber
ORDER BY num_miembros DESC;

-- 2.4 Miembros de una cohorte específica
-- (reemplaza ID_COHORTE por el ID real)
SELECT 
    u.id as userid,
    u.username,
    u.firstname,
    u.lastname,
    u.email,
    FROM_UNIXTIME(cm.timeadded) as fecha_matricula_cohorte
FROM mdl_cohort_members cm
JOIN mdl_user u ON u.id = cm.userid
WHERE cm.cohortid = (SELECT id FROM mdl_cohort WHERE idnumber = 'alumnado' LIMIT 1)
ORDER BY cm.timeadded DESC;


-- =====================================================
-- 3. EXPLORAR CURSOS
-- =====================================================

-- 3.1 Contar cursos totales
SELECT COUNT(*) as total_cursos FROM mdl_course WHERE id > 1;  -- id=1 es site course

-- 3.2 Cursos activos (visibles)
SELECT id, shortname, fullname, visible
FROM mdl_course
WHERE id > 1 AND visible = 1
ORDER BY shortname;

-- 3.3 Buscar cursos por siglas (ej: IPPE1, IFC301, etc.)
SELECT id, shortname, fullname, category
FROM mdl_course
WHERE shortname LIKE '%IPPE%'
   OR shortname LIKE '%IFC%'
   OR shortname LIKE '%SSC%'
ORDER BY shortname;


-- =====================================================
-- 4. EXPLORAR MATRÍCULAS
-- =====================================================

-- 4.1 Contar matrículas activas
SELECT COUNT(*) as matriculas_activas 
FROM mdl_user_enrolments ue
JOIN mdl_enrol e ON e.id = ue.enrolid
WHERE ue.status = 0;

-- 4.2 Matrículas por usuario específico
-- (reemplaza '12345678a' por el username)
SELECT 
    u.username,
    u.firstname,
    u.lastname,
    c.shortname as curso_siglas,
    c.fullname as curso_nombre,
    e.enrol as metodo_matricula,
    FROM_UNIXTIME(ue.timestart) as fecha_inicio,
    CASE ue.status 
        WHEN 0 THEN 'Activa'
        WHEN 1 THEN 'Suspendida'
        ELSE 'Otro'
    END as estado
FROM mdl_user u
JOIN mdl_user_enrolments ue ON ue.userid = u.id
JOIN mdl_enrol e ON e.id = ue.enrolid
JOIN mdl_course c ON c.id = e.courseid
WHERE u.username = '12345678a'
ORDER BY c.shortname;

-- 4.3 Usuarios sin matrículas (posiblemente huérfanos)
SELECT 
    u.id,
    u.username,
    u.firstname,
    u.lastname,
    u.email,
    FROM_UNIXTIME(u.timecreated) as fecha_creacion
FROM mdl_user u
LEFT JOIN mdl_user_enrolments ue ON ue.userid = u.id
WHERE u.deleted = 0
  AND u.id > 1  -- No es admin/guest
  AND ue.id IS NULL
ORDER BY u.timecreated DESC
LIMIT 50;


-- =====================================================
-- 5. VISTA INTEGRADA: Estado completo de un usuario
-- =====================================================
-- (reemplaza '12345678a' por el username a consultar)

SELECT 
    u.id as moodle_userid,
    u.username,
    u.firstname,
    u.lastname,
    u.email as moodle_email,
    u.suspended as usuario_suspendido,
    FROM_UNIXTIME(u.timecreated) as fecha_creacion_moodle,
    FROM_UNIXTIME(u.lastlogin) as ultimo_acceso,
    
    -- Cohorte
    c.idnumber as cohorte,
    FROM_UNIXTIME(cm.timeadded) as fecha_en_cohorte,
    
    -- Contar matrículas
    (SELECT COUNT(*) 
     FROM mdl_user_enrolments ue2 
     JOIN mdl_enrol e2 ON e2.id = ue2.enrolid
     WHERE ue2.userid = u.id AND ue2.status = 0) as num_matriculas_activas,
     
    -- Lista de cursos matriculados
    (SELECT GROUP_CONCAT(c2.shortname SEPARATOR ', ')
     FROM mdl_user_enrolments ue3
     JOIN mdl_enrol e3 ON e3.id = ue3.enrolid
     JOIN mdl_course c2 ON c2.id = e3.courseid
     WHERE ue3.userid = u.id AND ue3.status = 0
     LIMIT 10) as cursos_matriculados

FROM mdl_user u
LEFT JOIN mdl_cohort_members cm ON cm.userid = u.id
LEFT JOIN mdl_cohort c ON c.id = cm.cohortid
WHERE u.username = '12345678a'
  AND u.deleted = 0;
