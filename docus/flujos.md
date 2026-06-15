# Flujos de la Aplicación: Gestión de Alumnos v0.4.1

Documento que describe los flujos principales del sistema de gestión automática de alumnos entre SIGAD y Moodle.

---

## Índice de Contenidos

- [1. Flujo General de Sincronización (v0.4)](#1-flujo-general-de-sincronización-v04)
- [2. Arquitectura de Capas](#2-arquitectura-de-capas)
- [3. Flujo de Obtención de Datos SIGAD](#3-flujo-de-obtención-de-datos-sigad)
- [4. Flujo de Obtención de Datos Moodle](#4-flujo-de-obtención-de-datos-moodle)
- [5. Flujo de Análisis con DuckDB](#5-flujo-de-análisis-con-duckdb)
- [6. Flujo de Aplicación de Cambios](#6-flujo-de-aplicación-de-cambios)
- [7. Flujo de Selección del Driver Moodle](#7-flujo-de-selección-del-driver-moodle)
- [8. Flujo de Envío de Emails](#8-flujo-de-envío-de-emails)
- [9. Diagrama de Dependencias entre Módulos](#9-diagrama-de-dependencias-entre-módulos)
- [Resumen de Comandos CLI](#resumen-de-comandos-cli)
- [Estados del SyncReport](#estados-del-syncreport)

---

## 1. Flujo General de Sincronización (v0.4)

Flujo completo desde la invocación CLI hasta la generación del informe final.

```mermaid
flowchart TD
    subgraph CLI["CLI Entrypoint"]
        A[Usuario ejecuta<br/>gestion-alumnos sync] --> B{Parsear argumentos}
        B --> C[Cargar Settings<br/>desde .env]
        C --> D[Configurar Logging]
    end

    subgraph DI["Dependency Injection"]
        D --> E[DIContainer]
        E --> E1[EstudianteRepository<br/>SIGADRepository]
        E --> E2[MoodleSource<br/>API Course-based o Snapshot]
        E --> E3[MoodleSink<br/>API o Moosh]
        E --> E4[EmailRepository<br/>Directo o Queue]
        E --> F[SyncOrchestrator]
    end

    subgraph EXTRACT["Extracción"]
        F --> G1[Obtener Registro SIGAD]
        F --> G2[Obtener Snapshot Moodle<br/>via MoodleSource.extract_all]
    end

    subgraph ANALYZE["Análisis (DuckDB)"]
        G1 & G2 --> H[SyncAnalyzer]
        H --> H1[Cargar SIGAD en tabla sigad_users]
        H --> H2[Cargar Moodle en tabla moodle_users]
        H1 & H2 --> H3[Ejecutar queries SQL<br/>JOINs / LEFT JOINs]
        H3 --> H4[Generar SyncReport]
    end

    subgraph APPLY["Aplicación (opcional)"]
        H4 --> I{¿dry-run?}
        I -->|Sí| J[Skip aplicación]
        I -->|No| K[SyncApplier]
        K --> K1[Crear usuarios nuevos]
        K --> K2[Actualizar emails/nombres]
        K --> K3[Matricular/desmatricular]
        K --> K4[Suspender bajas]
    end

    subgraph OUT["Salida"]
        J & K4 --> L[Generar SyncReport Markdown]
        L --> M[Log resumen + Informe .md]
        M --> N[Retornar código<br/>de salida 0/1]
    end

    style CLI fill:#e1f5fe
    style DI fill:#fff3e0
    style EXTRACT fill:#e8f5e9
    style ANALYZE fill:#fff8e1
    style APPLY fill:#fce4ec
    style OUT fill:#f3e5f5
```

---

## 2. Arquitectura de Capas

Diagrama de la estructura de capas del sistema y sus dependencias.

```mermaid
flowchart TB
    subgraph CapaPresentacion["Capa de Presentación (CLI)"]
        CLI_MOD["cli.py<br/>ArgumentParser + main()"]
    end

    subgraph CapaAplicacion["Capa de Aplicación (Servicios)"]
        ORC["SyncOrchestrator<br/>Coordina 4 capas"]
        ANA["SyncAnalyzer<br/>DuckDB in-memory"]
        APP["SyncApplier<br/>Aplica cambios"]
        RES["SyncReport<br/>Deltas detectados"]
    end

    subgraph CapaDominio["Capa de Dominio (Modelos)"]
        MOD1["Alumno / Registro"]
        MOD2["MoodleSnapshot"]
        MOD3["MoodleUserRecord / MoodleEnrolmentRecord"]
        MOD4["SyncReport / Deltas"]
    end

    subgraph CapaInfraestructura["Capa de Infraestructura (Repositories)"]
        REP1["SIGADRepository"]
        REP2["MoodleSource<br/>APICourseBased / APISnapshot"]
        REP3["MoodleSink<br/>APIMoodleRepository / MooshMoodleRepository"]
        REP4["EmailRepositoryImpl"]
        REP5["EmailQueueRepository"]
    end

    subgraph CapaCore["Capa Core (Transversal)"]
        CFG["Settings (Pydantic)"]
        LOG["Logging"]
        EXC["Excepciones custom"]
        CON["DIContainer"]
    end

    CLI_MOD --> ORC
    ORC --> ANA
    ORC --> APP
    ANA --> MOD4
    APP --> REP3
    ORC --> REP1
    ORC --> REP2
    ORC --> REP4
    ORC --> REP5

    ANA --> MOD1
    ANA --> MOD2
    ANA --> MOD3

    CON --> CFG
    CON --> REP1
    CON --> REP2
    CON --> REP3
    CON --> REP4
    CON --> ORC

    CLI_MOD --> CON
    CLI_MOD --> CFG
    CLI_MOD --> LOG

    style CapaPresentacion fill:#e3f2fd
    style CapaAplicacion fill:#e8f5e9
    style CapaDominio fill:#fff8e1
    style CapaInfraestructura fill:#fce4ec
    style CapaCore fill:#f3e5f5
```

---

## 3. Flujo de Obtención de Datos SIGAD

Detalle del proceso de descarga desde la API de SIGAD, incluyendo reintentos y modos de operación.

```mermaid
flowchart TD
    A[obtener_registro] --> B{¿is_test?}
    B -->|Sí| C[Cargar desde<br/>tests/data/test_estudiantes_data.json]
    B -->|No| D[_descargar_desde_api]

    D --> E{¿Credenciales<br/>configuradas?}
    E -->|No| F[Lanzar APIError]
    E -->|Sí| G[_solicitar_datos]

    G --> H[POST /solicitud/{año}]
    H --> I{Respuesta}
    I -->|Timeout| J[Lanzar APITimeoutError]
    I -->|Error HTTP| K[Lanzar APIError]
    I -->|codigo != 0| L[Lanzar APIError]
    I -->|codigo == 0| M[Extraer idSolicitud]

    M --> N[Esperar 3s]
    N --> O[_obtener_estudiantes_con_reintentos]

    O --> P[GET /fichero/{idSolicitud}]
    P --> Q{Intento N/M}
    Q -->|Timeout| R{¿Último intento?}
    R -->|Sí| S[Lanzar APITimeoutError]
    R -->|No| T[Esperar delay] --> P
    Q -->|codigo == 0| U[Parsear JSON] --> V[_guardar_copia_local]
    Q -->|codigo == -1| W{¿Último intento?}
    W -->|Sí| X[Lanzar APIError]
    W -->|No| Y[Esperar delay] --> P
    Q -->|Otro error| Z[Lanzar APIError]

    V --> AA[Guardar en data/estudiantes_{id}.json]
    AA --> AB{¿is_produccion?}
    AB -->|Sí| AC[_limpiar_archivos_antiguos]
    AB -->|No| AD[Retornar Registro]
    AC --> AD

    C --> AD

    style A fill:#e3f2fd
    style AD fill:#c8e6c9
    style F fill:#ffcdd2
    style J fill:#ffcdd2
    style K fill:#ffcdd2
    style L fill:#ffcdd2
    style S fill:#ffcdd2
    style X fill:#ffcdd2
    style Z fill:#ffcdd2
```

---

## 4. Flujo de Obtención de Datos Moodle

### Opción A: API Course-based (~1000 llamadas)

```mermaid
flowchart TD
    A[MoodleSource.extract_all] --> B[extract_users]
    A --> C[extract_courses]
    A --> D[extract_enrolments]

    B --> B1[core_user_get_users<br/>1 llamada]
    C --> C1[core_course_get_courses<br/>1 llamada]
    D --> D1[Por cada curso]
    D1 --> D2[core_enrol_get_enrolled_users<br/>~1000 llamadas]
    D2 --> D3[Acumular en lista<br/>de matriculaciones]

    B1 & C1 & D3 --> E[Construir MoodleSnapshot]

    style A fill:#e3f2fd
    style E fill:#c8e6c9
    style D1 fill:#fff8e1
```

### Opción B: API Snapshot (1 llamada, requiere plugin)

```mermaid
flowchart TD
    A[MoodleSource.extract_all] --> B[local_fparagon_get_snapshot<br/>1 llamada]
    B --> C{¿Plugin instalado?}
    C -->|Sí| D[Parsear JSON<br/>usuarios + matriculas]
    C -->|No| E[Lanzar MoodleError]
    D --> F[Construir MoodleSnapshot]

    style A fill:#e3f2fd
    style F fill:#c8e6c9
    style E fill:#ffcdd2
```

---

## 5. Flujo de Análisis con DuckDB

```mermaid
flowchart TD
    A[SyncAnalyzer.__init__] --> B[_cargar_sigad]
    A --> C[_cargar_moodle]

    B --> B1[Crear DataFrame<br/>sigad_users + sigad_enrolments]
    B1 --> B2[CREATE TABLE ... AS SELECT * FROM df]

    C --> C1[Crear DataFrame<br/>moodle_users + moodle_enrolments]
    C1 --> C2[CREATE TABLE ... AS SELECT * FROM df]

    B2 & C2 --> D[analyze]

    D --> E1[_find_new_users<br/>LEFT JOIN WHERE moodle.id IS NULL]
    D --> E2[_find_removed_users<br/>LEFT JOIN WHERE sigad.documento IS NULL]
    D --> E3[_find_email_changes<br/>JOIN WHERE email difiere]
    D --> E4[_find_name_changes<br/>JOIN WHERE nombre difiere]
    D --> E5[_find_username_changes<br/>JOIN por IdSIGAD WHERE username cambia]
    D --> E6[_find_new_enrolments<br/>LEFT JOIN WHERE moodle.course IS NULL]
    D --> E7[_find_removed_enrolments<br/>LEFT JOIN WHERE sigad.modulo IS NULL]

    E1 & E2 & E3 & E4 & E5 & E6 & E7 --> F[Construir SyncReport]

    style A fill:#e3f2fd
    style F fill:#c8e6c9
    style D fill:#fff8e1
```

---

## 6. Flujo de Aplicación de Cambios

```mermaid
flowchart TD
    A[SyncApplier.apply] --> B[_apply_new_users]
    B --> B1[Crear usuario en Moodle<br/>generar password aleatorio + customfields<br/>IdSIGAD, tipoDocumento, emailsigad, consentimientoCDD]
    B1 --> B2[Matricular en cohorte alumnado]

    B2 --> C[_apply_email_changes]
    C --> C1[update_user_email]

    C1 --> D[_apply_name_changes]
    D --> D1[update_user<br/>firstname + lastname]

    D1 --> E[_apply_username_changes]
    E --> E1[update_user_username<br/>NIE → DNI]

    E1 --> F[_apply_new_enrolments]
    F --> F1[enrol_user_to_course<br/>usar mapping shortname→course_id]

    F1 --> G[_apply_removed_enrolments]
    G --> G1[suspend_enrolment<br/>o desmatricular si no disponible]

    G1 --> H[_apply_removed_users]
    H --> H1[suspend_user]

    style A fill:#e3f2fd
    style B fill:#e8f5e9
    style F fill:#e8f5e9
    style G fill:#fff8e1
    style H fill:#ffcdd2
```

---

## 7. Flujo de Selección del Driver Moodle

```mermaid
flowchart TD
    A[DIContainer] --> B{settings.moodle_driver}
    B -->|api| C[APIMoodleRepository]
    B -->|moosh| D[MooshMoodleRepository]

    A --> E{settings.moodle_source_strategy}
    E -->|api-course-based| F[APICourseBasedMoodleSource]
    E -->|api-snapshot| G[APISnapshotMoodleSource]

    C & F & G --> H[SyncOrchestrator]

    style A fill:#e3f2fd
    style C fill:#e8f5e9
    style D fill:#e8f5e9
    style F fill:#fff8e1
    style G fill:#fff8e1
```

---

## 8. Flujo de Envío de Emails

### Modo Directo (SMTP inmediato)

```mermaid
flowchart TD
    A[enviar_bienvenida_nuevo_usuario] --> B[_cargar_template<br/>nuevoUsuario.html]
    B --> C[Reemplazar placeholders<br/>nombre, apellidos, usuario, contraseña, módulos]

    C --> D[_enviar destinatario, asunto, contenido]
    D --> E[_verificar_limite]
    E --> F{¿emails_enviados<br/>>= limite?}
    F -->|Sí| G[Lanzar EmailLimitExceeded]
    F -->|No| H[_get_destinatario]

    H --> I{¿subdomain == www?}
    I -->|Sí| J[Usar email_real]
    I -->|No| K[Redirigir a<br/>gestion@fpvirtualaragon.es]

    J --> L[Crear MIMEMultipart HTML]
    K --> L
    L --> M[Conectar SMTP<br/>starttls + login]
    M --> N[send_message]
    N --> O[Incrementar emails_enviados]
    O --> P[Log info]
    P --> Q[Retornar True]

    G --> R[No enviar]
    M -->|Error| S[Incrementar emails_no_enviados]
    S --> T[Lanzar EmailError]

    style A fill:#e3f2fd
    style Q fill:#c8e6c9
    style G fill:#ffcdd2
    style T fill:#ffcdd2
```

Cuando `EMAIL_MODE=queue`, los emails no se envían por SMTP inmediatamente. En su lugar se escriben en `csvs/email_queue.csv` y se procesan posteriormente con el comando `process-emails`.

```mermaid
flowchart TD
    A[enviar_bienvenida_nuevo_usuario] --> B[_cargar_template<br/>nuevoUsuario.html]
    B --> C[Reemplazar placeholders]
    C --> D[Crear EmailJob]
    D --> E[Serializar a CSV<br/>csvs/email_queue.csv]
    E --> F[Log: Email encolado]
    F --> G[Retornar True]

    style A fill:#e3f2fd
    style G fill:#c8e6c9
```

### Modo Cola (CSV para procesamiento externo)

```mermaid
flowchart TD
    A[enviar_bienvenida_nuevo_usuario] --> B[_cargar_template<br/>nuevoUsuario.html]
    B --> C[Reemplazar placeholders<br/>nombre, apellidos, usuario, contraseña, módulos]

    C --> D[_enviar destinatario, asunto, contenido]
    D --> E[_verificar_limite]
    E --> F{¿emails_enviados<br/>>= limite?}
    F -->|Sí| G[Lanzar EmailLimitExceeded]
    F -->|No| H[_get_destinatario]

    H --> I{¿subdomain == www?}
    I -->|Sí| J[Usar email_real]
    I -->|No| K[Redirigir a<br/>gestion@fpvirtualaragon.es]

    J --> L[Crear MIMEMultipart HTML]
    K --> L
    L --> M[Conectar SMTP<br/>starttls + login]
    M --> N[send_message]
    N --> O[Incrementar emails_enviados]
    O --> P[Log info]
    P --> Q[Retornar True]

    G --> R[No enviar]
    M -->|Error| S[Incrementar emails_no_enviados]
    S --> T[Lanzar EmailError]

    style A fill:#e3f2fd
    style Q fill:#c8e6c9
    style G fill:#ffcdd2
    style T fill:#ffcdd2
```

---

### Flujo de Procesamiento de Cola (process-emails)

```mermaid
flowchart TD
    A[process-emails CLI] --> B[EmailQueueProcessor]
    B --> C[obtener_pendientes]
    C --> D{¿Hay pendientes?}
    D -->|No| E[Log: cola vacía]
    D -->|Sí| F[Iterar EmailJobs]

    F --> G{¿limite alcanzado?}
    G -->|Sí| H[Skip resto<br/>saltados++]
    G -->|No| I[Cargar template HTML]
    I --> J[Renderizar con datos]
    J --> K[EmailRepositoryImpl._enviar]
    K --> L{¿Éxito?}
    L -->|Sí| M[actualizar_estado → sent]
    L -->|No| N[actualizar_estado → failed]

    M --> O[enviados++]
    N --> P[fallidos++]
    H --> Q[Fin iteración]
    O --> Q
    P --> Q

    Q --> R[Log estadísticas]

    style A fill:#e3f2fd
    style R fill:#c8e6c9
    style M fill:#c8e6c9
    style N fill:#ffcdd2
```

## 9. Diagrama de Dependencias entre Módulos

```mermaid
graph LR
    subgraph Models
        A1[Alumno]
        A2[Registro]
        A3[MoodleSnapshot]
        A4[SyncReport]
    end

    subgraph Core
        B1[Settings]
        B2[DIContainer]
        B3[Logging]
        B4[Exceptions]
    end

    subgraph Repositories
        C1[SIGADRepository]
        C2[MoodleSource]
        C3[MoodleSink]
        C4[EmailRepositoryImpl]
        C5[EmailQueueRepository]
        C6[Protocols]
    end

    subgraph Services
        D1[SyncOrchestrator]
        D2[SyncAnalyzer]
        D3[SyncApplier]
        D4[GestionAlumnosService]
    end

    subgraph CLI
        E1[cli.py]
    end

    C1 --> A2
    C2 --> A3
    C3 --> A1
    C4 --> A1
    C5 --> A1

    D2 --> A2
    D2 --> A3
    D2 --> A4
    D3 --> A4
    D3 --> C3

    D1 --> C1
    D1 --> C2
    D1 --> D2
    D1 --> D3

    E1 --> B1
    E1 --> B2
    E1 --> D1

    B2 --> C1
    B2 --> C2
    B2 --> C3
    B2 --> C4
    B2 --> C5
    B2 --> D1

    style Models fill:#fff8e1
    style Core fill:#f3e5f5
    style Repositories fill:#fce4ec
    style Services fill:#e8f5e9
    style CLI fill:#e3f2fd
```

---

## Resumen de Comandos CLI

| Comando | Descripción | Estado |
|---------|-------------|--------|
| `sync` | Analizar diferencias (dry-run por defecto) | ✅ v0.4 |
| `sync --apply` | Aplicar cambios en Moodle | ✅ v0.4 |
| `sync --source-strategy api-snapshot` | Usar plugin PHP para extracción | ✅ v0.4 |
| `report` | Generar informe sin modificar datos | ✅ v0.4 |
| `process-emails` | Enviar emails pendientes de la cola CSV | ✅ v0.4.1 |
| `extract` | Extraer alumnado a CSV | Pendiente |

---

## Estados del SyncReport

| Delta | Descripción |
|-------|-------------|
| `new_users` | Alumnos en SIGAD que no existen en Moodle (altas) |
| `removed_users` | Usuarios en Moodle que no están en SIGAD (bajas) |
| `email_changes` | Emails diferentes entre SIGAD y Moodle |
| `name_changes` | Nombre o apellidos diferentes |
| `username_changes` | Cambio de documento/username (ej: NIE→DNI) |
| `new_enrolments` | Matrículas en SIGAD no presentes en Moodle |
| `removed_enrolments` | Matrículas en Moodle no presentes en SIGAD |
