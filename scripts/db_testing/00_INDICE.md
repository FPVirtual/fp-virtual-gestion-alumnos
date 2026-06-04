# Índice de Scripts para Testing con Base de Datos

> Scripts y guías para testear la sincronización SIGAD ↔ Moodle usando DBeaver

---

## 📁 Archivos Disponibles

### Scripts SQL Automáticos

| Orden | Archivo | Descripción | Cuándo usar |
|-------|---------|-------------|-------------|
| 1 | `01_esquema_tabla_auxiliar.sql` | Crea tabla `sigad_alumnos_aux` y vistas | **Primera vez** o recrear tabla |
| 2 | `02_queries_exploracion_moodle.sql` | Explorar datos existentes en Moodle | Antes de importar |
| 3 | `03_cargar_datos_desde_sigad.sql` | Cargar datos manualmente | Importación pequeña/testing |
| 4 | `04_queries_sincronizacion.sql` | Comparar SIGAD vs Moodle | Después de importar |
| 5 | `05_queries_actualizacion.sql` | Queries que modifican datos | **⚠️ Con precaución** |
| 6 | `06_verificar_estructura_moodle.sql` | Verificar tablas e índices | Si hay problemas de rendimiento |
| 7 | `07_extraer_casos_test.sql` | Extraer usuarios y crear casos de test | Para testing con datos reales |
| 8 | `08_preparar_bd_para_testing.sql` | Modificar BD temporalmente para tests | **⚠️ Solo en test/pre** |

### Carpeta `manual/` - Flujo 100% Manual

Para control total paso a paso (recomendado para aprendizaje):

| Archivo | Descripción |
|---------|-------------|
| `01_extraer_datos_a_mano.sql` | Queries para copiar/pegar resultados |
| `02_plantilla_casos_test.csv` | Plantilla con estructura de casos |
| `csv_a_json.py` | Convierte tu CSV a JSON formato SIGAD |
| `03_queries_verificacion_manual.sql` | Verifica casos sin modificar BD |
| `04_queries_modificacion_manual.sql` | Modifica BD con control total (⚠️) |
| `README_MANUAL.md` | Guía completa del flujo manual |

### Scripts Python

| Archivo | Descripción |
|---------|-------------|
| `importar_sigad_a_bd.py` | Importar JSON de SIGAD directamente a MySQL |
| `generar_json_test_desde_bd.py` | Generar JSON de test desde casos en BD |

### Documentación

| Archivo | Descripción |
|---------|-------------|
| `README_DBEAVER.md` | Guía completa de uso con DBeaver |
| `GUIA_CASOS_TEST.md` | Guía para crear casos de test específicos |
| `datos_prueba_ejemplo.csv` | CSV de ejemplo para importar |
| `test_casos_ejemplo.json` | JSON con 7 casos de test listos para usar |
| `00_INDICE.md` | Este archivo |

---

## 🚀 Flujo Rápido de Inicio

### Opción A: Usando DBeaver (recomendado para explorar)

```bash
# 1. Conectar DBeaver al backup de BD
#    Host: 192.168.1.110 (o tu servidor)
#    BD: www_fpvirtualaragon_es

# 2. En DBeaver, ejecutar en orden:
#    → 01_esquema_tabla_auxiliar.sql
#    → 02_queries_exploracion_moodle.sql

# 3. Preparar CSV con datos de SIGAD (ver datos_prueba_ejemplo.csv)

# 4. Importar CSV a tabla sigad_alumnos_aux
#    (Click derecho tabla → Importar datos)

# 5. Ejecutar 04_queries_sincronizacion.sql
```

### Opción B: Usando Script Python (más rápido)

```bash
# 1. Crear tabla auxiliar (una sola vez)
cd scripts/db_testing
mysql -u admin -p -h 192.168.1.110 www_fpvirtualaragon_es < 01_esquema_tabla_auxiliar.sql

# 2. Importar JSON de SIGAD
python importar_sigad_a_bd.py \
    --file /ruta/a/estudiantes_sigad.json \
    --batch "20250301_test"

# 3. Abrir DBeaver y ejecutar 04_queries_sincronizacion.sql
```

---

## 📋 Comandos Útiles

### Conectar por línea de comandos

```bash
# Conexión interactiva
mysql -u admin -p -h 192.168.1.110 www_fpvirtualaragon_es

# Ejecutar script SQL
mysql -u admin -p -h 192.168.1.110 www_fpvirtualaragon_es < 01_esquema_tabla_auxiliar.sql

# Exportar resultados a CSV
mysql -u admin -p -h 192.168.1.110 www_fpvirtualaragon_es -e "
  SELECT * FROM sigad_alumnos_aux LIMIT 10
" > resultados.csv
```

### Backup rápido antes de cambios

```bash
mysqldump -u admin -p -h 192.168.1.110 \
  www_fpvirtualaragon_es sigad_alumnos_aux \
  > backup_tabla_aux_$(date +%Y%m%d).sql
```

---

## 🎯 Casos de Uso

### "Quiero ver cómo está un alumno específico"

1. Abrir `02_queries_exploracion_moodle.sql` en DBeaver
2. Buscar sección "5. VISTA INTEGRADA"
3. Reemplazar `'12345678a'` por el DNI del alumno
4. Ejecutar

### "Quiero saber qué usuarios crearían"

1. Asegurar que `sigad_alumnos_aux` tiene datos
2. Ejecutar query de "PASO 1: CRUZAR DATOS" de `04_queries_sincronizacion.sql`
3. Ejecutar query "2.1 Alumnos NUEVOS"

### "Quiero probar con pocos datos primero"

1. Usar `datos_prueba_ejemplo.csv` (tiene 3 alumnos)
2. Importar a tabla auxiliar
3. Ejecutar queries de sincronización
4. Verificar resultados

---

## ⚠️ Checklist de Seguridad

Antes de ejecutar `05_queries_actualizacion.sql`:

- [ ] Estás en **preproducción** o has verificado 3 veces los datos
- [ ] Backup creado: `mysqldump ... > backup_$(date +%Y%m%d).sql`
- [ ] Ejecutaste primero los SELECTs para ver qué se modificaría
- [ ] Desactivaste autocommit en DBeaver
- [ ] Tienes el `ROLLBACK;` preparado por si algo falla
- [ ] No estás modificando usuarios con ID 1-33 (protegidos)

---

## 🐛 Solución de Problemas

### "Tabla no existe"
```sql
-- Ejecutar primero:
SOURCE 01_esquema_tabla_auxiliar.sql;
```

### "Datos no aparecen en vistas"
```sql
-- Ejecutar el cruce de datos:
UPDATE sigad_alumnos_aux aux
LEFT JOIN mdl_user u ON LOWER(u.username) = LOWER(aux.sigad_documento)
SET 
    aux.moodle_userid = u.id,
    aux.moodle_existe = (u.id IS NOT NULL AND u.deleted = 0);
```

### "Query muy lento"
```sql
-- Crear índices faltantes:
CREATE INDEX idx_user_username ON mdl_user(username);
CREATE INDEX idx_sigad_documento ON sigad_alumnos_aux(sigad_documento);
```

---

## 📊 Estructura de la Tabla Auxiliar

```
sigad_alumnos_aux
├── Datos SIGAD (origen)
│   ├── sigad_idalumno
│   ├── sigad_documento
│   ├── sigad_nombre, apellido1, apellido2
│   ├── sigad_email
│   ├── sigad_codigo_centro, nombre_centro
│   ├── sigad_codigo_ciclo, nombre_ciclo, siglas_ciclo
│   └── sigad_modulos (JSON)
│
├── Datos Moodle (referencia)
│   ├── moodle_userid
│   ├── moodle_username
│   ├── moodle_existe (boolean)
│   ├── moodle_suspended (boolean)
│   └── moodle_email_actual
│
└── Control de proceso
    ├── import_estado (PENDIENTE/PROCESADO/ERROR)
    ├── import_batch
    ├── import_fecha
    ├── fecha_procesamiento
    └── observaciones
```

---

## 💡 Tips para DBeaver

### Atajos útiles
- `Ctrl+Enter`: Ejecutar query actual
- `Ctrl+/`: Comentar/descomentar línea
- `Ctrl+E`: Formatear SQL
- `F4`: Ver detalles de tabla

### Configuraciones recomendadas
1. **Desactivar autocommit**: 
   - Botón "Auto" en toolbar → Desactivar
   - O ejecutar: `SET autocommit = 0;`

2. **Ver resultados en formato tabla**:
   - Click derecho en resultados → "Visualizar en formato tabla"

3. **Exportar resultados**:
   - Click derecho en resultados → "Exportar resultado"
   - Formato: CSV, JSON, etc.

---

## 📞 Soporte

Si encuentras problemas:
1. Verificar `README_DBEAVER.md` para más detalles
2. Revisar que los scripts SQL se ejecutaron en orden
3. Confirmar permisos de usuario MySQL
