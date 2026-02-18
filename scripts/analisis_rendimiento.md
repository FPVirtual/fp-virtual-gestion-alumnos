# Análisis de Rendimiento: Sincronización SIGAD-Moodle

## 📊 Estimación de Tiempos para 5000 Alumnos

### Suposiciones Base
- **5000 alumnos** en SIGAD
- **Promedio de 5 módulos** por alumno (variará por ciclo)
- **Filas en tabla auxiliar**: ~25,000 registros
- **mdl_user** con ~10,000 usuarios (alumnos + profesores)
- **mdl_user_enrolments** con ~50,000 matrículas

---

## ⏱️ Tiempos Estimados por Operación

### 1. INSERT en Tabla Auxiliar (~25,000 filas)

```sql
-- INSERT batch de 25,000 filas con índices
```

| Escenario | Tiempo Estimado |
|-----------|-----------------|
| **Con TRUNCATE previo** | 2-5 segundos |
| **Con índices activos** | 3-8 segundos |
| **Sin índices + rebuild** | 1-3 segundos |

**Optimización**: Usar `INSERT IGNORE` o `REPLACE` si hay duplicados.

---

### 2. Queries de Comparación Principales

#### Query A: Alumnos Nuevos (LEFT JOIN)
```sql
SELECT s.sigad_idalumno, s.sigad_documento
FROM mdl_aux_sigad_matriculas s
LEFT JOIN v_moodle_alumnos m ON m.moodle_documento = LOWER(s.sigad_documento)
WHERE m.moodle_userid IS NULL
GROUP BY s.sigad_idalumno
```

| Operación | Complejidad | Tiempo Estimado |
|-----------|-------------|-----------------|
| **FULL TABLE SCAN** (sin índice) | O(n×m) | 5-15 segundos |
| **CON ÍNDICE** en documento | O(n log m) | **0.1-0.5 segundos** |

✅ **Nuestra implementación tiene índices**: `idx_documento` en tabla auxiliar + índice en `mdl_user.username`

---

#### Query B: Alumnos de Baja (Anti-JOIN)
```sql
SELECT m.moodle_userid, m.moodle_documento
FROM v_moodle_alumnos m
LEFT JOIN mdl_aux_sigad_matriculas s ON LOWER(s.sigad_documento) = m.moodle_documento
WHERE s.sigad_idalumno IS NULL AND m.moodle_suspended = 0
```

| Escenario | Tiempo Estimado |
|-----------|-----------------|
| **Con índices** | 0.2-1 segundo |
| **Con muchos usuarios** (>50k) | 1-3 segundos |

---

#### Query C: Cambios de Email (INNER JOIN)
```sql
SELECT s.sigad_idalumno, m.moodle_email, s.sigad_email
FROM mdl_aux_sigad_matriculas s
INNER JOIN v_moodle_alumnos m ON m.moodle_documento = LOWER(s.sigad_documento)
WHERE m.moodle_email <> s.sigad_email
```

| Escenario | Tiempo Estimado |
|-----------|-----------------|
| **Con índice en documento** | 0.1-0.3 segundos |
| **Comparando strings** | +0.1 segundos |

---

#### Query D: Matrículas Nuevas (JOIN Complejo)
```sql
SELECT s.sigad_idalumno, s.sigad_siglasmodulo
FROM mdl_aux_sigad_matriculas s
INNER JOIN v_moodle_alumnos ma ON ma.moodle_documento = LOWER(s.sigad_documento)
LEFT JOIN v_moodle_matriculas m ON m.moodle_userid = ma.moodle_userid 
    AND m.moodle_course_shortname LIKE CONCAT('%', s.sigad_siglasmodulo, '%')
WHERE m.moodle_enrol_status IS NULL
```

| Operación | Tiempo Estimado |
|-----------|-----------------|
| **JOIN + LIKE** (sin índice en curso) | 5-20 segundos |
| **JOIN + índice en shortname** | 2-5 segundos |
| **FULL SCAN** (peor caso) | 30+ segundos |

⚠️ **Este es el cuello de botella potencial** por el `LIKE '%sigla%'`

---

## 📈 TIEMPO TOTAL ESTIMADO

### Escenario Óptimo (Servidor BD dedicado, SSD, índices optimizados)

| Operación | Tiempo |
|-----------|--------|
| TRUNCATE tabla auxiliar | 0.1s |
| INSERT 25,000 filas | 2s |
| Alumnos nuevos | 0.2s |
| Alumnos baja | 0.3s |
| Reactivaciones | 0.2s |
| Cambios email | 0.2s |
| Cambios documento | 0.2s |
| Matrículas nuevas | 3s |
| Matrículas baja | 2s |
| **TOTAL** | **~8-10 segundos** |

### Escenario Realista (Servidor compartido, carga media)

| Operación | Tiempo |
|-----------|--------|
| TRUNCATE + INSERT | 5s |
| Todas las queries de comparación | 10-15s |
| Overhead de red/Python | 2-3s |
| **TOTAL** | **~15-25 segundos** |

### Escenario Pesimista (BD lenta, muchos datos, sin optimización)

| Operación | Tiempo |
|-----------|--------|
| Operaciones de tabla | 10s |
| Queries complejas | 30-60s |
| **TOTAL** | **~40-70 segundos** |

---

## 🚀 Optimizaciones Recomendadas

### 1. Índices Críticos (ya incluidos en el script SQL)

```sql
-- Ya creados en el script
CREATE INDEX idx_documento ON mdl_aux_sigad_matriculas(sigad_documento);
CREATE INDEX idx_alumno ON mdl_aux_sigad_matriculas(sigad_idalumno);

-- Verificar índice en mdl_user (debería existir)
SHOW INDEX FROM mdl_user WHERE Column_name = 'username';
```

### 2. Índice Adicional Recomendado en Moodle

```sql
-- Si no existe, crearlo para acelerar las búsquedas
CREATE INDEX idx_user_username_lower ON mdl_user((LOWER(username)));
-- o
CREATE INDEX idx_user_email ON mdl_user(email);
```

### 3. Optimización para Matrículas (El JOIN más costoso)

En lugar de `LIKE '%sigla%'`, considerar una **tabla de mapeo**:

```sql
-- Tabla de mapeo: sigla SIGAD -> courseid Moodle
CREATE TABLE mdl_aux_sigad_moodle_cursos (
    sigad_siglasmodulo VARCHAR(50) PRIMARY KEY,
    moodle_courseid INT NOT NULL,
    moodle_shortname VARCHAR(255)
);

-- Entonces el JOIN sería:
SELECT s.sigad_idalumno, c.moodle_courseid
FROM mdl_aux_sigad_matriculas s
JOIN mdl_aux_sigad_moodle_cursos c ON c.sigad_siglasmodulo = s.sigad_siglasmodulo
LEFT JOIN mdl_user_enrolments ue ON ue.userid = ...
WHERE ue.id IS NULL;
```

**Mejora**: De 5-20s a **0.5-1s**

### 4. Consultas en Paralelo (Python)

```python
import concurrent.futures

def detectar_cambios_paralelo(self):
    queries = {
        'alumnos_nuevos': query_nuevos,
        'alumnos_baja': query_baja,
        'cambios_email': query_email,
        # ...
    }
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        resultados = executor.ejecutar_queries(queries)
```

**Mejora**: Reduce tiempo total en 30-40%

### 5. Cache de Resultados (para comparaciones frecuentes)

```python
# Si se ejecuta varias veces al día, cachear resultados de Moodle
alumnos_moodle_cache = obtener_todos_alumnos_moodle()  # Solo una vez
# Comparar contra cache en lugar de BD
```

---

## 📊 Comparativa: Batch vs Individual

| Método | 100 alumnos | 1000 alumnos | 5000 alumnos | 10,000 alumnos |
|--------|-------------|--------------|--------------|----------------|
| **Proceso Individual** (1 por 1) | 5-10s | 60-120s | 5-10 min | 15-30 min |
| **Batch con SQL** (nuestro método) | 1-2s | 3-5s | **8-25s** | 20-45s |
| **Batch optimizado** | 0.5s | 2s | **5-10s** | 10-20s |

**Mejora**: ~95% más rápido que procesar uno por uno

---

## 🎯 Recomendaciones para Producción

### Para 5000 alumnos:

1. **Ejecutar en horario de baja carga** (madrugada)
2. **Usar transacciones** para consistencia
3. **Limitar el número de cambios por ejecución**:
   ```python
   MAX_CAMBIOS_POR_EJECUCION = 100  # Prevenir sobrecarga
   ```
4. **Logging detallado** para auditoría de tiempos
5. **Monitorear** con:
   ```sql
   SHOW PROCESSLIST;  -- Ver queries activas
   SHOW ENGINE INNODB STATUS;  -- Ver bloqueos
   ```

### Frecuencia Recomendada:

- **Sincronización completa**: 1-2 veces al día
- **Verificación rápida** (solo nuevos): Cada 2-4 horas
- **Sincronización en tiempo real**: No recomendado (sobrecarga BD)

---

## 🔍 Diagnóstico de Rendimiento

### Ver tiempo de ejecución de queries:

```sql
-- Activar profiling
SET profiling = 1;

-- Ejecutar query
SELECT ... FROM mdl_aux_sigad_matriculas ...

-- Ver tiempo
SHOW PROFILES;
```

### Ver plan de ejecución:

```sql
EXPLAIN SELECT s.sigad_idalumno, s.sigad_documento
FROM mdl_aux_sigad_matriculas s
LEFT JOIN mdl_user u ON LOWER(u.username) = LOWER(s.sigad_documento);

-- Debe decir "Using index" o "Range checked for each record"
-- Evitar "Using where; Using join buffer"
```

---

## ✅ Conclusión

Para **5000 alumnos** (~25,000 filas desnormalizadas):

| Configuración | Tiempo Estimado | Aceptable? |
|---------------|-----------------|------------|
| **Mínimo** (sin optimizar) | 40-70s | ⚠️ Lento |
| **Estándar** (con índices) | 15-25s | ✅ Sí |
| **Optimizado** (mapeo + índices) | **5-10s** | ✅ Excelente |

**Recomendación**: Con la configuración actual del script SQL, espera **10-20 segundos** para 5000 alumnos.
