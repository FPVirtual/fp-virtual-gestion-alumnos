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
 * Notificaciones al alumnado que genera la aplicación del plan (R18).
 *
 * @package    local_fpvirtual_gestion_alumnado
 * @copyright  2026 FP virtual Aragón
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
interface notifier_interface {

    /**
     * Bienvenida a un usuario recién creado, con sus credenciales y matrículas.
     *
     * @param array $user operación create_user + institutionalemail
     * @param string $password
     * @param string[] $modules descripción de cada módulo matriculado
     */
    public function welcome(array $user, string $password, array $modules): void;

    /**
     * Aviso de cambio de nombre de usuario.
     *
     * @param array $op operación rename_user
     */
    public function username_changed(array $op): void;

    /**
     * Aviso de nuevas matrículas a un alumno existente.
     *
     * @param array $student alumno del dataset de SIGAD
     * @param string[] $modules
     */
    public function new_enrolments(array $student, array $modules): void;
}
