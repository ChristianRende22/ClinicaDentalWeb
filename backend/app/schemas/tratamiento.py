from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.schemas.comunes import no_nulo as _no_nulo
from app.schemas.comunes import texto_limpio as _texto_limpio


class TratamientoCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    descripcion: str | None = Field(default=None, max_length=255)
    precio: Decimal = Field(gt=0)
    duracion_minutos_estimada: int | None = Field(default=None, ge=1, le=1440)

    @field_validator("nombre")
    @classmethod
    def _validar_nombre(cls, valor: str) -> str:
        return _texto_limpio(valor)


class TratamientoUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    descripcion: str | None = Field(default=None, max_length=255)
    precio: Decimal | None = Field(default=None, gt=0)
    duracion_minutos_estimada: int | None = Field(default=None, ge=1, le=1440)
    activo: bool | None = None

    @field_validator("nombre")
    @classmethod
    def _validar_nombre(cls, valor: str | None) -> str:
        return _texto_limpio(_no_nulo(valor, "nombre"))

    @field_validator("precio")
    @classmethod
    def _validar_precio(cls, valor: Decimal | None) -> Decimal:
        return _no_nulo(valor, "precio")

    @field_validator("activo")
    @classmethod
    def _validar_activo(cls, valor: bool | None) -> bool:
        return _no_nulo(valor, "activo")


class TratamientoResponse(BaseModel):
    id_tratamiento: int
    nombre: str
    descripcion: str | None
    precio: Decimal
    duracion_minutos_estimada: int | None
    activo: bool

    model_config = {"from_attributes": True}
