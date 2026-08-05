from tests.factories import crear_clinica, crear_doctor, crear_paciente, headers_de


def _base(db):
    clinica = crear_clinica(db)
    paciente = crear_paciente(db, clinica.id_clinica)
    doctor = crear_doctor(db, clinica.id_clinica)
    db.commit()
    return clinica, paciente, doctor


def test_crear_plan_y_agregar_detalle(client, db_session):
    from app.models import RolUsuario

    clinica, paciente, doctor = _base(db_session)
    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.DOCTOR)
    db_session.commit()

    resp = client.post(
        "/planes-tratamiento",
        json={"id_paciente": paciente.id_paciente, "id_doctor": doctor.id_doctor},
        headers=headers,
    )
    assert resp.status_code == 201
    id_plan = resp.json()["id_plan"]
    assert resp.json()["estado"] == "borrador"

    resp_admin = headers_de(db_session, clinica.id_clinica, RolUsuario.ADMIN)
    db_session.commit()
    resp = client.post(
        "/tratamientos", json={"nombre": "Limpieza", "precio": "25.00"}, headers=resp_admin
    )
    id_tratamiento = resp.json()["id_tratamiento"]

    resp = client.post(
        f"/planes-tratamiento/{id_plan}/detalles",
        json={"id_tratamiento": id_tratamiento, "cantidad": 2},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["precio_unitario"] == "25.00"

    resp = client.get(f"/planes-tratamiento/{id_plan}/detalles", headers=headers)
    assert len(resp.json()) == 1


def test_cambiar_estado_plan_en_progreso_no_cancela_de_un_tiro(client, db_session):
    from app.models import RolUsuario

    clinica, paciente, doctor = _base(db_session)
    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.DOCTOR)
    db_session.commit()
    id_plan = client.post(
        "/planes-tratamiento",
        json={"id_paciente": paciente.id_paciente, "id_doctor": doctor.id_doctor},
        headers=headers,
    ).json()["id_plan"]

    client.patch(f"/planes-tratamiento/{id_plan}/estado", json={"estado": "aprobado"}, headers=headers)
    client.patch(
        f"/planes-tratamiento/{id_plan}/estado", json={"estado": "en_progreso"}, headers=headers
    )
    resp = client.patch(
        f"/planes-tratamiento/{id_plan}/estado", json={"estado": "cancelado"}, headers=headers
    )
    assert resp.status_code == 409


def test_generar_presupuesto_dos_veces_actualiza_el_mismo(client, db_session):
    from app.models import RolUsuario

    clinica, paciente, doctor = _base(db_session)
    headers_doctor = headers_de(db_session, clinica.id_clinica, RolUsuario.DOCTOR)
    headers_admin = headers_de(db_session, clinica.id_clinica, RolUsuario.ADMIN)
    db_session.commit()

    id_plan = client.post(
        "/planes-tratamiento",
        json={"id_paciente": paciente.id_paciente, "id_doctor": doctor.id_doctor},
        headers=headers_doctor,
    ).json()["id_plan"]
    id_tratamiento = client.post(
        "/tratamientos", json={"nombre": "Limpieza", "precio": "25.00"}, headers=headers_admin
    ).json()["id_tratamiento"]
    client.post(
        f"/planes-tratamiento/{id_plan}/detalles",
        json={"id_tratamiento": id_tratamiento},
        headers=headers_doctor,
    )

    resp1 = client.post(f"/planes-tratamiento/{id_plan}/presupuesto", headers=headers_admin)
    assert resp1.status_code == 200
    assert resp1.json()["monto_total"] == "25.00"

    client.post(
        f"/planes-tratamiento/{id_plan}/detalles",
        json={"id_tratamiento": id_tratamiento},
        headers=headers_doctor,
    )
    resp2 = client.post(f"/planes-tratamiento/{id_plan}/presupuesto", headers=headers_admin)
    assert resp2.status_code == 200
    assert resp2.json()["id_presupuesto"] == resp1.json()["id_presupuesto"]
    assert resp2.json()["monto_total"] == "50.00"


def test_doctor_no_puede_generar_presupuesto(client, db_session):
    from app.models import RolUsuario

    clinica, paciente, doctor = _base(db_session)
    headers_doctor = headers_de(db_session, clinica.id_clinica, RolUsuario.DOCTOR)
    db_session.commit()
    id_plan = client.post(
        "/planes-tratamiento",
        json={"id_paciente": paciente.id_paciente, "id_doctor": doctor.id_doctor},
        headers=headers_doctor,
    ).json()["id_plan"]

    resp = client.post(f"/planes-tratamiento/{id_plan}/presupuesto", headers=headers_doctor)
    assert resp.status_code == 403


def test_aislamiento_entre_clinicas(client, db_session):
    from app.models import RolUsuario

    clinica_a, paciente_a, doctor_a = _base(db_session)
    clinica_b = crear_clinica(db_session, nombre="B")
    db_session.commit()

    headers_a = headers_de(db_session, clinica_a.id_clinica, RolUsuario.DOCTOR)
    db_session.commit()
    id_plan = client.post(
        "/planes-tratamiento",
        json={"id_paciente": paciente_a.id_paciente, "id_doctor": doctor_a.id_doctor},
        headers=headers_a,
    ).json()["id_plan"]

    headers_b = headers_de(db_session, clinica_b.id_clinica, RolUsuario.ADMIN)
    db_session.commit()
    resp = client.get(f"/planes-tratamiento/{id_plan}", headers=headers_b)
    assert resp.status_code == 404
