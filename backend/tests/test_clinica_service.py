import pytest


def test_crear_clinica_con_admin_devuelve_todo(db_session):
    from app.services.clinica_service import ClinicaService

    resultado = ClinicaService(db_session).crear_clinica_con_admin(
        nombre="Dental Smiling", admin_username="admin.dentalsmiling"
    )

    assert resultado["clinica"].nombre == "Dental Smiling"
    assert resultado["admin"].username == "admin.dentalsmiling"
    assert resultado["admin"].debe_cambiar_password is True
    assert isinstance(resultado["password_temporal"], str)
    assert len(resultado["password_temporal"]) >= 12


def test_crear_clinica_con_admin_siembra_8_modulos_habilitados(db_session):
    from app.repositories.clinica_modulo_repository import ClinicaModuloRepository
    from app.services.clinica_service import ClinicaService

    resultado = ClinicaService(db_session).crear_clinica_con_admin(
        nombre="Dental Smiling", admin_username="admin.dentalsmiling"
    )

    modulos = ClinicaModuloRepository(db_session).listar(resultado["clinica"].id_clinica)

    assert len(modulos) == 8
    assert all(m.habilitado is True for m in modulos)


def test_crear_clinica_con_admin_password_es_verificable(db_session):
    from app.security.passwords import verify_password
    from app.services.clinica_service import ClinicaService

    resultado = ClinicaService(db_session).crear_clinica_con_admin(
        nombre="Dental Smiling", admin_username="admin.dentalsmiling"
    )

    assert verify_password(resultado["password_temporal"], resultado["admin"].password_hash)


def test_crear_clinica_con_admin_username_duplicado_lanza_error(db_session):
    from app.exceptions import UsernameYaExisteError
    from app.services.clinica_service import ClinicaService

    ClinicaService(db_session).crear_clinica_con_admin(
        nombre="Dental Uno", admin_username="admin.repetido"
    )

    with pytest.raises(UsernameYaExisteError):
        ClinicaService(db_session).crear_clinica_con_admin(
            nombre="Dental Dos", admin_username="admin.repetido"
        )


def test_crear_clinica_con_admin_hace_rollback_si_falla(db_session, monkeypatch):
    from app.repositories.clinica_repository import ClinicaRepository
    import app.services.clinica_service as clinica_service_module

    def _falla(*args, **kwargs):
        raise RuntimeError("fallo simulado")

    monkeypatch.setattr(clinica_service_module, "generar_password_temporal", _falla)

    with pytest.raises(RuntimeError):
        clinica_service_module.ClinicaService(db_session).crear_clinica_con_admin(
            nombre="Dental Que No Debe Quedar", admin_username="admin.fallido"
        )

    assert ClinicaRepository(db_session).listar() == []
