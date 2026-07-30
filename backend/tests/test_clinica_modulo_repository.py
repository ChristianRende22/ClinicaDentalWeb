def _crear_clinica(db_session, nombre="Dental Uno"):
    from app.models import Clinica

    clinica = Clinica(nombre=nombre)
    db_session.add(clinica)
    db_session.flush()
    return clinica


def test_sembrar_modulos_default_crea_8_filas_habilitadas(db_session):
    from app.repositories.clinica_modulo_repository import (
        MODULOS_DISPONIBLES,
        ClinicaModuloRepository,
    )

    clinica = _crear_clinica(db_session)
    repo = ClinicaModuloRepository(db_session)

    repo.sembrar_modulos_default(clinica.id_clinica)
    db_session.commit()

    modulos = repo.listar(clinica.id_clinica)

    assert len(modulos) == 8
    assert len(MODULOS_DISPONIBLES) == 8
    assert all(m.habilitado is True for m in modulos)
    assert {m.modulo for m in modulos} == set(MODULOS_DISPONIBLES)


def test_listar_solo_los_de_esa_clinica(db_session):
    from app.repositories.clinica_modulo_repository import ClinicaModuloRepository

    clinica_a = _crear_clinica(db_session, "Dental A")
    clinica_b = _crear_clinica(db_session, "Dental B")
    repo = ClinicaModuloRepository(db_session)

    repo.sembrar_modulos_default(clinica_a.id_clinica)
    repo.sembrar_modulos_default(clinica_b.id_clinica)
    db_session.commit()

    modulos_a = repo.listar(clinica_a.id_clinica)

    assert len(modulos_a) == 8
    assert all(m.id_clinica == clinica_a.id_clinica for m in modulos_a)


def test_actualizar_estado_deshabilita_modulo(db_session):
    from app.repositories.clinica_modulo_repository import ClinicaModuloRepository

    clinica = _crear_clinica(db_session)
    repo = ClinicaModuloRepository(db_session)
    repo.sembrar_modulos_default(clinica.id_clinica)
    db_session.commit()

    actualizado = repo.actualizar_estado(clinica.id_clinica, "recetas", False)
    db_session.commit()

    assert actualizado.habilitado is False


def test_actualizar_estado_modulo_inexistente_devuelve_none(db_session):
    from app.repositories.clinica_modulo_repository import ClinicaModuloRepository

    clinica = _crear_clinica(db_session)
    repo = ClinicaModuloRepository(db_session)

    assert repo.actualizar_estado(clinica.id_clinica, "no-existe", False) is None
