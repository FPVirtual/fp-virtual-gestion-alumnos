-- =====================================================
-- QUERIES PARA VERIFICACIÓN MANUAL DE CASOS
-- =====================================================
-- Ejecutar estas queries en DBeaver para verificar
-- que los casos se detectan correctamente
-- =====================================================

-- =====================================================
-- CONFIGURACIÓN: Crear tabla temporal con tus casos
-- =====================================================
-- PASO 1: Ejecutar esto y modificar con tus datos

DROP TABLE IF EXISTS tmp_mis_casos_test;

CREATE TABLE tmp_mis_casos_test (
    caso_id INT PRIMARY KEY,
    caso_descripcion VARCHAR(100),
    sigad_documento VARCHAR(20),
    sigad_nombre VARCHAR(100),
    sigad_apellido1 VARCHAR(100),
    sigad_email VARCHAR(200),
    sigad_cursos TEXT
);

-- PASO 2: Insertar tus casos (modifica con tus datos)
INSERT INTO tmp_mis_casos_test VALUES
(1, 'NUEVO', '12345678A', 'Ana', 'García', 'ana.nueva@ejemplo.com', 'IFC301;IFC302'),
(2, 'REACTIVAR', '23456789B', 'Carlos', 'Martínez', 'carlos@ejemplo.com', 'IFC302'),
(3, 'CAMBIO_EMAIL', '34567890C', 'Lucía', 'Fernández', 'lucia.nuevo@ejemplo.com', 'SSC302'),
(4, 'CAMBIO_NOMBRE', '45678901D', 'María Elena', 'Rodríguez', 'maria@ejemplo.com', 'IFC303'),
(5, 'CAMBIO_DOC', '56789012E', 'Pedro', 'López', 'pedro@ejemplo.com', 'IFC301'),
(6, 'NUEVOS_CURSOS', '67890123F', 'Sofía', 'Martín', 'sofia@ejemplo.com', 'IFC301;LM;ED;SI'),
(7, 'BAJA_PARCIAL', '78901234G', 'Javier', 'Sánchez', 'javier@ejemplo.com', 'PROG');


-- =====================================================
-- VERIFICACIÓN 1: ¿Existen en Moodle?
-- =====================================================

SELECT 
    c.caso_id,
    c.caso_descripcion,
    c.sigad_documento,
    CASE 
        WHEN u.id IS NOT NULL THEN 'EXISTE'
        ELSE 'NO EXISTE'
    END as estado_moodle,
    u.id as moodle_userid,
    u.username as moodle_username,
    u.suspended,
    u.email as moodle_email
FROM tmp_mis_casos_test c
LEFT JOIN mdl_user u ON LOWER(u.username) = LOWER(c.sigad_documento)
ORDER BY c.caso_id;


-- =====================================================
-- VERIFICACIÓN 2: Comparar emails
-- =====================================================

SELECT 
    c.caso_id,
    c.caso_descripcion,
    c.sigad_documento,
    c.sigad_email as email_sigad,
    u.email as email_moodle,
    CASE 
        WHEN LOWER(TRIM(c.sigad_email)) = LOWER(TRIM(u.email)) THEN 'IGUAL'
        ELSE 'DIFERENTE'
    END as comparacion
FROM tmp_mis_casos_test c
LEFT JOIN mdl_user u ON LOWER(u.username) = LOWER(c.sigad_documento)
WHERE u.id IS NOT NULL
ORDER BY c.caso_id;


-- =====================================================
-- VERIFICACIÓN 3: Comparar nombres
-- =====================================================

SELECT 
    c.caso_id,
    c.sigad_documento,
    c.sigad_nombre as nombre_sigad,
    u.firstname as nombre_moodle,
    c.sigad_apellido1 as apellido_sigad,
    u.lastname as apellido_moodle,
    CASE 
        WHEN CONCAT(c.sigad_nombre, ' ', c.sigad_apellido1) != 
             CONCAT(u.firstname, ' ', u.lastname) THEN 'DIFERENTE'
        ELSE 'IGUAL'
    END as comparacion
FROM tmp_mis_casos_test c
LEFT JOIN mdl_user u ON LOWER(u.username) = LOWER(c.sigad_documento)
WHERE u.id IS NOT NULL
ORDER BY c.caso_id;


-- =====================================================
-- VERIFICACIÓN 4: Matrículas actuales
-- =====================================================

SELECT 
    c.caso_id,
    c.sigad_documento,
    c.sigad_cursos as cursos_sigad,
    GROUP_CONCAT(DISTINCT co.shortname ORDER BY co.shortname SEPARATOR ', ') as cursos_moodle,
    COUNT(DISTINCT co.id) as num_cursos_moodle
FROM tmp_mis_casos_test c
LEFT JOIN mdl_user u ON LOWER(u.username) = LOWER(c.sigad_documento)
LEFT JOIN mdl_user_enrolments ue ON ue.userid = u.id AND ue.status = 0
LEFT JOIN mdl_enrol e ON e.id = ue.enrolid
LEFT JOIN mdl_course co ON co.id = e.courseid
WHERE u.id IS NOT NULL
GROUP BY c.caso_id, c.sigad_documento, c.sigad_cursos
ORDER BY c.caso_id;


-- =====================================================
-- VERIFICACIÓN 5: Resumen de acciones necesarias
-- =====================================================

SELECT 
    c.caso_id,
    c.caso_descripcion,
    c.sigad_documento,
    CASE 
        WHEN u.id IS NULL THEN 'CREAR_USUARIO'
        WHEN u.suspended = 1 THEN 'REACTIVAR'
        WHEN LOWER(TRIM(c.sigad_email)) != LOWER(TRIM(u.email)) THEN 'ACTUALIZAR_EMAIL'
        WHEN c.sigad_nombre != u.firstname THEN 'VERIFICAR_NOMBRE'
        ELSE 'VERIFICAR_MATRICULAS'
    END as accion_sugerida,
    CASE 
        WHEN u.id IS NULL THEN 'Usuario no existe'
        WHEN u.suspended = 1 THEN 'Está suspendido'
        WHEN LOWER(TRIM(c.sigad_email)) != LOWER(TRIM(u.email)) 
            THEN CONCAT('Email: ', u.email, ' → ', c.sigad_email)
        WHEN c.sigad_nombre != u.firstname 
            THEN CONCAT('Nombre: ', u.firstname, ' → ', c.sigad_nombre)
        ELSE 'Revisar cursos'
    END as detalle
FROM tmp_mis_casos_test c
LEFT JOIN mdl_user u ON LOWER(u.username) = LOWER(c.sigad_documento)
ORDER BY c.caso_id;


-- =====================================================
-- VERIFICACIÓN 6: Comparación detallada de cursos
-- =====================================================
-- Para casos 6 y 7 (nuevas matrículas / bajas)

SELECT 
    c.caso_id,
    c.sigad_documento,
    'SIGAD' as origen,
    TRIM(SUBSTRING_INDEX(SUBSTRING_INDEX(c.sigad_cursos, ';', numbers.n), ';', -1)) as curso
FROM tmp_mis_casos_test c
CROSS JOIN (
    SELECT 1 as n UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 
    UNION SELECT 5
) numbers
WHERE CHAR_LENGTH(c.sigad_cursos) - CHAR_LENGTH(REPLACE(c.sigad_cursos, ';', '')) >= numbers.n - 1

UNION ALL

SELECT 
    c.caso_id,
    c.sigad_documento,
    'MOODLE' as origen,
    co.shortname as curso
FROM tmp_mis_casos_test c
JOIN mdl_user u ON LOWER(u.username) = LOWER(c.sigad_documento)
JOIN mdl_user_enrolments ue ON ue.userid = u.id AND ue.status = 0
JOIN mdl_enrol e ON e.id = ue.enrolid
JOIN mdl_course co ON co.id = e.courseid

ORDER BY caso_id, sigad_documento, origen, curso;
