from tests.factories import crear_clinica, crear_doctor, crear_paciente
from tests.test_expediente_models import crear_tratamiento


def crear_plan(db, id_clinica, id_paciente, id_doctor, **campos):
    from app.models import PlanTratamiento

    plan = PlanTratamiento(
        id_clinica=id_clinica, id_paciente=id_paciente, id_doctor=id_doctor, **campos
    )
    db.add(plan)
    db.flush()
    return plan


def test_plan_tratamiento_estado_default_borrador(db_session):
    from app.models import EstadoPlanTratamiento

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    plan = crear_plan(db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor)
    db_session.refresh(plan)
    assert plan.estado == EstadoPlanTratamiento.BORRADOR
    assert plan.estado.value == "borrador"


def test_transiciones_plan_permitidas_es_terminal_en_completado_y_cancelado():
    from app.models import EstadoPlanTratamiento, TRANSICIONES_PLAN_PERMITIDAS

    assert TRANSICIONES_PLAN_PERMITIDAS[EstadoPlanTratamiento.COMPLETADO] == set()
    assert TRANSICIONES_PLAN_PERMITIDAS[EstadoPlanTratamiento.CANCELADO] == set()
    # 'en_progreso' NO puede cancelarse de un tiro (decision del spec, seccion 2).
    assert (
        EstadoPlanTratamiento.CANCELADO
        not in TRANSICIONES_PLAN_PERMITIDAS[EstadoPlanTratamiento.EN_PROGRESO]
    )


def test_estados_plan_activos_no_incluye_terminales():
    from app.models import ESTADOS_PLAN_ACTIVOS, EstadoPlanTratamiento

    assert EstadoPlanTratamiento.COMPLETADO not in ESTADOS_PLAN_ACTIVOS
    assert EstadoPlanTratamiento.CANCELADO not in ESTADOS_PLAN_ACTIVOS
    assert EstadoPlanTratamiento.BORRADOR in ESTADOS_PLAN_ACTIVOS
    assert EstadoPlanTratamiento.APROBADO in ESTADOS_PLAN_ACTIVOS
    assert EstadoPlanTratamiento.EN_PROGRESO in ESTADOS_PLAN_ACTIVOS


def test_detalle_defaults_y_precio_congelado(db_session):
    from app.models import EstadoDetallePlanTratamiento, PlanTratamientoDetalle

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica, precio="25.00")
    plan = crear_plan(db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor)

    detalle = PlanTratamientoDetalle(
        id_plan=plan.id_plan,
        id_tratamiento=tratamiento.id_tratamiento,
        precio_unitario=tratamiento.precio,
    )
    db_session.add(detalle)
    db_session.flush()
    db_session.refresh(detalle)

    assert detalle.cantidad == 1
    assert detalle.orden == 0
    assert detalle.estado == EstadoDetallePlanTratamiento.PENDIENTE
    assert str(detalle.precio_unitario) == "25.00"

    # Subir el precio del catalogo despues no debe mover el detalle ya creado.
    tratamiento.precio = "40.00"
    db_session.flush()
    db_session.refresh(detalle)
    assert str(detalle.precio_unitario) == "25.00"


def test_transiciones_detalle_cancelado_alcanzable_desde_pendiente_y_en_progreso():
    from app.models import EstadoDetallePlanTratamiento, TRANSICIONES_DETALLE_PERMITIDAS

    assert (
        EstadoDetallePlanTratamiento.CANCELADO
        in TRANSICIONES_DETALLE_PERMITIDAS[EstadoDetallePlanTratamiento.PENDIENTE]
    )
    assert (
        EstadoDetallePlanTratamiento.CANCELADO
        in TRANSICIONES_DETALLE_PERMITIDAS[EstadoDetallePlanTratamiento.EN_PROGRESO]
    )
    assert TRANSICIONES_DETALLE_PERMITIDAS[EstadoDetallePlanTratamiento.COMPLETADO] == set()
