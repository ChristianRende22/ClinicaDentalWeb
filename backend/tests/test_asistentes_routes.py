import pytest

from tests.factories import auth, crear_clinica, crear_usuario, token_de


def _clinica(db_session, nombre="Dental A"):
    clinica = crear_clinica(db_session, nombre)
    db_session.commit()
    return clinica


def _token(db_session, rol_nombre, id_clinica=None, username=None):
    from app.models import RolUsuario

    rol = getattr(RolUsuario, rol_nombre)
    usuario = crear_usuario(
        db_session, rol, id_clinica, username or f"user.{rol_nombre.lower()}"
    )
    db_session.commit()
    return token_de(usuario)


_NUEVO = {
    "username": "recepcion",
    "nombre": "Rosa",
    "apellido": "Diaz",
    "telefono": "70005566",
}


def test_crear_asistente_devuelve_201_y_la_password_temporal(client, db_session):
    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")

    respuesta = client.post("/asistentes", headers=auth(token), json=_NUEVO)

    assert respuesta.status_code == 201
    assert respuesta.json()["asistente"]["nombre"] == "Rosa"
    assert len(respuesta.json()["password_temporal"]) >= 12


def test_username_repetido_devuelve_409(client, db_session):
    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    client.post("/asistentes", headers=auth(token), json=_NUEVO)

    assert client.post(
        "/asistentes", headers=auth(token), json=_NUEVO
    ).status_code == 409


def test_un_null_explicito_en_un_campo_obligatorio_da_422_no_500(client, db_session):
    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    creado = client.post("/asistentes", headers=auth(token), json=_NUEVO).json()

    respuesta = client.put(
        f"/asistentes/{creado['asistente']['id_asistente']}",
        headers=auth(token),
        json={"nombre": None},
    )

    assert respuesta.status_code == 422


@pytest.mark.parametrize("rol_nombre", ["DOCTOR", "ASISTENTE"])
def test_doctor_y_asistente_leen_pero_no_dan_de_alta(client, db_session, rol_nombre):
    clinica = _clinica(db_session)
    token = _token(db_session, rol_nombre, clinica.id_clinica)

    assert client.get("/asistentes", headers=auth(token)).status_code == 200
    assert client.post(
        "/asistentes", headers=auth(token), json=_NUEVO
    ).status_code == 403


def test_reactivar_por_put_tambien_reactiva_el_usuario(client, db_session):
    from app.repositories.usuario_repository import UsuarioRepository

    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    creado = client.post("/asistentes", headers=auth(token), json=_NUEVO).json()
    id_asistente = creado["asistente"]["id_asistente"]
    client.delete(f"/asistentes/{id_asistente}", headers=auth(token))

    respuesta = client.put(
        f"/asistentes/{id_asistente}", headers=auth(token), json={"activo": True}
    )

    assert respuesta.status_code == 200
    assert UsuarioRepository(db_session).obtener_por_username("recepcion").activo is True


def test_la_baja_desactiva_tambien_el_usuario(client, db_session):
    from app.repositories.usuario_repository import UsuarioRepository

    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    creado = client.post("/asistentes", headers=auth(token), json=_NUEVO).json()

    baja = client.delete(
        f"/asistentes/{creado['asistente']['id_asistente']}", headers=auth(token)
    )

    assert baja.status_code == 204
    assert UsuarioRepository(db_session).obtener_por_username("recepcion").activo is False


def test_no_se_puede_ver_un_asistente_de_otra_clinica(client, db_session):
    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    token_b = _token(db_session, "ADMIN", clinica_b.id_clinica, "admin.b")
    creado = client.post("/asistentes", headers=auth(token_b), json=_NUEVO).json()
    token_a = _token(db_session, "ADMIN", clinica_a.id_clinica, "admin.a")

    assert client.get(
        f"/asistentes/{creado['asistente']['id_asistente']}", headers=auth(token_a)
    ).status_code == 404
