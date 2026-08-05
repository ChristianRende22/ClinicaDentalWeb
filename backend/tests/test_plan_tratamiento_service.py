from tests.factories import crear_clinica, crear_doctor, crear_paciente
from tests.test_expediente_models import crear_tratamiento


def _service(db):
    from app.services.plan_tratamiento_service import PlanTratamientoService

    return PlanTratamientoService(db)


def _crear_plan(db, id_clinica, paciente, doctor):
    return _service(db).crear(
        id_clinica, {"id_paciente": paciente.id_paciente, "id_doctor": doctor.id_doctor}
    )


def test_crear_valida_paciente_y_doctor(db_session):
    from app.exceptions import ReferenciaInvalidaError

    clinica = crear_clinica(db_session)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    try:
        _service(db_session).crear(
            clinica.id_clinica, {"id_paciente": 9999, "id_doctor": doctor.id_doctor}
        )
        assert False, "debia lanzar ReferenciaInvalidaError"
    except ReferenciaInvalidaError:
        pass


def test_agregar_detalle_copia_el_precio_del_catalogo(db_session):
    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica, precio="25.00")
    plan = _crear_plan(db_session, clinica.id_clinica, paciente, doctor)

    detalle = _service(db_session).agregar_detalle(
        clinica.id_clinica, plan.id_plan, {"id_tratamiento": tratamiento.id_tratamiento}
    )
    assert str(detalle.precio_unitario) == "25.00"

    # Subir el precio del catalogo despues no mueve el detalle ya agregado.
    tratamiento.precio = "40.00"
    db_session.flush()
    db_session.refresh(detalle)
    assert str(detalle.precio_unitario) == "25.00"


def test_agregar_detalle_rechaza_tratamiento_inactivo(db_session):
    from app.exceptions import ReferenciaInvalidaError
    from app.repositories.tratamiento_repository import TratamientoRepository

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica)
    TratamientoRepository(db_session).eliminar(clinica.id_clinica, tratamiento.id_tratamiento)
    plan = _crear_plan(db_session, clinica.id_clinica, paciente, doctor)

    try:
        _service(db_session).agregar_detalle(
            clinica.id_clinica, plan.id_plan, {"id_tratamiento": tratamiento.id_tratamiento}
        )
        assert False, "debia lanzar ReferenciaInvalidaError"
    except ReferenciaInvalidaError:
        pass


def test_cambiar_estado_detalle_respeta_transiciones(db_session):
    from app.exceptions import TransicionInvalidaError
    from app.models import EstadoDetallePlanTratamiento

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica)
    plan = _crear_plan(db_session, clinica.id_clinica, paciente, doctor)
    detalle = _service(db_session).agregar_detalle(
        clinica.id_clinica, plan.id_plan, {"id_tratamiento": tratamiento.id_tratamiento}
    )

    servicio = _service(db_session)
    detalle = servicio.cambiar_estado_detalle(
        clinica.id_clinica, plan.id_plan, detalle.id_detalle, EstadoDetallePlanTratamiento.EN_PROGRESO
    )
    assert detalle.estado == EstadoDetallePlanTratamiento.EN_PROGRESO

    detalle = servicio.cambiar_estado_detalle(
        clinica.id_clinica, plan.id_plan, detalle.id_detalle, EstadoDetallePlanTratamiento.COMPLETADO
    )
    assert detalle.estado == EstadoDetallePlanTratamiento.COMPLETADO

    try:
        servicio.cambiar_estado_detalle(
            clinica.id_clinica, plan.id_plan, detalle.id_detalle, EstadoDetallePlanTratamiento.PENDIENTE
        )
        assert False, "debia lanzar TransicionInvalidaError"
    except TransicionInvalidaError:
        pass


def test_cambiar_estado_plan_respeta_transiciones(db_session):
    from app.exceptions import TransicionInvalidaError
    from app.models import EstadoPlanTratamiento

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    plan = _crear_plan(db_session, clinica.id_clinica, paciente, doctor)

    servicio = _service(db_session)
    plan = servicio.cambiar_estado(clinica.id_clinica, plan.id_plan, EstadoPlanTratamiento.APROBADO)
    assert plan.estado == EstadoPlanTratamiento.APROBADO
    plan = servicio.cambiar_estado(
        clinica.id_clinica, plan.id_plan, EstadoPlanTratamiento.EN_PROGRESO
    )
    assert plan.estado == EstadoPlanTratamiento.EN_PROGRESO

    try:
        servicio.cambiar_estado(clinica.id_clinica, plan.id_plan, EstadoPlanTratamiento.CANCELADO)
        assert False, "debia lanzar TransicionInvalidaError: en_progreso no cancela de un tiro"
    except TransicionInvalidaError:
        pass

    plan = servicio.cambiar_estado(
        clinica.id_clinica, plan.id_plan, EstadoPlanTratamiento.COMPLETADO
    )
    assert plan.estado == EstadoPlanTratamiento.COMPLETADO
