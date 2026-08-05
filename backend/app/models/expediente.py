"""Catalogo de tratamientos, historial de consultas, diagnosticos y odontograma.

Cuatro entidades con una relacion en comun: todas cuelgan de Paciente y/o
Doctor, que son del Modulo 4. Ver la politica de bajas en el spec del
Modulo 5 (nace de la deuda que dejo pendiente la seccion 11 del spec del
Modulo 4): dar de baja un Paciente o un Doctor se bloquea si tiene un
PlanTratamiento activo, y eso vive en plan_tratamiento.py, no aca.
"""
import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class Tratamiento(Base):
    """Catalogo de procedimientos que la clinica ofrece, con su precio.

    Es el mismo caso que Especialidad/Consultorio/MetodoPago del Modulo 3
    (nombre unico por clinica, borrado logico), asi que el repositorio
    hereda CatalogoRepository. La diferencia con esos tres es que ademas
    lleva precio y duracion estimada, y que dar de baja SI puede bloquearse
    (ver TratamientoRepository.eliminar): un tratamiento en uso en un plan
    activo no se puede desactivar en silencio.

    precio_unitario NO se lee desde aca al construir un detalle de plan: se
    copia una vez, al agregar el detalle (PlanTratamientoDetalle.precio_unitario).
    Es la misma foto-del-momento que Cita.duracion_minutos: si la clinica
    sube el precio de una limpieza, los planes ya armados no deben
    encarecerse solos.
    """

    __tablename__ = "tratamiento"
    __table_args__ = (
        UniqueConstraint("id_clinica", "nombre", name="uq_tratamiento_clinica_nombre"),
    )

    id_tratamiento: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_clinica: Mapped[int] = mapped_column(
        ForeignKey("clinica.id_clinica"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    #: Numeric, no Float: mismo motivo que ConfiguracionClinica.porcentaje_impuesto
    #: (Modulo 3) -- la plata no se representa con coma flotante binaria.
    precio: Mapped[str] = mapped_column(Numeric(10, 2), nullable=False)
    duracion_minutos_estimada: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    activo: Mapped[bool] = mapped_column(default=True, server_default="1")


class Consulta(Base):
    """Un encuentro clinico: el registro de que el paciente vino y que paso.

    id_cita es nullable: no toda consulta viene de una cita agendada (una
    emergencia sin cita previa, o migracion de historial del legacy que no
    tiene cita asociada). Cuando existe, referencia la cita que la origino,
    pero la consulta es el registro clinico permanente y la cita solo el
    turno; por eso no se borra (ver ConsultaRepository.eliminar), igual que
    Cita.
    """

    __tablename__ = "consulta"

    id_consulta: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_clinica: Mapped[int] = mapped_column(
        ForeignKey("clinica.id_clinica"), nullable=False
    )
    id_paciente: Mapped[int] = mapped_column(
        ForeignKey("paciente.id_paciente"), nullable=False
    )
    id_doctor: Mapped[int] = mapped_column(
        ForeignKey("doctor.id_doctor"), nullable=False
    )
    id_cita: Mapped[int | None] = mapped_column(
        ForeignKey("cita.id_cita"), nullable=True
    )
    fecha_hora: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    motivo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Diagnostico(Base):
    """Un diagnostico registrado durante una consulta.

    Una consulta puede dejar varios diagnosticos (una limpieza de rutina que
    revela dos caries, por ejemplo), asi que es una entidad propia y no un
    campo de texto suelto en Consulta. pieza_numero es opcional: hay
    diagnosticos generales (bruxismo) que no senalan una pieza puntual.
    """

    __tablename__ = "diagnostico"

    id_diagnostico: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_clinica: Mapped[int] = mapped_column(
        ForeignKey("clinica.id_clinica"), nullable=False
    )
    id_consulta: Mapped[int] = mapped_column(
        ForeignKey("consulta.id_consulta"), nullable=False
    )
    descripcion: Mapped[str] = mapped_column(String(255), nullable=False)
    pieza_numero: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class EstadoPiezaDental(str, enum.Enum):
    SANO = "sano"
    CARIADO = "cariado"
    OBTURADO = "obturado"
    AUSENTE = "ausente"
    CORONA = "corona"
    ENDODONCIA = "endodoncia"
    IMPLANTE = "implante"


class Odontograma(Base):
    """1:1 con Paciente, igual que ConfiguracionClinica con Clinica.

    Se crea al vuelo la primera vez que se consulta (mismo patron que
    GET /configuracion del Modulo 3): no hace falta un alta explicita, y asi
    no hay que migrar a los pacientes que ya existian antes de este modulo.
    """

    __tablename__ = "odontograma"

    id_odontograma: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_clinica: Mapped[int] = mapped_column(
        ForeignKey("clinica.id_clinica"), nullable=False
    )
    id_paciente: Mapped[int] = mapped_column(
        ForeignKey("paciente.id_paciente"), nullable=False, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PiezaDental(Base):
    """El estado de una pieza dentro de un odontograma.

    numero_pieza usa la numeracion universal 1-32 (dentadura permanente
    completa). No se crean las 32 filas al crear el odontograma: se crean
    perezosamente, una por una, la primera vez que alguien la actualiza.
    Leer un odontograma (OdontogramaRepository.listar_piezas) rellena con
    'sano' las que faltan, igual que HorarioClinicaRepository rellena los
    dias sin fila con HORARIO_POR_DEFECTO.
    """

    __tablename__ = "pieza_dental"
    __table_args__ = (
        UniqueConstraint(
            "id_odontograma", "numero_pieza", name="uq_pieza_odontograma_numero"
        ),
    )

    id_pieza: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_odontograma: Mapped[int] = mapped_column(
        ForeignKey("odontograma.id_odontograma"), nullable=False
    )
    numero_pieza: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[EstadoPiezaDental] = mapped_column(
        SAEnum(
            EstadoPiezaDental,
            name="estado_pieza_dental",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        default=EstadoPiezaDental.SANO,
        server_default="sano",
        nullable=False,
    )
    observaciones: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
