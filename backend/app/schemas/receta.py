from datetime import datetime

from pydantic import BaseModel, Field


class RecetaDetalleCreate(BaseModel):
    medicamento: str = Field(min_length=1, max_length=100)
    dosis: str = Field(min_length=1, max_length=50)
    frecuencia: str = Field(min_length=1, max_length=50)
    duracion: str | None = Field(default=None, max_length=50)
    indicaciones: str | None = Field(default=None, max_length=255)


class RecetaDetalleResponse(BaseModel):
    id_detalle: int
    medicamento: str
    dosis: str
    frecuencia: str
    duracion: str | None
    indicaciones: str | None

    model_config = {"from_attributes": True}


class RecetaCreate(BaseModel):
    id_paciente: int = Field(gt=0)
    id_doctor: int = Field(gt=0)
    id_consulta: int | None = Field(default=None, gt=0)
    indicaciones_generales: str | None = None
    #: Al menos un medicamento (min_length=1): espejo del chequeo que hace
    #: RecetaService.crear, cinturon y tirantes -- mismo criterio que
    #: _sin_zona_horaria en el schema de Cita del Modulo 4.
    medicamentos: list[RecetaDetalleCreate] = Field(min_length=1)


class RecetaResponse(BaseModel):
    id_receta: int
    id_paciente: int
    id_doctor: int
    id_consulta: int | None
    fecha_emision: datetime
    indicaciones_generales: str | None
    medicamentos: list[RecetaDetalleResponse] = []

    model_config = {"from_attributes": True}
