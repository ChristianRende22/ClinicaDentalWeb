from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db
from app.exceptions import ClinicaInactivaError, InvalidCredentialsError
from app.models import Usuario
from app.schemas.auth import LoginRequest, TokenResponse, UsuarioResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(credenciales: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        resultado = AuthService(db).login(credenciales.username, credenciales.password)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contrasena incorrectos",
        )
    except ClinicaInactivaError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La clinica de este usuario no esta activa",
        )
    return TokenResponse(
        access_token=resultado["access_token"],
        token_type=resultado["token_type"],
        usuario=UsuarioResponse.model_validate(resultado["usuario"]),
    )


@router.get("/me", response_model=UsuarioResponse)
def me(usuario: Usuario = Depends(get_current_user)) -> UsuarioResponse:
    return UsuarioResponse.model_validate(usuario)


@router.post("/logout")
def logout() -> dict:
    return {"detail": "Sesion cerrada"}
