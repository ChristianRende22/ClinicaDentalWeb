from decimal import Decimal

from tests.factories import crear_clinica, crear_metodo_pago, crear_paciente


def _crear_factura(db, id_clinica, id_paciente, monto_total="28.25"):
    from app.repositories.factura_repository import FacturaRepository

    return FacturaRepository(db).crear(
        id_clinica,
        {
            "id_paciente": id_paciente,
            "numero_factura": "F000001",
            "monto_subtotal": "25.00",
            "monto_impuesto": "3.25",
            "monto_total": monto_total,
        },
    )


def test_crear_y_listar_pagos(db_session):
    from app.repositories.pago_repository import PagoRepository

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    metodo = crear_metodo_pago(db_session, clinica.id_clinica)
    factura = _crear_factura(db_session, clinica.id_clinica, paciente.id_paciente)

    repo = PagoRepository(db_session)
    repo.crear(factura.id_factura, {"id_metodo_pago": metodo.id_metodo_pago, "monto": "10.00"})
    repo.crear(factura.id_factura, {"id_metodo_pago": metodo.id_metodo_pago, "monto": "18.25"})
    db_session.commit()

    pagos = repo.listar_de_factura(clinica.id_clinica, factura.id_factura)

    assert len(pagos) == 2


def test_suma_pagada(db_session):
    from app.repositories.pago_repository import PagoRepository

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    metodo = crear_metodo_pago(db_session, clinica.id_clinica)
    factura = _crear_factura(db_session, clinica.id_clinica, paciente.id_paciente)

    repo = PagoRepository(db_session)
    repo.crear(factura.id_factura, {"id_metodo_pago": metodo.id_metodo_pago, "monto": "10.00"})
    repo.crear(factura.id_factura, {"id_metodo_pago": metodo.id_metodo_pago, "monto": "18.25"})
    db_session.commit()

    assert repo.suma_pagada(clinica.id_clinica, factura.id_factura) == Decimal("28.25")


def test_suma_pagada_sin_pagos_es_cero(db_session):
    from app.repositories.pago_repository import PagoRepository

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    factura = _crear_factura(db_session, clinica.id_clinica, paciente.id_paciente)
    db_session.commit()

    assert PagoRepository(db_session).suma_pagada(clinica.id_clinica, factura.id_factura) == Decimal("0.00")
