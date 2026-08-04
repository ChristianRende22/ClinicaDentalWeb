"""Tests de los validadores: SIN base de datos y SIN servicio.

Ese es el premio de haberlos separado. El contexto se arma a mano y los
validadores que consultan reciben dobles.
"""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

import pytest

AHORA = datetime(2026, 9, 1, 8, 0)  # martes
MANANA_9 = datetime(2026, 9, 2, 9, 0)  # miercoles 09:00


@dataclass
class _Config:
    anticipacion_minima_reserva_horas: int = 24
    duracion_cita_minutos: int = 30
    horas_minimas_cambio_cita: int = 24
    dias_minimos_reagendamiento: int = 3


@dataclass
class _Fila:
    """Sirve como paciente, doctor o consultorio de mentira."""
    activo: bool = True


@dataclass
class _Bloque:
    dia_semana: object
    hora_inicio: time
    hora_fin: time
    disponible: bool = True


class _RepoDeUno:
    """Doble que devuelve siempre lo mismo desde obtener()."""

    def __init__(self, valor):
        self.valor = valor

    def obtener(self, id_clinica, id_):
        return self.valor


class _HorariosClinica:
    def __init__(self, filas):
        self.filas = filas

    def listar_semana(self, id_clinica):
        return self.filas


class _HorariosDoctor:
    def __init__(self, bloques):
        self.bloques = bloques

    def listar_de_doctor(self, id_clinica, id_doctor):
        return self.bloques


class _Citas:
    def __init__(self, choca_doctor=False, choca_consultorio=False):
        self.choca_doctor = choca_doctor
        self.choca_consultorio = choca_consultorio
        self.ultima_exclusion = "no-llamado"
        self.ultima_exclusion_consultorio = "no-llamado"

    def hay_solapamiento_de_doctor(self, id_clinica, id_doctor, inicio, fin, excluir_id_cita=None):
        self.ultima_exclusion = excluir_id_cita
        return self.choca_doctor

    def hay_solapamiento_de_consultorio(
        self, id_clinica, id_consultorio, inicio, fin, excluir_id_cita=None
    ):
        self.ultima_exclusion_consultorio = excluir_id_cita
        return self.choca_consultorio


def _ctx(**campos):
    from app.services.validadores_cita import ContextoCita

    base = {
        "id_clinica": 1,
        "id_paciente": 10,
        "id_doctor": 20,
        "id_consultorio": None,
        "fecha_hora": MANANA_9,
        "duracion_minutos": 30,
        "configuracion": _Config(),
        "ahora": AHORA,
    }
    base.update(campos)
    return ContextoCita(**base)


# --- ContextoCita ---------------------------------------------------------

def test_el_contexto_calcula_el_fin_y_el_dia_de_la_semana():
    from app.models import DiaSemana

    ctx = _ctx(fecha_hora=MANANA_9, duracion_minutos=45)

    assert ctx.fin == MANANA_9 + timedelta(minutes=45)
    assert ctx.dia_semana == DiaSemana.MIERCOLES


# --- 1. ReferenciasDeLaMismaClinica ---------------------------------------

def _referencias(paciente=_Fila(), doctor=_Fila(), consultorio=_Fila()):
    from app.services.validadores_cita import ReferenciasDeLaMismaClinica

    return ReferenciasDeLaMismaClinica(
        _RepoDeUno(paciente), _RepoDeUno(doctor), _RepoDeUno(consultorio)
    )


def test_referencias_validas_no_lanzan_nada():
    _referencias().validar(_ctx())


def test_paciente_inexistente_es_referencia_invalida():
    from app.exceptions import ReferenciaInvalidaError

    with pytest.raises(ReferenciaInvalidaError):
        _referencias(paciente=None).validar(_ctx())


def test_paciente_inactivo_es_referencia_invalida():
    from app.exceptions import ReferenciaInvalidaError

    with pytest.raises(ReferenciaInvalidaError):
        _referencias(paciente=_Fila(activo=False)).validar(_ctx())


def test_doctor_inexistente_o_inactivo_es_referencia_invalida():
    from app.exceptions import ReferenciaInvalidaError

    with pytest.raises(ReferenciaInvalidaError):
        _referencias(doctor=None).validar(_ctx())
    with pytest.raises(ReferenciaInvalidaError):
        _referencias(doctor=_Fila(activo=False)).validar(_ctx())


def test_el_consultorio_solo_se_valida_si_vino():
    from app.exceptions import ReferenciaInvalidaError

    _referencias(consultorio=None).validar(_ctx(id_consultorio=None))

    with pytest.raises(ReferenciaInvalidaError):
        _referencias(consultorio=None).validar(_ctx(id_consultorio=5))


def test_el_mensaje_distingue_inexistente_de_dado_de_baja():
    """Un doctor dado de baja puede tener citas futuras: el mensaje tiene que
    decir que esta inactivo, no que no existe.
    """
    from app.exceptions import ReferenciaInvalidaError

    with pytest.raises(ReferenciaInvalidaError, match="no existe"):
        _referencias(doctor=None).validar(_ctx())

    with pytest.raises(ReferenciaInvalidaError, match="dado de baja"):
        _referencias(doctor=_Fila(activo=False)).validar(_ctx())


# --- 2. NoEnElPasado ------------------------------------------------------

def test_una_cita_futura_pasa_y_una_pasada_no():
    from app.exceptions import CitaEnElPasadoError
    from app.services.validadores_cita import NoEnElPasado

    NoEnElPasado().validar(_ctx(fecha_hora=AHORA + timedelta(minutes=1)))

    with pytest.raises(CitaEnElPasadoError):
        NoEnElPasado().validar(_ctx(fecha_hora=AHORA - timedelta(minutes=1)))


def test_una_cita_exactamente_ahora_esta_en_el_pasado():
    from app.exceptions import CitaEnElPasadoError
    from app.services.validadores_cita import NoEnElPasado

    with pytest.raises(CitaEnElPasadoError):
        NoEnElPasado().validar(_ctx(fecha_hora=AHORA))


# --- 3. AnticipacionMinima ------------------------------------------------

def test_anticipacion_justa_pasa_y_una_hora_menos_no():
    from app.exceptions import AnticipacionInsuficienteError
    from app.services.validadores_cita import AnticipacionMinima

    validador = AnticipacionMinima()
    validador.validar(_ctx(fecha_hora=AHORA + timedelta(hours=24)))

    with pytest.raises(AnticipacionInsuficienteError):
        validador.validar(_ctx(fecha_hora=AHORA + timedelta(hours=23)))


def test_la_anticipacion_sale_de_la_configuracion_de_la_clinica():
    from app.services.validadores_cita import AnticipacionMinima

    permisiva = _Config(anticipacion_minima_reserva_horas=2)

    AnticipacionMinima().validar(
        _ctx(fecha_hora=AHORA + timedelta(hours=2), configuracion=permisiva)
    )


# --- 4. DentroDelHorarioDeLaClinica ---------------------------------------

def _horario_clinica(filas):
    from app.services.validadores_cita import DentroDelHorarioDeLaClinica

    return DentroDelHorarioDeLaClinica(_HorariosClinica(filas))


@dataclass
class _FilaHorario:
    dia_semana: object
    hora_apertura: time | None
    hora_cierre: time | None
    cerrado: bool = False


def test_sin_filas_usa_el_horario_por_defecto_y_el_miercoles_esta_abierto():
    _horario_clinica([]).validar(_ctx(fecha_hora=MANANA_9))


def test_sin_filas_el_domingo_esta_cerrado_por_defecto():
    from app.exceptions import FueraDeHorarioClinicaError

    domingo_9 = datetime(2026, 9, 6, 9, 0)

    with pytest.raises(FueraDeHorarioClinicaError):
        _horario_clinica([]).validar(_ctx(fecha_hora=domingo_9))


def test_una_cita_que_termina_despues_del_cierre_no_pasa():
    from app.exceptions import FueraDeHorarioClinicaError
    from app.models import DiaSemana

    filas = [_FilaHorario(DiaSemana.MIERCOLES, time(8, 0), time(17, 0))]
    validador = _horario_clinica(filas)

    validador.validar(_ctx(fecha_hora=datetime(2026, 9, 2, 16, 30), duracion_minutos=30))

    with pytest.raises(FueraDeHorarioClinicaError):
        validador.validar(
            _ctx(fecha_hora=datetime(2026, 9, 2, 16, 45), duracion_minutos=30)
        )


def test_una_cita_antes_de_la_apertura_no_pasa():
    from app.exceptions import FueraDeHorarioClinicaError
    from app.models import DiaSemana

    filas = [_FilaHorario(DiaSemana.MIERCOLES, time(8, 0), time(17, 0))]

    with pytest.raises(FueraDeHorarioClinicaError):
        _horario_clinica(filas).validar(_ctx(fecha_hora=datetime(2026, 9, 2, 7, 30)))


def test_un_dia_marcado_cerrado_no_pasa():
    from app.exceptions import FueraDeHorarioClinicaError
    from app.models import DiaSemana

    filas = [_FilaHorario(DiaSemana.MIERCOLES, None, None, cerrado=True)]

    with pytest.raises(FueraDeHorarioClinicaError):
        _horario_clinica(filas).validar(_ctx(fecha_hora=MANANA_9))


# --- 5. DentroDelHorarioDelDoctor -----------------------------------------

def _horario_doctor(bloques):
    from app.services.validadores_cita import DentroDelHorarioDelDoctor

    return DentroDelHorarioDelDoctor(_HorariosDoctor(bloques))


def test_un_doctor_sin_bloques_cargados_no_esta_disponible():
    from app.exceptions import DoctorNoDisponibleError

    with pytest.raises(DoctorNoDisponibleError):
        _horario_doctor([]).validar(_ctx())


def test_la_cita_debe_caer_entera_dentro_de_un_mismo_bloque():
    from app.exceptions import DoctorNoDisponibleError
    from app.models import DiaSemana

    bloques = [
        _Bloque(DiaSemana.MIERCOLES, time(8, 0), time(12, 0)),
        _Bloque(DiaSemana.MIERCOLES, time(14, 0), time(18, 0)),
    ]
    validador = _horario_doctor(bloques)

    validador.validar(_ctx(fecha_hora=datetime(2026, 9, 2, 11, 30), duracion_minutos=30))

    # 11:45-12:15 se sale del bloque de la manana y no entra en el de la tarde.
    with pytest.raises(DoctorNoDisponibleError):
        validador.validar(
            _ctx(fecha_hora=datetime(2026, 9, 2, 11, 45), duracion_minutos=30)
        )


def test_un_bloque_marcado_no_disponible_no_sirve():
    from app.exceptions import DoctorNoDisponibleError
    from app.models import DiaSemana

    bloques = [_Bloque(DiaSemana.MIERCOLES, time(8, 0), time(12, 0), disponible=False)]

    with pytest.raises(DoctorNoDisponibleError):
        _horario_doctor(bloques).validar(_ctx())


def test_un_bloque_de_otro_dia_no_sirve():
    from app.exceptions import DoctorNoDisponibleError
    from app.models import DiaSemana

    bloques = [_Bloque(DiaSemana.LUNES, time(8, 0), time(12, 0))]

    with pytest.raises(DoctorNoDisponibleError):
        _horario_doctor(bloques).validar(_ctx(fecha_hora=MANANA_9))


# --- 6 y 7. Choques -------------------------------------------------------

def test_sin_choque_de_doctor_pasa_y_con_choque_no():
    from app.exceptions import ChoqueDeCitaError
    from app.services.validadores_cita import SinChoqueDeDoctor

    SinChoqueDeDoctor(_Citas(choca_doctor=False)).validar(_ctx())

    with pytest.raises(ChoqueDeCitaError):
        SinChoqueDeDoctor(_Citas(choca_doctor=True)).validar(_ctx())


def test_el_choque_de_doctor_propaga_excluir_id_cita():
    """Sin esto, al reagendar la cita chocaria contra si misma."""
    from app.services.validadores_cita import SinChoqueDeDoctor

    citas = _Citas()
    SinChoqueDeDoctor(citas).validar(_ctx(excluir_id_cita=77))

    assert citas.ultima_exclusion == 77


def test_el_choque_de_consultorio_se_saltea_si_no_hay_consultorio():
    from app.services.validadores_cita import SinChoqueDeConsultorio

    validador = SinChoqueDeConsultorio(_Citas(choca_consultorio=True))

    validador.validar(_ctx(id_consultorio=None))  # no debe lanzar


def test_el_choque_de_consultorio_se_detecta_cuando_hay_consultorio():
    from app.exceptions import ChoqueDeCitaError
    from app.services.validadores_cita import SinChoqueDeConsultorio

    with pytest.raises(ChoqueDeCitaError):
        SinChoqueDeConsultorio(_Citas(choca_consultorio=True)).validar(
            _ctx(id_consultorio=5)
        )


def test_el_choque_de_consultorio_tambien_propaga_excluir_id_cita():
    """Al reagendar manteniendo la misma sala, la cita no debe chocar consigo misma."""
    from app.services.validadores_cita import SinChoqueDeConsultorio

    citas = _Citas()
    SinChoqueDeConsultorio(citas).validar(_ctx(id_consultorio=5, excluir_id_cita=77))

    assert citas.ultima_exclusion_consultorio == 77


# --- cruza_medianoche -------------------------------------------------------

def test_una_cita_que_cruza_la_medianoche_no_cae_en_el_horario_de_la_clinica():
    from app.exceptions import FueraDeHorarioClinicaError
    from app.models import DiaSemana

    filas = [_FilaHorario(DiaSemana.MIERCOLES, time(0, 0), time(23, 59))]

    with pytest.raises(FueraDeHorarioClinicaError):
        _horario_clinica(filas).validar(
            _ctx(fecha_hora=datetime(2026, 9, 2, 23, 45), duracion_minutos=30)
        )


def test_una_cita_que_cruza_la_medianoche_tampoco_cae_en_el_horario_del_doctor():
    from app.exceptions import DoctorNoDisponibleError
    from app.models import DiaSemana

    bloques = [_Bloque(DiaSemana.MIERCOLES, time(0, 0), time(23, 59))]

    with pytest.raises(DoctorNoDisponibleError):
        _horario_doctor(bloques).validar(
            _ctx(fecha_hora=datetime(2026, 9, 2, 23, 45), duracion_minutos=30)
        )


# --- La lista por defecto -------------------------------------------------

def test_validadores_por_defecto_devuelve_los_siete_en_orden(db_session):
    from app.services.validadores_cita import (
        AnticipacionMinima,
        DentroDelHorarioDeLaClinica,
        DentroDelHorarioDelDoctor,
        NoEnElPasado,
        ReferenciasDeLaMismaClinica,
        SinChoqueDeConsultorio,
        SinChoqueDeDoctor,
        validadores_por_defecto,
    )

    tipos = [type(v) for v in validadores_por_defecto(db_session)]

    assert tipos == [
        ReferenciasDeLaMismaClinica,
        NoEnElPasado,
        AnticipacionMinima,
        DentroDelHorarioDeLaClinica,
        DentroDelHorarioDelDoctor,
        SinChoqueDeDoctor,
        SinChoqueDeConsultorio,
    ]
