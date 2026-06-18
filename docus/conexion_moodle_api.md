# Conexión con Moodle mediante API REST

Este documento describe la configuración necesaria, tanto en la aplicación como en Moodle, para que `gestion-alumnos` pueda comunicarse con Moodle a través de su API REST.

> **Alcance:** cubre la conexión remota vía API (`MOODLE_DRIVER=api`). Para ejecución local con `moosh`, consulta la sección de driver `moosh` del `README.md`.

---

## 1. Resumen de la conexión

La aplicación se comunica con Moodle usando el protocolo **REST** sobre HTTPS, enviando siempre estos parámetros base:

| Parámetro | Valor |
|-----------|-------|
| URL base  | `MOODLE_API_URL` (ej. `https://moodle.ejemplo.es/webservice/rest/server.php`) |
| Token     | `MOODLE_API_TOKEN` |
| Formato   | `json` |
| User-Agent| `gestion-alumnos/<version>` |
| Timeout   | 60 segundos |

Dependiendo de la estrategia de extracción configurada, las llamadas serán:

- `MOODLE_SOURCE_STRATEGY=api-course-based`: una llamada a `core_course_get_courses` y una llamada a `core_enrol_get_enrolled_users` por cada curso.
- `MOODLE_SOURCE_STRATEGY=api-snapshot`: una única llamada a `local_fparagon_get_snapshot`, que requiere el plugin propio `local_fparagon` instalado en Moodle.

---

## 2. Configuración en la aplicación

Copia el archivo de ejemplo y edita las variables de entorno:

```bash
cp .env.example .env
```

Variables obligatorias para el driver API:

```bash
# Activa el driver remoto por API REST
MOODLE_DRIVER=api

# Estrategia de extracción: api-course-based o api-snapshot
MOODLE_SOURCE_STRATEGY=api-course-based

# Credenciales de Moodle
MOODLE_API_URL=https://moodle.ejemplo.es/webservice/rest/server.php
MOODLE_API_TOKEN=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
```

La aplicación valida que ambas variables estén presentes cuando `MOODLE_DRIVER=api`. Si falta alguna, se lanza un error antes de realizar cualquier llamada.

---

## 3. Configuración en Moodle (interfaz web)

Se recomienda crear un **usuario de sistema dedicado** y un **servicio web externo** exclusivo para esta aplicación. No se debe usar una cuenta personal de administrador.

### 3.1. Habilitar servicios web

1. Ve a `Administración del sitio > Funciones avanzadas`.
2. Activa **Habilitar servicios web**.

### 3.2. Habilitar el protocolo REST

1. Ve a `Administración del sitio > Servidor > Servicios web > Gestionar protocolos`.
2. Activa **REST** (`webservice/rest:use`).

### 3.3. Crear el usuario de sistema

1. Ve a `Administración del sitio > Usuarios > Cuentas > Añadir un nuevo usuario`.
2. Crea un usuario dedicado, por ejemplo:
   - **Nombre de usuario:** `svc-fpvirtual-gestion`
   - **Nombre:** `Servicio`
   - **Apellido(s):** `Gestión Alumnos`
   - **Correo electrónico:** una dirección real y monitorizada
   - **Método de autenticación:** Manual
3. Establece una contraseña segura.

### 3.4. Crear el rol de servicio web

1. Ve a `Administración del sitio > Usuarios > Permisos > Definir roles > Añadir un nuevo rol`.
2. Configura:
   - **Nombre largo:** `FP Virtual - Gestión Alumnos API`
   - **Nombre corto:** `fpvirtualgestionapi`
   - **Archetipo:** `Authenticated user` (o ninguno)
   - **Contexto:** Sistema
3. En la pestaña **Permisos**, permite (`Allow`) al menos las siguientes capacidades:

   | Capacidad | Motivo |
   |-----------|--------|
   | `webservice/rest:use` | Usar el protocolo REST |
   | `moodle/user:create` | Crear alumnos nuevos |
   | `moodle/user:update` | Actualizar usuarios y suspender |
   | `moodle/user:viewdetails` | Consultar datos de usuarios |
   | `moodle/user:viewhiddendetails` | Ver campos ocultos del perfil |
   | `moodle/user:viewalldetails` | Ver todos los detalles del perfil |
   | `moodle/course:view` | Listar cursos |
   | `moodle/course:viewhiddencourses` | Ver cursos ocultos |
   | `moodle/course:update` | Necesario para algunas lecturas de curso |
   | `moodle/course:useremail` | Ver emails de usuarios en cursos |
   | `moodle/site:accessallgroups` | Acceder a todos los grupos |
   | `enrol/manual:enrol` | Matricular usuarios manualmente |
   | `enrol/manual:unenrol` | Desmatricular usuarios |
   | `moodle/role:assign` | Asignar roles durante la matriculación |
   | `moodle/cohort:view` | Buscar cohortes |
   | `moodle/cohort:assign` | Añadir/eliminar miembros de cohortes |

4. En la pestaña **Permitir asignaciones de roles**, marca **Student**. Esto es imprescindible para que el usuario de servicio pueda matricular como estudiante (`roleid=5`).

### 3.5. Asignar el rol al usuario de sistema

1. Ve a `Administración del sitio > Usuarios > Permisos > Asignar roles del sistema`.
2. Selecciona el rol creado y asígnalo al usuario `svc-fpvirtual-gestion`.

### 3.6. Crear el servicio web externo

1. Ve a `Administración del sitio > Servidor > Servicios web > Servicios externos`.
2. Añade un servicio:
   - **Nombre:** `FP Virtual - Gestión Alumnos`
   - **Nombre corto:** `fpvirtual_gestion`
   - **Habilitado:** Sí
   - **Solo usuarios autorizados:** Sí
3. Guarda y abre el servicio.
4. Añade las siguientes funciones una a una:

   | Función REST | Uso en la aplicación |
   |--------------|----------------------|
   | `core_webservice_get_site_info` | Validar conexión y token |
   | `core_user_get_users_by_field` | Buscar usuario por `username` |
   | `core_user_get_users` | Búsqueda alternativa de usuarios |
   | `core_user_create_users` | Crear alumnos nuevos |
   | `core_user_update_users` | Actualizar datos, email, suspender |
   | `core_course_get_courses` | Listar todos los cursos |
   | `core_enrol_get_enrolled_users` | Obtener matriculados de un curso |
   | `core_enrol_get_users_courses` | Obtener cursos de un usuario |
   | `enrol_manual_enrol_users` | Matricular en curso como estudiante |
   | `enrol_manual_unenrol_users` | Desmatricular de curso |
   | `core_cohort_search_cohorts` | Buscar cohortes por nombre |
   | `core_cohort_add_cohort_members` | Añadir usuario a cohorte |
   | `core_cohort_delete_cohort_members` | Eliminar usuario de cohorte |
   | `local_fparagon_get_snapshot` | **Solo si usas `api-snapshot`** y tienes el plugin instalado |

5. En **Usuarios autorizados**, añade el usuario `svc-fpvirtual-gestion`.

### 3.7. Crear el token

1. Ve a `Administración del sitio > Servidor > Servicios web > Gestionar tokens`.
2. Añade un token:
   - **Usuario:** `svc-fpvirtual-gestion`
   - **Servicio:** `FP Virtual - Gestión Alumnos`
3. Guarda y copia el token generado.
4. Pega ese token en la variable `MOODLE_API_TOKEN` del `.env` de la aplicación.

---

## 4. Equivalencia en SQL

> **Advertencia:** ejecuta estas sentencias solo si conoces el prefijo de tablas de tu Moodle (por defecto `mdl_`) y el `contextid` del contexto de sistema. Es preferible usar la interfaz web o la herramienta `moosh`. Prueba primero en un entorno no productivo.

### 4.1. Crear el rol

```sql
INSERT INTO mdl_role (name, shortname, description, archetype)
VALUES (
    'FP Virtual - Gestión Alumnos API',
    'fpvirtualgestionapi',
    'Rol para sincronización SIGAD-Moodle vía API REST',
    ''
);
```

Recupera el `id` del rol recién creado:

```sql
SELECT id FROM mdl_role WHERE shortname = 'fpvirtualgestionapi';
```

En los ejemplos siguientes se asume que el rol tiene `id = 21`.

### 4.2. Obtener el contexto de sistema

```sql
SELECT id AS contextid FROM mdl_context WHERE contextlevel = 10 AND instanceid = 0;
```

En los ejemplos siguientes se asume que el contexto de sistema tiene `id = 1`.

### 4.3. Asignar capacidades al rol

```sql
INSERT INTO mdl_role_capabilities (contextid, roleid, capability, permission, timemodified, modifierid)
VALUES
(1, 21, 'webservice/rest:use', 1, UNIX_TIMESTAMP(), 2),
(1, 21, 'moodle/user:create', 1, UNIX_TIMESTAMP(), 2),
(1, 21, 'moodle/user:update', 1, UNIX_TIMESTAMP(), 2),
(1, 21, 'moodle/user:viewdetails', 1, UNIX_TIMESTAMP(), 2),
(1, 21, 'moodle/user:viewhiddendetails', 1, UNIX_TIMESTAMP(), 2),
(1, 21, 'moodle/user:viewalldetails', 1, UNIX_TIMESTAMP(), 2),
(1, 21, 'moodle/course:view', 1, UNIX_TIMESTAMP(), 2),
(1, 21, 'moodle/course:viewhiddencourses', 1, UNIX_TIMESTAMP(), 2),
(1, 21, 'moodle/course:update', 1, UNIX_TIMESTAMP(), 2),
(1, 21, 'moodle/course:useremail', 1, UNIX_TIMESTAMP(), 2),
(1, 21, 'moodle/site:accessallgroups', 1, UNIX_TIMESTAMP(), 2),
(1, 21, 'enrol/manual:enrol', 1, UNIX_TIMESTAMP(), 2),
(1, 21, 'enrol/manual:unenrol', 1, UNIX_TIMESTAMP(), 2),
(1, 21, 'moodle/role:assign', 1, UNIX_TIMESTAMP(), 2),
(1, 21, 'moodle/cohort:view', 1, UNIX_TIMESTAMP(), 2),
(1, 21, 'moodle/cohort:assign', 1, UNIX_TIMESTAMP(), 2);
```

> **Nota:** la capacidad de permitir asignar el rol **Student** no se almacena en `mdl_role_capabilities`; se configura en la pestaña *Permitir asignaciones de roles* del rol o mediante la API interna de Moodle.

### 4.4. Crear el usuario de sistema

Se recomienda usar `moosh` para generar correctamente el hash de contraseña:

```bash
moosh user-create \
  --password 'ContraseñaSegura123!' \
  --email svc-fpvirtual-gestion@ejemplo.es \
  --firstname Servicio \
  --lastname "Gestión Alumnos" \
  svc-fpvirtual-gestion
```

Recupera su `id`:

```sql
SELECT id FROM mdl_user WHERE username = 'svc-fpvirtual-gestion';
```

En los ejemplos siguientes se asume `userid = 999`.

### 4.5. Asignar el rol al usuario en el contexto de sistema

```sql
INSERT INTO mdl_role_assignments (roleid, contextid, userid, timemodified, component)
VALUES (21, 1, 999, UNIX_TIMESTAMP(), '');
```

### 4.6. Crear el servicio externo

```sql
INSERT INTO mdl_external_services (
    name, shortname, enabled, restrictedusers,
    timecreated, timemodified, downloadfiles, uploadfiles
) VALUES (
    'FP Virtual - Gestión Alumnos',
    'fpvirtual_gestion',
    1, 1,
    UNIX_TIMESTAMP(), UNIX_TIMESTAMP(), 0, 0
);
```

Recupera su `id`:

```sql
SELECT id FROM mdl_external_services WHERE shortname = 'fpvirtual_gestion';
```

En los ejemplos siguientes se asume `externalserviceid = 5`.

### 4.7. Añadir funciones al servicio

```sql
INSERT INTO mdl_external_services_functions (externalserviceid, functionname)
VALUES
(5, 'core_webservice_get_site_info'),
(5, 'core_user_get_users_by_field'),
(5, 'core_user_get_users'),
(5, 'core_user_create_users'),
(5, 'core_user_update_users'),
(5, 'core_course_get_courses'),
(5, 'core_enrol_get_enrolled_users'),
(5, 'core_enrol_get_users_courses'),
(5, 'enrol_manual_enrol_users'),
(5, 'enrol_manual_unenrol_users'),
(5, 'core_cohort_search_cohorts'),
(5, 'core_cohort_add_cohort_members'),
(5, 'core_cohort_delete_cohort_members');
```

Añade también `local_fparagon_get_snapshot` si vas a usar la estrategia `api-snapshot` y tienes el plugin instalado.

### 4.8. Autorizar al usuario en el servicio

```sql
INSERT INTO mdl_external_services_users (externalserviceid, userid)
VALUES (5, 999);
```

### 4.9. Crear el token

Genera un token de 32 caracteres hexadecimales. Es más seguro hacerlo desde la interfaz web, pero si necesitas SQL:

```sql
INSERT INTO mdl_external_tokens (
    token, userid, externalserviceid, creatorid, contextid, timecreated, validuntil
) VALUES (
    LOWER(CONV(FLOOR(RAND() * 99999999999999999999), 10, 16)),
    999, 5, 2, 1, UNIX_TIMESTAMP(), 0
);
```

Recupera el token y configúralo en `MOODLE_API_TOKEN`:

```sql
SELECT token FROM mdl_external_tokens WHERE userid = 999 AND externalserviceid = 5;
```

---

## 5. Campos personalizados de usuario

La aplicación lee y escribe los siguientes campos personalizados del perfil de usuario de Moodle. Deben crearse previamente en `Administración del sitio > Usuarios > Campos del perfil de usuario > Campos personalizados` con los **nombres cortos** exactos:

| Nombre corto | Tipo | Uso |
|--------------|------|-----|
| `IdSIGAD` | Texto corto | Identificador del alumno en SIGAD |
| `tipoDocumento` | Texto corto | Tipo de documento (DNI, NIE, pasaporte) |
| `emailsigad` | Texto corto | Email registrado en SIGAD |
| `consentimientoCDD` | Casilla de verificación | Indica si ha aceptado la CDD |

Si alguno de estos campos no existe, las operaciones de creación/actualización de usuarios pueden fallar o ignorar dichos valores.

---

## 6. Plugin `local_fparagon` (estrategia `api-snapshot`)

La estrategia `api-snapshot` requiere que el plugin `local_fparagon` esté instalado en Moodle y exponga la función `local_fparagon_get_snapshot`. En la estructura actual del repositorio, el plugin está especificado pero **no implementado**.

### Instalación prevista

```bash
cp -r moodle_plugin/local_fparagon /ruta/a/moodle/local/
```

Una vez copiado, accede a `Administración del sitio > Notificaciones` para completar la instalación.

### Funciones a añadir al servicio web

Si el plugin estuviera implementado, habría que añadir `local_fparagon_get_snapshot` al servicio web creado en el paso 3.6.

---

## 7. Verificación de la conexión

Una vez configurado todo, prueba la conexión base con `curl`:

```bash
curl -s -X POST "https://moodle.ejemplo.es/webservice/rest/server.php" \
  -d "wstoken=TU_TOKEN" \
  -d "wsfunction=core_webservice_get_site_info" \
  -d "moodlewsrestformat=json" | jq
```

Debería devolver información del sitio (`sitename`, `siteurl`, `functions`, etc.).

Prueba una lectura de usuario:

```bash
curl -s -X POST "https://moodle.ejemplo.es/webservice/rest/server.php" \
  -d "wstoken=TU_TOKEN" \
  -d "wsfunction=core_user_get_users_by_field" \
  -d "moodlewsrestformat=json" \
  -d "field=username" \
  -d "values[0]=svc-fpvirtual-gestion" | jq
```

Si obtienes un error de permisos (`accessexception`, `nopermissions`), revisa:

- Que la función esté añadida al servicio web.
- Que el rol del usuario de servicio tenga las capacidades necesarias.
- Que el rol pueda asignar el rol **Student** si vas a probar matriculaciones.

---

## 8. Buenas prácticas y advertencias

- **Usuario dedicado:** no reutilices una cuenta humana de administrador. Crea un usuario de sistema exclusivo por entorno.
- **No suspender al usuario del token:** si el usuario propietario del token se suspende, todas las llamadas a la API fallarán.
- **Token seguro:** trata el token como una contraseña. No lo incluyas en repositorios públicos; usa siempre el archivo `.env`.
- **Usuarios protegidos:** la aplicación carga un CSV con IDs de usuarios que nunca deben suspenderse ni eliminarse. Configura `USUARIOS_PROTEGIDOS_CSV` adecuadamente.
- **Rol estudiante:** la aplicación matricula siempre con `roleid=5` (estudiante). Comprueba que en tu instancia de Moodle el rol **Student** sigue teniendo ese id, o ajusta el código.
- **Matriculación manual:** para que `enrol_manual_enrol_users` funcione, el método de matriculación manual debe estar habilitado en cada curso destino.
- **Límite de llamadas:** la estrategia `api-course-based` realiza aproximadamente una llamada por curso. En instancias con muchos cursos, considera usar `api-snapshot` cuando el plugin esté disponible.

---

## 9. Diagnóstico rápido de errores comunes

| Síntoma | Causa probable | Solución |
|---------|----------------|----------|
| `Faltan MOODLE_API_URL o MOODLE_API_TOKEN` | Variables no definidas en `.env` | Revisa el archivo `.env` |
| `Invalid token` | Token incorrecto o revocado | Regenera el token en Moodle |
| `accessexception` | El usuario no está autorizado en el servicio | Añade el usuario en **Usuarios autorizados** |
| `nopermissions` | Falta alguna capacidad en el rol | Revisa las capacidades del paso 3.4 |
| `functionnotavailable` | La función no está en el servicio o no existe | Añádela al servicio; si es `local_fparagon_get_snapshot`, instala el plugin |
| `errorcoursecontextnotvalid` o similar al matricular | El método de matriculación manual está deshabilitado en el curso | Habilita la matriculación manual en el curso |
| Los campos personalizados no se actualizan | No existen en Moodle o los nombres cortos no coinciden | Crea los campos con los nombres exactos del paso 5 |
