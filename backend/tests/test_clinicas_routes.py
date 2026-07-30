from datetime import timedelta


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


def _token_superadmin(db_session):
    from app.models import RolUsuario

    return _token_para(db_session, RolUsuario.SUPERADMIN, username="superadmin")


def test_crear_clinica_sin_token_devuelve_401(client):
    respuesta = client.post("/clinicas", json={"nombre": "Dental X", "admin_username": "x"})

    assert respuesta.status_code == 401


def test_crear_clinica_con_rol_no_superadmin_devuelve_403(client, db_session):
    from app.models import RolUsuario

    token = _token_para(db_session, RolUsuario.ADMIN, id_clinica=None, username="admin.normal")

    respuesta = client.post(
        "/clinicas",
        headers={"Authorization": f"Bearer {token}"},
        json={"nombre": "Dental X", "admin_username": "x"},
    )

    assert respuesta.status_code == 403


def test_crear_clinica_exitoso(client, db_session):
    token = _token_superadmin(db_session)

    respuesta = client.post(
        "/clinicas",
        headers={"Authorization": f"Bearer {token}"},
        json={"nombre": "Dental Smiling", "admin_username": "admin.dentalsmiling"},
    )

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["clinica"]["nombre"] == "Dental Smiling"
    assert cuerpo["clinica"]["estado"] == "activa"
    assert cuerpo["admin"]["username"] == "admin.dentalsmiling"
    assert len(cuerpo["password_temporal"]) >= 12


def test_crear_clinica_username_duplicado_devuelve_409(client, db_session):
    token = _token_superadmin(db_session)
    client.post(
        "/clinicas",
        headers={"Authorization": f"Bearer {token}"},
        json={"nombre": "Dental Uno", "admin_username": "admin.repetido"},
    )

    respuesta = client.post(
        "/clinicas",
        headers={"Authorization": f"Bearer {token}"},
        json={"nombre": "Dental Dos", "admin_username": "admin.repetido"},
    )

    assert respuesta.status_code == 409


def test_listar_clinicas(client, db_session):
    token = _token_superadmin(db_session)
    client.post(
        "/clinicas",
        headers={"Authorization": f"Bearer {token}"},
        json={"nombre": "Dental Uno", "admin_username": "admin.uno"},
    )

    respuesta = client.get("/clinicas", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 1


def test_obtener_clinica_inexistente_devuelve_404(client, db_session):
    token = _token_superadmin(db_session)

    respuesta = client.get("/clinicas/999", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 404


def test_actualizar_clinica(client, db_session):
    token = _token_superadmin(db_session)
    creada = client.post(
        "/clinicas",
        headers={"Authorization": f"Bearer {token}"},
        json={"nombre": "Dental Original", "admin_username": "admin.original"},
    ).json()

    respuesta = client.put(
        f"/clinicas/{creada['clinica']['id_clinica']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"nombre": "Dental Renombrada"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Dental Renombrada"


def test_cambiar_estado_clinica(client, db_session):
    token = _token_superadmin(db_session)
    creada = client.post(
        "/clinicas",
        headers={"Authorization": f"Bearer {token}"},
        json={"nombre": "Dental Uno", "admin_username": "admin.uno"},
    ).json()

    respuesta = client.patch(
        f"/clinicas/{creada['clinica']['id_clinica']}/estado",
        headers={"Authorization": f"Bearer {token}"},
        json={"estado": "suspendida"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "suspendida"


def test_actualizar_modulo_deshabilita(client, db_session):
    token = _token_superadmin(db_session)
    creada = client.post(
        "/clinicas",
        headers={"Authorization": f"Bearer {token}"},
        json={"nombre": "Dental Uno", "admin_username": "admin.uno"},
    ).json()

    respuesta = client.patch(
        f"/clinicas/{creada['clinica']['id_clinica']}/modulos/recetas",
        headers={"Authorization": f"Bearer {token}"},
        json={"habilitado": False},
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"modulo": "recetas", "habilitado": False}


def test_actualizar_modulo_inexistente_devuelve_404(client, db_session):
    token = _token_superadmin(db_session)
    creada = client.post(
        "/clinicas",
        headers={"Authorization": f"Bearer {token}"},
        json={"nombre": "Dental Uno", "admin_username": "admin.uno"},
    ).json()

    respuesta = client.patch(
        f"/clinicas/{creada['clinica']['id_clinica']}/modulos/no-existe",
        headers={"Authorization": f"Bearer {token}"},
        json={"habilitado": False},
    )

    assert respuesta.status_code == 404
