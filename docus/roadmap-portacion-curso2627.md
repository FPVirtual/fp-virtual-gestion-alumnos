# Roadmap — Portación de mejoras de `curso2627` a `v0.3`

> **Origen:** análisis comparativo realizado el 2026-10-28 entre
> `origin/curso2627` (línea legacy) y `v0.3-estructura-paquete-con-logs`.
>
> **Progreso (2026-10-29):** implementados los lotes 1, 2, 4 y 5
> (más los fixes detectados en la revisión de seguridad) con 129 tests
> en verde. **Pendiente: Lote 3** (migración de plantillas a Jinja2 con
> `base.html`, preheader y logo incrustado) y el punto 5.3, que dependen
> de añadir `jinja2` como dependencia y resolver la carga de plantillas
> dentro del zipapp (`importlib.resources`).
>
> **Contexto de diseño que condiciona varios puntos:**
> - En `curso2627` el username de Moodle es el documento y el email
>   corporativo se genera con `creaEmailsDominio` (iniciales + apellidos) —
>   colisionable por construcción.
> - En `v0.3` el username sigue siendo el documento en minúsculas
>   (`models/alumno.py:84`) pero el email institucional es
>   `{documento}@fpvirtualaragon.es` (`models/alumno.py:89-91`) — único por
>   construcción. Esto hace innecesarias varias comprobaciones de la legacy.

---

## Lote 1 — Email: quick wins (esfuerzo bajo) ✅ IMPLEMENTADO

| # | Mejora | Origen curso2627 | Acción en v0.3 | Estado |
|---|--------|------------------|----------------|--------|
| 1.1 | **SMTP con timeout** | c3330bc | `smtp_timeout: int = 30` en `Settings`; se pasa a `smtplib.SMTP` en `EmailRepositoryImpl._conectar_smtp` | ✅ |
| 1.2 | **Pausa entre correos** | `PAUSA_ENTRE_CORREOS = 2` | `email_pausa_segundos: int = 2` + `time.sleep` en el bucle del procesador | ✅ |
| 1.3 | **Texto plano real derivado del HTML** | baa978b (`_ExtractorTexto`) | Portado a `gestion_alumnos/utils/html_to_text.py`; `_enviar` usa `EmailMessage` con `set_content()` + `add_alternative()` y `add_attachment` | ✅ |
| 1.4 | **`--dry-run` en `process-emails`** | enviar_correos.py | Flag en `cli.py`; el procesador renderiza sin enviar ni tocar estados | ✅ |
| 1.5 | **Salida con código 1 si hay fallos** | b30a9b9 | `return 1 if stats["fallidos"] else 0` en el subcomando `process-emails` | ✅ |
| 1.6 | **Fix enlace curso de Ayuda (`id=654`)** | c096a7a | Corregido `gestion_alumnos/templates/nuevoUsuario.html` (era `id=2`, bug heredado) junto a la etiqueta `<b>` sin cerrar | ✅ |

## Lote 2 — Email: robustez de la cola (esfuerzo medio) ✅ IMPLEMENTADO

| # | Mejora | Origen curso2627 | Acción en v0.3 | Estado |
|---|--------|------------------|----------------|--------|
| 2.1 | **Reintentos de envío (3 intentos)** | `MAX_INTENTOS=3` | `EmailJob.intentos` + `email_max_intentos`; `EmailQueueRepository.registrar_fallo` deja el email `pending` hasta agotar intentos | ✅ |
| 2.2 | **Reintento de transporte SMTP** | reconexión única en `main()` | En `_enviar`: si `send_message` falla, se cierra, reconecta y reintenta una vez | ✅ |
| 2.3 | **Límite de correos por ejecución** | e7bff6e | Consolidado: `Settings.email_limit` es la única fuente (`MAX_EMAILS_DIARIOS` en `www`, 10 en otros entornos); eliminada la duplicación en repositorios | ✅ |
| 2.4 | **`BIENVENIDA_TO` configurable** | 908c3b8 / e7bff6e | `bienvenida_to: str \| None` en `Settings`; lo usa `_get_destinatario` (fallback anterior hardcodeado) | ✅ |
| 2.5 | **Lock anti-ejecución concurrente** | `bloquea_ejecucion()` con `flock` | `bloqueo_ejecucion` en `utils/helpers.py` (lock en `csv_dir/.<subdomain>.lock`), usado por `process-emails` | ✅ |
| 2.6 | **`--solo-informes` en `process-emails`** | b30a9b9 | `EmailJob.tipo` explícito (`aviso`/`informe`); filtro en `obtener_pendientes(solo_informes=True)` | ✅ |
| 2.7 | **Priorización de informes en la cola** | prefijos `0-informe` / `1-aviso` | `obtener_pendientes` ordena informes primero (orden estable) | ✅ |

## Lote 3 — Email: plantillas Jinja2 (esfuerzo mayor) ⬜ PENDIENTE

La migración más grande; además corrige un **defecto de seguridad residual**:
el render actual con `str.format()` escapa los valores (mitigado con
`gestion_alumnos/utils/plantillas.py`), pero la herencia de plantillas y el
preheader requieren Jinja2.

| # | Mejora | Origen curso2627 | Acción en v0.3 | Estado |
|---|--------|------------------|----------------|--------|
| 3.1 | **Migrar render a Jinja2 con autoescape** | 10c4033, `select_autoescape(["html"])` | Añadir `jinja2` a dependencias; `Environment` con `PackageLoader`/`DictLoader` vía `importlib.resources` (⚠️ `FileSystemLoader` no sirve dentro del zipapp); sustituir el render de `plantillas.py` | ⬜ |
| 3.2 | **`base.html` con herencia de bloques** | `base.html` (layout 600px, Roboto, bloques `titulo`/`preheader`/`contenido`/`pie`, footer RRSS) | Reescribir las 5 plantillas a herencia; elimina el footer de RRSS duplicado en cada una | ⬜ |
| 3.3 | **Preheader oculto** | baa978b | Bloque `preheader` en `base.html` | ⬜ |
| 3.4 | **Logo incrustado inline (`cid:logo`)** | baa978b | Copiar `logo.png` a `gestion_alumnos/templates/img/`, verificar que `scripts/build_zipapp.py` incluya binarios; `add_related(...cid="<logo>")` | ⬜ |
| 3.5 | **Plantilla `nuevoUsuario.html` mejorada** | 24cdac1 / 80896da | Versión curso2627 con explicación de las dos cuentas, recuperación de contraseña y matrículas como `<ul><li>` | ⬜ |

## Lote 4 — DNI/documento: sincronización (esfuerzo medio) ✅ IMPLEMENTADO

| # | Mejora | Origen curso2627 | Acción en v0.3 | Estado |
|---|--------|------------------|----------------|--------|
| 4.1 | **Guard de colisión en renombres** | 31a6b83 | `_find_username_changes` omite el rename si el username nuevo ya existe en Moodle (`lower(s.documento) NOT IN (SELECT username FROM moodle_users)`) | ✅ |
| 4.2 | **Reactivación de suspendidos** | 31a6b83 | Nuevo `ReactivationDelta` (Moodle `suspended=1` y presente en SIGAD); `SyncApplier._apply_reactivations` llama a `reactivate_user` + `enrol_user_to_cohort(username, "alumnado")`; sección nueva en el informe | ✅ |
| 4.3 | **Parada forzosa si SIGAD devuelve 0 alumnos** ⚠️ | 77e6352 | `SyncOrchestrator.run` lanza `APIError` antes de extraer de Moodle; test específico | ✅ |

## Lote 5 — Email + DNI: aviso de cambio de documento ✅ IMPLEMENTADO

| # | Mejora | Origen curso2627 | Acción en v0.3 | Estado |
|---|--------|------------------|----------------|--------|
| 5.1 | **Cablear el aviso al flujo de sync** | — | `SyncApplier` recibe `EmailRepository` (inyectado por el orquestador según `EMAIL_MODE`) y notifica altas, cambios de username y matrículas nuevas; errores de email nunca bloquean la sync | ✅ |
| 5.2 | **Contenido mejorado del aviso NIE→DNI** | d16d329 | `nombreUsuarioActualizado.html` portada (saludo con nombre/apellidos, "su correo {email} NO cambia durante este curso", enlace a soporte); los contextos pasan `nombre`/`apellidos`/`email` | ✅ |
| 5.3 | **Aviso con plantilla Jinja2** | d16d329 | Pendiente del lote 3 (la plantilla actual ya usa el contenido de curso2627 adaptado a `str.format` escapado) | ⬜ |

## Ya cubierto en v0.3 — no portar

| Mejora curso2627 | Por qué no aplica |
|------------------|-------------------|
| Cola de emails en disco (a9fc6dd/ab9f18d) | Equivalente funcional: `EmailQueueRepository` + `EmailQueueProcessor` |
| Separación encolado/envío | Ya existe vía `email_mode` (`direct`/`queue`) |
| Generalización del cambio de documento (31a6b83, parte id_sigad) | `_find_username_changes` ya cruza por `id_sigad` sin validar formato NIE/DNI |
| Usuario en minúsculas en avisos (fc9a148) | `username_moodle` ya devuelve minúsculas; el analyzer normaliza |
| Timeout en llamadas a SIGAD (77e6352) | `api_timeout` configurable con reintentos y `APITimeoutError` |
| Fix confusión email/email_sigad (d57cabf) | `EmailChangeDelta` compara campos explícitos; el applier solo toca el custom field |
| Destinatario del aviso NIE→DNI al email de SIGAD (d16d329) | `enviar_actualizacion_usuario` ya envía a `alumno.email` (SIGAD) |
| **Email corporativo no repetido (14d7870)** | **No aplica al esquema actual**: el email `{documento}@dominio` es único y `_find_new_users` ya excluye documentos existentes. 🟡 Solo portar (`get_email_dominio_libre` como función pura en `utils/helpers.py`, alimentada por `MoodleSnapshot`) si v0.3 recupera el esquema `creaEmailsDominio` basado en nombre/apellidos |

---

## Notas transversales para quien ejecute

- **Zipapp**: cualquier plantilla Jinja2 o `logo.png` debe cargarse con
  `importlib.resources` (`PackageLoader`); `FileSystemLoader` falla dentro del
  `.pyz`. Verificar `scripts/build_zipapp.py` para datos binarios.
- **Tests**: suite en verde (129 tests tras la portación). Cada lote
  añadió sus tests (`test_email_queue.py`, `test_sync_analyzer.py`,
  `test_sync_applier.py`, `test_sync_orchestrator.py`).
- **Hallazgos de la revisión de seguridad resueltos en esta portación**:
  fallback de desmatriculación que rematriculaba, apellido corrupto con
  `replace`, escape HTML en el render y SQL interpolado en
  `_find_removed_users`. Ver `docus/revision-seguridad-calidad-v0.3.md`.
- **Orden recomendado restante**: Lote 3 (Jinja2) → tag y merge a `main`.

## Fuentes

Commits de `curso2627` analizados: `a9fc6dd`, `ab9f18d`, `10c4033`,
`24cdac1`, `80896da`, `baa978b`, `c3330bc`, `b30a9b9`, `e7bff6e`, `908c3b8`,
`d80d81b`, `c096a7a`, `14d7870`, `31a6b83`, `d16d329`, `fc9a148`, `77e6352`,
y `d57cabf` (en `main`, previo).
