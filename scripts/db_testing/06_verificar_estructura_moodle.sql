-- =====================================================
-- VERIFICACIÓN DE ESTRUCTURA DE TABLAS MOODLE
-- =====================================================
-- Ejecutar estas queries para verificar que las tablas
-- necesarias existen y tienen la estructura esperada

-- =====================================================
-- 1. VERIFICAR TABLAS NECESARIAS
-- =====================================================

-- Lista de tablas que necesita el sistema
SELECT 
    table_name,
    CASE 
        WHEN table_name IN (
            'mdl_user',
            'mdl_course', 
            'mdl_enrol',
            'mdl_user_enrolments',
            'mdl_cohort',
            'mdl_cohort_members',
            'mdl_user_info_data',
            'mdl_user_info_field'
        ) THEN 'REQUERIDA'
        ELSE 'OPCIONAL'
    END as importancia
FROM information_schema.tables
WHERE table_schema = DATABASE()
  AND table_name LIKE 'mdl_%'
ORDER BY 
    CASE 
        WHEN table_name = 'mdl_user' THEN 1
        WHEN table_name = 'mdl_course' THEN 2
        WHEN table_name = 'mdl_enrol' THEN 3
        WHEN table_name = 'mdl_user_enrolments' THEN 4
        WHEN table_name = 'mdl_cohort' THEN 5
        WHEN table_name = 'mdl_cohort_members' THEN 6
        ELSE 99
    END;


-- =====================================================
-- 2. ESTRUCTURA DE mdl_user
-- =====================================================

-- Columnas importantes de usuarios
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default,
    extra
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'mdl_user'
ORDER BY ordinal_position;

-- Índices de mdl_user
SELECT 
    index_name,
    column_name,
    cardinality
FROM information_schema.statistics
WHERE table_schema = DATABASE()
  AND table_name = 'mdl_user'
ORDER BY index_name, seq_in_index;


-- =====================================================
-- 3. ESTRUCTURA DE mdl_cohort
-- =====================================================

-- Verificar estructura de cohortes
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'mdl_cohort'
ORDER BY ordinal_position;


-- =====================================================
-- 4. ESTRUCTURA DE mdl_user_enrolments
-- =====================================================

-- Verificar estructura de matrículas
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'mdl_user_enrolments'
ORDER BY ordinal_position;


-- =====================================================
-- 5. VERIFICAR COHORTE "alumnado"
-- =====================================================

-- Esta cohorte es CRÍTICA para el funcionamiento
SELECT 
    id,
    name,
    idnumber,
    description,
    CASE 
        WHEN idnumber = 'alumnado' THEN '✅ OK - Cohorte alumnado encontrada'
        ELSE '⚠️ Cohorte encontrada pero idnumber diferente'
    END as estado
FROM mdl_cohort
WHERE idnumber = 'alumnado'
   OR name LIKE '%alumnado%'
   OR name LIKE '%Alumnado%';

-- Si no existe, mostrar todas las cohortes para elegir alternativa
SELECT 'Cohortes disponibles:' as info;
SELECT id, name, idnumber FROM mdl_cohort ORDER BY name LIMIT 20;


-- =====================================================
-- 6. VERIFICAR ÍNDICES CRÍTICOS
-- =====================================================

-- Índice en username (fundamental para búsquedas)
SELECT 
    'mdl_user.username' as campo,
    CASE 
        WHEN COUNT(*) > 0 THEN '✅ Tiene índice'
        ELSE '⚠️ SIN ÍNDICE - Puede ser lento'
    END as estado
FROM information_schema.statistics
WHERE table_schema = DATABASE()
  AND table_name = 'mdl_user'
  AND column_name = 'username';

-- Índice en email
SELECT 
    'mdl_user.email' as campo,
    CASE 
        WHEN COUNT(*) > 0 THEN '✅ Tiene índice'
        ELSE '⚠️ SIN ÍNDICE'
    END as estado
FROM information_schema.statistics
WHERE table_schema = DATABASE()
  AND table_name = 'mdl_user'
  AND column_name = 'email';


-- =====================================================
-- 7. ESTADÍSTICAS DE TABLAS
-- =====================================================

-- Tamaño de tablas principales
SELECT 
    table_name,
    table_rows as filas_aprox,
    ROUND(data_length / 1024 / 1024, 2) as tamano_mb
FROM information_schema.tables
WHERE table_schema = DATABASE()
  AND table_name IN (
      'mdl_user',
      'mdl_course',
      'mdl_user_enrolments',
      'mdl_cohort_members'
  )
ORDER BY data_length DESC;


-- =====================================================
-- 8. CREAR ÍNDICES FALTANTES (si es necesario)
-- =====================================================

-- Si falta índice en username (descomentar para crear)
-- CREATE INDEX idx_user_username ON mdl_user(username);

-- Índice para búsquedas por email (descomentar para crear)
-- CREATE INDEX idx_user_email ON mdl_user(email);

-- Índice útil para cruce SIGAD-Moodle (descomentar para crear)
-- CREATE INDEX idx_sigad_documento ON sigad_alumnos_aux(sigad_documento);
