from decimal import Decimal

import pytest

from tests.factories import crear_clinica, crear_metodo_pago, crear_paciente, crear_tratamiento


def _crear_factura_suelta(db, id_clinica, id_paciente, precio="100.00"):
    from app.services.factura_service import FacturaService

    tratamiento = crear_tratamiento(db, id_clinica, precio=precio)
    db.commit()
    return FacturaService(db).crear_suelta(
        id_clinica, id_paciente, None, [{"id_tratamiento": tratamiento.id_tratamiento, "cantidad": 1}]
    )


def test_registrar_pago_parcial_deja_la_factura_en_parcial(db_session):
    from app.models import EstadoFactura
    from app.services.pago_service import PagoService

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    metodo = crear_metodo_pago(db_session, clinica.id_clinica)
    factura = _crear_factura_suelta(db_session, clinica.id_clinica, paciente.id_paciente, precio="100.00")
    # monto_total = 113.00 (100 + 13% de impuesto)

    pago = PagoService(db_session).registrar_pago(
        clinica.id_clinica, factura.id_factura, Decimal("50.00"), metodo.id_metodo_pago
    )

    assert pago.id_pago is not None
    db_session.refresh(factura)
    assert factura.estado == EstadoFactura.PARCIAL


def test_registrar_pago_que_completa_el_saldo_deja_la_factura_pagada(db_session):
    from app.models import EstadoFactura
    from app.services.pago_service import PagoService

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    metodo = crear_metodo_pago(db_session, clinica.id_clinica)
    factura = _crear_factura_suelta(db_session, clinica.id_clinica, paciente.id_paciente, precio="100.00")

    servicio = PagoService(db_session)
    servicio.registrar_pago(clinica.id_clinica, factura.id_factura, Decimal("113.00"), metodo.id_metodo_pago)

    db_session.refresh(factura)
    assert factura.estado == EstadoFactura.PAGADA


def test_registrar_pago_que_excede_el_saldo_lanza_error(db_session):
    from app.exceptions import PagoExcedeSaldoError
    from app.services.pago_service import PagoService

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    metodo = crear_metodo_pago(db_session, clinica.id_clinica)
    factura = _crear_factura_suelta(db_session, clinica.id_clinica, paciente.id_paciente, precio="100.00")

    with pytest.raises(PagoExcedeSaldoError):
        PagoService(db_session).registrar_pago(
            clinica.id_clinica, factura.id_factura, Decimal("999.00"), metodo.id_metodo_pago
        )


def test_registrar_pago_sobre_factura_anulada_lanza_error(db_session):
    from app.exceptions import FacturaAnuladaError
    from app.services.factura_service import FacturaService
    from app.services.pago_service import PagoService

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    metodo = crear_metodo_pago(db_session, clinica.id_clinica)
    factura = _crear_factura_suelta(db_session, clinica.id_clinica, paciente.id_paciente, precio="100.00")
    FacturaService(db_session).anular(clinica.id_clinica, factura.id_factura)

    with pytest.raises(FacturaAnuladaError):
        PagoService(db_session).registrar_pago(
            clinica.id_clinica, factura.id_factura, Decimal("10.00"), metodo.id_metodo_pago
        )


def test_registrar_pago_factura_inexistente_devuelve_none(db_session):
    from app.services.pago_service import PagoService

    clinica = crear_clinica(db_session)
    metodo = crear_metodo_pago(db_session, clinica.id_clinica)
    db_session.commit()

    resultado = PagoService(db_session).registrar_pago(
        clinica.id_clinica, 999, Decimal("10.00"), metodo.id_metodo_pago
    )

    assert resultado is None
