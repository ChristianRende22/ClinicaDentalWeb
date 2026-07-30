import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base


class EstadoClinica(str, enum.Enum):
    ACTIVA = "activa"
    SUSPENDIDA = "suspendida"
    INACTIVA = "inactiva"


class Clinica(Base):
    __tablename__ = "clinica"

    id_clinica: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    direccion: Mapped[str | None] = mapped_column(String(150), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(8), nullable=True)
    correo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    estado: Mapped[EstadoClinica] = mapped_column(
        SAEnum(
            EstadoClinica,
            name="estado_clinica",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        default=EstadoClinica.ACTIVA,
        server_default=EstadoClinica.ACTIVA.value,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="clinica")
    modulos: Mapped[list["ClinicaModulo"]] = relationship(back_populates="clinica")


class ClinicaModulo(Base):
    __tablename__ = "clinica_modulo"

    id_clinica: Mapped[int] = mapped_column(
        ForeignKey("clinica.id_clinica"), primary_key=True
    )
    modulo: Mapped[str] = mapped_column(String(50), primary_key=True)
    habilitado: Mapped[bool] = mapped_column(default=True, server_default="1")

    clinica: Mapped["Clinica"] = relationship(back_populates="modulos")
