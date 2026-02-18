-- =============================================================================
-- TABLA AUXILIAR PARA SINCRONIZACIÓN SIGAD -> MOODLE
-- =============================================================================
-- Propósito: Almacenar el estado de matriculaciones desde SIGAD para poder
-- comparar con ejecuciones anteriores y detectar cambios.
-- 
-- Estructura: Tabla desnormalizada (una fila por cada combinación 
-- Alumno + Centro + Ciclo + Módulo)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. CREACIÓN DE LA TABLA AUXILIAR
-- -----------------------------------------------------------------------------
DROP TABLE IF EXISTS mdl_aux_sigad_matriculas;

CREATE TABLE mdl_aux_sigad_matriculas (
    -- Clave primaria interna
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    
    -- -------------------------------------------------------------------------
    -- DATOS DEL ALUMNO (desde SIGAD)
    -- -------------------------------------------------------------------------
    sigad_idalumno INT UNSIGNED NOT NULL COMMENT 'ID único del alumno en SIGAD',
    sigad_idtipodocumento TINYINT UNSIGNED COMMENT '1=DNI, 2=NIE, 3=PASAPORTE, etc.',
    sigad_documento VARCHAR(20) NOT NULL COMMENT 'Número de documento (DNI/NIE)',
    sigad_nombre VARCHAR(100) NOT NULL,
    sigad_apellido1 VARCHAR(100) NOT NULL,
    sigad_apellido2 VARCHAR(100) NULL COMMENT 'Puede ser NULL',
    sigad_email VARCHAR(255) NOT NULL,
    
    -- -------------------------------------------------------------------------
    -- DATOS DEL CENTRO
    -- -------------------------------------------------------------------------
    sigad_codigocentro VARCHAR(20) NOT NULL COMMENT 'Código del centro en SIGAD',
    sigad_centro VARCHAR(200) NOT NULL COMMENT 'Nombre del centro',
    
    -- -------------------------------------------------------------------------
    -- DATOS DEL CICLO
    -- -------------------------------------------------------------------------
    sigad_idficha INT UNSIGNED NOT NULL COMMENT 'ID de la ficha de matrícula',
    sigad_codigociclo VARCHAR(20) NOT NULL COMMENT 'Código oficial del ciclo',
    sigad_ciclo VARCHAR(200) NOT NULL COMMENT 'Nombre completo del ciclo',
    sigad_siglasciclo VARCHAR(20) NOT NULL COMMENT 'Siglas del ciclo (ej: SSC302)',
    
    -- -------------------------------------------------------------------------
    -- DATOS DEL MÓDULO
    -- -------------------------------------------------------------------------
    sigad_idmateria INT UNSIGNED NOT NULL COMMENT 'ID de la materia/módulo',
    sigad_modulo VARCHAR(255) NOT NULL COMMENT 'Nombre completo del módulo',
    sigad_siglasmodulo VARCHAR(50) NOT NULL COMMENT 'Siglas del módulo (ej: IPPE1)',
    
    -- -------------------------------------------------------------------------
    -- METADATOS DE SINCRONIZACIÓN
    -- -------------------------------------------------------------------------
    fecha_sincronizacion DATE NOT NULL COMMENT 'Fecha de la sincronización (desde JSON)',
    hora_sincronizacion TIME NOT NULL COMMENT 'Hora de la sincronización (desde JSON)',
    batch_id VARCHAR(50) NOT NULL COMMENT 'Identificador único de la ejecución (ej: 20250218_153000)',
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Cuándo se insertó en esta tabla',
    
    -- -------------------------------------------------------------------------
    -- ÍNDICES ÚNICOS Y CONSTRAINTS
    -- -------------------------------------------------------------------------
    UNIQUE KEY uk_alumno_matricula (
        sigad_idalumno, 
        sigad_codigocentro, 
        sigad_idficha, 
        sigad_idmateria,
        batch_id
    ) COMMENT 'Evita duplicados por batch',
    
    -- Índice para búsquedas rápidas por alumno
    KEY idx_alumno (sigad_idalumno),
    
    -- Índice para búsquedas por documento
    KEY idx_documento (sigad_documento),
    
    -- Índice para búsquedas por batch (comparaciones entre ejecuciones)
    KEY idx_batch (batch_id),
    
    -- Índice compuesto para joins eficientes
    KEY idx_matricula_compuesta (sigad_codigocentro, sigad_codigociclo, sigad_idmateria)
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Tabla auxiliar para comparar datos de SIGAD entre ejecuciones';


-- -----------------------------------------------------------------------------
-- 2. TABLA DE HISTÓRICO DE CAMBIOS (opcional pero recomendada)
-- -----------------------------------------------------------------------------
DROP TABLE IF EXISTS mdl_aux_sigad_historico_cambios;

CREATE TABLE mdl_aux_sigad_historico_cambios (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    
    -- Identificación del cambio
    tipo_cambio ENUM('NUEVO_ALUMNO', 'ALUMNO_ELIMINADO', 'DATOS_PERSONALES_MODIFICADOS', 
                     'MODULO_AGREGADO', 'MODULO_ELIMINADO', 'CENTRO_CAMBIADO', 
                     'CICLO_CAMBIADO', 'EMAIL_MODIFICADO', 'DOCUMENTO_MODIFICADO') NOT NULL,
    
    -- Datos del alumno afectado
    sigad_idalumno INT UNSIGNED NOT NULL,
    sigad_documento VARCHAR(20),
    
    -- Descripción del cambio
    campo_afectado VARCHAR(50) COMMENT 'Qué campo cambió (si aplica)',
    valor_anterior TEXT COMMENT 'Valor anterior',
    valor_nuevo TEXT COMMENT 'Valor nuevo',
    
    -- Contexto
    batch_anterior VARCHAR(50) COMMENT 'ID del batch anterior',
    batch_nuevo VARCHAR(50) COMMENT 'ID del batch nuevo (actual)',
    
    -- Metadatos
    fecha_deteccion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    procesado BOOLEAN DEFAULT FALSE COMMENT 'Si ya se aplicó el cambio en Moodle',
    observaciones TEXT
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Histórico de cambios detectados entre sincronizaciones';

CREATE KEY idx_historico_alumno ON mdl_aux_sigad_historico_cambios(sigad_idalumno);
CREATE KEY idx_historico_batch ON mdl_aux_sigad_historico_cambios(batch_nuevo);
CREATE KEY idx_historico_tipo ON mdl_aux_sigad_historico_cambios(tipo_cambio);


-- -----------------------------------------------------------------------------
-- 3. VISTAS ÚTILES PARA CONSULTAS FRECUENTES
-- -----------------------------------------------------------------------------

-- Vista: Resumen de alumnos por batch
DROP VIEW IF EXISTS v_sigad_resumen_alumnos;
CREATE VIEW v_sigad_resumen_alumnos AS
SELECT 
    batch_id,
    fecha_sincronizacion,
    COUNT(DISTINCT sigad_idalumno) AS total_alumnos,
    COUNT(DISTINCT sigad_documento) AS total_documentos_unicos,
    COUNT(*) AS total_matriculas_modulos
FROM mdl_aux_sigad_matriculas
GROUP BY batch_id, fecha_sincronizacion
ORDER BY fecha_sincronizacion DESC, batch_id DESC;


-- Vista: Alumnos con múltiples centros en el mismo batch
DROP VIEW IF EXISTS v_sigad_alumnos_multicentro;
CREATE VIEW v_sigad_alumnos_multicentro AS
SELECT 
    batch_id,
    sigad_idalumno,
    sigad_documento,
    sigad_nombre,
    sigad_apellido1,
    COUNT(DISTINCT sigad_codigocentro) AS num_centros,
    GROUP_CONCAT(DISTINCT sigad_centro SEPARATOR ' | ') AS centros
FROM mdl_aux_sigad_matriculas
GROUP BY batch_id, sigad_idalumno, sigad_documento, sigad_nombre, sigad_apellido1
HAVING num_centros > 1;


-- =============================================================================
-- 4. QUERIES PARA DETECCIÓN DE CAMBIOS
-- =============================================================================
-- Estas queries se ejecutan comparando dos batches (ejecuciones)
-- Reemplazar :batch_anterior y :batch_nuevo con los valores correspondientes
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 4.1 ALUMNOS NUEVOS: Están en batch_nuevo pero NO en batch_anterior
-- -----------------------------------------------------------------------------
-- Resultado: Alumnos que deben crearse en Moodle
-- -----------------------------------------------------------------------------
SELECT DISTINCT 
    n.sigad_idalumno,
    n.sigad_documento,
    n.sigad_idtipodocumento,
    n.sigad_nombre,
    n.sigad_apellido1,
    n.sigad_apellido2,
    n.sigad_email,
    n.batch_id AS batch_detectado
FROM mdl_aux_sigad_matriculas n
LEFT JOIN mdl_aux_sigad_matriculas a 
    ON n.sigad_idalumno = a.sigad_idalumno 
    AND a.batch_id = :batch_anterior
WHERE n.batch_id = :batch_nuevo
  AND a.sigad_idalumno IS NULL;


-- -----------------------------------------------------------------------------
-- 4.2 ALUMNOS ELIMINADOS: Están en batch_anterior pero NO en batch_nuevo
-- -----------------------------------------------------------------------------
-- Resultado: Alumnos que deben darse de baja/suspenderse en Moodle
-- -----------------------------------------------------------------------------
SELECT DISTINCT 
    a.sigad_idalumno,
    a.sigad_documento,
    a.sigad_nombre,
    a.sigad_apellido1,
    a.sigad_email,
    a.batch_id AS batch_ultimo_registro
FROM mdl_aux_sigad_matriculas a
LEFT JOIN mdl_aux_sigad_matriculas n 
    ON a.sigad_idalumno = n.sigad_idalumno 
    AND n.batch_id = :batch_nuevo
WHERE a.batch_id = :batch_anterior
  AND n.sigad_idalumno IS NULL;


-- -----------------------------------------------------------------------------
-- 4.3 CAMBIOS EN DATOS PERSONALES
-- -----------------------------------------------------------------------------
-- Compara datos personales de alumnos presentes en ambos batches
-- -----------------------------------------------------------------------------

-- Cambio de email
SELECT 
    n.sigad_idalumno,
    n.sigad_documento,
    n.sigad_nombre,
    n.sigad_apellido1,
    'email' AS campo_cambiado,
    a.sigad_email AS valor_anterior,
    n.sigad_email AS valor_nuevo,
    :batch_anterior AS batch_anterior,
    :batch_nuevo AS batch_nuevo
FROM mdl_aux_sigad_matriculas n
INNER JOIN mdl_aux_sigad_matriculas a 
    ON n.sigad_idalumno = a.sigad_idalumno 
    AND a.batch_id = :batch_anterior
WHERE n.batch_id = :batch_nuevo
  AND n.sigad_email <> a.sigad_email
GROUP BY n.sigad_idalumno, n.sigad_documento, n.sigad_nombre, n.sigad_apellido1,
         n.sigad_email, a.sigad_email;

-- Cambio de documento (DNI/NIE) - importante para el username de Moodle
SELECT 
    n.sigad_idalumno,
    n.sigad_documento AS documento_nuevo,
    a.sigad_documento AS documento_anterior,
    n.sigad_nombre,
    n.sigad_apellido1,
    'documento' AS campo_cambiado,
    :batch_anterior AS batch_anterior,
    :batch_nuevo AS batch_nuevo
FROM mdl_aux_sigad_matriculas n
INNER JOIN mdl_aux_sigad_matriculas a 
    ON n.sigad_idalumno = a.sigad_idalumno 
    AND a.batch_id = :batch_anterior
WHERE n.batch_id = :batch_nuevo
  AND n.sigad_documento <> a.sigad_documento
GROUP BY n.sigad_idalumno, n.sigad_documento, a.sigad_documento, 
         n.sigad_nombre, n.sigad_apellido1;

-- Cambio de nombre/apellidos
SELECT 
    n.sigad_idalumno,
    n.sigad_documento,
    n.sigad_nombre AS nombre_nuevo,
    a.sigad_nombre AS nombre_anterior,
    n.sigad_apellido1 AS apellido1_nuevo,
    a.sigad_apellido1 AS apellido1_anterior,
    n.sigad_apellido2 AS apellido2_nuevo,
    a.sigad_apellido2 AS apellido2_anterior,
    CASE 
        WHEN n.sigad_nombre <> a.sigad_nombre THEN 'nombre'
        WHEN n.sigad_apellido1 <> a.sigad_apellido1 THEN 'apellido1'
        WHEN COALESCE(n.sigad_apellido2, '') <> COALESCE(a.sigad_apellido2, '') THEN 'apellido2'
    END AS campo_cambiado,
    :batch_anterior AS batch_anterior,
    :batch_nuevo AS batch_nuevo
FROM mdl_aux_sigad_matriculas n
INNER JOIN mdl_aux_sigad_matriculas a 
    ON n.sigad_idalumno = a.sigad_idalumno 
    AND a.batch_id = :batch_anterior
WHERE n.batch_id = :batch_nuevo
  AND (
      n.sigad_nombre <> a.sigad_nombre
      OR n.sigad_apellido1 <> a.sigad_apellido1
      OR COALESCE(n.sigad_apellido2, '') <> COALESCE(a.sigad_apellido2, '')
  )
GROUP BY n.sigad_idalumno, n.sigad_documento, n.sigad_nombre, a.sigad_nombre,
         n.sigad_apellido1, a.sigad_apellido1, n.sigad_apellido2, a.sigad_apellido2;


-- -----------------------------------------------------------------------------
-- 4.4 CAMBIOS EN MATRICULACIONES (MÓDULOS)
-- -----------------------------------------------------------------------------

-- Módulos AGREGADOS (nueva matrícula en módulos)
-- Está en batch_nuevo pero NO en batch_anterior
SELECT 
    n.sigad_idalumno,
    n.sigad_documento,
    n.sigad_nombre,
    n.sigad_apellido1,
    n.sigad_codigocentro,
    n.sigad_centro,
    n.sigad_siglasciclo,
    n.sigad_idmateria,
    n.sigad_modulo,
    n.sigad_siglasmodulo,
    'MODULO_AGREGADO' AS tipo_cambio,
    :batch_anterior AS batch_anterior,
    :batch_nuevo AS batch_nuevo
FROM mdl_aux_sigad_matriculas n
LEFT JOIN mdl_aux_sigad_matriculas a 
    ON n.sigad_idalumno = a.sigad_idalumno 
    AND n.sigad_idmateria = a.sigad_idmateria
    AND a.batch_id = :batch_anterior
WHERE n.batch_id = :batch_nuevo
  AND a.sigad_idmateria IS NULL;


-- Módulos ELIMINADOS (baja de módulo)
-- Está en batch_anterior pero NO en batch_nuevo
SELECT 
    a.sigad_idalumno,
    a.sigad_documento,
    a.sigad_nombre,
    a.sigad_apellido1,
    a.sigad_codigocentro,
    a.sigad_centro,
    a.sigad_siglasciclo,
    a.sigad_idmateria,
    a.sigad_modulo,
    a.sigad_siglasmodulo,
    'MODULO_ELIMINADO' AS tipo_cambio,
    :batch_anterior AS batch_anterior,
    :batch_nuevo AS batch_nuevo
FROM mdl_aux_sigad_matriculas a
LEFT JOIN mdl_aux_sigad_matriculas n 
    ON a.sigad_idalumno = n.sigad_idalumno 
    AND a.sigad_idmateria = n.sigad_idmateria
    AND n.batch_id = :batch_nuevo
WHERE a.batch_id = :batch_anterior
  AND n.sigad_idmateria IS NULL;


-- -----------------------------------------------------------------------------
-- 4.5 CAMBIOS DE CENTRO O CICLO (misma materia, diferente ubicación)
-- -----------------------------------------------------------------------------
-- Detecta si un alumno cambió de centro o ciclo manteniendo alguna materia
-- -----------------------------------------------------------------------------
SELECT 
    n.sigad_idalumno,
    n.sigad_documento,
    n.sigad_nombre,
    n.sigad_apellido1,
    n.sigad_idmateria,
    n.sigad_modulo,
    a.sigad_codigocentro AS centro_anterior,
    n.sigad_codigocentro AS centro_nuevo,
    a.sigad_siglasciclo AS ciclo_anterior,
    n.sigad_siglasciclo AS ciclo_nuevo,
    CASE 
        WHEN a.sigad_codigocentro <> n.sigad_codigocentro THEN 'CENTRO_CAMBIADO'
        WHEN a.sigad_siglasciclo <> n.sigad_siglasciclo THEN 'CICLO_CAMBIADO'
    END AS tipo_cambio,
    :batch_anterior AS batch_anterior,
    :batch_nuevo AS batch_nuevo
FROM mdl_aux_sigad_matriculas n
INNER JOIN mdl_aux_sigad_matriculas a 
    ON n.sigad_idalumno = a.sigad_idalumno 
    AND n.sigad_idmateria = a.sigad_idmateria
    AND a.batch_id = :batch_anterior
WHERE n.batch_id = :batch_nuevo
  AND (
      n.sigad_codigocentro <> a.sigad_codigocentro
      OR n.sigad_siglasciclo <> a.sigad_siglasciclo
  );


-- -----------------------------------------------------------------------------
-- 4.6 RESUMEN COMPLETO DE CAMBIOS (UNION DE TODOS)
-- -----------------------------------------------------------------------------
-- Query maestra que devuelve todos los cambios detectados
-- -----------------------------------------------------------------------------
SELECT * FROM (
    -- Alumnos nuevos
    SELECT 
        'NUEVO_ALUMNO' AS tipo_cambio,
        n.sigad_idalumno,
        n.sigad_documento,
        CONCAT(n.sigad_nombre, ' ', n.sigad_apellido1) AS nombre_completo,
        NULL AS detalle_cambio,
        NULL AS valor_anterior,
        n.sigad_email AS valor_nuevo,
        :batch_anterior AS batch_anterior,
        :batch_nuevo AS batch_nuevo
    FROM mdl_aux_sigad_matriculas n
    LEFT JOIN mdl_aux_sigad_matriculas a 
        ON n.sigad_idalumno = a.sigad_idalumno 
        AND a.batch_id = :batch_anterior
    WHERE n.batch_id = :batch_nuevo
      AND a.sigad_idalumno IS NULL
    
    UNION ALL
    
    -- Alumnos eliminados
    SELECT 
        'ALUMNO_ELIMINADO' AS tipo_cambio,
        a.sigad_idalumno,
        a.sigad_documento,
        CONCAT(a.sigad_nombre, ' ', a.sigad_apellido1) AS nombre_completo,
        NULL AS detalle_cambio,
        a.sigad_email AS valor_anterior,
        NULL AS valor_nuevo,
        :batch_anterior AS batch_anterior,
        :batch_nuevo AS batch_nuevo
    FROM mdl_aux_sigad_matriculas a
    LEFT JOIN mdl_aux_sigad_matriculas n 
        ON a.sigad_idalumno = n.sigad_idalumno 
        AND n.batch_id = :batch_nuevo
    WHERE a.batch_id = :batch_anterior
      AND n.sigad_idalumno IS NULL
    
    UNION ALL
    
    -- Cambio de email
    SELECT 
        'EMAIL_MODIFICADO' AS tipo_cambio,
        n.sigad_idalumno,
        n.sigad_documento,
        CONCAT(n.sigad_nombre, ' ', n.sigad_apellido1) AS nombre_completo,
        'Email actualizado' AS detalle_cambio,
        a.sigad_email AS valor_anterior,
        n.sigad_email AS valor_nuevo,
        :batch_anterior AS batch_anterior,
        :batch_nuevo AS batch_nuevo
    FROM mdl_aux_sigad_matriculas n
    INNER JOIN mdl_aux_sigad_matriculas a 
        ON n.sigad_idalumno = a.sigad_idalumno 
        AND a.batch_id = :batch_anterior
    WHERE n.batch_id = :batch_nuevo
      AND n.sigad_email <> a.sigad_email
    GROUP BY n.sigad_idalumno, n.sigad_documento, n.sigad_nombre, n.sigad_apellido1,
             n.sigad_email, a.sigad_email
    
    UNION ALL
    
    -- Cambio de documento
    SELECT 
        'DOCUMENTO_MODIFICADO' AS tipo_cambio,
        n.sigad_idalumno,
        n.sigad_documento,
        CONCAT(n.sigad_nombre, ' ', n.sigad_apellido1) AS nombre_completo,
        'DNI/NIE actualizado' AS detalle_cambio,
        a.sigad_documento AS valor_anterior,
        n.sigad_documento AS valor_nuevo,
        :batch_anterior AS batch_anterior,
        :batch_nuevo AS batch_nuevo
    FROM mdl_aux_sigad_matriculas n
    INNER JOIN mdl_aux_sigad_matriculas a 
        ON n.sigad_idalumno = a.sigad_idalumno 
        AND a.batch_id = :batch_anterior
    WHERE n.batch_id = :batch_nuevo
      AND n.sigad_documento <> a.sigad_documento
    GROUP BY n.sigad_idalumno, n.sigad_documento, a.sigad_documento, 
             n.sigad_nombre, n.sigad_apellido1
    
    UNION ALL
    
    -- Módulos agregados
    SELECT 
        'MODULO_AGREGADO' AS tipo_cambio,
        n.sigad_idalumno,
        n.sigad_documento,
        CONCAT(n.sigad_nombre, ' ', n.sigad_apellido1) AS nombre_completo,
        CONCAT(n.sigad_siglasciclo, ' - ', n.sigad_siglasmodulo) AS detalle_cambio,
        NULL AS valor_anterior,
        n.sigad_modulo AS valor_nuevo,
        :batch_anterior AS batch_anterior,
        :batch_nuevo AS batch_nuevo
    FROM mdl_aux_sigad_matriculas n
    LEFT JOIN mdl_aux_sigad_matriculas a 
        ON n.sigad_idalumno = a.sigad_idalumno 
        AND n.sigad_idmateria = a.sigad_idmateria
        AND a.batch_id = :batch_anterior
    WHERE n.batch_id = :batch_nuevo
      AND a.sigad_idmateria IS NULL
    
    UNION ALL
    
    -- Módulos eliminados
    SELECT 
        'MODULO_ELIMINADO' AS tipo_cambio,
        a.sigad_idalumno,
        a.sigad_documento,
        CONCAT(a.sigad_nombre, ' ', a.sigad_apellido1) AS nombre_completo,
        CONCAT(a.sigad_siglasciclo, ' - ', a.sigad_siglasmodulo) AS detalle_cambio,
        a.sigad_modulo AS valor_anterior,
        NULL AS valor_nuevo,
        :batch_anterior AS batch_anterior,
        :batch_nuevo AS batch_nuevo
    FROM mdl_aux_sigad_matriculas a
    LEFT JOIN mdl_aux_sigad_matriculas n 
        ON a.sigad_idalumno = n.sigad_idalumno 
        AND a.sigad_idmateria = n.sigad_idmateria
        AND n.batch_id = :batch_nuevo
    WHERE a.batch_id = :batch_anterior
      AND n.sigad_idmateria IS NULL
      
) AS resumen_cambios
ORDER BY tipo_cambio, sigad_apellido1, sigad_nombre;


-- =============================================================================
-- 5. PROCEDIMIENTO ALMACENADO: DETECTAR Y REGISTRAR CAMBIOS
-- =============================================================================
-- Automatiza la detección y registro en el histórico
-- =============================================================================

DELIMITER //

DROP PROCEDURE IF EXISTS sp_sigad_detectar_cambios//

CREATE PROCEDURE sp_sigad_detectar_cambios(
    IN p_batch_anterior VARCHAR(50),
    IN p_batch_nuevo VARCHAR(50)
)
BEGIN
    DECLARE v_fecha_actual TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    
    -- Insertar alumnos nuevos
    INSERT INTO mdl_aux_sigad_historico_cambios 
        (tipo_cambio, sigad_idalumno, sigad_documento, batch_anterior, batch_nuevo, observaciones)
    SELECT DISTINCT
        'NUEVO_ALUMNO',
        n.sigad_idalumno,
        n.sigad_documento,
        p_batch_anterior,
        p_batch_nuevo,
        CONCAT('Email: ', n.sigad_email)
    FROM mdl_aux_sigad_matriculas n
    LEFT JOIN mdl_aux_sigad_matriculas a 
        ON n.sigad_idalumno = a.sigad_idalumno 
        AND a.batch_id = p_batch_anterior
    WHERE n.batch_id = p_batch_nuevo
      AND a.sigad_idalumno IS NULL;
    
    -- Insertar alumnos eliminados
    INSERT INTO mdl_aux_sigad_historico_cambios 
        (tipo_cambio, sigad_idalumno, sigad_documento, batch_anterior, batch_nuevo, observaciones)
    SELECT DISTINCT
        'ALUMNO_ELIMINADO',
        a.sigad_idalumno,
        a.sigad_documento,
        p_batch_anterior,
        p_batch_nuevo,
        CONCAT('Email: ', a.sigad_email)
    FROM mdl_aux_sigad_matriculas a
    LEFT JOIN mdl_aux_sigad_matriculas n 
        ON a.sigad_idalumno = n.sigad_idalumno 
        AND n.batch_id = p_batch_nuevo
    WHERE a.batch_id = p_batch_anterior
      AND n.sigad_idalumno IS NULL;
    
    -- Insertar cambios de email
    INSERT INTO mdl_aux_sigad_historico_cambios 
        (tipo_cambio, sigad_idalumno, sigad_documento, campo_afectado, valor_anterior, valor_nuevo, batch_anterior, batch_nuevo)
    SELECT DISTINCT
        'EMAIL_MODIFICADO',
        n.sigad_idalumno,
        n.sigad_documento,
        'email',
        a.sigad_email,
        n.sigad_email,
        p_batch_anterior,
        p_batch_nuevo
    FROM mdl_aux_sigad_matriculas n
    INNER JOIN mdl_aux_sigad_matriculas a 
        ON n.sigad_idalumno = a.sigad_idalumno 
        AND a.batch_id = p_batch_anterior
    WHERE n.batch_id = p_batch_nuevo
      AND n.sigad_email <> a.sigad_email;
    
    -- Insertar cambios de documento
    INSERT INTO mdl_aux_sigad_historico_cambios 
        (tipo_cambio, sigad_idalumno, sigad_documento, campo_afectado, valor_anterior, valor_nuevo, batch_anterior, batch_nuevo)
    SELECT DISTINCT
        'DOCUMENTO_MODIFICADO',
        n.sigad_idalumno,
        n.sigad_documento,
        'documento',
        a.sigad_documento,
        n.sigad_documento,
        p_batch_anterior,
        p_batch_nuevo
    FROM mdl_aux_sigad_matriculas n
    INNER JOIN mdl_aux_sigad_matriculas a 
        ON n.sigad_idalumno = a.sigad_idalumno 
        AND a.batch_id = p_batch_anterior
    WHERE n.batch_id = p_batch_nuevo
      AND n.sigad_documento <> a.sigad_documento;
    
    -- Insertar módulos agregados
    INSERT INTO mdl_aux_sigad_historico_cambios 
        (tipo_cambio, sigad_idalumno, sigad_documento, campo_afectado, valor_nuevo, batch_anterior, batch_nuevo)
    SELECT 
        'MODULO_AGREGADO',
        n.sigad_idalumno,
        n.sigad_documento,
        CONCAT(n.sigad_siglasciclo, '.', n.sigad_siglasmodulo),
        CONCAT('idMateria:', n.sigad_idmateria, ' - ', n.sigad_modulo),
        p_batch_anterior,
        p_batch_nuevo
    FROM mdl_aux_sigad_matriculas n
    LEFT JOIN mdl_aux_sigad_matriculas a 
        ON n.sigad_idalumno = a.sigad_idalumno 
        AND n.sigad_idmateria = a.sigad_idmateria
        AND a.batch_id = p_batch_anterior
    WHERE n.batch_id = p_batch_nuevo
      AND a.sigad_idmateria IS NULL;
    
    -- Insertar módulos eliminados
    INSERT INTO mdl_aux_sigad_historico_cambios 
        (tipo_cambio, sigad_idalumno, sigad_documento, campo_afectado, valor_anterior, batch_anterior, batch_nuevo)
    SELECT 
        'MODULO_ELIMINADO',
        a.sigad_idalumno,
        a.sigad_documento,
        CONCAT(a.sigad_siglasciclo, '.', a.sigad_siglasmodulo),
        CONCAT('idMateria:', a.sigad_idmateria, ' - ', a.sigad_modulo),
        p_batch_anterior,
        p_batch_nuevo
    FROM mdl_aux_sigad_matriculas a
    LEFT JOIN mdl_aux_sigad_matriculas n 
        ON a.sigad_idalumno = n.sigad_idalumno 
        AND a.sigad_idmateria = n.sigad_idmateria
        AND n.batch_id = p_batch_nuevo
    WHERE a.batch_id = p_batch_anterior
      AND n.sigad_idmateria IS NULL;
    
    -- Devolver resumen
    SELECT 
        tipo_cambio,
        COUNT(*) AS cantidad
    FROM mdl_aux_sigad_historico_cambios
    WHERE batch_nuevo = p_batch_nuevo
      AND fecha_deteccion >= v_fecha_actual
    GROUP BY tipo_cambio;
    
END//

DELIMITER ;


-- =============================================================================
-- 6. EJEMPLO DE USO
-- =============================================================================

-- Paso 1: Insertar datos del JSON en la tabla (ejemplo con batch)
-- INSERT INTO mdl_aux_sigad_matriculas 
--     (sigad_idalumno, sigad_idtipodocumento, sigad_documento, sigad_nombre, 
--      sigad_apellido1, sigad_apellido2, sigad_email, sigad_codigocentro, 
--      sigad_centro, sigad_idficha, sigad_codigociclo, sigad_ciclo, sigad_siglasciclo,
--      sigad_idmateria, sigad_modulo, sigad_siglasmodulo, 
--      fecha_sincronizacion, hora_sincronizacion, batch_id)
-- VALUES 
--     (16839, 1, '78842153Q', 'Valeria', 'Torres', 'Medina', 
--      'valeria.torres.medina@ejemplo.com', '50009348', 'AVEMPACE',
--      22, '12242301', 'Educación Infantil...', 'SSC302',
--      18599, 'Itinerario personal...', 'IPPE1',
--      '2025-12-15', '11:42:28', '20251215_114228');

-- Paso 2: Comparar batches
-- CALL sp_sigad_detectar_cambios('20251214_100000', '20251215_114228');

-- Paso 3: Ver histórico de cambios
-- SELECT * FROM mdl_aux_sigad_historico_cambios 
-- WHERE batch_nuevo = '20251215_114228' 
-- ORDER BY tipo_cambio;
