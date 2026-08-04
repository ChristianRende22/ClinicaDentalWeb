from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models import EstadoCita


def _sin_zona_horaria(valor: datetime) -> datetime:
    """Rechaza fechas con offset.

    Toda la aplicacion trabaja con datetime naive en hora local de la clinica:
    la columna Cita.fecha_hora es DateTime sin zona y CitaService compara contra
    datetime.now(). Aceptar una fecha con offset haria que la comparacion lance
    TypeError y la ruta devuelva 500 en vez de 422, y persistiria un valor
    inconsistente entre SQLite y MySQL. Se rechaza en el borde, que es donde el
    error todavia se puede reportar bien.
    """
    if valor.tzinfo is not None:
        raise ValueError(
            "La fecha y hora debe ir sin zona horaria, en hora local de la clinica"
        )
    return valor


class CitaCreate(BaseModel):
    """Las reglas de negocio (pasado, anticipacion, horario, choques) NO se
    validan aca: dependen de la configuracion de la clinica y de la base, y
    viven en los validadores. El schema solo valida la forma del request.

    id_asistente no esta en el body a proposito: sale del usuario autenticado.
    """

    id_paciente: int = Field(gt=0)
    id_doctor: int = Field(gt=0)
    id_consultorio: int | None = Field(default=None, gt=0)
    fecha_hora: datetime
    # El tope de 480 esta acoplado a DURACION_MAXIMA_MINUTOS de
    # cita_repository.py: el prefiltro de solapamiento asume que ninguna cita
    # dura mas que eso. Si se sube uno, hay que subir el otro.
    duracion_minutos: int | None = Field(default=None, ge=5, le=480)
    motivo: str | None = Field(default=None, max_length=255)

    @field_validator("fecha_hora")
    @classmethod
    def _validar_fecha_hora(cls, valor: datetime) -> datetime:
        return _sin_zona_horaria(valor)


class CitaResponse(BaseModel):
    id_cita: int
    id_paciente: int
    id_doctor: int
    id_consultorio: int | None
    id_asistente: int | None
    fecha_hora: datetime
    duracion_minutos: int
    estado: EstadoCita
    motivo: str | None
    veces_reagendada: int

    model_config = {"from_attributes": True}


class CambiarEstadoRequest(BaseModel):
    estado: EstadoCita


class ReagendarRequest(BaseModel):
    fecha_hora: datetime
    id_consultorio: int | None = Field(default=None, gt=0)

    @field_validator("fecha_hora")
    @classmethod
    def _validar_fecha_hora(cls, valor: datetime) -> datetime:
        return _sin_zona_horaria(valor)
