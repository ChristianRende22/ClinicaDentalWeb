from tests.factories import crear_clinica, crear_doctor, crear_paciente
from tests.test_plan_tratamiento_models import crear_plan


def test_presupuesto_estado_default_vigente(db_session):
    from app.models import EstadoPresupuesto, Presupuesto

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    plan = crear_plan(db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor)

    presupuesto = Presupuesto(
        id_clinica=clinica.id_clinica, id_plan=plan.id_plan, monto_total="0.00"
    )
    db_session.add(presupuesto)
    db_session.flush()
    db_session.refresh(presupuesto)
    assert presupuesto.estado == EstadoPresupuesto.VIGENTE
    assert presupuesto.estado.value == "vigente"


def test_presupuesto_unico_por_plan(db_session):
    from sqlalchemy.exc import IntegrityError

    from app.models import Presupuesto

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    plan = crear_plan(db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor)

    db_session.add(Presupuesto(id_clinica=clinica.id_clinica, id_plan=plan.id_plan, monto_total="0.00"))
    db_session.flush()
    try:
        db_session.add(
            Presupuesto(id_clinica=clinica.id_clinica, id_plan=plan.id_plan, monto_total="0.00")
        )
        db_session.flush()
        assert False, "debia lanzar IntegrityError"
    except IntegrityError:
        db_session.rollback()


def test_transiciones_presupuesto_todos_terminales_salvo_vigente():
    from app.models import EstadoPresupuesto, TRANSICIONES_PRESUPUESTO_PERMITIDAS

    assert TRANSICIONES_PRESUPUESTO_PERMITIDAS[EstadoPresupuesto.ACEPTADO] == set()
    assert TRANSICIONES_PRESUPUESTO_PERMITIDAS[EstadoPresupuesto.RECHAZADO] == set()
    assert TRANSICIONES_PRESUPUESTO_PERMITIDAS[EstadoPresupuesto.VENCIDO] == set()
    assert EstadoPresupuesto.ACEPTADO in TRANSICIONES_PRESUPUESTO_PERMITIDAS[EstadoPresupuesto.VIGENTE]
