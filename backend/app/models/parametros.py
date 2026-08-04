import enum
from datetime import datetime, time

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class DiaSemana(str, enum.Enum):
    LUNES = "lunes"
    MARTES = "martes"
    MIERCOLES = "miercoles"
    JUEVES = "jueves"
    VIERNES = "viernes"
    SABADO = "sabado"
    DOMINGO = "domingo"


class Especialidad(Base):
    __tablename__ = "especialidad"
    __table_args__ = (
        UniqueConstraint("id_clinica", "nombre", name="uq_especialidad_clinica_nombre"),
    )

    id_especialidad: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_clinica: Mapped[int] = mapped_column(
        ForeignKey("clinica.id_clinica"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")


class Consultorio(Base):
    __tablename__ = "consultorio"
    __table_args__ = (
        UniqueConstraint("id_clinica", "nombre", name="uq_consultorio_clinica_nombre"),
    )

    id_consultorio: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_clinica: Mapped[int] = mapped_column(
        ForeignKey("clinica.id_clinica"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")


class MetodoPago(Base):
    __tablename__ = "metodo_pago"
    __table_args__ = (
        UniqueConstraint("id_clinica", "nombre", name="uq_metodo_pago_clinica_nombre"),
    )

    id_metodo_pago: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_clinica: Mapped[int] = mapped_column(
        ForeignKey("clinica.id_clinica"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")


class HorarioClinica(Base):
    """Horario de atencion de la clinica, una fila por dia de la semana.

    Llave compuesta (id_clinica, dia_semana): impide a nivel de esquema que
    existan dos filas para el mismo dia. Mismo criterio que ClinicaModulo.
    """

    __tablename__ = "horario_clinica"

    id_clinica: Mapped[int] = mapped_column(
        ForeignKey("clinica.id_clinica"), primary_key=True
    )
    dia_semana: Mapped[DiaSemana] = mapped_column(
        SAEnum(
            DiaSemana,
            name="dia_semana",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        primary_key=True,
    )
    hora_apertura: Mapped[time | None] = mapped_column(Time, nullable=True)
    hora_cierre: Mapped[time | None] = mapped_column(Time, nullable=True)
    cerrado: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")


class ConfiguracionClinica(Base):
    """Parametros escalares de una clinica. 1:1 con Clinica: id_clinica es PK y FK
    a la vez, asi que el esquema mismo impide dos configuraciones por clinica.
    """

    __tablename__ = "configuracion_clinica"

    id_clinica: Mapped[int] = mapped_column(
        ForeignKey("clinica.id_clinica"), primary_key=True
    )
    duracion_cita_minutos: Mapped[int] = mapped_column(
        Integer, default=30, server_default="30"
    )
    porcentaje_impuesto: Mapped[str] = mapped_column(
        Numeric(5, 2), default="13.00", server_default="13.00"
    )
    prefijo_factura: Mapped[str] = mapped_column(
        String(10), default="F", server_default="F"
    )
    proximo_numero_factura: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1"
    )
    horas_minimas_cambio_cita: Mapped[int] = mapped_column(
        Integer, default=24, server_default="24"
    )
    dias_minimos_reagendamiento: Mapped[int] = mapped_column(
        Integer, default=3, server_default="3"
    )
    #: Anticipacion minima para CREAR una cita nueva. Minimo 1 y no 0, igual que
    #: los otros dos parametros de cambio de cita: la regla es configurable en
    #: intensidad pero no desactivable. El default de 24 refleja la practica de
    #: las clinicas dentales salvadorenas, donde no se atiende sin cita previa.
    anticipacion_minima_reserva_horas: Mapped[int] = mapped_column(
        Integer, default=24, server_default="24"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


#: Unica fuente de verdad de los defaults del horario de atencion.
#: La usan la ruta GET /horarios (para rellenar dias sin fila) y los tests.
HORARIO_POR_DEFECTO: dict[DiaSemana, dict] = {
    DiaSemana.LUNES: {"hora_apertura": time(8, 0), "hora_cierre": time(17, 0), "cerrado": False},
    DiaSemana.MARTES: {"hora_apertura": time(8, 0), "hora_cierre": time(17, 0), "cerrado": False},
    DiaSemana.MIERCOLES: {
        "hora_apertura": time(8, 0),
        "hora_cierre": time(17, 0),
        "cerrado": False,
    },
    DiaSemana.JUEVES: {"hora_apertura": time(8, 0), "hora_cierre": time(17, 0), "cerrado": False},
    DiaSemana.VIERNES: {"hora_apertura": time(8, 0), "hora_cierre": time(17, 0), "cerrado": False},
    DiaSemana.SABADO: {"hora_apertura": None, "hora_cierre": None, "cerrado": True},
    DiaSemana.DOMINGO: {"hora_apertura": None, "hora_cierre": None, "cerrado": True},
}
