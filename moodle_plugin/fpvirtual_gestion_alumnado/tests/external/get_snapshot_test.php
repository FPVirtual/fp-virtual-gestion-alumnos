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

namespace local_fpvirtual_gestion_alumnado\external;

/**
 * Verifica la forma de la respuesta del snapshot con datos de generator.
 *
 * @covers \local_fpvirtual_gestion_alumnado\external\get_snapshot
 *
 * @package    local_fpvirtual_gestion_alumnado
 * @copyright  2026 FP virtual Aragón
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class get_snapshot_test extends \advanced_testcase {
    public function test_execute_returns_users_and_enrolments(): void {
        $this->resetAfterTest(true);
        $this->setAdminUser();

        $user = $this->getDataGenerator()->create_user([
            'username' => '12345678a',
            'email' => '12345678a@fpvirtualaragon.es',
            'firstname' => 'Juan',
            'lastname' => 'Pérez',
        ]);
        $course = $this->getDataGenerator()->create_course(['shortname' => 'PROG']);
        $this->getDataGenerator()->enrol_user($user->id, $course->id);

        $result = get_snapshot::execute();

        $this->assertArrayHasKey('usuarios', $result);
        $this->assertArrayHasKey('matriculas', $result);

        $usernames = array_column($result['usuarios'], 'username');
        $this->assertContains('12345678a', $usernames);

        $enrolment = array_filter($result['matriculas'], function (array $m) use ($user, $course): bool {
            return $m['userid'] === (int)$user->id && $m['courseid'] === (int)$course->id;
        });
        $this->assertCount(1, $enrolment);
        $enrolment = reset($enrolment);
        $this->assertSame('PROG', $enrolment['shortname']);
        $this->assertSame(0, $enrolment['status']);
    }

    /**
     * Regresión: get_records_sql colapsaba filas por la primera columna, así
     * que solo quedaba una matrícula por usuario y se perdían campos de perfil.
     */
    public function test_execute_keeps_every_enrolment_and_custom_field(): void {
        $this->resetAfterTest(true);
        $this->setAdminUser();
        $gen = $this->getDataGenerator();

        foreach (['id_sigad', 'email_sigad', 'otrocampo'] as $shortname) {
            $gen->create_custom_profile_field([
                'datatype' => 'text', 'shortname' => $shortname, 'name' => $shortname,
            ]);
        }
        $user = $gen->create_user([
            'username' => '12345678a',
            'profile_field_id_sigad' => '16839',
            'profile_field_email_sigad' => 'personal@example.com',
            'profile_field_otrocampo' => 'ignorar',
        ]);
        $c1 = $gen->create_course(['shortname' => '50009348-DAW-1001']);
        $c2 = $gen->create_course(['shortname' => '50009348-DAW-1002']);
        $gen->enrol_user($user->id, $c1->id);
        $gen->enrol_user($user->id, $c2->id, null, 'manual', 0, 0, ENROL_USER_SUSPENDED);

        $result = get_snapshot::execute();

        $mias = array_values(array_filter($result['matriculas'], fn(array $m) => $m['userid'] === (int)$user->id));
        $this->assertCount(2, $mias);
        $estados = array_column($mias, 'status', 'shortname');
        $this->assertSame(0, $estados['50009348-DAW-1001']);
        $this->assertSame(1, $estados['50009348-DAW-1002']);

        $usuario = array_values(array_filter($result['usuarios'], fn(array $u) => $u['id'] === (int)$user->id));
        $this->assertCount(1, $usuario);
        $campos = array_column($usuario[0]['customfields'], 'value', 'shortname');
        $this->assertSame(['id_sigad' => '16839', 'email_sigad' => 'personal@example.com'], $campos);
    }

    public function test_execute_requires_capability(): void {
        $this->resetAfterTest(true);

        $user = $this->getDataGenerator()->create_user();
        $this->setUser($user);

        $this->expectException(\required_capability_exception::class);
        get_snapshot::execute();
    }
}
