from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import RolUsuario, Usuario
from app.repositories.usuario_repository import UsuarioRepository
from app.security.jwt import TokenError, decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> Usuario:
    try:
        payload = decode_access_token(token)
    except TokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido o expirado",
        )

    id_usuario = int(payload["sub"])
    usuario = UsuarioRepository(db).obtener_por_id(id_usuario)
    if usuario is None or not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo",
        )
    return usuario


def require_roles(*roles: RolUsuario):
    def _dependency(usuario: Usuario = Depends(get_current_user)) -> Usuario:
        if usuario.rol not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tenes permiso para esta accion",
            )
        return usuario

    return _dependency


def resolve_clinica_id(
    usuario: Usuario = Depends(get_current_user),
    x_clinica_id: int | None = Header(default=None),
) -> int:
    if usuario.rol == RolUsuario.SUPERADMIN:
        if x_clinica_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un superadmin debe indicar X-Clinica-Id para operar sobre una clinica",
            )
        return x_clinica_id

    return usuario.id_clinica
