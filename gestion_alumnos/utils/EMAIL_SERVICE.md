# Servicio de Email - Documentación

## Resumen

El `EmailService` es un módulo dedicado a la gestión de envíos de email en la aplicación de gestión de alumnos. Proporciona funcionalidades para enviar notificaciones a usuarios e informes a administradores, con control de límites diarios según el entorno.

## Estructura

```
gestion_alumnos/utils/
├── __init__.py              # Exporta EmailService y crear_email_service_desde_env
├── email_service.py         # Clase principal EmailService
├── email_service_example.py # Ejemplos de uso
└── EMAIL_SERVICE.md         # Esta documentación
```

## Características

- ✅ **Múltiples tipos de email**: Nuevos usuarios, actualizaciones, matrículas, informes
- ✅ **Gestión de límites**: 1000 emails/día en producción, 10 en otros entornos
- ✅ **Soporte de adjuntos**: Para envío de informes con archivos MD y CSV
- ✅ **Redirección segura**: En entornos no productivos redirige a cuenta de control
- ✅ **Sistema de templates**: Usa archivos HTML con placeholders
- ✅ **Logging integrado**: Registra todos los envíos y errores
- ✅ **Estadísticas**: Contador de emails enviados, fallidos y disponibles

## Templates Disponibles

Los templates HTML se encuentran en `gestion_alumnos/templates/`:

| Template | Uso | Parámetros |
|----------|-----|------------|
| `nuevoUsuario.html` | Bienvenida a nuevos alumnos | nombre, apellidos, subdomain, usuario, contrasena, matriculado_en_texto, email |
| `nombreUsuarioActualizado.html` | Notificar cambio NIE→DNI | subdomain, usuario, oldUsuario |
| `matriculasAnadidas.html` | Nuevas matrículas | nombre, apellidos, subdomain, matriculado_en_texto |
| `informeAutomatizado.html` | Informe de ejecución | subdomain, filename_md, filename_csv |
| `haFalladoElInforme.html` | Notificación de error | subdomain, filename_md, filename_csv, error, traceback, tracebackException |

## Uso Básico

### 1. Crear el servicio

```python
from gestion_alumnos.utils.email_service import EmailService, crear_email_service_desde_env
from dotenv import load_dotenv

# Cargar variables de entorno desde archivo .env
load_dotenv(".env.produccion")  # o .env.preproduccion, .env.test

# Opción 1: Crear directamente (útil para testing)
service = EmailService(
    smtp_host="smtp.gmail.com",
    smtp_port=587,
    smtp_user="tu-email@gmail.com",
    smtp_password="tu-password",
    subdomain="www",  # "www" para producción
    templates_path="/ruta/a/templates",
    report_to="admin1@ejemplo.com admin2@ejemplo.com"
)

# Opción 2: Desde variables de entorno (recomendado)
service = crear_email_service_desde_env()
```

### Variables de Entorno Requeridas

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `SMTP_HOSTS` | Servidor SMTP | `smtp.gmail.com` |
| `SMTP_PORT` | Puerto SMTP | `587` |
| `SMTP_USER` | Usuario SMTP | `usuario@gmail.com` |
| `SMTP_PASSWORD` | Contraseña SMTP | `contraseña` |
| `SUBDOMAIN` | Entorno | `www`, `preproduccion`, `test` |
| `PATH` | Ruta base del proyecto | `/var/fp-distancia/` |
| `REPORT_TO` | Emails para informes | `admin1@ej.com admin2@ej.com` |

### 2. Ejemplo Completo con .env

```python
from dotenv import load_dotenv
from gestion_alumnos.utils.email_service import crear_email_service_desde_env
from gestion_alumnos.models import Alumno

# Cargar configuración según entorno
# load_dotenv(".env.produccion")
# load_dotenv(".env.preproduccion")
load_dotenv(".env.test")

# Crear servicio
service = crear_email_service_desde_env()

# Crear alumno de ejemplo
alumno = Alumno(
    idAlumno=12345,
    idTipoDocumento=1,
    documento="12345678A",
    nombre="María",
    apellido1="García",
    apellido2="López",
    email="maria@email.com",
    centros=[]
)

# Enviar email de bienvenida
exito = service.enviar_email_nuevo_usuario(
    alumno=alumno,
    password="Pass1234!",
    matriculado_en_texto="<b>Gestión Administrativa</b> - Comunicación empresarial<br/>"
)

# Verificar estado
if exito:
    print("Email enviado correctamente")
else:
    print("Error al enviar email")

# Enviar informe a administradores (REPORT_TO)
service.enviar_informe_ejecucion(
    filename_md="/logs/informe_2024-01-15.md",
    filename_csv="/logs/alumnos_2024-01-15.csv"
)
```

## API Reference

### Clase `EmailService`

#### Constructor

```python
EmailService(
    smtp_host: str,        # Servidor SMTP
    smtp_port: int,        # Puerto SMTP
    smtp_user: str,        # Usuario SMTP
    smtp_password: str,    # Contraseña SMTP
    subdomain: str,        # Entorno (www, preproduccion, test)
    templates_path: str,   # Ruta a templates HTML
    report_to: str         # Emails para reportes (separados por espacios)
)
```

### Función `crear_email_service_desde_env()`

Crea un `EmailService` usando variables de entorno:

```python
from gestion_alumnos.utils.email_service import crear_email_service_desde_env
from dotenv import load_dotenv

load_dotenv(".env.produccion")
service = crear_email_service_desde_env()
```

**Variables de entorno requeridas:**
- `SMTP_HOSTS`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASSWORD`

**Variables opcionales:**
- `SUBDOMAIN` (default: "test")
- `PATH` (default: "/")
- `REPORT_TO` (default: "")

#### Métodos principales

| Método | Descripción | Retorna |
|--------|-------------|---------|
| `enviar_email_nuevo_usuario(alumno, password, matriculado_en_texto)` | Email de bienvenida | bool |
| `enviar_email_usuario_actualizado(alumno, old_usuario, nuevo_usuario)` | Notificar cambio de usuario | bool |
| `enviar_email_matriculas_añadidas(alumno, matriculado_en_texto)` | Notificar nuevas matrículas | bool |
| `enviar_informe_ejecucion(filename_md, filename_csv, resumen)` | Enviar informe a REPORT_TO | bool |
| `enviar_error_informe(filename_md, filename_csv, error, traceback_str)` | Notificar error | bool |
| `limite_alcanzado()` | Verificar si se alcanzó el límite | bool |
| `obtener_estadisticas()` | Estadísticas de envío | dict |

#### Atributos

| Atributo | Descripción |
|----------|-------------|
| `emails_enviados` | Contador de emails enviados en la sesión |
| `emails_no_enviados` | Contador de fallos de envío |
| `max_emails_diarios` | Límite según entorno (1000 en prod, 10 en otros) |

## Límites de Envío

| Entorno | Subdominio | Límite |
|---------|------------|--------|
| Producción | `www` | 1000 emails/día |
| Preproducción | `preproduccion` | 10 emails/día |
| Test | `test` | 10 emails/día |

En entornos no productivos, los emails se redirigen a `gestion@fpvirtualaragon.es`.

## Testing

Ejecutar tests:

```bash
poetry run pytest tests/test_email_service.py -v
```

Con cobertura:

```bash
poetry run pytest tests/test_email_service.py --cov=gestion_alumnos.utils.email_service
```

## Ejemplos

Ver `email_service_example.py` para ejemplos completos de:
- Creación del servicio
- Envío de emails a nuevos usuarios
- Envío de emails de actualización
- Envío de informes
- Manejo de errores
- Verificación de límites
- Flujo completo de uso

## Integración con el Sistema

El servicio se integra con:
- **models.py**: Usa las dataclasses `Alumno`, `Centro`, `Ciclo`, `Modulo`
- **Config.py**: Obtiene configuración SMTP y paths
- **logger_config.py**: Registra actividad
- **templates/**: Archivos HTML con formato de emails

## Notas de Implementación

1. **Seguridad**: Las contraseñas SMTP se leen desde `Config.py` (no versionado)
2. **SSL/TLS**: Todos los envíos usan `STARTTLS` con contexto seguro
3. **HTML/Texto plano**: Los emails incluyen versión de texto plano como fallback
4. **MIMEBase**: Para adjuntos se usa codificación base64 estándar
5. **Excepciones**: Se capturan y loguean todos los errores, no se propagan
