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
 * Convierte el JSON de SIGAD en un {@see dataset} normalizado.
 *
 * Reglas aplicadas aquí:
 *  - R1: username = documento en minúsculas.
 *  - R3: shortname de curso = {codigoCentro}-{siglasCiclo}-{idMateria}.
 *  - R5: un alumno es creable si tiene documento, nombre, apellido1 y email.
 *  - R6: cohorte de ciclo = {codigoCentro}-{siglasCiclo}.
 *
 * @package    local_fpvirtual_gestion_alumnado
 * @copyright  2026 FP virtual Aragón
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class parser {
    /**
     * Interpreta el contenido de un fichero (JSON) de SIGAD.
     *
     * Acepta tanto el contenido interno ({fecha, hora, alumnos}) como la
     * respuesta completa del servicio ({codigo, estudiantes: "<json>"}).
     *
     * @param string $json
     * @return dataset
     * @throws sigad_exception
     */
    public static function parse_json(string $json): dataset {
        $data = json_decode($json, true);
        if (!is_array($data)) {
            throw new sigad_exception('El fichero de SIGAD no es un JSON válido.');
        }
        if (isset($data['estudiantes'])) {
            $data = is_string($data['estudiantes']) ? json_decode($data['estudiantes'], true) : $data['estudiantes'];
            if (!is_array($data)) {
                throw new sigad_exception('El campo "estudiantes" de SIGAD no es un JSON válido.');
            }
        }
        return self::parse($data);
    }

    /**
     * Normaliza los datos decodificados de SIGAD.
     *
     * @param array $data {fecha, hora, alumnos: [...]}
     * @return dataset
     * @throws sigad_exception
     */
    public static function parse(array $data): dataset {
        if (!isset($data['alumnos']) || !is_array($data['alumnos'])) {
            throw new sigad_exception('Los datos de SIGAD no contienen la lista "alumnos".');
        }

        $dataset = new dataset();
        $dataset->fecha = (string)($data['fecha'] ?? '');
        $dataset->hora = (string)($data['hora'] ?? '');

        foreach ($data['alumnos'] as $index => $alumno) {
            if (!is_array($alumno)) {
                $dataset->discarded[] = "Registro {$index}: formato inválido";
                continue;
            }
            $documento = self::text($alumno['documento'] ?? null);
            if ($documento === null) {
                $dataset->discarded[] = "Registro {$index} (idAlumno " . ($alumno['idAlumno'] ?? '?') . '): sin documento';
                continue;
            }
            $documento = \core_text::strtoupper(preg_replace('/\s+/', '', $documento));
            $username = \core_text::strtolower($documento);

            $student = $dataset->students[$username] ?? self::student($alumno, $documento, $username);
            foreach (($alumno['centros'] ?? []) as $centro) {
                self::add_centro($student, (array)$centro);
            }
            $dataset->students[$username] = $student;
        }

        return $dataset;
    }

    /**
     * Construye el registro de un alumno (sin matrículas).
     *
     * @param array $alumno
     * @param string $documento
     * @param string $username
     * @return array
     */
    protected static function student(array $alumno, string $documento, string $username): array {
        $nombre = self::text($alumno['nombre'] ?? null);
        $apellido1 = self::text($alumno['apellido1'] ?? null);
        $apellido2 = self::text($alumno['apellido2'] ?? null);
        $email = self::text($alumno['email'] ?? null);

        $missing = [];
        foreach (['nombre' => $nombre, 'apellido1' => $apellido1, 'email' => $email] as $field => $value) {
            if ($value === null) {
                $missing[] = $field;
            }
        }

        return [
            'idsigad' => self::int($alumno['idAlumno'] ?? null),
            'idtipodocumento' => self::int($alumno['idTipoDocumento'] ?? null),
            'documento' => $documento,
            'username' => $username,
            'nombre' => $nombre,
            'apellido1' => $apellido1,
            'apellido2' => $apellido2,
            'apellidos' => trim(($apellido1 ?? '') . ' ' . ($apellido2 ?? '')),
            'email' => $email,
            'missing' => $missing,
            'modules' => [],
            'cohorts' => [],
        ];
    }

    /**
     * Añade los ciclos y módulos de un centro al alumno.
     *
     * @param array $student
     * @param array $centro
     */
    protected static function add_centro(array &$student, array $centro): void {
        $codigocentro = self::text($centro['codigoCentro'] ?? null);
        if ($codigocentro === null) {
            return;
        }
        foreach (($centro['ciclos'] ?? []) as $ciclo) {
            $ciclo = (array)$ciclo;
            $siglasciclo = self::text($ciclo['siglasCiclo'] ?? null);
            if ($siglasciclo === null) {
                continue;
            }
            $cohort = $codigocentro . '-' . $siglasciclo;
            if (!in_array($cohort, $student['cohorts'], true)) {
                $student['cohorts'][] = $cohort;
            }
            foreach (($ciclo['modulos'] ?? []) ?: [] as $modulo) {
                $modulo = (array)$modulo;
                $idmateria = self::int($modulo['idMateria'] ?? null);
                if (!$idmateria) {
                    continue;
                }
                $shortname = $cohort . '-' . $idmateria;
                $student['modules'][$shortname] = [
                    'shortname' => $shortname,
                    'codigocentro' => $codigocentro,
                    'centro' => self::text($centro['centro'] ?? null) ?? $codigocentro,
                    'siglasciclo' => $siglasciclo,
                    'ciclo' => self::text($ciclo['ciclo'] ?? null) ?? $siglasciclo,
                    'idmateria' => $idmateria,
                    'modulo' => self::text($modulo['modulo'] ?? null) ?? (string)$idmateria,
                ];
            }
        }
    }

    /**
     * Texto recortado o null si está vacío.
     *
     * @param mixed $value
     * @return string|null
     */
    protected static function text($value): ?string {
        if ($value === null || is_array($value)) {
            return null;
        }
        $value = trim((string)$value);
        return $value === '' ? null : $value;
    }

    /**
     * Entero positivo o null.
     *
     * @param mixed $value
     * @return int|null
     */
    protected static function int($value): ?int {
        return is_numeric($value) && (int)$value > 0 ? (int)$value : null;
    }
}
