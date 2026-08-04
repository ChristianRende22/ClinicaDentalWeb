from datetime import datetime

from sqlalchemy import text


def _clinica_con_gente(db_session):
    """Devuelve (clinica, paciente, doctor) listos para colgarles una cita."""
    from app.models import Clinica, Doctor, Paciente, RolUsuario, Usuario

    clinica = Clinica(nombre="Dental A")
    db_session.add(clinica)
    db_session.flush()

    usuario = Usuario(
        id_clinica=clinica.id_clinica,
        username="dra.perez",
        password_hash="x",
        rol=RolUsuario.DOCTOR,
    )
    paciente = Paciente(
        id_clinica=clinica.id_clinica,
        nombre="Ana",
        apellido="Lopez",
        telefono="70001122",
    )
    db_session.add_all([usuario, paciente])
    db_session.flush()

    doctor = Doctor(
        id_clinica=clinica.id_clinica,
        id_usuario=usuario.id_usuario,
        nombre="Marta",
        apellido="Perez",
        telefono="70003344",
    )
    db_session.add(doctor)
    db_session.flush()
    return clinica, paciente, doctor


def test_cita_nace_programada_sin_reagendamientos(db_session):
    from app.models import Cita, EstadoCita

    clinica, paciente, doctor = _clinica_con_gente(db_session)
    cita = Cita(
        id_clinica=clinica.id_clinica,
        id_paciente=paciente.id_paciente,
        id_doctor=doctor.id_doctor,
        fecha_hora=datetime(2026, 9, 1, 9, 0),
        duracion_minutos=30,
    )
    db_session.add(cita)
    db_session.flush()

    assert cita.id_cita is not None
    assert cita.estado == EstadoCita.PROGRAMADA
    assert cita.veces_reagendada == 0
    assert cita.id_consultorio is None
    assert cita.id_asistente is None


def test_estado_cita_persiste_el_valor_en_minuscula_no_el_nombre(db_session):
    """Bug conocido #2: sin values_callable, MySQL guardaria 'PROGRAMADA'."""
    from app.models import Cita

    clinica, paciente, doctor = _clinica_con_gente(db_session)
    db_session.add(
        Cita(
            id_clinica=clinica.id_clinica,
            id_paciente=paciente.id_paciente,
            id_doctor=doctor.id_doctor,
            fecha_hora=datetime(2026, 9, 1, 9, 0),
            duracion_minutos=30,
        )
    )
    db_session.flush()

    guardado = db_session.execute(text("SELECT estado FROM cita")).scalar_one()
    assert guardado == "programada"


def test_transiciones_permitidas_cubre_los_cinco_estados():
    from app.models import TRANSICIONES_PERMITIDAS, EstadoCita

    assert set(TRANSICIONES_PERMITIDAS) == set(EstadoCita)


def test_los_tres_estados_terminales_no_admiten_transiciones():
    from app.models import TRANSICIONES_PERMITIDAS, EstadoCita

    for terminal in (EstadoCita.COMPLETADA, EstadoCita.CANCELADA, EstadoCita.NO_ASISTIO):
        assert TRANSICIONES_PERMITIDAS[terminal] == set()


def test_solo_se_completa_o_se_marca_ausente_desde_confirmada():
    from app.models import TRANSICIONES_PERMITIDAS, EstadoCita

    assert TRANSICIONES_PERMITIDAS[EstadoCita.PROGRAMADA] == {
        EstadoCita.CONFIRMADA,
        EstadoCita.CANCELADA,
    }
    assert TRANSICIONES_PERMITIDAS[EstadoCita.CONFIRMADA] == {
        EstadoCita.COMPLETADA,
        EstadoCita.NO_ASISTIO,
        EstadoCita.CANCELADA,
    }


def test_estados_activos_son_los_que_ocupan_agenda():
    from app.models import ESTADOS_ACTIVOS, EstadoCita

    assert ESTADOS_ACTIVOS == frozenset({EstadoCita.PROGRAMADA, EstadoCita.CONFIRMADA})
