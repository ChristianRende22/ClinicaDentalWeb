from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base
from app.models.parametros import DiaSemana


class Paciente(Base):
    """Ficha de la persona que la clinica atiende. No tiene login: el paciente
    no opera el sistema, lo opera la clinica en su nombre.

    La edad NO se almacena: es un dato derivado de fecha_nacimiento y guardarla
    la vuelve mentira al dia siguiente del cumpleanos.
    """

    __tablename__ = "paciente"

    id_paciente: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_clinica: Mapped[int] = mapped_column(
        ForeignKey("clinica.id_clinica"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    apellido: Mapped[str] = mapped_column(String(50), nullable=False)
    fecha_nacimiento: Mapped[date | None] = mapped_column(Date, nullable=True)
    telefono: Mapped[str] = mapped_column(String(15), nullable=False)
    # varchar100 y no varchar25 como el legacy: el ERD as-is documenta que
    # varchar25 "trunca correos largos". Es un bug, no una convencion.
    correo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    direccion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Doctor(Base):
    """Perfil profesional. 1:1 con un Usuario de rol 'doctor': id_usuario es
    NOT NULL y unico, tal como lo define el ERD to-be.

    id_especialidad es nullable a proposito: una clinica recien creada no tiene
    el catalogo cargado, y exigirla bloquearia el alta del primer doctor.
    """

    __tablename__ = "doctor"
    __table_args__ = (
        UniqueConstraint("id_usuario", name="uq_doctor_usuario"),
    )

    id_doctor: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_clinica: Mapped[int] = mapped_column(
        ForeignKey("clinica.id_clinica"), nullable=False
    )
    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("usuario.id_usuario"), nullable=False
    )
    id_especialidad: Mapped[int | None] = mapped_column(
        ForeignKey("especialidad.id_especialidad"), nullable=True
    )
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    apellido: Mapped[str] = mapped_column(String(50), nullable=False)
    telefono: Mapped[str] = mapped_column(String(15), nullable=False)
    correo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")


class Asistente(Base):
    """Perfil del personal de recepcion. 1:1 con un Usuario de rol 'asistente'."""

    __tablename__ = "asistente"
    __table_args__ = (
        UniqueConstraint("id_usuario", name="uq_asistente_usuario"),
    )

    id_asistente: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_clinica: Mapped[int] = mapped_column(
        ForeignKey("clinica.id_clinica"), nullable=False
    )
    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("usuario.id_usuario"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    apellido: Mapped[str] = mapped_column(String(50), nullable=False)
    telefono: Mapped[str] = mapped_column(String(15), nullable=False)
    correo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")


class HorarioDoctor(Base):
    """Bloque de disponibilidad semanal de un doctor.

    A diferencia de HorarioClinica, tiene PK propia y NO llave compuesta
    (id_doctor, dia_semana): un doctor atiende de 08:00 a 12:00, almuerza, y
    vuelve de 14:00 a 18:00. Con llave compuesta eso seria imposible.

    No lleva id_clinica: la clinica se deduce del doctor, y duplicarla abriria
    la posibilidad de que las dos columnas se contradigan. El aislamiento lo
    garantiza el repositorio con un join contra Doctor.
    """

    __tablename__ = "horario_doctor"
    __table_args__ = (
        UniqueConstraint(
            "id_doctor", "dia_semana", "hora_inicio", name="uq_horario_doctor_dia_inicio"
        ),
    )

    id_horario: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_doctor: Mapped[int] = mapped_column(
        ForeignKey("doctor.id_doctor"), nullable=False
    )
    dia_semana: Mapped[DiaSemana] = mapped_column(
        SAEnum(
            DiaSemana,
            name="dia_semana",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
    )
    hora_inicio: Mapped[time] = mapped_column(Time, nullable=False)
    hora_fin: Mapped[time] = mapped_column(Time, nullable=False)
    disponible: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
