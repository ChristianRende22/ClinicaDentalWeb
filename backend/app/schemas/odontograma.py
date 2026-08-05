from datetime import datetime

from pydantic import BaseModel, Field

from app.models import EstadoPiezaDental


class PiezaDentalResponse(BaseModel):
    numero_pieza: int
    estado: EstadoPiezaDental
    observaciones: str | None
    actualizado_en: datetime | None = None

    model_config = {"from_attributes": True}


class PiezaDentalItemRequest(BaseModel):
    """Un item del body de PUT /pacientes/{id}/odontograma."""

    numero_pieza: int = Field(ge=1, le=32)
    estado: EstadoPiezaDental
    observaciones: str | None = Field(default=None, max_length=255)


class OdontogramaUpdateRequest(BaseModel):
    """Reemplaza SOLO las piezas incluidas (decision 4 del spec): a
    diferencia de HorarioSemanaRequest, esto no exige las 32.
    """

    piezas: list[PiezaDentalItemRequest] = Field(min_length=1)
