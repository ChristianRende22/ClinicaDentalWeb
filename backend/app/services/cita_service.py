from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.exceptions import AnticipacionInsuficienteError, TransicionInvalidaError
from app.models import TRANSICIONES_PERMITIDAS, Cita, EstadoCita
from app.repositories.cita_repository import CitaRepository
from app.repositories.configuracion_repository import ConfiguracionClinicaRepository
from app.services.validadores_cita import (
    ContextoCita,
    ValidadorDeCita,
    validadores_por_defecto,
)


class CitaService:
    """Toda la logica de agendamiento. Ninguna ruta valida una cita por su cuenta.

    Los validadores se inyectan para poder testear la orquestacion sin depender
    de las siete reglas reales.
    """

    def __init__(self, db: Session, validadores: list[ValidadorDeCita] | None = None):
        self.db = db
        self.citas = CitaRepository(db)
        self.configuraciones = ConfiguracionClinicaRepository(db)
        self.validadores = (
            validadores if validadores is not None else validadores_por_defecto(db)
        )

    @staticmethod
    def _ahora(ahora: datetime | None) -> datetime:
        """Inyectable para que los tests sean deterministas."""
        return ahora if ahora is not None else datetime.now()

    def _validar(self, ctx: ContextoCita) -> None:
        """Corre los validadores en orden y corta en el primero que falla: el
        mensaje util es el de la primera regla violada, no una lista de siete.
        """
        for validador in self.validadores:
            validador.validar(ctx)

    def crear(
        self,
        id_clinica: int,
        datos: dict,
        id_asistente: int | None = None,
        ahora: datetime | None = None,
    ) -> Cita:
        configuracion = self.configuraciones.obtener_o_crear(id_clinica)
        pedida = datos.get("duracion_minutos")
        duracion = pedida if pedida is not None else configuracion.duracion_cita_minutos

        ctx = ContextoCita(
            id_clinica=id_clinica,
            id_paciente=datos["id_paciente"],
            id_doctor=datos["id_doctor"],
            id_consultorio=datos.get("id_consultorio"),
            fecha_hora=datos["fecha_hora"],
            duracion_minutos=duracion,
            configuracion=configuracion,
            ahora=self._ahora(ahora),
        )
        self._validar(ctx)

        return self.citas.crear(
            id_clinica,
            {
                "id_paciente": ctx.id_paciente,
                "id_doctor": ctx.id_doctor,
                "id_consultorio": ctx.id_consultorio,
                "id_asistente": id_asistente,
                "fecha_hora": ctx.fecha_hora,
                "duracion_minutos": duracion,
                "motivo": datos.get("motivo"),
            },
        )

    @staticmethod
    def _exigir_transicion(actual: EstadoCita, nuevo: EstadoCita) -> None:
        if nuevo not in TRANSICIONES_PERMITIDAS[actual]:
            raise TransicionInvalidaError(
                f"Una cita en estado '{actual.value}' no puede pasar a '{nuevo.value}'"
            )

    def cambiar_estado(
        self,
        id_clinica: int,
        id_cita: int,
        nuevo: EstadoCita,
        ahora: datetime | None = None,
    ) -> Cita | None:
        """Cancelar NO se atiende aca, se delega en cancelar().

        La tabla de transiciones permite pasar a 'cancelada', pero cancelar
        tiene ademas una regla propia (horas_minimas_cambio_cita) que este
        metodo no conoce. Si no se delegara, cualquiera podria cancelar sobre
        la hora pidiendo el cambio de estado por esta via y la regla quedaria
        decorativa.
        """
        if nuevo is EstadoCita.CANCELADA:
            return self.cancelar(id_clinica, id_cita, ahora=ahora)

        cita = self.citas.obtener(id_clinica, id_cita)
        if cita is None:
            return None
        self._exigir_transicion(cita.estado, nuevo)
        cita.estado = nuevo
        self.db.flush()
        return cita

    def _exigir_anticipacion_de_cambio(
        self, cita: Cita, configuracion, ahora: datetime
    ) -> None:
        """Mide con cuanta anticipacion avisas, respecto de la cita VIGENTE."""
        horas = configuracion.horas_minimas_cambio_cita
        if cita.fecha_hora - ahora < timedelta(hours=horas):
            raise AnticipacionInsuficienteError(
                f"Hay que avisar con al menos {horas} horas de anticipacion"
            )

    def cancelar(
        self, id_clinica: int, id_cita: int, ahora: datetime | None = None
    ) -> Cita | None:
        cita = self.citas.obtener(id_clinica, id_cita)
        if cita is None:
            return None

        self._exigir_transicion(cita.estado, EstadoCita.CANCELADA)
        configuracion = self.configuraciones.obtener_o_crear(id_clinica)
        self._exigir_anticipacion_de_cambio(cita, configuracion, self._ahora(ahora))

        cita.estado = EstadoCita.CANCELADA
        self.db.flush()
        return cita

    def reagendar(
        self,
        id_clinica: int,
        id_cita: int,
        fecha_hora: datetime,
        id_consultorio: int | None = None,
        ahora: datetime | None = None,
    ) -> Cita | None:
        """Mueve la cita en su lugar. No cancela ni crea otra: una cita del mundo
        real que se corre de dia sigue siendo la misma cita.
        """
        cita = self.citas.obtener(id_clinica, id_cita)
        if cita is None:
            return None

        # Terminalidad derivada de la tabla, que la expresa como conjunto
        # vacio. NO se usa ESTADOS_ACTIVOS: esa constante es para detectar
        # choques de agenda, y que hoy coincida con "no terminal" es
        # accidental — si manana no_asistio pasara a ocupar el slot para las
        # metricas del Modulo 7, se volveria reagendable una cita a la que el
        # paciente no vino.
        if not TRANSICIONES_PERMITIDAS[cita.estado]:
            raise TransicionInvalidaError(
                f"Una cita en estado '{cita.estado.value}' no se puede reagendar"
            )

        momento = self._ahora(ahora)
        configuracion = self.configuraciones.obtener_o_crear(id_clinica)

        # Regla 1: anticipacion respecto de la cita vieja (cuando avisas).
        self._exigir_anticipacion_de_cambio(cita, configuracion, momento)

        # Regla 2: distancia respecto de la cita nueva (para cuando la moves).
        # Son dos reglas distintas, con unidades distintas, tal como las
        # justifico el Modulo 3.
        dias = configuracion.dias_minimos_reagendamiento
        if fecha_hora - momento < timedelta(days=dias):
            raise AnticipacionInsuficienteError(
                f"La cita nueva debe quedar a {dias} dias o mas de hoy"
            )

        # Regla 3: las siete validaciones de siempre, contra la fecha nueva y
        # excluyendo esta cita del chequeo de solapamiento.
        ctx = ContextoCita(
            id_clinica=id_clinica,
            id_paciente=cita.id_paciente,
            id_doctor=cita.id_doctor,
            id_consultorio=(
                id_consultorio if id_consultorio is not None else cita.id_consultorio
            ),
            fecha_hora=fecha_hora,
            duracion_minutos=cita.duracion_minutos,
            configuracion=configuracion,
            ahora=momento,
            excluir_id_cita=cita.id_cita,
        )
        self._validar(ctx)

        cita.fecha_hora = fecha_hora
        cita.id_consultorio = ctx.id_consultorio
        cita.veces_reagendada += 1
        # La confirmacion era para la hora vieja: mantenerla afirmaria algo que
        # nadie confirmo.
        cita.estado = EstadoCita.PROGRAMADA
        self.db.flush()
        return cita
