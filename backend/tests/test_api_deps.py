from datetime import timedelta

import pytest
from fastapi import HTTPException


def _crear_usuario_con_token(db_session, rol, id_clinica=None, username="user1"):
    from app.models import RolUsuario, Usuario
    from app.security.jwt import create_access_token
    from app.security.passwords import hash_password

    usuario = Usuario(
        id_clinica=id_clinica,
        username=username,
        password_hash=hash_password("clave123"),
        rol=rol,
    )
    db_session.add(usuario)
    db_session.commit()

    token = create_access_token(
        data={"sub": str(usuario.id_usuario), "id_clinica": id_clinica, "rol": rol.value},
        expires_delta=timedelta(minutes=10),
    )
    return usuario, token


def test_get_current_user_devuelve_el_usuario_del_token(db_session):
    from app.api.deps import get_current_user
    from app.models import RolUsuario

    usuario, token = _crear_usuario_con_token(db_session, RolUsuario.ADMIN, id_clinica=None)

    resultado = get_current_user(token=token, db=db_session)

    assert resultado.id_usuario == usuario.id_usuario


def test_get_current_user_con_token_invalido_lanza_401(db_session):
    from app.api.deps import get_current_user

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token="token-invalido", db=db_session)

    assert exc_info.value.status_code == 401


def test_require_roles_permite_rol_correcto(db_session):
    from app.api.deps import require_roles
    from app.models import RolUsuario

    usuario, _ = _crear_usuario_con_token(db_session, RolUsuario.SUPERADMIN)

    dependencia = require_roles(RolUsuario.SUPERADMIN)
    resultado = dependencia(usuario=usuario)

    assert resultado is usuario


def test_require_roles_rechaza_rol_incorrecto(db_session):
    from app.api.deps import require_roles
    from app.models import RolUsuario

    usuario, _ = _crear_usuario_con_token(db_session, RolUsuario.ASISTENTE)

    dependencia = require_roles(RolUsuario.SUPERADMIN)

    with pytest.raises(HTTPException) as exc_info:
        dependencia(usuario=usuario)

    assert exc_info.value.status_code == 403


def test_resolve_clinica_id_usuario_normal_usa_su_propia_clinica(db_session):
    from app.api.deps import resolve_clinica_id
    from app.models import RolUsuario

    usuario, _ = _crear_usuario_con_token(db_session, RolUsuario.ADMIN, id_clinica=7)

    assert resolve_clinica_id(usuario=usuario, x_clinica_id=99) == 7


def test_resolve_clinica_id_superadmin_requiere_header(db_session):
    from app.api.deps import resolve_clinica_id
    from app.models import RolUsuario

    usuario, _ = _crear_usuario_con_token(db_session, RolUsuario.SUPERADMIN)

    with pytest.raises(HTTPException) as exc_info:
        resolve_clinica_id(usuario=usuario, x_clinica_id=None)
    assert exc_info.value.status_code == 400

    assert resolve_clinica_id(usuario=usuario, x_clinica_id=3) == 3
