# Sincronización SIGAD con Moodle (Tablas Reales)

Este módulo compara los datos de alumnos desde **SIGAD** (tabla auxiliar) contra las **tablas reales de Moodle** (`mdl_user`, `mdl_user_enrolments`, etc.) para detectar cambios pendientes.

## 🎯 Arquitectura

```
┌─────────────────────────┐         ┌──────────────────────────────┐
│  SIGAD (JSON/API)       │         │  MOODLE (Tablas reales)      │
├─────────────────────────┤         ├──────────────────────────────┤
│  idAlumno, DNI, etc.    │         │  mdl_user                    │
└──────────┬──────────────┘         │  mdl_user_enrolments         │
           │ INSERT                  │  mdl_course                  │
           ▼                         └──────────────┬───────────────┘
┌─────────────────────────┐                        │
│  TABLA AUXILIAR         │         ┌──────────────▼───────────────┐
│  mdl_aux_sigad_...      │◄────────┤  VISTAS TRANSFORMADAS        │
├─────────────────────────┤  JOIN   │  v_moodle_alumnos            │
│  sigad_documento        │         │  v_moodle_matriculas         │
│  sigad_email            │         └──────────────────────────────┘
│  sigad_siglasmodulo     │                        │
└─────────────────────────┘                        ▼
           │                         ┌──────────────────────────────┐
           ▼                         │  DETECCIÓN DE CAMBIOS        │
┌─────────────────────────┐          │  (Queries SQL)               │
│  APLICAR CAMBIOS        │          └──────────────┬───────────────┘
├─────────────────────────┤                         │
│ 📧 Datos personales:    │◄────────────────────────┘
│    UPDATE SQL (rápido)  │
├─────────────────────────┤
│ 👤 Altas/Bajas:         │
│    moosh user-create    │
│    moosh user-mod       │
├─────────────────────────┤
│ 📚 Matrículas:          │
│    moosh course-enrol   │
│    moosh course-unenrol │
└─────────────────────────┘
```

## 📁 Archivos

| Archivo | Descripción |
|---------|-------------|
| `crear_tabla_auxiliar_sigad_v2.sql` | Script SQL con tabla auxiliar y vistas |
| `sigad_db_sync.py` | Detección de cambios (comparación SIGAD vs Moodle) |
| `sigad_aplicar_cambios.py` | **NUEVO** - Aplicación de cambios (SQL + moosh) |
| `ejemplo_aplicar_cambios.py` | Ejemplo completo de detección + aplicación |

---

## 🚀 Instalación Rápida

```bash
# 1. Crear tablas y vistas
mysql -u $DB_USER -p$DB_PASS -h $DB_HOST $DB_NAME < scripts/crear_tabla_auxiliar_sigad_v2.sql

# 2. Instalar dependencias
poetry add pymysql

# 3. Configurar variables de entorno (.env)
DB_HOST=192.168.1.110
DB_USER=admin
DB_PASS=tu_password
DB_NAME=www_fpvirtualaragon_es
MOODLE_CONTAINER=wwwfpvirtualaragones-moodle-1
```

---

## 📖 Uso Completo (Detectar + Aplicar)

### Ejemplo 1: Flujo Completo

```python
from gestion_alumnos.utils.sigad_db_sync import sincronizar_y_detectar
from gestion_alumnos.utils.sigad_aplicar_cambios import aplicar_cambios_sigad

# 1. OBTENER datos de SIGAD (desde API)
registro_sigad = {
    "fecha": "18/02/2026",
    "hora": "15:30:00",
    "alumnos": [...]  # Lista de alumnos desde API
}

# 2. DETECTAR cambios (inserta en tabla auxiliar y compara)
filas, cambios = sincronizar_y_detectar(registro_sigad)

# 3. APLICAR cambios
#    - Datos personales: UPDATE SQL (rápido)
#    - Matrículas/Usuarios: moosh (robusto)
resultado = aplicar_cambios_sigad(
    cambios=cambios,
    moodle_container="wwwfpvirtualaragones-moodle-1",
    mapeo_cursos={'IPPE1': 123, 'PA': 124},  # Opcional
    dry_run=False  # False = aplicar de verdad
)

# Ver resultados
print(f"Exitosos: {resultado['exitosos']}")
print(f"Fallidos: {resultado['fallidos']}")
print(f"Estadísticas: {resultado['estadisticas']}")
```

### Ejemplo 2: Simulación (Dry-Run)

```python
# Solo simular, no aplicar cambios reales
resultado = aplicar_cambios_sigad(
    cambios=cambios,
    moodle_container="wwwfpvirtualaragones-moodle-1",
    dry_run=True  # True = solo simular
)

# Revisar qué se haría sin hacerlo
for res in resultado['resultados']:
    print(f"{res.tipo}: {res.documento} - {res.mensaje}")
```

---

## 🔧 Métodos de Aplicación de Cambios

### Datos Personales (SQL Directo - Rápido)

```python
from gestion_alumnos.utils.sigad_aplicar_cambios import AplicadorCambiosSigad

app = AplicadorCambiosSigad("wwwfpvirtualaragones-moodle-1")

# Actualizar email (UPDATE mdl_user)
app.actualizar_email(
    userid=1234,
    email_nuevo="nuevo@email.com",
    email_anterior="viejo@email.com"
)

# Actualizar nombre (UPDATE mdl_user)
app.actualizar_nombre_completo(
    userid=1234,
    nombre="NuevoNombre",
    apellido1="NuevoApellido",
    apellido2="SegundoApellido"
)

# Actualizar documento/username (UPDATE mdl_user)
# ⚠️ Cuidado: cambia el login del usuario
app.actualizar_documento_username(
    userid=1234,
    documento_nuevo="12345678A",
    documento_anterior="X1234567Y"
)
```

**Velocidad**: ~50-100 ms por operación

### Gestión de Usuarios (Moosh)

```python
# Crear nuevo usuario
app.crear_usuario({
    'sigad_documento': '12345678A',
    'sigad_nombre': 'Juan',
    'sigad_apellido1': 'García',
    'sigad_apellido2': 'López',
    'sigad_email': 'juan.garcia@ejemplo.com'
})

# Suspender usuario (baja)
app.suspender_usuario(userid=1234, documento='12345678A')

# Reactivar usuario
app.reactivar_usuario(userid=1234, documento='12345678A')

# Agregar a cohorte
app.agregar_a_cohorte(userid=1234, cohorte='alumnado', documento='12345678A')
```

**Velocidad**: ~1-3 segundos por operación (incluye cache de Moodle)

### Matrículas (Moosh)

```python
# Matricular en curso
app.matricular_en_curso(
    userid=1234,
    courseid=456,
    documento='12345678A',
    nombre_curso='IPPE1'
)

# Desmatricular (baja de módulo)
app.desmatricular_de_curso(
    userid=1234,
    courseid=456,
    documento='12345678A',
    nombre_curso='IPPE1'
)
```

**Velocidad**: ~1-2 segundos por operación

---

## 🎮 Uso desde Línea de Comandos

```bash
# Simulación (ver qué cambios se detectan y aplicarían)
python scripts/ejemplo_aplicar_cambios.py --dry-run

# Solo detectar cambios (sin aplicar)
python scripts/ejemplo_aplicar_cambios.py --detect-only

# Aplicar cambios reales ⚠️
python scripts/ejemplo_aplicar_cambios.py --apply
```

---

## 📊 Comparativa: SQL vs Moosh

| Operación | Método | Velocidad | Cuándo usar |
|-----------|--------|-----------|-------------|
| **Email** | SQL UPDATE | ~50ms | Cambios simples de campo |
| **Nombre** | SQL UPDATE | ~50ms | Cambios simples de campo |
| **Username** | SQL UPDATE | ~50ms | Cambio DNI/NIE (⚠️ cuidado) |
| **Crear usuario** | moosh | ~2s | Necesita generar password, perfil |
| **Suspender** | moosh | ~1s | Limpia sesiones, actualiza cache |
| **Matricular** | moosh | ~1.5s | Maneja enrolments, roles, cache |
| **Desmatricular** | moosh | ~1s | Limpia permisos, grupos |

**¿Por qué moosh para matrículas?**
- Maneja automáticamente la caché de Moodle
- Actualiza correctamente las tablas de enrolment
- Dispara eventos de Moodle (logs, notificaciones)
- Más seguro que UPDATEs directos en múltiples tablas

---

## 🔍 Flujo de Procesamiento

```python
# 1. DETECTAR (sigad_db_sync)
cambios = detectar_cambios_vs_moodle()

# cambios contiene:
# {
#   'alumnos_nuevos': [...],      # Crear con moosh
#   'alumnos_baja': [...],        # Suspender con moosh
#   'alumnos_reactivar': [...],   # Reactivar con moosh
#   'cambios_email': [...],       # UPDATE SQL
#   'cambios_nombre': [...],      # UPDATE SQL
#   'cambios_documento': [...],   # UPDATE SQL
#   'matriculas_nuevas': [...],   # moosh course-enrol
#   'matriculas_baja': [...],     # moosh course-unenrol
# }

# 2. APLICAR (sigad_aplicar_cambios)
aplicador.aplicar_todos_los_cambios(cambios)

# Orden interno:
# 1. Datos personales (SQL) - más rápido, sin dependencias
# 2. Altas de usuarios (moosh)
# 3. Reactivaciones (moosh)
# 4. Bajas de usuarios (moosh)
# 5. Matrículas nuevas (moosh)
# 6. Bajas de matrículas (moosh)
```

---

## ⚠️ Consideraciones Importantes

### Cambio de Username (Documento)

```python
# ⚠️ OPERACIÓN CRÍTICA
# El username es el login del usuario

# Antes de cambiar:
# 1. Verificar que no exista otro usuario con el nuevo username
# 2. Notificar al usuario del cambio
# 3. Considerar mantener sesiones activas

# Implementación actual verifica duplicados
app.actualizar_documento_username(
    userid=1234,
    documento_nuevo="12345678A",
    documento_anterior="X1234567Y"
)
```

### Mapeo de Cursos

Para matricular automáticamente, necesitas mapear siglas SIGAD a course IDs:

```python
MAPEO_CURSOS = {
    'IPPE1': 123,   # SIGAD 'IPPE1' -> Moodle course ID 123
    'PA': 124,
    'APSI': 125,
    # ...
}

# Si no hay mapeo, se loggea la necesidad pero no se matricula
```

Alternativa: Crear tabla en BD
```sql
CREATE TABLE mdl_aux_sigad_moodle_cursos (
    siglas_modulo VARCHAR(50) PRIMARY KEY,
    courseid INT NOT NULL,
    nombre_curso VARCHAR(255)
);
```

### Transacciones y Consistencia

```python
# Datos personales: usan transacción por operación
# Si falla uno, los anteriores se mantienen

# Moosh: cada comando es independiente
# Si falla una matrícula, las anteriores siguen aplicadas

# Recomendación: ejecutar en horario de baja carga
# y tener backups antes de cambios masivos
```

---

## 🐛 Troubleshooting

| Problema | Solución |
|----------|----------|
| "Container not found" | Verificar nombre del contenedor en MOODLE_CONTAINER |
| "Permission denied" en moosh | Verificar que el usuario puede ejecutar docker exec |
| Cambios de email no aplican | Verificar formato de email válido |
| Matrículas fallan | Verificar que existe el mapeo curso-sigla |
| Username duplicado | El nuevo username ya existe en otro usuario |
| Timeout en moosh | Aumentar timeout en run_moosh_command |

---

## 📈 Rendimiento Estimado

Para **5000 alumnos** con cambios en ~10%:

| Operación | Cantidad | Tiempo Estimado |
|-----------|----------|-----------------|
| Detectar cambios | - | 10-20s |
| Actualizar datos personales | 50 | 2-5s (SQL rápido) |
| Crear usuarios | 10 | 20-30s (moosh) |
| Suspender usuarios | 5 | 5-10s (moosh) |
| Matricular en cursos | 100 | 2-3 min (moosh) |
| **TOTAL** | - | **~5 minutos** |

---

## 📝 Resumen de Comandos Moosh Utilizados

| Comando | Propósito |
|---------|-----------|
| `moosh user-create` | Crear nuevo usuario |
| `moosh user-mod --suspend 1` | Suspender usuario |
| `moosh user-mod --suspend 0` | Reactivar usuario |
| `moosh course-enrol -i` | Matricular en curso |
| `moosh course-unenrol` | Desmatricular de curso |
| `moosh cohort-enrol` | Agregar a cohorte |
| `moosh user-list` | Obtener userid por username |
