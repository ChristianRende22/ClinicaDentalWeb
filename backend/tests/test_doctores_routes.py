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
    "username": "dra.perez",
    "nombre": "Marta",
    "apellido": "Perez",
    "telefono": "70003344",
}


def test_crear_doctor_devuelve_201_y_la_password_temporal(client, db_session):
    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")

    respuesta = client.post("/doctores", headers=auth(token), json=_NUEVO)

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["doctor"]["nombre"] == "Marta"
    assert len(cuerpo["password_temporal"]) >= 12


def test_el_listado_nunca_devuelve_la_password(client, db_session):
    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    client.post("/doctores", headers=auth(token), json=_NUEVO)

    listado = client.get("/doctores", headers=auth(token)).json()

    assert "password_temporal" not in listado[0]


def test_username_repetido_devuelve_409(client, db_session):
    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    client.post("/doctores", headers=auth(token), json=_NUEVO)

    repetido = client.post("/doctores", headers=auth(token), json=_NUEVO)

    assert repetido.status_code == 409


def test_una_especialidad_de_otra_clinica_devuelve_422(client, db_session):
    from app.repositories.especialidad_repository import EspecialidadRepository

    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    de_b = EspecialidadRepository(db_session).crear(
        clinica_b.id_clinica, {"nombre": "Ortodoncia"}
    )
    db_session.commit()
    token_a = _token(db_session, "ADMIN", clinica_a.id_clinica, "admin.a")

    respuesta = client.post(
        "/doctores",
        headers=auth(token_a),
        json={**_NUEVO, "id_especialidad": de_b.id_especialidad},
    )

    assert respuesta.status_code == 422


@pytest.mark.parametrize("rol_nombre", ["DOCTOR", "ASISTENTE"])
def test_doctor_y_asistente_leen_pero_no_dan_de_alta(client, db_session, rol_nombre):
    clinica = _clinica(db_session)
    token = _token(db_session, rol_nombre, clinica.id_clinica)

    assert client.get("/doctores", headers=auth(token)).status_code == 200
    assert client.post("/doctores", headers=auth(token), json=_NUEVO).status_code == 403


def test_el_put_no_acepta_una_especialidad_de_otra_clinica(client, db_session):
    from app.repositories.especialidad_repository import EspecialidadRepository

    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    de_b = EspecialidadRepository(db_session).crear(
        clinica_b.id_clinica, {"nombre": "Ortodoncia"}
    )
    db_session.commit()
    token_a = _token(db_session, "ADMIN", clinica_a.id_clinica, "admin.a")
    creado = client.post("/doctores", headers=auth(token_a), json=_NUEVO).json()

    respuesta = client.put(
        f"/doctores/{creado['doctor']['id_doctor']}",
        headers=auth(token_a),
        json={"id_especialidad": de_b.id_especialidad},
    )

    assert respuesta.status_code == 422


def test_el_put_no_acepta_una_especialidad_inexistente(client, db_session):
    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    creado = client.post("/doctores", headers=auth(token), json=_NUEVO).json()

    respuesta = client.put(
        f"/doctores/{creado['doctor']['id_doctor']}",
        headers=auth(token),
        json={"id_especialidad": 987654},
    )

    assert respuesta.status_code == 422


def test_reactivar_por_put_tambien_reactiva_el_usuario(client, db_session):
    """La actividad del perfil y la del login se mueven juntas en los dos sentidos."""
    from app.repositories.usuario_repository import UsuarioRepository

    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    creado = client.post("/doctores", headers=auth(token), json=_NUEVO).json()
    id_doctor = creado["doctor"]["id_doctor"]
    client.delete(f"/doctores/{id_doctor}", headers=auth(token))
    assert UsuarioRepository(db_session).obtener_por_username("dra.perez").activo is False

    respuesta = client.put(
        f"/doctores/{id_doctor}", headers=auth(token), json={"activo": True}
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["activo"] is True
    assert UsuarioRepository(db_session).obtener_por_username("dra.perez").activo is True


def test_desactivar_por_put_tambien_desactiva_el_usuario(client, db_session):
    from app.repositories.usuario_repository import UsuarioRepository

    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    creado = client.post("/doctores", headers=auth(token), json=_NUEVO).json()

    respuesta = client.put(
        f"/doctores/{creado['doctor']['id_doctor']}",
        headers=auth(token),
        json={"activo": False},
    )

    assert respuesta.status_code == 200
    assert UsuarioRepository(db_session).obtener_por_username("dra.perez").activo is False


def test_la_baja_desactiva_tambien_el_usuario(client, db_session):
    from app.repositories.usuario_repository import UsuarioRepository

    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    creado = client.post("/doctores", headers=auth(token), json=_NUEVO).json()

    baja = client.delete(
        f"/doctores/{creado['doctor']['id_doctor']}", headers=auth(token)
    )

    assert baja.status_code == 204
    usuario = UsuarioRepository(db_session).obtener_por_username("dra.perez")
    assert usuario.activo is False


def test_no_se_puede_ver_un_doctor_de_otra_clinica(client, db_session):
    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    token_b = _token(db_session, "ADMIN", clinica_b.id_clinica, "admin.b")
    creado = client.post("/doctores", headers=auth(token_b), json=_NUEVO).json()
    token_a = _token(db_session, "ADMIN", clinica_a.id_clinica, "admin.a")

    assert client.get(
        f"/doctores/{creado['doctor']['id_doctor']}", headers=auth(token_a)
    ).status_code == 404


def test_un_null_explicito_en_un_campo_obligatorio_da_422_no_500(client, db_session):
    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    creado = client.post("/doctores", headers=auth(token), json=_NUEVO).json()

    respuesta = client.put(
        f"/doctores/{creado['doctor']['id_doctor']}",
        headers=auth(token),
        json={"nombre": None},
    )

    assert respuesta.status_code == 422


def test_un_null_en_un_campo_opcional_si_se_acepta(client, db_session):
    """correo e id_especialidad son nullable: null es como se borra el dato."""
    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    creado = client.post(
        "/doctores",
        headers=auth(token),
        json={**_NUEVO, "correo": "dra@ejemplo.com"},
    ).json()

    respuesta = client.put(
        f"/doctores/{creado['doctor']['id_doctor']}",
        headers=auth(token),
        json={"correo": None},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["correo"] is None


def test_un_put_que_falla_no_deja_la_baja_aplicada_a_medias(client, db_session):
    """El PUT es todo o nada: no puede desactivar y despues fallar.

    Antes el manejo de 'activo' iba primero y el servicio commiteaba adentro,
    asi que un fallo posterior dejaba al doctor y su Usuario desactivados con
    un error en la respuesta.
    """
    from app.repositories.usuario_repository import UsuarioRepository

    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    creado = client.post("/doctores", headers=auth(token), json=_NUEVO).json()

    respuesta = client.put(
        f"/doctores/{creado['doctor']['id_doctor']}",
        headers=auth(token),
        json={"activo": False, "nombre": None},
    )

    assert respuesta.status_code == 422
    assert UsuarioRepository(db_session).obtener_por_username("dra.perez").activo is True
    detalle = client.get(
        f"/doctores/{creado['doctor']['id_doctor']}", headers=auth(token)
    ).json()
    assert detalle["activo"] is True


def test_filtrar_el_listado_por_especialidad(client, db_session):
    from app.repositories.especialidad_repository import EspecialidadRepository

    clinica = _clinica(db_session)
    orto = EspecialidadRepository(db_session).crear(
        clinica.id_clinica, {"nombre": "Ortodoncia"}
    )
    db_session.commit()
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    client.post(
        "/doctores",
        headers=auth(token),
        json={**_NUEVO, "id_especialidad": orto.id_especialidad},
    )
    client.post(
        "/doctores",
        headers=auth(token),
        json={**_NUEVO, "username": "dr.otro", "nombre": "Otro"},
    )

    filtrado = client.get(
        f"/doctores?id_especialidad={orto.id_especialidad}", headers=auth(token)
    ).json()

    assert [d["nombre"] for d in filtrado] == ["Marta"]


# --- horarios anidados ----------------------------------------------------

_BLOQUES = {
    "bloques": [
        {"dia_semana": "lunes", "hora_inicio": "08:00:00", "hora_fin": "12:00:00"},
        {"dia_semana": "lunes", "hora_inicio": "14:00:00", "hora_fin": "18:00:00"},
    ]
}


def test_el_admin_carga_el_horario_de_un_doctor(client, db_session):
    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    creado = client.post("/doctores", headers=auth(token), json=_NUEVO).json()
    id_doctor = creado["doctor"]["id_doctor"]

    puesto = client.put(
        f"/doctores/{id_doctor}/horarios", headers=auth(token), json=_BLOQUES
    )

    assert puesto.status_code == 200
    assert len(puesto.json()) == 2
    assert client.get(
        f"/doctores/{id_doctor}/horarios", headers=auth(token)
    ).json() == puesto.json()


def test_bloques_solapados_devuelven_422(client, db_session):
    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    creado = client.post("/doctores", headers=auth(token), json=_NUEVO).json()

    respuesta = client.put(
        f"/doctores/{creado['doctor']['id_doctor']}/horarios",
        headers=auth(token),
        json={
            "bloques": [
                {"dia_semana": "lunes", "hora_inicio": "08:00:00", "hora_fin": "12:00:00"},
                {"dia_semana": "lunes", "hora_inicio": "11:00:00", "hora_fin": "14:00:00"},
            ]
        },
    )

    assert respuesta.status_code == 422


def test_un_doctor_edita_su_propio_horario_pero_no_el_de_otro(client, db_session):
    clinica = _clinica(db_session)
    token_admin = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    propio = client.post("/doctores", headers=auth(token_admin), json=_NUEVO).json()
    ajeno = client.post(
        "/doctores",
        headers=auth(token_admin),
        json={**_NUEVO, "username": "dr.otro", "nombre": "Otro"},
    ).json()

    # El token del doctor propio: su Usuario es el que creo PersonalService.
    from app.repositories.usuario_repository import UsuarioRepository

    usuario = UsuarioRepository(db_session).obtener_por_username("dra.perez")
    token_doctor = token_de(usuario)

    propio_ok = client.put(
        f"/doctores/{propio['doctor']['id_doctor']}/horarios",
        headers=auth(token_doctor),
        json=_BLOQUES,
    )
    ajeno_no = client.put(
        f"/doctores/{ajeno['doctor']['id_doctor']}/horarios",
        headers=auth(token_doctor),
        json=_BLOQUES,
    )

    assert propio_ok.status_code == 200
    assert ajeno_no.status_code == 403


def test_los_horarios_de_un_doctor_de_otra_clinica_devuelven_404(client, db_session):
    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    token_b = _token(db_session, "ADMIN", clinica_b.id_clinica, "admin.b")
    creado = client.post("/doctores", headers=auth(token_b), json=_NUEVO).json()
    token_a = _token(db_session, "ADMIN", clinica_a.id_clinica, "admin.a")

    assert client.get(
        f"/doctores/{creado['doctor']['id_doctor']}/horarios", headers=auth(token_a)
    ).status_code == 404
