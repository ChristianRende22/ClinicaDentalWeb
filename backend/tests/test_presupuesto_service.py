from tests.factories import crear_clinica, crear_doctor, crear_paciente
from tests.test_expediente_models import crear_tratamiento
from tests.test_plan_tratamiento_models import crear_plan


def _service(db):
    from app.services.presupuesto_service import PresupuestoService

    return PresupuestoService(db)


def _detalle_repo(db):
    from app.repositories.plan_tratamiento_repository import PlanTratamientoDetalleRepository

    return PlanTratamientoDetalleRepository(db)


def test_generar_sobre_plan_sin_detalles_da_cero(db_session):
    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    plan = crear_plan(db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor)

    presupuesto = _service(db_session).generar_o_regenerar(clinica.id_clinica, plan.id_plan)
    assert str(presupuesto.monto_total) == "0.00"


def test_generar_suma_detalles_no_cancelados(db_session):
    from app.models import EstadoDetallePlanTratamiento

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica, precio="25.00")
    plan = crear_plan(db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor)
    _detalle_repo(db_session).crear(
        plan.id_plan,
        {"id_tratamiento": tratamiento.id_tratamiento, "precio_unitario": "25.00", "cantidad": 2},
    )
    _detalle_repo(db_session).crear(
        plan.id_plan,
        {
            "id_tratamiento": tratamiento.id_tratamiento,
            "precio_unitario": "100.00",
            "estado": EstadoDetallePlanTratamiento.CANCELADO,
        },
    )

    presupuesto = _service(db_session).generar_o_regenerar(clinica.id_clinica, plan.id_plan)
    assert str(presupuesto.monto_total) == "50.00"


def test_regenerar_actualiza_el_mismo_presupuesto_no_crea_otro(db_session):
    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica, precio="25.00")
    plan = crear_plan(db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor)
    detalle = _detalle_repo(db_session).crear(
        plan.id_plan, {"id_tratamiento": tratamiento.id_tratamiento, "precio_unitario": "25.00"}
    )

    servicio = _service(db_session)
    primero = servicio.generar_o_regenerar(clinica.id_clinica, plan.id_plan)

    detalle.cantidad = 3
    db_session.flush()
    segundo = servicio.generar_o_regenerar(clinica.id_clinica, plan.id_plan)

    assert segundo.id_presupuesto == primero.id_presupuesto
    assert str(segundo.monto_total) == "75.00"


def test_cambiar_estado_respeta_transiciones(db_session):
    from app.exceptions import TransicionInvalidaError
    from app.models import EstadoPresupuesto

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    plan = crear_plan(db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor)

    servicio = _service(db_session)
    presupuesto = servicio.generar_o_regenerar(clinica.id_clinica, plan.id_plan)
    presupuesto = servicio.cambiar_estado(
        clinica.id_clinica, presupuesto.id_presupuesto, EstadoPresupuesto.ACEPTADO
    )
    assert presupuesto.estado == EstadoPresupuesto.ACEPTADO

    try:
        servicio.cambiar_estado(
            clinica.id_clinica, presupuesto.id_presupuesto, EstadoPresupuesto.RECHAZADO
        )
        assert False, "debia lanzar TransicionInvalidaError"
    except TransicionInvalidaError:
        pass
