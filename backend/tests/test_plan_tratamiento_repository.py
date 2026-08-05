from tests.factories import crear_clinica, crear_doctor, crear_paciente
from tests.test_expediente_models import crear_tratamiento
from tests.test_plan_tratamiento_models import crear_plan


def _repo(db):
    from app.repositories.plan_tratamiento_repository import PlanTratamientoRepository

    return PlanTratamientoRepository(db)


def _detalle_repo(db):
    from app.repositories.plan_tratamiento_repository import (
        PlanTratamientoDetalleRepository,
    )

    return PlanTratamientoDetalleRepository(db)


def test_crear_y_obtener(db_session):
    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)

    plan = _repo(db_session).crear(
        clinica.id_clinica, {"id_paciente": paciente.id_paciente, "id_doctor": doctor.id_doctor}
    )
    assert _repo(db_session).obtener(clinica.id_clinica, plan.id_plan) is not None


def test_aislamiento_entre_clinicas(db_session):
    clinica_a = crear_clinica(db_session, nombre="A")
    clinica_b = crear_clinica(db_session, nombre="B")
    paciente = crear_paciente(db_session, clinica_a.id_clinica)
    doctor = crear_doctor(db_session, clinica_a.id_clinica)
    plan = crear_plan(db_session, clinica_a.id_clinica, paciente.id_paciente, doctor.id_doctor)

    assert _repo(db_session).obtener(clinica_b.id_clinica, plan.id_plan) is None
    assert _repo(db_session).listar(clinica_b.id_clinica) == []


def test_eliminar_no_esta_implementado(db_session):
    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    plan = crear_plan(db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor)

    try:
        _repo(db_session).eliminar(clinica.id_clinica, plan.id_plan)
        assert False, "debia lanzar NotImplementedError"
    except NotImplementedError:
        pass


def test_existe_plan_activo_de_paciente_true_con_borrador_aprobado_o_en_progreso(db_session):
    from app.models import EstadoPlanTratamiento

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)

    for estado in (
        EstadoPlanTratamiento.BORRADOR,
        EstadoPlanTratamiento.APROBADO,
        EstadoPlanTratamiento.EN_PROGRESO,
    ):
        otro_paciente = crear_paciente(db_session, clinica.id_clinica, telefono="70009999")
        crear_plan(
            db_session, clinica.id_clinica, otro_paciente.id_paciente, doctor.id_doctor,
            estado=estado,
        )
        assert _repo(db_session).existe_plan_activo_de_paciente(
            clinica.id_clinica, otro_paciente.id_paciente
        ) is True

    # El paciente original, sin ningun plan, no da falso positivo.
    assert (
        _repo(db_session).existe_plan_activo_de_paciente(clinica.id_clinica, paciente.id_paciente)
        is False
    )


def test_existe_plan_activo_de_paciente_false_con_completado_o_cancelado(db_session):
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

    assert (
        _repo(db_session).existe_plan_activo_de_paciente(clinica.id_clinica, paciente.id_paciente)
        is False
    )


def test_existe_plan_activo_de_doctor(db_session):
    from app.models import EstadoPlanTratamiento

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    crear_plan(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor,
        estado=EstadoPlanTratamiento.EN_PROGRESO,
    )

    assert _repo(db_session).existe_plan_activo_de_doctor(clinica.id_clinica, doctor.id_doctor) is True

    otro_doctor = crear_doctor(db_session, clinica.id_clinica, username="dr.otro")
    assert (
        _repo(db_session).existe_plan_activo_de_doctor(clinica.id_clinica, otro_doctor.id_doctor)
        is False
    )


def test_detalle_listar_de_plan_ordena_por_orden(db_session):
    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica)
    plan = crear_plan(db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor)

    _detalle_repo(db_session).crear(
        plan.id_plan,
        {"id_tratamiento": tratamiento.id_tratamiento, "precio_unitario": "10.00", "orden": 2},
    )
    _detalle_repo(db_session).crear(
        plan.id_plan,
        {"id_tratamiento": tratamiento.id_tratamiento, "precio_unitario": "10.00", "orden": 1},
    )

    detalles = _detalle_repo(db_session).listar_de_plan(clinica.id_clinica, plan.id_plan)
    assert [d.orden for d in detalles] == [1, 2]


def test_detalle_aislamiento_entre_clinicas(db_session):
    clinica_a = crear_clinica(db_session, nombre="A")
    clinica_b = crear_clinica(db_session, nombre="B")
    paciente = crear_paciente(db_session, clinica_a.id_clinica)
    doctor = crear_doctor(db_session, clinica_a.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica_a.id_clinica)
    plan = crear_plan(db_session, clinica_a.id_clinica, paciente.id_paciente, doctor.id_doctor)
    detalle = _detalle_repo(db_session).crear(
        plan.id_plan, {"id_tratamiento": tratamiento.id_tratamiento, "precio_unitario": "10.00"}
    )

    assert (
        _detalle_repo(db_session).obtener(clinica_b.id_clinica, plan.id_plan, detalle.id_detalle)
        is None
    )
