def _clinica_y_paciente(db):
    from app.models import Clinica, Paciente

    clinica = Clinica(nombre="Dental Uno")
    db.add(clinica)
    db.flush()
    paciente = Paciente(id_clinica=clinica.id_clinica, nombre="Ana", apellido="Lopez", telefono="70001122")
    db.add(paciente)
    db.flush()
    return clinica, paciente


def test_crear_y_obtener(db_session):
    from app.repositories.factura_repository import FacturaRepository

    clinica, paciente = _clinica_y_paciente(db_session)
    repo = FacturaRepository(db_session)
    factura = repo.crear(
        clinica.id_clinica,
        {
            "id_paciente": paciente.id_paciente,
            "numero_factura": "F000001",
            "monto_subtotal": "25.00",
            "monto_impuesto": "3.25",
            "monto_total": "28.25",
        },
    )
    db_session.commit()

    encontrada = repo.obtener(clinica.id_clinica, factura.id_factura)

    assert encontrada is not None
    assert encontrada.numero_factura == "F000001"


def test_obtener_de_otra_clinica_devuelve_none(db_session):
    from app.repositories.factura_repository import FacturaRepository
    from app.models import Clinica

    clinica, paciente = _clinica_y_paciente(db_session)
    otra_clinica = Clinica(nombre="Dental Dos")
    db_session.add(otra_clinica)
    db_session.flush()

    repo = FacturaRepository(db_session)
    factura = repo.crear(
        clinica.id_clinica,
        {
            "id_paciente": paciente.id_paciente,
            "numero_factura": "F000001",
            "monto_subtotal": "25.00",
            "monto_impuesto": "3.25",
            "monto_total": "28.25",
        },
    )
    db_session.commit()

    assert repo.obtener(otra_clinica.id_clinica, factura.id_factura) is None


def test_listar_filtra_por_paciente_y_doctor(db_session):
    from app.models import Doctor, RolUsuario, Usuario
    from app.repositories.factura_repository import FacturaRepository

    clinica, paciente = _clinica_y_paciente(db_session)
    usuario = Usuario(id_clinica=clinica.id_clinica, username="dra.perez", password_hash="x", rol=RolUsuario.DOCTOR)
    db_session.add(usuario)
    db_session.flush()
    doctor = Doctor(id_clinica=clinica.id_clinica, id_usuario=usuario.id_usuario, nombre="Marta", apellido="Perez", telefono="70003344")
    db_session.add(doctor)
    db_session.flush()

    repo = FacturaRepository(db_session)
    repo.crear(
        clinica.id_clinica,
        {
            "id_paciente": paciente.id_paciente,
            "id_doctor": doctor.id_doctor,
            "numero_factura": "F000001",
            "monto_subtotal": "25.00",
            "monto_impuesto": "3.25",
            "monto_total": "28.25",
        },
    )
    repo.crear(
        clinica.id_clinica,
        {
            "id_paciente": paciente.id_paciente,
            "numero_factura": "F000002",
            "monto_subtotal": "10.00",
            "monto_impuesto": "1.30",
            "monto_total": "11.30",
        },
    )
    db_session.commit()

    solo_del_doctor = repo.listar(clinica.id_clinica, id_doctor=doctor.id_doctor)

    assert len(solo_del_doctor) == 1
    assert solo_del_doctor[0].numero_factura == "F000001"


def test_eliminar_lanza_not_implemented(db_session):
    import pytest
    from app.repositories.factura_repository import FacturaRepository

    with pytest.raises(NotImplementedError):
        FacturaRepository(db_session).eliminar(1, 1)
