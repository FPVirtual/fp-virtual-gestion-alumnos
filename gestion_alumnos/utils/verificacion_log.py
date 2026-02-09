import re
from pathlib import Path
from gestion_alumnos.logger_config import logger 

def extraer_resumen_final(carpeta_logs: str) -> dict:
    """
    Lee el último archivo .md de la carpeta dada (por fecha en el nombre)
    y extrae el resumen final del script.
    """
    carpeta = Path(carpeta_logs)
    archivos_md = list(carpeta.glob("*.md"))

    if not archivos_md:
        raise FileNotFoundError(f"No se encontraron archivos .md en {carpeta}")

    def extraer_fecha(archivo: Path):
        partes = archivo.stem.split("_")[:6]
        try:
            return tuple(map(int, partes))
        except ValueError:
            return (0, 0, 0, 0, 0, 0)

    ultimo_archivo = max(archivos_md, key=extraer_fecha)
    logger.info(f"Archivo más reciente detectado: {ultimo_archivo.name}")

    with ultimo_archivo.open(encoding="utf-8") as f:
        contenido = f.read()

    inicio = contenido.find("## RESUMEN de acciones llevadas a cabo por este script:")
    if inicio == -1:
        raise ValueError("No se encontró el bloque de resumen final.")

    bloque = contenido[inicio:]

    def extraer_valor(clave: str) -> int:
        match = re.search(rf"- {re.escape(clave)}: (\d+)", bloque)
        return int(match.group(1)) if match else 0

    resumen = {
        "alumnos_antes": extraer_valor("Alumnos existentes en moodle antes de ejecutar este programa"),
        "alumnos_despues": extraer_valor("Alumnos existentes en moodle despues de ejecutar este programa"),
        "alumnos_creados": extraer_valor("Alumnos creados por este script"),
        "alumnos_no_creados": extraer_valor("Alumnos que NO es posible crear por este script"),
        "alumnos_reactivados": extraer_valor("Alumnos reactivados por este script"),
        "alumnos_suspendidos": extraer_valor("Alumnos suspendidos por este script"),
        "logins_modificados": extraer_valor("Alumnos cuyo login ha sido modificado por este script"),
        "emails_modificados": extraer_valor("Alumnos cuyo email ha sido modificado por este script"),
        "matriculas_hechas": extraer_valor("Cantidad de matriculas hechas en modulos"),
        "matriculas_reactivadas": extraer_valor("Cantidad de matriculas reactivadas en modulos"),
        "matriculas_suspendidas": extraer_valor("Cantidad de matriculas suspendidas en modulos"),
        "matriculas_borradas_tutorias": extraer_valor("Cantidad de matriculas borradas en tutorías"),
        "matriculas_borradas_modulos": extraer_valor("Cantidad de matriculas borradas en modulos"),
        "matriculas_no_hechas": extraer_valor("Cantidad de matriculas no hechas por no existir el curso destino"),
        "emails_enviados": extraer_valor("Cantidad de emails enviados"),
        "emails_no_enviados": extraer_valor("Cantidad de emails NO enviados"),
    }

    logger.info("Resumen extraído del archivo más reciente:")
    for k, v in resumen.items():
        logger.info(f"{k}: {v}")

    return resumen

# Ejemplo de uso
if __name__ == "__main__":
    carpeta_logs = "../logs/tests"
    try:
        extraer_resumen_final(carpeta_logs)
    except Exception as e:
        logger.error(f"Error al extraer resumen: {e}")