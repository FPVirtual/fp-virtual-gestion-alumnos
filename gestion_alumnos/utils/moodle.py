import io
import os
from utils.moosh import run_moosh_command, run_command
from gestion_alumnos.logger_config import logger


def get_moodle(subdomain):
    """
    Devuelve un objeto como el siguiente:
    
    """
    logger.info(f"get_moodle(subdomain: ",subdomain,")", sep="")
    
    data = os.popen(f"docker ps | grep {subdomain}").read()
    data_s = io.StringIO(data).read()
    lines = data_s.splitlines()
    container = [
        {
            "url": line.split()[-1].replace("wwwfpvirtualaragones-moodle-1", ".fpvirtualaragon.es"), # "url": line.split()[-1].replace("adistanciafparagones-moodle-1", ".adistanciafparagon.es"),
            "container_name": line.split()[-1],
        }
        for line in lines
        if line.split()[-1].endswith("moodle-1")
    ]

    return container



"""
Devuelve una lista de alumnos (omite usuarios con username que empiece por prof)
    que actualmente están en moodle:
"""
def get_alumnos_moodle_no_borrados(moodle):
    logger.info("get_alumnos_moodle_no_borrados(...)")

    #listado de usuarios limitado a 50.000 # username (id), email,
    cmd = "moosh -n user-list -n 50000 \"deleted = 0 and username not like 'prof%' \" " 
    logger.test("cmd: ", cmd)
    alumnos_moodle = run_moosh_command(moodle, cmd, True)
    
    alumnos = []    
    
    data_s = io.StringIO(alumnos_moodle).read()
    lines = data_s.splitlines()
    alumno = [
        {
            "username": line.split()[0],
            "userid": line.split()[1].replace("(","").replace("),",""),
            "email": line.split()[2].replace(",",""), # email del dominio google
            "email_sigad": "", # email de sigad
        }
        for line in lines
       
    ]
    alumnos.extend(alumno)

    # Recorro cada alumno y le añado el email de sigad
    for al in alumnos:
    ## TODO Darío: Optimizar esta consulta para que no sea una por alumno    
        command = '''\
            mysql --user=\"{DB_USER}\" --password=\"{DB_PASS}\" --host=\"{DB_HOST}\" -D \"{DB_NAME}\"  --execute=\"
                SELECT data
                FROM mdl_user_info_data
                where fieldid = 4 and userid = {id_usuario}
            \" | tail -n +2
            '''.format(DB_USER = os.getenv("DB_USER"), DB_PASS = os.getenv("DB_PASS"), DB_HOST = os.getenv("DB_HOST"), DB_NAME = os.getenv("DB_NAME"), id_usuario = al["userid"] )

        email_sigad = run_command( command , True).rstrip()
    
        logger.info("email_sigad: ", email_sigad)

        al["email_sigad"] = email_sigad
    
    # Devuelvo el listado de alumnos que cumplen las condiciones
    return alumnos