# fp-distancia-gestion-usuarios-automatica

Script en Python que sincroniza automáticamente el alumnado de SIGAD con una plataforma Moodle (FP a distancia de Aragón): crea usuarios, los suspende/reactiva, actualiza sus datos y gestiona sus matrículas en cursos y cohortes. Al terminar envía un informe por correo.

## Cómo funciona

1. Calcula el curso académico a consultar (de septiembre a diciembre, el año actual; de enero a agosto, el anterior).
2. Llama al **1er Web Service** de SIGAD, que devuelve un `idSolicitud`.
3. Consulta el **2º Web Service** con ese identificador, hasta 10 veces esperando 10 s entre intentos, hasta que el JSON del alumnado está listo.
4. Transforma el JSON en objetos `Alumno` / `Centro` / `Ciclo` / `Modulo` (carpeta `classes/`).
5. Compara con los usuarios de Moodle y:
   - crea los alumnos que no existen (si tienen nombre, apellidos, documento y email SIGAD) y les envía un correo de bienvenida;
   - reactiva a los suspendidos que vuelven a figurar en SIGAD;
   - suspende a los que ya no figuran;
   - actualiza nombre de usuario y email cuando cambian;
   - matricula, suspende, reactiva o borra matrículas en los cursos (por `shortname` de curso) y en las cohortes;
   - detecta alumnado con más de una tutoría.
6. Escribe un informe detallado (Markdown/HTML en `logs/`), un CSV en `csvs/`, y lo envía por correo a `REPORT_TO`. Las plantillas de correo están en `templates/`.

Las acciones sobre Moodle se hacen con **moosh** dentro del contenedor Docker de Moodle (`docker exec <contenedor> moosh ...`) y con consultas directas al cliente `mysql` de la base de datos.

## Requisitos

- Linux con acceso al Docker donde corre Moodle (el contenedor se localiza con `docker ps | grep <SUBDOMAIN>`).
- Python 3.8+ (ver `Dockerfile`).
- `moosh` y cliente `mysql` disponibles donde se ejecutan los comandos.
- Acceso a los dos Web Services de SIGAD, a la base de datos de Moodle y a un servidor SMTP.

## Configuración

Copia `Config-sample.py` a `Config.py` (está en `.gitignore`, **no lo subas al repositorio**) y rellena:

| Grupo | Variables |
|---|---|
| General | `SUBDOMAIN` |
| 1er WS | `url1`, `path1`, `usuario1`, `password1`, `method1` |
| 2º WS | `url2`, `path2`, `usuario2`, `password2`, `method2` |
| Correo | `SMTP_HOSTS`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` |
| Base de datos | `DB_USER`, `DB_PASS`, `DB_HOST`, `DB_NAME` |
| Informes | `REPORT_TO` (correos separados por espacios) |

También se ignoran `Config-predesarrollo.py`, `Config-test.py` y `Config-www.py`, útiles para tener un fichero por entorno y copiarlo a `Config.py`.

## Ejecución

```bash
python main.py
```

O con Docker:

```bash
docker build -t fp-gestion-usuarios .
docker run --rm fp-gestion-usuarios
```

Nota: `main.py` escribe logs y CSVs en `logs/` y `csvs/` dentro de la carpeta del proyecto (se crean si no existen). Está pensado para lanzarse periódicamente (cron).

Para probar sin llamar a los Web Services, pon `procesa_desde_fichero = True` en `main()` y deja un JSON en `jsons/` .

## Estructura

| Ruta | Contenido |
|---|---|
| `main.py` | Flujo principal y funciones de acceso a Moodle, BD y correo |
| `Conexion.py` | Cliente HTTP para los Web Services |
| `Util.py` | Utilidades (generación de emails de dominio, normalización de texto, conversión LFP→LOE) |
| `classes/` | Modelos `Alumno`, `Centro`, `Ciclo`, `Modulo` |
| `templates/` | Plantillas HTML de correos e informes |
| `extrae_alumnado.sh` | Genera CSVs a partir de los informes HTML del día (opcionalmente los copia con `scp` si defines `SCP_TARGET`) |
| `Config-sample.py` | Plantilla de configuración |

## Notas

- Los usuarios de sistema de Moodle (ids fijos listados en `usuarios_moodle_no_borrables` en `main.py`) nunca se suspenden ni se borran.
- El proyecto sólo usa la librería estándar de Python, por eso no hay `requirements.txt`.
