from tests.factories import crear_clinica, crear_doctor, crear_paciente, headers_de


def _crear_presupuesto(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    db_session.commit()
    headers_doctor = headers_de(db_session, clinica.id_clinica, RolUsuario.DOCTOR)
    headers_admin = headers_de(db_session, clinica.id_clinica, RolUsuario.ADMIN)
    db_session.commit()

    id_plan = client.post(
        "/planes-tratamiento",
        json={"id_paciente": paciente.id_paciente, "id_doctor": doctor.id_doctor},
        headers=headers_doctor,
    ).json()["id_plan"]
    resp = client.post(f"/planes-tratamiento/{id_plan}/presupuesto", headers=headers_admin)
    return clinica, resp.json(), headers_admin, headers_doctor


def test_cambiar_estado_camino_feliz(client, db_session):
    clinica, presupuesto, headers_admin, _ = _crear_presupuesto(client, db_session)

    resp = client.patch(
        f"/presupuestos/{presupuesto['id_presupuesto']}/estado",
        json={"estado": "aceptado"},
        headers=headers_admin,
    )
    assert resp.status_code == 200
    assert resp.json()["estado"] == "aceptado"


def test_transicion_invalida_da_409(client, db_session):
    clinica, presupuesto, headers_admin, _ = _crear_presupuesto(client, db_session)
    client.patch(
        f"/presupuestos/{presupuesto['id_presupuesto']}/estado",
        json={"estado": "aceptado"},
        headers=headers_admin,
    )
    resp = client.patch(
        f"/presupuestos/{presupuesto['id_presupuesto']}/estado",
        json={"estado": "rechazado"},
        headers=headers_admin,
    )
    assert resp.status_code == 409


def test_doctor_no_puede_cambiar_estado(client, db_session):
    clinica, presupuesto, _, headers_doctor = _crear_presupuesto(client, db_session)
    resp = client.patch(
        f"/presupuestos/{presupuesto['id_presupuesto']}/estado",
        json={"estado": "aceptado"},
        headers=headers_doctor,
    )
    assert resp.status_code == 403


def test_aislamiento_entre_clinicas(client, db_session):
    from app.models import RolUsuario

    clinica_a, presupuesto, _, _ = _crear_presupuesto(client, db_session)
    clinica_b = crear_clinica(db_session, nombre="B")
    db_session.commit()
    headers_b = headers_de(db_session, clinica_b.id_clinica, RolUsuario.ADMIN)
    db_session.commit()

    resp = client.get(f"/presupuestos/{presupuesto['id_presupuesto']}", headers=headers_b)
    assert resp.status_code == 404
