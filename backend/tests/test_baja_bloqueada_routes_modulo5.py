"""Regresion a nivel de ruta para la politica de bajas del Modulo 5.

Estos tests existian ya a nivel de repositorio/servicio
(test_paciente_repository_baja_modulo5.py, test_personal_service_baja_modulo5.py),
pero ninguno pasaba por las rutas reales. Una revision de codigo encontro que
DELETE /pacientes/{id}, PUT /pacientes/{id} con activo:false, y el equivalente
en /doctores no capturaban ReferenciaEnUsoError -- el PUT de pacientes ni
siquiera llegaba a lanzarla, porque pasaba por actualizar() en vez de
eliminar(). Sin esto, dar de baja a alguien con un plan de tratamiento activo
devolvia 500 (DELETE) o aplicaba la baja igual, sin bloquear nada (PUT).
"""
from tests.factories import crear_clinica, crear_doctor, crear_paciente, headers_de
from tests.test_plan_tratamiento_models import crear_plan


def _base_con_plan_activo(db):
    from app.models import EstadoPlanTratamiento, RolUsuario

    clinica = crear_clinica(db)
    paciente = crear_paciente(db, clinica.id_clinica)
    doctor = crear_doctor(db, clinica.id_clinica)
    crear_plan(
        db, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor,
        estado=EstadoPlanTratamiento.APROBADO,
    )
    db.commit()
    headers_admin = headers_de(db, clinica.id_clinica, RolUsuario.ADMIN)
    db.commit()
    return clinica, paciente, doctor, headers_admin


def test_delete_paciente_con_plan_activo_da_409(client, db_session):
    clinica, paciente, doctor, headers_admin = _base_con_plan_activo(db_session)

    resp = client.delete(f"/pacientes/{paciente.id_paciente}", headers=headers_admin)
    assert resp.status_code == 409


def test_put_activo_false_en_paciente_con_plan_activo_da_409(client, db_session):
    clinica, paciente, doctor, headers_admin = _base_con_plan_activo(db_session)

    resp = client.put(
        f"/pacientes/{paciente.id_paciente}",
        json={"activo": False},
        headers=headers_admin,
    )
    assert resp.status_code == 409

    # Y el paciente sigue activo: el intento no aplico la baja a medias.
    resp = client.get(f"/pacientes/{paciente.id_paciente}", headers=headers_admin)
    assert resp.json()["activo"] is True


def test_delete_doctor_con_plan_activo_da_409(client, db_session):
    clinica, paciente, doctor, headers_admin = _base_con_plan_activo(db_session)

    resp = client.delete(f"/doctores/{doctor.id_doctor}", headers=headers_admin)
    assert resp.status_code == 409


def test_put_activo_false_en_doctor_con_plan_activo_da_409(client, db_session):
    clinica, paciente, doctor, headers_admin = _base_con_plan_activo(db_session)

    resp = client.put(
        f"/doctores/{doctor.id_doctor}",
        json={"activo": False},
        headers=headers_admin,
    )
    assert resp.status_code == 409

    resp = client.get(f"/doctores/{doctor.id_doctor}", headers=headers_admin)
    assert resp.json()["activo"] is True


def test_delete_paciente_sin_plan_activo_sigue_dando_204(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    db_session.commit()
    headers_admin = headers_de(db_session, clinica.id_clinica, RolUsuario.ADMIN)
    db_session.commit()

    resp = client.delete(f"/pacientes/{paciente.id_paciente}", headers=headers_admin)
    assert resp.status_code == 204
