from datetime import timedelta


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


def _cuerpo_semana():
    from app.models import DiaSemana

    dias = []
    for dia in DiaSemana:
        if dia in (DiaSemana.SABADO, DiaSemana.DOMINGO):
            dias.append(
                {
                    "dia_semana": dia.value,
                    "hora_apertura": None,
                    "hora_cierre": None,
                    "cerrado": True,
                }
            )
        else:
            dias.append(
                {
                    "dia_semana": dia.value,
                    "hora_apertura": "08:00:00",
                    "hora_cierre": "17:00:00",
                    "cerrado": False,
                }
            )
    return {"dias": dias}


def test_get_sin_datos_devuelve_los_siete_dias_con_defaults(client, db_session):
    from app.models import HorarioClinica, RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")

    respuesta = client.get("/horarios", headers=_auth(token))

    assert respuesta.status_code == 200
    dias = respuesta.json()
    assert [d["dia_semana"] for d in dias] == [
        "lunes",
        "martes",
        "miercoles",
        "jueves",
        "viernes",
        "sabado",
        "domingo",
    ]
    assert dias[0]["hora_apertura"] == "08:00:00"
    assert dias[0]["cerrado"] is False
    assert dias[5]["cerrado"] is True
    assert dias[5]["hora_apertura"] is None

    # el GET no debe persistir nada
    assert db_session.query(HorarioClinica).count() == 0


def test_put_guarda_la_semana_y_el_get_la_devuelve(client, db_session):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")
    cuerpo = _cuerpo_semana()
    cuerpo["dias"][5] = {
        "dia_semana": "sabado",
        "hora_apertura": "08:00:00",
        "hora_cierre": "12:00:00",
        "cerrado": False,
    }

    guardado = client.put("/horarios", headers=_auth(token), json=cuerpo)

    assert guardado.status_code == 200
    sabado = client.get("/horarios", headers=_auth(token)).json()[5]
    assert sabado["hora_cierre"] == "12:00:00"
    assert sabado["cerrado"] is False


def test_put_con_hora_de_cierre_invalida_devuelve_422(client, db_session):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")
    cuerpo = _cuerpo_semana()
    cuerpo["dias"][0]["hora_cierre"] = "07:00:00"

    assert client.put("/horarios", headers=_auth(token), json=cuerpo).status_code == 422


def test_put_con_menos_de_siete_dias_devuelve_422(client, db_session):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")
    cuerpo = _cuerpo_semana()
    cuerpo["dias"] = cuerpo["dias"][:5]

    assert client.put("/horarios", headers=_auth(token), json=cuerpo).status_code == 422


def test_el_horario_de_una_clinica_no_se_ve_desde_otra(client, db_session):
    from app.models import RolUsuario

    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    token_a = _token_para(db_session, RolUsuario.ADMIN, clinica_a.id_clinica, "admin.a")
    token_b = _token_para(db_session, RolUsuario.ADMIN, clinica_b.id_clinica, "admin.b")
    cuerpo = _cuerpo_semana()
    cuerpo["dias"][0]["hora_cierre"] = "20:00:00"
    client.put("/horarios", headers=_auth(token_a), json=cuerpo)

    lunes_b = client.get("/horarios", headers=_auth(token_b)).json()[0]

    assert lunes_b["hora_cierre"] == "17:00:00"  # sigue viendo el default


def test_el_doctor_lee_el_horario_pero_no_lo_edita(client, db_session):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.DOCTOR, clinica.id_clinica, "doc.a")

    assert client.get("/horarios", headers=_auth(token)).status_code == 200
    assert client.put(
        "/horarios", headers=_auth(token), json=_cuerpo_semana()
    ).status_code == 403
