from tests.factories import (
    crear_clinica,
    crear_doctor,
    crear_metodo_pago,
    crear_paciente,
    crear_plan_aceptado_con_presupuesto,
    crear_tratamiento,
    headers_de,
)


def test_crear_factura_suelta_requiere_login(client):
    respuesta = client.post("/facturas", json={"id_paciente": 1, "lineas": []})

    assert respuesta.status_code == 401


def test_doctor_no_puede_crear_factura(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica)
    db_session.commit()

    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.DOCTOR)

    respuesta = client.post(
        "/facturas",
        headers=headers,
        json={
            "id_paciente": paciente.id_paciente,
            "lineas": [{"id_tratamiento": tratamiento.id_tratamiento, "cantidad": 1}],
        },
    )

    assert respuesta.status_code == 403


def test_asistente_crea_factura_suelta(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica, precio="40.00")
    db_session.commit()

    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.ASISTENTE)

    respuesta = client.post(
        "/facturas",
        headers=headers,
        json={
            "id_paciente": paciente.id_paciente,
            "lineas": [{"id_tratamiento": tratamiento.id_tratamiento, "cantidad": 2}],
        },
    )

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["numero_factura"] == "F000001"
    assert cuerpo["monto_subtotal"] == "80.00"


def test_generar_factura_desde_plan(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica, precio="100.00")
    plan, _, _ = crear_plan_aceptado_con_presupuesto(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor,
        tratamiento.id_tratamiento,
    )
    db_session.commit()

    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.ASISTENTE)

    respuesta = client.post(f"/planes-tratamiento/{plan.id_plan}/factura", headers=headers)

    assert respuesta.status_code == 201
    assert respuesta.json()["id_plan"] == plan.id_plan


def test_generar_factura_desde_plan_sin_presupuesto_aceptado_da_409(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    db_session.commit()

    from app.models import PlanTratamiento

    plan = PlanTratamiento(id_clinica=clinica.id_clinica, id_paciente=paciente.id_paciente, id_doctor=doctor.id_doctor)
    db_session.add(plan)
    db_session.commit()

    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.ASISTENTE)

    respuesta = client.post(f"/planes-tratamiento/{plan.id_plan}/factura", headers=headers)

    assert respuesta.status_code == 409


def test_doctor_solo_ve_sus_propias_facturas(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor_a = crear_doctor(db_session, clinica.id_clinica, username="dra.a")
    doctor_b = crear_doctor(db_session, clinica.id_clinica, username="dr.b")
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica, precio="20.00")
    db_session.commit()

    headers_asistente = headers_de(db_session, clinica.id_clinica, RolUsuario.ASISTENTE)
    client.post(
        "/facturas", headers=headers_asistente,
        json={
            "id_paciente": paciente.id_paciente, "id_doctor": doctor_a.id_doctor,
            "lineas": [{"id_tratamiento": tratamiento.id_tratamiento, "cantidad": 1}],
        },
    )
    creada_b = client.post(
        "/facturas", headers=headers_asistente,
        json={
            "id_paciente": paciente.id_paciente, "id_doctor": doctor_b.id_doctor,
            "lineas": [{"id_tratamiento": tratamiento.id_tratamiento, "cantidad": 1}],
        },
    ).json()

    from app.repositories.doctor_repository import DoctorRepository
    from app.security.jwt import create_access_token
    from datetime import timedelta

    perfil_b = DoctorRepository(db_session).obtener(clinica.id_clinica, doctor_b.id_doctor)
    token_doctor_b = create_access_token(
        data={"sub": str(perfil_b.id_usuario), "id_clinica": clinica.id_clinica, "rol": "doctor"},
        expires_delta=timedelta(minutes=10),
    )

    respuesta = client.get("/facturas", headers={"Authorization": f"Bearer {token_doctor_b}"})

    assert respuesta.status_code == 200
    numeros = [f["numero_factura"] for f in respuesta.json()]
    assert creada_b["numero_factura"] in numeros
    assert len(respuesta.json()) == 1


def test_anular_factura_sin_pagos(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica)
    db_session.commit()

    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.ASISTENTE)
    creada = client.post(
        "/facturas", headers=headers,
        json={
            "id_paciente": paciente.id_paciente,
            "lineas": [{"id_tratamiento": tratamiento.id_tratamiento, "cantidad": 1}],
        },
    ).json()

    respuesta = client.patch(f"/facturas/{creada['id_factura']}/anular", headers=headers)

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "anulada"


def test_registrar_pago_y_consultar_historial(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica, precio="100.00")
    metodo = crear_metodo_pago(db_session, clinica.id_clinica)
    db_session.commit()

    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.ASISTENTE)
    creada = client.post(
        "/facturas", headers=headers,
        json={
            "id_paciente": paciente.id_paciente,
            "lineas": [{"id_tratamiento": tratamiento.id_tratamiento, "cantidad": 1}],
        },
    ).json()

    pago = client.post(
        f"/facturas/{creada['id_factura']}/pagos", headers=headers,
        json={"id_metodo_pago": metodo.id_metodo_pago, "monto": "50.00"},
    )
    assert pago.status_code == 201

    historial = client.get(f"/facturas/{creada['id_factura']}/pagos", headers=headers)
    assert historial.status_code == 200
    assert len(historial.json()) == 1


def test_registrar_pago_que_excede_saldo_da_422(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica, precio="10.00")
    metodo = crear_metodo_pago(db_session, clinica.id_clinica)
    db_session.commit()

    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.ASISTENTE)
    creada = client.post(
        "/facturas", headers=headers,
        json={
            "id_paciente": paciente.id_paciente,
            "lineas": [{"id_tratamiento": tratamiento.id_tratamiento, "cantidad": 1}],
        },
    ).json()

    respuesta = client.post(
        f"/facturas/{creada['id_factura']}/pagos", headers=headers,
        json={"id_metodo_pago": metodo.id_metodo_pago, "monto": "9999.00"},
    )

    assert respuesta.status_code == 422
