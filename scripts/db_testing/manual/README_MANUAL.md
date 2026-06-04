# Guía Manual: Testing con Datos Reales

> Flujo 100% manual para extraer, crear casos y verificar en BD

---

## 🎯 Flujo de Trabajo

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  1. EXTRAER     │────▶│  2. CREAR CSV   │────▶│  3. CONVERTIR   │
│  datos de BD    │     │  con 7 casos    │     │  CSV → JSON     │
│  (copiar/pegar) │     │  (editar a mano)│     │  (script)       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  6. VERIFICAR   │◀────│  5. MODIFICAR   │◀────│  4. CARGAR EN   │
│  resultados     │     │  BD (manual)    │     │  TABLA AUX      │
│  en DBeaver     │     │  con SQL        │     │  (DBeaver)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## 📋 Paso 1: Extraer Datos de BD

### 1.1 Conectar DBeaver
- Host: `192.168.1.110`
- BD: `www_fpvirtualaragon_es` (o tu backup)

### 1.2 Ejecutar query de selección
Abrir: `01_extraer_datos_a_mano.sql`

Ejecutar **QUERY 1**:
```sql
SELECT 
    u.id as moodle_userid,
    u.username as documento_actual,
    ...
```

### 1.3 Copiar resultados
- Seleccionar todos los resultados
- Click derecho → **Copy** (o Ctrl+C)
- Pegar en Excel o editor

### 1.4 Guardar como CSV
- Guardar como: `mis_datos_base.csv`

---

## 📋 Paso 2: Crear CSV con 7 Casos

### 2.1 Usar plantilla
Abrir: `02_plantilla_casos_test.csv`

### 2.2 Completar con tus datos
Copiar datos de `mis_datos_base.csv` y modificar según cada caso:

| Caso | Qué modificar | Ejemplo |
|------|---------------|---------|
| 1 - Nuevo | Documento inventado | `TEST99999X` |
| 2 - Reactivar | `esta_suspendido = 1` | `1` |
| 3 - Email | Email diferente | `nuevo@email.com` |
| 4 - Nombre | Nombre distinto | `María` → `María Elena` |
| 5 - NIE→DNI | `documento_moodle` = NIE | `X1234567L` |
| 6 - +Cursos | Más cursos en SIGAD | `PROG,BD,LM,ED` |
| 7 - -Cursos | Menos cursos en SIGAD | `PROG` |

### 2.3 Guardar CSV final
- Nombre: `mis_casos_test.csv`

---

## 📋 Paso 3: Convertir CSV a JSON

### 3.1 Ejecutar script
```bash
cd scripts/db_testing/manual

python csv_a_json.py mis_casos_test.csv \
    --output ../../../tests/data/mis_casos_test.json
```

### 3.2 Verificar JSON generado
```bash
cat tests/data/mis_casos_test.json | head -50
```

---

## 📋 Paso 4: Cargar en Tabla Auxiliar (DBeaver)

### 4.1 Crear tabla auxiliar
Ejecutar: `01_esquema_tabla_auxiliar.sql` (de carpeta anterior)

### 4.2 Insertar datos manualmente
Usar query de `03_cargar_datos_desde_sigad.sql` o:

```sql
INSERT INTO sigad_alumnos_aux 
(sigad_idalumno, sigad_documento, sigad_nombre, ...)
VALUES
(90001, '12345678A', 'Ana', ...),
(90002, '23456789B', 'Carlos', ...),
...;
```

O usar import CSV de DBeaver:
- Click derecho en tabla → Import Data → CSV
- Seleccionar `mis_casos_test.csv`

---

## 📋 Paso 5: Ejecutar Queries de Verificación

### 5.1 Abrir script de verificación
`03_queries_verificacion_manual.sql`

### 5.2 Configurar casos
Modificar la sección "PASO 2: Insertar tus casos" con tus documentos

### 5.3 Ejecutar verificaciones
Ejecutar cada query y verificar:

| Query | Qué verifica |
|-------|--------------|
| VERIFICACIÓN 1 | Si existe en Moodle |
| VERIFICACIÓN 2 | Comparación de emails |
| VERIFICACIÓN 3 | Comparación de nombres |
| VERIFICACIÓN 4 | Matrículas actuales |
| VERIFICACIÓN 5 | **Resumen de acciones** |

---

## 📋 Paso 6: Modificar BD (Opcional y con Cuidado)

### 6.1 Preparar entorno seguro
```sql
SET autocommit = 0;
START TRANSACTION;
```

### 6.2 Ejecutar modificaciones
Abrir: `04_queries_modificacion_manual.sql`

Descomentar y ejecutar las modificaciones que necesites:
- Suspender usuario (Caso 2)
- Cambiar email (Caso 3)
- Cambiar nombre (Caso 4)
- etc.

### 6.3 Verificar cambios
Ejecutar queries de verificación nuevamente

### 6.4 Decisión
```sql
-- Si todo está bien:
COMMIT;

-- Si algo falló o es prueba:
ROLLBACK;
```

---

## 📁 Archivos de esta Carpeta

| Archivo | Uso |
|---------|-----|
| `01_extraer_datos_a_mano.sql` | Queries para copiar datos desde BD |
| `02_plantilla_casos_test.csv` | Plantilla CSV con estructura |
| `csv_a_json.py` | Script para convertir CSV a JSON |
| `03_queries_verificacion_manual.sql` | Verificar casos sin modificar BD |
| `04_queries_modificacion_manual.sql` | Modificar BD (⚠️ con cuidado) |
| `README_MANUAL.md` | Esta guía |

---

## 💡 Tips

### Ver transacción activa
```sql
SELECT @@autocommit;
-- 0 = En transacción (puedes hacer ROLLBACK)
-- 1 = Autocommit activo (cada query es permanente)
```

### Ver últimos cambios
```sql
SELECT username, FROM_UNIXTIME(timemodified) 
FROM mdl_user 
ORDER BY timemodified DESC 
LIMIT 10;
```

### Backup rápido de usuario antes de modificar
```sql
-- Crear tabla de backup temporal
CREATE TABLE tmp_backup_user AS
SELECT * FROM mdl_user WHERE username = '23456789b';

-- Si necesitas restaurar:
-- UPDATE mdl_user 
-- SET (copiar campos desde tmp_backup_user)
-- WHERE id = (SELECT id FROM tmp_backup_user);
```

---

## ✅ Checklist por Caso

### Caso 1: Nuevo
- [ ] Documento NO existe en `mdl_user`
- [ ] Acción detectada: `CREAR_USUARIO`

### Caso 2: Reactivar
- [ ] Usuario existe con `suspended = 1`
- [ ] Acción detectada: `REACTIVAR`

### Caso 3: Cambio Email
- [ ] Email en SIGAD ≠ Email en Moodle
- [ ] Acción detectada: `ACTUALIZAR_EMAIL`

### Caso 4: Cambio Nombre
- [ ] Nombre en SIGAD ≠ `firstname` en Moodle
- [ ] Acción detectada: `ACTUALIZAR_NOMBRE`

### Caso 5: NIE→DNI
- [ ] `username` en Moodle ≠ `documento` en SIGAD
- [ ] Acción detectada: `ACTUALIZAR_USERNAME`

### Caso 6: Nuevas Matrículas
- [ ] Más cursos en SIGAD que en Moodle
- [ ] Acción detectada: `MATRICULAR_NUEVOS`

### Caso 7: Baja Parcial
- [ ] Menos cursos en SIGAD que en Moodle
- [ ] Acción detectada: `DESMATRICULAR_PARCIAL`
