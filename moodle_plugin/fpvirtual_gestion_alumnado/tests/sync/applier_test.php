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
use local_fpvirtual_gestion_alumnado\sigad\dataset;
use local_fpvirtual_gestion_alumnado\sigad\parser;

/**
 * Tests del aplicador: escrituras reales en Moodle e idempotencia.
 *
 * @package    local_fpvirtual_gestion_alumnado
 * @copyright  2026 FP virtual Aragón
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 * @covers     \local_fpvirtual_gestion_alumnado\sync\applier
 */
final class applier_test extends \advanced_testcase {
    /** @var \stdClass[] Cursos por shortname. */
    private array $courses = [];

    /** @var config */
    private config $config;

    /** @var dataset */
    private dataset $sigad;

    protected function setUp(): void {
        parent::setUp();
        $this->resetAfterTest();
        $gen = $this->getDataGenerator();
        foreach (['id_sigad', 'email_sigad', 'tipo_documento', 'consentimiento_cdd'] as $field) {
            $gen->create_custom_profile_field(['datatype' => 'text', 'shortname' => $field, 'name' => $field]);
        }
        foreach (['alumnado', '50009348-IFC303', '22002521-SSC302'] as $cohort) {
            $gen->create_cohort(['name' => $cohort, 'idnumber' => $cohort]);
        }
        foreach (['50009348-IFC303-5001', '50009348-IFC303-5002', '50009348-IFC303-5099', '22002521-SSC302-6001'] as $sn) {
            $this->courses[$sn] = $gen->create_course(['shortname' => $sn]);
        }
        $this->config = config::from_array();
        $this->sigad = parser::parse_json(file_get_contents(__DIR__ . '/../fixtures/sigad_basico.json'));
    }

    /**
     * Analiza el estado actual.
     *
     * @return plan
     */
    private function analyze(): plan {
        return (new analyzer($this->sigad, moodle_state::load($this->config), $this->config, 1795000000))->analyze();
    }

    /**
     * Aplica un plan con un notificador de prueba.
     *
     * @param plan $plan
     * @param notifier_interface|null $notifier
     * @return result
     */
    private function apply(plan $plan, ?notifier_interface $notifier = null): result {
        return (new applier($this->config, $this->sigad, $notifier))->apply($plan);
    }

    public function test_aplicar_y_reanalizar_no_deja_acciones_pendientes(): void {
        $baja = $this->getDataGenerator()->create_user(['username' => '11111111h']);
        $this->getDataGenerator()->enrol_user($baja->id, $this->courses['50009348-IFC303-5099']->id);

        $result = $this->apply($this->analyze());

        $this->assertSame(0, $result->error_count(), json_encode($result->errors));
        $this->assertSame(0, $this->analyze()->total_actions(), json_encode($this->analyze()->counts()));
    }

    public function test_campo_opcional_vacio_no_se_escribe(): void {
        global $DB;
        $this->config = config::from_array(['field_consentimiento' => '']);
        $this->assertSame(0, $this->apply($this->analyze())->error_count());

        $ana = $DB->get_record('user', ['username' => '00000001r'], '*', MUST_EXIST);
        profile_load_custom_fields($ana);
        $this->assertSame('1001', $ana->profile['id_sigad']);
        $this->assertSame('', $ana->profile['consentimiento_cdd'] ?? '');
    }

    public function test_alta_completa(): void {
        global $DB;
        $notifier = new class implements notifier_interface {
            /** @var array */
            public array $calls = [];
            /**
             * Registra la bienvenida.
             *
             * @param array $user
             * @param string $password
             * @param array $modules
             */
            public function welcome(array $user, string $password, array $modules): void {
                $this->calls[] = ['welcome', $user['username'], $password, $modules];
            }
            /**
             * Registra el cambio de usuario.
             *
             * @param array $op
             */
            public function username_changed(array $op): void {
                $this->calls[] = ['renamed', $op['username']];
            }
            /**
             * Registra el aviso de matrículas.
             *
             * @param array $student
             * @param array $modules
             */
            public function new_enrolments(array $student, array $modules): void {
                $this->calls[] = ['enrolments', $student['username'], $modules];
            }
        };

        $result = $this->apply($this->analyze(), $notifier);

        $ana = $DB->get_record('user', ['username' => '00000001r'], '*', MUST_EXIST);
        $this->assertSame('De la Fuente Gil', $ana->lastname);
        $this->assertSame('00000001r@fpvirtualaragon.es', $ana->email);
        $this->assertSame('manual', $ana->auth);
        $this->assertSame('1', get_user_preferences('auth_forcepasswordchange', null, $ana->id));
        profile_load_custom_fields($ana);
        $this->assertSame('1001', $ana->profile['id_sigad']);
        $this->assertSame('ana.personal@example.com', $ana->profile['email_sigad']);
        $this->assertSame('0', $ana->profile['consentimiento_cdd']);

        $credentials = array_column($result->created, 'password', 'username');
        $this->assertTrue(validate_internal_user_password($ana, $credentials['00000001r']));

        $this->assertTrue(is_enrolled(\context_course::instance($this->courses['50009348-IFC303-5001']->id), $ana));
        $this->assertTrue(cohort_is_member($DB->get_field('cohort', 'id', ['name' => 'alumnado']), $ana->id));
        $this->assertTrue(cohort_is_member($DB->get_field('cohort', 'id', ['name' => '50009348-IFC303']), $ana->id));

        $welcome = array_values(array_filter($notifier->calls, fn($c) => $c[0] === 'welcome'));
        $this->assertCount(2, $welcome);
        $this->assertSame($credentials['00000001r'], $welcome[0][2]);
        $this->assertContains('CPIFP Test - Desarrollo de Aplicaciones Web - Programación', $welcome[0][3]);
        // Los nuevos no reciben además el aviso de matrículas.
        $this->assertEmpty(array_filter($notifier->calls, fn($c) => $c[0] === 'enrolments'));
    }

    public function test_baja_suspende_cuenta_y_matriculas(): void {
        global $DB;
        $baja = $this->getDataGenerator()->create_user(['username' => '11111111h']);
        $course = $this->courses['50009348-IFC303-5001'];
        $this->getDataGenerator()->enrol_user($baja->id, $course->id);

        $this->apply($this->analyze());

        $this->assertSame('1', (string)$DB->get_field('user', 'suspended', ['id' => $baja->id]));
        $this->assertFalse(is_enrolled(\context_course::instance($course->id), $baja, '', true));
        $this->assertTrue(is_enrolled(\context_course::instance($course->id), $baja), 'Matrícula suspendida, no borrada');
    }

    public function test_renombrado_conserva_usuario_y_matriculas(): void {
        global $DB;
        $old = $this->getDataGenerator()->create_user(['username' => 'y9999999z', 'profile_field_id_sigad' => '1002']);
        $this->getDataGenerator()->enrol_user($old->id, $this->courses['50009348-IFC303-5001']->id);

        $result = $this->apply($this->analyze());

        $this->assertSame(0, $result->error_count(), json_encode($result->errors));
        $this->assertSame('x0000002t', $DB->get_field('user', 'username', ['id' => $old->id]));
        $this->assertTrue(is_enrolled(\context_course::instance($this->courses['50009348-IFC303-5001']->id), $old->id, '', true));
        $this->assertTrue(is_enrolled(\context_course::instance($this->courses['22002521-SSC302-6001']->id), $old->id, '', true));
    }

    public function test_un_error_no_detiene_el_resto(): void {
        global $DB;
        // Se elimina el método manual de un curso: la matrícula en él falla.
        $DB->delete_records('enrol', ['courseid' => $this->courses['50009348-IFC303-5002']->id, 'enrol' => 'manual']);

        $result = $this->apply($this->analyze());

        $this->assertSame(1, $result->failed[plan::ENROL] ?? 0);
        $this->assertSame('00000001r', $result->errors[0]['username']);
        $this->assertSame(3, $result->done[plan::ENROL]);
        $this->assertSame(2, $result->done[plan::CREATE_USER]);
    }

    public function test_contrasena_generada(): void {
        $password = applier::generate_password();
        $this->assertSame(10, strlen($password));
        $errmsg = '';
        $this->assertTrue(check_password_policy($password, $errmsg), $errmsg);
        $this->assertNotSame($password, applier::generate_password());
    }
}
