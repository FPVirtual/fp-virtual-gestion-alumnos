#!/usr/bin/env bash
# Ejecuta los tests PHPUnit del plugin en el entorno Docker (moodle_plugin/dev).
#
#   MOODLE_DIR=/ruta/a/moodle scripts/plugin-test.sh            # todos los tests del plugin
#   MOODLE_DIR=... scripts/plugin-test.sh --filter analyzer     # args extra para phpunit
#   MOODLE_DIR=... scripts/plugin-test.sh --down                # parar y borrar el entorno
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE=(docker compose -f "$ROOT/moodle_plugin/dev/docker-compose.yml")
: "${MOODLE_DIR:?Define MOODLE_DIR con la ruta a un Moodle limpio (ver moodle_plugin/dev/docker-compose.yml)}"
export MOODLE_DIR

if [[ "${1:-}" == "--down" ]]; then
  "${COMPOSE[@]}" down -v
  exit 0
fi

"${COMPOSE[@]}" up -d --wait

run() { "${COMPOSE[@]}" exec -T php "$@"; }

if ! run test -f vendor/bin/phpunit; then
  echo ">> Instalando dependencias de Composer de Moodle (solo la primera vez)"
  run bash -c 'curl -sS https://getcomposer.org/installer | php -- --quiet && php composer.phar install --no-interaction --no-progress --quiet'
fi

if ! run php admin/tool/phpunit/cli/util.php --diag >/dev/null 2>&1; then
  echo ">> Inicializando el entorno PHPUnit de Moodle"
  run php admin/tool/phpunit/cli/init.php >/dev/null
fi

# Reconstruye la base de tests si cambia la versión del plugin.
run php admin/tool/phpunit/cli/util.php --buildconfig >/dev/null

run vendor/bin/phpunit --testsuite local_fpvirtual_gestion_alumnado_testsuite "$@"
