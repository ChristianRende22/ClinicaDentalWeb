from datetime import timedelta

import pytest


def _clinica(db_session, nombre="Dental A"):
    from app.models import Clinica

    clinica = Clinica(nombre=nombre)
    db_session.add(clinica)
    db_session.commit()
    return clinica


def _token_para(db_session, rol, id_clinica=None, username="user.test"):
    from app.models import Usuario
    from app.security.jwt import create_access_token
    from app.security.passwords import hash_password

    usuario = Usuario(
        id_clinica=id_clinica,
        username=username,
        password_hash=hash_password("clave123"),
        rol=rol,
    )
    db_session.add(usuario)
    db_session.commit()

    return create_access_token(
        data={"sub": str(usuario.id_usuario), "id_clinica": id_clinica, "rol": rol.value},
        expires_delta=timedelta(minutes=10),
    )


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_ciclo_completo_de_consultorios(client, db_session):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")

    creado = client.post("/consultorios", headers=_auth(token), json={"nombre": "Consultorio 1"})
    assert creado.status_code == 201
    id_consultorio = creado.json()["id_consultorio"]

    assert client.get(
        f"/consultorios/{id_consultorio}", headers=_auth(token)
    ).json()["nombre"] == "Consultorio 1"

    renombrado = client.put(
        f"/consultorios/{id_consultorio}", headers=_auth(token), json={"nombre": "Sala A"}
    )
    assert renombrado.json()["nombre"] == "Sala A"

    assert client.delete(
        f"/consultorios/{id_consultorio}", headers=_auth(token)
    ).status_code == 204
    assert client.get("/consultorios", headers=_auth(token)).json() == []


def test_consultorio_duplicado_devuelve_409(client, db_session):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")
    client.post("/consultorios", headers=_auth(token), json={"nombre": "Consultorio 1"})

    repetido = client.post(
        "/consultorios", headers=_auth(token), json={"nombre": "Consultorio 1"}
    )

    assert repetido.status_code == 409


def test_consultorios_de_otra_clinica_no_se_ven(client, db_session):
    from app.models import RolUsuario

    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    token_a = _token_para(db_session, RolUsuario.ADMIN, clinica_a.id_clinica, "admin.a")
    token_b = _token_para(db_session, RolUsuario.ADMIN, clinica_b.id_clinica, "admin.b")
    creado = client.post(
        "/consultorios", headers=_auth(token_a), json={"nombre": "Consultorio 1"}
    ).json()

    assert client.get("/consultorios", headers=_auth(token_b)).json() == []
    assert client.get(
        f"/consultorios/{creado['id_consultorio']}", headers=_auth(token_b)
    ).status_code == 404


@pytest.mark.parametrize("rol_nombre", ["DOCTOR", "ASISTENTE"])
def test_permisos_de_consultorios(client, db_session, rol_nombre):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    rol = getattr(RolUsuario, rol_nombre)
    token = _token_para(db_session, rol, clinica.id_clinica, f"user.{rol_nombre.lower()}")

    assert client.get("/consultorios", headers=_auth(token)).status_code == 200
    assert client.post(
        "/consultorios", headers=_auth(token), json={"nombre": "Consultorio 1"}
    ).status_code == 403
