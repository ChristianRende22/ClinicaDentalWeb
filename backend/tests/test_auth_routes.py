def _crear_clinica_y_admin(db_session, estado="activa"):
    from app.models import Clinica, EstadoClinica, RolUsuario, Usuario
    from app.security.passwords import hash_password

    clinica = Clinica(nombre="Dental Smiling", estado=EstadoClinica(estado))
    db_session.add(clinica)
    db_session.flush()

    usuario = Usuario(
        id_clinica=clinica.id_clinica,
        username="admin.dental",
        password_hash=hash_password("clave123"),
        rol=RolUsuario.ADMIN,
    )
    db_session.add(usuario)
    db_session.commit()
    return clinica, usuario


def test_login_exitoso(client, db_session):
    _crear_clinica_y_admin(db_session)

    respuesta = client.post(
        "/auth/login", json={"username": "admin.dental", "password": "clave123"}
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["token_type"] == "bearer"
    assert cuerpo["usuario"]["username"] == "admin.dental"
    assert "access_token" in cuerpo


def test_login_con_password_incorrecta_devuelve_401(client, db_session):
    _crear_clinica_y_admin(db_session)

    respuesta = client.post(
        "/auth/login", json={"username": "admin.dental", "password": "mala-clave"}
    )

    assert respuesta.status_code == 401


def test_login_con_clinica_suspendida_devuelve_403(client, db_session):
    _crear_clinica_y_admin(db_session, estado="suspendida")

    respuesta = client.post(
        "/auth/login", json={"username": "admin.dental", "password": "clave123"}
    )

    assert respuesta.status_code == 403


def test_me_con_token_valido_devuelve_datos_del_usuario(client, db_session):
    _crear_clinica_y_admin(db_session)

    login = client.post(
        "/auth/login", json={"username": "admin.dental", "password": "clave123"}
    )
    token = login.json()["access_token"]

    respuesta = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    assert respuesta.json()["username"] == "admin.dental"


def test_me_sin_token_devuelve_401(client):
    respuesta = client.get("/auth/me")

    assert respuesta.status_code == 401
