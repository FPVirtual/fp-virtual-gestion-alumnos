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
 * Datos de SIGAD normalizados y listos para el análisis.
 *
 * Cada alumno es un array con:
 *  - idsigad (?int), idtipodocumento (?int), documento (string, mayúsculas),
 *    username (string, minúsculas), nombre, apellido1, apellido2 (?string),
 *    apellidos (string), email (?string)
 *  - missing (string[]): campos obligatorios ausentes (vacío = creable)
 *  - modules: [shortname => [shortname, codigocentro, centro, siglasciclo, ciclo, idmateria, modulo]]
 *  - cohorts: string[] nombres de cohorte {codigoCentro}-{siglasCiclo}
 *
 * @package    local_fpvirtual_gestion_alumnado
 * @copyright  2026 FP virtual Aragón
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class dataset {
    /** @var string Fecha de generación declarada por SIGAD. */
    public string $fecha = '';

    /** @var string Hora de generación declarada por SIGAD. */
    public string $hora = '';

    /** @var array[] Alumnos indexados por username. */
    public array $students = [];

    /** @var string[] Registros descartados (sin documento), con el motivo. */
    public array $discarded = [];

    /**
     * Número de alumnos válidos.
     *
     * @return int
     */
    public function count(): int {
        return count($this->students);
    }

    /**
     * Número total de matrículas en módulos.
     *
     * @return int
     */
    public function count_modules(): int {
        return array_sum(array_map(fn(array $s) => count($s['modules']), $this->students));
    }

    /**
     * Alumno por username (o null).
     *
     * @param string $username
     * @return array|null
     */
    public function student(string $username): ?array {
        return $this->students[\core_text::strtolower($username)] ?? null;
    }
}
