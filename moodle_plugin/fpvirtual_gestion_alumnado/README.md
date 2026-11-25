# Plugin Moodle `local_fpvirtual_gestion_alumnado`

Sincroniza el alumnado de **SIGAD** con **Moodle** desde dentro de Moodle:
altas, cambios de documento, datos personales, cohortes, matrículas,
suspensiones, correos al alumnado e informe a los responsables.

- **Lecturas** con SQL a través de `$DB` (sin moosh ni MySQL externo).
- **Escrituras** solo con las APIs internas de Moodle (eventos, cachés y contextos correctos).
- **Plan revisable**: cada ejecución calcula un plan; en *dry-run* solo se informa.
- **Guardas de seguridad**: aborta si SIGAD no devuelve alumnos o si el plan supera los límites.

Reglas de negocio, decisiones y fases: [`docus/roadmap-v0.4-plugin-php.md`](../../docus/roadmap-v0.4-plugin-php.md).

## Requisitos

- Moodle 4.2+ (`$plugin->requires = 2023042400`). Producción: 4.5.
- Campos de perfil `IdSIGAD`, `emailsigad` (y opcionalmente `tipoDocumento`, `consentimientoCDD`).
- Cohortes `alumnado` y `{codigoCentro}-{siglasCiclo}`; cursos `{codigoCentro}-{siglasCiclo}-{idMateria}`
  con matriculación manual activa.

## Instalación

```bash
cp -r moodle_plugin/fpvirtual_gestion_alumnado /ruta/a/moodle/local/
```

Después, **Administración del sitio > Notificaciones** para completar la instalación.

## Configuración

**Administración del sitio > Plugins > Plugins locales > FP Virtual: gestión de alumnado**

| Sección | Ajustes principales |
|---------|---------------------|
| Ejecución | Activar tarea programada, modo (`dry`/`apply`), motor (integrado / comando externo), retención |
| Conexión con SIGAD | URL base, usuario, contraseña (cifrada), timeout, espera y reintentos |
| Reglas | Dominio del email, prefijos excluidos (`prof`), usuarios protegidos, cursos excluidos (`ayuda`), cohorte general, sincronizar nombres, limpieza anual (agosto) |
| Límites de seguridad | Máximo de usuarios suspendidos y % de matrículas suspendidas por ejecución |
| Notificaciones | Activar, redirigir a un buzón de pruebas, límite diario, pausa, destinatarios del informe, curso de ayuda, URL de soporte |

> **Preproducción:** rellena *Redirigir los correos del alumnado a* para que ningún correo llegue a alumnos reales.

El horario se ajusta en **Administración del sitio > Servidor > Tareas programadas**
(`local_fpvirtual_gestion_alumnado\task\sync_task`, por defecto a las 04:00).

## Uso

### Panel

- **Gestión alumnado: ejecutar ahora** — lanza un dry-run o un apply en segundo plano (tarea adhoc).
- **Gestión alumnado: estado** — configuración, tarea programada y resumen de la última ejecución.
- **Gestión alumnado: historial** — cada ejecución con su resumen, informe y ficheros descargables
  (log, informe, plan; el CSV de altas y la copia de SIGAD solo con la capacidad `:launch`).

### Línea de comandos

```bash
sudo -u www-data php local/fpvirtual_gestion_alumnado/cli/sync.php --mode=dry
sudo -u www-data php local/fpvirtual_gestion_alumnado/cli/sync.php --mode=apply
sudo -u www-data php local/fpvirtual_gestion_alumnado/cli/sync.php --mode=dry --sigad-file=/ruta/sigad.json
sudo -u www-data php local/fpvirtual_gestion_alumnado/cli/sync.php --mode=apply --force   # ignora los límites
```

Códigos de salida: `0` correcta, `1` error, `2` detenida por una guarda de seguridad.

### Artefactos de cada ejecución

En `{dataroot}/fpvirtual_gestion_alumnado/runs/{id}/`: `output.log`, `informe.md`, `plan.json`,
`altas_google.csv` (permisos 0600, contiene contraseñas iniciales) y `sigad.json`. Se purgan
con la retención configurada.

## Permisos

| Capacidad | Por defecto | Para qué |
|-----------|-------------|----------|
| `local/fpvirtual_gestion_alumnado:viewstatus` | Manager | Ver estado, historial e informes |
| `local/fpvirtual_gestion_alumnado:launch` | Manager | Lanzar manualmente; descargar CSV de altas y copia de SIGAD |
| `local/fpvirtual_gestion_alumnado:usewebservice` | Nadie | Función webservice `get_snapshot` (solo para el motor externo en transición) |

## Desarrollo y tests

Entorno Docker reproducible en [`../dev/`](../dev/) (Moodle limpio + MariaDB 10.11 + PHP 8.2).
Necesita un código fuente de Moodle **limpio** (nunca el de producción):

```bash
git clone --depth 1 -b MOODLE_405_STABLE https://github.com/moodle/moodle.git ~/moodle405
export MOODLE_DIR=~/moodle405
scripts/plugin-test.sh                    # todos los tests del plugin
scripts/plugin-test.sh --filter analyzer  # argumentos extra para phpunit
scripts/plugin-test.sh --down             # parar y borrar el entorno
```

Si cambia `version.php`, reinicializa con
`docker compose -f moodle_plugin/dev/docker-compose.yml exec php php admin/tool/phpunit/cli/init.php`.

En GitHub Actions se ejecuta `moodle-plugin-ci` (lint, validate, phpcs, PHPUnit) contra Moodle 4.2 y 4.5.

## Estructura

```
fpvirtual_gestion_alumnado/
├── classes/
│   ├── config.php              # Ajustes con valores por defecto
│   ├── sigad/                  # client (HTTP), parser, dataset
│   ├── sync/                   # moodle_state, analyzer, plan, applier, notifier, report, engine
│   ├── runner.php              # Punto de entrada común (cron/manual)
│   ├── run_store.php           # Historial y artefactos
│   ├── output/helper.php       # Fragmentos del panel
│   ├── task/                   # sync_task, adhoc_sync_task, cleanup_task
│   └── external/get_snapshot.php
├── cli/sync.php
├── admin/                      # status, logs, launch
├── templates/                  # Correos (Mustache)
├── db/ lang/ tests/
```

## Troubleshooting

| Síntoma | Causa probable | Solución |
|---------|----------------|----------|
| Ejecución «Detenida por seguridad» | SIGAD sin alumnos o plan por encima de los límites | Revisar el informe; si es correcto, `cli/sync.php --mode=apply --force` |
| «Faltan las credenciales de SIGAD» | Usuario/contraseña vacíos | Ajustes > Conexión con SIGAD |
| Avisos «Cursos que no existen en Moodle» | Curso `{centro}-{ciclo}-{idMateria}` no creado | Crear el curso; la matrícula se hará en la siguiente ejecución |
| Errores `create_user` por contraseña | Política de contraseñas muy estricta | Se usa `generate_password()` si la alfanumérica no cumple; revisar política |
| No llegan correos | Correo de Moodle sin configurar, redirección activa o límite diario | Revisar SMTP de Moodle y los ajustes de notificaciones |
