from datetime import time
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.models import DiaSemana


def _nombre_limpio(valor: str) -> str:
    limpio = valor.strip()
    if not limpio:
        raise ValueError("El nombre no puede estar vacio")
    return limpio


class CatalogoCreateRequest(BaseModel):
    """Contrato de entrada compartido por Especialidad, Consultorio y MetodoPago."""

    nombre: str = Field(min_length=1, max_length=50)

    @field_validator("nombre")
    @classmethod
    def _validar_nombre(cls, valor: str) -> str:
        return _nombre_limpio(valor)


class CatalogoUpdateRequest(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=50)
    activo: bool | None = None

    @field_validator("nombre")
    @classmethod
    def _validar_nombre(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return _nombre_limpio(valor)


class EspecialidadResponse(BaseModel):
    id_especialidad: int
    nombre: str
    activo: bool

    model_config = {"from_attributes": True}


class ConsultorioResponse(BaseModel):
    id_consultorio: int
    nombre: str
    activo: bool

    model_config = {"from_attributes": True}


class MetodoPagoResponse(BaseModel):
    id_metodo_pago: int
    nombre: str
    activo: bool

    model_config = {"from_attributes": True}


class HorarioDiaSchema(BaseModel):
    dia_semana: DiaSemana
    hora_apertura: time | None = None
    hora_cierre: time | None = None
    cerrado: bool = False

    model_config = {"from_attributes": True}


class HorarioSemanaRequest(BaseModel):
    dias: list[HorarioDiaSchema]

    @field_validator("dias")
    @classmethod
    def _deben_ser_los_siete_dias(cls, valor: list[HorarioDiaSchema]) -> list[HorarioDiaSchema]:
        recibidos = [dia.dia_semana for dia in valor]
        if len(recibidos) != len(set(recibidos)) or set(recibidos) != set(DiaSemana):
            raise ValueError("Hay que enviar exactamente los 7 dias de la semana, sin repetidos")
        return valor


class ConfiguracionResponse(BaseModel):
    duracion_cita_minutos: int
    porcentaje_impuesto: Decimal
    prefijo_factura: str
    proximo_numero_factura: int
    horas_minimas_cambio_cita: int
    dias_minimos_reagendamiento: int

    model_config = {"from_attributes": True}


class ConfiguracionUpdateRequest(BaseModel):
    """Actualizacion parcial: solo se aplican los campos presentes en el body.

    Los minimos de horas_minimas_cambio_cita y dias_minimos_reagendamiento son 1
    y no 0 a proposito: la regla es configurable en intensidad, pero no se puede
    desactivar.
    """

    duracion_cita_minutos: int | None = Field(default=None, ge=5, le=480)
    porcentaje_impuesto: Decimal | None = Field(default=None, ge=0, le=100)
    prefijo_factura: str | None = Field(default=None, max_length=10)
    proximo_numero_factura: int | None = Field(default=None, ge=1)
    horas_minimas_cambio_cita: int | None = Field(default=None, ge=1, le=720)
    dias_minimos_reagendamiento: int | None = Field(default=None, ge=1, le=90)
