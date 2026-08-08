from datetime import datetime

from tests.factories import crear_clinica, crear_cita, crear_doctor, crear_paciente


def test_resumen_por_estado_cuenta_por_estado_y_total(db_session):
    from app.repositories.cita_repository import CitaRepository

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    crear_cita(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor,
        fecha_hora=datetime(2026, 8, 5, 9, 0), estado="programada",
    )
    crear_cita(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor,
        fecha_hora=datetime(2026, 8, 6, 9, 0), estado="completada",
    )
    crear_cita(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor,
        fecha_hora=datetime(2026, 8, 7, 9, 0), estado="completada",
    )
    db_session.commit()

    resumen = CitaRepository(db_session).resumen_por_estado(clinica.id_clinica)

    assert resumen["total"] == 3
    assert resumen["por_estado"]["programada"] == 1
    assert resumen["por_estado"]["completada"] == 2
    assert resumen["por_estado"]["cancelada"] == 0


def test_resumen_por_estado_filtra_por_rango_de_fechas(db_session):
    from app.repositories.cita_repository import CitaRepository

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    crear_cita(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor,
        fecha_hora=datetime(2026, 7, 1, 9, 0), estado="completada",
    )
    crear_cita(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor,
        fecha_hora=datetime(2026, 8, 5, 9, 0), estado="completada",
    )
    db_session.commit()

    resumen = CitaRepository(db_session).resumen_por_estado(
        clinica.id_clinica, desde=datetime(2026, 8, 1), hasta=datetime(2026, 8, 31, 23, 59, 59),
    )

    assert resumen["total"] == 1


def test_resumen_por_estado_desglosa_por_doctor(db_session):
    from app.repositories.cita_repository import CitaRepository

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doc_a = crear_doctor(db_session, clinica.id_clinica, username="doc.a", nombre="Marta", apellido="Perez")
    doc_b = crear_doctor(db_session, clinica.id_clinica, username="doc.b", nombre="Luis", apellido="Gomez")
    crear_cita(
        db_session, clinica.id_clinica, paciente.id_paciente, doc_a.id_doctor,
        fecha_hora=datetime(2026, 8, 5, 9, 0), estado="completada",
    )
    crear_cita(
        db_session, clinica.id_clinica, paciente.id_paciente, doc_b.id_doctor,
        fecha_hora=datetime(2026, 8, 6, 9, 0), estado="programada",
    )
    db_session.commit()

    resumen = CitaRepository(db_session).resumen_por_estado(clinica.id_clinica)

    por_doctor = {fila["id_doctor"]: fila for fila in resumen["por_doctor"]}
    assert por_doctor[doc_a.id_doctor]["nombre"] == "Marta Perez"
    assert por_doctor[doc_a.id_doctor]["total"] == 1
    assert por_doctor[doc_a.id_doctor]["por_estado"]["completada"] == 1
    assert por_doctor[doc_b.id_doctor]["por_estado"]["programada"] == 1


def test_resumen_por_estado_sin_incluir_por_doctor(db_session):
    from app.repositories.cita_repository import CitaRepository

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    crear_cita(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor,
        fecha_hora=datetime(2026, 8, 5, 9, 0), estado="completada",
    )
    db_session.commit()

    resumen = CitaRepository(db_session).resumen_por_estado(
        clinica.id_clinica, incluir_por_doctor=False,
    )

    assert resumen["por_doctor"] == []


def test_resumen_por_estado_filtra_por_id_doctor(db_session):
    from app.repositories.cita_repository import CitaRepository

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

    resumen = CitaRepository(db_session).resumen_por_estado(
        clinica.id_clinica, id_doctor=doc_a.id_doctor,
    )

    assert resumen["total"] == 1


def test_resumen_por_estado_no_mezcla_clinicas(db_session):
    from app.repositories.cita_repository import CitaRepository

    clinica_a = crear_clinica(db_session, nombre="Dental A")
    clinica_b = crear_clinica(db_session, nombre="Dental B")
    paciente_a = crear_paciente(db_session, clinica_a.id_clinica)
    doctor_a = crear_doctor(db_session, clinica_a.id_clinica, username="doc.a")
    paciente_b = crear_paciente(db_session, clinica_b.id_clinica)
    doctor_b = crear_doctor(db_session, clinica_b.id_clinica, username="doc.b")
    crear_cita(
        db_session, clinica_a.id_clinica, paciente_a.id_paciente, doctor_a.id_doctor,
        fecha_hora=datetime(2026, 8, 5, 9, 0), estado="completada",
    )
    crear_cita(
        db_session, clinica_b.id_clinica, paciente_b.id_paciente, doctor_b.id_doctor,
        fecha_hora=datetime(2026, 8, 5, 9, 0), estado="completada",
    )
    db_session.commit()

    resumen = CitaRepository(db_session).resumen_por_estado(clinica_a.id_clinica)

    assert resumen["total"] == 1
