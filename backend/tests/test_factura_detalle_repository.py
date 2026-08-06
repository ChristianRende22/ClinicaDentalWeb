from tests.factories import crear_clinica, crear_paciente, crear_tratamiento


def _crear_factura(db, id_clinica, id_paciente):
    from app.repositories.factura_repository import FacturaRepository

    return FacturaRepository(db).crear(
        id_clinica,
        {
            "id_paciente": id_paciente,
            "numero_factura": "F000001",
            "monto_subtotal": "25.00",
            "monto_impuesto": "3.25",
            "monto_total": "28.25",
        },
    )


def test_crear_y_listar_de_factura(db_session):
    from app.repositories.factura_detalle_repository import FacturaDetalleRepository

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica)
    factura = _crear_factura(db_session, clinica.id_clinica, paciente.id_paciente)

    repo = FacturaDetalleRepository(db_session)
    repo.crear(
        factura.id_factura,
        {"id_tratamiento": tratamiento.id_tratamiento, "cantidad": 2, "precio_unitario": "25.00"},
    )
    db_session.commit()

    detalles = repo.listar_de_factura(clinica.id_clinica, factura.id_factura)

    assert len(detalles) == 1
    assert detalles[0].cantidad == 2


def test_listar_de_factura_de_otra_clinica_devuelve_vacio(db_session):
    from app.models import Clinica
    from app.repositories.factura_detalle_repository import FacturaDetalleRepository

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica)
    factura = _crear_factura(db_session, clinica.id_clinica, paciente.id_paciente)

    repo = FacturaDetalleRepository(db_session)
    repo.crear(
        factura.id_factura,
        {"id_tratamiento": tratamiento.id_tratamiento, "cantidad": 1, "precio_unitario": "25.00"},
    )
    db_session.commit()

    otra_clinica = Clinica(nombre="Dental Dos")
    db_session.add(otra_clinica)
    db_session.commit()

    assert repo.listar_de_factura(otra_clinica.id_clinica, factura.id_factura) == []
