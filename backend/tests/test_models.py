def test_crear_clinica_usuario_y_modulo(db_session):
    from app.models import Clinica, ClinicaModulo, EstadoClinica, RolUsuario, Usuario

    clinica = Clinica(nombre="Dental Smiling", correo="contacto@dentalsmiling.com")
    db_session.add(clinica)
    db_session.flush()

    assert clinica.id_clinica is not None
    assert clinica.estado == EstadoClinica.ACTIVA

    modulo = ClinicaModulo(id_clinica=clinica.id_clinica, modulo="recetas", habilitado=False)
    db_session.add(modulo)

    usuario = Usuario(
        id_clinica=clinica.id_clinica,
        username="admin.dentalsmiling",
        password_hash="hash-de-prueba",
        rol=RolUsuario.ADMIN,
    )
    db_session.add(usuario)
    db_session.commit()

    assert usuario.activo is True
    assert usuario.clinica.nombre == "Dental Smiling"
    assert clinica.modulos[0].modulo == "recetas"
    assert clinica.modulos[0].habilitado is False


def test_usuario_superadmin_sin_clinica(db_session):
    from app.models import RolUsuario, Usuario

    superadmin = Usuario(
        id_clinica=None,
        username="superadmin",
        password_hash="hash-de-prueba",
        rol=RolUsuario.SUPERADMIN,
    )
    db_session.add(superadmin)
    db_session.commit()

    assert superadmin.id_clinica is None
    assert superadmin.clinica is None


def test_usuario_debe_cambiar_password_por_defecto(db_session):
    from app.models import RolUsuario, Usuario

    usuario = Usuario(
        id_clinica=None,
        username="nuevo.usuario",
        password_hash="hash",
        rol=RolUsuario.ADMIN,
    )
    db_session.add(usuario)
    db_session.commit()

    assert usuario.debe_cambiar_password is True
