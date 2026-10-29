# Ramas del proyecto: diferencias, mejoras y grado de avance

> Análisis realizado el 2026-10-28 sobre el repositorio
> `fp-virtual-gestion-alumnos` (remoto: `Campus-Digital-FP/fp-virtual-gestion-alumnos`).
>
> **Nota (2026-10-28):** las ramas cerradas o abandonadas (`v0.1`,
> `v0.1.1` y `v0.2`) fueron eliminadas en local y en remoto tras este
> análisis. Esta tabla queda como registro histórico; sus commits únicos
> no fusionados quedaron huérfanos (recuperables temporalmente vía reflog
> en local hasta que expire).

## Resumen ejecutivo

El repositorio convive con **dos líneas evolutivas que divergen desde `main`**:

1. **Línea legacy (scripts sueltos):** `main` → `curso2627`. Es la versión que
   históricamente ha estado en producción y la que sigue recibiendo arreglos
   funcionales puntuales (rama más activa: último commit el 2026-10-01).
2. **Línea de refactor (paquete Python):** `v0.1` → `v0.1.1` / `v0.2` →
   `v0.3-estructura-paquete-con-logs` (rama de trabajo actual). Reescritura
   completa con arquitectura por capas, inyección de dependencias, tests y
   empaquetado zipapp.

Las ramas `v0.1.1` y `v0.2` son ramas de trabajo intermedio ya concluidas o
abandonadas; su valor está en el código que `v0.3` reutilizó de ellas.

| Rama | Último commit | Estado | Rol |
|------|---------------|--------|-----|
| `main` | 2026-05-29 | Estable (legacy) | Versión monolítica original |
| `curso2627` | 2026-10-01 | **Activa** | Evolución de la legacy con fixes de producción 26/27 |
| `v0.1-gestion-alumnos` | 2026-02-21 | Cerrada | Base del refactor a paquete |
| `v0.1.1-optimización-de-consultas-con-SQLAlchemy` | 2025-12-18 | Abandonada | Experimento SQLAlchemy / moosh |
| `v0.2-gestion-alumnos-actualizacionIA` | 2026-06-04 | Cerrada ("FIN RAMA") | Tests y tooling de testing de BD |
| `v0.3-estructura-paquete-con-logs` | 2026-06-23 | **Activa (actual)** | Refactor completo, roadmap v0.4.1 terminado |

---

## `main` — versión legacy

**Estructura:** scripts sueltos en la raíz (`main.py`, `Conexion.py`,
`Util.py`, `classes/`, `templates/`, `extrae_alumnado.sh`).

**Qué es:** el programa monolítico original (desde 2021) que sincroniza
alumnado de SIGAD con Moodle creando usuarios, matrículas e informes por
correo. Toda la lógica está en `main.py` (~600 líneas) con acceso directo a
MySQL mediante `subprocess`/`pymysql`.

**Mejoras aportadas sobre el origen:** es la referencia. Recibió sobre todo
reverts y ajustes del comportamiento de envío de correos (desactivar avisos de
matrículas añadidas, corrección de emails).

**Grado de avance:** funcional y en producción, pero con deuda técnica alta
(sin tests, configuración por `Config.py` editado a mano, acoplamiento total a
la BD de Moodle). Sirve de base desde la que divergen todas las demás ramas.

---

## `curso2627` — evolución funcional de la legacy

**Estructura:** misma disposición de scripts sueltos que `main` (más
`enviar_correos.py`, `samples/`, `CLAUDE.md`).

**Diferencias con `main`** (~300 600 líneas añadidas, principalmente datos de
prueba anonimizados en `samples/`):

- **Aviso de cambio NIE → DNI** al email de SIGAD, con usuario en minúsculas y
  más información en el mensaje.
- **Cambio de usuario ante cualquier cambio de documento** en SIGAD.
- **Email corporativo no repetido** al crear alumnos.
- **Timeout en las llamadas a SIGAD** y parada del proceso si no devuelve
  alumnos (antes seguía con datos incompletos).
- Informes en `logs/<SUBDOMAIN>/md` y **fechas unificadas** en nombres de
  archivo.
- Separación del envío de correos en `enviar_correos.py`, plantillas
  refactorizadas con `base.html`, logo añadido.

**Grado de avance:** es la rama **más reciente y activa del repositorio**
(commits hasta el 2026-10-01) y concentra los arreglos funcionales que el
centro necesita para el curso 26/27. Sin embargo, mantiene la arquitectura
legacy: sin tests y con la lógica monolítica. **Sus mejoras no están
presentes en `v0.3`** (ambas divergen desde el mismo commit de `main`), lo
que es la principal deuda de integración del proyecto.

---

## `v0.1-gestion-alumnos` — inicio del refactor a paquete

**Estructura:** nace el paquete `gestion_alumnos/` con `pyproject.toml`
(poetry), `tests/`, `data/`, `examples/` y documentación de migración
(`MIGRACION_SINGLE_FILE.md`, `v0.1-README.md`, `ANALISIS_ELEMENTOS_INNECESARIOS.md`).

**Mejoras sobre `main`:**

- Migración del monolito a **estructura de paquete Python** siguiendo buenas
  prácticas (módulos `classes/`, servicios, etc.).
- **Configuración mediante `.env`** en lugar de `Config.py` editado a mano.
- **Primeros tests unitarios** con `pytest` y **datos mock**
  (`test_estudiantes_data.json`) para probar sin tocar SIGAD/Moodle reales.
- Sistema de emails actualizado y limpieza de elementos innecesarios.

**Grado de avance:** fase completa y estable; es la base sobre la que se
apoyaron `v0.2` y, a través de ella, `v0.3`. Ya no recibe commits.

---

## `v0.1.1-optimización-de-consultas-con-SQLAlchemy` — experimento abandonado

**Estructura:** convive lo viejo (`main.py`, `Conexion.py`) con lo nuevo:
`models.py`, módulo `utils/` (`api_client.py`, `json_parser.py`, `moodle.py`,
`moodle_queries.py`, `moosh.py`), `tests/` y `poetry.lock`.

**Mejoras aportadas:**

- Introducción de **SQLAlchemy** para el acceso a datos y de **moosh**
  (CLI de Moodle) como vía de consulta alternativa a los `subprocess` con
  `mysql`.
- Cliente HTTP y parser JSON reutilizables, primeros tests de la API de
  Moodle y registro de datos importados de SIGAD.

**Grado de avance:** **rama abandonada** (último commit el 2025-12-18,
anterior incluso al cierre de `v0.1`). El merge con `v0.1` quedó a medias y
la estructura híbrida vieja/nueva indica trabajo incompleto. Sus ideas
(moosh, parser, tests de Moodle) se recuperaron después en `v0.3`, que optó
por Pydantic + API REST en lugar de SQLAlchemy.

---

## `v0.2-gestion-alumnos-actualizacionIA` — testing y cierre de etapa

**Estructura:** parte de `v0.1` y añade `scripts/db_testing/manual/`
(herramientas para generar casos de prueba en CSV/JSON y queries SQL de
verificación/modificación) y más tests (`test_core_config.py`,
`test_repositories.py`, `test_services.py`), además de `MEJORES_PRACTICAS.md`.

**Mejoras aportadas:**

- **Cobertura de tests ampliada** hacia la capa de servicios y repositorios
  (adiós a testear solo utilidades).
- **Tooling de testing manual contra la base de datos**: plantillas de casos,
  queries de verificación y scripts para generar datos de prueba desde una
  base real.
- Documentación de mejores prácticas.

**Grado de avance:** el propio último commit lo indica — *"FIN RAMA: guardado
de todo para su trabajo posterior"*. Es una **fotografía de trabajo
terminada**, no una entrega. `v0.3` la trató como cantera: su roadmap explicita
que se reutilizaron de aquí `core/logging.py`, `core/exceptions.py`,
`core/config.py`, `models_v2.py` y `protocols.py`.

---

## `v0.3-estructura-paquete-con-logs` — refactor completo (rama actual)

**Estructura:** paquete `gestion_alumnos/` organizado por capas —
`core/` (logging, config, contenedor de inyección de dependencias), `models/`
(Pydantic), `repositories/` (SIGAD, Moosh, **API REST de Moodle**),
`services/` (SyncAnalyzer, SyncOrchestrator, EmailQueue, ReportLogger),
`templates/`, más `tests/` (84 tests), `scripts/build_zipapp.py`,
`dist/gestion_alumnos.pyz` y documentación extensa en `docus/`.

**Mejoras sobre todas las anteriores:**

- **Arquitectura por capas con inyección de dependencias**, eliminando el
  acceso directo a MySQL (se sustituye por moosh / API REST según el driver
  configurado).
- **Sincronización por deltas** con detección de altas/cambios vía IdSIGAD y
  custom fields, orquestada por `SyncOrchestrator` y analizada por
  `SyncAnalyzer` (con documentación y diagramas Mermaid).
- **Sistema de logs e informes estructurado** (`logs/`, ReportLogger) y
  **cola de emails** con plantillas.
- **84 tests pasando** (unitarios e integración MoodleSource + E2E del
  orquestador).
- **Distribución como zipapp** (`dist/gestion_alumnos.pyz`) lista para
  desplegar sin instalar dependencias.
- **Documentación completa**: roadmap versionado (v0.4.1), guías de conexión
  con la API de Moodle, análisis de sincronización y sistema de testing.

**Grado de avance:** según `docus/tareas-y-roadmap.md`, **todas las fases del
roadmap (0–10) están completas**: infraestructura, core, modelos,
repositorios, pipeline de sincronización, reportes, cola de emails, tests,
zipapp y documentación. El refactor es funcional y verificado, pero **no está
en producción** y todavía no ha absorbido las mejoras funcionales de
`curso2627` (avisos NIE→DNI, timeouts de SIGAD, email corporativo, etc.).

---

## Conclusiones y deuda de integración

- **Producción hoy:** la línea `main`/`curso2627` es la que resuelve las
  necesidades reales del curso actual, a costa de mantener el monolito sin
  tests.
- **Futuro técnico:** `v0.3` es claramente la base correcta a largo plazo,
  con arquitectura, tests y distribución resueltos.
- **Pendiente principal:** ambas líneas divergen desde el mismo commit de
  `main` y **no se han reconciliado**. Para consolidar el proyecto habría que
  portar a `v0.3` los cambios funcionales de `curso2627` y las lecciones de
  `v0.1.1`/`v0.2`, y definir `v0.3` como la nueva `main`.
