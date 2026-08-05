import re
from datetime import date, time

from pydantic import BaseModel, EmailStr, Field, computed_field, field_validator, model_validator

from app.models import DiaSemana
from app.schemas.comunes import no_nulo as _no_nulo
from app.schemas.comunes import texto_limpio as _texto_limpio

_SOLO_TELEFONO = re.compile(r"^[0-9+]{8,15}$")
_EDAD_MAXIMA = 120


def _telefono_limpio(valor: str) -> str:
    """Normaliza antes de validar: '7000-1122' y '7000 1122' son el mismo numero."""
    limpio = valor.replace(" ", "").replace("-", "")
    if not _SOLO_TELEFONO.match(limpio):
        raise ValueError("El telefono debe tener entre 8 y 15 digitos")
    return limpio


def _fecha_de_nacimiento_valida(valor: date | None) -> date | None:
    if valor is None:
        return None
    hoy = date.today()
    if valor > hoy:
        raise ValueError("La fecha de nacimiento no puede ser futura")
    if valor.year < hoy.year - _EDAD_MAXIMA:
        raise ValueError(f"La fecha de nacimiento no puede ser de hace mas de {_EDAD_MAXIMA} anos")
    return valor


class _DatosDePersona(BaseModel):
    """Campos comunes a paciente, doctor y asistente en los requests de alta."""

    nombre: str = Field(min_length=1, max_length=50)
    apellido: str = Field(min_length=1, max_length=50)
    telefono: str
    correo: EmailStr | None = Field(default=None, max_length=100)

    @field_validator("nombre", "apellido")
    @classmethod
    def _validar_texto(cls, valor: str) -> str:
        return _texto_limpio(valor)

    @field_validator("telefono")
    @classmethod
    def _validar_telefono(cls, valor: str) -> str:
        return _telefono_limpio(valor)


class PacienteCreate(_DatosDePersona):
    fecha_nacimiento: date | None = None
    direccion: str | None = Field(default=None, max_length=200)

    @field_validator("fecha_nacimiento")
    @classmethod
    def _validar_fecha(cls, valor: date | None) -> date | None:
        return _fecha_de_nacimiento_valida(valor)


class PacienteUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=50)
    apellido: str | None = Field(default=None, min_length=1, max_length=50)
    telefono: str | None = None
    correo: EmailStr | None = Field(default=None, max_length=100)
    fecha_nacimiento: date | None = None
    direccion: str | None = Field(default=None, max_length=200)
    activo: bool | None = None

    @field_validator("nombre", "apellido")
    @classmethod
    def _validar_texto(cls, valor: str | None) -> str:
        return _texto_limpio(_no_nulo(valor, "nombre/apellido"))

    @field_validator("telefono")
    @classmethod
    def _validar_telefono(cls, valor: str | None) -> str:
        return _telefono_limpio(_no_nulo(valor, "telefono"))

    @field_validator("fecha_nacimiento")
    @classmethod
    def _validar_fecha(cls, valor: date | None) -> date | None:
        return _fecha_de_nacimiento_valida(valor)

    @field_validator("activo")
    @classmethod
    def _validar_activo(cls, valor: bool | None) -> bool:
        return _no_nulo(valor, "activo")


class PacienteResponse(BaseModel):
    id_paciente: int
    nombre: str
    apellido: str
    fecha_nacimiento: date | None
    telefono: str
    correo: str | None
    direccion: str | None
    activo: bool

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def edad(self) -> int | None:
        """Derivada, nunca almacenada: guardarla la volveria mentira al dia
        siguiente del cumpleanos.
        """
        if self.fecha_nacimiento is None:
            return None
        hoy = date.today()
        return (
            hoy.year
            - self.fecha_nacimiento.year
            - ((hoy.month, hoy.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day))
        )


class DoctorCreate(_DatosDePersona):
    username: str = Field(min_length=3, max_length=30)
    id_especialidad: int | None = Field(default=None, gt=0)

    @field_validator("username")
    @classmethod
    def _validar_username(cls, valor: str) -> str:
        return _texto_limpio(valor)


class DoctorUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=50)
    apellido: str | None = Field(default=None, min_length=1, max_length=50)
    telefono: str | None = None
    correo: EmailStr | None = Field(default=None, max_length=100)
    id_especialidad: int | None = Field(default=None, gt=0)
    activo: bool | None = None

    @field_validator("nombre", "apellido")
    @classmethod
    def _validar_texto(cls, valor: str | None) -> str:
        return _texto_limpio(_no_nulo(valor, "nombre/apellido"))

    @field_validator("telefono")
    @classmethod
    def _validar_telefono(cls, valor: str | None) -> str:
        return _telefono_limpio(_no_nulo(valor, "telefono"))

    @field_validator("activo")
    @classmethod
    def _validar_activo(cls, valor: bool | None) -> bool:
        return _no_nulo(valor, "activo")


class DoctorResponse(BaseModel):
    id_doctor: int
    id_usuario: int
    id_especialidad: int | None
    nombre: str
    apellido: str
    telefono: str
    correo: str | None
    activo: bool

    model_config = {"from_attributes": True}


class DoctorCreateResponse(BaseModel):
    """La password temporal se expone UNA sola vez, aca. Ningun GET la devuelve."""

    doctor: DoctorResponse
    password_temporal: str


class AsistenteCreate(_DatosDePersona):
    username: str = Field(min_length=3, max_length=30)

    @field_validator("username")
    @classmethod
    def _validar_username(cls, valor: str) -> str:
        return _texto_limpio(valor)


class AsistenteUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=50)
    apellido: str | None = Field(default=None, min_length=1, max_length=50)
    telefono: str | None = None
    correo: EmailStr | None = Field(default=None, max_length=100)
    activo: bool | None = None

    @field_validator("nombre", "apellido")
    @classmethod
    def _validar_texto(cls, valor: str | None) -> str:
        return _texto_limpio(_no_nulo(valor, "nombre/apellido"))

    @field_validator("telefono")
    @classmethod
    def _validar_telefono(cls, valor: str | None) -> str:
        return _telefono_limpio(_no_nulo(valor, "telefono"))

    @field_validator("activo")
    @classmethod
    def _validar_activo(cls, valor: bool | None) -> bool:
        return _no_nulo(valor, "activo")


class AsistenteResponse(BaseModel):
    id_asistente: int
    id_usuario: int
    nombre: str
    apellido: str
    telefono: str
    correo: str | None
    activo: bool

    model_config = {"from_attributes": True}


class AsistenteCreateResponse(BaseModel):
    asistente: AsistenteResponse
    password_temporal: str


class BloqueHorarioSchema(BaseModel):
    dia_semana: DiaSemana
    hora_inicio: time
    hora_fin: time
    disponible: bool = True

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def _fin_posterior_al_inicio(self) -> "BloqueHorarioSchema":
        if self.hora_fin <= self.hora_inicio:
            raise ValueError("La hora de fin debe ser posterior a la de inicio")
        return self


class HorarioDoctorRequest(BaseModel):
    """Reemplaza el conjunto completo de bloques del doctor.

    Se edita y se valida como una unidad, por el mismo motivo que
    PUT /horarios del Modulo 3: asi no puede quedar en un estado intermedio
    (un bloque movido y el que le sigue no, solapandose).
    """

    bloques: list[BloqueHorarioSchema]
