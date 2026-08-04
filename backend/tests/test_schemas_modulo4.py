from datetime import date, datetime, time

import pytest
from pydantic import ValidationError


def test_el_nombre_se_recorta_y_no_puede_quedar_vacio():
    from app.schemas.personas import PacienteCreate

    creado = PacienteCreate(nombre="  Ana  ", apellido="Lopez", telefono="70001122")
    assert creado.nombre == "Ana"

    with pytest.raises(ValidationError):
        PacienteCreate(nombre="   ", apellido="Lopez", telefono="70001122")


def test_el_telefono_se_normaliza_quitando_espacios_y_guiones():
    from app.schemas.personas import PacienteCreate

    creado = PacienteCreate(nombre="Ana", apellido="Lopez", telefono="7000-1122")
    assert creado.telefono == "70001122"


def test_un_telefono_con_letras_es_invalido():
    from app.schemas.personas import PacienteCreate

    with pytest.raises(ValidationError):
        PacienteCreate(nombre="Ana", apellido="Lopez", telefono="7000abcd")


def test_un_telefono_demasiado_corto_es_invalido():
    from app.schemas.personas import PacienteCreate

    with pytest.raises(ValidationError):
        PacienteCreate(nombre="Ana", apellido="Lopez", telefono="7000")


def test_la_fecha_de_nacimiento_no_puede_ser_futura():
    from app.schemas.personas import PacienteCreate

    with pytest.raises(ValidationError):
        PacienteCreate(
            nombre="Ana",
            apellido="Lopez",
            telefono="70001122",
            fecha_nacimiento=date.today().replace(year=date.today().year + 1),
        )


def test_un_correo_mal_formado_es_invalido():
    from app.schemas.personas import PacienteCreate

    with pytest.raises(ValidationError):
        PacienteCreate(
            nombre="Ana", apellido="Lopez", telefono="70001122", correo="no-es-correo"
        )


def test_la_respuesta_del_paciente_calcula_la_edad():
    from app.schemas.personas import PacienteResponse

    class _Paciente:
        id_paciente = 1
        nombre = "Ana"
        apellido = "Lopez"
        fecha_nacimiento = date(2000, 1, 1)
        telefono = "70001122"
        correo = None
        direccion = None
        activo = True

    respuesta = PacienteResponse.model_validate(_Paciente())

    esperada = date.today().year - 2000 - (
        (date.today().month, date.today().day) < (1, 1)
    )
    assert respuesta.edad == esperada


def test_sin_fecha_de_nacimiento_la_edad_es_none():
    from app.schemas.personas import PacienteResponse

    class _Paciente:
        id_paciente = 1
        nombre = "Ana"
        apellido = "Lopez"
        fecha_nacimiento = None
        telefono = "70001122"
        correo = None
        direccion = None
        activo = True

    assert PacienteResponse.model_validate(_Paciente()).edad is None


def test_un_bloque_con_fin_menor_al_inicio_es_invalido():
    from app.models import DiaSemana
    from app.schemas.personas import BloqueHorarioSchema

    with pytest.raises(ValidationError):
        BloqueHorarioSchema(
            dia_semana=DiaSemana.LUNES, hora_inicio=time(12, 0), hora_fin=time(8, 0)
        )


def test_la_duracion_de_la_cita_respeta_el_rango():
    from app.schemas.cita import CitaCreate

    CitaCreate(
        id_paciente=1, id_doctor=1, fecha_hora=datetime(2026, 9, 1, 9, 0),
        duracion_minutos=30,
    )

    with pytest.raises(ValidationError):
        CitaCreate(
            id_paciente=1, id_doctor=1, fecha_hora=datetime(2026, 9, 1, 9, 0),
            duracion_minutos=4,
        )
    with pytest.raises(ValidationError):
        CitaCreate(
            id_paciente=1, id_doctor=1, fecha_hora=datetime(2026, 9, 1, 9, 0),
            duracion_minutos=481,
        )


def test_la_duracion_de_la_cita_es_opcional():
    from app.schemas.cita import CitaCreate

    creada = CitaCreate(
        id_paciente=1, id_doctor=1, fecha_hora=datetime(2026, 9, 1, 9, 0)
    )
    assert creada.duracion_minutos is None


def test_la_anticipacion_minima_no_puede_ser_cero():
    from app.schemas.parametros import ConfiguracionUpdateRequest

    ConfiguracionUpdateRequest(anticipacion_minima_reserva_horas=1)

    with pytest.raises(ValidationError):
        ConfiguracionUpdateRequest(anticipacion_minima_reserva_horas=0)
    with pytest.raises(ValidationError):
        ConfiguracionUpdateRequest(anticipacion_minima_reserva_horas=721)


def test_una_fecha_con_zona_horaria_se_rechaza():
    from app.schemas.cita import CitaCreate

    with pytest.raises(ValidationError):
        CitaCreate(
            id_paciente=1, id_doctor=1, fecha_hora="2026-09-08T09:00:00Z"
        )


def test_reagendar_tambien_rechaza_la_fecha_con_zona_horaria():
    from app.schemas.cita import ReagendarRequest

    with pytest.raises(ValidationError):
        ReagendarRequest(fecha_hora="2026-09-08T09:00:00+02:00")

    ReagendarRequest(fecha_hora="2026-09-08T09:00:00")  # naive: valida
