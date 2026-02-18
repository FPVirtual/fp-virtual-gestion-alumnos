# Estimación Realista de Tiempos: 5000 Alumnos

## 📊 Escenario Definido

| Métrica | Valor |
|---------|-------|
| **Alumnos totales** | 5,000 |
| **Filas en tabla auxiliar** | ~25,000 (5 módulos/alumno promedio) |
| **Modificaciones de datos personales** | 350 |
| **Matrículas nuevas** | 2,700 |
| **Modificaciones de módulos/cursos** | 860 (bajas + cambios) |
| **Total operaciones moosh** | ~3,560 |

---

## ⏱️ Desglose Detallado por Fase

### FASE 1: DETECCIÓN DE CAMBIOS

| Operación | Detalle | Tiempo |
|-----------|---------|--------|
| `TRUNCATE` tabla auxiliar | Limpieza completa | **0.2s** |
| `INSERT` 25,000 filas | Batch insert con índices | **3-5s** |
| Query alumnos nuevos/baja | JOIN con índices | **0.5s** |
| Query cambios email | JOIN + comparación | **0.3s** |
| Query cambios nombre | JOIN + comparación | **0.3s** |
| Query matrículas necesarias | JOIN + LIKE (más lento) | **5-8s** |
| Query matrículas a dar baja | Anti-JOIN | **2-3s** |
| Overhead Python/BD | Conexiones, cursores | **1-2s** |
| **SUBTOTAL DETECCIÓN** | | **~12-19 segundos** |

✅ **Fase 1: ~15 segundos**

---

### FASE 2: APLICACIÓN DE DATOS PERSONALES (350 cambios)

**Método**: UPDATE SQL directo (sin moosh)

| Tipo | Cantidad | Tiempo unitario | Tiempo total |
|------|----------|-----------------|--------------|
| Cambios de email | ~200 | 50ms | 10s |
| Cambios de nombre | ~100 | 50ms | 5s |
| Cambios de documento | ~50 | 80ms (verificación extra) | 4s |
| Overhead transacciones | - | - | 2s |
| **SUBTOTAL DATOS PERSONALES** | **350** | | **~21 segundos** |

⚡ **Optimización**: Estos se ejecutan en una sola conexión BD, muy eficiente.

---

### FASE 3: MATRÍCULAS NUEVAS (2,700 matrículas)

**Método**: `moosh course-enrol` (docker exec + moosh + Moodle)

| Componente | Tiempo |
|------------|--------|
| Latencia `docker exec` | ~300-500ms |
| Inicialización moosh | ~200-300ms |
| Operación `course-enrol` | ~800-1200ms |
| **Tiempo por matrícula** | **~1.5 segundos** |

| Escenario | Cálculo | Tiempo Total |
|-----------|---------|--------------|
| **Secuencial (1 por 1)** | 2,700 × 1.5s | **~67 minutos** 😱 |
| **Batch optimizado (grupos de 50)** | 2,700 × 1.2s (mejor latencia) | **~54 minutos** |
| **Con paralelización (4 workers)** | 2,700 × 1.5s / 4 | **~17 minutos** |

🚨 **Problema**: 2,700 operaciones moosh son muchas.

---

### FASE 4: MODIFICACIONES DE MÓDULOS (860 cambios)

Asumimos: 860 cambios = ~430 bajas + ~430 nuevas matrículas (sustitución de módulos)

| Operación | Cantidad | Tiempo unitario | Tiempo total |
|-----------|----------|-----------------|--------------|
| `moosh course-unenrol` | 430 | ~1.0s | 7.2 min |
| `moosh course-enrol` (nuevas) | 430 | ~1.5s | 10.8 min |
| **Secuencial total** | | | **~18 minutos** |
| **Con paralelización (4 workers)** | | | **~4.5 minutos** |

---

## 📈 ESCENARIOS DE EJECUCIÓN

### Escenario 1: Secuencial (Sin Optimizaciones)

```
Fase 1 (Detección):     15 segundos
Fase 2 (Datos SQL):     21 segundos  
Fase 3 (2,700 matrículas moosh):  67 minutos
Fase 4 (860 cambios moosh):       18 minutos
─────────────────────────────────────────
TOTAL:                  ~85 minutos (1 hora 25 min)
```

❌ **Inaceptable para producción**

---

### Escenario 2: Con Paralelización (4 workers)

```python
# Ejecutar 4 operaciones moosh en paralelo
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(matricular, m) for m in matriculas]
```

```
Fase 1 (Detección):     15 segundos
Fase 2 (Datos SQL):     21 segundos
Fase 3 (2,700 matrículas / 4):    17 minutos
Fase 4 (860 cambios / 4):         4.5 minutos
─────────────────────────────────────────
TOTAL:                  ~22 minutos
```

⚠️ **Mejor, pero aún largo**

---

### Escenario 3: Optimizado con Agrupación por Usuario

**Estrategia**: Un alumno suele matricularse en varios módulos a la vez. 
En lugar de 2,700 llamadas individuales, usar scripts SQL para matriculaciones masivas.

```sql
-- Matricular usuario en múltiples cursos con un solo INSERT
INSERT INTO mdl_user_enrolments (enrolid, userid, timestart, timeend, status)
SELECT e.id, 1234, UNIX_TIMESTAMP(), 0, 0
FROM mdl_enrol e
WHERE e.courseid IN (101, 102, 103, 104, 105);
```

| Optimización | Impacto |
|--------------|---------|
| Agrupar por usuario (5 cursos promedio) | Reducir 2,700 → 540 operaciones |
| Usar SQL para matrículas masivas | De 1.5s a 0.2s por grupo |
| Batch de 50 operaciones | Reducir overhead docker |

```
Fase 1 (Detección):                     15 segundos
Fase 2 (Datos SQL):                     21 segundos
Fase 3 (Matrículas SQL agrupadas):      3 minutos
Fase 4 (Cambios SQL agrupados):         1 minuto
─────────────────────────────────────────────────
TOTAL:                                  ~5 minutos ✅
```

---

## 🚀 RECOMENDACIÓN: Implementación Optimizada

### Opción A: SQL Directo para Matrículas (Recomendada)

Para matrículas masivas, usar SQL en lugar de moosh:

```python
def matricular_masivo_sql(self, matriculas_por_usuario: Dict):
    """
    Matricula usuarios en múltiples cursos usando SQL directo.
    Mucho más rápido que moosh para operaciones masivas.
    """
    sql = """
        INSERT INTO mdl_user_enrolments (enrolid, userid, timestart, status)
        SELECT e.id, %s, UNIX_TIMESTAMP(), 0
        FROM mdl_enrol e
        WHERE e.courseid = %s AND e.status = 0
        ON DUPLICATE KEY UPDATE status = 0
    """
    # 100 matrículas en ~500ms vs 150s con moosh
```

**Ventajas**:
- 100x más rápido
- Transaccional
- Atómico

**Desventajas**:
- No dispara eventos de Moodle (logs, notificaciones)
- Requiere flush de caché después

---

### Opción B: Híbrido (Recomendado para Producción)

```
DATOS PERSONALES (350):
  → SQL directo (21 segundos)

MATRÍCULAS NUEVAS (2,700):
  → 90% SQL masivo (3 minutos)
  → 10% moosh individual para casos especiales (2 minutos)

CAMBIOS DE MÓDULOS (860):
  → SQL masivo para bajas (30 segundos)
  → SQL masivo para altas (30 segundos)

COHORTES / ESPECIALES:
  → moosh (2 minutos)
─────────────────────────────────
TOTAL: ~8-10 minutos
```

---

## 📊 Tabla Comparativa Final

| Escenario | Tiempo Estimado | Viabilidad |
|-----------|-----------------|------------|
| **Todo secuencial con moosh** | ~85 minutos | ❌ No usable |
| **Paralelización 4 workers** | ~22 minutos | ⚠️ Aceptable para ocasional |
| **SQL híbrido optimizado** | **~8-10 minutos** | ✅ Recomendado |
| **SQL completo (sin moosh)** | ~5 minutos | ⚠️ Riesgo: sin eventos Moodle |

---

## 🎯 Implementación Propuesta para tu Caso

### Código Optimizado

```python
class AplicadorCambiosOptimizado(AplicadorCambiosSigad):
    
    def aplicar_matriculas_masivo_sql(self, matriculas: List[Dict]):
        """Matricula en lote usando SQL (100x más rápido)."""
        # Agrupar por curso para eficiencia
        por_curso = defaultdict(list)
        for m in matriculas:
            courseid = self.mapeo_cursos.get(m['sigad_siglasmodulo'])
            if courseid:
                por_curso[courseid].append(m['moodle_userid'])
        
        # Insert masivo por curso
        for courseid, userids in por_curso.items():
            self._matricular_en_curso_sql(courseid, userids)
    
    def _matricular_en_curso_sql(self, courseid: int, userids: List[int]):
        """SQL directo para múltiples usuarios en un curso."""
        sql = """
            INSERT INTO mdl_user_enrolments (enrolid, userid, timestart, status)
            SELECT e.id, %s, UNIX_TIMESTAMP(), 0
            FROM mdl_enrol e
            WHERE e.courseid = %s AND e.enrol = 'manual' AND e.status = 0
            ON DUPLICATE KEY UPDATE status = 0, timestart = UNIX_TIMESTAMP()
        """
        with self.connection.cursor() as cursor:
            for userid in userids:
                cursor.execute(sql, (userid, courseid))
            self.connection.commit()
```

---

## ⏰ Estimación Final para tu Escenario

```
5000 alumnos
├─ 350 modificaciones datos personales    → 21 segundos (SQL)
├─ 2700 matrículas nuevas                 → 3 minutos (SQL masivo)
├─ 860 modificaciones módulos             → 1 minuto (SQL masivo)
├─ Detección de cambios                   → 15 segundos
└─ Overhead y logging                     → 30 segundos
────────────────────────────────────────────────────
TOTAL: ~5 minutos (con optimización SQL)
TOTAL: ~85 minutos (sin optimización, moosh puro)
```

### Recomendación:

1. **Para producción diaria**: Implementar versión SQL masiva (**~5 min**)
2. **Para auditoría/migración**: Usar moosh con paralelización (**~20 min**)
3. **Para pruebas**: Dry-run con SQL (**~15 seg** solo detección)

---

## ⚠️ Consideraciones de Seguridad

Si usas SQL directo en lugar de moosh:

1. **Flush de caché obligatorio** después:
   ```bash
   moosh cache-clear
   ```

2. **Verificación post-ejecución**:
   ```sql
   -- Contar matrículas creadas
   SELECT COUNT(*) FROM mdl_user_enrolments 
   WHERE timestart > UNIX_TIMESTAMP() - 3600;
   ```

3. **Backup antes de ejecución masiva**:
   ```bash
   mysqldump -u root -p mdl_user_enrolments > backup_enrolments.sql
   ```
