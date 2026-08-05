from tests.factories import crear_clinica, crear_doctor, crear_paciente, headers_de


def _base(db):
    clinica = crear_clinica(db)
    paciente = crear_paciente(db, clinica.id_clinica)
    doctor = crear_doctor(db, clinica.id_clinica)
    db.commit()
    return clinica, paciente, doctor


def test_crear_receta_camino_feliz(client, db_session):
    from app.models import RolUsuario

    clinica, paciente, doctor = _base(db_session)
    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.DOCTOR)
    db_session.commit()

    resp = client.post(
        "/recetas",
        json={
            "id_paciente": paciente.id_paciente,
            "id_doctor": doctor.id_doctor,
            "medicamentos": [
                {"medicamento": "Amoxicilina", "dosis": "500mg", "frecuencia": "cada 8 horas"}
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 201
    assert len(resp.json()["medicamentos"]) == 1


def test_asistente_no_puede_crear_receta(client, db_session):
    from app.models import RolUsuario

    clinica, paciente, doctor = _base(db_session)
    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.ASISTENTE)
    db_session.commit()

    resp = client.post(
        "/recetas",
        json={
            "id_paciente": paciente.id_paciente,
            "id_doctor": doctor.id_doctor,
            "medicamentos": [
                {"medicamento": "Amoxicilina", "dosis": "500mg", "frecuencia": "cada 8 horas"}
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 403
    # Pero si puede leerlas.
    resp = client.get("/recetas", headers=headers)
    assert resp.status_code == 200


def test_crear_receta_sin_medicamentos_da_422(client, db_session):
    from app.models import RolUsuario

    clinica, paciente, doctor = _base(db_session)
    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.DOCTOR)
    db_session.commit()

    resp = client.post(
        "/recetas",
        json={"id_paciente": paciente.id_paciente, "id_doctor": doctor.id_doctor, "medicamentos": []},
        headers=headers,
    )
    assert resp.status_code == 422


def test_aislamiento_entre_clinicas(client, db_session):
    from app.models import RolUsuario

    clinica_a, paciente_a, doctor_a = _base(db_session)
    clinica_b = crear_clinica(db_session, nombre="B")
    db_session.commit()

    headers_a = headers_de(db_session, clinica_a.id_clinica, RolUsuario.DOCTOR)
    db_session.commit()
    id_receta = client.post(
        "/recetas",
        json={
            "id_paciente": paciente_a.id_paciente,
            "id_doctor": doctor_a.id_doctor,
            "medicamentos": [
                {"medicamento": "Amoxicilina", "dosis": "500mg", "frecuencia": "cada 8 horas"}
            ],
        },
        headers=headers_a,
    ).json()["id_receta"]

    headers_b = headers_de(db_session, clinica_b.id_clinica, RolUsuario.ADMIN)
    db_session.commit()
    resp = client.get(f"/recetas/{id_receta}", headers=headers_b)
    assert resp.status_code == 404
