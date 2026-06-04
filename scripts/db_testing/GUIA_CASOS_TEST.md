# Guía de Casos de Test para Sincronización

> Instrucciones para crear y probar casos de test con datos reales

---

## 🎯 Objetivo

Crear 7 casos de test representativos para validar la sincronización SIGAD ↔ Moodle:

1. **Nuevo alumno** - No existe en Moodle
2. **Reincorporación** - Estaba suspendido, vuelve
3. **Cambio de email** - Email diferente en SIGAD
4. **Cambio de nombre** - Nombre/apellidos modificados
5. **Cambio NIE→DNI** - Cambio de tipo de documento
6. **Nuevas matrículas** - Agregó cursos nuevos
7. **Baja parcial** - Quitó algunos cursos (no todos)

---

## 📁 Archivos Disponibles

| Archivo | Descripción |
|---------|-------------|
| `07_extraer_casos_test.sql` | Extrae usuarios reales y crea casos modificados |
| `08_preparar_bd_para_testing.sql` | Prepara BD modificando datos temporalmente |
| `generar_json_test_desde_bd.py` | Genera JSON de test desde casos en BD |
| `test_casos_ejemplo.json` | JSON de ejemplo listo para usar (sin BD) |

---

## 🚀 Opción A: Usar JSON de Ejemplo (Rápido)

Si no puedes/puedes modificar la BD ahora:

```bash
# Copiar JSON de ejemplo a carpeta de tests
cp tests/data/test_casos_ejemplo.json tests/data/test_casos_test.json

# Usar en código Python
from gestion_alumnos.models_v2 import Registro
import json

with open('tests/data/test_casos_test.json') as f:
    datos = json.load(f)
    
registro = Registro.model_validate(datos)

# Ver casos
for alumno in registro.alumnos:
    meta = alumno._meta_caso  # Información del caso
    print(f"Caso {meta['caso_id']}: {meta['descripcion']}")
```

---

## 🔧 Opción B: Extraer desde BD (Recomendado)

### Paso 1: Conectar DBeaver al backup
- Host: `192.168.1.110`
- BD: `www_fpvirtualaragon_es` (o tu backup)

### Paso 2: Seleccionar usuarios base
Ejecutar en DBeaver: `07_extraer_casos_test.sql`

Esto crea:
- `tmp_test_usuarios_base` - 10 usuarios reales
- `tmp_casos_test` - 7 casos modificados

### Paso 3: Ver casos creados
```sql
SELECT * FROM tmp_casos_test ORDER BY caso_id;
```

Verás algo como:
```
caso_id | descripcion                           | sigad_documento | ...
--------|---------------------------------------|-----------------|----
1       | NUEVO: No existe en Moodle            | TESTNEW12345    | ...
2       | REINCORPORACION: Estaba suspendido    | 23456789b       | ...
3       | CAMBIO_EMAIL: Email diferente         | 34567890c       | ...
...
```

### Paso 4: Generar JSON
```bash
cd scripts/db_testing

python generar_json_test_desde_bd.py \
    --env ../../.env.preproduccion \
    --output ../../tests/data/test_casos_reales.json
```

### Paso 5: Copiar a data/ para procesar
```bash
cp tests/data/test_casos_reales.json data/estudiantes_casos_test.json
```

---

## ⚡ Opción C: Preparar BD para Testing Controlado

### ⚠️ IMPORTANTE
- Solo en **preproducción** o **backup**
- Siempre dentro de **transacción** (autocommit OFF)
- Hacer **ROLLBACK** después de probar

### Pasos:

1. **Abrir transacción en DBeaver:**
```sql
SET autocommit = 0;
START TRANSACTION;
```

2. **Ejecutar:** `08_preparar_bd_para_testing.sql`

3. **Ver casos creados:**
```sql
SELECT * FROM sigad_alumnos_aux 
WHERE import_batch LIKE 'TEST_%';
```

4. **Ejecutar queries de sincronización:**
```sql
-- De 04_queries_sincronizacion.sql
UPDATE sigad_alumnos_aux ... -- (cruce de datos)
SELECT * FROM v_sigad_pendientes;
```

5. **Verificar detección de casos:**
   - Caso 1: Debe aparecer como "CREAR_USUARIO"
   - Caso 2: Debe aparecer como "REACTIVAR"
   - Caso 3: Debe aparecer como "ACTUALIZAR_EMAIL"
   - etc.

6. **Restaurar datos (IMPORTANTE):**
```sql
ROLLBACK;
```

7. **Verificar rollback:**
```sql
-- Los usuarios deben volver a su estado original
SELECT username, suspended, email, firstname 
FROM mdl_user 
WHERE id IN (SELECT user_id FROM tmp_usuarios_test_seleccionados);
```

---

## 📋 Ejemplo de Uso en Python

```python
from gestion_alumnos.core.container import get_container
from gestion_alumnos.models_v2 import Registro
import json

# Cargar casos de test
with open('tests/data/test_casos_ejemplo.json') as f:
    datos = json.load(f)

registro = Registro.model_validate(datos)

# Procesar cada caso
for alumno in registro.alumnos:
    meta = alumno._meta_caso
    print(f"\n{'='*60}")
    print(f"CASO {meta['caso_id']}: {meta['descripcion']}")
    print(f"Esperado: {meta['resultado_esperado']}")
    print(f"Documento: {alumno.documento}")
    print(f"Email: {alumno.email}")
    
    # Aquí iría la lógica de sincronización
    # ...
```

---

## ✅ Checklist de Validación

Para cada caso, verificar:

- [ ] **Caso 1 (Nuevo)**: Se detecta como `moodle_existe = FALSE`
- [ ] **Caso 2 (Reactivar)**: Se detecta como `suspended = TRUE`
- [ ] **Caso 3 (Email)**: Se detecta diferencia de email
- [ ] **Caso 4 (Nombre)**: Se detecta diferencia de nombre
- [ ] **Caso 5 (Documento)**: Se detecta cambio de username
- [ ] **Caso 6 (Nuevas matrículas)**: Se detectan cursos adicionales
- [ ] **Caso 7 (Baja parcial)**: Se detectan cursos faltantes

---

## 🐛 Solución de Problemas

### "Tabla tmp_casos_test no existe"
→ Ejecutar primero `07_extraer_casos_test.sql`

### "No hay datos en tmp_test_usuarios_base"
→ Verificar que hay usuarios con matrículas en mdl_user_enrolments

### "Caso 2 no tiene suspendidos"
→ El script automáticamente simula uno si no existe

### "No puedo hacer ROLLBACK"
→ Asegúrate de haber ejecutado `SET autocommit = 0` ANTES de las modificaciones

---

## 💡 Tips

### Ver usuarios modificados:
```sql
SELECT * FROM tmp_usuarios_test_seleccionados;
```

### Ver backup de originales:
```sql
SELECT * FROM tmp_backup_datos_originales;
```

### Comparar antes/después:
```sql
SELECT 
    b.caso_id,
    b.username_original,
    u.username as username_actual,
    b.email_original,
    u.email as email_actual
FROM tmp_backup_datos_originales b
JOIN mdl_user u ON u.id = b.user_id;
```

---

## 📊 Estructura del JSON Generado

```json
{
  "fecha": "03/03/2026",
  "hora": "14:30:00",
  "alumnos": [
    {
      "idAlumno": 99901,
      "documento": "12345678A",
      "nombre": "Ana",
      "apellido1": "García",
      ...
      "_meta_caso": {
        "caso_id": 1,
        "descripcion": "NUEVO: No existe en Moodle",
        "resultado_esperado": "CREAR_USUARIO",
        "notas": "..."
      }
    }
  ]
}
```

El campo `_meta_caso` contiene:
- `caso_id`: Número de caso (1-7)
- `descripcion`: Qué se está probando
- `resultado_esperado`: Qué acción debe tomar el sistema
- `moodle_*_original`: Datos originales en Moodle (para comparar)
- `notas`: Información adicional
