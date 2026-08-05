from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models import EstadoPresupuesto


class PresupuestoResponse(BaseModel):
    id_presupuesto: int
    id_plan: int
    monto_total: Decimal
    estado: EstadoPresupuesto
    fecha_emision: datetime
    notas: str | None

    model_config = {"from_attributes": True}


class CambiarEstadoPresupuestoRequest(BaseModel):
    estado: EstadoPresupuesto
