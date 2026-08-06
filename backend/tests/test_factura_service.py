from decimal import Decimal

import pytest

from tests.factories import (
    crear_clinica,
    crear_doctor,
    crear_paciente,
    crear_plan_aceptado_con_presupuesto,
    crear_tratamiento,
)


def test_generar_desde_presupuesto_calcula_impuesto_y_numera(db_session):
    from app.services.factura_service import FacturaService

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica, precio="100.00")
    plan, detalle, presupuesto = crear_plan_aceptado_con_presupuesto(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor,
        tratamiento.id_tratamiento, cantidad=2,
    )
    db_session.commit()

    factura = FacturaService(db_session).generar_desde_presupuesto(clinica.id_clinica, plan.id_plan)

    assert factura.numero_factura == "F000001"
    assert Decimal(str(factura.monto_subtotal)) == Decimal("200.00")
    # ConfiguracionClinica.porcentaje_impuesto default = 13.00
    assert Decimal(str(factura.monto_impuesto)) == Decimal("26.00")
    assert Decimal(str(factura.monto_total)) == Decimal("226.00")
    assert factura.id_paciente == paciente.id_paciente
    assert factura.id_doctor == doctor.id_doctor
    assert factura.id_plan == plan.id_plan


def test_generar_desde_presupuesto_copia_las_lineas_del_plan(db_session):
    from app.repositories.factura_detalle_repository import FacturaDetalleRepository
    from app.services.factura_service import FacturaService

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica, precio="50.00")
    plan, _, _ = crear_plan_aceptado_con_presupuesto(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor,
        tratamiento.id_tratamiento, cantidad=1,
    )
    db_session.commit()

    factura = FacturaService(db_session).generar_desde_presupuesto(clinica.id_clinica, plan.id_plan)

    detalles = FacturaDetalleRepository(db_session).listar_de_factura(clinica.id_clinica, factura.id_factura)
    assert len(detalles) == 1
    assert detalles[0].id_tratamiento == tratamiento.id_tratamiento
    assert Decimal(str(detalles[0].precio_unitario)) == Decimal("50.00")


def test_generar_desde_presupuesto_incrementa_el_correlativo(db_session):
    from app.services.factura_service import FacturaService

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica, precio="10.00")
    plan_1, _, _ = crear_plan_aceptado_con_presupuesto(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor, tratamiento.id_tratamiento,
    )
    plan_2, _, _ = crear_plan_aceptado_con_presupuesto(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor, tratamiento.id_tratamiento,
    )
    db_session.commit()

    servicio = FacturaService(db_session)
    factura_1 = servicio.generar_desde_presupuesto(clinica.id_clinica, plan_1.id_plan)
    factura_2 = servicio.generar_desde_presupuesto(clinica.id_clinica, plan_2.id_plan)

    assert factura_1.numero_factura == "F000001"
    assert factura_2.numero_factura == "F000002"


def test_generar_desde_presupuesto_sin_aceptar_lanza_error(db_session):
    from app.exceptions import PresupuestoNoAceptadoError
    from app.models import EstadoPresupuesto
    from app.services.factura_service import FacturaService

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica)
    plan, _, presupuesto = crear_plan_aceptado_con_presupuesto(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor, tratamiento.id_tratamiento,
    )
    presupuesto.estado = EstadoPresupuesto.VIGENTE
    db_session.commit()

    with pytest.raises(PresupuestoNoAceptadoError):
        FacturaService(db_session).generar_desde_presupuesto(clinica.id_clinica, plan.id_plan)


def test_generar_desde_presupuesto_plan_inexistente_devuelve_none(db_session):
    from app.services.factura_service import FacturaService

    clinica = crear_clinica(db_session)

    assert FacturaService(db_session).generar_desde_presupuesto(clinica.id_clinica, 999) is None


def test_crear_suelta_calcula_desde_el_catalogo(db_session):
    from app.services.factura_service import FacturaService

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica, precio="40.00")
    db_session.commit()

    factura = FacturaService(db_session).crear_suelta(
        clinica.id_clinica, paciente.id_paciente, None,
        [{"id_tratamiento": tratamiento.id_tratamiento, "cantidad": 3}],
    )

    assert Decimal(str(factura.monto_subtotal)) == Decimal("120.00")
    assert factura.id_plan is None
    assert factura.numero_factura == "F000001"


def test_crear_suelta_con_tratamiento_de_otra_clinica_lanza_error(db_session):
    from app.exceptions import ReferenciaInvalidaError
    from app.models import Clinica
    from app.services.factura_service import FacturaService

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    otra_clinica = Clinica(nombre="Dental Dos")
    db_session.add(otra_clinica)
    db_session.flush()
    tratamiento_ajeno = crear_tratamiento(db_session, otra_clinica.id_clinica)
    db_session.commit()

    with pytest.raises(ReferenciaInvalidaError):
        FacturaService(db_session).crear_suelta(
            clinica.id_clinica, paciente.id_paciente, None,
            [{"id_tratamiento": tratamiento_ajeno.id_tratamiento, "cantidad": 1}],
        )


def test_anular_sin_pagos(db_session):
    from app.models import EstadoFactura
    from app.services.factura_service import FacturaService

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica)
    db_session.commit()

    servicio = FacturaService(db_session)
    factura = servicio.crear_suelta(
        clinica.id_clinica, paciente.id_paciente, None,
        [{"id_tratamiento": tratamiento.id_tratamiento, "cantidad": 1}],
    )

    anulada = servicio.anular(clinica.id_clinica, factura.id_factura)

    assert anulada.estado == EstadoFactura.ANULADA


def test_anular_con_pagos_lanza_error(db_session):
    from app.exceptions import FacturaConPagosError
    from app.repositories.pago_repository import PagoRepository
    from app.services.factura_service import FacturaService
    from tests.factories import crear_metodo_pago

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica)
    metodo = crear_metodo_pago(db_session, clinica.id_clinica)
    db_session.commit()

    servicio = FacturaService(db_session)
    factura = servicio.crear_suelta(
        clinica.id_clinica, paciente.id_paciente, None,
        [{"id_tratamiento": tratamiento.id_tratamiento, "cantidad": 1}],
    )
    PagoRepository(db_session).crear(
        factura.id_factura, {"id_metodo_pago": metodo.id_metodo_pago, "monto": "10.00"}
    )
    db_session.commit()

    with pytest.raises(FacturaConPagosError):
        servicio.anular(clinica.id_clinica, factura.id_factura)


def test_anular_factura_inexistente_devuelve_none(db_session):
    from app.services.factura_service import FacturaService

    clinica = crear_clinica(db_session)

    assert FacturaService(db_session).anular(clinica.id_clinica, 999) is None
