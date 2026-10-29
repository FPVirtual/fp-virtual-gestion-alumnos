<?php
// Tests del external function del snapshot.

namespace local_fpvirtual_gestion_alumnado\external;

defined('MOODLE_INTERNAL') || die();

/**
 * Verifica la forma de la respuesta del snapshot con datos de generator.
 *
 * @covers \local_fpvirtual_gestion_alumnado\external\get_snapshot
 */
class get_snapshot_test extends \advanced_testcase {

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

    public function test_execute_requires_capability(): void {
        $this->resetAfterTest(true);

        $user = $this->getDataGenerator()->create_user();
        $this->setUser($user);

        $this->expectException(\required_capability_exception::class);
        get_snapshot::execute();
    }
}
