from datetime import datetime

from tests.factories import crear_clinica, crear_cita, crear_doctor, crear_paciente, headers_de


def test_resumen_citas_requiere_login(client):
    respuesta = client.get("/dashboard/citas/resumen")

    assert respuesta.status_code == 401


def test_admin_ve_resumen_de_citas(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    crear_cita(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor,
        fecha_hora=datetime(2026, 8, 5, 9, 0), estado="completada",
    )
    db_session.commit()

    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.ADMIN)

    respuesta = client.get(
        "/dashboard/citas/resumen",
        params={"desde": "2026-08-01", "hasta": "2026-08-31"},
        headers=headers,
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["total"] == 1
    assert cuerpo["por_estado"]["completada"] == 1
    assert len(cuerpo["por_doctor"]) == 1


def test_doctor_ve_solo_sus_propias_citas(client, db_session):
    from app.models import RolUsuario
    from tests.factories import crear_usuario, token_de, auth

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doc_a = crear_doctor(db_session, clinica.id_clinica, username="doc.a")
    doc_b = crear_doctor(db_session, clinica.id_clinica, username="doc.b")
    crear_cita(
        db_session, clinica.id_clinica, paciente.id_paciente, doc_a.id_doctor,
        fecha_hora=datetime(2026, 8, 5, 9, 0), estado="completada",
    )
    crear_cita(
        db_session, clinica.id_clinica, paciente.id_paciente, doc_b.id_doctor,
        fecha_hora=datetime(2026, 8, 6, 9, 0), estado="completada",
    )
    db_session.commit()

    usuario_doc_a = db_session.get(type(doc_a).id_usuario.class_, doc_a.id_usuario) if False else None
    from app.models import Usuario

    usuario_doc_a = db_session.get(Usuario, doc_a.id_usuario)
    headers = auth(token_de(usuario_doc_a))

    respuesta = client.get(
        "/dashboard/citas/resumen",
        params={"desde": "2026-08-01", "hasta": "2026-08-31"},
        headers=headers,
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["total"] == 1
    assert cuerpo["por_doctor"] == []


def test_doctor_sin_perfil_no_ve_citas(client, db_session):
    from app.models import RolUsuario
    from tests.factories import crear_usuario, token_de, auth

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica, username="doc.con.perfil")
    crear_cita(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor,
        fecha_hora=datetime(2026, 8, 5, 9, 0), estado="completada",
    )
    usuario_sin_perfil = crear_usuario(db_session, RolUsuario.DOCTOR, clinica.id_clinica, "doc.sin.perfil")
    db_session.commit()

    headers = auth(token_de(usuario_sin_perfil))

    respuesta = client.get("/dashboard/citas/resumen", headers=headers)

    assert respuesta.status_code == 200
    assert respuesta.json()["total"] == 0


def test_sin_fechas_usa_mes_actual(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    db_session.commit()
    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.ADMIN)

    respuesta = client.get("/dashboard/citas/resumen", headers=headers)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["desde"] is not None
    assert cuerpo["hasta"] is not None


def _factura_con_pago(db, id_clinica, id_paciente, id_metodo_pago, monto, fecha_pago, numero):
    from app.models import Factura, Pago

    factura = Factura(
        id_clinica=id_clinica, id_paciente=id_paciente, numero_factura=numero,
        monto_subtotal=monto, monto_impuesto="0.00", monto_total=monto,
    )
    db.add(factura)
    db.flush()
    db.add(Pago(id_factura=factura.id_factura, id_metodo_pago=id_metodo_pago, monto=monto, fecha_pago=fecha_pago))
    db.flush()
    return factura


def test_ingresos_requiere_login(client):
    respuesta = client.get("/dashboard/ingresos")

    assert respuesta.status_code == 401


def test_asistente_no_puede_ver_ingresos(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    db_session.commit()
    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.ASISTENTE)

    respuesta = client.get("/dashboard/ingresos", headers=headers)

    assert respuesta.status_code == 403


def test_doctor_no_puede_ver_ingresos(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    db_session.commit()
    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.DOCTOR)

    respuesta = client.get("/dashboard/ingresos", headers=headers)

    assert respuesta.status_code == 403


def test_admin_ve_ingresos_por_metodo_de_pago(client, db_session):
    from app.models import RolUsuario
    from tests.factories import crear_metodo_pago

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    metodo = crear_metodo_pago(db_session, clinica.id_clinica, nombre="Efectivo")
    _factura_con_pago(
        db_session, clinica.id_clinica, paciente.id_paciente, metodo.id_metodo_pago,
        "45.00", datetime(2026, 8, 5, 10, 0), "F000001",
    )
    db_session.commit()
    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.ADMIN)

    respuesta = client.get(
        "/dashboard/ingresos",
        params={"desde": "2026-08-01", "hasta": "2026-08-31", "agrupar_por": "dia"},
        headers=headers,
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["total"] == "45.00"
    assert cuerpo["por_metodo_pago"][0]["nombre"] == "Efectivo"
    assert len(cuerpo["serie"]) == 1


def test_ingresos_agrupar_por_invalido_da_422(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    db_session.commit()
    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.ADMIN)

    respuesta = client.get(
        "/dashboard/ingresos", params={"agrupar_por": "anio"}, headers=headers,
    )

    assert respuesta.status_code == 422
