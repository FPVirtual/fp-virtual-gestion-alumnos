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

namespace local_fpvirtual_gestion_alumnado\sigad;

use local_fpvirtual_gestion_alumnado\config;

/**
 * Cliente del servicio de SIGAD (alumnado de FP a distancia).
 *
 * Protocolo en dos pasos:
 *  1. GET {base}/solicitud/{curso}   → {codigo: 0, idSolicitud: N}
 *  2. GET {base}/fichero/{N}         → {codigo: 0, estudiantes: "<json>"}
 *     (codigo -1 mientras el fichero se genera: se reintenta)
 *
 * Las credenciales viajan en cabeceras (usuario/password) porque así lo
 * exige el servicio. Los errores nunca incluyen el cuerpo de la respuesta.
 *
 * @package    local_fpvirtual_gestion_alumnado
 * @copyright  2026 FP virtual Aragón
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class client {
    /** @var config */
    protected config $config;

    /** @var callable(string, array): array{0:int,1:string} Hace un GET y devuelve [status, body]. */
    protected $http;

    /** @var callable(int): void Espera N segundos. */
    protected $sleep;

    /** @var callable(string): void Registro de progreso. */
    protected $log;

    /**
     * Constructor.
     *
     * @param config $config
     * @param callable|null $http transporte HTTP (inyectable en tests)
     * @param callable|null $sleep función de espera (inyectable en tests)
     * @param callable|null $log registro de progreso
     */
    public function __construct(config $config, ?callable $http = null, ?callable $sleep = null, ?callable $log = null) {
        $this->config = $config;
        $this->http = $http ?? [$this, 'curl_get'];
        $this->sleep = $sleep ?? fn(int $s) => sleep($s);
        $this->log = $log ?? fn(string $m) => null;
    }

    /**
     * Año del curso académico que se pide a SIGAD.
     *
     * De enero a agosto se pide el curso que empezó el año anterior.
     *
     * @param int $time timestamp
     * @return int
     */
    public static function academic_year(int $time): int {
        $year = (int)date('Y', $time);
        return ((int)date('n', $time) <= 8) ? $year - 1 : $year;
    }

    /**
     * Descarga el fichero de alumnado y devuelve el JSON decodificado.
     *
     * @param int|null $time momento de referencia para el curso académico
     * @return array datos con claves fecha, hora y alumnos
     * @throws sigad_exception
     */
    public function fetch(?int $time = null): array {
        if ($this->config->str('sigad_user') === '' || $this->config->str('sigad_password') === '') {
            throw new sigad_exception('Faltan las credenciales de SIGAD en la configuración del plugin.');
        }
        $base = rtrim($this->config->str('sigad_baseurl'), '/');
        $curso = self::academic_year($time ?? time());

        ($this->log)("Solicitando a SIGAD el curso {$curso}");
        $respuesta = $this->get_json($base . '/solicitud/' . $curso);
        if (($respuesta['codigo'] ?? null) !== 0 || empty($respuesta['idSolicitud'])) {
            throw new sigad_exception('SIGAD rechazó la solicitud (código ' . var_export($respuesta['codigo'] ?? null, true) .
                '): ' . clean_param((string)($respuesta['mensaje'] ?? ''), PARAM_TEXT));
        }
        $idsolicitud = (int)$respuesta['idSolicitud'];
        ($this->log)("Solicitud aceptada: {$idsolicitud}");

        $intentos = max(1, $this->config->int('sigad_maxretries'));
        ($this->sleep)($this->config->int('sigad_initialwait'));
        for ($intento = 1; $intento <= $intentos; $intento++) {
            try {
                $respuesta = $this->get_json($base . '/fichero/' . $idsolicitud);
            } catch (sigad_exception $e) {
                if ($intento === $intentos) {
                    throw $e;
                }
                ($this->log)("Intento {$intento}/{$intentos} fallido: " . $e->getMessage());
                ($this->sleep)($this->config->int('sigad_retrydelay'));
                continue;
            }

            $codigo = $respuesta['codigo'] ?? null;
            if ($codigo === 0) {
                $datos = is_string($respuesta['estudiantes'] ?? null)
                    ? json_decode($respuesta['estudiantes'], true)
                    : ($respuesta['estudiantes'] ?? null);
                if (!is_array($datos)) {
                    throw new sigad_exception('SIGAD devolvió un fichero de estudiantes ilegible.');
                }
                ($this->log)('Fichero recibido: ' . count($datos['alumnos'] ?? []) . ' alumnos');
                return $datos;
            }
            if ($codigo !== -1) {
                throw new sigad_exception('SIGAD devolvió un error al descargar el fichero (código ' .
                    var_export($codigo, true) . ').');
            }
            ($this->log)("Fichero aún no disponible (intento {$intento}/{$intentos})");
            if ($intento < $intentos) {
                ($this->sleep)($this->config->int('sigad_retrydelay'));
            }
        }
        throw new sigad_exception("El fichero de SIGAD no estuvo disponible tras {$intentos} intentos.");
    }

    /**
     * GET con decodificación JSON.
     *
     * @param string $url
     * @return array
     * @throws sigad_exception
     */
    protected function get_json(string $url): array {
        [$status, $body] = ($this->http)($url, [
            'usuario: ' . $this->config->str('sigad_user'),
            'password: ' . $this->config->str('sigad_password'),
            'Accept: application/json',
        ]);
        if ($status !== 200) {
            throw new sigad_exception("SIGAD respondió HTTP {$status}.");
        }
        $json = json_decode($body, true);
        if (!is_array($json)) {
            throw new sigad_exception('SIGAD devolvió una respuesta que no es JSON.');
        }
        return $json;
    }

    /**
     * Transporte por defecto: curl de Moodle (respeta proxy y lista de hosts bloqueados).
     *
     * @param string $url
     * @param array $headers
     * @return array [status, body]
     * @throws sigad_exception
     */
    protected function curl_get(string $url, array $headers): array {
        global $CFG;
        require_once($CFG->libdir . '/filelib.php');

        $curl = new \curl();
        $curl->setHeader($headers);
        $body = $curl->get($url, null, [
            'CURLOPT_TIMEOUT' => $this->config->int('sigad_timeout'),
            'CURLOPT_CONNECTTIMEOUT' => 20,
        ]);
        if ($curl->get_errno()) {
            throw new sigad_exception('Error de conexión con SIGAD: ' . $curl->error);
        }
        return [(int)($curl->get_info()['http_code'] ?? 0), (string)$body];
    }
}
