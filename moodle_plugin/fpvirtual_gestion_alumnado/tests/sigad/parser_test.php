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

/**
 * Tests del parser de SIGAD.
 *
 * @package    local_fpvirtual_gestion_alumnado
 * @copyright  2026 FP virtual Aragón
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 * @covers     \local_fpvirtual_gestion_alumnado\sigad\parser
 */
final class parser_test extends \basic_testcase {
    /**
     * Dataset del fichero de ejemplo.
     *
     * @return dataset
     */
    private function fixture(): dataset {
        return parser::parse_json(file_get_contents(__DIR__ . '/../fixtures/sigad_basico.json'));
    }

    public function test_normaliza_documento_y_username(): void {
        $ds = $this->fixture();

        $this->assertSame(['00000001r', 'x0000002t', '00000003a'], array_keys($ds->students));
        $luis = $ds->student('X0000002T');
        $this->assertSame('X0000002T', $luis['documento']);
        $this->assertSame('x0000002t', $luis['username']);
        $this->assertSame(1002, $luis['idsigad']);
        $this->assertSame('Pérez', $luis['apellidos']);
    }

    public function test_shortname_de_curso_usa_centro_ciclo_y_materia(): void {
        $ana = $this->fixture()->student('00000001r');

        $this->assertSame(['50009348-IFC303-5001', '50009348-IFC303-5002'], array_keys($ana['modules']));
        $this->assertSame('De la Fuente Gil', $ana['apellidos']);
        $this->assertSame('Programación', $ana['modules']['50009348-IFC303-5001']['modulo']);
    }

    public function test_cohortes_por_centro_y_ciclo(): void {
        $luis = $this->fixture()->student('x0000002t');

        $this->assertSame(['50009348-IFC303', '22002521-SSC302'], $luis['cohorts']);
        $this->assertCount(2, $luis['modules']);
    }

    public function test_alumno_sin_email_no_es_creable(): void {
        $ds = $this->fixture();

        $this->assertSame(['email'], $ds->student('00000003a')['missing']);
        $this->assertSame([], $ds->student('00000001r')['missing']);
        $this->assertNull($ds->student('00000003a')['apellido2']);
    }

    public function test_registro_sin_documento_se_descarta(): void {
        $ds = $this->fixture();

        $this->assertSame(3, $ds->count());
        $this->assertCount(1, $ds->discarded);
        $this->assertStringContainsString('1004', $ds->discarded[0]);
        $this->assertSame(4, $ds->count_modules());
    }

    public function test_acepta_la_respuesta_completa_del_servicio(): void {
        $inner = file_get_contents(__DIR__ . '/../fixtures/sigad_basico.json');
        $outer = json_encode(['codigo' => 0, 'mensaje' => 'OK', 'estudiantes' => $inner]);

        $this->assertSame(3, parser::parse_json($outer)->count());
    }

    public function test_alumno_duplicado_fusiona_matriculas(): void {
        $alumno = fn(int $materia) => [
            'idAlumno' => 1, 'documento' => '00000001R', 'nombre' => 'A', 'apellido1' => 'B', 'email' => 'a@b.c',
            'centros' => [['codigoCentro' => 'C', 'ciclos' => [['siglasCiclo' => 'X', 'modulos' => [['idMateria' => $materia]]]]]],
        ];
        $ds = parser::parse(['alumnos' => [$alumno(1), $alumno(2)]]);

        $this->assertSame(['C-X-1', 'C-X-2'], array_keys($ds->student('00000001r')['modules']));
    }

    public function test_json_invalido_lanza_excepcion(): void {
        $this->expectException(sigad_exception::class);
        parser::parse_json('{"sin": "alumnos"}');
    }
}
