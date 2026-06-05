"""Motor de análisis de sincronización SIGAD ↔ Moodle.

Servicio puro (sin dependencias de red) que recibe un Registro de SIGAD
y un MoodleSnapshot, los carga en DuckDB in-memory y calcula todos los
deltas mediante queries SQL.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from gestion_alumnos.core.logging import get_logger
from gestion_alumnos.models import (
    Alumno,
    EmailChangeDelta,
    EnrolmentDelta,
    MoodleEnrolmentRecord,
    MoodleSnapshot,
    MoodleUserRecord,
    NameChangeDelta,
    NewUserDelta,
    Registro,
    RemovedUserDelta,
    SyncReport,
    UsernameChangeDelta,
)

logger = get_logger(__name__)


def cargar_usuarios_protegidos(csv_path: Path | str | None = None) -> set[int]:
    """Carga los IDs de usuarios protegidos desde un CSV.

    Args:
        csv_path: Ruta al CSV. Si es None, usa el CSV por defecto.

    Returns:
        Set de IDs de usuarios protegidos.
    """
    if csv_path is None:
        csv_path = Path(__file__).resolve().parent.parent / "data" / "usuarios_protegidos.csv"
    path = Path(csv_path)
    if not path.exists():
        logger.warning(f"CSV de usuarios protegidos no encontrado: {path}")
        return set()
    try:
        df = pd.read_csv(path)
        ids = set(df["user_id"].dropna().astype(int).tolist())
        logger.debug(f"Usuarios protegidos cargados: {len(ids)} IDs")
        return ids
    except Exception as e:
        logger.error(f"Error cargando usuarios protegidos: {e}")
        return set()


class SyncAnalyzer:
    """Analiza diferencias entre SIGAD y Moodle usando DuckDB.

    Usage:
        analyzer = SyncAnalyzer(registro_sigad, moodle_snapshot)
        report = analyzer.analyze()
    """

    def __init__(
        self,
        registro: Registro,
        snapshot: MoodleSnapshot,
        usuarios_protegidos: set[int] | None = None,
    ) -> None:
        self._registro = registro
        self._snapshot = snapshot
        self._usuarios_protegidos = usuarios_protegidos or cargar_usuarios_protegidos()
        self._con = duckdb.connect(":memory:")
        self._cargar_sigad()
        self._cargar_moodle()

    # ------------------------------------------------------------------
    # Carga en DuckDB
    # ------------------------------------------------------------------
    def _cargar_sigad(self) -> None:
        """Normaliza el JSON jerárquico de SIGAD en tablas planas."""
        usuarios = []
        matriculas = []
        for alumno in self._registro.alumnos:
            if not alumno.documento:
                continue
            usuarios.append({
                "documento": alumno.documento.upper(),
                "id_tipo_documento": alumno.id_tipo_documento,
                "nombre": alumno.nombre,
                "apellido1": alumno.apellido1,
                "apellido2": alumno.apellido2,
                "email": alumno.email,
            })
            for centro in alumno.centros:
                for ciclo in centro.ciclos:
                    for modulo in ciclo.modulos:
                        matriculas.append({
                            "documento": alumno.documento.upper(),
                            "codigo_centro": centro.codigo,
                            "nombre_centro": centro.nombre,
                            "siglas_ciclo": ciclo.siglas,
                            "id_materia": modulo.id_materia,
                            "siglas_modulo": modulo.siglas,
                        })
        df_users = pd.DataFrame(usuarios)
        df_enrol = pd.DataFrame(matriculas)
        self._con.execute("CREATE OR REPLACE TABLE sigad_users AS SELECT * FROM df_users")
        self._con.execute("CREATE OR REPLACE TABLE sigad_enrolments AS SELECT * FROM df_enrol")
        logger.debug(
            f"SIGAD cargado: {len(usuarios)} usuarios, {len(matriculas)} matriculas"
        )

    def _cargar_moodle(self) -> None:
        """Carga el snapshot plano de Moodle en DuckDB."""
        users = [
            {
                "id": u.id,
                "username": u.username.lower(),
                "email": u.email,
                "firstname": u.firstname,
                "lastname": u.lastname,
                "suspended": u.suspended,
            }
            for u in self._snapshot.users
        ]
        user_map = {u.id: u.username.lower() for u in self._snapshot.users}
        enrolments = [
            {
                "user_id": e.user_id,
                "username": user_map.get(e.user_id, ""),
                "course_id": e.course_id,
                "shortname": e.shortname,
                "status": e.status,
            }
            for e in self._snapshot.enrolments
        ]
        df_users = pd.DataFrame(users)
        df_enrol = pd.DataFrame(enrolments)
        self._con.execute("CREATE OR REPLACE TABLE moodle_users AS SELECT * FROM df_users")
        self._con.execute(
            "CREATE OR REPLACE TABLE moodle_enrolments AS SELECT * FROM df_enrol"
        )
        logger.debug(
            f"Moodle cargado: {len(users)} usuarios, {len(enrolments)} matriculas"
        )

    # ------------------------------------------------------------------
    # Queries de delta
    # ------------------------------------------------------------------
    def _find_new_users(self) -> list[NewUserDelta]:
        """Altas: en SIGAD, no en Moodle."""
        df = self._con.execute("""
            SELECT s.documento
            FROM sigad_users s
            LEFT JOIN moodle_users m ON m.username = lower(s.documento)
            WHERE m.id IS NULL
        """).fetchdf()

        documentos = df["documento"].tolist() if not df.empty else []
        return [
            NewUserDelta(alumno=a)
            for a in self._registro.alumnos
            if a.documento and a.documento.upper() in documentos
        ]

    def _find_removed_users(self) -> list[RemovedUserDelta]:
        """Bajas: en Moodle, no en SIGAD."""
        protegidos = ",".join(str(i) for i in self._usuarios_protegidos) if self._usuarios_protegidos else "-1"
        df = self._con.execute(f"""
            SELECT m.id, m.username, m.email, m.firstname, m.lastname, m.suspended
            FROM moodle_users m
            LEFT JOIN sigad_users s ON lower(s.documento) = m.username
            WHERE s.documento IS NULL
              AND m.id NOT IN ({protegidos})
        """).fetchdf()

        if df.empty:
            return []
        return [
            RemovedUserDelta(
                user=MoodleUserRecord(
                    id=row["id"],
                    username=row["username"],
                    email=row["email"],
                    firstname=row["firstname"],
                    lastname=row["lastname"],
                    suspended=row["suspended"],
                )
            )
            for _, row in df.iterrows()
        ]

    def _find_email_changes(self) -> list[EmailChangeDelta]:
        """Emails diferentes entre SIGAD y Moodle."""
        df = self._con.execute("""
            SELECT
                s.documento,
                s.email AS email_sigad,
                m.email AS email_moodle
            FROM sigad_users s
            JOIN moodle_users m ON lower(s.documento) = m.username
            WHERE lower(s.email) <> lower(m.email)
               OR (s.email IS NOT NULL AND m.email IS NULL)
               OR (s.email IS NULL AND m.email IS NOT NULL)
        """).fetchdf()

        if df.empty:
            return []
        return [
            EmailChangeDelta(
                documento=row["documento"],
                email_sigad=row["email_sigad"] if pd.notna(row["email_sigad"]) else None,
                email_moodle=row["email_moodle"] if pd.notna(row["email_moodle"]) else None,
            )
            for _, row in df.iterrows()
        ]

    def _find_name_changes(self) -> list[NameChangeDelta]:
        """Nombre o apellidos diferentes entre SIGAD y Moodle."""
        df = self._con.execute("""
            SELECT
                s.documento,
                s.nombre,
                s.apellido1,
                s.apellido2,
                m.firstname,
                m.lastname
            FROM sigad_users s
            JOIN moodle_users m ON lower(s.documento) = m.username
            WHERE s.nombre <> m.firstname
               OR s.apellido1 <> split_part(m.lastname, ' ', 1)
               OR COALESCE(s.apellido2, '') <> trim(
                      replace(m.lastname, split_part(m.lastname, ' ', 1), '')
                  )
        """).fetchdf()

        if df.empty:
            return []
        return [
            NameChangeDelta(
                documento=row["documento"],
                nombre_sigad=row["nombre"] if pd.notna(row["nombre"]) else None,
                apellido1_sigad=row["apellido1"] if pd.notna(row["apellido1"]) else None,
                apellido2_sigad=row["apellido2"] if pd.notna(row["apellido2"]) else None,
                firstname_moodle=row["firstname"] if pd.notna(row["firstname"]) else None,
                lastname_moodle=row["lastname"] if pd.notna(row["lastname"]) else None,
            )
            for _, row in df.iterrows()
        ]

    def _find_username_changes(self) -> list[UsernameChangeDelta]:
        """Cambio de username (ej: NIE → DNI) detectado por coincidencia de email.

        Buscamos pares donde el email coincida pero el username de Moodle
        no coincida con el documento de SIGAD.
        """
        df = self._con.execute("""
            SELECT
                m.username AS old_username,
                s.documento AS new_documento,
                s.email AS email
            FROM moodle_users m
            JOIN sigad_users s ON lower(s.email) = lower(m.email)
            WHERE m.username <> lower(s.documento)
        """).fetchdf()

        if df.empty:
            return []
        return [
            UsernameChangeDelta(
                old_username=row["old_username"],
                new_documento=row["new_documento"],
                email=row["email"] if pd.notna(row["email"]) else None,
            )
            for _, row in df.iterrows()
        ]

    def _find_new_enrolments(self) -> list[EnrolmentDelta]:
        """Matrículas en SIGAD que no están en Moodle."""
        df = self._con.execute("""
            SELECT
                s.documento,
                s.siglas_modulo AS shortname
            FROM sigad_enrolments s
            LEFT JOIN moodle_enrolments me
                ON me.username = lower(s.documento)
               AND me.shortname = s.siglas_modulo
            WHERE me.course_id IS NULL
        """).fetchdf()

        if df.empty:
            return []
        return [
            EnrolmentDelta(
                documento=row["documento"],
                course_shortname=row["shortname"],
            )
            for _, row in df.iterrows()
        ]

    def _find_removed_enrolments(self) -> list[EnrolmentDelta]:
        """Matrículas en Moodle que no están en SIGAD."""
        df = self._con.execute("""
            SELECT
                me.username AS documento,
                me.shortname,
                me.course_id
            FROM moodle_enrolments me
            LEFT JOIN sigad_enrolments se
                ON lower(se.documento) = me.username
               AND se.siglas_modulo = me.shortname
            WHERE se.documento IS NULL
        """).fetchdf()

        if df.empty:
            return []
        return [
            EnrolmentDelta(
                documento=row["documento"],
                course_shortname=row["shortname"],
                course_id=row["course_id"],
            )
            for _, row in df.iterrows()
        ]

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def analyze(self) -> SyncReport:
        """Ejecuta el análisis completo y devuelve el reporte de deltas."""
        logger.info("Iniciando análisis de sincronización")
        report = SyncReport(
            new_users=self._find_new_users(),
            removed_users=self._find_removed_users(),
            email_changes=self._find_email_changes(),
            name_changes=self._find_name_changes(),
            username_changes=self._find_username_changes(),
            new_enrolments=self._find_new_enrolments(),
            removed_enrolments=self._find_removed_enrolments(),
        )
        logger.info(
            f"Análisis completado: {len(report.new_users)} altas, "
            f"{len(report.removed_users)} bajas, "
            f"{len(report.email_changes)} email_changes, "
            f"{len(report.name_changes)} name_changes, "
            f"{len(report.username_changes)} username_changes, "
            f"{len(report.new_enrolments)} matrículas nuevas, "
            f"{len(report.removed_enrolments)} matrículas eliminadas"
        )
        return report
