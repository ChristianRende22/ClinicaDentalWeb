from tests.factories import crear_clinica, crear_doctor, crear_paciente
from tests.test_expediente_models import crear_tratamiento
from tests.test_plan_tratamiento_models import crear_plan


def _repo(db):
    from app.repositories.tratamiento_repository import TratamientoRepository

    return TratamientoRepository(db)


def test_es_subclase_de_catalogo_repository_apuntando_al_modelo_correcto():
    from app.models import Tratamiento
    from app.repositories.tratamiento_repository import TratamientoRepository

    assert TratamientoRepository.model is Tratamiento


def test_eliminar_desactiva_un_tratamiento_sin_uso(db_session):
    clinica = crear_clinica(db_session)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica)

    assert _repo(db_session).eliminar(clinica.id_clinica, tratamiento.id_tratamiento) is True
    db_session.refresh(tratamiento)
    assert tratamiento.activo is False


def test_eliminar_bloquea_si_hay_detalle_pendiente(db_session):
    from app.exceptions import ReferenciaEnUsoError
    from app.repositories.plan_tratamiento_repository import PlanTratamientoDetalleRepository

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica)
    plan = crear_plan(db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor)
    PlanTratamientoDetalleRepository(db_session).crear(
        plan.id_plan,
        {"id_tratamiento": tratamiento.id_tratamiento, "precio_unitario": tratamiento.precio},
    )

    try:
        _repo(db_session).eliminar(clinica.id_clinica, tratamiento.id_tratamiento)
        assert False, "debia lanzar ReferenciaEnUsoError"
    except ReferenciaEnUsoError:
        pass
    db_session.refresh(tratamiento)
    assert tratamiento.activo is True


def test_eliminar_bloquea_si_hay_detalle_en_progreso(db_session):
    from app.exceptions import ReferenciaEnUsoError
    from app.models import EstadoDetallePlanTratamiento
    from app.repositories.plan_tratamiento_repository import PlanTratamientoDetalleRepository

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica)
    plan = crear_plan(db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor)
    PlanTratamientoDetalleRepository(db_session).crear(
        plan.id_plan,
        {
            "id_tratamiento": tratamiento.id_tratamiento,
            "precio_unitario": tratamiento.precio,
            "estado": EstadoDetallePlanTratamiento.EN_PROGRESO,
        },
    )

    try:
        _repo(db_session).eliminar(clinica.id_clinica, tratamiento.id_tratamiento)
        assert False, "debia lanzar ReferenciaEnUsoError"
    except ReferenciaEnUsoError:
        pass


def test_eliminar_no_bloquea_si_el_detalle_esta_completado_o_cancelado(db_session):
    from app.models import EstadoDetallePlanTratamiento
    from app.repositories.plan_tratamiento_repository import PlanTratamientoDetalleRepository

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica)
    plan = crear_plan(db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor)
    PlanTratamientoDetalleRepository(db_session).crear(
        plan.id_plan,
        {
            "id_tratamiento": tratamiento.id_tratamiento,
            "precio_unitario": tratamiento.precio,
            "estado": EstadoDetallePlanTratamiento.COMPLETADO,
        },
    )

    assert _repo(db_session).eliminar(clinica.id_clinica, tratamiento.id_tratamiento) is True


def test_aislamiento_entre_clinicas(db_session):
    clinica_a = crear_clinica(db_session, nombre="A")
    clinica_b = crear_clinica(db_session, nombre="B")
    tratamiento = crear_tratamiento(db_session, clinica_a.id_clinica)

    assert _repo(db_session).obtener(clinica_b.id_clinica, tratamiento.id_tratamiento) is None
    assert _repo(db_session).listar(clinica_b.id_clinica) == []
