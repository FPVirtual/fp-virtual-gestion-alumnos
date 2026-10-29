"""Tests unitarios para SyncApplier.

Validan la aplicación de deltas sobre el sink, las notificaciones por
email conectadas al flujo y los portados desde curso2627 (reactivación,
fallback de desmatriculación).
"""

from unittest.mock import MagicMock

import pytest

from gestion_alumnos.models import (
    Alumno,
    Centro,
    Ciclo,
    Modulo,
    MoodleUserRecord,
    ReactivationDelta,
    RemovedUserDelta,
    SyncReport,
    UsernameChangeDelta,
    EnrolmentDelta,
)
from gestion_alumnos.services.sync_applier import SyncApplier


@pytest.fixture
def alumno_maria_marin():
    """Caso límite: el nombre aparece dentro del apellido."""
    return Alumno(
        idAlumno=16839,
        idTipoDocumento=1,
        documento="78842153Q",
        nombre="María",
        apellido1="Marín",
        apellido2=None,
        email="maria.marin@ejemplo.com",
        centros=[
            Centro(
                codigoCentro="50009348",
                centro="AVEMPACE",
                ciclos=[
                    Ciclo(
                        idFicha=22,
                        codigoCiclo="12242301",
                        ciclo="Test",
                        siglasCiclo="SSC302",
                        modulos=[
                            Modulo(idMateria=18599, modulo="IPPE1", siglasModulo="IPPE1"),
                        ],
                    )
                ],
            )
        ],
    )


@pytest.fixture
def sink():
    s = MagicMock()
    s.create_user.return_value = 999
    s.update_user.return_value = True
    s.update_user_username.return_value = True
    s.suspend_user.return_value = True
    s.reactivate_user.return_value = True
    s.enrol_user_to_course.return_value = True
    s.enrol_user_to_cohort.return_value = True
    s.suspend_enrolment.side_effect = NotImplementedError("requiere plugin")
    s.unenrol_user_from_course.return_value = True
    return s


@pytest.fixture
def email_repo():
    return MagicMock()


class TestNotificacionesEmail:
    """El applier notifica altas, cambios de username y matrículas."""

    def test_alta_envia_bienvenida(self, alumno_maria_marin, sink, email_repo):
        from gestion_alumnos.models import NewUserDelta
        report = SyncReport(new_users=[NewUserDelta(alumno=alumno_maria_marin)])

        applier = SyncApplier(report, sink, email_repo=email_repo)
        applier.apply()

        email_repo.enviar_bienvenida_nuevo_usuario.assert_called_once()
        alumno_arg, password_arg, matriculas_arg = (
            email_repo.enviar_bienvenida_nuevo_usuario.call_args.args
        )
        assert matriculas_arg == ["IPPE1"]
        assert len(password_arg) == 10

    def test_apellido_no_se_corrompe_si_contiene_el_nombre(
        self, alumno_maria_marin, sink
    ):
        """'María Marín': el apellido debe ser 'Marín', no ''."""
        from gestion_alumnos.models import NewUserDelta
        report = SyncReport(new_users=[NewUserDelta(alumno=alumno_maria_marin)])

        applier = SyncApplier(report, sink)
        applier.apply()

        kwargs = sink.create_user.call_args.kwargs
        assert kwargs["apellido"] == "Marín"

    def test_cambio_username_envia_aviso(self, sink, email_repo):
        report = SyncReport(
            username_changes=[
                UsernameChangeDelta(
                    old_username="x1234567z",
                    new_documento="12345678Z",
                    email="pepe@ejemplo.com",
                )
            ]
        )
        applier = SyncApplier(report, sink, email_repo=email_repo)
        applier.apply()

        email_repo.enviar_actualizacion_usuario.assert_called_once()
        alumno_arg, anterior_arg = (
            email_repo.enviar_actualizacion_usuario.call_args.args
        )
        assert anterior_arg == "x1234567z"
        assert alumno_arg.documento == "12345678Z"
        assert alumno_arg.username_moodle == "12345678z"

    def test_nuevas_matriculas_agrupadas_por_alumno(
        self, alumno_maria_marin, sink, email_repo
    ):
        report = SyncReport(
            new_enrolments=[
                EnrolmentDelta(documento="78842153Q", course_shortname="PROG"),
                EnrolmentDelta(documento="78842153Q", course_shortname="BD"),
            ]
        )
        resolver = MagicMock(return_value=alumno_maria_marin)
        applier = SyncApplier(
            report, sink, {"PROG": "2", "BD": "3"},
            email_repo=email_repo,
            alumno_por_documento=resolver,
        )
        applier.apply()

        email_repo.enviar_nuevas_matriculas.assert_called_once()
        matriculas_arg = email_repo.enviar_nuevas_matriculas.call_args.args[1]
        assert sorted(matriculas_arg) == ["BD", "PROG"]

    def test_errores_de_email_no_bloquean_sync(self, alumno_maria_marin, sink, email_repo):
        from gestion_alumnos.models import NewUserDelta
        email_repo.enviar_bienvenida_nuevo_usuario.side_effect = Exception("SMTP caído")
        report = SyncReport(new_users=[NewUserDelta(alumno=alumno_maria_marin)])

        applier = SyncApplier(report, sink, email_repo=email_repo)
        stats = applier.apply()

        assert stats["users_created"] == 1
        assert stats["users_created_errors"] == []


class TestReactivaciones:
    """Portado desde curso2627 (commit 31a6b83)."""

    def test_reactivar_incluye_cohorte_alumnado(self, sink):
        report = SyncReport(
            reactivations=[
                ReactivationDelta(
                    user=MoodleUserRecord(
                        id=101,
                        username="78842153q",
                        email="78842153q@fpvirtualaragon.es",
                        firstname="María",
                        lastname="Marín",
                        suspended=1,
                    )
                )
            ]
        )
        applier = SyncApplier(report, sink)
        stats = applier.apply()

        sink.reactivate_user.assert_called_once_with("78842153q")
        sink.enrol_user_to_cohort.assert_called_once_with("78842153q", "alumnado")
        assert stats["users_reactivated"] == 1

    def test_error_de_reactivacion_no_bloquea(self, sink):
        sink.reactivate_user.side_effect = Exception("API caída")
        report = SyncReport(
            reactivations=[
                ReactivationDelta(
                    user=MoodleUserRecord(
                        id=101,
                        username="78842153q",
                        email="a@b.es",
                        firstname="A",
                        lastname="B",
                        suspended=1,
                    )
                )
            ]
        )
        applier = SyncApplier(report, sink)
        stats = applier.apply()

        assert stats["users_reactivated"] == 0
        assert len(stats["users_reactivated_errors"]) == 1


class TestDesmatriculacion:
    """El fallback usa unenrol, no enrol (bug de la revisión de seguridad)."""

    def test_fallback_desmatricula_al_no_haber_suspension(self, sink):
        report = SyncReport(
            removed_enrolments=[
                EnrolmentDelta(
                    documento="78842153Q",
                    course_shortname="PROG",
                    course_id=2,
                )
            ]
        )
        applier = SyncApplier(report, sink)
        stats = applier.apply()

        sink.suspend_enrolment.assert_called_once()
        sink.unenrol_user_from_course.assert_called_once_with("78842153q", "2")
        sink.enrol_user_to_course.assert_not_called()
        assert stats["enrolments_removed"] == 1
