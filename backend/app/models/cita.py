import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class EstadoCita(str, enum.Enum):
    PROGRAMADA = "programada"
    CONFIRMADA = "confirmada"
    COMPLETADA = "completada"
    CANCELADA = "cancelada"
    NO_ASISTIO = "no_asistio"


#: Maquina de estados en una sola tabla, en vez de condicionales repartidos.
#: Agregar un estado es una entrada aca; el conjunto vacio expresa "terminal"
#: sin necesitar un if especial.
#:
#: Solo se completa o se marca ausente desde 'confirmada': una cita que el
#: paciente nunca confirmo y a la que no vino es informacion distinta de una
#: que confirmo y no honro.
#:
#: Reagendar queda deliberadamente fuera de esta tabla. No es una transicion de
#: estado sino un movimiento de datos: la cita cambia de fecha y su estado se
#: RESETEA a 'programada' porque la confirmacion era para la hora vieja. Modelarlo
#: como transicion obligaria a permitir 'confirmada -> programada' en general, y
#: eso habilitaria des-confirmar una cita sin moverla, que no es una operacion
#: que el negocio tenga. CitaService.reagendar solo consulta esta tabla para
#: saber si el estado actual es terminal (conjunto vacio).
TRANSICIONES_PERMITIDAS: dict[EstadoCita, set[EstadoCita]] = {
    EstadoCita.PROGRAMADA: {EstadoCita.CONFIRMADA, EstadoCita.CANCELADA},
    EstadoCita.CONFIRMADA: {
        EstadoCita.COMPLETADA,
        EstadoCita.NO_ASISTIO,
        EstadoCita.CANCELADA,
    },
    EstadoCita.COMPLETADA: set(),
    EstadoCita.CANCELADA: set(),
    EstadoCita.NO_ASISTIO: set(),
}

#: Los estados que ocupan un lugar en la agenda. Una cita cancelada, completada
#: o marcada como ausente libera el horario y no cuenta para los choques.
ESTADOS_ACTIVOS: frozenset[EstadoCita] = frozenset(
    {EstadoCita.PROGRAMADA, EstadoCita.CONFIRMADA}
)


class Cita(Base):
    """El agendamiento. Toda la logica de validacion vive en CitaService y en
    los validadores; este modelo solo guarda el dato.
    """

    __tablename__ = "cita"
    __table_args__ = (
        # La agenda de un doctor en un rango de fechas es la consulta central
        # del modulo. El indice tiene que estar tambien aca y no solo en la
        # migracion: si no, los tests corren contra un esquema sin indice.
        Index("ix_cita_doctor_fecha", "id_doctor", "fecha_hora"),
    )

    id_cita: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # id_clinica explicito aunque sea derivable del paciente o del doctor: todos
    # los repositorios tenant-scoped filtran por id_clinica directo, y derivarlo
    # con un join haria que el aislamiento dependa de la correccion de ese join.
    id_clinica: Mapped[int] = mapped_column(
        ForeignKey("clinica.id_clinica"), nullable=False
    )
    id_paciente: Mapped[int] = mapped_column(
        ForeignKey("paciente.id_paciente"), nullable=False
    )
    id_doctor: Mapped[int] = mapped_column(
        ForeignKey("doctor.id_doctor"), nullable=False
    )
    id_consultorio: Mapped[int | None] = mapped_column(
        ForeignKey("consultorio.id_consultorio"), nullable=True
    )
    #: Quien la agendo. Nullable porque un admin (que no tiene fila en Asistente)
    #: tambien puede agendar.
    id_asistente: Mapped[int | None] = mapped_column(
        ForeignKey("asistente.id_asistente"), nullable=True
    )
    fecha_hora: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    #: Foto del momento en que se agendo. Si la clinica cambia la duracion por
    #: defecto, las citas ya agendadas no deben estirarse solas ni empezar a
    #: chocar entre si retroactivamente.
    duracion_minutos: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[EstadoCita] = mapped_column(
        SAEnum(
            EstadoCita,
            name="estado_cita",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        default=EstadoCita.PROGRAMADA,
        server_default="programada",
        nullable=False,
    )
    motivo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    #: Contador en vez de un estado 'reagendada': reagendar es una transicion,
    #: no una situacion. Un estado 'reagendada' no responde "esta confirmada o
    #: no?" y ensuciaria todos los filtros de agenda activa.
    veces_reagendada: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
