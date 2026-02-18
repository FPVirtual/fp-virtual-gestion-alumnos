"""
Ejemplos de uso del servicio de email.

Este archivo muestra cómo utilizar EmailService para enviar
notificaciones a usuarios e informes a administradores.
"""

from gestion_alumnos.utils.email_service import EmailService, crear_email_service
from gestion_alumnos.models import Alumno, Centro, Ciclo, Modulo


def ejemplo_crear_servicio():
    """Ejemplo de creación del servicio de email."""
    
    # Opción 1: Crear directamente
    email_service = EmailService(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        smtp_user="tu-email@gmail.com",
        smtp_password="tu-password",
        subdomain="www",  # "www" para producción
        templates_path="/var/fp-distancia-gestion-usuarios-automatica/templates",
        report_to="admin1@ejemplo.com admin2@ejemplo.com"
    )
    
    # Opción 2: Desde configuración (usando variables de entorno o Config.py)
    from Config import (
        SMTP_HOSTS, SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
        SUBDOMAIN, PATH, REPORT_TO
    )
    
    email_service = crear_email_service(
        smtp_host=SMTP_HOSTS,
        smtp_port=SMTP_PORT,
        smtp_user=SMTP_USER,
        smtp_password=SMTP_PASSWORD,
        subdomain=SUBDOMAIN,
        templates_path=f"{PATH}/templates",
        report_to=REPORT_TO
    )
    
    return email_service


def ejemplo_email_nuevo_usuario():
    """Ejemplo de envío de email a nuevo usuario."""
    
    # Crear servicio
    service = ejemplo_crear_servicio()
    
    # Crear alumno de ejemplo
    alumno = Alumno(
        idAlumno=12345,
        idTipoDocumento=1,
        documento="12345678A",
        nombre="María",
        apellido1="García",
        apellido2="López",
        email="maria.garcia@email.com",
        centros=[
            Centro(
                codigoCentro="Z00001",
                centro="IES Ejemplo",
                ciclos=[
                    Ciclo(
                        idFicha=100,
                        codigoCiclo="ADG201",
                        ciclo="Gestión Administrativa",
                        siglasCiclo="GAD",
                        modulos=[
                            Modulo(
                                idMateria=14634,
                                modulo="Comunicación empresarial",
                                siglasModulo="CEAC"
                            )
                        ]
                    )
                ]
            )
        ]
    )
    
    # Enviar email de bienvenida
    matriculado_en = [
        "<b>Gestión Administrativa</b> - Comunicación empresarial",
        "<b>Gestión Administrativa</b> - Técnica contable"
    ]
    
    exito = service.enviar_email_nuevo_usuario(
        alumno=alumno,
        password="Pass1234!",
        matriculado_en_texto="<br/>".join(matriculado_en)
    )
    
    if exito:
        print("Email enviado correctamente")
    else:
        print("Error al enviar email")


def ejemplo_email_usuario_actualizado():
    """Ejemplo de envío de email cuando cambia el usuario (NIE→DNI)."""
    
    service = ejemplo_crear_servicio()
    
    alumno = Alumno(
        idAlumno=12345,
        idTipoDocumento=1,
        documento="12345678A",
        nombre="María",
        apellido1="García",
        apellido2="López",
        email="maria.garcia@email.com",
        centros=[]
    )
    
    exito = service.enviar_email_usuario_actualizado(
        alumno=alumno,
        old_usuario="X1234567L",
        nuevo_usuario="12345678A"
    )
    
    print(f"Email de actualización enviado: {exito}")


def ejemplo_email_matriculas_añadidas():
    """Ejemplo de envío de email con nuevas matrículas."""
    
    service = ejemplo_crear_servicio()
    
    alumno = Alumno(
        idAlumno=12345,
        idTipoDocumento=1,
        documento="12345678A",
        nombre="María",
        apellido1="García",
        apellido2="López",
        email="maria.garcia@email.com",
        centros=[]
    )
    
    nuevas_matriculas = [
        "<b>Administración y Finanzas</b> - Contabilidad y fiscalidad",
        "<b>Administración y Finanzas</b> - Gestión financiera"
    ]
    
    exito = service.enviar_email_matriculas_añadidas(
        alumno=alumno,
        matriculado_en_texto="<br/>".join(nuevas_matriculas)
    )
    
    print(f"Email de matrículas enviado: {exito}")


def ejemplo_enviar_informe():
    """Ejemplo de envío de informe a administradores."""
    
    service = ejemplo_crear_servicio()
    
    # Enviar informe de ejecución exitosa
    exito = service.enviar_informe_ejecucion(
        filename_md="/logs/informe_2024-01-15.md",
        filename_csv="/logs/alumnos_2024-01-15.csv",
        resumen={
            "alumnos_creados": 10,
            "alumnos_suspendidos": 2,
            "emails_enviados": 12
        }
    )
    
    print(f"Informe enviado: {exito}")


def ejemplo_enviar_error():
    """Ejemplo de envío de notificación de error."""
    
    service = ejemplo_crear_servicio()
    
    import traceback
    
    try:
        # Simular un error
        raise ValueError("Error de conexión a la base de datos")
    except Exception as e:
        tb_str = traceback.format_exc()
        
        exito = service.enviar_error_informe(
            filename_md="/logs/informe_2024-01-15.md",
            filename_csv="/logs/alumnos_2024-01-15.csv",
            error=e,
            traceback_str=tb_str
        )
        
        print(f"Notificación de error enviada: {exito}")


def ejemplo_verificar_limites():
    """Ejemplo de verificación de límites de envío."""
    
    service = ejemplo_crear_servicio()
    
    # Ver estadísticas
    stats = service.obtener_estadisticas()
    print(f"Estadísticas: {stats}")
    
    # Verificar si se alcanzó el límite
    if service.limite_alcanzado():
        print("¡Límite de emails diarios alcanzado!")
    else:
        disponibles = stats["disponibles"]
        print(f"Emails disponibles hoy: {disponibles}")


def ejemplo_flujo_completo():
    """
    Ejemplo de flujo completo de uso del servicio de email
    en el contexto de la gestión de alumnos.
    """
    from Config import (
        SMTP_HOSTS, SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
        SUBDOMAIN, PATH, REPORT_TO
    )
    
    # 1. Inicializar servicio
    email_service = crear_email_service(
        smtp_host=SMTP_HOSTS,
        smtp_port=SMTP_PORT,
        smtp_user=SMTP_USER,
        smtp_password=SMTP_PASSWORD,
        subdomain=SUBDOMAIN,
        templates_path=f"{PATH}/templates",
        report_to=REPORT_TO
    )
    
    # 2. Procesar nuevos alumnos
    alumnos_nuevos = [...]  # Lista de objetos Alumno
    
    for alumno in alumnos_nuevos:
        if email_service.limite_alcanzado():
            print("Límite alcanzado, no se envían más emails")
            break
        
        # Generar contraseña y matrículas
        password = "generar_password()"
        matriculas = "<b>Ciclo</b> - Módulo<br/>"
        
        exito = email_service.enviar_email_nuevo_usuario(
            alumno=alumno,
            password=password,
            matriculado_en_texto=matriculas
        )
        
        if not exito:
            print(f"Error enviando email a {alumno.email}")
    
    # 3. Al finalizar, enviar informe
    email_service.enviar_informe_ejecucion(
        filename_md="/logs/informe.md",
        filename_csv="/logs/datos.csv"
    )
    
    # 4. Mostrar estadísticas finales
    stats = email_service.obtener_estadisticas()
    print(f"Resumen: {stats['emails_enviados']} enviados, "
          f"{stats['emails_no_enviados']} fallidos")


if __name__ == "__main__":
    print("Ejemplos de uso de EmailService")
    print("=" * 50)
    
    # Descomentar para probar cada ejemplo:
    # ejemplo_crear_servicio()
    # ejemplo_email_nuevo_usuario()
    # ejemplo_email_usuario_actualizado()
    # ejemplo_email_matriculas_añadidas()
    # ejemplo_enviar_informe()
    # ejemplo_enviar_error()
    # ejemplo_verificar_limites()
