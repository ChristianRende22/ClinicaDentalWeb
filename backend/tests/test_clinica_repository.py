def test_crear_y_obtener(db_session):
    from app.repositories.clinica_repository import ClinicaRepository

    repo = ClinicaRepository(db_session)
    clinica = repo.crear({"nombre": "Dental Uno"})
    db_session.commit()

    encontrada = repo.obtener(clinica.id_clinica)

    assert encontrada is not None
    assert encontrada.nombre == "Dental Uno"


def test_obtener_inexistente_devuelve_none(db_session):
    from app.repositories.clinica_repository import ClinicaRepository

    repo = ClinicaRepository(db_session)

    assert repo.obtener(999) is None


def test_listar_todas(db_session):
    from app.repositories.clinica_repository import ClinicaRepository

    repo = ClinicaRepository(db_session)
    repo.crear({"nombre": "Dental Uno"})
    repo.crear({"nombre": "Dental Dos"})
    db_session.commit()

    todas = repo.listar()

    assert len(todas) == 2


def test_listar_filtra_por_estado(db_session):
    from app.models import EstadoClinica
    from app.repositories.clinica_repository import ClinicaRepository

    repo = ClinicaRepository(db_session)
    activa = repo.crear({"nombre": "Dental Activa"})
    suspendida = repo.crear({"nombre": "Dental Suspendida", "estado": EstadoClinica.SUSPENDIDA})
    db_session.commit()

    solo_activas = repo.listar(EstadoClinica.ACTIVA)

    assert [c.id_clinica for c in solo_activas] == [activa.id_clinica]
    assert suspendida.id_clinica not in [c.id_clinica for c in solo_activas]


def test_actualizar_campos(db_session):
    from app.repositories.clinica_repository import ClinicaRepository

    repo = ClinicaRepository(db_session)
    clinica = repo.crear({"nombre": "Dental Original"})
    db_session.commit()

    actualizada = repo.actualizar(clinica.id_clinica, {"nombre": "Dental Renombrada"})
    db_session.commit()

    assert actualizada.nombre == "Dental Renombrada"


def test_cambiar_estado(db_session):
    from app.models import EstadoClinica
    from app.repositories.clinica_repository import ClinicaRepository

    repo = ClinicaRepository(db_session)
    clinica = repo.crear({"nombre": "Dental Uno"})
    db_session.commit()

    actualizada = repo.cambiar_estado(clinica.id_clinica, EstadoClinica.SUSPENDIDA)
    db_session.commit()

    assert actualizada.estado == EstadoClinica.SUSPENDIDA
