# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es

Scripts Python (sin framework): `main.py` sincroniza el alumnado de SIGAD (2 Web Services) con una instancia Moodle de FP a distancia de Aragón: crea/suspende/reactiva usuarios, actualiza login y email, gestiona matrículas en cursos y cohortes, y deja los correos (avisos e informe) como JSON en `pendientes/`; `enviar_correos.py` los envía. Está pensado para ejecutarse periódicamente (cron) en el servidor donde corre Moodle en Docker. El README.md tiene la descripción funcional en español.

## Comandos

```bash
python main.py                      # ejecuta todo el flujo (`try: main()` bajo `if __name__ == "__main__"`)
python main.py --dry-run            # no modifica Moodle ni genera correos; --help lista las opciones
python main.py --no-emails           # sí modifica Moodle pero no genera ningún correo (implícito en --dry-run)
python enviar_correos.py            # envía los correos de pendientes/<SUBDOMAIN>/ (2 s entre correos)
python enviar_correos.py --dry-run  # renderiza los pendientes sin enviarlos ni borrarlos
docker build -t fp-gestion-usuarios .   # Dockerfile usa python:3.8-slim-buster
./extrae_alumnado.sh                # genera CSVs a partir de los informes de hoy en logs/ (SCP_TARGET opcional)
```

No hay tests, linter ni sistema de build. Única dependencia externa: Jinja2 (`pip install -r requirements.txt`).

Para probar sin llamar a SIGAD: poner `procesa_desde_fichero = True` en `main()` (main.py) y dejar un JSON en `jsons/...` (bajo `BASE_DIR`) (el nombre del fichero está hardcodeado).

## Configuración y entorno

- `Config.py` (ignorado por git; plantilla en `Config-sample.py`) se importa con `from Config import *`. Variables globales: `SUBDOMAIN`, credenciales de los dos WS, SMTP, BD, `REPORT_TO`. También se ignoran `Config-{predesarrollo,test,www}.py` (uno por entorno, copiado a `Config.py`).
- `SUBDOMAIN == "www"` es producción y cambia el comportamiento: sólo ahí los correos de aviso van a los alumnos (en otros entornos van a `gestion@fpvirtualaragon.es`), y el tope de correos por ejecución de `enviar_correos.py` es 1000 (www) frente a 3 (resto); lo que no se envía queda pendiente.
- Las rutas (`logs/<SUBDOMAIN>/html/`, `csvs/`, `templates/`, `jsons/`, `pendientes/<SUBDOMAIN>/`, `enviados/<SUBDOMAIN>/`, `fallidos/<SUBDOMAIN>/`) son relativas a `BASE_DIR`, la carpeta de `main.py`; los directorios de salida se crean al arrancar.
- Los directorios `processors/` y `services/` están vacíos (sin seguimiento en git); todo el código vive en `main.py`, `enviar_correos.py` y `Correo.py`.

## Arquitectura

Casi toda la lógica está en `main.py` (~1700 líneas): una función `main()` gigante y secuencial, más helpers. Fases de `main()`, en orden:

1. Calcula el curso académico (`get_curso_para_REST`: sep–dic = año actual; ene–ago = año anterior).
2. `Conexion` (http.client) llama al 1er WS → `idSolicitud`; hace polling al 2º WS (10 intentos × 10 s) hasta que `codigo == 0`. Guarda las respuestas crudas (`guarda_fichero_respuesta_ws1/2`).
3. `procesaJsonEstudiantes` construye el árbol `Alumno → Centro → Ciclo → Modulo` (`classes/`). `Alumno` calcula su email corporativo con `Util.creaEmailsDominio`.
4. Reactiva suspendidos que vuelven a estar en SIGAD → detecta cambios de email (SIGAD vs. campo de perfil `email_sigad` de Moodle) → cambio de login NIE→DNI emparejando por `id_sigad` (envía correo) → suspende a quienes no están en SIGAD (primero sus matrículas de curso, luego sale de las cohortes; los ids de `usuarios_moodle_no_borrables` se saltan siempre).
5. Suspende matrículas de curso que SIGAD ya no contempla (se ignoran el curso `ayuda` y los cursos cuyo shortname `centro-ciclo-materia` lleva "t" en el tercer campo = tutoría, matriculados vía cohorte).
6. Recorre `alumnos_sigad` (entero; ya no se corta por número de correos): crea los inexistentes (contraseña aleatoria, cohorte `alumnado`, fila en el CSV de alta de Google Workspace, correo de bienvenida), y matricula/reactiva en cursos y cohortes `<centro>-<ciclo>`.
7. Evalúa alumnado con más de una tutoría, cierra el informe y genera un correo por cada dirección de `REPORT_TO` (con adjuntos). Cualquier excepción genera un correo de error (`haFalladoElInforme.html`) a `gestion@fpvirtualaragon.es`.

`main.py` no hace esperas salvo el polling al 2º WS.

Convenciones clave que enlazan varias piezas:
- Identidad de alumno = `documento` (DNI/NIE) de SIGAD == `username` en Moodle (comparación en minúsculas).
- Shortname de curso Moodle = `crearShortnameCurso(codigo_centro, siglas_ciclo, id_materia)` → `centro-ciclo-materia`; los cursos inexistentes se registran en el informe y no se crean.
- **No sacar a un alumno de una cohorte por una baja de matrícula puntual**: borra su progreso (comentado en el código). Sólo se desmatricula de las cohortes al suspender al usuario entero.

### Acceso a Moodle (sin API)

Nada usa la API REST de Moodle. Las acciones se hacen con:
- `run_moosh_command`: `docker exec <contenedor> moosh ...` (el contenedor se localiza con `docker ps | grep <SUBDOMAIN>` en `get_moodle`, filtrando nombres que terminan en `moodle-1`).
- `run_command`: comandos `mysql --execute="..."` con SQL directo sobre tablas `mdl_*` (lecturas de usuarios/matrículas y varios updates/deletes), con SQL construido por `.format()` de strings.
`--dry-run` (`DRY_RUN`, parseado con argparse antes de importar `Config`) se aplica en estos dos helpers: `run_command` no ejecuta nada con `capture=False`; `run_moosh_command` igual, salvo `mutates=True` (p. ej. `user-create`, que usa `capture=True` porque devuelve el id). `genera_correo` respeta `SEND_EMAILS` (falso con `--no-emails` o `--dry-run`). Cualquier acción nueva que modifique Moodle debe pasar por ellos.
Ambos tienen timeout de 10 s por defecto y `shell=True`.

**Campos personalizados de perfil de usuario** (`mdl_user_info_field` / `mdl_user_info_data`): se usan `email_sigad` (email de SIGAD; comparado contra el email de SIGAD del fichero para detectar cambios) y `id_sigad` (el `idAlumno` de SIGAD; sólo se escribe al crear el alumno, es estable aunque cambien documento o email). `get_user_info_fieldid(shortname)` resuelve el `id` numérico de cada uno por su `shortname` (en vez de asumir un id fijo, que puede variar entre instalaciones) y lo cachea en memoria. Ambos campos deben existir de antemano en Moodle (Administración del sitio → Usuarios → Campos de perfil de usuario) con esos shortnames exactos; si no existen, `get_user_info_fieldid` lanza `ValueError`.
`id_sigad` es la identidad usada para reemparejar a un alumno tras un cambio de NIE a DNI (ver punto 4 del flujo): al no encontrarlo por `documento == username`, se busca entre los que quedaron "en Moodle pero no en SIGAD" uno cuyo `id_sigad` coincida con el `idAlumno` de algún alumno de SIGAD. **Los alumnos creados antes de que existiera este campo no tienen `id_sigad` en Moodle**, así que ese reemparejamiento no funcionará para ellos hasta que se les rellene a mano (o se les vuelva a crear).

### Informes y plantillas de correo

`escribeEnFichero(filename_md, ...)` va acumulando el informe Markdown; `filename_csv` acumula las altas para Google Workspace.

Los correos se generan con `genera_correo(tipo, destinatario, asunto, plantilla, contexto, adjuntos)` en main.py, que llama a `Correo.guarda_correo_pendiente`: escribe un JSON (escritura atómica `.tmp` + `os.replace`) en `pendientes/<SUBDOMAIN>/` con la **plantilla y su contexto, no el HTML**. El contexto debe ser serializable a JSON (las listas de matrículas se pasan como lista, `matriculado_en`). Los adjuntos son rutas y deben estar completos al generar el correo. El nombre del fichero empieza por `0-informe` o `1-aviso` para que al ordenarlo se envíen antes los informes. Los JSON de bienvenida llevan la contraseña en claro (`pendientes/`, `enviados/` y `fallidos/` están en `.gitignore`; `enviados/` no se purga).

Plantillas (Jinja2, autoescape activado; las renderiza `enviar_correos.py`): todas las de `templates/` heredan de `base.html`, que contiene cabecera con logo, estilos y pie con redes sociales; los estilos comunes se cambian sólo ahí (los clientes de correo ignoran muchas reglas CSS, así que lo importante va en línea y con tablas). `_aviso_automatico.html` es un fragmento incluido. El logo es opcional: si existe `templates/img/logo.png` se incrusta como imagen `cid:logo`; si no, la cabecera muestra texto.

### Envío de correo (`enviar_correos.py`)

Proceso independiente de main.py (se lanza aparte, p. ej. en el cron justo después). Recorre `pendientes/<SUBDOMAIN>/*.json` ordenados, renderiza cada plantilla y envía por una única conexión SMTP (un reintento de reconexión), con `PAUSA_ENTRE_CORREOS` = 2 s entre correos y como mucho `MAX_CORREOS_POR_EJECUCION`. Si va bien lo mueve a `enviados/<SUBDOMAIN>/` añadiendo `enviado` (fecha); si falla suma `intentos` y al llegar a `MAX_INTENTOS` (3) lo mueve a `fallidos/<SUBDOMAIN>/`. Un `flock` sobre `pendientes/.<SUBDOMAIN>.lock` impide dos envíos simultáneos (en Windows no hay bloqueo). main.py ya no sabe si los correos llegan: el informe sólo cuenta los generados.
