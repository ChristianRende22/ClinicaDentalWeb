from tests.factories import crear_clinica, crear_doctor, crear_paciente, headers_de


def _crear(db):
    clinica = crear_clinica(db)
    paciente = crear_paciente(db, clinica.id_clinica)
    doctor = crear_doctor(db, clinica.id_clinica)
    db.commit()
    return clinica, paciente, doctor


def test_crear_consulta_camino_feliz(client, db_session):
    from app.models import RolUsuario

    clinica, paciente, doctor = _crear(db_session)
    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.DOCTOR)
    db_session.commit()

    resp = client.post(
        "/consultas",
        json={
            "id_paciente": paciente.id_paciente,
            "id_doctor": doctor.id_doctor,
            "fecha_hora": "2026-09-01T09:00:00",
            "motivo": "Dolor de muela",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["motivo"] == "Dolor de muela"


def test_asistente_no_puede_leer_o_escribir_es_falso_puede_ambos(client, db_session):
    """Tabla de permisos: asistente SI puede crear consultas (quien atiende
    registra), a diferencia de odontogramas.
    """
    from app.models import RolUsuario

    clinica, paciente, doctor = _crear(db_session)
    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.ASISTENTE)
    db_session.commit()

    resp = client.post(
        "/consultas",
        json={
            "id_paciente": paciente.id_paciente,
            "id_doctor": doctor.id_doctor,
            "fecha_hora": "2026-09-01T09:00:00",
        },
        headers=headers,
    )
    assert resp.status_code == 201


def test_crear_consulta_con_paciente_inexistente_da_422(client, db_session):
    from app.models import RolUsuario

    clinica, paciente, doctor = _crear(db_session)
    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.DOCTOR)
    db_session.commit()

    resp = client.post(
        "/consultas",
        json={"id_paciente": 9999, "id_doctor": doctor.id_doctor, "fecha_hora": "2026-09-01T09:00:00"},
        headers=headers,
    )
    assert resp.status_code == 422


def test_diagnostico_cuelga_de_una_consulta_existente(client, db_session):
    from app.models import RolUsuario

    clinica, paciente, doctor = _crear(db_session)
    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.DOCTOR)
    db_session.commit()

    resp = client.post(
        "/consultas",
        json={
            "id_paciente": paciente.id_paciente,
            "id_doctor": doctor.id_doctor,
            "fecha_hora": "2026-09-01T09:00:00",
        },
        headers=headers,
    )
    id_consulta = resp.json()["id_consulta"]

    resp = client.post(
        f"/consultas/{id_consulta}/diagnosticos",
        json={"descripcion": "Caries en molar", "pieza_numero": 8},
        headers=headers,
    )
    assert resp.status_code == 201

    resp = client.get(f"/consultas/{id_consulta}/diagnosticos", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_diagnostico_de_consulta_inexistente_da_404(client, db_session):
    from app.models import RolUsuario

    clinica, paciente, doctor = _crear(db_session)
    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.DOCTOR)
    db_session.commit()

    resp = client.post(
        "/consultas/9999/diagnosticos",
        json={"descripcion": "Caries"},
        headers=headers,
    )
    assert resp.status_code == 404


def test_aislamiento_entre_clinicas(client, db_session):
    from app.models import RolUsuario

    clinica_a, paciente_a, doctor_a = _crear(db_session)
    clinica_b = crear_clinica(db_session, nombre="B")
    db_session.commit()

    headers_a = headers_de(db_session, clinica_a.id_clinica, RolUsuario.DOCTOR)
    db_session.commit()
    resp = client.post(
        "/consultas",
        json={
            "id_paciente": paciente_a.id_paciente,
            "id_doctor": doctor_a.id_doctor,
            "fecha_hora": "2026-09-01T09:00:00",
        },
        headers=headers_a,
    )
    id_consulta = resp.json()["id_consulta"]

    headers_b = headers_de(db_session, clinica_b.id_clinica, RolUsuario.ADMIN)
    db_session.commit()
    resp = client.get(f"/consultas/{id_consulta}", headers=headers_b)
    assert resp.status_code == 404
