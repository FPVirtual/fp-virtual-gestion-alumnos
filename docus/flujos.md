# Flujos de la Aplicación: Gestión de Alumnos

Documento que describe los flujos principales del sistema de gestión automática de alumnos entre SIGAD y Moodle.

---

## Índice de Contenidos

- [1. Flujo General de Sincronización](#1-flujo-general-de-sincronización)
- [2. Arquitectura de Capas](#2-arquitectura-de-capas)
- [3. Flujo de Obtención de Datos SIGAD](#3-flujo-de-obtención-de-datos-sigad)
- [4. Flujo de Procesamiento de un Alumno](#4-flujo-de-procesamiento-de-un-alumno)
- [5. Flujo de Selección del Driver Moodle](#5-flujo-de-selección-del-driver-moodle)
- [6. Flujo de Envío de Emails](#6-flujo-de-envío-de-emails)
- [7. Flujo de Suspensión de Bajas](#7-flujo-de-suspensión-de-bajas)
- [8. Diagrama de Dependencias entre Módulos](#8-diagrama-de-dependencias-entre-módulos)
- [Resumen de Comandos CLI](#resumen-de-comandos-cli)
- [Estados del ResultadoSync](#estados-del-resultadosync)

---

## 1. Flujo General de Sincronización

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
        E --> E2[MoodleRepository<br/>API o Moosh]
        E --> E3[EmailRepository<br/>SMTP opcional]
        E --> F[GestionAlumnosService]
    end

    subgraph SYNC["Sincronización"]
        F --> G1[Obtener Registro SIGAD]
        G1 --> G2[Obtener Usuarios Moodle]
        G2 --> H{Por cada alumno}
        H --> I{¿Usuario existe<br/>en Moodle?}
        I -->|No| J[Crear Usuario]
        I -->|Sí| K[Actualizar Usuario]
        J --> L[Matricular en Cursos]
        K --> L
        L --> M[Matricular en Cohorte<br/>alumnado]
        J --> N{¿Email config<br/>y límite ok?}
        N -->|Sí| O[Enviar email<br/>de bienvenida]
        N -->|No| P[Skip email]
        H --> Q[Suspender bajas]
    end

    subgraph OUT["Salida"]
        Q --> R[Generar ResultadoSync]
        R --> S[Log resumen Markdown]
        S --> T[Retornar código<br/>de salida 0/1]
    end

    style CLI fill:#e1f5fe
    style DI fill:#fff3e0
    style SYNC fill:#e8f5e9
    style OUT fill:#fce4ec
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
        SVC["GestionAlumnosService<br/>Orquesta sincronización"]
        RES["ResultadoSync<br/>Métricas y resumen"]
    end

    subgraph CapaDominio["Capa de Dominio (Modelos)"]
        MOD1["Alumno"]
        MOD2["Registro"]
        MOD3["Centro / Ciclo / Modulo"]
    end

    subgraph CapaInfraestructura["Capa de Infraestructura (Repositories)"]
        REP1["SIGADRepository<br/>API REST + cache"]
        REP2["APIMoodleRepository<br/>Moodle REST API"]
        REP3["MooshMoodleRepository<br/>Comandos moosh"]
        REP4["EmailRepositoryImpl<br/>SMTP + templates HTML"]
    end

    subgraph CapaCore["Capa Core (Transversal)"]
        CFG["Settings (Pydantic)"]
        LOG["Logging"]
        EXC["Excepciones custom"]
        CON["DIContainer"]
    end

    CLI_MOD --> SVC
    SVC --> MOD1
    SVC --> MOD2
    SVC --> REP1
    SVC --> REP2
    SVC --> REP3
    SVC --> REP4
    SVC --> RES

    REP1 --> MOD2
    REP2 --> MOD1
    REP3 --> MOD1
    REP4 --> MOD1

    CON --> CFG
    CON --> REP1
    CON --> REP2
    CON --> REP3
    CON --> REP4
    CON --> SVC

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

## 4. Flujo de Procesamiento de un Alumno

Decisiones tomadas para cada alumno durante la sincronización.

```mermaid
flowchart TD
    A[_procesar_alumno<br/>alumno] --> B[username = alumno.documento.lower]
    B --> C{moodle_repo<br/>.usuario_existe?}

    C -->|No| D[_crear_usuario]
    C -->|Sí| E[_actualizar_usuario]

    D --> D1[Generar password<br/>aleatorio 10 chars]
    D1 --> D2[moodle_repo.crear_usuario<br/>username, email, nombre, apellido, password]
    D2 --> D3{¿Éxito?}
    D3 -->|Sí| D4[Incrementar nuevos_creados]
    D3 -->|No| D5[Registrar error]
    D4 --> D6[Matricular en cohorte<br/>alumnado]
    D6 --> D7{¿Email repo<br/>y límite ok?}
    D7 -->|Sí| D8[email_repo.enviar_bienvenida_nuevo_usuario<br/>alumno, password, modulos]
    D8 --> D9{¿Éxito?}
    D9 -->|Sí| D10[Incrementar emails_enviados]
    D9 -->|No| D11[Incrementar emails_fallidos]
    D7 -->|No| D12[Skip email]

    E --> E1[Comparar campos<br/>SIGAD vs Moodle]
    E1 --> E2{¿Cambios?}
    E2 -->|Sí| E3[Actualizar campos<br/>email, username, etc.]
    E2 -->|No| E4[Skip actualización]

    D12 --> F
    D10 --> F
    D11 --> F
    D5 --> F
    E3 --> F
    E4 --> F

    F[Por cada módulo del alumno] --> G[moodle_repo.matricular_en_curso<br/>username, modulo.siglas]
    G --> H{¿Éxito?}
    H -->|Sí| I[Incrementar matriculas_creadas]
    H -->|No| J[Log warning]

    style A fill:#e3f2fd
    style D fill:#e8f5e9
    style E fill:#fff8e1
    style D10 fill:#c8e6c9
    style D11 fill:#ffcdd2
    style D5 fill:#ffcdd2
```

---

## 5. Flujo de Selección del Driver Moodle

El sistema soporta dos drivers para Moodle: API REST y Moosh. Este flujo muestra cómo se selecciona e instancia el repositorio adecuado.

```mermaid
flowchart TD
    A[DIContainer.moodle_repository] --> B{¿_moodle_repo<br/>ya existe?}
    B -->|Sí| C[Retornar instancia cacheada]
    B -->|No| D{settings<br/>.moodle_driver}

    D -->|api| E[Crear APIMoodleRepository]
    D -->|moosh| F[Crear MooshMoodleRepository]

    E --> E1{¿URL y Token<br/>configurados?}
    E1 -->|No| E2[Lanzar MoodleError]
    E1 -->|Sí| E3[Instanciar con requests.Session]
    E3 --> C

    F --> F1[Instanciar con<br/>settings.moosh_path]
    F1 --> C

    subgraph APIMoodle["APIMoodleRepository"]
        API1["_call wsfunction<br/>POST wstoken + wsfunction"]
        API2["usuario_existe<br/>get_users_by_field / get_users"]
        API3["crear_usuario<br/>core_user_create_users"]
        API4["suspender_usuario<br/>core_user_update_users suspended=1"]
        API5["matricular_en_curso<br/>enrol_manual_enrol_users"]
        API6["matricular_en_cohorte<br/>cohort_add_cohort_members"]
    end

    subgraph MooshMoodle["MooshMoodleRepository"]
        MOO1["_run comando<br/>subprocess moosh / docker exec"]
        MOO2["usuario_existe<br/>user-get username"]
        MOO3["crear_usuario<br/>user-create --username ..."]
        MOO4["suspender_usuario<br/>user-mod --suspend 1"]
        MOO5["matricular_en_curso<br/>course-enrol --user ..."]
        MOO6["matricular_en_cohorte<br/>cohort-enrol cohorte username"]
    end

    E3 --> APIMoodle
    F1 --> MooshMoodle

    style APIMoodle fill:#e8f5e9
    style MooshMoodle fill:#fff8e1
    style E2 fill:#ffcdd2
```

---

## 6. Flujo de Envío de Emails

Proceso de notificación a los usuarios recién creados, con control de límites y templates HTML.

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

## 7. Flujo de Suspensión de Bajas

Al finalizar la sincronización, se suspenden los usuarios de Moodle que ya no están en SIGAD.

```mermaid
flowchart TD
    A[_suspender_bajas<br/>registro, usuarios_moodle] --> B[documentos_sigad =<br/>set de alumno.documento.lower]

    B --> C[Por cada usuario en Moodle]
    C --> D{user_id en<br/>USUARIOS_PROTEGIDOS?}
    D -->|Sí| E[Skip usuario protegido]
    D -->|No| F{username en<br/>documentos_sigad?}

    F -->|Sí| G[Usuario activo,<br/>no hacer nada]
    F -->|No| H[moodle_repo<br/>.suspender_usuario]
    H --> I{¿Éxito?}
    I -->|Sí| J[Incrementar suspendidos]
    I -->|No| K[Log warning]

    E --> C
    G --> C
    J --> C
    K --> C

    C --> L[Fin del loop]

    style A fill:#e3f2fd
    style J fill:#c8e6c9
    style K fill:#ffcdd2
```

---

## 8. Diagrama de Dependencias entre Módulos

Vista general de imports y relaciones entre los paquetes Python.

```mermaid
graph LR
    subgraph Models
        A1[Alumno]
        A2[Registro]
        A3[Centro]
        A4[Ciclo]
        A5[Modulo]
    end

    subgraph Core
        B1[Settings]
        B2[DIContainer]
        B3[Logging]
        B4[Exceptions]
    end

    subgraph Repositories
        C1[SIGADRepository]
        C2[APIMoodleRepository]
        C3[MooshMoodleRepository]
        C4[EmailRepositoryImpl]
        C5[Protocols]
    end

    subgraph Services
        D1[GestionAlumnosService]
        D2[ResultadoSync]
    end

    subgraph CLI
        E1[cli.py]
    end

    C1 --> A2
    C1 --> B1
    C1 --> B3
    C1 --> B4

    C2 --> B1
    C2 --> B3
    C2 --> B4
    C2 --> C5

    C3 --> B1
    C3 --> B3
    C3 --> B4
    C3 --> C5

    C4 --> A1
    C4 --> B1
    C4 --> B3
    C4 --> B4

    D1 --> A1
    D1 --> A2
    D1 --> C5
    D1 --> B1
    D1 --> B3
    D1 --> D2

    E1 --> B1
    E1 --> B2
    E1 --> B3
    E1 --> D1

    B2 --> B1
    B2 --> C1
    B2 --> C2
    B2 --> C3
    B2 --> C4
    B2 --> D1

    A2 --> A1
    A1 --> A3
    A3 --> A4
    A4 --> A5

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
| `sync` | Sincronización completa SIGAD → Moodle | Implementado |
| `sync --desde-fichero` | Sincronización desde JSON local | Implementado |
| `extract` | Extraer alumnado a CSV | Pendiente |
| `report` | Generar informe sin modificar datos | Pendiente |

---

## Estados del ResultadoSync

| Métrica | Descripción |
|---------|-------------|
| `alumnos_sigad` | Total de alumnos en el registro SIGAD |
| `alumnos_moodle` | Total de usuarios existentes en Moodle |
| `nuevos_creados` | Usuarios nuevos creados en Moodle |
| `suspendidos` | Usuarios suspendidos (bajas) |
| `reactivados` | Usuarios reactivados |
| `emails_actualizados` | Emails modificados |
| `usernames_actualizados` | Usernames modificados |
| `matriculas_creadas` | Matrículas en cursos realizadas |
| `matriculas_suspendidas` | Matrículas suspendidas |
| `emails_enviados` | Emails de bienvenida enviados |
| `emails_fallidos` | Emails que fallaron |
| `errores` | Lista de mensajes de error |
