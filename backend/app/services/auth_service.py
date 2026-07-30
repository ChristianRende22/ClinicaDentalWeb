from datetime import timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.exceptions import ClinicaInactivaError, InvalidCredentialsError
from app.models import EstadoClinica, RolUsuario
from app.repositories.usuario_repository import UsuarioRepository
from app.security.jwt import create_access_token
from app.security.passwords import hash_password, verify_password


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.usuarios = UsuarioRepository(db)

    def login(self, username: str, password: str) -> dict:
        usuario = self.usuarios.obtener_por_username(username)
        if usuario is None or not usuario.activo:
            raise InvalidCredentialsError()
        if not verify_password(password, usuario.password_hash):
            raise InvalidCredentialsError()

        if usuario.rol != RolUsuario.SUPERADMIN:
            if usuario.clinica is None or usuario.clinica.estado != EstadoClinica.ACTIVA:
                raise ClinicaInactivaError()

        token = create_access_token(
            data={
                "sub": str(usuario.id_usuario),
                "id_clinica": usuario.id_clinica,
                "rol": usuario.rol.value,
            },
            expires_delta=timedelta(minutes=settings.jwt_expire_minutes),
        )
        return {
            "access_token": token,
            "token_type": "bearer",
            "usuario": usuario,
        }

    def cambiar_password(
        self, usuario, password_actual: str, password_nueva: str
    ) -> None:
        if not verify_password(password_actual, usuario.password_hash):
            raise InvalidCredentialsError()
        usuario.password_hash = hash_password(password_nueva)
        usuario.debe_cambiar_password = False
        self.db.commit()
