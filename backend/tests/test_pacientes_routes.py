import pytest

from tests.factories import auth, crear_clinica, crear_usuario, token_de


def _token(db_session, rol_nombre, id_clinica=None, username=None):
    from app.models import RolUsuario

    rol = getattr(RolUsuario, rol_nombre)
    usuario = crear_usuario(
        db_session, rol, id_clinica, username or f"user.{rol_nombre.lower()}"
    )
    db_session.commit()
    return token_de(usuario)


def _clinica(db_session, nombre="Dental A"):
    clinica = crear_clinica(db_session, nombre)
    db_session.commit()
    return clinica


_NUEVO = {"nombre": "Ana", "apellido": "Lopez", "telefono": "70001122"}


def test_listar_sin_token_devuelve_401(client):
    assert client.get("/pacientes").status_code == 401


def test_crear_y_listar_como_admin(client, db_session):
    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")

    creacion = client.post("/pacientes", headers=auth(token), json=_NUEVO)
    assert creacion.status_code == 201
    assert creacion.json()["nombre"] == "Ana"
    assert creacion.json()["activo"] is True

    listado = client.get("/pacientes", headers=auth(token))
    assert listado.status_code == 200
    assert [p["apellido"] for p in listado.json()] == ["Lopez"]


def test_la_respuesta_incluye_la_edad_calculada(client, db_session):
    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")

    creacion = client.post(
        "/pacientes",
        headers=auth(token),
        json={**_NUEVO, "fecha_nacimiento": "2000-01-01"},
    )

    assert creacion.json()["edad"] >= 26


def test_buscar_filtra_el_listado(client, db_session):
    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    client.post("/pacientes", headers=auth(token), json=_NUEVO)
    client.post(
        "/pacientes",
        headers=auth(token),
        json={"nombre": "Beto", "apellido": "Martinez", "telefono": "70003344"},
    )

    respuesta = client.get("/pacientes?buscar=marti", headers=auth(token))

    assert [p["nombre"] for p in respuesta.json()] == ["Beto"]


def test_un_null_explicito_en_un_campo_obligatorio_da_422_no_500(client, db_session):
    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    creado = client.post("/pacientes", headers=auth(token), json=_NUEVO).json()

    for campo in ("nombre", "apellido", "telefono", "activo"):
        respuesta = client.put(
            f"/pacientes/{creado['id_paciente']}",
            headers=auth(token),
            json={campo: None},
        )
        assert respuesta.status_code == 422, campo


def test_un_null_en_los_campos_opcionales_del_paciente_si_se_acepta(client, db_session):
    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    creado = client.post(
        "/pacientes",
        headers=auth(token),
        json={**_NUEVO, "correo": "ana@ejemplo.com", "direccion": "Calle 1"},
    ).json()

    respuesta = client.put(
        f"/pacientes/{creado['id_paciente']}",
        headers=auth(token),
        json={"correo": None, "direccion": None, "fecha_nacimiento": None},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["correo"] is None
    assert respuesta.json()["edad"] is None


def test_telefono_invalido_devuelve_422(client, db_session):
    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")

    respuesta = client.post(
        "/pacientes", headers=auth(token), json={**_NUEVO, "telefono": "abc"}
    )

    assert respuesta.status_code == 422


@pytest.mark.parametrize("rol_nombre", ["ADMIN", "ASISTENTE", "DOCTOR"])
def test_admin_asistente_y_doctor_pueden_registrar_pacientes(client, db_session, rol_nombre):
    clinica = _clinica(db_session)
    token = _token(db_session, rol_nombre, clinica.id_clinica)

    respuesta = client.post("/pacientes", headers=auth(token), json=_NUEVO)

    assert respuesta.status_code == 201


@pytest.mark.parametrize("rol_nombre", ["ASISTENTE", "DOCTOR"])
def test_asistente_y_doctor_no_pueden_dar_de_baja(client, db_session, rol_nombre):
    clinica = _clinica(db_session)
    token_admin = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    creado = client.post("/pacientes", headers=auth(token_admin), json=_NUEVO).json()
    token = _token(db_session, rol_nombre, clinica.id_clinica)

    respuesta = client.delete(
        f"/pacientes/{creado['id_paciente']}", headers=auth(token)
    )

    assert respuesta.status_code == 403


@pytest.mark.parametrize("rol_nombre", ["ASISTENTE", "DOCTOR"])
def test_el_put_no_es_una_puerta_trasera_al_delete(client, db_session, rol_nombre):
    """Quien no puede dar de baja tampoco puede desactivar por PUT.

    'activo' viaja en el body y el repositorio lo aplica con setattr, asi que
    sin el chequeo explicito un asistente podria mandar {"activo": false} y
    esquivar la regla de que solo un admin da de baja.
    """
    clinica = _clinica(db_session)
    token_admin = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    creado = client.post("/pacientes", headers=auth(token_admin), json=_NUEVO).json()
    token = _token(db_session, rol_nombre, clinica.id_clinica)

    respuesta = client.put(
        f"/pacientes/{creado['id_paciente']}",
        headers=auth(token),
        json={"activo": False},
    )

    assert respuesta.status_code == 403
    sigue = client.get(f"/pacientes/{creado['id_paciente']}", headers=auth(token_admin))
    assert sigue.json()["activo"] is True


@pytest.mark.parametrize("rol_nombre", ["ASISTENTE", "DOCTOR"])
def test_el_asistente_y_el_doctor_si_pueden_editar_los_demas_campos(
    client, db_session, rol_nombre
):
    """El chequeo de 'activo' no debe bloquear la edicion normal."""
    clinica = _clinica(db_session)
    token_admin = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    creado = client.post("/pacientes", headers=auth(token_admin), json=_NUEVO).json()
    token = _token(db_session, rol_nombre, clinica.id_clinica)

    respuesta = client.put(
        f"/pacientes/{creado['id_paciente']}",
        headers=auth(token),
        json={"telefono": "70009999"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["telefono"] == "70009999"


def test_el_admin_si_puede_reactivar_por_put(client, db_session):
    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    creado = client.post("/pacientes", headers=auth(token), json=_NUEVO).json()
    client.delete(f"/pacientes/{creado['id_paciente']}", headers=auth(token))

    respuesta = client.put(
        f"/pacientes/{creado['id_paciente']}",
        headers=auth(token),
        json={"activo": True},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["activo"] is True


def test_el_admin_da_de_baja_y_el_paciente_desaparece_del_listado(client, db_session):
    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    creado = client.post("/pacientes", headers=auth(token), json=_NUEVO).json()

    baja = client.delete(f"/pacientes/{creado['id_paciente']}", headers=auth(token))

    assert baja.status_code == 204
    assert client.get("/pacientes", headers=auth(token)).json() == []
    con_inactivos = client.get("/pacientes?incluir_inactivos=true", headers=auth(token))
    assert len(con_inactivos.json()) == 1


def test_un_admin_no_puede_ver_un_paciente_de_otra_clinica(client, db_session):
    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    token_b = _token(db_session, "ADMIN", clinica_b.id_clinica, "admin.b")
    creado = client.post("/pacientes", headers=auth(token_b), json=_NUEVO).json()
    token_a = _token(db_session, "ADMIN", clinica_a.id_clinica, "admin.a")

    assert client.get(
        f"/pacientes/{creado['id_paciente']}", headers=auth(token_a)
    ).status_code == 404
    assert client.put(
        f"/pacientes/{creado['id_paciente']}",
        headers=auth(token_a),
        json={"nombre": "Hackeado"},
    ).status_code == 404
    assert client.delete(
        f"/pacientes/{creado['id_paciente']}", headers=auth(token_a)
    ).status_code == 404


def test_el_header_x_clinica_id_se_ignora_para_roles_no_superadmin(client, db_session):
    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    token_b = _token(db_session, "ADMIN", clinica_b.id_clinica, "admin.b")
    client.post("/pacientes", headers=auth(token_b), json=_NUEVO)
    token_a = _token(db_session, "ADMIN", clinica_a.id_clinica, "admin.a")

    respuesta = client.get(
        "/pacientes",
        headers={**auth(token_a), "X-Clinica-Id": str(clinica_b.id_clinica)},
    )

    assert respuesta.json() == []


def test_el_superadmin_opera_con_x_clinica_id(client, db_session):
    clinica = _clinica(db_session)
    token = _token(db_session, "SUPERADMIN", None, "super")

    respuesta = client.post(
        "/pacientes",
        headers={**auth(token), "X-Clinica-Id": str(clinica.id_clinica)},
        json=_NUEVO,
    )

    assert respuesta.status_code == 201


def test_el_superadmin_sin_x_clinica_id_recibe_400(client, db_session):
    _clinica(db_session)
    token = _token(db_session, "SUPERADMIN", None, "super")

    assert client.get("/pacientes", headers=auth(token)).status_code == 400
