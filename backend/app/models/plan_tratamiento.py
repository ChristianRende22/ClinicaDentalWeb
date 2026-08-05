"""Plan de tratamiento: la entidad que dispara la politica de bajas del Modulo 5.

Ver la seccion 1 del spec del Modulo 5: un Paciente o un Doctor no se puede
dar de baja si tiene un PlanTratamiento en un estado no terminal. Por eso
TRANSICIONES_PLAN_PERMITIDAS existe (para saber que es "terminal") y por eso
PlanTratamientoRepository trae existe_plan_activo_de_paciente/_de_doctor.
"""
import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class EstadoPlanTratamiento(str, enum.Enum):
    BORRADOR = "borrador"
    APROBADO = "aprobado"
    EN_PROGRESO = "en_progreso"
    COMPLETADO = "completado"
    CANCELADO = "cancelado"


#: Igual formato que TRANSICIONES_PERMITIDAS de Cita: conjunto vacio = terminal.
#: 'cancelado' NO es alcanzable desde 'en_progreso' a proposito: un plan que ya
#: empezo a ejecutarse no se cancela entero de un tiro, se cancelan los
#: detalles que falten uno por uno (PlanTratamientoDetalle tiene su propia
#: maquina de estados, mas abajo). Bloquear esta transicion es lo que impide
#: que cancelar el plan borre en silencio el registro de lo que ya se hizo.
TRANSICIONES_PLAN_PERMITIDAS: dict[EstadoPlanTratamiento, set[EstadoPlanTratamiento]] = {
    EstadoPlanTratamiento.BORRADOR: {
        EstadoPlanTratamiento.APROBADO,
        EstadoPlanTratamiento.CANCELADO,
    },
    EstadoPlanTratamiento.APROBADO: {
        EstadoPlanTratamiento.EN_PROGRESO,
        EstadoPlanTratamiento.CANCELADO,
    },
    EstadoPlanTratamiento.EN_PROGRESO: {EstadoPlanTratamiento.COMPLETADO},
    EstadoPlanTratamiento.COMPLETADO: set(),
    EstadoPlanTratamiento.CANCELADO: set(),
}

#: Los estados que activan la politica de bajas (seccion 1 del spec): un plan
#: en cualquiera de estos tres bloquea dar de baja al paciente o al doctor
#: responsable. 'completado' y 'cancelado' no bloquean: son historial cerrado.
ESTADOS_PLAN_ACTIVOS: frozenset[EstadoPlanTratamiento] = frozenset(
    {
        EstadoPlanTratamiento.BORRADOR,
        EstadoPlanTratamiento.APROBADO,
        EstadoPlanTratamiento.EN_PROGRESO,
    }
)


class EstadoDetallePlanTratamiento(str, enum.Enum):
    PENDIENTE = "pendiente"
    EN_PROGRESO = "en_progreso"
    COMPLETADO = "completado"
    CANCELADO = "cancelado"


#: Maquina de estados propia del detalle, independiente de la del plan (ver
#: decision 6 del spec): un plan en_progreso normalmente tiene detalles en
#: varios estados no-cancelados a la vez.
TRANSICIONES_DETALLE_PERMITIDAS: dict[
    EstadoDetallePlanTratamiento, set[EstadoDetallePlanTratamiento]
] = {
    EstadoDetallePlanTratamiento.PENDIENTE: {
        EstadoDetallePlanTratamiento.EN_PROGRESO,
        EstadoDetallePlanTratamiento.CANCELADO,
    },
    EstadoDetallePlanTratamiento.EN_PROGRESO: {
        EstadoDetallePlanTratamiento.COMPLETADO,
        EstadoDetallePlanTratamiento.CANCELADO,
    },
    EstadoDetallePlanTratamiento.COMPLETADO: set(),
    EstadoDetallePlanTratamiento.CANCELADO: set(),
}

#: Los que SI cuentan para el total de un presupuesto y para bloquear la baja
#: de un Tratamiento del catalogo (seccion 1 del spec).
ESTADOS_DETALLE_ACTIVOS: frozenset[EstadoDetallePlanTratamiento] = frozenset(
    {EstadoDetallePlanTratamiento.PENDIENTE, EstadoDetallePlanTratamiento.EN_PROGRESO}
)


class PlanTratamiento(Base):
    __tablename__ = "plan_tratamiento"

    id_plan: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_clinica: Mapped[int] = mapped_column(
        ForeignKey("clinica.id_clinica"), nullable=False
    )
    id_paciente: Mapped[int] = mapped_column(
        ForeignKey("paciente.id_paciente"), nullable=False
    )
    id_doctor: Mapped[int] = mapped_column(
        ForeignKey("doctor.id_doctor"), nullable=False
    )
    estado: Mapped[EstadoPlanTratamiento] = mapped_column(
        SAEnum(
            EstadoPlanTratamiento,
            name="estado_plan_tratamiento",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        default=EstadoPlanTratamiento.BORRADOR,
        server_default="borrador",
        nullable=False,
    )
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PlanTratamientoDetalle(Base):
    """Una linea del plan: un tratamiento del catalogo, aplicado a una pieza
    (opcional) y con su precio congelado al momento de agregarse.
    """

    __tablename__ = "plan_tratamiento_detalle"

    id_detalle: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_plan: Mapped[int] = mapped_column(
        ForeignKey("plan_tratamiento.id_plan"), nullable=False
    )
    id_tratamiento: Mapped[int] = mapped_column(
        ForeignKey("tratamiento.id_tratamiento"), nullable=False
    )
    pieza_numero: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cantidad: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    #: Foto del precio de Tratamiento al momento de agregar este detalle. Ver
    #: decision 1 del spec: si el catalogo sube de precio despues, esta fila
    #: no se mueve.
    precio_unitario: Mapped[str] = mapped_column(Numeric(10, 2), nullable=False)
    estado: Mapped[EstadoDetallePlanTratamiento] = mapped_column(
        SAEnum(
            EstadoDetallePlanTratamiento,
            name="estado_detalle_plan_tratamiento",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        default=EstadoDetallePlanTratamiento.PENDIENTE,
        server_default="pendiente",
        nullable=False,
    )
    orden: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
