from datetime import datetime, timedelta

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


def _futuro(dias=7, hora=9):
    """Un martes futuro a las 9, dentro del horario por defecto (L-V 08-17)."""
    base = datetime.now() + timedelta(days=dias)
    while base.weekday() != 1:  # martes
        base += timedelta(days=1)
    return base.replace(hour=hora, minute=0, second=0, microsecond=0)


def _clinica_lista(client, db_session, nombre="Dental A", sufijo="a"):
    """Crea clinica, admin, paciente y doctor CON horario cargado.

    Devuelve (clinica, token_admin, id_paciente, id_doctor).
    """
    clinica = _clinica(db_session, nombre)
    token = _token(db_session, "ADMIN", clinica.id_clinica, f"admin.{sufijo}")

    paciente = client.post(
        "/pacientes",
        headers=auth(token),
        json={"nombre": "Ana", "apellido": "Lopez", "telefono": "70001122"},
    ).json()
    doctor = client.post(
        "/doctores",
        headers=auth(token),
        json={
            "username": f"dra.{sufijo}",
            "nombre": "Marta",
            "apellido": "Perez",
            "telefono": "70003344",
        },
    ).json()["doctor"]
    client.put(
        f"/doctores/{doctor['id_doctor']}/horarios",
        headers=auth(token),
        json={
            "bloques": [
                {"dia_semana": dia, "hora_inicio": "08:00:00", "hora_fin": "17:00:00"}
                for dia in ("lunes", "martes", "miercoles", "jueves", "viernes")
            ]
        },
    )
    return clinica, token, paciente["id_paciente"], doctor["id_doctor"]


def _cuerpo(id_paciente, id_doctor, cuando=None, **campos):
    base = {
        "id_paciente": id_paciente,
        "id_doctor": id_doctor,
        "fecha_hora": (cuando or _futuro()).isoformat(),
    }
    base.update(campos)
    return base


def test_agendar_una_cita_valida(client, db_session):
    _, token, id_paciente, id_doctor = _clinica_lista(client, db_session)

    respuesta = client.post(
        "/citas", headers=auth(token), json=_cuerpo(id_paciente, id_doctor)
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["estado"] == "programada"
    assert respuesta.json()["duracion_minutos"] == 30


def test_agendar_en_el_pasado_devuelve_422(client, db_session):
    _, token, id_paciente, id_doctor = _clinica_lista(client, db_session)
    ayer = datetime.now() - timedelta(days=1)

    respuesta = client.post(
        "/citas", headers=auth(token), json=_cuerpo(id_paciente, id_doctor, ayer)
    )

    assert respuesta.status_code == 422


def test_agendar_sin_la_anticipacion_minima_devuelve_422(client, db_session):
    _, token, id_paciente, id_doctor = _clinica_lista(client, db_session)
    en_dos_horas = datetime.now() + timedelta(hours=2)

    respuesta = client.post(
        "/citas", headers=auth(token), json=_cuerpo(id_paciente, id_doctor, en_dos_horas)
    )

    assert respuesta.status_code == 422


def test_agendar_fuera_del_horario_de_la_clinica_devuelve_422(client, db_session):
    _, token, id_paciente, id_doctor = _clinica_lista(client, db_session)
    a_las_seis = _futuro(hora=6)

    respuesta = client.post(
        "/citas", headers=auth(token), json=_cuerpo(id_paciente, id_doctor, a_las_seis)
    )

    assert respuesta.status_code == 422


def test_un_doctor_sin_horario_cargado_devuelve_422(client, db_session):
    clinica, token, id_paciente, _ = _clinica_lista(client, db_session)
    sin_horario = client.post(
        "/doctores",
        headers=auth(token),
        json={
            "username": "dr.nuevo",
            "nombre": "Nuevo",
            "apellido": "Doctor",
            "telefono": "70009999",
        },
    ).json()["doctor"]

    respuesta = client.post(
        "/citas",
        headers=auth(token),
        json=_cuerpo(id_paciente, sin_horario["id_doctor"]),
    )

    assert respuesta.status_code == 422


def test_dos_citas_solapadas_del_mismo_doctor_devuelven_409(client, db_session):
    _, token, id_paciente, id_doctor = _clinica_lista(client, db_session)
    cuando = _futuro()
    client.post("/citas", headers=auth(token), json=_cuerpo(id_paciente, id_doctor, cuando))

    repetida = client.post(
        "/citas",
        headers=auth(token),
        json=_cuerpo(id_paciente, id_doctor, cuando + timedelta(minutes=15)),
    )

    assert repetida.status_code == 409


def test_un_paciente_de_otra_clinica_devuelve_422(client, db_session):
    _, token_a, _, id_doctor_a = _clinica_lista(client, db_session, "Dental A", "a")
    _, _, id_paciente_b, _ = _clinica_lista(client, db_session, "Dental B", "b")

    respuesta = client.post(
        "/citas", headers=auth(token_a), json=_cuerpo(id_paciente_b, id_doctor_a)
    )

    assert respuesta.status_code == 422


def test_el_asistente_agenda_y_queda_registrado_como_quien_agendo(client, db_session):
    from app.repositories.usuario_repository import UsuarioRepository

    clinica, token_admin, id_paciente, id_doctor = _clinica_lista(client, db_session)
    creado = client.post(
        "/asistentes",
        headers=auth(token_admin),
        json={
            "username": "recepcion",
            "nombre": "Rosa",
            "apellido": "Diaz",
            "telefono": "70005566",
        },
    ).json()
    usuario = UsuarioRepository(db_session).obtener_por_username("recepcion")
    token_asistente = token_de(usuario)

    respuesta = client.post(
        "/citas", headers=auth(token_asistente), json=_cuerpo(id_paciente, id_doctor)
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["id_asistente"] == creado["asistente"]["id_asistente"]


def test_un_doctor_no_puede_agendar(client, db_session):
    clinica, token_admin, id_paciente, id_doctor = _clinica_lista(client, db_session)
    from app.repositories.usuario_repository import UsuarioRepository

    usuario = UsuarioRepository(db_session).obtener_por_username("dra.a")
    token_doctor = token_de(usuario)

    respuesta = client.post(
        "/citas", headers=auth(token_doctor), json=_cuerpo(id_paciente, id_doctor)
    )

    assert respuesta.status_code == 403


def test_un_doctor_solo_ve_sus_propias_citas(client, db_session):
    from app.repositories.usuario_repository import UsuarioRepository

    clinica, token, id_paciente, id_doctor = _clinica_lista(client, db_session)
    otro = client.post(
        "/doctores",
        headers=auth(token),
        json={
            "username": "dr.otro",
            "nombre": "Otro",
            "apellido": "Doctor",
            "telefono": "70009999",
        },
    ).json()["doctor"]
    client.put(
        f"/doctores/{otro['id_doctor']}/horarios",
        headers=auth(token),
        json={
            "bloques": [
                {"dia_semana": "martes", "hora_inicio": "08:00:00", "hora_fin": "17:00:00"}
            ]
        },
    )
    mia = client.post(
        "/citas", headers=auth(token), json=_cuerpo(id_paciente, id_doctor)
    ).json()
    ajena = client.post(
        "/citas",
        headers=auth(token),
        json=_cuerpo(id_paciente, otro["id_doctor"], _futuro(dias=14)),
    ).json()

    usuario = UsuarioRepository(db_session).obtener_por_username("dra.a")
    token_doctor = token_de(usuario)

    listado = client.get("/citas", headers=auth(token_doctor)).json()

    assert [c["id_cita"] for c in listado] == [mia["id_cita"]]
    assert ajena["id_cita"] != mia["id_cita"]


def test_un_doctor_pide_una_cita_ajena_y_recibe_404_no_403(client, db_session):
    """404 y no 403: un 403 le confirmaria que la cita existe, que ya es
    informacion sobre un paciente que no atiende.
    """
    from app.repositories.usuario_repository import UsuarioRepository

    clinica, token, id_paciente, id_doctor = _clinica_lista(client, db_session)
    otro = client.post(
        "/doctores",
        headers=auth(token),
        json={
            "username": "dr.otro",
            "nombre": "Otro",
            "apellido": "Doctor",
            "telefono": "70009999",
        },
    ).json()["doctor"]
    client.put(
        f"/doctores/{otro['id_doctor']}/horarios",
        headers=auth(token),
        json={
            "bloques": [
                {"dia_semana": "martes", "hora_inicio": "08:00:00", "hora_fin": "17:00:00"}
            ]
        },
    )
    ajena = client.post(
        "/citas", headers=auth(token), json=_cuerpo(id_paciente, otro["id_doctor"])
    ).json()

    usuario = UsuarioRepository(db_session).obtener_por_username("dra.a")
    token_doctor = token_de(usuario)

    respuesta = client.get(f"/citas/{ajena['id_cita']}", headers=auth(token_doctor))

    assert respuesta.status_code == 404
    # Control: la misma cita existe y el admin si la ve. Sin esto el test
    # pasaria igual si el endpoint devolviera 404 siempre.
    assert client.get(
        f"/citas/{ajena['id_cita']}", headers=auth(token)
    ).status_code == 200


def test_un_doctor_sin_perfil_no_ve_ninguna_cita(client, db_session):
    """El filtro falla cerrado: sin perfil no se ve nada, en vez de verse todo.

    Un Usuario con rol doctor pero sin fila Doctor es alcanzable si el alta no
    paso por PersonalService (un seed, un INSERT a mano, un perfil borrado).
    """
    clinica, token, id_paciente, id_doctor = _clinica_lista(client, db_session)
    ajena = client.post(
        "/citas", headers=auth(token), json=_cuerpo(id_paciente, id_doctor)
    ).json()
    token_sin_perfil = _token(db_session, "DOCTOR", clinica.id_clinica, "doctor.sin.perfil")

    listado = client.get("/citas", headers=auth(token_sin_perfil))
    detalle = client.get(f"/citas/{ajena['id_cita']}", headers=auth(token_sin_perfil))

    assert listado.status_code == 200
    assert listado.json() == []
    assert detalle.status_code == 404


def test_un_doctor_no_puede_ver_las_citas_de_otro_por_query_string(client, db_session):
    """El id_doctor del query string se ignora para el rol doctor."""
    from app.repositories.usuario_repository import UsuarioRepository

    clinica, token, id_paciente, id_doctor = _clinica_lista(client, db_session)
    otro = client.post(
        "/doctores",
        headers=auth(token),
        json={
            "username": "dr.otro",
            "nombre": "Otro",
            "apellido": "Doctor",
            "telefono": "70009999",
        },
    ).json()["doctor"]
    client.put(
        f"/doctores/{otro['id_doctor']}/horarios",
        headers=auth(token),
        json={
            "bloques": [
                {"dia_semana": "martes", "hora_inicio": "08:00:00", "hora_fin": "17:00:00"}
            ]
        },
    )
    client.post(
        "/citas", headers=auth(token), json=_cuerpo(id_paciente, otro["id_doctor"])
    )

    usuario = UsuarioRepository(db_session).obtener_por_username("dra.a")
    token_doctor = token_de(usuario)

    listado = client.get(
        f"/citas?id_doctor={otro['id_doctor']}", headers=auth(token_doctor)
    )

    assert listado.status_code == 200
    assert listado.json() == []


def test_un_doctor_recibe_404_al_cambiar_el_estado_de_una_cita_ajena(client, db_session):
    from app.repositories.usuario_repository import UsuarioRepository

    clinica, token, id_paciente, id_doctor = _clinica_lista(client, db_session)
    otro = client.post(
        "/doctores",
        headers=auth(token),
        json={
            "username": "dr.otro",
            "nombre": "Otro",
            "apellido": "Doctor",
            "telefono": "70009999",
        },
    ).json()["doctor"]
    client.put(
        f"/doctores/{otro['id_doctor']}/horarios",
        headers=auth(token),
        json={
            "bloques": [
                {"dia_semana": "martes", "hora_inicio": "08:00:00", "hora_fin": "17:00:00"}
            ]
        },
    )
    ajena = client.post(
        "/citas", headers=auth(token), json=_cuerpo(id_paciente, otro["id_doctor"])
    ).json()

    usuario = UsuarioRepository(db_session).obtener_por_username("dra.a")
    token_doctor = token_de(usuario)

    estado = client.patch(
        f"/citas/{ajena['id_cita']}/estado",
        headers=auth(token_doctor),
        json={"estado": "confirmada"},
    )
    cancelar = client.patch(
        f"/citas/{ajena['id_cita']}/cancelar", headers=auth(token_doctor)
    )

    assert estado.status_code == 404
    assert cancelar.status_code == 404
    # Control: la misma cita existe y el admin si la ve. Sin esto el test
    # pasaria igual si el endpoint devolviera 404 siempre.
    assert client.get(
        f"/citas/{ajena['id_cita']}", headers=auth(token)
    ).status_code == 200


def test_el_doctor_de_la_cita_si_puede_cambiarle_el_estado(client, db_session):
    from app.repositories.usuario_repository import UsuarioRepository

    clinica, token, id_paciente, id_doctor = _clinica_lista(client, db_session)
    propia = client.post(
        "/citas", headers=auth(token), json=_cuerpo(id_paciente, id_doctor)
    ).json()

    usuario = UsuarioRepository(db_session).obtener_por_username("dra.a")
    token_doctor = token_de(usuario)

    respuesta = client.patch(
        f"/citas/{propia['id_cita']}/estado",
        headers=auth(token_doctor),
        json={"estado": "confirmada"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "confirmada"


def test_confirmar_y_completar_una_cita(client, db_session):
    _, token, id_paciente, id_doctor = _clinica_lista(client, db_session)
    cita = client.post(
        "/citas", headers=auth(token), json=_cuerpo(id_paciente, id_doctor)
    ).json()

    confirmada = client.patch(
        f"/citas/{cita['id_cita']}/estado",
        headers=auth(token),
        json={"estado": "confirmada"},
    )
    completada = client.patch(
        f"/citas/{cita['id_cita']}/estado",
        headers=auth(token),
        json={"estado": "completada"},
    )

    assert confirmada.json()["estado"] == "confirmada"
    assert completada.json()["estado"] == "completada"


def test_completar_una_cita_sin_confirmar_devuelve_409(client, db_session):
    _, token, id_paciente, id_doctor = _clinica_lista(client, db_session)
    cita = client.post(
        "/citas", headers=auth(token), json=_cuerpo(id_paciente, id_doctor)
    ).json()

    respuesta = client.patch(
        f"/citas/{cita['id_cita']}/estado",
        headers=auth(token),
        json={"estado": "completada"},
    )

    assert respuesta.status_code == 409


def test_cancelar_con_anticipacion_suficiente(client, db_session):
    _, token, id_paciente, id_doctor = _clinica_lista(client, db_session)
    cita = client.post(
        "/citas", headers=auth(token), json=_cuerpo(id_paciente, id_doctor)
    ).json()

    respuesta = client.patch(f"/citas/{cita['id_cita']}/cancelar", headers=auth(token))

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "cancelada"


def test_reagendar_mueve_la_cita_y_cuenta_el_movimiento(client, db_session):
    _, token, id_paciente, id_doctor = _clinica_lista(client, db_session)
    cita = client.post(
        "/citas", headers=auth(token), json=_cuerpo(id_paciente, id_doctor)
    ).json()

    respuesta = client.patch(
        f"/citas/{cita['id_cita']}/reagendar",
        headers=auth(token),
        json={"fecha_hora": _futuro(dias=21).isoformat()},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["id_cita"] == cita["id_cita"]
    assert cuerpo["veces_reagendada"] == 1
    assert cuerpo["estado"] == "programada"


def test_reagendar_demasiado_pronto_devuelve_422(client, db_session):
    _, token, id_paciente, id_doctor = _clinica_lista(client, db_session)
    cita = client.post(
        "/citas", headers=auth(token), json=_cuerpo(id_paciente, id_doctor)
    ).json()
    manana = datetime.now() + timedelta(days=1)

    respuesta = client.patch(
        f"/citas/{cita['id_cita']}/reagendar",
        headers=auth(token),
        json={"fecha_hora": manana.isoformat()},
    )

    assert respuesta.status_code == 422


def test_una_cita_de_otra_clinica_devuelve_404(client, db_session):
    _, token_a, _, _ = _clinica_lista(client, db_session, "Dental A", "a")
    _, token_b, id_paciente_b, id_doctor_b = _clinica_lista(
        client, db_session, "Dental B", "b"
    )
    de_b = client.post(
        "/citas", headers=auth(token_b), json=_cuerpo(id_paciente_b, id_doctor_b)
    ).json()

    assert client.get(
        f"/citas/{de_b['id_cita']}", headers=auth(token_a)
    ).status_code == 404
    assert client.patch(
        f"/citas/{de_b['id_cita']}/cancelar", headers=auth(token_a)
    ).status_code == 404


def test_no_existe_delete_de_citas(client, db_session):
    """Una cita no se borra, se cancela."""
    _, token, id_paciente, id_doctor = _clinica_lista(client, db_session)
    cita = client.post(
        "/citas", headers=auth(token), json=_cuerpo(id_paciente, id_doctor)
    ).json()

    respuesta = client.delete(f"/citas/{cita['id_cita']}", headers=auth(token))

    assert respuesta.status_code == 405
