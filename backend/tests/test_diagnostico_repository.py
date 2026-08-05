from tests.factories import crear_clinica, crear_doctor, crear_paciente
from tests.test_expediente_models import crear_consulta


def _repo(db):
    from app.repositories.diagnostico_repository import DiagnosticoRepository

    return DiagnosticoRepository(db)


def _crear_diagnostico(db, id_clinica, id_consulta, **campos):
    datos = {"descripcion": "Caries"}
    datos.update(campos)
    return _repo(db).crear(id_clinica, {"id_consulta": id_consulta, **datos})


def test_listar_de_consulta(db_session):
    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    consulta = crear_consulta(db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor)
    _crear_diagnostico(db_session, clinica.id_clinica, consulta.id_consulta, descripcion="Caries molar")
    _crear_diagnostico(db_session, clinica.id_clinica, consulta.id_consulta, descripcion="Gingivitis")

    resultado = _repo(db_session).listar(clinica.id_clinica, id_consulta=consulta.id_consulta)
    assert len(resultado) == 2


def test_aislamiento_entre_clinicas(db_session):
    clinica_a = crear_clinica(db_session, nombre="A")
    clinica_b = crear_clinica(db_session, nombre="B")
    paciente = crear_paciente(db_session, clinica_a.id_clinica)
    doctor = crear_doctor(db_session, clinica_a.id_clinica)
    consulta = crear_consulta(db_session, clinica_a.id_clinica, paciente.id_paciente, doctor.id_doctor)
    diagnostico = _crear_diagnostico(db_session, clinica_a.id_clinica, consulta.id_consulta)

    assert _repo(db_session).obtener(clinica_b.id_clinica, diagnostico.id_diagnostico) is None


def test_eliminar_no_implementado(db_session):
    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    consulta = crear_consulta(db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor)
    diagnostico = _crear_diagnostico(db_session, clinica.id_clinica, consulta.id_consulta)

    try:
        _repo(db_session).eliminar(clinica.id_clinica, diagnostico.id_diagnostico)
        assert False, "debia lanzar NotImplementedError"
    except NotImplementedError:
        pass
