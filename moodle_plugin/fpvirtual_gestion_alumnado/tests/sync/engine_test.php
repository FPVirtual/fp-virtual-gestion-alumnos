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
use local_fpvirtual_gestion_alumnado\runner;
use local_fpvirtual_gestion_alumnado\sigad\client;

/**
 * Tests de extremo a extremo del motor de sincronización.
 *
 * @package    local_fpvirtual_gestion_alumnado
 * @copyright  2026 FP virtual Aragón
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 * @covers     \local_fpvirtual_gestion_alumnado\sync\engine
 * @covers     \local_fpvirtual_gestion_alumnado\sync\report
 * @covers     \local_fpvirtual_gestion_alumnado\run_store
 */
final class engine_test extends \advanced_testcase {
    /** @var string Fichero SIGAD de ejemplo. */
    private string $fixture;

    /** @var \phpunit_message_sink */
    private $sink;

    protected function setUp(): void {
        parent::setUp();
        $this->resetAfterTest();
        $this->setAdminUser();
        unset_config('noemailever');
        $this->sink = $this->redirectEmails();
        $this->fixture = __DIR__ . '/../fixtures/sigad_basico.json';

        $gen = $this->getDataGenerator();
        foreach (['IdSIGAD', 'emailsigad'] as $field) {
            $gen->create_custom_profile_field(['datatype' => 'text', 'shortname' => $field, 'name' => $field]);
        }
        foreach (['alumnado', '50009348-IFC303', '22002521-SSC302'] as $cohort) {
            $gen->create_cohort(['name' => $cohort, 'idnumber' => $cohort]);
        }
        foreach (['50009348-IFC303-5001', '50009348-IFC303-5002', '22002521-SSC302-6001'] as $sn) {
            $gen->create_course(['shortname' => $sn]);
        }
    }

    /**
     * Motor con configuración de prueba.
     *
     * @param array $config
     * @param client|null $client
     * @return engine
     */
    private function engine(array $config = [], ?client $client = null): engine {
        return new engine(config::from_array($config + [
            'emailpause' => 0, 'reportto' => 'gestion@example.com', 'notifyredirect' => 'pruebas@example.com',
        ]), $client);
    }

    public function test_dry_run_no_escribe_y_deja_artefactos(): void {
        global $DB;

        $run = $this->engine()->run('dry', 'cli', $this->fixture);

        $this->assertSame(engine::EXIT_OK, $run['exitcode']);
        $this->assertSame(2, $run['plan']->count(plan::CREATE_USER));
        $this->assertNull($run['result']);
        $this->assertFalse($DB->record_exists('user', ['username' => '00000001r']));

        $record = run_store::get($run['runid']);
        $this->assertSame(run_store::STATUS_SUCCESS, $record->status);
        $this->assertSame('cli', $record->origen);
        $summary = json_decode($record->summary, true);
        $this->assertSame(2, $summary['plan'][plan::CREATE_USER]);
        $this->assertNotNull(run_store::artifact($record, 'plan'));
        $this->assertNotNull(run_store::artifact($record, 'log'));
        $this->assertNull(run_store::artifact($record, 'csv'));
        $informe = file_get_contents(run_store::artifact($record, 'report'));
        $this->assertStringContainsString('no se ha escrito nada en Moodle', $informe);
        $this->assertStringContainsString('00000001r: Ana De la Fuente Gil', $informe);

        // Solo el informe a responsables: en dry no se escribe al alumnado.
        $this->assertSame(['gestion@example.com'], array_column($this->sink->get_messages(), 'to'));
    }

    public function test_apply_crea_csv_notifica_y_es_idempotente(): void {
        global $DB;

        $run = $this->engine()->run('apply', 'manual', $this->fixture);

        $this->assertSame(engine::EXIT_OK, $run['exitcode'], json_encode($run['result']->errors));
        $this->assertTrue($DB->record_exists('user', ['username' => '00000001r']));
        $record = run_store::get($run['runid']);
        $csv = file_get_contents(run_store::artifact($record, 'csv'));
        $this->assertStringContainsString('00000001r@fpvirtualaragon.es', $csv);
        $this->assertStringContainsString('/Alumnado', $csv);
        $this->assertStringNotContainsString(
            'password',
            strtolower(json_encode(json_decode($record->summary))),
            'Las contraseñas no se guardan en el resumen'
        );

        $to = array_column($this->sink->get_messages(), 'to');
        $this->assertSame(2, count(array_keys($to, 'pruebas@example.com')), 'Dos bienvenidas redirigidas');
        $this->assertContains('gestion@example.com', $to);

        $second = $this->engine()->run('apply', 'manual', $this->fixture);
        $this->assertSame(0, $second['plan']->total_actions());
    }

    public function test_sigad_vacio_aborta(): void {
        $this->getDataGenerator()->create_user(['username' => '11111111h']);
        $empty = make_request_directory() . '/vacio.json';
        file_put_contents($empty, json_encode(['fecha' => '01/01/2026', 'hora' => '00:00:00', 'alumnos' => []]));

        $run = $this->engine()->run('apply', 'cron', $empty);

        $this->assertSame(engine::EXIT_GUARD, $run['exitcode']);
        $this->assertSame(run_store::STATUS_ABORTED, run_store::get($run['runid'])->status);
        $this->assertSame(0, (int)\core_user::get_user_by_username('11111111h')->suspended);
    }

    public function test_guardas_impiden_aplicar_salvo_force(): void {
        for ($i = 0; $i < 3; $i++) {
            $this->getDataGenerator()->create_user(['username' => 'baja' . $i]);
        }

        $run = $this->engine(['maxusersuspensions' => 2])->run('apply', 'cron', $this->fixture);
        $this->assertSame(engine::EXIT_GUARD, $run['exitcode']);
        $this->assertSame(0, (int)\core_user::get_user_by_username('baja0')->suspended);
        $this->assertStringContainsString('3 usuarios', run_store::get($run['runid'])->summary);

        $forced = $this->engine(['maxusersuspensions' => 2])->run('apply', 'cli', $this->fixture, true);
        $this->assertSame(engine::EXIT_OK, $forced['exitcode']);
        $this->assertSame(1, (int)\core_user::get_user_by_username('baja0')->suspended);
    }

    public function test_descarga_desde_sigad_y_guarda_copia(): void {
        $datos = json_decode(file_get_contents($this->fixture), true);
        $responses = [
            [200, json_encode(['codigo' => 0, 'idSolicitud' => 5])],
            [200, json_encode(['codigo' => 0, 'estudiantes' => json_encode($datos)])],
        ];
        $config = config::from_array(['sigad_user' => 'u', 'sigad_password' => 'p', 'sigad_initialwait' => 0]);
        $client = new client($config, function () use (&$responses) {
            return array_shift($responses);
        }, fn() => null);

        $run = $this->engine(['sigad_user' => 'u', 'sigad_password' => 'p'], $client)->run('dry', 'cron');

        $this->assertSame(engine::EXIT_OK, $run['exitcode']);
        $copia = run_store::artifact(run_store::get($run['runid']), 'sigad');
        $this->assertSame($datos, json_decode(file_get_contents($copia), true));
    }

    public function test_error_queda_registrado_y_se_avisa(): void {
        $run = $this->engine()->run('dry', 'cron', '/no/existe.json');

        $this->assertSame(engine::EXIT_ERROR, $run['exitcode']);
        $record = run_store::get($run['runid']);
        $this->assertSame(run_store::STATUS_ERROR, $record->status);
        $this->assertStringContainsString('/no/existe.json', run_store::read_log($record));
        $this->assertStringContainsString('Con errores', $this->sink->get_messages()[0]->subject);
    }

    public function test_runner_usa_el_motor_integrado(): void {
        // Sin credenciales de SIGAD: la ejecución falla pero queda registrada por el motor PHP.
        $this->expectOutputRegex('/Faltan las credenciales de SIGAD/');
        $exitcode = runner::ejecutar('dry', 'manual');

        $this->assertSame(engine::EXIT_ERROR, $exitcode);
        $this->assertSame(run_store::STATUS_ERROR, run_store::latest()->status);
    }
}
