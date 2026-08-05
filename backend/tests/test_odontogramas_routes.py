from tests.factories import crear_clinica, crear_paciente, headers_de


def test_get_crea_al_vuelo_y_devuelve_32(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    db_session.commit()
    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.DOCTOR)
    db_session.commit()

    resp = client.get(f"/pacientes/{paciente.id_paciente}/odontograma", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 32


def test_asistente_no_puede_escribir_pero_si_leer(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    db_session.commit()
    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.ASISTENTE)
    db_session.commit()

    resp = client.get(f"/pacientes/{paciente.id_paciente}/odontograma", headers=headers)
    assert resp.status_code == 200

    resp = client.put(
        f"/pacientes/{paciente.id_paciente}/odontograma",
        json={"piezas": [{"numero_pieza": 8, "estado": "cariado"}]},
        headers=headers,
    )
    assert resp.status_code == 403


def test_put_parcial_no_toca_las_demas_piezas(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    db_session.commit()
    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.DOCTOR)
    db_session.commit()

    resp = client.put(
        f"/pacientes/{paciente.id_paciente}/odontograma",
        json={"piezas": [{"numero_pieza": 8, "estado": "cariado"}]},
        headers=headers,
    )
    assert resp.status_code == 200
    piezas = resp.json()
    pieza_8 = next(p for p in piezas if p["numero_pieza"] == 8)
    assert pieza_8["estado"] == "cariado"
    otras = [p for p in piezas if p["numero_pieza"] != 8]
    assert all(p["estado"] == "sano" for p in otras)


def test_paciente_inexistente_da_404(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    db_session.commit()
    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.DOCTOR)
    db_session.commit()

    resp = client.get("/pacientes/9999/odontograma", headers=headers)
    assert resp.status_code == 404


def test_aislamiento_entre_clinicas(client, db_session):
    from app.models import RolUsuario

    clinica_a = crear_clinica(db_session, nombre="A")
    clinica_b = crear_clinica(db_session, nombre="B")
    paciente_a = crear_paciente(db_session, clinica_a.id_clinica)
    db_session.commit()

    headers_b = headers_de(db_session, clinica_b.id_clinica, RolUsuario.DOCTOR)
    db_session.commit()
    resp = client.get(f"/pacientes/{paciente_a.id_paciente}/odontograma", headers=headers_b)
    assert resp.status_code == 404
