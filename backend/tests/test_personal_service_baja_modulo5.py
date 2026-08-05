"""Casos nuevos sobre PersonalService.dar_de_baja_doctor, agregados por el
Modulo 5 (Task 7 del plan).
"""
from tests.factories import crear_clinica, crear_doctor, crear_paciente
from tests.test_plan_tratamiento_models import crear_plan


def _service(db):
    from app.services.personal_service import PersonalService

    return PersonalService(db)


def test_dar_de_baja_doctor_sin_planes_sigue_funcionando(db_session):
    clinica = crear_clinica(db_session)
    doctor = crear_doctor(db_session, clinica.id_clinica)

    assert _service(db_session).dar_de_baja_doctor(clinica.id_clinica, doctor.id_doctor) is True


def test_dar_de_baja_doctor_con_plan_activo_bloquea(db_session):
    from app.exceptions import ReferenciaEnUsoError
    from app.models import EstadoPlanTratamiento

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    crear_plan(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor,
        estado=EstadoPlanTratamiento.EN_PROGRESO,
    )

    try:
        _service(db_session).dar_de_baja_doctor(clinica.id_clinica, doctor.id_doctor)
        assert False, "debia lanzar ReferenciaEnUsoError"
    except ReferenciaEnUsoError:
        pass
    db_session.refresh(doctor)
    assert doctor.activo is True


def test_dar_de_baja_doctor_con_planes_terminales_no_bloquea(db_session):
    from app.models import EstadoPlanTratamiento

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    crear_plan(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor,
        estado=EstadoPlanTratamiento.CANCELADO,
    )

    assert _service(db_session).dar_de_baja_doctor(clinica.id_clinica, doctor.id_doctor) is True
