from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.comunes import texto_limpio


class ConsultaCreate(BaseModel):
    id_paciente: int = Field(gt=0)
    id_doctor: int = Field(gt=0)
    id_cita: int | None = Field(default=None, gt=0)
    fecha_hora: datetime
    motivo: str | None = Field(default=None, max_length=255)
    notas: str | None = None


class ConsultaUpdate(BaseModel):
    motivo: str | None = Field(default=None, max_length=255)
    notas: str | None = None


class ConsultaResponse(BaseModel):
    id_consulta: int
    id_paciente: int
    id_doctor: int
    id_cita: int | None
    fecha_hora: datetime
    motivo: str | None
    notas: str | None

    model_config = {"from_attributes": True}


class DiagnosticoCreate(BaseModel):
    descripcion: str = Field(min_length=1, max_length=255)
    pieza_numero: int | None = Field(default=None, ge=1, le=32)

    @field_validator("descripcion")
    @classmethod
    def _validar_descripcion(cls, valor: str) -> str:
        return texto_limpio(valor)


class DiagnosticoResponse(BaseModel):
    id_diagnostico: int
    id_consulta: int
    descripcion: str
    pieza_numero: int | None

    model_config = {"from_attributes": True}
