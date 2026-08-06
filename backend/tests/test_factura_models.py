def _crear_clinica(db):
    from app.models import Clinica

    clinica = Clinica(nombre="Dental Uno")
    db.add(clinica)
    db.flush()
    return clinica


def _crear_paciente(db, id_clinica):
    from app.models import Paciente

    paciente = Paciente(id_clinica=id_clinica, nombre="Ana", apellido="Lopez", telefono="70001122")
    db.add(paciente)
    db.flush()
    return paciente


def _crear_tratamiento(db, id_clinica):
    from app.models import Tratamiento

    tratamiento = Tratamiento(id_clinica=id_clinica, nombre="Limpieza", precio="25.00")
    db.add(tratamiento)
    db.flush()
    return tratamiento


def test_crear_factura_con_detalle_y_pago(db_session):
    from app.models import EstadoFactura, Factura, FacturaDetalle, Pago

    clinica = _crear_clinica(db_session)
    paciente = _crear_paciente(db_session, clinica.id_clinica)
    tratamiento = _crear_tratamiento(db_session, clinica.id_clinica)

    factura = Factura(
        id_clinica=clinica.id_clinica,
        id_paciente=paciente.id_paciente,
        numero_factura="F000001",
        monto_subtotal="25.00",
        monto_impuesto="3.25",
        monto_total="28.25",
    )
    db_session.add(factura)
    db_session.flush()

    assert factura.id_factura is not None
    assert factura.estado == EstadoFactura.PENDIENTE

    detalle = FacturaDetalle(
        id_factura=factura.id_factura,
        id_tratamiento=tratamiento.id_tratamiento,
        cantidad=1,
        precio_unitario="25.00",
    )
    db_session.add(detalle)

    from app.models import MetodoPago

    metodo = MetodoPago(id_clinica=clinica.id_clinica, nombre="Efectivo")
    db_session.add(metodo)
    db_session.flush()

    pago = Pago(id_factura=factura.id_factura, id_metodo_pago=metodo.id_metodo_pago, monto="28.25")
    db_session.add(pago)
    db_session.commit()

    assert detalle.id_detalle is not None
    assert pago.id_pago is not None


def test_numero_factura_es_unico_por_clinica(db_session):
    from app.models import Factura
    from sqlalchemy.exc import IntegrityError
    import pytest

    clinica = _crear_clinica(db_session)
    paciente = _crear_paciente(db_session, clinica.id_clinica)

    db_session.add(
        Factura(
            id_clinica=clinica.id_clinica,
            id_paciente=paciente.id_paciente,
            numero_factura="F000001",
            monto_subtotal="10.00",
            monto_impuesto="1.30",
            monto_total="11.30",
        )
    )
    db_session.commit()

    db_session.add(
        Factura(
            id_clinica=clinica.id_clinica,
            id_paciente=paciente.id_paciente,
            numero_factura="F000001",
            monto_subtotal="20.00",
            monto_impuesto="2.60",
            monto_total="22.60",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
