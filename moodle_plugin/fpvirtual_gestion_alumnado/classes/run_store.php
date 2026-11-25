<?php
// Almacenamiento del historial de ejecuciones y de sus logs.

namespace local_fpvirtual_gestion_alumnado;

defined('MOODLE_INTERNAL') || die();

/**
 * Gestiona la tabla de ejecuciones y los ficheros de log en dataroot.
 *
 * Cada ejecución del proceso (manual o cron) queda registrada con su
 * origen, modo, tiempos, código de salida, resumen y ruta al log.
 */
class run_store {

    /** Nombre de la tabla (sin prefijo). */
    public const TABLE = 'local_fpvirtual_gestion_alumnado_run';

    /** Directorio (bajo dataroot) donde se guardan los logs del modo comando externo. */
    public const LOG_SUBDIR = 'fpvirtual_gestion_alumnado/logs';

    /** Directorio (bajo dataroot) con un subdirectorio de artefactos por ejecución. */
    public const RUNS_SUBDIR = 'fpvirtual_gestion_alumnado/runs';

    /** Estados de una ejecución. */
    public const STATUS_SUCCESS = 'success';
    /** La ejecución terminó con errores. */
    public const STATUS_ERROR = 'error';
    /** Una guarda de seguridad impidió aplicar los cambios. */
    public const STATUS_ABORTED = 'aborted';
    /** En curso. */
    public const STATUS_RUNNING = 'running';

    /** Artefactos descargables de una ejecución: clave => [fichero, tipo MIME, requiere capacidad launch]. */
    public const ARTIFACTS = [
        'log' => ['output.log', 'text/plain', false],
        'report' => ['informe.md', 'text/markdown', false],
        'plan' => ['plan.json', 'application/json', false],
        'csv' => ['altas_google.csv', 'text/csv', true],
        'sigad' => ['sigad.json', 'application/json', true],
    ];

    /**
     * Registra el inicio de una ejecución y devuelve su id.
     *
     * @param string $origen 'manual' o 'cron'
     * @param string $modo 'dry' o 'apply'
     * @return int id del registro
     */
    public static function start(string $origen, string $modo): int {
        global $DB;

        $record = (object)[
            'origen' => $origen,
            'modo' => $modo,
            'timestart' => time(),
            'timeend' => null,
            'exitcode' => null,
            'status' => 'running',
            'summary' => null,
            'logfile' => null,
        ];

        return (int)$DB->insert_record(self::TABLE, $record);
    }

    /**
     * Finaliza una ejecución: guarda el log y actualiza el registro.
     *
     * @param int $runid
     * @param int $exitcode código de salida del proceso
     * @param string $output salida completa (stdout + stderr)
     */
    public static function finish(int $runid, int $exitcode, string $output, ?array $summary = null,
            ?string $status = null): void {
        global $DB;

        $logfile = self::run_dir($runid) . '/' . self::ARTIFACTS['log'][0];
        file_put_contents($logfile, $output);

        $record = (object)[
            'id' => $runid,
            'timeend' => time(),
            'exitcode' => $exitcode,
            'status' => $status ?? ($exitcode === 0 ? self::STATUS_SUCCESS : self::STATUS_ERROR),
            'logfile' => $logfile,
        ];
        if ($summary !== null) {
            $record->summary = json_encode($summary, JSON_UNESCAPED_UNICODE);
        }
        $DB->update_record(self::TABLE, $record);
    }

    /**
     * Directorio de artefactos de una ejecución (lo crea si no existe).
     *
     * @param int $runid
     * @return string ruta absoluta
     */
    public static function run_dir(int $runid): string {
        global $CFG;
        return make_writable_directory($CFG->dataroot . '/' . self::RUNS_SUBDIR . '/' . $runid);
    }

    /**
     * Ruta de un artefacto si existe.
     *
     * @param \stdClass $run
     * @param string $key clave de {@see self::ARTIFACTS}
     * @return string|null
     */
    public static function artifact(\stdClass $run, string $key): ?string {
        global $CFG;
        if (!isset(self::ARTIFACTS[$key])) {
            return null;
        }
        if ($key === 'log' && !empty($run->logfile)) {
            return is_file($run->logfile) ? $run->logfile : null;
        }
        $path = $CFG->dataroot . '/' . self::RUNS_SUBDIR . '/' . (int)$run->id . '/' . self::ARTIFACTS[$key][0];
        return is_file($path) ? $path : null;
    }

    /**
     * Devuelve la última ejecución registrada (cualquier estado).
     *
     * @return \stdClass|null
     */
    public static function latest(): ?\stdClass {
        global $DB;

        $record = $DB->get_records(self::TABLE, [], 'timestart DESC', '*', 0, 1);
        return $record ? reset($record) : null;
    }

    /**
     * Devuelve una ejecución por id.
     *
     * @param int $runid
     * @return \stdClass|null
     */
    public static function get(int $runid): ?\stdClass {
        global $DB;

        $record = $DB->get_record(self::TABLE, ['id' => $runid]);
        return $record ?: null;
    }

    /**
     * Lista de ejecuciones más recientes para el historial.
     *
     * @param int $limit
     * @param int $offset
     * @return \stdClass[]
     */
    public static function recent(int $limit = 50, int $offset = 0): array {
        global $DB;

        return $DB->get_records(self::TABLE, [], 'timestart DESC', '*', $offset, $limit);
    }

    /**
     * Cuenta el total de ejecuciones registradas.
     *
     * @return int
     */
    public static function count(): int {
        global $DB;

        return $DB->count_records(self::TABLE);
    }

    /**
     * Elimina ejecuciones anteriores al timestamp dado, junto a sus logs.
     *
     * @param int $olderthan epoch; se purgan las ejecuciones con timestart anterior
     * @return int número de registros eliminados
     */
    public static function purge(int $olderthan): int {
        global $DB;

        global $CFG;

        $olds = $DB->get_records_select(self::TABLE, 'timestart < :t', ['t' => $olderthan]);
        foreach ($olds as $old) {
            if (!empty($old->logfile) && is_file($old->logfile)) {
                unlink($old->logfile);
            }
            $dir = $CFG->dataroot . '/' . self::RUNS_SUBDIR . '/' . (int)$old->id;
            if (is_dir($dir)) {
                remove_dir($dir);
            }
        }
        $DB->delete_records_select(self::TABLE, 'timestart < :t', ['t' => $olderthan]);

        return count($olds);
    }

    /**
     * Lee el contenido del log de una ejecución.
     *
     * @param \stdClass $run
     * @return string
     */
    public static function read_log(\stdClass $run): string {
        if (empty($run->logfile) || !is_file($run->logfile)) {
            return '';
        }

        return (string)file_get_contents($run->logfile);
    }

    /**
     * Directorio de logs (lo crea si no existe).
     *
     * @return string ruta absoluta
     */
    public static function log_dir(): string {
        global $CFG;

        $dir = $CFG->dataroot . DIRECTORY_SEPARATOR . self::LOG_SUBDIR;
        if (!is_dir($dir)) {
            mkdir($dir, $CFG->directorypermissions, true);
        }

        return $dir;
    }
}
