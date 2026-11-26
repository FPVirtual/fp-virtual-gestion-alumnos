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

namespace local_fpvirtual_gestion_alumnado;

/**
 * Tests de la configuración: campos de perfil.
 *
 * @package    local_fpvirtual_gestion_alumnado
 * @copyright  2026 FP virtual Aragón
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 * @covers     \local_fpvirtual_gestion_alumnado\config
 */
final class config_test extends \advanced_testcase {
    /**
     * Crea campos de perfil de texto.
     *
     * @param string[] $shortnames
     */
    private function fields(array $shortnames): void {
        foreach ($shortnames as $shortname) {
            $this->getDataGenerator()->create_custom_profile_field(
                ['datatype' => 'text', 'shortname' => $shortname, 'name' => $shortname]
            );
        }
    }

    public function test_valores_por_defecto_son_los_de_produccion(): void {
        $this->assertSame([
            'idsigad' => 'id_sigad',
            'emailsigad' => 'email_sigad',
            'tipodocumento' => 'tipo_documento',
            'consentimiento' => 'consentimiento_cdd',
        ], config::from_array()->profile_fields());
    }

    public function test_campos_existentes_sin_problemas(): void {
        $this->resetAfterTest();
        $this->fields(['id_sigad', 'email_sigad', 'tipo_documento', 'consentimiento_cdd']);

        $this->assertSame([], config::from_array()->profile_field_problems());
    }

    public function test_campos_inexistentes_o_con_otras_mayusculas(): void {
        $this->resetAfterTest();
        $this->fields(['id_sigad', 'email_sigad', 'tipo_documento', 'consentimiento_cdd']);

        $problems = config::from_array(['field_idsigad' => 'IdSIGAD', 'field_emailsigad' => 'EMAIL_SIGAD'])
            ->profile_field_problems();

        $this->assertCount(2, $problems);
        $this->assertStringContainsString("'IdSIGAD'", $problems[0]);
        $this->assertStringContainsString("'EMAIL_SIGAD'", $problems[1]);
    }

    public function test_opcionales_vacios_y_obligatorios_vacios(): void {
        $this->resetAfterTest();
        $this->fields(['id_sigad', 'email_sigad']);

        $config = config::from_array(['field_tipodocumento' => '', 'field_consentimiento' => '']);
        $this->assertSame([], $config->profile_field_problems());
        $this->assertSame(['idsigad', 'emailsigad'], array_keys($config->profile_fields()));

        $problems = config::from_array(['field_tipodocumento' => '', 'field_consentimiento' => '', 'field_idsigad' => ''])
            ->profile_field_problems();
        $this->assertSame(['El ajuste field_idsigad es obligatorio y está vacío.'], $problems);
    }
}
