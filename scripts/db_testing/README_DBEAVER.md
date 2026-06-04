# Guía de Testing con DBeaver

> Instrucciones para testear la sincronización SIGAD ↔ Moodle usando datos reales de backup

---

## 📋 Requisitos Previos

1. **DBeaver** instalado
2. **Backup de la BD** de Moodle restaurado en un servidor accesible
3. **Datos de conexión**:
   - Host: `192.168.1.110` (o tu servidor)
   - Puerto: `3306`
   - Base de datos: `www_fpvirtualaragon_es` (o la que corresponda)
   - Usuario/contraseña: según tu `.env`

---

## 🔌 Conexión a la Base de Datos

### Paso 1: Crear nueva conexión
1. Abre DBeaver
2. Click en **Nueva Conexión** (icono de enchufe)
3. Selecciona **MySQL**
4. Configura:
   - **Host**: `192.168.1.110`
   - **Puerto**: `3306`
   - **Base de datos**: `www_fpvirtualaragon_es`
   - **Usuario**: `admin` (o el que tengas)
   - **Contraseña**: (la de tu .env)

### Paso 2: Probar conexión
Click en **Probar conexión** antes de guardar

---

## 📁 Archivos SQL Disponibles

| Archivo | Descripción | Uso |
|---------|-------------|-----|
| `01_esquema_tabla_auxiliar.sql` | Crea tabla `sigad_alumnos_aux` y vistas | **Ejecutar primero** |
| `02_queries_exploracion_moodle.sql` | Queries para explorar datos existentes | Consulta/análisis |
| `03_cargar_datos_desde_sigad.sql` | Cargar datos JSON/CSV a tabla auxiliar | Importación datos |
| `04_queries_sincronizacion.sql` | Comparar SIGAD vs Moodle | Análisis diferencias |
| `05_queries_actualizacion.sql` | Queries que modifican datos | **⚠️ Precaución** |

---

## 🚀 Flujo de Trabajo Recomendado

### FASE 1: Exploración (solo lectura)

```sql
-- 1. Abrir 02_queries_exploracion_moodle.sql
-- 2. Ejecutar sección "1. EXPLORAR USUARIOS"
--    → Ver total de usuarios, suspendidos, etc.

-- 3. Ejecutar sección "2. EXPLORAR COHORTES"
--    → Verificar que existe cohorte "alumnado"

-- 4. Buscar un usuario específico (reemplaza el DNI)
SELECT * FROM mdl_user WHERE username = '12345678a';
```

### FASE 2: Preparar tabla auxiliar

```sql
-- 1. Abrir 01_esquema_tabla_auxiliar.sql
-- 2. Ejecutar todo el script
-- 3. Verificar que se creó la tabla:
DESCRIBE sigad_alumnos_aux;
```

### FASE 3: Cargar datos de SIGAD

**Opción A: Manual (para tests)**
```sql
-- Abrir 03_cargar_datos_desde_sigad.sql
-- Ir a "MÉTODO 1: Carga manual"
-- Modificar el INSERT con datos reales de SIGAD
-- Ejecutar
```

**Opción B: Desde CSV**
1. Preparar CSV con columnas: `idAlumno,documento,nombre,apellido1,apellido2,email,...`
2. En DBeaver: Click derecho en `sigad_alumnos_aux` → **Importar datos**
3. Seleccionar CSV y mapear columnas

**Opción C: Desde JSON** (si tienes el JSON de SIGAD)
```sql
-- Usar el procedimiento almacenado en el script
CALL sp_cargar_sigad_json('{"alumnos": [...]}', 'BATCH_20250301');
```

### FASE 4: Análisis de diferencias

```sql
-- Abrir 04_queries_sincronizacion.sql

-- 1. Ejecutar "PASO 1: CRUZAR DATOS"
--    → Actualiza moodle_userid, moodle_existe, etc.

-- 2. Ejecutar "2.1 Alumnos NUEVOS"
--    → Lista de usuarios a crear

-- 3. Ejecutar "2.2 Alumnos a REACTIVAR"
--    → Usuarios suspendidos que vuelven

-- 4. Ejecutar "2.3 Alumnos con EMAIL DIFERENTE"
--    → Cambios de email detectados

-- 5. Ejecutar "PASO 4: RESUMEN EJECUTIVO"
--    → Vista general de todo el proceso
```

### FASE 5: Actualización (⚠️ con cuidado)

```sql
-- ⚠️ IMPORTANTE: Desactivar autocommit primero
SET autocommit = 0;
START TRANSACTION;

-- Abrir 05_queries_actualizacion.sql

-- 1. Ejecutar ACTUALIZACIÓN 1: Reactivar usuarios
--    (descomentar y ejecutar)

-- 2. Verificar resultados con las queries de verificación
SELECT * FROM mdl_user WHERE timemodified > UNIX_TIMESTAMP() - 3600;

-- 3. Si todo OK:
COMMIT;

-- 4. Si algo falló:
-- ROLLBACK;
```

---

## 🔍 Queries Útiles para Debugging

### Buscar usuario por DNI
```sql
SELECT 
    u.id, u.username, u.email, u.firstname, u.lastname,
    u.suspended, u.deleted,
    FROM_UNIXTIME(u.timecreated) as creado,
    FROM_UNIXTIME(u.lastlogin) as ultimo_acceso
FROM mdl_user u
WHERE u.username LIKE '%12345678%'
   OR u.email LIKE '%12345678%';
```

### Ver matrículas de un usuario
```sql
SELECT 
    c.shortname as curso,
    c.fullname as nombre_curso,
    e.enrol as metodo,
    CASE ue.status 
        WHEN 0 THEN 'Activa' 
        WHEN 1 THEN 'Suspendida' 
    END as estado
FROM mdl_user u
JOIN mdl_user_enrolments ue ON ue.userid = u.id
JOIN mdl_enrol e ON e.id = ue.enrolid
JOIN mdl_course c ON c.id = e.courseid
WHERE u.username = '12345678a';
```

### Ver cohortes de un usuario
```sql
SELECT 
    c.name as cohorte,
    c.idnumber,
    FROM_UNIXTIME(cm.timeadded) as fecha_matricula
FROM mdl_user u
JOIN mdl_cohort_members cm ON cm.userid = u.id
JOIN mdl_cohort c ON c.id = cm.cohortid
WHERE u.username = '12345678a';
```

---

## ⚠️ Precauciones Importantes

### Antes de modificar datos:

1. **Hacer backup**
```bash
# En servidor MySQL
mysqldump -u admin -p www_fpvirtualaragon_es > backup_$(date +%Y%m%d).sql
```

2. **Verificar en transacción**
```sql
START TRANSACTION;
-- tus queries
-- verificar resultados
ROLLBACK;  -- o COMMIT si está todo OK
```

3. **Probar en preproducción primero**

### Usuarios protegidos (NO TOCAR):
- IDs: 1-33, 3725, 3729, 3730, 7152, 7490, 7491, 11720, 12270, 12272
- Admin, guest, y cuentas de sistema

---

## 📊 Interpretación de Resultados

### Estados de matrícula (`mdl_user_enrolments.status`):
| Valor | Significado |
|-------|-------------|
| 0 | Activa |
| 1 | Suspendida |

### Estados de usuario (`mdl_user`):
| Campo | Valor | Significado |
|-------|-------|-------------|
| deleted | 0 | Usuario activo |
| deleted | 1 | Eliminado (soft delete) |
| suspended | 0 | Activo |
| suspended | 1 | Suspendido (no puede login) |

---

## 🆘 Solución de Problemas

### Error: "Access denied"
→ Verificar credenciales en `.env`

### Error: "Table doesn't exist"
→ Ejecutar primero `01_esquema_tabla_auxiliar.sql`

### No aparecen datos en vistas
→ Verificar que se ejecutó el cruce de datos (PASO 1)

### Query tarda mucho
→ Agregar índices si no existen:
```sql
CREATE INDEX idx_user_username ON mdl_user(username);
CREATE INDEX idx_user_email ON mdl_user(email);
```

---

## ✅ Checklist Final

Antes de ejecutar en producción:

- [ ] Backup creado y verificado
- [ ] Tests ejecutados en preproducción
- [ ] Queries revisadas por otro desarrollador
- [ ] Lista de usuarios protegidos verificada
- [ ] Horario de baja afluencia confirmado
- [ ] Plan de rollback preparado
