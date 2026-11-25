<?php
// This file is part of Moodle - http://moodle.org/
//
// Moodle is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// Moodle is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with Moodle.  If not, see <http://www.gnu.org/licenses/>.

/**
 * Ejecuta la sincronización SIGAD ↔ Moodle desde la línea de comandos.
 *
 * @package    local_fpvirtual_gestion_alumnado
 * @copyright  2026 FP virtual Aragón
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

define('CLI_SCRIPT', true);

// Directorio desde el que se lanzó el comando (para resolver rutas relativas).
$cwd = getcwd();

require(__DIR__ . '/../../../config.php');
require_once($CFG->libdir . '/clilib.php');

[$options, $unrecognized] = cli_get_params(
    ['mode' => 'dry', 'sigad-file' => '', 'force' => false, 'help' => false],
    ['m' => 'mode', 'f' => 'sigad-file', 'h' => 'help']
);

if ($unrecognized) {
    cli_error(get_string('cliunknowoption', 'admin', implode("\n  ", $unrecognized)));
}

if ($options['help'] || !in_array($options['mode'], ['dry', 'apply'], true)) {
    echo "Sincronización del alumnado de SIGAD con Moodle (local_fpvirtual_gestion_alumnado).

Opciones:
  -m, --mode=dry|apply   dry (por defecto): solo analiza e informa. apply: escribe los cambios.
                         Forma corta: -m=apply
  -f, --sigad-file=RUTA  Usa un fichero JSON de SIGAD en lugar de descargarlo (ruta absoluta
                         o relativa al directorio actual).
      --force            Aplica aunque el plan supere los límites de seguridad.
  -h, --help             Muestra esta ayuda.

Cada ejecución queda en el historial del plugin con su log, informe y plan.

Ejemplo:
  sudo -u www-data php local/fpvirtual_gestion_alumnado/cli/sync.php --mode=dry
";
    exit($options['help'] ? 0 : 1);
}

$sigadfile = null;
if ($options['sigad-file'] !== '') {
    $sigadfile = $options['sigad-file'];
    if ($sigadfile[0] !== '/' && $cwd !== false) {
        $sigadfile = $cwd . '/' . $sigadfile;
    }
    if (!is_readable($sigadfile)) {
        cli_error('No se puede leer el fichero de SIGAD: ' . $sigadfile);
    }
}

\core\cron::setup_user();

$engine = new \local_fpvirtual_gestion_alumnado\sync\engine(null, null, fn(string $line) => mtrace($line));
$run = $engine->run(
    $options['mode'],
    'cli',
    $sigadfile,
    (bool)$options['force']
);

mtrace('Artefactos: ' . \local_fpvirtual_gestion_alumnado\run_store::run_dir($run['runid']));
exit($run['exitcode']);
