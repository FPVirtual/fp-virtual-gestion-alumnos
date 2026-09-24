# fp-distancia-gestion-usuarios-automatica

Script en Python que sincroniza automáticamente el alumnado de SIGAD con una plataforma Moodle (FP a distancia de Aragón): crea usuarios, los suspende/reactiva, actualiza sus datos y gestiona sus matrículas en cursos y cohortes. Al terminar genera un informe que se envía por correo.

Son dos scripts: `main.py` hace todo el trabajo sobre Moodle y deja los correos que hay que mandar como ficheros JSON en `pendientes/`, y `enviar_correos.py` los envía. Si un envío falla o se interrumpe, el correo sigue en `pendientes/` y se manda en la siguiente ejecución.

## Cómo funciona

1. Calcula el curso académico a consultar (de septiembre a diciembre, el año actual; de enero a agosto, el anterior).
2. Llama al **1er Web Service** de SIGAD, que devuelve un `idSolicitud`.
3. Consulta el **2º Web Service** con ese identificador, hasta 10 veces esperando 10 s entre intentos, hasta que el JSON del alumnado está listo.
4. Transforma el JSON en objetos `Alumno` / `Centro` / `Ciclo` / `Modulo` (carpeta `classes/`).
5. Compara con los usuarios de Moodle y:
   - crea los alumnos que no existen (si tienen nombre, apellidos, documento y email SIGAD) y les genera un correo de bienvenida;
   - reactiva a los suspendidos que vuelven a figurar en SIGAD;
   - suspende a los que ya no figuran;
   - actualiza nombre de usuario y email cuando cambian;
   - matricula, suspende, reactiva o borra matrículas en los cursos (por `shortname` de curso) y en las cohortes;
   - detecta alumnado con más de una tutoría.
6. Al crear un alumno nuevo, añade su alta a un CSV en `csvs/` para importarlo a mano en la Admin Console de Google Workspace.
7. Escribe un informe detallado (Markdown/HTML en `logs/`) y genera un correo con él para cada dirección de `REPORT_TO`.

### Envío de correos (`enviar_correos.py`)

- Cada correo es un JSON en `pendientes/<SUBDOMAIN>/` con el destinatario, el asunto, la plantilla de `templates/`, los datos para rellenarla y las rutas de los adjuntos. El HTML se genera al enviar.
- Envía primero los informes y después los avisos a alumnos, por orden de creación, con **2 segundos de espera** entre correo y correo.
- Como mucho envía 1000 correos por ejecución en `www` (límite diario de la cuenta) y 3 en el resto de entornos; lo demás queda pendiente.
- Si un envío va bien, mueve el JSON a `enviados/<SUBDOMAIN>/` añadiéndole la fecha de envío (`enviado`). Si falla, lo deja para la siguiente ejecución y, tras 3 intentos, lo mueve a `fallidos/<SUBDOMAIN>/`.
- Si ya hay otro `enviar_correos.py` en marcha para el mismo entorno, sale sin hacer nada.
- **Los JSON de bienvenida contienen la contraseña del alumno en claro.** `pendientes/`, `enviados/` y `fallidos/` están en `.gitignore`; protege esas carpetas en el servidor. `enviados/` no se vacía sola.

Las acciones sobre Moodle se hacen con **moosh** dentro del contenedor Docker de Moodle (`docker exec <contenedor> moosh ...`) y con consultas directas al cliente `mysql` de la base de datos.

## Requisitos

- Linux con acceso al Docker donde corre Moodle (el contenedor se localiza con `docker ps | grep <SUBDOMAIN>`).
- Python 3.11.2 (ver `Dockerfile`).
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
python main.py             # sincroniza Moodle y deja los correos en pendientes/
python enviar_correos.py   # envía los correos pendientes
```

En cron conviene lanzar `enviar_correos.py` justo después de `main.py` (p. ej. `python main.py; python enviar_correos.py`) y, si se quiere, también en otros momentos para reintentar lo pendiente. Para pruebas, `python main.py --limite-alumnos` procesa sólo los 100 primeros alumnos de SIGAD (o los N de `--limite-alumnos N`). En ese modo no se suspende a nadie por no estar en SIGAD, porque faltarían todos los demás; se combina con `--dry-run` o `--no-emails`. `enviar_correos.py --dry-run` genera el HTML de los pendientes sin enviarlos ni moverlos.

O con Docker:

```bash
docker build -t fp-gestion-usuarios .
docker run --rm fp-gestion-usuarios                           # main.py
docker run --rm fp-gestion-usuarios python enviar_correos.py  # envío
```

Con Docker, `pendientes/`, `enviados/`, `fallidos/`, `logs/` y `csvs/` (los adjuntos del informe) tienen que estar en volúmenes compartidos por los dos contenedores; si no, se pierden al borrarse el contenedor de `main.py`.

Nota: `main.py` escribe logs, CSVs y correos pendientes en `logs/`, `csvs/` y `pendientes/` dentro de la carpeta del proyecto (se crean si no existen). Está pensado para lanzarse periódicamente (cron).

Para probar sin llamar a los Web Services, pon `procesa_desde_fichero = True` en `main()` y deja un JSON en `jsons/` .

## Estructura

| Ruta | Contenido |
|---|---|
| `main.py` | Flujo principal y funciones de acceso a Moodle y BD; genera los correos en `pendientes/` |
| `enviar_correos.py` | Envía los correos de `pendientes/` |
| `Correo.py` | Formato y escritura de los correos pendientes (compartido por los dos scripts) |
| `Conexion.py` | Cliente HTTP para los Web Services |
| `Util.py` | Utilidades (generación de emails de dominio, normalización de texto) |
| `classes/` | Modelos `Alumno`, `Centro`, `Ciclo`, `Modulo` |
| `templates/` | Plantillas HTML de correos e informes |
| `extrae_alumnado.sh` | Genera CSVs a partir de los informes HTML del día (opcionalmente los copia con `scp` si defines `SCP_TARGET`) |
| `Config-sample.py` | Plantilla de configuración |

## Notas

- Los usuarios de sistema de Moodle (ids fijos listados en `usuarios_moodle_no_borrables` en `main.py`) nunca se suspenden ni se borran.
- Dependencia externa: Jinja2 (`pip install -r requirements.txt`), para las plantillas de correo.
- Las plantillas (`templates/`) heredan de `base.html`, donde están los estilos y el pie. Para incluir un logo en los correos, guárdalo como `templates/img/logo.png` (si no existe, se muestra el texto "FP virtual Aragón").
