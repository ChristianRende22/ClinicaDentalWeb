"""Las reglas de agendamiento, una clase por regla.

Cada validador es un objeto chico e independiente con la misma interfaz. Se
testean de a uno, sin base de datos ni servicio alrededor. Agregar una regla es
un archivo nuevo (o una clase mas aca) y un renglon en validadores_por_defecto:
no hay que volver a abrir CitaService. Esto es OCP, y es el mismo criterio con
el que el Modulo 3 justifico MetodoPago como tabla en vez de columnas booleanas.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from sqlalchemy.orm import Session

from app.exceptions import (
    AnticipacionInsuficienteError,
    ChoqueDeCitaError,
    CitaEnElPasadoError,
    DoctorNoDisponibleError,
    FueraDeHorarioClinicaError,
    ReferenciaInvalidaError,
)
from app.models import HORARIO_POR_DEFECTO, DiaSemana

#: datetime.weekday() devuelve 0 para lunes y 6 para domingo, que es exactamente
#: el orden de declaracion de DiaSemana.
_DIA_POR_INDICE = list(DiaSemana)


@dataclass(frozen=True)
class ContextoCita:
    """Todo lo que los validadores necesitan saber, en un solo objeto inmutable.

    excluir_id_cita es lo que hace que los mismos validadores sirvan para crear
    y para reagendar: al reagendar se excluye la propia cita del chequeo de
    solapamiento, si no chocaria contra si misma.
    """

    id_clinica: int
    id_paciente: int
    id_doctor: int
    id_consultorio: int | None
    fecha_hora: datetime
    duracion_minutos: int
    configuracion: object
    ahora: datetime
    excluir_id_cita: int | None = None

    @property
    def fin(self) -> datetime:
        return self.fecha_hora + timedelta(minutes=self.duracion_minutos)

    @property
    def dia_semana(self) -> DiaSemana:
        return _DIA_POR_INDICE[self.fecha_hora.weekday()]

    @property
    def cruza_medianoche(self) -> bool:
        return self.fin.date() != self.fecha_hora.date()


class ValidadorDeCita(Protocol):
    def validar(self, ctx: ContextoCita) -> None:
        """Lanza una excepcion de dominio si la cita no es valida."""
        ...


class ReferenciasDeLaMismaClinica:
    """1. Paciente, doctor y consultorio existen, estan activos y son de esta clinica."""

    def __init__(self, pacientes, doctores, consultorios):
        self.pacientes = pacientes
        self.doctores = doctores
        self.consultorios = consultorios

    def validar(self, ctx: ContextoCita) -> None:
        self._exigir(self.pacientes.obtener(ctx.id_clinica, ctx.id_paciente), "paciente")
        self._exigir(self.doctores.obtener(ctx.id_clinica, ctx.id_doctor), "doctor")
        if ctx.id_consultorio is not None:
            self._exigir(
                self.consultorios.obtener(ctx.id_clinica, ctx.id_consultorio),
                "consultorio",
            )

    @staticmethod
    def _exigir(registro, nombre: str) -> None:
        """Distingue "no existe" de "esta dado de baja".

        No es cosmetico: un doctor dado de baja puede seguir teniendo citas
        futuras, y quien recibe el error necesita saber si el id esta mal o si
        hay que reasignar la cita a otro profesional.
        """
        if registro is None:
            raise ReferenciaInvalidaError(f"El {nombre} no existe en esta clinica")
        if not registro.activo:
            raise ReferenciaInvalidaError(f"El {nombre} esta dado de baja")


class NoEnElPasado:
    """2. La cita no puede quedar en el pasado ni exactamente ahora."""

    def validar(self, ctx: ContextoCita) -> None:
        if ctx.fecha_hora <= ctx.ahora:
            raise CitaEnElPasadoError("No se puede agendar una cita en el pasado")


class AnticipacionMinima:
    """3. Se respeta la anticipacion minima que configuro la clinica."""

    def validar(self, ctx: ContextoCita) -> None:
        horas = ctx.configuracion.anticipacion_minima_reserva_horas
        if ctx.fecha_hora < ctx.ahora + timedelta(hours=horas):
            raise AnticipacionInsuficienteError(
                f"Hay que agendar con al menos {horas} horas de anticipacion"
            )


class DentroDelHorarioDeLaClinica:
    """4. Inicio y fin caen dentro del horario de atencion del dia."""

    def __init__(self, horarios_clinica):
        self.horarios_clinica = horarios_clinica

    def validar(self, ctx: ContextoCita) -> None:
        filas = {
            fila.dia_semana: fila
            for fila in self.horarios_clinica.listar_semana(ctx.id_clinica)
        }
        fila = filas.get(ctx.dia_semana)
        if fila is None:
            # Mismo relleno con defaults que hace GET /horarios del Modulo 3.
            defecto = HORARIO_POR_DEFECTO[ctx.dia_semana]
            cerrado = defecto["cerrado"]
            apertura = defecto["hora_apertura"]
            cierre = defecto["hora_cierre"]
        else:
            cerrado, apertura, cierre = fila.cerrado, fila.hora_apertura, fila.hora_cierre

        if cerrado or apertura is None or cierre is None:
            raise FueraDeHorarioClinicaError(
                f"La clinica no atiende los {ctx.dia_semana.value}"
            )

        if ctx.cruza_medianoche or ctx.fecha_hora.time() < apertura or ctx.fin.time() > cierre:
            raise FueraDeHorarioClinicaError(
                f"El horario de atencion del {ctx.dia_semana.value} es de "
                f"{apertura} a {cierre}"
            )


class DentroDelHorarioDelDoctor:
    """5. La cita cae entera dentro de UN MISMO bloque disponible del doctor.

    Un doctor sin ningun bloque cargado se considera no disponible. La
    alternativa (sin bloques = disponible en todo el horario de la clinica) es
    mas comoda pero silenciosa: nadie se entera de que falta configurar algo.
    """

    def __init__(self, horarios_doctor):
        self.horarios_doctor = horarios_doctor

    def validar(self, ctx: ContextoCita) -> None:
        bloques = [
            bloque
            for bloque in self.horarios_doctor.listar_de_doctor(
                ctx.id_clinica, ctx.id_doctor
            )
            if bloque.dia_semana == ctx.dia_semana and bloque.disponible
        ]
        inicio, fin = ctx.fecha_hora.time(), ctx.fin.time()
        entra = not ctx.cruza_medianoche and any(
            bloque.hora_inicio <= inicio and fin <= bloque.hora_fin for bloque in bloques
        )
        if not entra:
            raise DoctorNoDisponibleError(
                "El doctor no atiende en ese horario"
            )


class SinChoqueDeDoctor:
    """6. El doctor no tiene otra cita activa solapada."""

    def __init__(self, citas):
        self.citas = citas

    def validar(self, ctx: ContextoCita) -> None:
        if self.citas.hay_solapamiento_de_doctor(
            ctx.id_clinica,
            ctx.id_doctor,
            ctx.fecha_hora,
            ctx.fin,
            excluir_id_cita=ctx.excluir_id_cita,
        ):
            raise ChoqueDeCitaError("El doctor ya tiene una cita en ese horario")


class SinChoqueDeConsultorio:
    """7. El consultorio no esta ocupado. Se saltea si la cita no lleva sala."""

    def __init__(self, citas):
        self.citas = citas

    def validar(self, ctx: ContextoCita) -> None:
        if ctx.id_consultorio is None:
            return
        if self.citas.hay_solapamiento_de_consultorio(
            ctx.id_clinica,
            ctx.id_consultorio,
            ctx.fecha_hora,
            ctx.fin,
            excluir_id_cita=ctx.excluir_id_cita,
        ):
            raise ChoqueDeCitaError("El consultorio ya esta ocupado en ese horario")


def validadores_por_defecto(db: Session) -> list[ValidadorDeCita]:
    """El orden importa: se corta en el primero que falla, y no tiene sentido
    chequear solapamientos si el paciente ni siquiera existe.
    """
    from app.repositories.cita_repository import CitaRepository
    from app.repositories.consultorio_repository import ConsultorioRepository
    from app.repositories.doctor_repository import DoctorRepository
    from app.repositories.horario_clinica_repository import HorarioClinicaRepository
    from app.repositories.horario_doctor_repository import HorarioDoctorRepository
    from app.repositories.paciente_repository import PacienteRepository

    citas = CitaRepository(db)
    return [
        ReferenciasDeLaMismaClinica(
            PacienteRepository(db), DoctorRepository(db), ConsultorioRepository(db)
        ),
        NoEnElPasado(),
        AnticipacionMinima(),
        DentroDelHorarioDeLaClinica(HorarioClinicaRepository(db)),
        DentroDelHorarioDelDoctor(HorarioDoctorRepository(db)),
        SinChoqueDeDoctor(citas),
        SinChoqueDeConsultorio(citas),
    ]
