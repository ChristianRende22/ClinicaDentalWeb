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


def test_get_crea_la_configuracion_al_vuelo_con_los_defaults(client, db_session):
    from app.models import ConfiguracionClinica, RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")

    respuesta = client.get("/configuracion", headers=_auth(token))

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["duracion_cita_minutos"] == 30
    assert float(cuerpo["porcentaje_impuesto"]) == 13.00
    assert cuerpo["prefijo_factura"] == "F"
    assert cuerpo["proximo_numero_factura"] == 1
    assert cuerpo["horas_minimas_cambio_cita"] == 24
    assert cuerpo["dias_minimos_reagendamiento"] == 3
    assert db_session.query(ConfiguracionClinica).count() == 1


def test_get_dos_veces_no_duplica_la_fila(client, db_session):
    from app.models import ConfiguracionClinica, RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")

    client.get("/configuracion", headers=_auth(token))
    client.get("/configuracion", headers=_auth(token))

    assert db_session.query(ConfiguracionClinica).count() == 1


def test_put_actualiza_solo_lo_enviado(client, db_session):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")

    respuesta = client.put(
        "/configuracion", headers=_auth(token), json={"duracion_cita_minutos": 45}
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["duracion_cita_minutos"] == 45
    assert float(respuesta.json()["porcentaje_impuesto"]) == 13.00


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("duracion_cita_minutos", 4),
        ("duracion_cita_minutos", 481),
        ("porcentaje_impuesto", -1),
        ("porcentaje_impuesto", 101),
        ("proximo_numero_factura", 0),
        ("horas_minimas_cambio_cita", 0),
        ("horas_minimas_cambio_cita", 721),
        ("dias_minimos_reagendamiento", 0),
        ("dias_minimos_reagendamiento", 91),
    ],
)
def test_valores_fuera_de_rango_devuelven_422(client, db_session, campo, valor):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")

    assert client.put(
        "/configuracion", headers=_auth(token), json={campo: valor}
    ).status_code == 422


def test_la_configuracion_de_una_clinica_no_se_ve_desde_otra(client, db_session):
    from app.models import RolUsuario

    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    token_a = _token_para(db_session, RolUsuario.ADMIN, clinica_a.id_clinica, "admin.a")
    token_b = _token_para(db_session, RolUsuario.ADMIN, clinica_b.id_clinica, "admin.b")
    client.put("/configuracion", headers=_auth(token_a), json={"duracion_cita_minutos": 60})

    assert client.get("/configuracion", headers=_auth(token_b)).json()[
        "duracion_cita_minutos"
    ] == 30


@pytest.mark.parametrize("rol_nombre", ["DOCTOR", "ASISTENTE"])
def test_doctor_y_asistente_leen_la_configuracion_pero_no_la_editan(
    client, db_session, rol_nombre
):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    rol = getattr(RolUsuario, rol_nombre)
    token = _token_para(db_session, rol, clinica.id_clinica, f"user.{rol_nombre.lower()}")

    assert client.get("/configuracion", headers=_auth(token)).status_code == 200
    assert client.put(
        "/configuracion", headers=_auth(token), json={"duracion_cita_minutos": 45}
    ).status_code == 403
