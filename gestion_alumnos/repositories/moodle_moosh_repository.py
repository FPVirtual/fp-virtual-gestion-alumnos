"""Implementación de MoodleRepository usando moosh.

Ejecuta comandos moosh via subprocess. Si docker_container está
configurado, usa ``docker exec {container} moosh ...``.
"""

import json
import subprocess
from typing import Any

from gestion_alumnos.core.config import Settings
from gestion_alumnos.core.exceptions import MoodleError
from gestion_alumnos.core.logging import get_logger
from gestion_alumnos.repositories.protocols import MoodleRepository

logger = get_logger(__name__)


class MooshMoodleRepository(MoodleRepository):
    """Repositorio de Moodle usando moosh.

    TODAS las operaciones pasan por moosh. Cero SQL directo.
    """

    USUARIOS_PROTEGIDOS = frozenset({
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
        16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28,
        29, 30, 31, 32, 33, 3725, 3729, 3730, 7152, 7490,
        7491, 11720, 12270, 12272,
    })

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()

    def _run(self, comando: list[str], capture: bool = True) -> str:
        """Ejecuta un comando moosh.

        Args:
            comando: Lista de argumentos para moosh (sin el propio moosh).
            capture: Si True, captura stdout/stderr.

        Returns:
            stdout del comando.

        Raises:
            MoodleError: Si el comando falla.
        """
        if self._settings.docker_container:
            cmd = [
                "docker", "exec", self._settings.docker_container,
                self._settings.moosh_path,
            ] + comando
        else:
            cmd = [self._settings.moosh_path] + comando

        try:
            logger.debug(f"Ejecutando moosh: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=capture,
                text=True,
                timeout=self._settings.moosh_timeout,
            )
            if result.returncode != 0:
                raise MoodleError(
                    mensaje=f"Moosh error: {result.stderr}",
                    comando=" ".join(cmd),
                    codigo_salida=result.returncode,
                )
            return result.stdout
        except subprocess.TimeoutExpired:
            raise MoodleError(
                mensaje="Timeout ejecutando moosh",
                comando=" ".join(cmd),
            )
        except FileNotFoundError:
            raise MoodleError(
                mensaje=f"moosh no encontrado: {self._settings.moosh_path}",
                comando=" ".join(cmd),
            )

    def usuario_existe(self, username: str) -> bool:
        """Verifica si existe un usuario en Moodle."""
        try:
            salida = self._run(["user-get", username])
            return bool(salida.strip())
        except MoodleError:
            return False

    def crear_usuario(
        self,
        username: str,
        email: str,
        nombre: str,
        apellido: str,
        password: str | None = None,
        customfields: dict[str, str] | None = None,
    ) -> int:
        """Crea un usuario en Moodle.

        Args:
            customfields: Diccionario shortname -> valor con los campos
                personalizados de Moodle.

        Returns:
            ID del usuario creado (parseado de la salida de moosh).
        """
        args = [
            "user-create",
            "--username", username,
            "--email", email,
            "--firstname", nombre,
            "--lastname", apellido,
        ]
        if password:
            args.extend(["--password", password])
        salida = self._run(args)
        # moosh user-create imprime el ID del usuario creado
        try:
            user_id = int(salida.strip().splitlines()[-1].strip())
        except (ValueError, IndexError):
            logger.warning(f"No se pudo parsear ID del usuario creado: {salida}")
            user_id = 0

        # moosh user-create no siempre soporta custom fields; los aplicamos
        # con user-mod tras la creación.
        if customfields:
            mod_args = ["user-mod", "--username", username]
            for shortname, value in customfields.items():
                mod_args.extend([f"--profile_field_{shortname}", str(value)])
            try:
                self._run(mod_args)
            except MoodleError as e:
                logger.warning(f"No se pudieron aplicar custom fields a {username}: {e}")

        return user_id

    def actualizar_usuario(
        self,
        username: str,
        customfields: dict[str, str] | None = None,
        **campos,
    ) -> bool:
        """Actualiza campos de un usuario.

        Args:
            customfields: Diccionario shortname -> valor con campos
                personalizados de Moodle a actualizar.
        """
        args = ["user-mod", "--username", username]
        for campo, valor in campos.items():
            args.extend([f"--{campo}", str(valor)])
        if customfields:
            for shortname, value in customfields.items():
                args.extend([f"--profile_field_{shortname}", str(value)])
        self._run(args)
        return True

    def suspender_usuario(self, username: str) -> bool:
        """Suspende un usuario."""
        self._run(["user-mod", "--username", username, "--suspend", "1"])
        return True

    def reactivar_usuario(self, username: str) -> bool:
        """Reactiva un usuario suspendido."""
        self._run(["user-mod", "--username", username, "--suspend", "0"])
        return True

    def matricular_en_curso(self, username: str, curso_id: str) -> bool:
        """Matricula un usuario en un curso."""
        self._run(["course-enrol", "--user", username, curso_id])
        return True

    def desmatricular_de_curso(self, username: str, curso_id: str) -> bool:
        """Desmatricula un usuario de un curso."""
        self._run(["course-unenrol", "--user", username, curso_id])
        return True

    def matricular_en_cohorte(self, username: str, cohorte: str) -> bool:
        """Matricula un usuario en una cohorte."""
        self._run(["cohort-enrol", cohorte, username])
        return True

    def obtener_matriculas(self, username: str) -> list[dict]:
        """Obtiene las matrículas activas de un usuario."""
        try:
            salida = self._run(["course-list-enrolled", username])
            # Intentar parsear como JSON si moosh lo soporta
            lineas = salida.strip().splitlines()
            matriculas = []
            for linea in lineas:
                if not linea.strip():
                    continue
                try:
                    matriculas.append(json.loads(linea))
                except json.JSONDecodeError:
                    # Formato plano: id,shortname,fullname
                    partes = linea.split(",")
                    if len(partes) >= 2:
                        matriculas.append({
                            "id": partes[0].strip(),
                            "shortname": partes[1].strip(),
                        })
            return matriculas
        except MoodleError:
            return []

    def obtener_todos_usuarios(self) -> list[dict]:
        """Obtiene todos los usuarios de Moodle."""
        try:
            salida = self._run(["user-list"])
            lineas = salida.strip().splitlines()
            usuarios = []
            for linea in lineas:
                if not linea.strip():
                    continue
                try:
                    usuarios.append(json.loads(linea))
                except json.JSONDecodeError:
                    partes = linea.split(",")
                    if len(partes) >= 3:
                        usuarios.append({
                            "id": partes[0].strip(),
                            "username": partes[1].strip(),
                            "email": partes[2].strip(),
                        })
            return usuarios
        except MoodleError:
            return []

    def obtener_por_username(self, username: str) -> dict | None:
        """Obtiene un usuario por su username."""
        try:
            salida = self._run(["user-get", username])
            # Intentar parsear como JSON
            lineas = salida.strip().splitlines()
            for linea in lineas:
                if not linea.strip():
                    continue
                try:
                    return json.loads(linea)
                except json.JSONDecodeError:
                    continue
            return None
        except MoodleError:
            return None

    def obtener_todos_cursos(self) -> list[dict]:
        """Obtiene todos los cursos de Moodle."""
        try:
            salida = self._run(["course-list"])
            lineas = salida.strip().splitlines()
            cursos = []
            for linea in lineas:
                if not linea.strip():
                    continue
                try:
                    cursos.append(json.loads(linea))
                except json.JSONDecodeError:
                    # Formato plano: id,category,shortname,fullname,visible
                    partes = linea.split(",")
                    if len(partes) >= 3:
                        cursos.append({
                            "id": partes[0].strip().strip('"'),
                            "category": partes[1].strip().strip('"') if len(partes) > 1 else "",
                            "shortname": partes[2].strip().strip('"') if len(partes) > 2 else "",
                            "fullname": partes[3].strip().strip('"') if len(partes) > 3 else "",
                            "visible": partes[4].strip().strip('"') if len(partes) > 4 else "1",
                        })
            return cursos
        except MoodleError:
            return []

    def obtener_usuarios_matriculados_en_curso(self, curso_id: str) -> list[dict]:
        """Obtiene los usuarios matriculados en un curso concreto."""
        try:
            salida = self._run(["user-list", "--course", curso_id])
            lineas = salida.strip().splitlines()
            usuarios = []
            for linea in lineas:
                if not linea.strip():
                    continue
                try:
                    usuarios.append(json.loads(linea))
                except json.JSONDecodeError:
                    # Formato plano: username (id), email, ...
                    partes = linea.split(",")
                    if len(partes) >= 2:
                        usuarios.append({
                            "username": partes[0].strip(),
                            "id": partes[1].strip().replace("(", "").replace(")", ""),
                            "email": partes[2].strip() if len(partes) > 2 else "",
                        })
            return usuarios
        except MoodleError:
            return []

    # ------------------------------------------------------------------
    # MoodleSink interface
    # ------------------------------------------------------------------
    def create_user(
        self,
        username: str,
        email: str,
        nombre: str,
        apellido: str,
        password: str | None = None,
        customfields: dict[str, str] | None = None,
    ) -> int:
        """MoodleSink alias."""
        return self.crear_usuario(username, email, nombre, apellido, password, customfields)

    def update_user(
        self,
        username: str,
        customfields: dict[str, str] | None = None,
        **campos,
    ) -> bool:
        """Actualiza campos arbitrarios de un usuario."""
        return self.actualizar_usuario(username, customfields, **campos)

    def update_user_email(self, username: str, email: str) -> bool:
        """Actualiza el email de un usuario."""
        return self.actualizar_usuario(username, email=email)

    def update_user_username(self, old_username: str, new_username: str) -> bool:
        """Cambia el username de un usuario."""
        return self.actualizar_usuario(old_username, username=new_username)

    def enrol_user_to_course(self, username: str, course_id: str) -> bool:
        """MoodleSink alias."""
        return self.matricular_en_curso(username, course_id)

    def suspend_enrolment(self, username: str, course_id: str) -> bool:
        """Suspende una matrícula individual.

        ⚠️ Moosh no expone un comando nativo para suspender matrículas
        sin usar SQL directo.
        """
        raise NotImplementedError(
            "suspend_enrolment no está implementado para driver=moosh. "
            "Requiere plugin local_fparagon o SQL directo."
        )

    def reactivate_enrolment(self, username: str, course_id: str) -> bool:
        """Reactiva una matrícula suspendida.

        ⚠️ Moosh no expone un comando nativo para reactivar matrículas
        sin usar SQL directo.
        """
        raise NotImplementedError(
            "reactivate_enrolment no está implementado para driver=moosh. "
            "Requiere plugin local_fparagon o SQL directo."
        )

    def remove_user_from_cohort(self, username: str, cohort_name: str) -> bool:
        """Elimina un usuario de una cohorte.

        ⚠️ Moosh no tiene comando nativo `cohort-unenrol` en todas las versiones.
        """
        try:
            self._run(["cohort-unenrol", cohort_name, username])
            return True
        except MoodleError as e:
            raise NotImplementedError(
                "cohort-unenrol no disponible en esta versión de moosh. "
                "Requiere plugin local_fparagon."
            ) from e
