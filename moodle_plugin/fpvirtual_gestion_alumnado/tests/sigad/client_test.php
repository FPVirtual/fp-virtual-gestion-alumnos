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
 * Tests del cliente de SIGAD (transporte HTTP simulado).
 *
 * @package    local_fpvirtual_gestion_alumnado
 * @copyright  2026 FP virtual Aragón
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 * @covers     \local_fpvirtual_gestion_alumnado\sigad\client
 */
final class client_test extends \advanced_testcase {
    /** @var string[] URLs pedidas. */
    private array $urls = [];

    /** @var array[] Cabeceras enviadas. */
    private array $headers = [];

    /** @var int[] Esperas realizadas. */
    private array $sleeps = [];

    /**
     * Cliente con respuestas simuladas en orden.
     *
     * @param array $responses lista de [status, body|array]
     * @param array $config
     * @return client
     */
    private function client(array $responses, array $config = []): client {
        $config = config::from_array($config + [
            'sigad_baseurl' => 'https://sigad.example/api/',
            'sigad_user' => 'u', 'sigad_password' => 'p',
            'sigad_maxretries' => 3, 'sigad_initialwait' => 7, 'sigad_retrydelay' => 2,
        ]);
        $http = function (string $url, array $headers) use (&$responses): array {
            $this->urls[] = $url;
            $this->headers[] = $headers;
            [$status, $body] = array_shift($responses);
            return [$status, is_array($body) ? json_encode($body) : $body];
        };
        return new client($config, $http, function (int $s): void {
            $this->sleeps[] = $s;
        });
    }

    public function test_curso_academico(): void {
        $this->assertSame(2025, client::academic_year(mktime(12, 0, 0, 1, 15, 2026)));
        $this->assertSame(2025, client::academic_year(mktime(12, 0, 0, 8, 31, 2026)));
        $this->assertSame(2026, client::academic_year(mktime(12, 0, 0, 9, 1, 2026)));
        $this->assertSame(2026, client::academic_year(mktime(12, 0, 0, 11, 25, 2026)));
    }

    public function test_descarga_en_dos_pasos_con_reintento(): void {
        $datos = ['fecha' => '01/01/2026', 'hora' => '00:00:00', 'alumnos' => [['documento' => '1A']]];
        $client = $this->client([
            [200, ['codigo' => 0, 'idSolicitud' => 77]],
            [200, ['codigo' => -1, 'mensaje' => 'no listo']],
            [200, ['codigo' => 0, 'estudiantes' => json_encode($datos)]],
        ]);

        $result = $client->fetch(mktime(0, 0, 0, 3, 1, 2026));

        $this->assertSame($datos, $result);
        $this->assertSame([
            'https://sigad.example/api/solicitud/2025',
            'https://sigad.example/api/fichero/77',
            'https://sigad.example/api/fichero/77',
        ], $this->urls);
        $this->assertSame([7, 2], $this->sleeps);
        $this->assertContains('usuario: u', $this->headers[0]);
        $this->assertContains('password: p', $this->headers[0]);
    }

    public function test_agota_reintentos(): void {
        $client = $this->client([
            [200, ['codigo' => 0, 'idSolicitud' => 1]],
            [200, ['codigo' => -1]], [200, ['codigo' => -1]], [200, ['codigo' => -1]],
        ]);

        $this->expectException(sigad_exception::class);
        $this->expectExceptionMessage('3 intentos');
        $client->fetch();
    }

    public function test_solicitud_rechazada(): void {
        $client = $this->client([[200, ['codigo' => 5, 'mensaje' => 'Usuario no autorizado']]]);

        $this->expectException(sigad_exception::class);
        $this->expectExceptionMessage('Usuario no autorizado');
        $client->fetch();
    }

    public function test_error_http_no_vuelca_el_cuerpo(): void {
        $client = $this->client([[500, 'secreto-interno password=p']]);

        try {
            $client->fetch();
            $this->fail('Debía lanzar excepción');
        } catch (sigad_exception $e) {
            $this->assertStringContainsString('HTTP 500', $e->getMessage());
            $this->assertStringNotContainsString('secreto', $e->getMessage());
        }
    }

    public function test_sin_credenciales(): void {
        $client = $this->client([], ['sigad_user' => '']);

        $this->expectException(sigad_exception::class);
        $client->fetch();
    }
}
