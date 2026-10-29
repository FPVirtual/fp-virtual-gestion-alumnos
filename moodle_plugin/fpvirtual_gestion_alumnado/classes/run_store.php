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

    /** Directorio (bajo dataroot) donde se guardan los logs. */
    public const LOG_SUBDIR = 'fpvirtual_gestion_alumnado/logs';

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
    public static function finish(int $runid, int $exitcode, string $output): void {
        global $DB;

        $logfile = self::log_dir() . '/run_' . $runid . '.log';
        file_put_contents($logfile, $output);

        $record = (object)[
            'id' => $runid,
            'timeend' => time(),
            'exitcode' => $exitcode,
            'status' => $exitcode === 0 ? 'success' : 'error',
            'logfile' => $logfile,
        ];
        $DB->update_record(self::TABLE, $record);
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

        $olds = $DB->get_records_select(self::TABLE, 'timestart < :t', ['t' => $olderthan]);
        foreach ($olds as $old) {
            if (!empty($old->logfile) && is_file($old->logfile)) {
                unlink($old->logfile);
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
