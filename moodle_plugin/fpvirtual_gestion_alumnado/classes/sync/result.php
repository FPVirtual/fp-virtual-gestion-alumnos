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

/**
 * Resultado de aplicar un plan.
 *
 * @package    local_fpvirtual_gestion_alumnado
 * @copyright  2026 FP virtual Aragón
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class result {

    /** @var int[] Operaciones correctas por tipo. */
    public array $done = [];

    /** @var int[] Operaciones fallidas por tipo. */
    public array $failed = [];

    /** @var array[] Errores: type, username, message. */
    public array $errors = [];

    /** @var array[] Credenciales de los usuarios creados (para el CSV de Google, R20). */
    public array $created = [];

    /** @var int[] username => id de los usuarios creados. */
    public array $userids = [];

    /**
     * Registra una operación correcta.
     *
     * @param string $type
     */
    public function ok(string $type): void {
        $this->done[$type] = ($this->done[$type] ?? 0) + 1;
    }

    /**
     * Registra una operación fallida.
     *
     * @param string $type
     * @param string $username
     * @param string $message
     */
    public function error(string $type, string $username, string $message): void {
        $this->failed[$type] = ($this->failed[$type] ?? 0) + 1;
        $this->errors[] = ['type' => $type, 'username' => $username, 'message' => $message];
    }

    /**
     * Número total de errores.
     *
     * @return int
     */
    public function error_count(): int {
        return array_sum($this->failed);
    }

    /**
     * Resumen serializable (sin contraseñas).
     *
     * @return array
     */
    public function summary(): array {
        return ['done' => $this->done, 'failed' => $this->failed, 'errors' => $this->errors];
    }
}
