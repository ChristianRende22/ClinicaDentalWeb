import pytest


def _crear_clinica_activa(db_session):
    from app.models import Clinica

    clinica = Clinica(nombre="Dental Smiling")
    db_session.add(clinica)
    db_session.flush()
    return clinica


def _crear_usuario(db_session, clinica, username, rol, password="clave123"):
    from app.models import Usuario
    from app.security.passwords import hash_password

    usuario = Usuario(
        id_clinica=clinica.id_clinica if clinica else None,
        username=username,
        password_hash=hash_password(password),
        rol=rol,
    )
    db_session.add(usuario)
    db_session.commit()
    return usuario


def test_login_exitoso_devuelve_token_y_usuario(db_session):
    from app.models import RolUsuario
    from app.services.auth_service import AuthService

    clinica = _crear_clinica_activa(db_session)
    _crear_usuario(db_session, clinica, "admin.dental", RolUsuario.ADMIN)

    resultado = AuthService(db_session).login("admin.dental", "clave123")

    assert resultado["token_type"] == "bearer"
    assert resultado["usuario"].username == "admin.dental"
    assert isinstance(resultado["access_token"], str) and len(resultado["access_token"]) > 0


def test_login_con_password_incorrecta_lanza_invalid_credentials(db_session):
    from app.exceptions import InvalidCredentialsError
    from app.models import RolUsuario
    from app.services.auth_service import AuthService

    clinica = _crear_clinica_activa(db_session)
    _crear_usuario(db_session, clinica, "admin.dental", RolUsuario.ADMIN)

    with pytest.raises(InvalidCredentialsError):
        AuthService(db_session).login("admin.dental", "clave-equivocada")


def test_login_usuario_inexistente_lanza_invalid_credentials(db_session):
    from app.exceptions import InvalidCredentialsError
    from app.services.auth_service import AuthService

    with pytest.raises(InvalidCredentialsError):
        AuthService(db_session).login("no-existe", "cualquier-clave")


def test_login_con_clinica_suspendida_lanza_clinica_inactiva(db_session):
    from app.exceptions import ClinicaInactivaError
    from app.models import EstadoClinica, RolUsuario
    from app.services.auth_service import AuthService

    clinica = _crear_clinica_activa(db_session)
    clinica.estado = EstadoClinica.SUSPENDIDA
    db_session.commit()
    _crear_usuario(db_session, clinica, "admin.dental", RolUsuario.ADMIN)

    with pytest.raises(ClinicaInactivaError):
        AuthService(db_session).login("admin.dental", "clave123")


def test_login_superadmin_no_requiere_clinica_activa(db_session):
    from app.models import RolUsuario
    from app.services.auth_service import AuthService

    _crear_usuario(db_session, None, "superadmin", RolUsuario.SUPERADMIN)

    resultado = AuthService(db_session).login("superadmin", "clave123")

    assert resultado["usuario"].rol == RolUsuario.SUPERADMIN
