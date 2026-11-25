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

/**
 * Tests del notificador.
 *
 * @package    local_fpvirtual_gestion_alumnado
 * @copyright  2026 FP virtual Aragón
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 * @covers     \local_fpvirtual_gestion_alumnado\sync\notifier
 */
final class notifier_test extends \advanced_testcase {
    /** @var \phpunit_message_sink */
    private $sink;

    protected function setUp(): void {
        parent::setUp();
        $this->resetAfterTest();
        unset_config('noemailever');
        $this->sink = $this->redirectEmails();
    }

    /**
     * Notificador sin pausas.
     *
     * @param array $config
     * @return notifier
     */
    private function notifier(array $config = []): notifier {
        return new notifier(config::from_array($config + ['emailpause' => 0]));
    }

    /**
     * Datos de una alta.
     *
     * @return array
     */
    private function user(): array {
        return [
            'username' => '00000001r', 'firstname' => 'Ana', 'lastname' => 'Gil <b>',
            'email' => 'ana.personal@example.com', 'institutionalemail' => '00000001r@fpvirtualaragon.es',
        ];
    }

    public function test_bienvenida_al_email_personal_con_credenciales(): void {
        $n = $this->notifier();
        $n->welcome($this->user(), 'Clave123', ['Centro - Ciclo - Programación']);

        $messages = $this->sink->get_messages();
        $this->assertCount(1, $messages);
        $this->assertSame('ana.personal@example.com', $messages[0]->to);
        $body = quoted_printable_decode($messages[0]->body);
        $this->assertStringContainsString('Clave123', $body);
        $this->assertStringContainsString('00000001r@fpvirtualaragon.es', $body);
        $this->assertStringContainsString('Programación', $body);
        $this->assertStringContainsString('Gil &lt;b&gt;', $body, 'Los datos se escapan');
        $this->assertSame(1, $n->stats['sent']);
    }

    public function test_redireccion_fuera_de_produccion(): void {
        $this->notifier(['notifyredirect' => 'pruebas@example.com'])->welcome($this->user(), 'x', []);

        $messages = $this->sink->get_messages();
        $this->assertSame('pruebas@example.com', $messages[0]->to);
        $this->assertStringContainsString('[ana.personal@example.com]', $messages[0]->subject);
    }

    public function test_limite_diario(): void {
        $n = $this->notifier(['dailyemaillimit' => 2]);
        for ($i = 0; $i < 3; $i++) {
            $n->new_enrolments(['nombre' => 'Ana', 'apellidos' => 'Gil', 'email' => 'a@example.com'], ['M']);
        }

        $this->assertCount(2, $this->sink->get_messages());
        $this->assertSame(['sent' => 2, 'failed' => 0, 'skipped' => 1], $n->stats);
        // El cupo se comparte entre ejecuciones del mismo día.
        $otra = $this->notifier(['dailyemaillimit' => 2]);
        $otra->new_enrolments(['nombre' => 'Ana', 'apellidos' => 'Gil', 'email' => 'a@example.com'], ['M']);
        $this->assertSame(1, $otra->stats['skipped']);
    }

    public function test_desactivado_y_email_invalido(): void {
        $this->notifier(['notifyenabled' => 0])->welcome($this->user(), 'x', []);
        $this->assertCount(0, $this->sink->get_messages());

        $n = $this->notifier();
        $n->welcome(['email' => 'no-es-un-email'] + $this->user(), 'x', []);
        $this->assertSame(1, $n->stats['failed']);
        $this->assertCount(0, $this->sink->get_messages());
    }

    public function test_cambio_de_usuario_muestra_el_email_actual(): void {
        $user = $this->getDataGenerator()->create_user(['username' => 'x0000002t', 'email' => 'y9999999z@fpvirtualaragon.es']);

        $this->notifier()->username_changed([
            'userid' => $user->id, 'username' => 'x0000002t', 'oldusername' => 'y9999999z',
            'email' => 'luis@example.com', 'nombre' => 'Luis', 'apellidos' => 'Pérez',
        ]);

        $body = quoted_printable_decode($this->sink->get_messages()[0]->body);
        $this->assertStringContainsString('y9999999z@fpvirtualaragon.es', $body);
        $this->assertStringContainsString('x0000002t', $body);
    }

    public function test_informe_a_responsables_con_adjunto(): void {
        global $CFG;
        $file = make_temp_directory('fpga') . '/informe.md';
        file_put_contents($file, '# Informe');

        $sent = $this->notifier(['reportto' => 'a@example.com, b@example.com', 'dailyemaillimit' => 1])
            ->send_report(['ok' => true, 'estado' => 'Correcta', 'modo' => 'dry', 'runid' => 3,
                'runurl' => $CFG->wwwroot, 'lineas' => [['etiqueta' => 'Altas', 'valor' => 2]]], $file, 'informe.md');

        $this->assertSame(2, $sent, 'El informe no consume cupo diario');
        $messages = $this->sink->get_messages();
        $this->assertSame(['a@example.com', 'b@example.com'], array_column($messages, 'to'));
        $this->assertStringContainsString('informe.md', $messages[0]->body);
    }
}
