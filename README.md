# fp-virtual-gestion-usuarios-automatica

Script en Python que sincroniza automáticamente el alumnado de SIGAD con una plataforma Moodle (FP a distancia de Aragón): crea usuarios, los suspende/reactiva, actualiza sus datos y gestiona sus matrículas en cursos y cohortes. Al terminar genera un informe que se envía por correo.

Son dos scripts: `main.py` hace todo el trabajo sobre Moodle y deja los correos que hay que mandar como ficheros JSON en `pendientes/`, y `enviar_correos.py` los envía. Si un envío falla o se interrumpe, el correo sigue en `pendientes/` y se manda en la siguiente ejecución.

## Cómo funciona

1. Calcula el curso académico a consultar (de septiembre a diciembre, el año actual; de enero a agosto, el anterior).
2. Llama al **1er Web Service** de SIGAD, que devuelve un `idSolicitud`.
3. Consulta el **2º Web Service** con ese identificador, hasta 10 veces esperando 10 s entre intentos, hasta que el JSON del alumnado está listo.
4. Transforma el JSON en objetos `Alumno` / `Centro` / `Ciclo` / `Modulo` (carpeta `classes/`).
5. Compara con los usuarios de Moodle y, en este orden:
   - reactiva a los suspendidos que vuelven a figurar en SIGAD;
   - actualiza el email cuando cambia en SIGAD y el nombre de usuario cuando un alumno pasa de NIE a DNI (lo reconoce por su `id_sigad`);
   - suspende a los que ya no figuran en SIGAD: primero sus matrículas y después les saca de sus cohortes;
   - suspende las matrículas en cursos que SIGAD ya no recoge (sin tocar las cohortes, porque sacar a un alumno de una cohorte borra su progreso);
   - crea los alumnos que no existen (si tienen nombre, apellidos, documento y email SIGAD), los mete en la cohorte `alumnado` y les genera un correo de bienvenida con sus datos de acceso;
   - matricula o reactiva a cada alumno en los cursos de sus módulos y en la cohorte de su ciclo, y avisa por correo de las matrículas nuevas a quien ya tenía cuenta;
   - revisa el alumnado con más de una tutoría y lo saca de las que no le corresponden;
   - en agosto borra las matrículas suspendidas.
6. Al crear un alumno nuevo, añade su alta a un CSV en `csvs/` para importarlo a mano en la Admin Console de Google Workspace.
7. Escribe un informe detallado (Markdown en `logs/<SUBDOMAIN>/md/`) y genera un correo con él para cada dirección de `REPORT_TO`. Si algo falla, genera en su lugar un correo de error a `gestion@fpvirtualaragon.es` y termina con código de salida 1.

Correspondencias que usa para enlazar SIGAD y Moodle:

- **Alumno:** el `documento` (DNI/NIE) de SIGAD es el nombre de usuario en Moodle (en minúsculas).
- **Curso:** el `shortname` es `<código centro>-<siglas ciclo>-<id materia>` (p. ej. `50020125-IFC303-18588`). Si el curso no existe, no se crea: se anota en el informe. Los cursos de tutoría (`...t`) y el curso `ayuda` van por cohorte y no se revisan uno a uno.
- **Cohorte:** `<código centro>-<siglas ciclo>` (p. ej. `50020125-IFC303`).

Las acciones sobre Moodle se hacen con **moosh** dentro del contenedor Docker de Moodle (`docker exec <contenedor> moosh ...`) y con consultas directas al cliente `mysql` de la base de datos.

### Envío de correos (`enviar_correos.py`)

- Cada correo es un JSON en `pendientes/<SUBDOMAIN>/` con el destinatario, el asunto, la plantilla de `templates/`, los datos para rellenarla y las rutas de los adjuntos. El HTML se genera al enviar, junto con una versión en texto plano sacada del propio HTML.
- Envía primero los informes y después los avisos a alumnos, por orden de creación, con **2 segundos de espera** entre correo y correo.
- Como mucho envía `MAX_CORREOS_POR_EJECUCION` correos por ejecución (por defecto 1000 en `www` y 3 en el resto de entornos); lo demás queda pendiente. La cuenta de Gmail admite unos 2000 correos al día.
- Si un envío va bien, mueve el JSON a `enviados/<SUBDOMAIN>/` añadiéndole la fecha de envío (`enviado`). Si falla, lo deja para la siguiente ejecución y, tras 3 intentos, lo mueve a `fallidos/<SUBDOMAIN>/`.
- Si ya hay otro `enviar_correos.py` en marcha para el mismo entorno, sale sin hacer nada.
- **Los JSON de bienvenida contienen la contraseña del alumno en claro.** `pendientes/`, `enviados/` y `fallidos/` están en `.gitignore`; protege esas carpetas en el servidor. `enviados/` no se vacía sola.

### A quién van los correos

| Correo | Plantilla | En `www` | En el resto de entornos |
|---|---|---|---|
| Bienvenida (usuario, contraseña y matrículas) | `nuevoUsuario.html` | email de SIGAD del alumno | `BIENVENIDA_TO` (o `gestion@fpvirtualaragon.es`) |
| Matrículas añadidas | `matriculasAnadidas.html` | email de SIGAD del alumno | `BIENVENIDA_TO` (o `gestion@fpvirtualaragon.es`) |
| Cambio de usuario (NIE → DNI) | `nombreUsuarioActualizado.html` | email corporativo del alumno | `gestion@fpvirtualaragon.es` |
| Informe de la ejecución (adjunta el informe y el CSV) | `informeAutomatizado.html` | cada dirección de `REPORT_TO` | igual |
| Error en la ejecución | `haFalladoElInforme.html` | `gestion@fpvirtualaragon.es` | igual |

Además de estos, el propio Moodle envía un "Bienvenido al curso" cada vez que se matricula a alguien, si está activado en el método de matriculación manual. En producción está desactivado; en los entornos de prueba conviene poner `$CFG->noemailever = true;` en el `config.php` de Moodle para que no salga ningún correo al alumnado real.

## Requisitos

- Linux con acceso al Docker donde corre Moodle (el contenedor se localiza con `docker ps | grep <SUBDOMAIN>` y debe terminar en `moodle-1`).
- Python 3.11.2 (ver `Dockerfile`) y Jinja2 (`pip install -r requirements.txt`).
- `moosh` dentro del contenedor de Moodle y cliente `mysql` donde se ejecuta el script.
- Acceso a los dos Web Services de SIGAD, a la base de datos de Moodle y a un servidor SMTP.
- En Moodle deben existir antes de ejecutar:
  - los campos de perfil de usuario con nombre corto `email_sigad` e `id_sigad` (si faltan, el script falla);
  - las cohortes `alumnado` y `<centro>-<ciclo>` de cada ciclo (si falta una, sus alumnos se quedan sin cohorte ni tutoría; moosh sólo avisa con "Cohort does not exist" en la salida);
  - los cursos `<centro>-<ciclo>-<materia>` (los que faltan aparecen en el informe).

## Configuración

Copia `Config-sample.py` a `Config.py` (está en `.gitignore`, **no lo subas al repositorio**) y rellena:

| Grupo | Variables |
|---|---|
| General | `SUBDOMAIN` (`www` es producción) |
| 1er WS | `url1`, `path1`, `usuario1`, `password1`, `method1` |
| 2º WS | `url2`, `path2`, `usuario2`, `password2`, `method2` |
| Correo | `SMTP_HOSTS`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` |
| Base de datos | `DB_USER`, `DB_PASS`, `DB_HOST`, `DB_NAME` (la misma base de datos que usa el contenedor de Moodle de ese entorno) |
| Informes | `REPORT_TO` (correos separados por espacios) |
| Opcionales | `BIENVENIDA_TO`: destinatario de las bienvenidas y avisos de matrícula fuera de `www`. `MAX_CORREOS_POR_EJECUCION`: tope de `enviar_correos.py` |

También se ignoran `Config-predesarrollo.py`, `Config-test.py` y `Config-www.py`, útiles para tener un fichero por entorno y copiarlo a `Config.py`.

## Uso

```bash
python main.py                      # sincroniza Moodle y deja los correos en pendientes/
python enviar_correos.py            # envía los correos pendientes
```

Opciones de `main.py` (`python main.py --help`):

| Opción | Qué hace |
|---|---|
| `--dry-run` | Consulta SIGAD y Moodle y escribe el informe, pero no modifica Moodle ni genera correos. Sirve para ver qué haría. |
| `--no-emails` | Modifica Moodle pero no genera ningún correo. |
| `--limite-alumnos [N]` | Procesa sólo los N primeros alumnos de SIGAD (100 si no se indica). No suspende a nadie por no estar en SIGAD, porque faltarían todos los demás. Se combina con las anteriores. |

Opciones de `enviar_correos.py`:

| Opción | Qué hace |
|---|---|
| `--dry-run` | Genera el HTML de los pendientes pero no los envía ni los mueve. |
| `--solo-informes` | Envía sólo los informes (`0-informe-*`) y deja pendientes los avisos a alumnos. |

Una prueba típica en un entorno de pruebas:

```bash
cp Config-predesarrollo.py Config.py
python main.py --dry-run --limite-alumnos 100    # ver qué haría
python main.py --no-emails --limite-alumnos 100  # aplicarlo en Moodle sin generar correos
```

### Ejecución periódica (cron)

En producción se lanza de lunes a viernes a las 04:00. Si `main.py` termina bien se envían todos los correos pendientes; si falla, sólo los informes (entre ellos el de error), y los avisos a alumnos esperan a la siguiente ejecución que vaya bien:

```
00 04 * * 1-5 cd /var/fp-distancia-gestion-usuarios-automatica && cp Config-www.py Config.py && FECHA=$(date +\%Y\%m\%d-\%H\%M\%S) && if python3 main.py > "logs/www/log/${FECHA}_www_main.log" 2>&1; then python3 enviar_correos.py > "logs/www/log/${FECHA}_www_envio.log" 2>&1; else python3 enviar_correos.py --solo-informes > "logs/www/log/${FECHA}_www_envio.log" 2>&1; fi
```

Una ejecución diaria sin altas nuevas tarda unas 2 horas. La carga inicial de un curso (unos 3100 alumnos nuevos) tarda unas 5 horas y genera una bienvenida por alumno, que con el límite diario de Gmail se envían en dos días.

### Con Docker

```bash
docker build -t fp-gestion-usuarios .
docker run --rm fp-gestion-usuarios                           # main.py
docker run --rm fp-gestion-usuarios python enviar_correos.py  # envío
```

Con Docker, `pendientes/`, `enviados/`, `fallidos/`, `logs/` y `csvs/` (los adjuntos del informe) tienen que estar en volúmenes compartidos por los dos contenedores; si no, se pierden al borrarse el contenedor de `main.py`.

### Probar sin llamar a SIGAD

Pon `procesa_desde_fichero = True` en `main()` y ajusta la ruta del JSON que lee (está fija en el código). `samples/datosAlumnosPrueba.json` es un fichero de ejemplo con ese formato.

## Estructura

| Ruta | Contenido |
|---|---|
| `main.py` | Flujo principal y funciones de acceso a Moodle y BD; genera los correos en `pendientes/` |
| `enviar_correos.py` | Envía los correos de `pendientes/` |
| `Correo.py` | Formato y escritura de los correos pendientes (compartido por los dos scripts) |
| `Conexion.py` | Cliente HTTP para los Web Services |
| `Util.py` | Utilidades (generación de emails de dominio, normalización de texto) |
| `classes/` | Modelos `Alumno`, `Centro`, `Ciclo`, `Modulo` |
| `templates/` | Plantillas HTML de los correos |
| `samples/` | JSON de alumnado de ejemplo para pruebas |
| `Config-sample.py` | Plantilla de configuración |

## Logs y ficheros generados

Todo se guarda dentro de la carpeta del proyecto, separado por entorno (`<SUBDOMAIN>`: `www`, `pre`...). Ninguna de estas carpetas está en git.

Todos los nombres empiezan por la fecha y hora en formato **`AAAAMMDD-HHMMSS`** (p. ej. `20260928-040001`), seguida del entorno y, si hace falta, de qué es el fichero, separados por `_`. Así, al ordenar por nombre quedan en orden cronológico. Los correos son la excepción: empiezan por su tipo (`0-informe` o `1-aviso`) para que se envíen primero los informes.

```
logs/
└── <SUBDOMAIN>/
    ├── md/     informe de cada ejecución de main.py (Markdown)   AAAAMMDD-HHMMSS_<SUBDOMAIN>.md
    ├── json/   respuestas en bruto de los Web Services de SIGAD  AAAAMMDD-HHMMSS_<SUBDOMAIN>_ws1.json / _ws2.json
    └── log/    salida completa por pantalla de cada ejecución del cron
                AAAAMMDD-HHMMSS_<SUBDOMAIN>_main.log   (main.py)
                AAAAMMDD-HHMMSS_<SUBDOMAIN>_envio.log  (enviar_correos.py)
csvs/        altas para Google Workspace de cada ejecución         AAAAMMDD-HHMMSS_<SUBDOMAIN>.csv
pendientes/<SUBDOMAIN>/   correos por enviar                       <tipo>-AAAAMMDD-HHMMSS-<microsegundos>-<id>.json
enviados/<SUBDOMAIN>/     correos enviados, con la fecha de envío  (mismo nombre)
fallidos/<SUBDOMAIN>/     correos que fallaron 3 veces             (mismo nombre)
```

- **`logs/<SUBDOMAIN>/md/`** es el sitio donde mirar qué ha hecho una ejecución: es el mismo informe que se adjunta al correo. Tiene un apartado por cada fase (reactivados, cambios de email y de usuario, alumnado en Moodle que no está en SIGAD, suspensiones, matrículas suspendidas, altas y matrículas, alumnado con más de una tutoría, altas que no se han podido hacer) y termina con un **resumen de acciones** con los totales. El informe y el CSV de una misma ejecución comparten la fecha y hora del nombre.
- **`logs/<SUBDOMAIN>/json/`** guarda lo que devolvió SIGAD en cada ejecución (`ws1` es la solicitud, `ws2` el alumnado completo). Sirve para revisar qué datos había en SIGAD un día concreto.
- **`logs/<SUBDOMAIN>/log/`** tiene todo lo que imprimen los scripts, incluidos los comandos de moosh y SQL y sus respuestas. Es donde buscar el detalle de un error (`Traceback`) o los avisos de moosh como `Cohort does not exist`. Esta carpeta y los nombres de sus ficheros los define la línea del cron, no los scripts; si se lanzan a mano, la salida va a la terminal.
- **`csvs/`** tiene una fila por alumno creado, con el formato de importación de usuarios de la Admin Console de Google Workspace.

Los ficheros de `md/`, `json/` y `csvs/` y las carpetas de correos los crea `main.py` si no existen; `log/` hay que crearla una vez para el cron. **Nada se borra solo:** los logs de `log/` ocupan unos 50 MB por ejecución (en `www` ya son varios GB), así que conviene purgarlos de vez en cuando (p. ej. `find logs/www/log -name '*.log' -mtime +90 -delete`).

**Datos sensibles.** Los ficheros de `log/` contienen la contraseña de la base de datos (aparece en los comandos `mysql` que se imprimen); los de `json/`, `csvs/` y `enviados/` contienen datos personales del alumnado, y los CSV y los correos de bienvenida, sus contraseñas iniciales. Protege estas carpetas en el servidor y no las compartas.

## Notas

- Nunca se suspenden, se revisan ni se sacan de sus cohortes:
  - los usuarios de sistema de Moodle, cuyos ids están en `usuarios_moodle_no_borrables` en `main.py` (los mismos en `www` y en `pre`);
  - el profesorado (usuarios que empiezan por `prof`).
- Los cursos cuyo `shortname` no sigue el formato `centro-ciclo-materia` (p. ej. `profesorado`, `coordinacion`) se ignoran al revisar matrículas.
- Los alumnos creados antes de que existiera el campo `id_sigad` no lo tienen relleno, así que no se les reconoce el cambio de NIE a DNI hasta que se rellene a mano.
- Plantillas de correo (`templates/`): todas heredan de `base.html`, que tiene los estilos, la cabecera, el pie y un texto de previsualización oculto (bloque `preheader`, que cada plantilla define). Para incluir un logo, guárdalo como `templates/img/logo.png`: se incrusta en el correo sin aparecer como adjunto (si no existe, se muestra el texto "FP virtual Aragón").
