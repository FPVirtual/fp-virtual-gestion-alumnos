-- =====================================================
-- CARGAR DATOS DESDE JSON DE SIGAD A TABLA AUXILIAR
-- =====================================================
-- Este script asume que tienes los datos de SIGAD en formato JSON
-- y los quieres cargar en la tabla auxiliar para procesarlos

-- =====================================================
-- MÉTODO 1: Carga manual registro por registro
-- =====================================================
-- Útil para tests con pocos alumnos

-- Ejemplo de inserción manual
INSERT INTO sigad_alumnos_aux (
    sigad_idalumno,
    sigad_documento,
    sigad_nombre,
    sigad_apellido1,
    sigad_apellido2,
    sigad_email,
    sigad_codigo_centro,
    sigad_nombre_centro,
    sigad_codigo_ciclo,
    sigad_nombre_ciclo,
    sigad_siglas_ciclo,
    sigad_modulos,
    import_batch
) VALUES (
    16839,
    '78842153Q',
    'Valeria',
    'Torres',
    'Medina',
    'valeria.torres.medina@ejemplo.com',
    '50009348',
    'AVEMPACE',
    '12242301',
    'Educación Infantil (Formación Profesional)',
    'SSC302',
    '[{"idMateria": 18599, "modulo": "Itinerario personal", "siglasModulo": "IPPE1"}]',
    'TEST_20250301'
);


-- =====================================================
-- MÉTODO 2: Carga masiva desde archivo CSV
-- =====================================================
-- Prepara primero un CSV con las columnas necesarias

-- Paso 1: Crear tabla temporal para carga
DROP TABLE IF EXISTS tmp_sigad_import;

CREATE TABLE tmp_sigad_import (
    idAlumno INT,
    documento VARCHAR(20),
    nombre VARCHAR(100),
    apellido1 VARCHAR(100),
    apellido2 VARCHAR(100),
    email VARCHAR(200),
    codigoCentro VARCHAR(20),
    centro VARCHAR(200),
    codigoCiclo VARCHAR(20),
    ciclo VARCHAR(200),
    siglasCiclo VARCHAR(20),
    modulos TEXT  -- JSON como string
);

-- Paso 2: Cargar CSV (ajusta la ruta según tu sistema)
-- En DBeaver: Click derecho en tabla → Import Data → CSV
-- O usa LOAD DATA si tienes acceso al servidor de BD:

/*
LOAD DATA LOCAL INFILE '/ruta/a/estudiantes_sigad.csv'
INTO TABLE tmp_sigad_import
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;
*/

-- Paso 3: Insertar desde tabla temporal a tabla auxiliar
INSERT INTO sigad_alumnos_aux (
    sigad_idalumno,
    sigad_documento,
    sigad_nombre,
    sigad_apellido1,
    sigad_apellido2,
    sigad_email,
    sigad_codigo_centro,
    sigad_nombre_centro,
    sigad_codigo_ciclo,
    sigad_nombre_ciclo,
    sigad_siglas_ciclo,
    sigad_modulos,
    import_batch
)
SELECT 
    idAlumno,
    documento,
    nombre,
    apellido1,
    apellido2,
    email,
    codigoCentro,
    centro,
    codigoCiclo,
    ciclo,
    siglasCiclo,
    modulos,  -- Asegúrate que sea JSON válido
    'IMPORT_CSV_' || DATE_FORMAT(NOW(), '%Y%m%d')
FROM tmp_sigad_import;

-- Limpiar tabla temporal
DROP TABLE IF EXISTS tmp_sigad_import;


-- =====================================================
-- MÉTODO 3: Procedimiento almacenado para procesar JSON
-- =====================================================
-- Si tienes los datos de SIGAD como JSON completo

DELIMITER //

CREATE PROCEDURE IF NOT EXISTS sp_cargar_sigad_json(
    IN json_data TEXT,
    IN batch_id VARCHAR(50)
)
BEGIN
    DECLARE i INT DEFAULT 0;
    DECLARE num_alumnos INT;
    
    -- Contar alumnos en JSON
    SET num_alumnos = JSON_LENGTH(JSON_EXTRACT(json_data, '$.alumnos'));
    
    -- Loop para insertar cada alumno
    WHILE i < num_alumnos DO
        SET @alumno_path = CONCAT('$.alumnos[', i, ']');
        
        INSERT INTO sigad_alumnos_aux (
            sigad_idalumno,
            sigad_documento,
            sigad_nombre,
            sigad_apellido1,
            sigad_apellido2,
            sigad_email,
            sigad_codigo_centro,
            sigad_nombre_centro,
            sigad_codigo_ciclo,
            sigad_nombre_ciclo,
            sigad_siglas_ciclo,
            sigad_modulos,
            import_batch
        )
        SELECT 
            JSON_UNQUOTE(JSON_EXTRACT(json_data, CONCAT(@alumno_path, '.idAlumno'))),
            JSON_UNQUOTE(JSON_EXTRACT(json_data, CONCAT(@alumno_path, '.documento'))),
            JSON_UNQUOTE(JSON_EXTRACT(json_data, CONCAT(@alumno_path, '.nombre'))),
            JSON_UNQUOTE(JSON_EXTRACT(json_data, CONCAT(@alumno_path, '.apellido1'))),
            JSON_UNQUOTE(JSON_EXTRACT(json_data, CONCAT(@alumno_path, '.apellido2'))),
            JSON_UNQUOTE(JSON_EXTRACT(json_data, CONCAT(@alumno_path, '.email'))),
            -- Centro (primer centro del array)
            JSON_UNQUOTE(JSON_EXTRACT(json_data, CONCAT(@alumno_path, '.centros[0].codigoCentro'))),
            JSON_UNQUOTE(JSON_EXTRACT(json_data, CONCAT(@alumno_path, '.centros[0].centro'))),
            -- Ciclo (primer ciclo del primer centro)
            JSON_UNQUOTE(JSON_EXTRACT(json_data, CONCAT(@alumno_path, '.centros[0].ciclos[0].codigoCiclo'))),
            JSON_UNQUOTE(JSON_EXTRACT(json_data, CONCAT(@alumno_path, '.centros[0].ciclos[0].ciclo'))),
            JSON_UNQUOTE(JSON_EXTRACT(json_data, CONCAT(@alumno_path, '.centros[0].ciclos[0].siglasCiclo'))),
            -- Módulos como JSON
            JSON_EXTRACT(json_data, CONCAT(@alumno_path, '.centros[0].ciclos[0].modulos')),
            batch_id;
        
        SET i = i + 1;
    END WHILE;
    
    SELECT CONCAT('Insertados ', num_alumnos, ' alumnos') as resultado;
END //

DELIMITER ;

-- Ejemplo de uso del procedimiento:
-- CALL sp_cargar_sigad_json('{"alumnos": [...]}', 'BATCH_20250301');
