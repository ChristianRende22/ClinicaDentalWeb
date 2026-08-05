from datetime import datetime

from tests.factories import crear_clinica, crear_doctor, crear_paciente


def _service(db):
    from app.services.consulta_service import ConsultaService

    return ConsultaService(db)


def _datos(paciente, doctor):
    return {
        "id_paciente": paciente.id_paciente,
        "id_doctor": doctor.id_doctor,
        "fecha_hora": datetime(2026, 9, 1, 9, 0),
    }


def test_crear_camino_feliz(db_session):
    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)

    consulta = _service(db_session).crear(clinica.id_clinica, _datos(paciente, doctor))
    assert consulta.id_consulta is not None


def test_crear_paciente_inexistente(db_session):
    from app.exceptions import ReferenciaInvalidaError

    clinica = crear_clinica(db_session)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    datos = _datos(type("P", (), {"id_paciente": 9999})(), doctor)

    try:
        _service(db_session).crear(clinica.id_clinica, datos)
        assert False, "debia lanzar ReferenciaInvalidaError"
    except ReferenciaInvalidaError:
        pass


def test_crear_paciente_inactivo(db_session):
    from app.exceptions import ReferenciaInvalidaError
    from app.repositories.paciente_repository import PacienteRepository

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    PacienteRepository(db_session).eliminar(clinica.id_clinica, paciente.id_paciente)

    try:
        _service(db_session).crear(clinica.id_clinica, _datos(paciente, doctor))
        assert False, "debia lanzar ReferenciaInvalidaError"
    except ReferenciaInvalidaError:
        pass


def test_crear_doctor_de_otra_clinica(db_session):
    from app.exceptions import ReferenciaInvalidaError

    clinica_a = crear_clinica(db_session, nombre="A")
    clinica_b = crear_clinica(db_session, nombre="B")
    paciente = crear_paciente(db_session, clinica_a.id_clinica)
    doctor_b = crear_doctor(db_session, clinica_b.id_clinica)

    try:
        _service(db_session).crear(clinica_a.id_clinica, _datos(paciente, doctor_b))
        assert False, "debia lanzar ReferenciaInvalidaError"
    except ReferenciaInvalidaError:
        pass
