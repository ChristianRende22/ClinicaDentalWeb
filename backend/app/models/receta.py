from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class Receta(Base):
    """La receta en si: quien la emite, a quien, y cuando. Los medicamentos
    van en RecetaDetalle -- ver decision 7 del spec: una tabla, no un campo
    de texto libre con todo adentro.
    """

    __tablename__ = "receta"

    id_receta: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_clinica: Mapped[int] = mapped_column(
        ForeignKey("clinica.id_clinica"), nullable=False
    )
    id_paciente: Mapped[int] = mapped_column(
        ForeignKey("paciente.id_paciente"), nullable=False
    )
    id_doctor: Mapped[int] = mapped_column(
        ForeignKey("doctor.id_doctor"), nullable=False
    )
    id_consulta: Mapped[int | None] = mapped_column(
        ForeignKey("consulta.id_consulta"), nullable=True
    )
    fecha_emision: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    indicaciones_generales: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class RecetaDetalle(Base):
    """Un medicamento dentro de una receta."""

    __tablename__ = "receta_detalle"

    id_detalle: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_receta: Mapped[int] = mapped_column(
        ForeignKey("receta.id_receta"), nullable=False
    )
    medicamento: Mapped[str] = mapped_column(String(100), nullable=False)
    dosis: Mapped[str] = mapped_column(String(50), nullable=False)
    frecuencia: Mapped[str] = mapped_column(String(50), nullable=False)
    duracion: Mapped[str | None] = mapped_column(String(50), nullable=True)
    indicaciones: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
