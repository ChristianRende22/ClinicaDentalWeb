from tests.factories import crear_clinica, crear_usuario


def _repo(db_session):
    from app.repositories.asistente_repository import AsistenteRepository

    return AsistenteRepository(db_session)


def _datos(db_session, id_clinica, username="recepcion", **campos):
    from app.models import RolUsuario

    usuario = crear_usuario(db_session, RolUsuario.ASISTENTE, id_clinica, username)
    base = {
        "id_usuario": usuario.id_usuario,
        "nombre": "Rosa",
        "apellido": "Diaz",
        "telefono": "70005566",
    }
    base.update(campos)
    return base


def test_crear_devuelve_el_asistente_activo(db_session):
    clinica = crear_clinica(db_session)

    creado = _repo(db_session).crear(
        clinica.id_clinica, _datos(db_session, clinica.id_clinica)
    )

    assert creado.id_asistente is not None
    assert creado.activo is True


def test_listar_solo_devuelve_los_de_la_clinica_pedida(db_session):
    clinica_a = crear_clinica(db_session, "Dental A")
    clinica_b = crear_clinica(db_session, "Dental B")
    repo = _repo(db_session)
    repo.crear(clinica_a.id_clinica, _datos(db_session, clinica_a.id_clinica, "rec.a"))
    repo.crear(clinica_b.id_clinica, _datos(db_session, clinica_b.id_clinica, "rec.b"))

    assert len(repo.listar(clinica_a.id_clinica)) == 1


def test_listar_omite_los_inactivos_por_defecto(db_session):
    clinica = crear_clinica(db_session)
    repo = _repo(db_session)
    creado = repo.crear(clinica.id_clinica, _datos(db_session, clinica.id_clinica))
    repo.eliminar(clinica.id_clinica, creado.id_asistente)

    assert repo.listar(clinica.id_clinica) == []
    assert len(repo.listar(clinica.id_clinica, incluir_inactivos=True)) == 1


def test_obtener_por_usuario_traduce_el_jwt_a_un_perfil(db_session):
    clinica = crear_clinica(db_session)
    repo = _repo(db_session)
    datos = _datos(db_session, clinica.id_clinica)
    creado = repo.crear(clinica.id_clinica, datos)

    assert repo.obtener_por_usuario(datos["id_usuario"]).id_asistente == creado.id_asistente


def test_obtener_de_otra_clinica_devuelve_none(db_session):
    clinica_a = crear_clinica(db_session, "Dental A")
    clinica_b = crear_clinica(db_session, "Dental B")
    repo = _repo(db_session)
    de_a = repo.crear(clinica_a.id_clinica, _datos(db_session, clinica_a.id_clinica))

    assert repo.obtener(clinica_b.id_clinica, de_a.id_asistente) is None
