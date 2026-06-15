# Análisis de Deltas en SyncAnalyzer

Este documento explica paso a paso cómo `SyncAnalyzer` detecta las diferencias entre los datos de SIGAD y los datos de Moodle usando **DuckDB in-memory**. Incluye diagramas de flujo, las queries SQL reales y ejemplos concretos.

---

## Índice

- [Análisis de Deltas en SyncAnalyzer](#análisis-de-deltas-en-syncanalyzer)
  - [Índice](#índice)
  - [Visión General](#visión-general)
  - [Carga de Datos en DuckDB](#carga-de-datos-en-duckdb)
    - [Tablas SIGAD](#tablas-sigad)
    - [Tablas Moodle](#tablas-moodle)
  - [Flujo Completo del Análisis](#flujo-completo-del-análisis)
  - [Listado de Deltas a implementar y cómo se resuelven:](#listado-de-deltas-a-implementar-y-cómo-se-resuelven)
  - [Delta 1: Altas (New Users)](#delta-1-altas-new-users)
    - [Lógica](#lógica)
    - [Diagrama](#diagrama)
    - [Ejemplo](#ejemplo)
  - [Delta 2: Bajas (Removed Users)](#delta-2-bajas-removed-users)
    - [Lógica](#lógica-1)
    - [Diagrama](#diagrama-1)
    - [Ejemplo](#ejemplo-1)
  - [Delta 3: Cambios de Email](#delta-3-cambios-de-email)
    - [Lógica](#lógica-2)
    - [Diagrama](#diagrama-2)
    - [Ejemplo](#ejemplo-2)
  - [Delta 4: Cambios de Nombre/Apellidos](#delta-4-cambios-de-nombreapellidos)
    - [Lógica](#lógica-3)
    - [Diagrama](#diagrama-3)
    - [Ejemplo](#ejemplo-3)
  - [Delta 5: Cambios de Username (NIE → DNI)](#delta-5-cambios-de-username-nie--dni)
    - [Lógica](#lógica-4)
    - [Diagrama](#diagrama-4)
    - [Ejemplo](#ejemplo-4)
  - [Delta 6: Nuevas Matrículas](#delta-6-nuevas-matrículas)
    - [Lógica](#lógica-5)
    - [Diagrama](#diagrama-5)
    - [Ejemplo](#ejemplo-5)
  - [Delta 7: Matrículas Eliminadas](#delta-7-matrículas-eliminadas)
    - [Lógica](#lógica-6)
    - [Diagrama](#diagrama-6)
    - [Ejemplo](#ejemplo-6)
  - [Casos Especiales](#casos-especiales)
    - [Usuarios Protegidos](#usuarios-protegidos)
    - [NIE → DNI](#nie--dni)
  - [Resumen de Tipos de Delta](#resumen-de-tipos-de-delta)
    - [Matriz de decisión](#matriz-de-decisión)
  - [Referencias](#referencias)

---

## Visión General

`SyncAnalyzer` es un servicio puro (sin dependencias de red) que recibe:

- **`Registro`** de SIGAD: lista jerárquica de alumnos → centros → ciclos → módulos
- **`MoodleSnapshot`**: lista plana de usuarios, cursos y matriculaciones de Moodle

Su objetivo es producir un **`SyncReport`** con todos los **deltas** (diferencias) detectados.

```mermaid
flowchart LR
    A[Registro SIGAD] -->|_cargar_sigad| D[DuckDB in-memory]
    B[MoodleSnapshot] -->|_cargar_moodle| D
    D -->|7 queries| C[SyncReport]
```

---

## Carga de Datos en DuckDB

Antes de analizar, el analyzer normaliza ambas fuentes en **4 tablas planas**:

### Tablas SIGAD

| Tabla | Origen | Filas |
|-------|--------|-------|
| `sigad_users` | Un `Alumno` → una fila | `documento`, `id_alumno`, `nombre`, `apellido1`, `apellido2`, `email` |
| `sigad_enrolments` | Un `Alumno` × sus módulos → N filas | `documento`, `codigo_centro`, `siglas_ciclo`, `siglas_modulo` |

### Tablas Moodle

| Tabla | Origen | Filas |
|-------|--------|-------|
| `moodle_users` | Un `MoodleUserRecord` → una fila | `id`, `username`, `email`, `firstname`, `lastname`, `suspended`, `id_sigad`, `email_sigad` |
| `moodle_enrolments` | Un `MoodleEnrolmentRecord` → una fila | `user_id`, `username`, `course_id`, `shortname`, `status` |

> **Nota sobre normalización:** El `documento` de SIGAD se convierte a `UPPERCASE`. El `username` de Moodle se convierte a `lowercase`. Esto permite comparar `78842153Q` (SIGAD) con `78842153q` (Moodle).

```mermaid
flowchart TB
    subgraph SIGAD["📥 SIGAD (jerárquico)"]
        SA[Alumno 78842153Q] --> SC[Centro 50009348]
        SC --> SCI[Ciclo SSC302]
        SCI --> SM1[Módulo IPPE1]
        SCI --> SM2[Módulo PROG]
    end

    subgraph DUCKDB["🦆 DuckDB (plano)"]
        DU["sigad_users<br/>documento=78842153Q<br/>nombre=Valeria<br/>email=valeria@..."]
        DE1["sigad_enrolments<br/>documento=78842153Q<br/>siglas_modulo=IPPE1"]
        DE2["sigad_enrolments<br/>documento=78842153Q<br/>siglas_modulo=PROG"]
    end

    SIGAD -->|_cargar_sigad| DUCKDB
```

---

## Flujo Completo del Análisis

```mermaid
flowchart TD
    Start([analyze]) --> Load[1. Cargar tablas en DuckDB]
    Load --> D1[2. find_new_users]
    D1 --> D2[3. find_removed_users]
    D2 --> D3[4. find_email_changes]
    D3 --> D4[5. find_name_changes]
    D4 --> D5[6. find_username_changes]
    D5 --> D6[7. find_new_enrolments]
    D6 --> D7[8. find_removed_enrolments]
    D7 --> Report[Construir SyncReport]
    Report --> End([return])
```

> **Importante:** Los 7 análisis son **independientes** entre sí. Se ejecutan secuencialmente pero cada uno opera sobre las mismas 4 tablas cargadas inicialmente.

---

## Listado de Deltas a implementar y cómo se resuelven:

> ToDo DARÍO
¿ Qué cambios pueden darse ?

* Altas de nuevos alumnos -> No existe nadie con ese DNI/NIE/Pasaporte
  * Verificamos con IdSIGAD como dato no cambiante
* Un usuario ha cambiado de DNI/NIE/Pasaporte a otro tipo de documento? 
  * ¿Sabemos si el *idAlumno* del json debe ser el mismo?
* Un usuario ha cambiado su nombre, apellidos | mantiene su DNI/NIE/Pasaporte
  * ¿Si cambia de nombre hay que crear un nuevo email de fpvirtualaragon.es?
* Un usuario ha cambiado su email | mantiene su DNI/NIE/Pasaporte
* Un usuario ha cambiado su matrícula (añade o elimina módulos en los que está matriculado) | mantiene DNI/NIE/Pasaporte
* Un usuario ha abandonado la formación (se le debe suspender en módulos y acceso) | mantiene DNI/NIE/Pasaporte
* 
-- Obtengo los alumnos (profesores no) que están suspendidos en moodle y miro si están en el fichero de SIGAD
-- Si están en el fichero de SIGAD los reactivo




## Delta 1: Altas (New Users)

**Definición:** Alumnos que existen en SIGAD pero no tienen usuario en Moodle.

### Lógica

```sql
SELECT s.documento
FROM sigad_users s
LEFT JOIN moodle_users m ON m.username = lower(s.documento)
WHERE m.id IS NULL
```

### Diagrama

```mermaid
flowchart LR
    subgraph SIGAD
        S1["Valeria<br/>documento=78842153Q"]
        S2["Juan<br/>documento=12345678A"]
    end

    subgraph Moodle
        M1["78842153q ✅"]
    end

    S1 -->|LEFT JOIN| M1
    S2 -.->|LEFT JOIN<br/>no encuentra| M1

    style S2 fill:#ffcccc
```

### Ejemplo

| Origen | Documento | ¿En Moodle? | Resultado |
|--------|-----------|-------------|-----------|
| SIGAD | `78842153Q` | Sí (`78842153q`) | — |
| SIGAD | `12345678A` | **No** | ✅ **Alta detectada** |

**Salida:** `NewUserDelta(alumno=Juan)`

---

## Delta 2: Bajas (Removed Users)

**Definición:** Usuarios que existen en Moodle pero no están en SIGAD. Se excluyen los usuarios **protegidos** (admin, guest, etc. cargados desde CSV).

### Lógica

```sql
SELECT m.id, m.username, m.email, m.firstname, m.lastname, m.suspended
FROM moodle_users m
LEFT JOIN sigad_users s ON lower(s.documento) = m.username
WHERE s.documento IS NULL
  AND m.id NOT IN (1, 2, 3, ...)  -- usuarios protegidos
```

### Diagrama

```mermaid
flowchart LR
    subgraph SIGAD
        S1["78842153Q ✅"]
    end

    subgraph Moodle
        M1["78842153q"]
        M2["99999999z"]
        M3["admin<br/>id=2<br/>🛡️ protegido"]
    end

    M1 -->|LEFT JOIN| S1
    M2 -.->|LEFT JOIN<br/>no encuentra| S1
    M3 -.->|protegido| S1

    style M2 fill:#ffcccc
    style M3 fill:#ccffcc
```

### Ejemplo

| Origen | Username | ¿En SIGAD? | ¿Protegido? | Resultado |
|--------|----------|------------|-------------|-----------|
| Moodle | `78842153q` | Sí | — | — |
| Moodle | `99999999z` | **No** | No | ✅ **Baja detectada** |
| Moodle | `admin` | No | **Sí (id=2)** | — |

**Salida:** `RemovedUserDelta(user=MoodleUserRecord(id=102, username="99999999z", ...))`

---

## Delta 3: Cambios de Email

**Definición:** Alumnos cuyo email personal de SIGAD difiere del custom field `emailsigad` de Moodle. El email principal/institucional de Moodle (`documento@fpvirtualaragon.es`) no se sincroniza desde SIGAD.

### Lógica

```sql
SELECT
    s.documento,
    s.email AS email_sigad,
    m.email_sigad AS email_moodle
FROM sigad_users s
JOIN moodle_users m ON lower(s.documento) = m.username
WHERE lower(s.email) <> lower(m.email_sigad)
   OR (s.email IS NOT NULL AND m.email_sigad IS NULL)
   OR (s.email IS NULL AND m.email_sigad IS NOT NULL)
```

### Diagrama

```mermaid
flowchart LR
    subgraph SIGAD
        S1["78842153Q<br/>email: valeria.torres@new.com"]
    end

    subgraph Moodle
        M1["78842153q<br/>email: valeria@old.com"]
    end

    S1 -->|JOIN<br/>mismo documento| M1

    style S1 fill:#ffffcc
    style M1 fill:#ffffcc
```

### Ejemplo

| Documento | Email SIGAD | Email Moodle | ¿Diferente? |
|-----------|-------------|--------------|-------------|
| `78842153Q` | `valeria.torres@new.com` | `valeria@old.com` | ✅ **Sí** |
| `12345678A` | `juan@ejemplo.com` | `juan@ejemplo.com` | No |

**Salida:** `EmailChangeDelta(documento="78842153Q", email_sigad="valeria.torres@new.com", email_moodle="valeria@old.com")`

> **Nota:** `email_moodle` aquí representa el valor del custom field `emailsigad` de Moodle, no el email principal de la cuenta.

---

## Delta 4: Cambios de Nombre/Apellidos

**Definición:** Alumnos cuyo nombre o apellidos difieren entre SIGAD y Moodle. El desafío aquí es que SIGAD tiene `nombre` + `apellido1` + `apellido2` (3 campos) mientras Moodle tiene `firstname` + `lastname` (2 campos).

### Lógica

```sql
SELECT
    s.documento, s.nombre, s.apellido1, s.apellido2,
    m.firstname, m.lastname
FROM sigad_users s
JOIN moodle_users m ON lower(s.documento) = m.username
WHERE s.nombre <> m.firstname
   OR s.apellido1 <> split_part(m.lastname, ' ', 1)
   OR COALESCE(s.apellido2, '') <> trim(
          replace(m.lastname, split_part(m.lastname, ' ', 1), '')
      )
```

### Diagrama

```mermaid
flowchart LR
    subgraph SIGAD
        S1["Valeria<br/>apellido1: Torres<br/>apellido2: Medina"]
    end

    subgraph Moodle
        M1["firstname: Valeria<br/>lastname: Torres"]
        M2["firstname: Valeria<br/>lastname: Torres García"]
    end

    S1 -->|JOIN| M1
    S1 -.->|JOIN<br/>apellido2 ≠ ''| M2

    style S1 fill:#ffffcc
    style M2 fill:#ffcccc
```

### Ejemplo

| Documento | SIGAD | Moodle | ¿Diferente? |
|-----------|-------|--------|-------------|
| `78842153Q` | `Valeria` / `Torres` / `Medina` | `Valeria` / `Torres Medina` | No (match aproximado) |
| `99999999Z` | `Ana` / `García` / `López` | `Ana` / `García` | ✅ **Sí** (falta López) |

> **Heurística:** `split_part(lastname, ' ', 1)` extrae el primer apellido. `replace(lastname, primer_apellido, '')` extrae el resto (segundo apellido). Esto es una aproximación.

**Salida:** `NameChangeDelta(documento="99999999Z", nombre_sigad="Ana", apellido1_sigad="García", apellido2_sigad="López", firstname_moodle="Ana", lastname_moodle="García")`

---

## Delta 5: Cambios de Username (NIE → DNI)

**Definición:** Un alumno cambió su documento de identidad (ej: de NIE extranjero a DNI español). Se detecta cruzando por **IdSIGAD**, el identificador inmutable de SIGAD que se almacena como custom field en Moodle.

### Lógica

```sql
SELECT
    m.username AS old_username,
    s.documento AS new_documento,
    s.email AS email
FROM moodle_users m
JOIN sigad_users s ON s.id_alumno = m.id_sigad
WHERE m.username <> lower(s.documento)
  AND m.id_sigad IS NOT NULL
```

### Diagrama

```mermaid
flowchart LR
    subgraph Moodle["🎓 Moodle (antiguo)"]
        M1["username: X1234567L<br/>email: juan@ejemplo.com"]
    end

    subgraph SIGAD["📋 SIGAD (actualizado)"]
        S1["documento: 12345678A<br/>email: juan@ejemplo.com"]
    end

    M1 -->|JOIN<br/>mismo email| S1

    style M1 fill:#ffcccc
    style S1 fill:#ccffcc
```

### Ejemplo

| Origen | Identificador | IdSIGAD | Coincidencia |
|--------|---------------|---------|--------------|
| Moodle | `X1234567L` | `99999` | — |
| SIGAD | `12345678A` | `99999` | ✅ Mismo IdSIGAD |

**Salida:** `UsernameChangeDelta(old_username="X1234567L", new_documento="12345678A", email="juan@ejemplo.com")`

> **Caso de uso típico:** Un estudiante extranjero obtiene la nacionalidad y cambia su NIE por DNI. SIGAD refleja el nuevo documento, pero Moodle conserva el antiguo como `username`. El `IdSIGAD` (custom field) permite relacionar ambos usuarios.

---

## Delta 6: Nuevas Matrículas

**Definición:** Módulos/cursos en los que un alumno debería estar matriculado según SIGAD pero no lo está en Moodle.

### Lógica

```sql
SELECT
    s.documento,
    s.siglas_modulo AS shortname
FROM sigad_enrolments s
LEFT JOIN moodle_enrolments me
    ON me.username = lower(s.documento)
   AND me.shortname = s.siglas_modulo
WHERE me.course_id IS NULL
```

### Diagrama

```mermaid
flowchart LR
    subgraph SIGAD
        S1["Juan → PROG ✅"]
        S2["Juan → BD ✅"]
        S3["Valeria → IPPE1 ✅"]
    end

    subgraph Moodle
        M1["Juan → PROG"]
        M2["Valeria → IPPE1"]
    end

    S1 -->|LEFT JOIN| M1
    S2 -.->|LEFT JOIN<br/>no encuentra| M1
    S3 -->|LEFT JOIN| M2

    style S2 fill:#ffcccc
```

### Ejemplo

| Alumno | Módulo SIGAD | ¿En Moodle? | Resultado |
|--------|--------------|-------------|-----------|
| Juan (`12345678A`) | `PROG` | Sí | — |
| Juan (`12345678A`) | `BD` | **No** | ✅ **Nueva matrícula** |
| Valeria (`78842153Q`) | `IPPE1` | Sí | — |

**Salida:** `EnrolmentDelta(documento="12345678A", course_shortname="BD")`

---

## Delta 7: Matrículas Eliminadas

**Definición:** Matrículas en Moodle que no deberían existir según SIGAD. Ocurre cuando un alumno abandona un módulo o se transfiere.

### Lógica

```sql
SELECT
    me.username AS documento,
    me.shortname,
    me.course_id
FROM moodle_enrolments me
LEFT JOIN sigad_enrolments se
    ON lower(se.documento) = me.username
   AND se.siglas_modulo = me.shortname
WHERE se.documento IS NULL
```

### Diagrama

```mermaid
flowchart LR
    subgraph SIGAD
        S1["Valeria → IPPE1 ✅"]
    end

    subgraph Moodle
        M1["Valeria → IPPE1"]
        M2["Valeria → PROG"]
        M3["Antiguo → BD"]
    end

    M1 -->|LEFT JOIN| S1
    M2 -.->|LEFT JOIN<br/>no encuentra| S1
    M3 -.->|LEFT JOIN<br/>no encuentra| S1

    style M2 fill:#ffcccc
    style M3 fill:#ffcccc
```

### Ejemplo

| Alumno (Moodle) | Módulo Moodle | ¿En SIGAD? | Resultado |
|-----------------|---------------|------------|-----------|
| `78842153q` | `IPPE1` | Sí (Valeria) | — |
| `78842153q` | `PROG` | **No** | ✅ **Matrícula a eliminar** |
| `99999999z` | `BD` | **No** (baja total) | ✅ **Matrícula a eliminar** |

> **Nota:** Una matrícula eliminada puede preceder una baja total (Delta 2). Si el usuario ya no está en SIGAD, todas sus matrículas aparecerán como eliminadas.

**Salida:** `EnrolmentDelta(documento="78842153q", course_shortname="PROG", course_id=2)`

---

## Casos Especiales

### Usuarios Protegidos

El sistema carga un CSV (`data/usuarios_protegidos.csv`) con IDs de Moodle que nunca deben eliminarse ni suspenderse (admin, guest, cuentas de servicio, etc.).

```mermaid
flowchart TD
    A[Usuario en Moodle<br/>no en SIGAD] --> B{¿ID protegido?}
    B -->|Sí| C[Ignorar 🛡️]
    B -->|No| D[Reportar como baja]
```

### NIE → DNI

Este delta depende críticamente de que el alumno mantenga el **mismo IdSIGAD** entre el cambio de documento. El `IdSIGAD` es un custom field de Moodle que no varía y se rellena con el `id_alumno` de SIGAD.

Si el usuario de Moodle no tiene `IdSIGAD` (por ejemplo, usuarios antiguos creados antes de esta sincronización), el sistema no detectará automáticamente la relación y reportará:
- Una **baja** del usuario antiguo (NIE)
- Una **alta** del usuario nuevo (DNI)

Esto es el comportamiento esperado y seguro.

---

## Resumen de Tipos de Delta

| # | Delta | JOIN | WHERE | Origen de la clave |
|---|-------|------|-------|-------------------|
| 1 | **Altas** | `sigad LEFT JOIN moodle` | `moodle.id IS NULL` | Documento normalizado |
| 2 | **Bajas** | `moodle LEFT JOIN sigad` | `sigad.documento IS NULL` + no protegido | Documento normalizado |
| 3 | **Email** | `sigad INNER JOIN moodle` | `email` personal diferente del custom field `emailsigad` (case-insensitive) | Documento normalizado |
| 4 | **Nombre** | `sigad INNER JOIN moodle` | `nombre` o `apellidos` diferente | Documento normalizado |
| 5 | **Username** | `moodle INNER JOIN sigad` | `username <> documento` cruzado por **IdSIGAD** | IdSIGAD (id_alumno) |
| 6 | **Matrículas nuevas** | `sigad_enrol LEFT JOIN moodle_enrol` | `moodle.course_id IS NULL` | Documento + siglas módulo |
| 7 | **Matrículas eliminadas** | `moodle_enrol LEFT JOIN sigad_enrol` | `sigad.documento IS NULL` | Documento + siglas módulo |

### Matriz de decisión

```mermaid
flowchart TD
    Start([Alumno/Usuario]) --> Existe{¿Existe en<br/>ambos sistemas?}

    Existe -->|Solo SIGAD| D1[Delta 1: Alta]
    Existe -->|Solo Moodle| D2{¿Protegido?}
    D2 -->|Sí| Ignore[Ignorar]
    D2 -->|No| D2b[Delta 2: Baja]
    Existe -->|Ambos| Comparar{¿Qué coincide?}

    Comparar -->|Email diferente| D3[Delta 3: Email]
    Comparar -->|Nombre diferente| D4[Delta 4: Nombre]
    Comparar -->|Documento ≠ Username<br/>pero IdSIGAD coincide| D5[Delta 5: Username]
    Comparar -->|Todo igual| Matricula{¿Matrículas?}

    Matricula -->|En SIGAD, no Moodle| D6[Delta 6: Nueva matrícula]
    Matricula -->|En Moodle, no SIGAD| D7[Delta 7: Matrícula eliminada]
    Matricula -->|Todo igual| OK[Sin delta]
```

---

## Referencias

- Código fuente: [`gestion_alumnos/services/sync_analyzer.py`](../gestion_alumnos/services/sync_analyzer.py)
- Modelos de delta: [`gestion_alumnos/models/sync_report.py`](../gestion_alumnos/models/sync_report.py)
- Tests unitarios: [`tests/test_sync_analyzer.py`](../tests/test_sync_analyzer.py)
