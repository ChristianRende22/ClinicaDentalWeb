import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class EstadoFactura(str, enum.Enum):
    PENDIENTE = "pendiente"
    PARCIAL = "parcial"
    PAGADA = "pagada"
    ANULADA = "anulada"


class Factura(Base):
    """Factura interna de la clinica -- NO es un Documento Tributario
    Electronico (DTE). numero_factura es un correlativo propio de
    ConfiguracionClinica (prefijo_factura + proximo_numero_factura, Modulo 3),
    no un codigo de generacion de Hacienda. Ver seccion 2 del spec del
    Modulo 6: un modulo futuro de facturacion electronica puede agregar esos
    campos (codigo_generacion, sello_recibido, etc.) con una migracion nueva
    de columnas nullable, sin romper nada de esto.

    monto_subtotal/monto_impuesto/monto_total se calculan y se CONGELAN al
    emitir -- misma foto-del-momento que Cita.duracion_minutos (Modulo 4) y
    PlanTratamientoDetalle.precio_unitario (Modulo 5): si el % de impuesto de
    la clinica cambia despues, las facturas ya emitidas no se mueven.
    """

    __tablename__ = "factura"
    __table_args__ = (
        UniqueConstraint("id_clinica", "numero_factura", name="uq_factura_clinica_numero"),
    )

    id_factura: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_clinica: Mapped[int] = mapped_column(ForeignKey("clinica.id_clinica"), nullable=False)
    id_paciente: Mapped[int] = mapped_column(ForeignKey("paciente.id_paciente"), nullable=False)
    #: Nullable: nulo en un cargo administrativo suelto sin tratamiento clinico
    #: asociado. Cuando tiene valor, es el filtro de "solo mis facturas" del
    #: doctor (ver GET /facturas).
    id_doctor: Mapped[int | None] = mapped_column(ForeignKey("doctor.id_doctor"), nullable=True)
    #: Quien la emitio. Sale del JWT en la ruta, nunca del body.
    id_asistente: Mapped[int | None] = mapped_column(
        ForeignKey("asistente.id_asistente"), nullable=True
    )
    #: 1:1 opcional: solo si esta factura nacio de un Presupuesto aceptado.
    id_plan: Mapped[int | None] = mapped_column(
        ForeignKey("plan_tratamiento.id_plan"), nullable=True, unique=True
    )
    numero_factura: Mapped[str] = mapped_column(String(20), nullable=False)
    monto_subtotal: Mapped[str] = mapped_column(Numeric(10, 2), nullable=False)
    monto_impuesto: Mapped[str] = mapped_column(Numeric(10, 2), nullable=False)
    monto_total: Mapped[str] = mapped_column(Numeric(10, 2), nullable=False)
    estado: Mapped[EstadoFactura] = mapped_column(
        SAEnum(
            EstadoFactura,
            name="estado_factura",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        default=EstadoFactura.PENDIENTE,
        server_default="pendiente",
        nullable=False,
    )
    fecha_emision: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class FacturaDetalle(Base):
    """Linea de una factura: un tratamiento con precio congelado al momento
    de facturar. NO lleva id_clinica propio -- se aisla via JOIN contra
    Factura, mismo criterio que PlanTratamientoDetalle del Modulo 5.
    """

    __tablename__ = "factura_detalle"

    id_detalle: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_factura: Mapped[int] = mapped_column(ForeignKey("factura.id_factura"), nullable=False)
    id_tratamiento: Mapped[int] = mapped_column(
        ForeignKey("tratamiento.id_tratamiento"), nullable=False
    )
    cantidad: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    precio_unitario: Mapped[str] = mapped_column(Numeric(10, 2), nullable=False)


class Pago(Base):
    """Un pago (parcial o total) contra una factura. NO lleva id_clinica
    propio, mismo criterio que FacturaDetalle.
    """

    __tablename__ = "pago"

    id_pago: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_factura: Mapped[int] = mapped_column(ForeignKey("factura.id_factura"), nullable=False)
    id_metodo_pago: Mapped[int] = mapped_column(
        ForeignKey("metodo_pago.id_metodo_pago"), nullable=False
    )
    id_asistente: Mapped[int | None] = mapped_column(
        ForeignKey("asistente.id_asistente"), nullable=True
    )
    monto: Mapped[str] = mapped_column(Numeric(10, 2), nullable=False)
    fecha_pago: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
