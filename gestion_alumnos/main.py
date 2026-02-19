#Import the modules
import os
import sys
import traceback
from datetime import datetime
from gestion_alumnos.conexion import *
from gestion_alumnos.classes.alumno import *
from gestion_alumnos.classes.centro import *
from gestion_alumnos.classes.ciclo import *
from gestion_alumnos.classes.modulo import *
from gestion_alumnos.logger_config import logger
from utils import api_client, json_parser

filename_md = "";
filename_csv = "";

LOCAL_PATH = os.path.dirname(os.path.abspath(__file__))

def gestion_alumnos():  
    logger.info("# Informe de gestion alumnos v1")
    logger.info(f"Fecha de informe: " + datetime.now().strftime("%d-%m-%Y_%H:%M:%S"))
    logger.info(f"## ENTORNO: "+ os.getenv("ENVIROMENT"))
    logger.info("## RESUMEN DETALLADO ---------------------------------------------")

    # ids de users creados en deploy que no hay que borrar
    usuarios_moodle_no_borrables = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 3725, 3729, 3730, 7152, 7490, 7491, 11720, 12270, 12272]

  #  moodle = get_moodle(os.getenv("SUBDOMAIN"))[0]
  #  alumnos_moodle = get_alumnos_moodle_no_borrados(moodle) # Alumnos que figuran en moodle antes de ejecutar el script
    
    ## 1. Obtener los alumnos actuales en sigad
    logger.info("## 1. Recuperación de todo el alumnado matriculado en SIGAD")
    nombre_fichero = api_client.main()
    logger.info(f"### Datos recuperados en: \" "+ nombre_fichero +"\"")
    registro_sigad = json_parser.cargar_fichero_estudiantes()

    logger.info(f"### Total de alumnos recuperados de SIGAD: " + str(len(registro_sigad.alumnos)) )
    

    # ----------------------------------------------
    ## REINCORPORACION: Un alumno puede estar suspendido en moodle y que ahora aparezca en sigad -> Dar de alta 
    
    ## ACTUALIZACION_EMAIL: Un alumno ha cambiado su email en sigad -> Modificarlo en moodle
    ## CAMBIO_NIE_A_DNI: Cuidado! 
    ## ACTUALIZACION_CURSOS:
    ##     BAJAS_COMPLETAS
    ##     BAJAS_EN_MODULOS
    ##     ALTAS_EN_MODULOS
    ##     NUEVAS_ALTAS
    ##     LIMPIEZA_AGOSTO
    # -----------------------------------------------------------------------------
  
def main():
    try:
        gestion_alumnos() 
    except Exception as exc:
        print("1.- traceback.print_exc()")
        traceback.print_exc()
        print("2.- traceback.print_exception(*sys.exc_info())")
        traceback.print_exception(*sys.exc_info())
        print("--------------------")
        print(exc)       

if __name__ == "__main__":
    main()