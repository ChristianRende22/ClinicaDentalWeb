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


def test_listar_sin_token_devuelve_401(client):
    assert client.get("/especialidades").status_code == 401


def test_crear_y_listar_como_admin(client, db_session):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")

    creacion = client.post(
        "/especialidades", headers=_auth(token), json={"nombre": "Ortodoncia"}
    )
    assert creacion.status_code == 201
    assert creacion.json()["nombre"] == "Ortodoncia"
    assert creacion.json()["activo"] is True

    listado = client.get("/especialidades", headers=_auth(token))
    assert listado.status_code == 200
    assert [e["nombre"] for e in listado.json()] == ["Ortodoncia"]


def test_crear_nombre_duplicado_devuelve_409(client, db_session):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")
    client.post("/especialidades", headers=_auth(token), json={"nombre": "Ortodoncia"})

    repetida = client.post(
        "/especialidades", headers=_auth(token), json={"nombre": "ortodoncia"}
    )

    assert repetida.status_code == 409


def test_crear_con_nombre_vacio_devuelve_422(client, db_session):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")

    assert client.post(
        "/especialidades", headers=_auth(token), json={"nombre": "   "}
    ).status_code == 422


@pytest.mark.parametrize("rol_nombre", ["DOCTOR", "ASISTENTE"])
def test_doctor_y_asistente_pueden_leer(client, db_session, rol_nombre):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    token_admin = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")
    client.post("/especialidades", headers=_auth(token_admin), json={"nombre": "Ortodoncia"})

    rol = getattr(RolUsuario, rol_nombre)
    token = _token_para(db_session, rol, clinica.id_clinica, f"user.{rol_nombre.lower()}")

    respuesta = client.get("/especialidades", headers=_auth(token))

    assert respuesta.status_code == 200
    assert [e["nombre"] for e in respuesta.json()] == ["Ortodoncia"]


@pytest.mark.parametrize("rol_nombre", ["DOCTOR", "ASISTENTE"])
def test_doctor_y_asistente_no_pueden_escribir(client, db_session, rol_nombre):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    rol = getattr(RolUsuario, rol_nombre)
    token = _token_para(db_session, rol, clinica.id_clinica, f"user.{rol_nombre.lower()}")

    assert client.post(
        "/especialidades", headers=_auth(token), json={"nombre": "Ortodoncia"}
    ).status_code == 403


def test_superadmin_sin_header_de_clinica_devuelve_400(client, db_session):
    from app.models import RolUsuario

    token = _token_para(db_session, RolUsuario.SUPERADMIN, None, "superadmin")

    assert client.get("/especialidades", headers=_auth(token)).status_code == 400


def test_superadmin_con_header_opera_sobre_esa_clinica(client, db_session):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.SUPERADMIN, None, "superadmin")
    cabeceras = {**_auth(token), "X-Clinica-Id": str(clinica.id_clinica)}

    creacion = client.post("/especialidades", headers=cabeceras, json={"nombre": "Ortodoncia"})

    assert creacion.status_code == 201
    assert client.get("/especialidades", headers=cabeceras).json()[0]["nombre"] == "Ortodoncia"


def test_un_admin_no_ve_las_especialidades_de_otra_clinica(client, db_session):
    from app.models import RolUsuario

    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    token_a = _token_para(db_session, RolUsuario.ADMIN, clinica_a.id_clinica, "admin.a")
    token_b = _token_para(db_session, RolUsuario.ADMIN, clinica_b.id_clinica, "admin.b")

    creada = client.post(
        "/especialidades", headers=_auth(token_a), json={"nombre": "Ortodoncia"}
    ).json()

    assert client.get("/especialidades", headers=_auth(token_b)).json() == []
    assert client.get(
        f"/especialidades/{creada['id_especialidad']}", headers=_auth(token_b)
    ).status_code == 404


def test_un_admin_no_puede_editar_ni_borrar_lo_de_otra_clinica(client, db_session):
    from app.models import RolUsuario

    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    token_a = _token_para(db_session, RolUsuario.ADMIN, clinica_a.id_clinica, "admin.a")
    token_b = _token_para(db_session, RolUsuario.ADMIN, clinica_b.id_clinica, "admin.b")
    creada = client.post(
        "/especialidades", headers=_auth(token_a), json={"nombre": "Ortodoncia"}
    ).json()
    id_ajeno = creada["id_especialidad"]

    assert client.put(
        f"/especialidades/{id_ajeno}", headers=_auth(token_b), json={"nombre": "Hackeada"}
    ).status_code == 404
    assert client.delete(
        f"/especialidades/{id_ajeno}", headers=_auth(token_b)
    ).status_code == 404

    sigue_igual = client.get(f"/especialidades/{id_ajeno}", headers=_auth(token_a)).json()
    assert sigue_igual["nombre"] == "Ortodoncia"
    assert sigue_igual["activo"] is True


def test_el_header_de_clinica_se_ignora_para_roles_no_superadmin(client, db_session):
    from app.models import RolUsuario

    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    token_a = _token_para(db_session, RolUsuario.ADMIN, clinica_a.id_clinica, "admin.a")

    client.post(
        "/especialidades",
        headers={**_auth(token_a), "X-Clinica-Id": str(clinica_b.id_clinica)},
        json={"nombre": "Ortodoncia"},
    )

    token_b = _token_para(db_session, RolUsuario.ADMIN, clinica_b.id_clinica, "admin.b")
    assert client.get("/especialidades", headers=_auth(token_b)).json() == []


def test_actualizar_devuelve_200_y_404_si_no_existe(client, db_session):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")
    creada = client.post(
        "/especialidades", headers=_auth(token), json={"nombre": "Ortodoncia"}
    ).json()

    actualizada = client.put(
        f"/especialidades/{creada['id_especialidad']}",
        headers=_auth(token),
        json={"nombre": "Ortodoncia avanzada"},
    )

    assert actualizada.status_code == 200
    assert actualizada.json()["nombre"] == "Ortodoncia avanzada"
    assert client.put(
        "/especialidades/9999", headers=_auth(token), json={"nombre": "X"}
    ).status_code == 404


def test_eliminar_desactiva_y_desaparece_del_listado(client, db_session):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")
    creada = client.post(
        "/especialidades", headers=_auth(token), json={"nombre": "Ortodoncia"}
    ).json()

    borrado = client.delete(
        f"/especialidades/{creada['id_especialidad']}", headers=_auth(token)
    )

    assert borrado.status_code == 204
    assert client.get("/especialidades", headers=_auth(token)).json() == []

    con_inactivos = client.get(
        "/especialidades?incluir_inactivos=true", headers=_auth(token)
    ).json()
    assert con_inactivos[0]["activo"] is False
    assert client.delete("/especialidades/9999", headers=_auth(token)).status_code == 404
