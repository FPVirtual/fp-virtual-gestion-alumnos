<?php
// Lanzador del proceso Python (zipapp) de gestión de alumnado.
//
// Único punto de ejecución compartido por el lanzamiento manual y la
// tarea cron. El plugin no implementa la sincronización: ejecuta el
// comando configurado y registra el resultado.

namespace local_fpvirtual_gestion_alumnado;

defined('MOODLE_INTERNAL') || die();

/**
 * Ejecuta el proceso de gestión de alumnado y registra la ejecución.
 */
class runner {

    /** Modos soportados. */
    public const MODOS = ['dry', 'apply'];

    /**
     * Lanza una ejecución completa (registro + proceso + log).
     *
     * @param string $modo 'dry' o 'apply'
     * @param string $origen 'manual' o 'cron'
     * @return int código de salida del proceso
     * @throws \moodle_exception si falta el comando configurado
     */
    public static function ejecutar(string $modo, string $origen): int {
        $runid = run_store::start($origen, $modo);

        try {
            [$exitcode, $output] = self::run_process(self::build_command($modo), self::timeout(), self::entorno());
        } catch (\Throwable $e) {
            $exitcode = 1;
            $output = 'Excepción al lanzar el proceso: ' . $e->getMessage();
        }

        run_store::finish($runid, $exitcode, $output);

        return $exitcode;
    }

    /**
     * Construye la línea de comando: comando configurado + subcomando sync.
     *
     * @param string $modo
     * @return string
     */
    public static function build_command(string $modo): string {
        $command = trim((string)get_config('local_fpvirtual_gestion_alumnado', 'command'));
        if ($command === '') {
            throw new \moodle_exception('error:nocommand', 'local_fpvirtual_gestion_alumnado');
        }

        $command .= ' sync';
        if ($modo === 'apply') {
            $command .= ' --apply';
        }

        return $command;
    }

    /**
     * Timeout configurado en segundos.
     *
     * @return int
     */
    public static function timeout(): int {
        $timeout = (int)get_config('local_fpvirtual_gestion_alumnado', 'timeout');
        return $timeout > 0 ? $timeout : 600;
    }

    /**
     * Variables de entorno: las del proceso actual + las extra configuradas.
     *
     * @return array
     */
    private static function entorno(): array {
        $env = $_ENV;
        $extra = (string)get_config('local_fpvirtual_gestion_alumnado', 'extraenv');
        foreach (preg_split('/\r\n|\r|\n/', $extra) as $linea) {
            $linea = trim($linea);
            if ($linea === '' || strpos($linea, '=') === false) {
                continue;
            }
            [$clave, $valor] = explode('=', $linea, 2);
            $env[trim($clave)] = trim($valor);
        }
        $env['MOODLE_SOURCE_STRATEGY'] = $env['MOODLE_SOURCE_STRATEGY'] ?? 'api-snapshot';

        return $env;
    }

    /**
     * Ejecuta un comando con captura de salida y timeout.
     *
     * @param string $command línea de comando completa (shell)
     * @param int $timeout segundos
     * @param array $env
     * @return array [exitcode, output]
     */
    private static function run_process(string $command, int $timeout, array $env): array {
        $descriptores = [
            0 => ['pipe', 'r'],
            1 => ['pipe', 'w'],
            2 => ['pipe', 'w'],
        ];
        $pipes = [];
        $process = proc_open($command, $descriptores, $pipes, null, $env);
        if (!is_resource($process)) {
            return [1, 'No se pudo lanzar el proceso: ' . $command];
        }

        fclose($pipes[0]);
        stream_set_blocking($pipes[1], false);
        stream_set_blocking($pipes[2], false);

        $salida = '';
        $inicio = time();
        $agotado = false;

        while (true) {
            $salida .= stream_get_contents($pipes[1]);
            $salida .= stream_get_contents($pipes[2]);

            $estado = proc_get_status($process);
            if (!$estado['running']) {
                break;
            }
            if ((time() - $inicio) > $timeout) {
                $agotado = true;
                proc_terminate($process);
                break;
            }
            usleep(100000); // 100 ms.
        }

        // Lectura final tras la terminación.
        $salida .= stream_get_contents($pipes[1]);
        $salida .= stream_get_contents($pipes[2]);
        fclose($pipes[1]);
        fclose($pipes[2]);

        $exitcode = proc_close($process);
        if ($agotado) {
            $salida .= "\n[plugin] Proceso terminado por timeout ({$timeout}s).\n";
            return [124, $salida];
        }
        if ($exitcode === -1) {
            // proc_close puede devolver -1 cuando el estado ya fue leído; se usa el del bucle.
            $exitcode = $estado['exitcode'] ?? 1;
        }

        return [(int)$exitcode, $salida];
    }
}
