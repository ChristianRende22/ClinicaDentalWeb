from pydantic import BaseModel, EmailStr

from app.models import EstadoClinica


class ClinicaCreateRequest(BaseModel):
    nombre: str
    direccion: str | None = None
    telefono: str | None = None
    correo: EmailStr | None = None
    admin_username: str


class ClinicaResponse(BaseModel):
    id_clinica: int
    nombre: str
    direccion: str | None
    telefono: str | None
    correo: str | None
    estado: EstadoClinica

    model_config = {"from_attributes": True}


class AdminCreadoResponse(BaseModel):
    id_usuario: int
    username: str

    model_config = {"from_attributes": True}


class ClinicaCreateResponse(BaseModel):
    clinica: ClinicaResponse
    admin: AdminCreadoResponse
    password_temporal: str


class ClinicaUpdateRequest(BaseModel):
    nombre: str | None = None
    direccion: str | None = None
    telefono: str | None = None
    correo: EmailStr | None = None


class EstadoUpdateRequest(BaseModel):
    estado: EstadoClinica


class ModuloUpdateRequest(BaseModel):
    habilitado: bool
