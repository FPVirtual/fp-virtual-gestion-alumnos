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

namespace local_fpvirtual_gestion_alumnado\sync;

use local_fpvirtual_gestion_alumnado\config;
use local_fpvirtual_gestion_alumnado\run_store;
use local_fpvirtual_gestion_alumnado\sigad\client;
use local_fpvirtual_gestion_alumnado\sigad\parser;

/**
 * Orquesta una ejecución completa de la sincronización dentro de Moodle.
 *
 * SIGAD → parser → guardas → analizador → plan → (apply) → notificaciones
 * → informe. Cada ejecución queda registrada en run_store con sus artefactos
 * (log, informe, plan, CSV de altas y copia del fichero de SIGAD).
 *
 * @package    local_fpvirtual_gestion_alumnado
 * @copyright  2026 FP virtual Aragón
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class engine {
    /** Ejecución correcta. */
    public const EXIT_OK = 0;
    /** Error. */
    public const EXIT_ERROR = 1;
    /** Detenida por una guarda de seguridad (no se aplicó nada). */
    public const EXIT_GUARD = 2;

    /** @var config */
    protected config $config;

    /** @var client|null Cliente de SIGAD (inyectable). */
    protected ?client $client;

    /** @var callable|null Salida adicional del log (p. ej. mtrace en CLI/cron). */
    protected $echo;

    /** @var notifier|null Notificador (inyectable). */
    protected ?notifier $notifier;

    /** @var string[] Líneas del log de la ejecución. */
    protected array $lines = [];

    /**
     * Constructor.
     *
     * @param config|null $config
     * @param client|null $client
     * @param callable|null $echo
     * @param notifier|null $notifier
     */
    public function __construct(
        ?config $config = null,
        ?client $client = null,
        ?callable $echo = null,
        ?notifier $notifier = null
    ) {
        $this->config = $config ?? config::load();
        $this->client = $client;
        $this->echo = $echo;
        $this->notifier = $notifier;
    }

    /**
     * Ejecuta la sincronización.
     *
     * @param string $mode 'dry' o 'apply'
     * @param string $origin 'manual', 'cron' o 'cli'
     * @param string|null $sigadfile fichero JSON de SIGAD en lugar de descargarlo
     * @param bool $force aplicar aunque se superen las guardas de seguridad (solo CLI)
     * @param int|null $now momento de referencia
     * @return array{runid:int, exitcode:int, status:string, plan:?plan, result:?result}
     */
    public function run(string $mode, string $origin, ?string $sigadfile = null, bool $force = false, ?int $now = null): array {
        $mode = $mode === 'apply' ? 'apply' : 'dry';
        $now = $now ?? time();
        $this->lines = [];

        $runid = run_store::start($origin, $mode);
        $dir = run_store::run_dir($runid);
        $meta = ['runid' => $runid, 'modo' => $mode, 'origen' => $origin, 'inicio' => $now, 'violaciones' => []];
        $plan = null;
        $result = null;
        $notifier = $this->notifier ?? new notifier($this->config, fn(string $m) => $this->log($m));
        $exitcode = self::EXIT_ERROR;
        $status = run_store::STATUS_ERROR;

        $lock = \core\lock\lock_config::get_lock_factory(config::COMPONENT)->get_lock('sync', 0);
        if (!$lock) {
            $this->log('Ya hay otra sincronización en curso: se cancela esta ejecución.');
            run_store::finish($runid, self::EXIT_ERROR, $this->output(), ['mensaje' => 'Ejecución concurrente']);
            return ['runid' => $runid, 'exitcode' => self::EXIT_ERROR, 'status' => $status, 'plan' => null, 'result' => null];
        }

        try {
            \core_php_time_limit::raise();
            raise_memory_limit(MEMORY_HUGE);
            $this->log("Inicio de la ejecución #{$runid} (modo {$mode}, origen {$origin})");

            // 0. Guarda: campos de perfil configurados. Sin ellos no se empareja por
            // IdSIGAD y las escrituras se perderían en silencio.
            $problems = $this->config->profile_field_problems();
            if ($problems) {
                $meta['violaciones'] = $problems;
                $meta['mensaje'] = 'Campos de perfil mal configurados: se aborta sin consultar SIGAD. ' .
                    'Revise los ajustes de la sección Reglas.';
                $this->log($meta['mensaje']);
                foreach ($problems as $problem) {
                    $this->log('GUARDA: ' . $problem);
                }
                return $this->finish($runid, self::EXIT_GUARD, run_store::STATUS_ABORTED, $meta, new plan(), null, $notifier);
            }

            // 1-2. SIGAD.
            if ($sigadfile !== null) {
                $this->log("Leyendo SIGAD desde fichero: {$sigadfile}");
                $json = @file_get_contents($sigadfile);
                if ($json === false) {
                    throw new \moodle_exception('error:sigadfile', config::COMPONENT, '', $sigadfile);
                }
                $sigad = parser::parse_json($json);
            } else {
                $client = $this->client ?? new client($this->config, null, null, fn(string $m) => $this->log($m));
                $raw = $client->fetch($now);
                file_put_contents($dir . '/' . run_store::ARTIFACTS['sigad'][0], json_encode($raw, JSON_UNESCAPED_UNICODE));
                $sigad = parser::parse($raw);
            }
            $this->log("SIGAD: {$sigad->count()} alumnos, {$sigad->count_modules()} matrículas, " .
                count($sigad->discarded) . ' descartados');

            // 3. Guarda: SIGAD vacío (R17).
            if ($sigad->count() === 0) {
                $meta['mensaje'] = 'SIGAD no ha devuelto alumnos: se aborta para no suspender a todo el alumnado.';
                $this->log($meta['mensaje']);
                $exitcode = self::EXIT_GUARD;
                $status = run_store::STATUS_ABORTED;
                return $this->finish($runid, $exitcode, $status, $meta, new plan(), null, $notifier);
            }

            // 4. Análisis.
            $state = moodle_state::load($this->config);
            $plan = (new analyzer($sigad, $state, $this->config, $now))->analyze();
            file_put_contents(
                $dir . '/' . run_store::ARTIFACTS['plan'][0],
                json_encode($plan->to_array(), JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE)
            );
            foreach ($plan->counts() as $type => $count) {
                if ($count) {
                    $this->log("Plan: {$type} = {$count}");
                }
            }

            // 5. Guardas del plan (R17).
            $meta['violaciones'] = $plan->check_limits($this->config);
            foreach ($meta['violaciones'] as $v) {
                $this->log('GUARDA: ' . $v);
            }

            // 6. Aplicación.
            if ($mode === 'apply') {
                if ($meta['violaciones'] && !$force) {
                    $meta['mensaje'] = 'No se aplican cambios: el plan supera los límites de seguridad. ' .
                        'Revise el informe y, si es correcto, ejecútelo por CLI con --force.';
                    $this->log($meta['mensaje']);
                    $exitcode = self::EXIT_GUARD;
                    $status = run_store::STATUS_ABORTED;
                    return $this->finish($runid, $exitcode, $status, $meta, $plan, null, $notifier);
                }
                $applier = new applier($this->config, $sigad, $notifier, fn(string $m) => $this->log($m));
                $result = $applier->apply($plan);
                if ($result->created) {
                    $csv = $dir . '/' . run_store::ARTIFACTS['csv'][0];
                    file_put_contents($csv, report::google_csv($result->created));
                    chmod($csv, 0600);
                }
            }

            $exitcode = ($result && $result->error_count()) ? self::EXIT_ERROR : self::EXIT_OK;
            $status = $exitcode === self::EXIT_OK ? run_store::STATUS_SUCCESS : run_store::STATUS_ERROR;
            return $this->finish($runid, $exitcode, $status, $meta, $plan, $result, $notifier);
        } catch (\Throwable $e) {
            $meta['mensaje'] = 'Error: ' . $e->getMessage();
            $this->log($meta['mensaje']);
            $this->log($e->getTraceAsString());
            return $this->finish($runid, self::EXIT_ERROR, run_store::STATUS_ERROR, $meta, $plan, $result, $notifier);
        } finally {
            $lock->release();
        }
    }

    /**
     * Genera el informe, avisa a los responsables y cierra el registro de la ejecución.
     *
     * @param int $runid
     * @param int $exitcode
     * @param string $status
     * @param array $meta
     * @param plan|null $plan
     * @param result|null $result
     * @param notifier $notifier
     * @return array
     */
    protected function finish(
        int $runid,
        int $exitcode,
        string $status,
        array $meta,
        ?plan $plan,
        ?result $result,
        notifier $notifier
    ): array {
        $estados = [
            run_store::STATUS_SUCCESS => 'Correcta',
            run_store::STATUS_ERROR => 'Con errores',
            run_store::STATUS_ABORTED => 'Detenida por seguridad',
        ];
        $meta['estado'] = $estados[$status] ?? $status;
        $plan = $plan ?? new plan();
        $dir = run_store::run_dir($runid);

        try {
            $report = report::markdown($plan, $meta, $result, $notifier->stats);
            $reportfile = $dir . '/' . run_store::ARTIFACTS['report'][0];
            file_put_contents($reportfile, $report);

            $lineas = [];
            foreach (array_merge(plan::ACTIONS, plan::NOTICES) as $type) {
                if ($plan->count($type)) {
                    $lineas[] = ['etiqueta' => report::TITLES[$type], 'valor' => $plan->count($type)];
                }
            }
            if ($result && $result->error_count()) {
                $lineas[] = ['etiqueta' => 'Errores al aplicar', 'valor' => $result->error_count()];
            }
            $notifier->send_report([
                'ok' => $status === run_store::STATUS_SUCCESS,
                'estado' => $meta['estado'],
                'modo' => $meta['modo'],
                'runid' => $runid,
                'runurl' => (new \moodle_url('/local/fpvirtual_gestion_alumnado/admin/logs.php', ['runid' => $runid]))->out(false),
                'lineas' => $lineas,
                'mensaje' => $meta['mensaje'] ?? '',
            ], $reportfile, 'informe_' . $runid . '.md');
        } catch (\Throwable $e) {
            $this->log('Error generando o enviando el informe: ' . $e->getMessage());
        }

        $summary = [
            'estado' => $meta['estado'],
            'mensaje' => $meta['mensaje'] ?? '',
            'violaciones' => $meta['violaciones'],
            'plan' => array_filter($plan->counts()),
            'stats' => $plan->stats,
            'resultado' => $result ? $result->summary() : null,
            'emails' => $notifier->stats,
        ];
        $this->log("Fin de la ejecución #{$runid}: {$meta['estado']} (código {$exitcode})");
        run_store::finish($runid, $exitcode, $this->output(), $summary, $status);

        return ['runid' => $runid, 'exitcode' => $exitcode, 'status' => $status, 'plan' => $plan, 'result' => $result];
    }

    /**
     * Añade una línea al log de la ejecución.
     *
     * @param string $message
     */
    protected function log(string $message): void {
        $line = '[' . date('H:i:s') . '] ' . $message;
        $this->lines[] = $line;
        if ($this->echo) {
            ($this->echo)($line);
        }
    }

    /**
     * Log completo.
     *
     * @return string
     */
    protected function output(): string {
        return implode("\n", $this->lines) . "\n";
    }
}
