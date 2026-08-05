from datetime import datetime

from tests.factories import crear_clinica, crear_doctor, crear_paciente
from tests.test_expediente_models import crear_consulta


def _repo(db):
    from app.repositories.consulta_repository import ConsultaRepository

    return ConsultaRepository(db)


def test_listar_ordena_mas_reciente_primero(db_session):
    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    vieja = crear_consulta(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor,
        fecha_hora=datetime(2026, 1, 1, 9, 0),
    )
    nueva = crear_consulta(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor,
        fecha_hora=datetime(2026, 6, 1, 9, 0),
    )

    resultado = _repo(db_session).listar(clinica.id_clinica, id_paciente=paciente.id_paciente)
    assert [c.id_consulta for c in resultado] == [nueva.id_consulta, vieja.id_consulta]


def test_listar_filtra_por_doctor_y_rango_de_fechas(db_session):
    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor_a = crear_doctor(db_session, clinica.id_clinica, username="dra.a")
    doctor_b = crear_doctor(db_session, clinica.id_clinica, username="dra.b")
    crear_consulta(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor_a.id_doctor,
        fecha_hora=datetime(2026, 3, 1, 9, 0),
    )
    crear_consulta(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor_b.id_doctor,
        fecha_hora=datetime(2026, 3, 2, 9, 0),
    )

    resultado = _repo(db_session).listar(clinica.id_clinica, id_doctor=doctor_a.id_doctor)
    assert len(resultado) == 1
    assert resultado[0].id_doctor == doctor_a.id_doctor

    resultado = _repo(db_session).listar(
        clinica.id_clinica, desde=datetime(2026, 3, 2), hasta=datetime(2026, 3, 3)
    )
    assert len(resultado) == 1


def test_aislamiento_entre_clinicas(db_session):
    clinica_a = crear_clinica(db_session, nombre="A")
    clinica_b = crear_clinica(db_session, nombre="B")
    paciente = crear_paciente(db_session, clinica_a.id_clinica)
    doctor = crear_doctor(db_session, clinica_a.id_clinica)
    consulta = crear_consulta(db_session, clinica_a.id_clinica, paciente.id_paciente, doctor.id_doctor)

    assert _repo(db_session).obtener(clinica_b.id_clinica, consulta.id_consulta) is None


def test_eliminar_no_implementado(db_session):
    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    consulta = crear_consulta(db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor)

    try:
        _repo(db_session).eliminar(clinica.id_clinica, consulta.id_consulta)
        assert False, "debia lanzar NotImplementedError"
    except NotImplementedError:
        pass
