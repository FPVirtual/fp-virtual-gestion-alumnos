-- =====================================================
-- ESQUEMA TABLA AUXILIAR SIGAD
-- =====================================================
-- Tabla para almacenar datos de estudiantes importados desde SIGAD
-- antes de sincronizar con Moodle

-- Eliminar tabla si existe (para recrear)
DROP TABLE IF EXISTS sigad_alumnos_aux;

-- Crear tabla auxiliar
CREATE TABLE sigad_alumnos_aux (
    -- Identificadores
    id INT AUTO_INCREMENT PRIMARY KEY,
    sigad_idalumno INT NOT NULL COMMENT 'ID del alumno en SIGAD',
    sigad_documento VARCHAR(20) NOT NULL COMMENT 'DNI/NIE del alumno',
    
    -- Datos personales
    sigad_nombre VARCHAR(100) NOT NULL,
    sigad_apellido1 VARCHAR(100) NOT NULL,
    sigad_apellido2 VARCHAR(100) NULL,
    sigad_email VARCHAR(200) NOT NULL,
    sigad_email_personal VARCHAR(200) NULL COMMENT 'Email personal (para notificaciones)',
    
    -- Centro y estudios
    sigad_codigo_centro VARCHAR(20) NULL,
    sigad_nombre_centro VARCHAR(200) NULL,
    sigad_codigo_ciclo VARCHAR(20) NULL,
    sigad_nombre_ciclo VARCHAR(200) NULL,
    sigad_siglas_ciclo VARCHAR(20) NULL,
    
    -- Módulos matriculados (JSON para flexibilidad)
    sigad_modulos JSON NULL COMMENT 'Array de módulos matriculados',
    
    -- Metadatos de importación
    import_fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    import_estado VARCHAR(20) DEFAULT 'PENDIENTE' 
        COMMENT 'PENDIENTE, PROCESADO, ERROR, IGNORADO',
    import_batch VARCHAR(50) NULL COMMENT 'Identificador del lote de importación',
    
    -- Campos de sincronización (se rellenan al comparar con Moodle)
    moodle_userid INT NULL COMMENT 'ID de usuario en Moodle (mdl_user.id)',
    moodle_username VARCHAR(100) NULL,
    moodle_existe TINYINT(1) DEFAULT 0,
    moodle_suspended TINYINT(1) DEFAULT 0,
    moodle_email_actual VARCHAR(200) NULL COMMENT 'Email actual en Moodle',
    
    -- Estado del proceso
    accion_requerida VARCHAR(50) NULL 
        COMMENT 'CREAR, ACTUALIZAR_EMAIL, REACTIVAR, SIN_CAMBIOS, etc.',
    fecha_procesamiento DATETIME NULL,
    observaciones TEXT NULL
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Tabla auxiliar para importación de datos desde SIGAD';

-- Crear índices por separado (mayor compatibilidad con MariaDB)
CREATE INDEX idx_sigad_idalumno ON sigad_alumnos_aux(sigad_idalumno);
CREATE INDEX idx_sigad_documento ON sigad_alumnos_aux(sigad_documento);
CREATE INDEX idx_import_estado ON sigad_alumnos_aux(import_estado);
CREATE INDEX idx_moodle_userid ON sigad_alumnos_aux(moodle_userid);
CREATE INDEX idx_accion ON sigad_alumnos_aux(accion_requerida);
CREATE INDEX idx_batch ON sigad_alumnos_aux(import_batch);


-- =====================================================
-- VISTA: Alumnos pendientes de procesar
-- =====================================================
DROP VIEW IF EXISTS v_sigad_pendientes;

CREATE VIEW v_sigad_pendientes AS
SELECT 
    id,
    sigad_idalumno,
    sigad_documento,
    sigad_nombre,
    sigad_apellido1,
    sigad_apellido2,
    sigad_email,
    sigad_nombre_ciclo,
    sigad_siglas_ciclo,
    import_fecha,
    moodle_existe,
    moodle_suspended,
    CASE 
        WHEN moodle_existe = 0 THEN 'CREAR_USUARIO'
        WHEN moodle_suspended = 1 THEN 'REACTIVAR'
        WHEN moodle_email_actual != sigad_email THEN 'ACTUALIZAR_EMAIL'
        ELSE 'VERIFICAR_MATRICULAS'
    END AS accion_sugerida
FROM sigad_alumnos_aux
WHERE import_estado = 'PENDIENTE';


-- =====================================================
-- VISTA: Resumen de importación por batch
-- =====================================================
DROP VIEW IF EXISTS v_sigad_resumen_batch;

CREATE VIEW v_sigad_resumen_batch AS
SELECT 
    import_batch,
    DATE(import_fecha) as fecha_importacion,
    COUNT(*) as total_alumnos,
    SUM(CASE WHEN import_estado = 'PENDIENTE' THEN 1 ELSE 0 END) as pendientes,
    SUM(CASE WHEN import_estado = 'PROCESADO' THEN 1 ELSE 0 END) as procesados,
    SUM(CASE WHEN import_estado = 'ERROR' THEN 1 ELSE 0 END) as con_error,
    SUM(CASE WHEN moodle_existe = 1 THEN 1 ELSE 0 END) as ya_existen_moodle,
    SUM(CASE WHEN moodle_existe = 0 THEN 1 ELSE 0 END) as nuevos
FROM sigad_alumnos_aux
GROUP BY import_batch, DATE(import_fecha)
ORDER BY import_fecha DESC;
