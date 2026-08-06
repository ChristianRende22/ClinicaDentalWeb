from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models import EstadoFactura


class LineaFacturaCreate(BaseModel):
    id_tratamiento: int = Field(gt=0)
    cantidad: int = Field(default=1, ge=1)


class FacturaCreate(BaseModel):
    id_paciente: int = Field(gt=0)
    id_doctor: int | None = None
    lineas: list[LineaFacturaCreate] = Field(min_length=1)


class FacturaDetalleResponse(BaseModel):
    id_detalle: int
    id_factura: int
    id_tratamiento: int
    cantidad: int
    precio_unitario: Decimal

    model_config = {"from_attributes": True}


class FacturaResponse(BaseModel):
    id_factura: int
    id_paciente: int
    id_doctor: int | None
    id_asistente: int | None
    id_plan: int | None
    numero_factura: str
    monto_subtotal: Decimal
    monto_impuesto: Decimal
    monto_total: Decimal
    estado: EstadoFactura
    fecha_emision: datetime

    model_config = {"from_attributes": True}


class PagoCreate(BaseModel):
    id_metodo_pago: int = Field(gt=0)
    monto: Decimal = Field(gt=0)


class PagoResponse(BaseModel):
    id_pago: int
    id_factura: int
    id_metodo_pago: int
    id_asistente: int | None
    monto: Decimal
    fecha_pago: datetime

    model_config = {"from_attributes": True}
