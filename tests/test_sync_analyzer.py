"""Tests unitarios para SyncAnalyzer.

Usan datos locales (sin red) para validar la lógica de comparación
SIGAD ↔ Moodle en DuckDB.
"""

import pytest

from gestion_alumnos.models import (
    MoodleCourseRecord,
    MoodleEnrolmentRecord,
    MoodleSnapshot,
    MoodleUserRecord,
    Registro,
)
from gestion_alumnos.services.sync_analyzer import SyncAnalyzer


@pytest.fixture
def registro_sigad() -> Registro:
    """Registro de test con 2 alumnos."""
    return Registro.model_validate({
        "fecha": "15/12/2025",
        "hora": "11:42:28",
        "alumnos": [
            {
                "idAlumno": 16839,
                "idTipoDocumento": 1,
                "documento": "78842153Q",
                "nombre": "Valeria",
                "apellido1": "Torres",
                "apellido2": "Medina",
                "email": "valeria.torres.medina@ejemplo.com",
                "centros": [
                    {
                        "codigoCentro": "50009348",
                        "centro": "AVEMPACE",
                        "ciclos": [
                            {
                                "idFicha": 22,
                                "codigoCiclo": "12242301",
                                "ciclo": "Educación Infantil",
                                "siglasCiclo": "SSC302",
                                "modulos": [
                                    {
                                        "idMateria": 18599,
                                        "modulo": "IPPE1",
                                        "siglasModulo": "IPPE1",
                                    }
                                ],
                            }
                        ],
                    }
                ],
            },
            {
                "idAlumno": 16840,
                "idTipoDocumento": 1,
                "documento": "12345678A",
                "nombre": "Juan",
                "apellido1": "Pérez",
                "apellido2": "García",
                "email": "juan.perez@ejemplo.com",
                "centros": [
                    {
                        "codigoCentro": "50009349",
                        "centro": "IES TEST",
                        "ciclos": [
                            {
                                "idFicha": 23,
                                "codigoCiclo": "12242302",
                                "ciclo": "DAW",
                                "siglasCiclo": "DAW",
                                "modulos": [
                                    {
                                        "idMateria": 18600,
                                        "modulo": "Programación",
                                        "siglasModulo": "PROG",
                                    },
                                    {
                                        "idMateria": 18601,
                                        "modulo": "Bases de Datos",
                                        "siglasModulo": "BD",
                                    },
                                ],
                            }
                        ],
                    }
                ],
            },
        ],
    })


@pytest.fixture
def snapshot_moodle() -> MoodleSnapshot:
    """Snapshot de Moodle con 2 usuarios y matriculaciones mixtas."""
    return MoodleSnapshot(
        users=[
            # Usuario 1: coincide con SIGAD, email cambiado
            MoodleUserRecord(
                id=101,
                username="78842153q",
                email="valeria.torres@ejemplo.com",  # cambiado
                firstname="Valeria",
                lastname="Torres Medina",
                suspended=0,
            ),
            # Usuario 2: está en Moodle pero no en SIGAD (baja)
            MoodleUserRecord(
                id=102,
                username="99999999z",
                email="viejo@ejemplo.com",
                firstname="Antiguo",
                lastname="Usuario",
                suspended=0,
            ),
        ],
        courses=[
            MoodleCourseRecord(id=1, shortname="50009348-SSC302-18599", fullname="IPPE1"),
            MoodleCourseRecord(id=2, shortname="50009349-DAW-18600", fullname="PROG"),
            MoodleCourseRecord(id=3, shortname="50009349-DAW-18601", fullname="BD"),
        ],
        enrolments=[
            # Valeria matriculada en IPPE1 (correcto)
            MoodleEnrolmentRecord(user_id=101, course_id=1, shortname="50009348-SSC302-18599", status=0),
            # Valeria también matriculada en PROG (ya no debería, es de Juan)
            MoodleEnrolmentRecord(user_id=101, course_id=2, shortname="50009349-DAW-18600", status=0),
            # Usuario viejo matriculado en BD
            MoodleEnrolmentRecord(user_id=102, course_id=3, shortname="50009349-DAW-18601", status=0),
        ],
    )


class TestSyncAnalyzer:
    """Valida detección de deltas entre SIGAD y Moodle."""

    def test_new_users_detected(self, registro_sigad, snapshot_moodle):
        """Juan (12345678A) está en SIGAD pero no en Moodle → alta."""
        analyzer = SyncAnalyzer(registro_sigad, snapshot_moodle)
        report = analyzer.analyze()

        assert len(report.new_users) == 1
        assert report.new_users[0].alumno.documento == "12345678A"

    def test_removed_users_detected(self, registro_sigad, snapshot_moodle):
        """Usuario 99999999Z está en Moodle pero no en SIGAD → baja."""
        analyzer = SyncAnalyzer(registro_sigad, snapshot_moodle)
        report = analyzer.analyze()

        assert len(report.removed_users) == 1
        assert report.removed_users[0].user.username == "99999999z"

    def test_email_changes_detected(self, registro_sigad, snapshot_moodle):
        """Valeria tiene email diferente entre SIGAD y Moodle."""
        analyzer = SyncAnalyzer(registro_sigad, snapshot_moodle)
        report = analyzer.analyze()

        assert len(report.email_changes) == 1
        delta = report.email_changes[0]
        assert delta.documento == "78842153Q"
        assert delta.email_sigad == "valeria.torres.medina@ejemplo.com"
        assert delta.email_moodle == "valeria.torres@ejemplo.com"

    def test_new_enrolments_detected(self, registro_sigad, snapshot_moodle):
        """Juan debería estar matriculado en PROG y BD pero no lo está."""
        analyzer = SyncAnalyzer(registro_sigad, snapshot_moodle)
        report = analyzer.analyze()

        docs = {e.documento for e in report.new_enrolments}
        mods = {e.course_shortname for e in report.new_enrolments}
        assert "12345678A" in docs
        assert "PROG" in mods
        assert "BD" in mods

    def test_removed_enrolments_detected(self, registro_sigad, snapshot_moodle):
        """Valeria está matriculada en PROG en Moodle pero no en SIGAD."""
        analyzer = SyncAnalyzer(registro_sigad, snapshot_moodle)
        report = analyzer.analyze()

        removed = [(e.documento, e.course_shortname) for e in report.removed_enrolments]
        assert ("78842153q", "50009349-DAW-18600") in removed

    def test_report_has_changes(self, registro_sigad, snapshot_moodle):
        analyzer = SyncAnalyzer(registro_sigad, snapshot_moodle)
        report = analyzer.analyze()
        assert report.has_changes is True
