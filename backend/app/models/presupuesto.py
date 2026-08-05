import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Numeric, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class EstadoPresupuesto(str, enum.Enum):
    VIGENTE = "vigente"
    ACEPTADO = "aceptado"
    RECHAZADO = "rechazado"
    VENCIDO = "vencido"


#: 'vigente' es el unico estado no terminal: los otros tres se deciden una
#: vez (aceptar, rechazar, o marcarlo vencido) y no se revierten. Si el plan
#: cambia despues de aceptado, se genera un presupuesto nuevo desde cero via
#: PresupuestoService.generar_o_regenerar (decision 2 del spec), no se
#: reabre este.
TRANSICIONES_PRESUPUESTO_PERMITIDAS: dict[EstadoPresupuesto, set[EstadoPresupuesto]] = {
    EstadoPresupuesto.VIGENTE: {
        EstadoPresupuesto.ACEPTADO,
        EstadoPresupuesto.RECHAZADO,
        EstadoPresupuesto.VENCIDO,
    },
    EstadoPresupuesto.ACEPTADO: set(),
    EstadoPresupuesto.RECHAZADO: set(),
    EstadoPresupuesto.VENCIDO: set(),
}


class Presupuesto(Base):
    """1:1 con PlanTratamiento (decision 2 del spec): se regenera, no se
    versiona. generar_o_regenerar hace upsert sobre esta fila.
    """

    __tablename__ = "presupuesto"
    __table_args__ = (
        UniqueConstraint("id_plan", name="uq_presupuesto_plan"),
    )

    id_presupuesto: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_clinica: Mapped[int] = mapped_column(
        ForeignKey("clinica.id_clinica"), nullable=False
    )
    id_plan: Mapped[int] = mapped_column(
        ForeignKey("plan_tratamiento.id_plan"), nullable=False
    )
    monto_total: Mapped[str] = mapped_column(Numeric(10, 2), nullable=False)
    estado: Mapped[EstadoPresupuesto] = mapped_column(
        SAEnum(
            EstadoPresupuesto,
            name="estado_presupuesto",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        default=EstadoPresupuesto.VIGENTE,
        server_default="vigente",
        nullable=False,
    )
    fecha_emision: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
