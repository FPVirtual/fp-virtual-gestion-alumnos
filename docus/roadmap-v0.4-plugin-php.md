# Roadmap v0.4 — Sincronización SIGAD ↔ Moodle íntegramente en el plugin PHP

> **Rama:** `v0.4-plugin-php-dev` (creada desde `v0.3-estructura-paquete-con-logs`)
> **Moodle objetivo:** 4.5 (producción: 4.5.12). Compatibilidad mínima: 4.1 LTS.
> **Plugin:** `local_fpvirtual_gestion_alumnado`

## Índice

- [Objetivo y decisión](#objetivo-y-decisión)
- [Arquitectura objetivo](#arquitectura-objetivo)
- [Catálogo de reglas de negocio](#catálogo-de-reglas-de-negocio)
- [Decisiones pendientes](#decisiones-pendientes)
- [Fases](#fases)
- [Estado](#estado)

---

## Objetivo y decisión

Llevar **todo** el proceso de sincronización (descarga de SIGAD, análisis de
diferencias, aplicación de cambios, notificaciones e informe) al plugin
Moodle, ejecutándose dentro de Moodle:

- **Lecturas** con SQL a través de `$DB` (capa DML de Moodle, consultas parametrizadas
  y tablas temporales). Sin `moosh` ni conexiones MySQL externas.
- **Escrituras** exclusivamente mediante las APIs internas de Moodle
  (`user_create_user`, `user_update_user`, `profile_save_data`,
  `enrol_plugin::enrol_user/update_user_enrol/unenrol_user`, `cohort_add_member`,
  `cohort_remove_member`…), que disparan eventos, purgan cachés y crean contextos.
- **Sin token ni servicio web** para el proceso. Sin Python en el servidor.

El paquete Python (`gestion_alumnos/`) queda **congelado como referencia**:
no se invierte más en él; sus tests y documentos sirven de especificación.
Se retirará al cerrar la fase 10.

## Arquitectura objetivo

```
tarea cron / botón admin / CLI
            │
            ▼
   sync\engine::run(modo)                       (classes/sync/engine.php)
     1. sigad\client      → JSON de SIGAD (2 llamadas + espera + reintentos)
     2. sigad\parser      → dataset normalizado (alumnos, matrículas, ciclos)
     3. guardas           → aborta si SIGAD = 0 alumnos o dataset inválido
     4. sync\analyzer     → carga dataset en tablas temporales, cruza con
                            {user}, {user_info_data}, {user_enrolments},
                            {enrol}, {course}, {cohort_members} → sync\plan
     5. guardas de plan   → aborta si las bajas/suspensiones superan umbrales
     6. sync\applier      → (solo apply) ejecuta el plan con APIs de Moodle
     7. sync\notifier     → encola emails (tareas adhoc) con límite diario
     8. sync\report       → informe Markdown + resumen JSON en run_store
```

El **plan** (`sync\plan`) es la frontera clave: es un objeto serializable a JSON
con todas las operaciones calculadas. En `dry` se calcula y se informa; en
`apply` se ejecuta. Permite revisar, comparar ejecuciones y testear el análisis
sin escribir nada.

## Catálogo de reglas de negocio

Extraídas de `archive/main.py` (legacy en producción) y del paquete Python.
Cada regla tendrá al menos un test PHPUnit.

| Id | Regla | Origen |
|----|-------|--------|
| R1 | **Identidad**: `username = lower(documento)`. Email principal = `documento@fpvirtualaragon.es` (dominio configurable). `IdSIGAD` (campo de perfil) es el identificador estable. | legacy + py |
| R2 | **Ámbito**: solo se gestionan usuarios con `deleted = 0`, `auth` gestionado, que **no** empiecen por `prof` (prefijos configurables) y que **no** estén en la lista de usuarios protegidos (IDs configurables; incluye guest y admin). | legacy |
| R3 | **Clave de curso**: `shortname = {codigoCentro}-{siglasCiclo}-{idMateria}`. Si el curso no existe se informa ("curso inexistente") y no se matricula. | legacy |
| R4 | **Cursos excluidos de la sincronización de matrículas**: `ayuda` y los de tutoría (3.ª parte del shortname contiene `t`), que se gestionan por cohorte. | legacy |
| R5 | **Alta**: alumno de SIGAD sin usuario en Moodle (ni por username ni por `IdSIGAD`). Requiere documento, nombre, apellido1 y email; si falta algo → "no creable" en el informe. Se crea con `auth=manual`, contraseña aleatoria (forzar cambio), `city=Aragón`, `country=ES`, `maildigest=2`, campos `IdSIGAD`, `tipoDocumento`, `emailsigad`, `consentimientoCDD=0`. | legacy + py |
| R6 | **Cohortes**: todo alumno activo pertenece a la cohorte `alumnado` y a `{codigoCentro}-{siglasCiclo}` por cada ciclo de SIGAD (da acceso a la tutoría y al curso de ayuda). | legacy |
| R7 | **Matrícula nueva**: módulo de SIGAD sin matrícula en el curso → matricular (método `manual`, rol `student`). | legacy + py |
| R8 | **Reactivar matrícula**: módulo de SIGAD con matrícula suspendida (`ue.status = 1`) → reactivar. | legacy |
| R9 | **Suspender matrícula**: matrícula activa en un curso gestionado (R3/R4) que no está en SIGAD → suspender (no desmatricular: conserva el progreso). | legacy + py |
| R10 | **Baja de usuario**: usuario en ámbito (R2), activo, que no está en SIGAD (ni por username ni por `IdSIGAD`) → suspender todas sus matrículas, quitarlo de cohortes y suspender la cuenta. | legacy + py |
| R11 | **Reactivar usuario**: usuario suspendido que vuelve a SIGAD → reactivar y añadir a `alumnado` (R6 completa el resto). | legacy + py |
| R12 | **Cambio de documento** (NIE→DNI, etc.): usuario cuyo `IdSIGAD` coincide pero su username no → renombrar. Si el nuevo username ya existe → no se toca y se informa para revisión manual. | py (legacy usaba el email) |
| R13 | **Email personal**: si el email de SIGAD difiere del campo `emailsigad` → actualizar el campo. El email principal de Moodle no se toca. | legacy + py |
| R14 | **Nombre/apellidos**: si `nombre` ≠ `firstname` o `apellido1 [apellido2]` ≠ `lastname` → actualizar. | py |
| R15 | **Tutorías sobrantes**: alumno en una cohorte `{centro}-{ciclo}` que ya no corresponde a ningún ciclo suyo en SIGAD → quitar de esa cohorte. | legacy (generalizada) |
| R16 | **Limpieza de agosto**: en agosto, las matrículas suspendidas de cursos gestionados se eliminan (unenrol). Configurable (mes y activación). | legacy |
| R17 | **Guardas**: abortar si SIGAD devuelve 0 alumnos; abortar `apply` si las bajas (R10) o suspensiones (R9) superan un umbral (absoluto y % configurable). | py + nuevo |
| R18 | **Notificaciones**: bienvenida (con credenciales) en altas, aviso de cambio de usuario (R12), aviso de nuevas matrículas (R7) e informe a responsables. Fuera de producción los emails se redirigen a una dirección de pruebas. Límite diario configurable. | legacy + py |
| R19 | **Informe**: Markdown con todas las secciones del plan y resultados, guardado con la ejecución y enviado a los responsables. | legacy + py |
| R20 | **CSV Google Workspace**: alta de cuentas de correo (`Nombre, Apellidos, email, contraseña, /Alumnado, …`) adjunta al informe. | legacy |

## Decisiones pendientes

Por defecto se mantiene el comportamiento del legacy; quedan como ajustes del
plugin para poder cambiarlas sin tocar código.

| # | Pregunta | Valor por defecto |
|---|----------|-------------------|
| D1 | En una baja (R10), ¿quitar de **todas** las cohortes? El propio legacy duda de si afecta al progreso. | Solo cohortes gestionadas (`alumnado` y `{centro}-{ciclo}`) |
| D2 | ¿Mantener el envío de la contraseña en claro por email (R18) y en el CSV (R20)? | Sí (como hoy); revisar con el centro |
| D3 | ¿Mantener la limpieza de agosto (R16)? | Sí, activable |
| D4 | Umbrales de seguridad (R17) | Máx. 200 bajas y 5 % de matrículas suspendidas por ejecución |

## Fases

### Fase 0 — Higiene del repositorio ✅
- Sacar del control de versiones los informes reales (`logs/tests/*.md`, con DNI/NIE y
  emails de alumnado) y `.env.test`; ampliar `.gitignore`.
- Eliminar el token y la IP del docstring de `tests/test_moodle_api_integration.py`.
- ⚠️ **Pendiente de decisión**: purgar el historial (`git filter-repo`) y rotar el token.

### Fase 1 — Entorno de desarrollo y CI
- Entorno Docker reproducible (Moodle 4.5 + PHP 8.3 + MariaDB) para PHPUnit.
- `phpunit.xml`/script `scripts/plugin-test.sh` que enlaza el plugin y ejecuta sus tests.
- GitHub Actions con `moodle-plugin-ci` (phpunit, phplint, phpcs, validate) — Moodle 4.1 y 4.5.

### Fase 2 — Corrección del snapshot (transición)
- `get_snapshot`: `get_recordset_sql` (hoy `get_records_sql` colapsa filas por la primera
  columna: una sola matrícula por usuario y campos de perfil perdidos). Test de regresión.

### Fase 3 — SIGAD
- `sigad\client`: 2 llamadas (solicitud + datos), espera, reintentos, timeout, curl de Moodle.
  Credenciales en `admin_setting_encryptedpassword`. Errores sin volcar la respuesta.
- `sigad\parser`: valida y normaliza el JSON (incluye el `estudiantes` anidado como string)
  a un `sigad\dataset`. Construye los shortnames (R3) y cohortes (R6).
- Modo fichero (`--sigad-file`) para pruebas y reproducción de incidencias.

### Fase 4 — Análisis
- `sync\analyzer`: carga el dataset en tablas temporales (`create_temp_table`) y calcula
  el plan con SQL (R2–R16). Sin escrituras.
- `sync\plan`: operaciones tipadas, conteos, serialización JSON.
- Guardas R17.

### Fase 5 — Aplicación
- `sync\applier`: ejecuta el plan con APIs de Moodle, en el orden: altas → datos personales
  → renombres → reactivaciones → cohortes → matrículas (nuevas/reactivar) → suspensiones →
  bajas → limpieza de agosto. Errores aislados por operación; resultado por operación.

### Fase 6 — Notificaciones
- Plantillas Mustache (portadas de las Jinja2), `email_to_user` desde un usuario remitente
  configurable, envío diferido con tareas adhoc (reintentos nativos), límite diario,
  redirección fuera de producción.

### Fase 7 — Informe, panel y CLI
- `sync\report`: Markdown (R19) + CSV de Google (R20) guardados en dataroot y vinculados a la ejecución.
- `runner` pasa a ejecutar el motor PHP en proceso (se mantiene el modo "comando externo"
  solo durante la transición).
- `cli/sync.php` (`--mode=dry|apply`, `--sigad-file`, `--plan-out`).
- Panel: resumen por tipo de operación y descarga de plan/informe/CSV.

### Fase 8 — Tests y calidad
- PHPUnit: parser, cada regla del analizador (R2–R16) con generadores de Moodle, applier,
  guardas, notificador, engine end-to-end con fichero SIGAD sintético.
- Privacy provider actualizado (el informe contiene datos personales: retención y borrado).

### Fase 9 — Validación en preproducción
- Instalar, configurar SIGAD y ejecutar `dry` a diario en paralelo con el legacy durante
  1–2 semanas. Comparar el plan PHP con lo que hace el legacy cada noche.
- Resolver discrepancias (cada una → regla + test).

### Fase 10 — Producción y retirada
- Producción en `dry` → `apply` con umbrales conservadores.
- Desactivar el legacy (`curso2627`) y retirar `gestion_alumnos/` (Python), `zipapp` y la
  función webservice si nadie más la usa. Tag `v1.0.0` del plugin.

## Estado

| Fase | Estado |
|------|--------|
| 0 — Higiene | ✅ (purga de historial pendiente de decisión) |
| 1 — Entorno y CI | 🟡 en curso |
| 2 — Snapshot | ⬜ |
| 3 — SIGAD | ⬜ |
| 4 — Análisis | ⬜ |
| 5 — Aplicación | ⬜ |
| 6 — Notificaciones | ⬜ |
| 7 — Informe, panel y CLI | ⬜ |
| 8 — Tests | ⬜ (se hacen junto a cada fase) |
| 9 — Preproducción | ⬜ requiere acceso a entornos |
| 10 — Producción | ⬜ |
