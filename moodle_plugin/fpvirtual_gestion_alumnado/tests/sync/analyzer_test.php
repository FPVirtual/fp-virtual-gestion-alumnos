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
use local_fpvirtual_gestion_alumnado\sigad\parser;

/**
 * Tests del analizador: una o varias pruebas por regla del roadmap.
 *
 * @package    local_fpvirtual_gestion_alumnado
 * @copyright  2026 FP virtual Aragón
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 * @covers     \local_fpvirtual_gestion_alumnado\sync\analyzer
 * @covers     \local_fpvirtual_gestion_alumnado\sync\moodle_state
 * @covers     \local_fpvirtual_gestion_alumnado\sync\plan
 */
final class analyzer_test extends \advanced_testcase {
    /** @var \stdClass[] Cursos por shortname. */
    private array $courses = [];

    /** @var int Noviembre (fuera del mes de limpieza). */
    private const NOVIEMBRE = 1795000000;

    protected function setUp(): void {
        parent::setUp();
        $this->resetAfterTest();
        $gen = $this->getDataGenerator();
        foreach (['id_sigad', 'email_sigad'] as $field) {
            $gen->create_custom_profile_field(['datatype' => 'text', 'shortname' => $field, 'name' => $field]);
        }
        foreach (['alumnado', '50009348-IFC303', '22002521-SSC302'] as $cohort) {
            $gen->create_cohort(['name' => $cohort, 'idnumber' => $cohort]);
        }
        foreach (
            ['50009348-IFC303-5001', '50009348-IFC303-5002', '50009348-IFC303-5099',
                '50009348-IFC303-01t', 'ayuda'] as $shortname
        ) {
            $this->courses[$shortname] = $gen->create_course(['shortname' => $shortname]);
        }
        // 22002521-SSC302-6001 no existe en Moodle a propósito.
    }

    /**
     * Ejecuta el análisis del fichero de ejemplo.
     *
     * @param array $config
     * @param int $now
     * @return plan
     */
    private function analyze(array $config = [], int $now = self::NOVIEMBRE): plan {
        $config = config::from_array($config);
        $sigad = parser::parse_json(file_get_contents(__DIR__ . '/../fixtures/sigad_basico.json'));
        return (new analyzer($sigad, moodle_state::load($config), $config, $now))->analyze();
    }

    /**
     * Crea un alumno en Moodle.
     *
     * @param string $username
     * @param array $extra
     * @return \stdClass
     */
    private function user(string $username, array $extra = []): \stdClass {
        return $this->getDataGenerator()->create_user(['username' => $username] + $extra);
    }

    /**
     * Matricula en un curso de prueba.
     *
     * @param \stdClass $user
     * @param string $shortname
     * @param int $status
     */
    private function enrol(\stdClass $user, string $shortname, int $status = ENROL_USER_ACTIVE): void {
        $this->getDataGenerator()->enrol_user($user->id, $this->courses[$shortname]->id, 'student', 'manual', 0, 0, $status);
    }

    /**
     * Valores de una columna de las operaciones de un tipo.
     *
     * @param plan $plan
     * @param string $type
     * @param string $column
     * @return array
     */
    private function col(plan $plan, string $type, string $column): array {
        $values = array_column($plan->get($type), $column);
        sort($values);
        return $values;
    }

    public function test_altas_con_cohortes_y_matriculas(): void {
        $plan = $this->analyze();

        $this->assertSame(['00000001r', 'x0000002t'], $this->col($plan, plan::CREATE_USER, 'username'));
        $ana = $plan->get(plan::CREATE_USER)[0];
        $this->assertSame('De la Fuente Gil', $ana['lastname']);
        $this->assertSame(1001, $ana['idsigad']);
        $this->assertNull($ana['userid']);

        // Ana: 5001 y 5002; Luis: 5001 (6001 no existe en Moodle).
        $this->assertSame(
            ['50009348-IFC303-5001', '50009348-IFC303-5001', '50009348-IFC303-5002'],
            $this->col($plan, plan::ENROL, 'shortname')
        );
        $this->assertSame(['22002521-SSC302-6001'], $this->col($plan, plan::MISSING_COURSE, 'nombre'));
        // Ana: alumnado + 1 ciclo; Luis: alumnado + 2 ciclos.
        $this->assertSame(5, $plan->count(plan::ADD_COHORT));

        $this->assertSame(['00000003a'], $this->col($plan, plan::NOT_CREATABLE, 'username'));
        $this->assertSame(1, $plan->count(plan::DISCARDED));
        $this->assertSame(0, $plan->count(plan::SUSPEND_USER));
    }

    public function test_matriculas_de_alumno_existente(): void {
        $ana = $this->user('00000001r', ['firstname' => 'Ana', 'lastname' => 'De la Fuente Gil',
            'profile_field_id_sigad' => '1001', 'profile_field_email_sigad' => 'ana.personal@example.com']);
        $this->enrol($ana, '50009348-IFC303-5001');                       // Correcta.
        $this->enrol($ana, '50009348-IFC303-5002', ENROL_USER_SUSPENDED); // Se reactiva (R8).
        $this->enrol($ana, '50009348-IFC303-5099');                       // No está en SIGAD (R9).
        $this->enrol($ana, '50009348-IFC303-01t');                        // Tutoría: no se toca (R4).
        $this->enrol($ana, 'ayuda');                                      // Excluido (R4).

        $plan = $this->analyze();

        $this->assertNotContains('00000001r', $this->col($plan, plan::CREATE_USER, 'username'));
        $this->assertSame(['50009348-IFC303-5002'], $this->col($plan, plan::REACTIVATE_ENROL, 'shortname'));
        $this->assertSame(['50009348-IFC303-5099'], $this->col($plan, plan::SUSPEND_ENROL, 'shortname'));
        $this->assertNotContains((int)$ana->id, array_column($plan->get(plan::ENROL), 'userid'));
        $this->assertSame(0, $plan->count(plan::UPDATE_PROFILE));
        $this->assertSame(0, $plan->count(plan::UPDATE_NAME));
    }

    public function test_cambio_de_documento_por_idsigad(): void {
        $old = $this->user('y9999999z', ['firstname' => 'Luis', 'lastname' => 'Pérez',
            'profile_field_id_sigad' => '1002', 'profile_field_email_sigad' => 'luis@example.com']);
        $this->enrol($old, '50009348-IFC303-5001');

        $plan = $this->analyze();

        $rename = $plan->get(plan::RENAME_USER);
        $this->assertCount(1, $rename);
        $this->assertSame(
            ['userid' => (int)$old->id, 'username' => 'x0000002t', 'oldusername' => 'y9999999z'],
            array_intersect_key($rename[0], array_flip(['userid', 'username', 'oldusername']))
        );
        $this->assertNotContains('x0000002t', $this->col($plan, plan::CREATE_USER, 'username'));
        // La matrícula existente se conserva: se cruza por id de usuario, no por username.
        $this->assertSame(0, $plan->count(plan::SUSPEND_ENROL));
        $this->assertSame(0, $plan->count(plan::SUSPEND_USER));
    }

    public function test_cambio_de_documento_por_email_si_no_hay_idsigad(): void {
        $old = $this->user('y9999999z', ['profile_field_email_sigad' => 'LUIS@example.com']);

        $plan = $this->analyze();

        $this->assertSame([(int)$old->id], $this->col($plan, plan::RENAME_USER, 'userid'));
        // Se rellena el IdSIGAD para que en adelante se empareje por él.
        $profile = $plan->get(plan::UPDATE_PROFILE)[0];
        $this->assertSame(['idsigad' => '1002'], $profile['fields']);
    }

    public function test_idsigad_duplicado_es_conflicto(): void {
        $this->user('a1', ['profile_field_id_sigad' => '1002']);
        $this->user('a2', ['profile_field_id_sigad' => '1002']);

        $plan = $this->analyze();

        $this->assertSame(['x0000002t'], $this->col($plan, plan::RENAME_CONFLICT, 'username'));
        $this->assertSame(0, $plan->count(plan::RENAME_USER));
    }

    public function test_bajas_y_ambito(): void {
        global $CFG;
        $baja = $this->user('11111111h');
        $this->enrol($baja, '50009348-IFC303-5001');
        $this->enrol($baja, 'ayuda');
        cohort_add_member($this->cohort('alumnado'), $baja->id);
        $yasuspendido = $this->user('22222222j', ['suspended' => 1]);
        $profesor = $this->user('prof_daw');
        $protegido = $this->user('servicio');
        $ws = $this->user('moodle-api', ['auth' => 'webservice']);

        $plan = $this->analyze(['protectedusers' => (string)$protegido->id]);

        $this->assertSame([(int)$baja->id], $this->col($plan, plan::SUSPEND_USER, 'userid'));
        $this->assertSame(['50009348-IFC303-5001'], $this->col($plan, plan::SUSPEND_ENROL, 'shortname'));
        $this->assertSame(['alumnado'], $this->col($plan, plan::REMOVE_COHORT, 'cohort'));
        $suspended = $this->col($plan, plan::SUSPEND_USER, 'userid');
        foreach ([$yasuspendido, $profesor, $protegido, $ws] as $u) {
            $this->assertNotContains((int)$u->id, $suspended);
        }
        $this->assertNotContains((int)explode(',', $CFG->siteadmins)[0], $suspended);
    }

    public function test_username_de_usuario_fuera_de_ambito(): void {
        $this->user('00000001r', ['auth' => 'webservice']);

        $plan = $this->analyze();

        $this->assertSame(['00000001r'], $this->col($plan, plan::OUT_OF_SCOPE, 'username'));
        $this->assertNotContains('00000001r', $this->col($plan, plan::CREATE_USER, 'username'));
    }

    public function test_reactivacion_perfil_y_nombre(): void {
        $luis = $this->user('x0000002t', ['suspended' => 1, 'firstname' => 'Luis', 'lastname' => 'Perez',
            'profile_field_email_sigad' => 'antiguo@example.com']);

        $plan = $this->analyze();

        $this->assertSame([(int)$luis->id], $this->col($plan, plan::REACTIVATE_USER, 'userid'));
        $profile = $plan->get(plan::UPDATE_PROFILE)[0];
        $this->assertSame(['idsigad' => '1002', 'emailsigad' => 'luis@example.com'], $profile['fields']);
        $this->assertSame('antiguo@example.com', $profile['old']['emailsigad']);
        $this->assertSame(['Pérez'], $this->col($plan, plan::UPDATE_NAME, 'lastname'));

        $this->assertSame(0, $this->analyze(['syncnames' => 0])->count(plan::UPDATE_NAME));
    }

    /**
     * Regresión (pre, 26/11/2026): con shortnames que no existían se leían vacíos
     * y se proponía actualizar el perfil de todos los alumnos emparejados.
     */
    public function test_perfil_al_dia_no_genera_actualizacion(): void {
        $this->user('00000001r', ['profile_field_id_sigad' => '1001', 'profile_field_email_sigad' => 'ana.personal@example.com']);
        $this->user('x0000002t', ['profile_field_id_sigad' => '1002', 'profile_field_email_sigad' => 'luis@example.com']);

        $this->assertSame(0, $this->analyze()->count(plan::UPDATE_PROFILE));
    }

    public function test_shortnames_configurables(): void {
        $gen = $this->getDataGenerator();
        $gen->create_custom_profile_field(['datatype' => 'text', 'shortname' => 'otro_id', 'name' => 'otro_id']);
        $old = $this->user('y9999999z', ['profile_field_otro_id' => '1002']);

        $plan = $this->analyze(['field_idsigad' => 'otro_id']);

        $this->assertSame([(int)$old->id], $this->col($plan, plan::RENAME_USER, 'userid'));
    }

    public function test_cohorte_de_ciclo_que_ya_no_corresponde(): void {
        $ana = $this->user('00000001r', ['profile_field_id_sigad' => '1001']);
        cohort_add_member($this->cohort('22002521-SSC302'), $ana->id);

        $plan = $this->analyze();

        $remove = array_filter($plan->get(plan::REMOVE_COHORT), fn($op) => $op['userid'] === (int)$ana->id);
        $this->assertSame(['22002521-SSC302'], array_column(array_values($remove), 'cohort'));
    }

    public function test_limpieza_en_agosto(): void {
        $ana = $this->user('00000001r', ['profile_field_id_sigad' => '1001']);
        $this->enrol($ana, '50009348-IFC303-5099', ENROL_USER_SUSPENDED);
        $this->enrol($ana, '50009348-IFC303-5002', ENROL_USER_SUSPENDED); // Se reactiva: no se limpia.
        $agosto = mktime(4, 0, 0, 8, 10, 2027);

        $this->assertSame(['50009348-IFC303-5099'], $this->col($this->analyze([], $agosto), plan::UNENROL, 'shortname'));
        $this->assertSame(0, $this->analyze()->count(plan::UNENROL));
        $this->assertSame(0, $this->analyze(['cleanupenabled' => 0], $agosto)->count(plan::UNENROL));
    }

    public function test_guardas_de_seguridad(): void {
        for ($i = 0; $i < 3; $i++) {
            $this->user('baja' . $i);
        }
        $plan = $this->analyze();

        $this->assertSame([], $plan->check_limits(config::from_array()));
        $violations = $plan->check_limits(config::from_array(['maxusersuspensions' => 2]));
        $this->assertCount(1, $violations);
        $this->assertStringContainsString('3 usuarios', $violations[0]);
    }

    public function test_plan_serializable(): void {
        $plan = $this->analyze();

        $copy = plan::from_array(json_decode(json_encode($plan->to_array()), true));

        $this->assertSame($plan->counts(), $copy->counts());
        $this->assertSame($plan->stats, $copy->stats);
    }

    /**
     * Id de cohorte por nombre.
     *
     * @param string $name
     * @return int
     */
    private function cohort(string $name): int {
        global $DB;
        return (int)$DB->get_field('cohort', 'id', ['name' => $name]);
    }
}
