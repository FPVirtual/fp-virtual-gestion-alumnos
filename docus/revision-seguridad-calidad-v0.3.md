# Revisión de seguridad y calidad — rama `v0.3-estructura-paquete-con-logs`

> **Fecha:** 2026-10-29
> **Alcance:** paquete `gestion_alumnos/` y `scripts/` en su última versión
> (HEAD de la rama, ~4.800 líneas). Suite ejecutada con `.venv`.
> **Veredicto general:** arquitectura sólida (sin `shell=True`, sin `eval`,
> TLS verificado por defecto, passwords con `secrets`), pero con 2
> hallazgos de seguridad que deben resolverse antes de producción y un
> riesgo operativo grave (suspensión masiva si SIGAD devuelve 0 alumnos).

---

## 🔴 Seguridad — altos

### 1. Token real de la API de Moodle commiteado en el repo
- **Dónde:** `tests/test_moodle_api_integration.py:12` (docstring) y
  `.env.test` (también trackeada en git).
- **Qué:** el docstring incluye `MOODLE_API_TOKEN=9a8fb5343608c92a694165f59fdc2ae4`
  y la IP interna del Moodle de test (`192.168.2.253`).
- **Estado actual:** el token ya está revocado (los tests fallan con
  "ficha no encontrada"), pero permanece en el historial de git.
- **Acción:** quitar el token del docstring, sacar `.env.test` del
  tracking (añadir a `.gitignore`), rotar el token si sigue vigente en
  algún entorno y valorar purgar el historial.

### 2. Inyección HTML en plantillas de email + DoS por formato
- **Dónde:** `gestion_alumnos/repositories/email_repository.py:37` y
  `gestion_alumnos/services/email_queue_processor.py:95`.
- **Qué:** render con `contenido.format(**kwargs)` **sin escapar**. Los
  datos de SIGAD (nombre, apellidos) llegan crudos al HTML del correo;
  un apellido con `<` inyecta markup y cualquier dato con `{`/`}` rompe el
  `format` y tumba el envío.
- **Acción:** es exactamente el defecto que corrige la migración a Jinja2
  con `select_autoescape` del roadmap (`roadmap-portacion-curso2627.md`,
  lote 3). Priorizar antes de producción con datos reales.

### 3. Contraseñas de alumnos persistidas en claro
- **Dónde:** `gestion_alumnos/repositories/email_queue_repository.py:86`.
- **Qué:** el campo `contrasena` se guarda en plaintext dentro de
  `csvs/email_queue.csv`, junto a emails de alumnado (PII/RGPD sin
  protección). Es la credencial de una cuenta real de estudiante en disco.
- **Acción:** minimizar el tiempo de residencia (procesar y borrar),
  restringir permisos del directorio `csvs/`, o sustituir el envío de
  contraseña por flujo de "primer acceso / restablecer" si Moodle lo
  permite.

### 4. Credenciales SIGAD como headers en GET
- **Dónde:** `gestion_alumnos/repositories/sigad_repository.py:96-98`.
- **Qué:** usuario/password viajan en headers de peticiones GET; quedan
  registradas en logs de proxies/servidores intermedios. Además, en los
  errores se incluye `respuesta=str(data)` que puede filtrar contenido.
- **Acción:** consultar con el proveedor de la API si soporta Basic Auth o
  POST; en cualquier caso, sanitizar lo que se adjunta en `APIError`.

### 5. SQL interpolado en `_find_removed_users`
- **Dónde:** `gestion_alumnos/services/sync_analyzer.py:211-218`.
- **Qué:** los IDs de usuarios protegidos van en un f-string dentro de la
  query DuckDB. Hoy es seguro (los IDs llegan casteados a `int` desde
  `cargar_usuarios_protegidos`), pero es un anti-patrón frágil: cualquier
  cambio futuro en el origen de datos lo rompería.
- **Acción:** parametrizar la query (DuckDB soporta `$1, $2...` con
  listas mediante `execute(sql, [params])`).

---

## 🟠 Funcionales graves (riesgo operativo)

### 6. Sin guarda de SIGAD vacío — suspensión masiva
- **Dónde:** `gestion_alumnos/services/sync_orchestrator.py:55`.
- **Qué:** si SIGAD responde con 0 alumnos (caída, cambio de API,
  respuesta vacía), el analyzer marca **todos** los usuarios de Moodle
  como bajas y el applier los suspende en masa.
- **Acción:** punto 4.3 del roadmap de portación (`curso2627` ya lo
  resolvió en el commit `77e6352`): abortar si
  `registro.total_alumnos == 0` + test.

### 7. Bug en el fallback de desmatriculación — rematrícula accidental
- **Dónde:** `gestion_alumnos/services/sync_applier.py:235-240`.
- **Qué:** si `suspend_enrolment` lanza `NotImplementedError`, el
  "fallback" llama a `enrol_user_to_course` (**¡rematricula al alumno!**)
  en lugar de desmatricularlo. Debería ser `unenrol`/`remove`.
- **Acción:** corregir a la operación inversa y añadir test.

### 8. Colisiones de rename de username sin guard
- **Dónde:** `_find_username_changes` (`sync_analyzer.py:307-316`).
- **Qué:** no comprueba si el username nuevo ya existe en Moodle: el
  rename fallará a medias dejando la cuenta sin renombrar y sin decisión
  de baja (roadmap 4.1).
- **Acción:** excluir el rename o emitir un delta alternativo con
  trazabilidad en el informe.

### 9. Emails desconectados del flujo de sincronización
- **Dónde:** `SyncApplier` no recibe `EmailRepository`.
- **Qué:** bienvenida, cambio de username y nuevas matrículas nunca se
  notifican desde la sincronización — el código existe pero es
  funcionalidad muerta (roadmap 5.1).
- **Acción:** inyectar el repositorio de email en `SyncApplier`/
  `SyncOrchestrator` y emitir el aviso por cada delta correspondiente.

### 10. Apellido calculado con `replace`
- **Dónde:** `sync_applier.py:113`.
- **Qué:** `nombre_completo.replace(nombre, "")` corrompe el apellido si
  el nombre aparece dentro de un apellido (p. ej. "María Marín").
- **Acción:** construir el apellido desde `apellido1`/`apellido2` (ya
  disponibles en el modelo `Alumno`).

---

## 🟡 Calidad — medios

| # | Problema | Dónde | Acción sugerida |
|---|----------|-------|-----------------|
| 11 | Límite de emails triplicado; `max_emails_diarios` huérfano | `config.py:104,213-215`, `email_repository.py:31`, `email_queue_repository.py:32` | Consolidar en un único setting efectivo (roadmap 2.3) |
| 12 | `settings` global construido en import-time; `--env-file` ignorado por esa instancia; mezcla con `Settings()` por defecto en muchos `__init__` | `config.py:223-234`, `cli.py:92-112` | Construir `Settings` una vez en `main()` y propagar por DI; eliminar el global |
| 13 | `USUARIOS_PROTEGIDOS` hardcodeados duplicados en los dos repositorios Moodle y aparentemente sin uso en la lógica de sync (que solo usa el CSV) | `moodle_api_repository.py:22-27`, `moodle_moosh_repository.py:25-30` | Usar el CSV configurable como única fuente o eliminar los frozenset |
| 14 | Duplicación de la serialización del contexto de email entre `EmailRepositoryImpl` y `EmailQueueRepository`; `_process_single` accede al privado `_sender._enviar` y duplica el render | `email_repository.py:105-156`, `email_queue_repository.py:69-132`, `email_queue_processor.py:76-103` | Extraer un builder de contexto compartido y unificar el render |
| 15 | Cola CSV sin lock y reescritura completa no atómica | `email_queue_repository.py:176-207` | Lock con `fcntl` (roadmap 2.5) + escritura atómica (tmp+rename) |
| 16 | Conexión DuckDB nunca cerrada | `sync_analyzer.py:76` | `close()` en `analyze()` o `__del__`/context manager |
| 17 | `cli.py` accede al atributo privado `orchestrator._report_logger` | `cli.py:147` | Exponer `filename` como propiedad pública del orquestador |
| 18 | Template mal formado: `<b>{usuario}</p>` (etiqueta sin cerrar); enlace a curso de ayuda `id=2` | `templates/nuevoUsuario.html:5,15` | Cerrar etiqueta; corregir enlace a `id=654` (roadmap 1.6) |
| 19 | SMTP sin timeout (riesgo de hang) | `email_repository.py:83` | `smtp_timeout: int = 30` en `Settings` (roadmap 1.1) |
| 20 | `gestion_service.py` legacy deprecado con generación de password duplicada | `services/gestion_service.py:133-137` | Eliminar tras conectar emails al flujo (punto 9) |

---

## Estado de la suite

- Con `.venv`: **109 pasan, 8 fallan** (`test_moodle_api_integration.py`).
- Los 8 fallos **no son regresión**: el módulo solo verifica que el host
  responde, no que el token sea válido, y falla contra
  `192.168.2.253:8087` con "ficha no encontrada" (token revocado).
- Con el `python` del sistema el módulo `duckdb` ni está instalado: la
  suite no se recolecta fuera de `.venv`. Documentar el entorno
  obligatorio o añadir un `Makefile`/task.

---

## Prioridades recomendadas

1. **Revocar/rotar el token de Moodle** y limpiarlo del repo + `.env.test`
   (hallazgo 1).
2. **Guarda de SIGAD vacío** (hallazgo 6) — es el único que puede causar
   un incidente en producción hoy.
3. **Corregir el fallback de desmatriculación** (hallazgo 7) — bug latente
   que rematrícula alumnos.
4. **Escapado HTML** (hallazgo 2) antes de producción con datos reales.
5. Resto de hallazgos según los lotes del
   [`roadmap-portacion-curso2627.md`](roadmap-portacion-curso2627.md).
