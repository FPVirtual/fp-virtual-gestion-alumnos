# Plugin Moodle `fpvirtual_gestion_alumnado`

Plugin `local` para Moodle que acompaña al paquete Python
[`gestion_alumnos`](../../gestion_alumnos): sirve el *snapshot* de Moodle
vía webservice y ofrece al administrador un panel para lanzar, programar
y auditar el proceso de sincronización de alumnado.

> **Límite de responsabilidad:** el plugin **no** implementa la
> sincronización (extracción SIGAD, deltas, altas/bajas, emails). Toda esa
> lógica vive en el paquete Python. Este plugin solo:
>
> 1. **Sirve datos**: función webservice `local_fpvirtual_gestion_alumnado_get_snapshot`.
> 2. **Orquesta ejecuciones**: lanza el comando configurado (zipapp) en modo
>    dry-run o apply, manualmente o por cron.
> 3. **Audita**: registra cada ejecución y guarda sus logs, visibles en el admin.

## Requisitos

- Moodle 4.2+ (`$plugin->requires = 2023042400`). Producción: 4.5.
- El paquete Python desplegado y accesible desde el servidor Moodle
  (p. ej. `/opt/gestion_alumnos.pyz` con sus dependencias o entorno).

## Instalación

```bash
cp -r moodle_plugin/fpvirtual_gestion_alumnado /ruta/a/moodle/local/
```

A continuación, en Moodle: **Administración del sitio > Notificaciones** y
completa la instalación.

## Configuración

**Administración del sitio > Plugins > Local > FP Virtual: gestión de alumnado**

| Ajuste | Descripción |
|--------|-------------|
| Activar ejecución programada | Habilita la tarea cron (el lanzamiento manual es independiente) |
| Modo de ejecución | `dry` (por defecto) o `apply` |
| Comando del proceso | P. ej. `python3 /opt/gestion_alumnos.pyz` (el plugin añade `sync [--apply]`) |
| Variables de entorno adicionales | Un `VAR=valor` por línea |
| Timeout (segundos) | Máximo de ejecución (por defecto 600) |
| Retención de logs (días) | Purgar automáticamente (por defecto 30) |

### Configurar el servicio web del snapshot

1. Crea/edita el **servicio web externo** usado por el paquete Python y
   añade la función `local_fpvirtual_gestion_alumnado_get_snapshot`
   (ver [`docus/conexion_moodle_api.md`](../../docus/conexion_moodle_api.md)).
2. En Python, usa `MOODLE_SOURCE_STRATEGY=api-snapshot`.

### Configurar el cron

La tarea `local_fpvirtual_gestion_alumnado\task\sync_task` aparece en
**Administración del sitio > Servidor > Tareas programadas**, donde se
ajusta hora y frecuencia. El modo (dry/apply) y el interruptor general
están en los ajustes del plugin.

El cron de Moodle debe estar activo en el servidor (`cron.php` vía
crontab del sistema), como para cualquier tarea programada.

## Uso del panel

- **Gestión alumnado: ejecutar ahora** — botones para lanzar un dry-run o
  un apply inmediatos (en segundo plano vía tarea adhoc).
- **Gestión alumnado: estado** — configuración actual, estado y próxima
  ejecución de la tarea cron, y resultado de la última ejecución.
- **Gestión alumnado: logs** — historial paginado de ejecuciones con
  visualización y descarga de cada log.

## Permisos

| Capacidad | Quién la tiene por defecto | Para qué |
|-----------|---------------------------|----------|
| `local/fpvirtual_gestion_alumnado:usewebservice` | Nadie (asignar al rol del usuario de servicio) | Consumir el snapshot (datos personales: `RISK_PERSONAL`) |
| `local/fpvirtual_gestion_alumnado:viewstatus` | Manager | Ver estado e historial |
| `local/fpvirtual_gestion_alumnado:launch` | Manager | Lanzar el proceso manualmente |

El rol de administrador dispone de todas.

## Estructura

```
fpvirtual_gestion_alumnado/
├── version.php
├── settings.php             # Ajustes + entradas del menú admin
├── db/
│   ├── access.php           # Capacidades
│   ├── install.xml          # Tabla de ejecuciones
│   ├── services.php         # Función webservice del snapshot
│   └── tasks.php            # Tareas cron (sync + limpieza)
├── classes/
│   ├── external/get_snapshot.php  # local_fpvirtual_gestion_alumnado_get_snapshot
│   ├── runner.php           # Ejecuta el proceso Python (común a manual y cron)
│   ├── run_store.php        # Registro de ejecuciones + logs en dataroot
│   ├── task/sync_task.php       # Tarea programada
│   ├── task/adhoc_sync_task.php # Lanzamiento manual en segundo plano
│   ├── task/cleanup_task.php    # Purgar historial antiguo
│   └── privacy/provider.php
├── admin/
│   ├── launch.php           # Botones dry-run / apply
│   ├── status.php           # Última ejecución + próxima ejecución cron
│   └── logs.php             # Historial y visualización de logs
├── lang/en/, lang/es/
└── tests/external/get_snapshot_test.php
```

## Tests

Entorno Docker reproducible en [`../dev/`](../dev/) (Moodle limpio + MariaDB 10.11 +
PHP 8.2). Necesita un código fuente de Moodle **limpio** (nunca el de producción):

```bash
git clone --depth 1 -b MOODLE_405_STABLE https://github.com/moodle/moodle.git ~/moodle405
export MOODLE_DIR=~/moodle405
scripts/plugin-test.sh                    # todos los tests del plugin
scripts/plugin-test.sh --filter analyzer  # argumentos extra para phpunit
scripts/plugin-test.sh --down             # parar y borrar el entorno
```

La primera ejecución construye la imagen, instala las dependencias de Composer de
Moodle e inicializa la base de tests. Si cambia `version.php`, reinicializa con
`docker compose -f moodle_plugin/dev/docker-compose.yml exec php php admin/tool/phpunit/cli/init.php`.

En GitHub Actions se ejecuta `moodle-plugin-ci` contra Moodle 4.2 y 4.5
(`.github/workflows/moodle-plugin-ci.yml`).

## Troubleshooting

| Síntoma | Causa probable | Solución |
|---------|----------------|----------|
| `functionnotavailable` desde Python | La función no está añadida al servicio web | Añadir `local_fpvirtual_gestion_alumnado_get_snapshot` al servicio externo |
| El cron no ejecuta | Tarea deshabilitada o cron del sistema sin configurar | Activar en Tareas programadas; revisar crontab → `cron.php` |
| Ejecuciones con código 124 | Timeout alcanzado | Aumentar el timeout o revisar duración real del proceso |
| `error:nocommand` | Comando sin configurar | Ajustes del plugin > Comando del proceso |
| La dry-run está bien pero apply no aplica | `modo_lanzamiento = dry` | Cambiar el modo en los ajustes |
