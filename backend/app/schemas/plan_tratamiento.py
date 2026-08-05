from decimal import Decimal

from pydantic import BaseModel, Field

from app.models import EstadoDetallePlanTratamiento, EstadoPlanTratamiento


class PlanTratamientoCreate(BaseModel):
    id_paciente: int = Field(gt=0)
    id_doctor: int = Field(gt=0)
    notas: str | None = None


class PlanTratamientoResponse(BaseModel):
    id_plan: int
    id_paciente: int
    id_doctor: int
    estado: EstadoPlanTratamiento
    notas: str | None

    model_config = {"from_attributes": True}


class CambiarEstadoPlanRequest(BaseModel):
    estado: EstadoPlanTratamiento


class DetalleCreate(BaseModel):
    id_tratamiento: int = Field(gt=0)
    pieza_numero: int | None = Field(default=None, ge=1, le=32)
    cantidad: int = Field(default=1, ge=1)
    orden: int = Field(default=0, ge=0)


class DetalleResponse(BaseModel):
    id_detalle: int
    id_plan: int
    id_tratamiento: int
    pieza_numero: int | None
    cantidad: int
    precio_unitario: Decimal
    estado: EstadoDetallePlanTratamiento
    orden: int

    model_config = {"from_attributes": True}


class CambiarEstadoDetalleRequest(BaseModel):
    estado: EstadoDetallePlanTratamiento
