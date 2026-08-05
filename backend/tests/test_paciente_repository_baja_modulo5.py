"""Casos nuevos sobre PacienteRepository.eliminar, agregados por el Modulo 5
(Task 7 del plan). Se dejan en archivo propio para no mezclar con los tests
del Modulo 4 ya existentes.
"""
from tests.factories import crear_clinica, crear_doctor, crear_paciente
from tests.test_plan_tratamiento_models import crear_plan


def _repo(db):
    from app.repositories.paciente_repository import PacienteRepository

    return PacienteRepository(db)


def test_eliminar_paciente_sin_planes_sigue_funcionando(db_session):
    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)

    assert _repo(db_session).eliminar(clinica.id_clinica, paciente.id_paciente) is True


def test_eliminar_paciente_con_plan_activo_bloquea(db_session):
    from app.exceptions import ReferenciaEnUsoError
    from app.models import EstadoPlanTratamiento

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    crear_plan(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor,
        estado=EstadoPlanTratamiento.APROBADO,
    )

    try:
        _repo(db_session).eliminar(clinica.id_clinica, paciente.id_paciente)
        assert False, "debia lanzar ReferenciaEnUsoError"
    except ReferenciaEnUsoError:
        pass
    db_session.refresh(paciente)
    assert paciente.activo is True


def test_eliminar_paciente_con_planes_terminales_no_bloquea(db_session):
    from app.models import EstadoPlanTratamiento

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    crear_plan(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor,
        estado=EstadoPlanTratamiento.COMPLETADO,
    )
    crear_plan(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor,
        estado=EstadoPlanTratamiento.CANCELADO,
    )

    assert _repo(db_session).eliminar(clinica.id_clinica, paciente.id_paciente) is True
