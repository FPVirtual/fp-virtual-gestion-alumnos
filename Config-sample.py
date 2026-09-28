# Plantilla de configuración. Cópiala a Config.py (o a Config-<entorno>.py y luego a Config.py) y rellena las contraseñas.
# Config.py y Config-{predesarrollo,test,www}.py están en .gitignore: no subas nunca las contraseñas al repositorio.
# Los valores de ejemplo son los de producción (www).

# ---------------------------------------------------------------------------------------------------------------------
# General
# ---------------------------------------------------------------------------------------------------------------------
# OBLIGATORIO. Entorno: "www" es producción; cualquier otro (p. ej. "pre", "test") se trata como pruebas.
# Se usa para localizar el contenedor de Moodle (docker ps | grep <SUBDOMAIN>, nombre terminado en moodle-1),
# para las carpetas logs/, pendientes/, enviados/ y fallidos/, y para decidir a quién van los avisos
# (sólo en "www" se envían al alumnado).
SUBDOMAIN = "www"

# ---------------------------------------------------------------------------------------------------------------------
# 1er Web Service de SIGAD (solicitud): devuelve un idSolicitud
# ---------------------------------------------------------------------------------------------------------------------
url1 = "aplicaciones.aragon.es"                             # OBLIGATORIO
path1 = "/pcrpe/services/alumnosFPDistancia/solicitud/"     # OBLIGATORIO (se le añade el curso académico)
usuario1 = "Aleja2"                                         # OBLIGATORIO
password1 = ""                                              # OBLIGATORIO
method1 = "GET"                                             # OBLIGATORIO

# ---------------------------------------------------------------------------------------------------------------------
# 2º Web Service de SIGAD (fichero): devuelve el JSON del alumnado a partir del idSolicitud
# ---------------------------------------------------------------------------------------------------------------------
url2 = "aplicaciones.aragon.es"                             # OBLIGATORIO
path2 = "/pcrpe/services/alumnosFPDistancia/fichero/"       # OBLIGATORIO (se le añade el idSolicitud)
usuario2 = "Aleja2"                                         # OBLIGATORIO
password2 = ""                                              # OBLIGATORIO
method2 = "GET"                                             # OBLIGATORIO

# ---------------------------------------------------------------------------------------------------------------------
# Correo (SMTP, con STARTTLS). Lo usa enviar_correos.py
# ---------------------------------------------------------------------------------------------------------------------
SMTP_HOSTS = "smtp.gmail.com"                               # OBLIGATORIO
SMTP_PORT = "587"                                           # OBLIGATORIO
SMTP_USER = "noreply@fpvirtualaragon.es"                    # OBLIGATORIO. También es el remitente de los correos
SMTP_PASSWORD = ""                                          # OBLIGATORIO. Contraseña de aplicación de la cuenta de Google

# ---------------------------------------------------------------------------------------------------------------------
# Base de datos de Moodle (MySQL/MariaDB)
# ---------------------------------------------------------------------------------------------------------------------
# Debe ser la MISMA base de datos que usa el contenedor de Moodle del entorno (variable MOODLE_DB_NAME del contenedor):
# moosh actúa sobre el contenedor y el SQL sobre esta base de datos; si no coinciden, se mezclan dos Moodles.
DB_USER = "admin"                                           # OBLIGATORIO
DB_PASS = ""                                                # OBLIGATORIO
DB_HOST = "192.168.1.110"                                   # OBLIGATORIO
DB_NAME = "www_fpvirtualaragon_es"                          # OBLIGATORIO (en pre: predesarrollo_fpvirtualaragon_es_20260127)

# ---------------------------------------------------------------------------------------------------------------------
# Informes
# ---------------------------------------------------------------------------------------------------------------------
# OBLIGATORIO. Direcciones (separadas por espacios) que reciben el informe de cada ejecución, con el informe y el CSV
# de altas adjuntos. El CSV lleva las contraseñas iniciales del alumnado nuevo.
REPORT_TO = "mruizg@campusdigitalfp.com fpdistancia@aragon.es gestion@fpvirtualaragon.es"

# ---------------------------------------------------------------------------------------------------------------------
# Opcionales
# ---------------------------------------------------------------------------------------------------------------------
# OPCIONAL. Sólo fuera de "www": destinatario de los correos de bienvenida y de matrículas añadidas, que en producción
# van al alumno. Si no se define o se deja vacío, van a gestion@fpvirtualaragon.es.
# Ejemplo para pre: BIENVENIDA_TO = "formacion@fpvirtualaragon.es"
BIENVENIDA_TO = ""

# OPCIONAL. Correos como máximo por ejecución de enviar_correos.py (los demás quedan pendientes para la siguiente).
# Si no se define o se deja vacío: 1000 en "www" y 3 en el resto. La cuenta de Gmail admite unos 2000 correos al día.
# Ejemplo para pre: MAX_CORREOS_POR_EJECUCION = 10
MAX_CORREOS_POR_EJECUCION = 1800
