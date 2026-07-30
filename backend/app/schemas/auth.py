from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class UsuarioResponse(BaseModel):
    id_usuario: int
    username: str
    rol: str
    id_clinica: int | None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    usuario: UsuarioResponse
