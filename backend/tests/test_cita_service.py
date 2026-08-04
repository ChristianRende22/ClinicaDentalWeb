from datetime import datetime, timedelta

import pytest

from tests.factories import crear_cita, crear_clinica, crear_doctor, crear_paciente

AHORA = datetime(2026, 9, 1, 8, 0)  # martes
EN_UNA_SEMANA = datetime(2026, 9, 8, 9, 0)  # martes siguiente


class _ValidadorQueCuenta:
    def __init__(self, nombre, registro, explota=None):
        self.nombre = nombre
        self.registro = registro
        self.explota = explota

    def validar(self, ctx):
        self.registro.append(self.nombre)
        if self.explota is not None:
            raise self.explota


def _servicio(db_session, validadores=None):
    from app.services.cita_service import CitaService

    return CitaService(db_session, validadores=validadores if validadores is not None else [])


def _escenario(db_session):
    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    return clinica.id_clinica, paciente.id_paciente, doctor.id_doctor


def _datos(id_paciente, id_doctor, **campos):
    base = {
        "id_paciente": id_paciente,
        "id_doctor": id_doctor,
        "fecha_hora": EN_UNA_SEMANA,
    }
    base.update(campos)
    return base


# --- crear ----------------------------------------------------------------

def test_crear_devuelve_una_cita_programada(db_session):
    from app.models import EstadoCita

    id_clinica, id_paciente, id_doctor = _escenario(db_session)

    cita = _servicio(db_session).crear(
        id_clinica, _datos(id_paciente, id_doctor), ahora=AHORA
    )

    assert cita.id_cita is not None
    assert cita.estado == EstadoCita.PROGRAMADA
    assert cita.veces_reagendada == 0


def test_la_duracion_sale_de_la_configuracion_cuando_no_viene(db_session):
    id_clinica, id_paciente, id_doctor = _escenario(db_session)

    cita = _servicio(db_session).crear(
        id_clinica, _datos(id_paciente, id_doctor), ahora=AHORA
    )

    assert cita.duracion_minutos == 30  # default de ConfiguracionClinica


def test_la_duracion_del_request_gana_sobre_la_configuracion(db_session):
    id_clinica, id_paciente, id_doctor = _escenario(db_session)

    cita = _servicio(db_session).crear(
        id_clinica,
        _datos(id_paciente, id_doctor, duracion_minutos=45),
        ahora=AHORA,
    )

    assert cita.duracion_minutos == 45


def test_el_asistente_se_toma_del_parametro_y_no_del_body(db_session):
    """id_asistente es un dato de auditoria: el cliente no debe poder mentir."""
    from tests.factories import crear_asistente

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    real = crear_asistente(db_session, id_clinica, "recepcion.real")
    otro = crear_asistente(db_session, id_clinica, "recepcion.otro")

    cita = _servicio(db_session).crear(
        id_clinica,
        _datos(id_paciente, id_doctor, id_asistente=otro.id_asistente),
        id_asistente=real.id_asistente,
        ahora=AHORA,
    )

    assert cita.id_asistente == real.id_asistente


def test_los_validadores_corren_en_orden(db_session):
    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    registro = []
    validadores = [
        _ValidadorQueCuenta("uno", registro),
        _ValidadorQueCuenta("dos", registro),
        _ValidadorQueCuenta("tres", registro),
    ]

    _servicio(db_session, validadores).crear(
        id_clinica, _datos(id_paciente, id_doctor), ahora=AHORA
    )

    assert registro == ["uno", "dos", "tres"]


def test_se_corta_en_el_primer_validador_que_falla(db_session):
    from app.exceptions import CitaEnElPasadoError

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    registro = []
    validadores = [
        _ValidadorQueCuenta("uno", registro),
        _ValidadorQueCuenta("dos", registro, explota=CitaEnElPasadoError()),
        _ValidadorQueCuenta("tres", registro),
    ]

    with pytest.raises(CitaEnElPasadoError):
        _servicio(db_session, validadores).crear(
            id_clinica, _datos(id_paciente, id_doctor), ahora=AHORA
        )

    assert registro == ["uno", "dos"]


def test_si_un_validador_falla_no_se_crea_ninguna_cita(db_session):
    from app.exceptions import ChoqueDeCitaError
    from app.repositories.cita_repository import CitaRepository

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    validadores = [_ValidadorQueCuenta("uno", [], explota=ChoqueDeCitaError())]

    with pytest.raises(ChoqueDeCitaError):
        _servicio(db_session, validadores).crear(
            id_clinica, _datos(id_paciente, id_doctor), ahora=AHORA
        )

    assert CitaRepository(db_session).listar(id_clinica) == []


# --- cambiar_estado -------------------------------------------------------

def test_cambiar_estado_permitido(db_session):
    from app.models import EstadoCita

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    cita = crear_cita(db_session, id_clinica, id_paciente, id_doctor)

    actualizada = _servicio(db_session).cambiar_estado(
        id_clinica, cita.id_cita, EstadoCita.CONFIRMADA
    )

    assert actualizada.estado == EstadoCita.CONFIRMADA


def test_no_se_puede_completar_una_cita_solo_programada(db_session):
    from app.exceptions import TransicionInvalidaError
    from app.models import EstadoCita

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    cita = crear_cita(db_session, id_clinica, id_paciente, id_doctor)

    with pytest.raises(TransicionInvalidaError):
        _servicio(db_session).cambiar_estado(
            id_clinica, cita.id_cita, EstadoCita.COMPLETADA
        )


def test_una_cita_cancelada_no_admite_mas_transiciones(db_session):
    from app.exceptions import TransicionInvalidaError
    from app.models import EstadoCita

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    cita = crear_cita(
        db_session, id_clinica, id_paciente, id_doctor, estado=EstadoCita.CANCELADA
    )

    with pytest.raises(TransicionInvalidaError):
        _servicio(db_session).cambiar_estado(
            id_clinica, cita.id_cita, EstadoCita.CONFIRMADA
        )


def test_cambiar_estado_de_una_cita_de_otra_clinica_devuelve_none(db_session):
    from app.models import EstadoCita

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    otra = crear_clinica(db_session, "Dental B")
    cita = crear_cita(db_session, id_clinica, id_paciente, id_doctor)

    assert _servicio(db_session).cambiar_estado(
        otra.id_clinica, cita.id_cita, EstadoCita.CONFIRMADA
    ) is None


def test_no_se_puede_cancelar_sobre_la_hora_por_la_via_de_cambiar_estado(db_session):
    """La regla de anticipacion no se puede esquivar pidiendo el cambio de estado.

    La tabla de transiciones permite pasar a 'cancelada', asi que sin la
    delegacion en cancelar() esta via saltearia horas_minimas_cambio_cita.
    """
    from app.exceptions import AnticipacionInsuficienteError
    from app.models import EstadoCita

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    cita = crear_cita(
        db_session, id_clinica, id_paciente, id_doctor,
        fecha_hora=AHORA + timedelta(hours=2),
    )

    with pytest.raises(AnticipacionInsuficienteError):
        _servicio(db_session).cambiar_estado(
            id_clinica, cita.id_cita, EstadoCita.CANCELADA, ahora=AHORA
        )


def test_cancelar_por_la_via_de_cambiar_estado_funciona_con_anticipacion(db_session):
    from app.models import EstadoCita

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    cita = crear_cita(
        db_session, id_clinica, id_paciente, id_doctor, fecha_hora=EN_UNA_SEMANA
    )

    cancelada = _servicio(db_session).cambiar_estado(
        id_clinica, cita.id_cita, EstadoCita.CANCELADA, ahora=AHORA
    )

    assert cancelada.estado == EstadoCita.CANCELADA


# --- cancelar -------------------------------------------------------------

def test_cancelar_con_anticipacion_suficiente(db_session):
    from app.models import EstadoCita

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    cita = crear_cita(
        db_session, id_clinica, id_paciente, id_doctor, fecha_hora=EN_UNA_SEMANA
    )

    cancelada = _servicio(db_session).cancelar(id_clinica, cita.id_cita, ahora=AHORA)

    assert cancelada.estado == EstadoCita.CANCELADA


def test_cancelar_sobre_la_hora_no_se_puede(db_session):
    from app.exceptions import AnticipacionInsuficienteError

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    cita = crear_cita(
        db_session, id_clinica, id_paciente, id_doctor,
        fecha_hora=AHORA + timedelta(hours=2),
    )

    with pytest.raises(AnticipacionInsuficienteError):
        _servicio(db_session).cancelar(id_clinica, cita.id_cita, ahora=AHORA)


def test_no_se_puede_cancelar_una_cita_ya_completada(db_session):
    from app.exceptions import TransicionInvalidaError
    from app.models import EstadoCita

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    cita = crear_cita(
        db_session, id_clinica, id_paciente, id_doctor,
        fecha_hora=EN_UNA_SEMANA, estado=EstadoCita.COMPLETADA,
    )

    with pytest.raises(TransicionInvalidaError):
        _servicio(db_session).cancelar(id_clinica, cita.id_cita, ahora=AHORA)


# --- reagendar ------------------------------------------------------------

def test_reagendar_mueve_la_cita_incrementa_el_contador_y_baja_el_estado(db_session):
    from app.models import EstadoCita

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    cita = crear_cita(
        db_session, id_clinica, id_paciente, id_doctor,
        fecha_hora=EN_UNA_SEMANA, estado=EstadoCita.CONFIRMADA,
    )
    nueva_fecha = EN_UNA_SEMANA + timedelta(days=7)

    movida = _servicio(db_session).reagendar(
        id_clinica, cita.id_cita, nueva_fecha, ahora=AHORA
    )

    assert movida.id_cita == cita.id_cita  # es la misma fila, no una nueva
    assert movida.fecha_hora == nueva_fecha
    assert movida.veces_reagendada == 1
    assert movida.estado == EstadoCita.PROGRAMADA


def test_reagendar_sin_anticipacion_respecto_de_la_cita_vieja_no_se_puede(db_session):
    from app.exceptions import AnticipacionInsuficienteError

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    cita = crear_cita(
        db_session, id_clinica, id_paciente, id_doctor,
        fecha_hora=AHORA + timedelta(hours=2),
    )

    with pytest.raises(AnticipacionInsuficienteError):
        _servicio(db_session).reagendar(
            id_clinica, cita.id_cita, EN_UNA_SEMANA, ahora=AHORA
        )


def test_la_fecha_nueva_debe_respetar_los_dias_minimos_de_reagendamiento(db_session):
    from app.exceptions import AnticipacionInsuficienteError

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    cita = crear_cita(
        db_session, id_clinica, id_paciente, id_doctor, fecha_hora=EN_UNA_SEMANA
    )
    # El default es 3 dias; mananas es demasiado pronto.
    pasado_manana = AHORA + timedelta(days=2)

    with pytest.raises(AnticipacionInsuficienteError):
        _servicio(db_session).reagendar(
            id_clinica, cita.id_cita, pasado_manana, ahora=AHORA
        )


@pytest.mark.parametrize("estado_nombre", ["COMPLETADA", "CANCELADA", "NO_ASISTIO"])
def test_ningun_estado_terminal_se_puede_reagendar(db_session, estado_nombre):
    from app.exceptions import TransicionInvalidaError
    from app.models import EstadoCita

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    cita = crear_cita(
        db_session, id_clinica, id_paciente, id_doctor,
        fecha_hora=EN_UNA_SEMANA, estado=getattr(EstadoCita, estado_nombre),
    )

    with pytest.raises(TransicionInvalidaError):
        _servicio(db_session).reagendar(
            id_clinica, cita.id_cita, EN_UNA_SEMANA + timedelta(days=7), ahora=AHORA
        )


def test_reagendar_pasa_excluir_id_cita_a_los_validadores(db_session):
    """Sin esto, la cita chocaria contra si misma al validar su horario nuevo."""
    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    cita = crear_cita(
        db_session, id_clinica, id_paciente, id_doctor, fecha_hora=EN_UNA_SEMANA
    )
    vistos = []

    class _Espia:
        def validar(self, ctx):
            vistos.append(ctx.excluir_id_cita)

    _servicio(db_session, [_Espia()]).reagendar(
        id_clinica, cita.id_cita, EN_UNA_SEMANA + timedelta(days=7), ahora=AHORA
    )

    assert vistos == [cita.id_cita]
