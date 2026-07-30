def test_obtener_por_username_encuentra_el_usuario(db_session):
    from app.models import RolUsuario, Usuario
    from app.repositories.usuario_repository import UsuarioRepository

    usuario = Usuario(
        id_clinica=None,
        username="superadmin",
        password_hash="hash",
        rol=RolUsuario.SUPERADMIN,
    )
    db_session.add(usuario)
    db_session.commit()

    repo = UsuarioRepository(db_session)
    encontrado = repo.obtener_por_username("superadmin")

    assert encontrado is not None
    assert encontrado.id_usuario == usuario.id_usuario


def test_obtener_por_username_devuelve_none_si_no_existe(db_session):
    from app.repositories.usuario_repository import UsuarioRepository

    repo = UsuarioRepository(db_session)

    assert repo.obtener_por_username("no-existe") is None


def test_obtener_por_id_encuentra_el_usuario(db_session):
    from app.models import RolUsuario, Usuario
    from app.repositories.usuario_repository import UsuarioRepository

    usuario = Usuario(
        id_clinica=None,
        username="superadmin",
        password_hash="hash",
        rol=RolUsuario.SUPERADMIN,
    )
    db_session.add(usuario)
    db_session.commit()

    repo = UsuarioRepository(db_session)
    encontrado = repo.obtener_por_id(usuario.id_usuario)

    assert encontrado is not None
    assert encontrado.username == "superadmin"
