from tests.factories import crear_clinica, headers_de


def test_crear_requiere_admin_o_superadmin(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    db_session.commit()

    headers_asistente = headers_de(db_session, clinica.id_clinica, RolUsuario.ASISTENTE)
    db_session.commit()
    resp = client.post(
        "/tratamientos",
        json={"nombre": "Limpieza", "precio": "25.00"},
        headers=headers_asistente,
    )
    assert resp.status_code == 403

    headers_admin = headers_de(db_session, clinica.id_clinica, RolUsuario.ADMIN)
    db_session.commit()
    resp = client.post(
        "/tratamientos", json={"nombre": "Limpieza", "precio": "25.00"}, headers=headers_admin
    )
    assert resp.status_code == 201


def test_los_cuatro_roles_pueden_leer(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    db_session.commit()
    headers_admin = headers_de(db_session, clinica.id_clinica, RolUsuario.ADMIN)
    db_session.commit()
    client.post(
        "/tratamientos", json={"nombre": "Limpieza", "precio": "25.00"}, headers=headers_admin
    )

    for rol in (RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.DOCTOR, RolUsuario.ASISTENTE):
        headers = headers_de(db_session, clinica.id_clinica, rol)
        db_session.commit()
        resp = client.get("/tratamientos", headers=headers)
        assert resp.status_code == 200, rol
        assert len(resp.json()) == 1


def test_dar_de_baja_en_uso_devuelve_409(client, db_session):
    from app.models import RolUsuario
    from tests.factories import crear_doctor, crear_paciente
    from tests.test_plan_tratamiento_models import crear_plan

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    db_session.commit()

    headers_admin = headers_de(db_session, clinica.id_clinica, RolUsuario.ADMIN)
    db_session.commit()
    resp = client.post(
        "/tratamientos", json={"nombre": "Limpieza", "precio": "25.00"}, headers=headers_admin
    )
    id_tratamiento = resp.json()["id_tratamiento"]

    plan = crear_plan(db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor)
    from app.repositories.plan_tratamiento_repository import PlanTratamientoDetalleRepository

    PlanTratamientoDetalleRepository(db_session).crear(
        plan.id_plan, {"id_tratamiento": id_tratamiento, "precio_unitario": "25.00"}
    )
    db_session.commit()

    resp = client.delete(f"/tratamientos/{id_tratamiento}", headers=headers_admin)
    assert resp.status_code == 409


def test_aislamiento_entre_clinicas(client, db_session):
    from app.models import RolUsuario

    clinica_a = crear_clinica(db_session, nombre="A")
    clinica_b = crear_clinica(db_session, nombre="B")
    db_session.commit()
    headers_admin_a = headers_de(db_session, clinica_a.id_clinica, RolUsuario.ADMIN)
    db_session.commit()
    resp = client.post(
        "/tratamientos", json={"nombre": "Limpieza", "precio": "25.00"}, headers=headers_admin_a
    )
    id_tratamiento = resp.json()["id_tratamiento"]

    headers_admin_b = headers_de(db_session, clinica_b.id_clinica, RolUsuario.ADMIN)
    db_session.commit()
    resp = client.get(f"/tratamientos/{id_tratamiento}", headers=headers_admin_b)
    assert resp.status_code == 404
