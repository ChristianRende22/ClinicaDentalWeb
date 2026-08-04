from datetime import datetime, timedelta

from tests.factories import crear_cita, crear_clinica, crear_doctor, crear_paciente

INICIO = datetime(2026, 9, 1, 9, 0)


def _repo(db_session):
    from app.repositories.cita_repository import CitaRepository

    return CitaRepository(db_session)


def _escenario(db_session, nombre="Dental A", username="dra.perez"):
    """Devuelve (id_clinica, id_paciente, id_doctor)."""
    clinica = crear_clinica(db_session, nombre)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica, username)
    return clinica.id_clinica, paciente.id_paciente, doctor.id_doctor


def test_crear_devuelve_la_cita_programada(db_session):
    from app.models import EstadoCita

    id_clinica, id_paciente, id_doctor = _escenario(db_session)

    creada = _repo(db_session).crear(
        id_clinica,
        {
            "id_paciente": id_paciente,
            "id_doctor": id_doctor,
            "fecha_hora": INICIO,
            "duracion_minutos": 30,
        },
    )

    assert creada.id_cita is not None
    assert creada.estado == EstadoCita.PROGRAMADA


def test_listar_solo_devuelve_las_de_la_clinica_pedida(db_session):
    id_clinica_a, id_paciente_a, id_doctor_a = _escenario(db_session, "Dental A", "dra.a")
    id_clinica_b, id_paciente_b, id_doctor_b = _escenario(db_session, "Dental B", "dr.b")
    crear_cita(db_session, id_clinica_a, id_paciente_a, id_doctor_a)
    crear_cita(db_session, id_clinica_b, id_paciente_b, id_doctor_b)

    assert len(_repo(db_session).listar(id_clinica_a)) == 1


def test_listar_filtra_por_rango_de_fechas(db_session):
    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    crear_cita(db_session, id_clinica, id_paciente, id_doctor, fecha_hora=INICIO)
    crear_cita(
        db_session, id_clinica, id_paciente, id_doctor,
        fecha_hora=INICIO + timedelta(days=10),
    )

    resultado = _repo(db_session).listar(
        id_clinica, desde=INICIO - timedelta(hours=1), hasta=INICIO + timedelta(hours=1)
    )

    assert len(resultado) == 1


def test_listar_filtra_por_doctor_paciente_y_estado(db_session):
    from app.models import EstadoCita

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    otro_doctor = crear_doctor(db_session, id_clinica, "dr.otro")
    crear_cita(db_session, id_clinica, id_paciente, id_doctor)
    crear_cita(
        db_session, id_clinica, id_paciente, otro_doctor.id_doctor,
        fecha_hora=INICIO + timedelta(days=1),
    )
    crear_cita(
        db_session, id_clinica, id_paciente, id_doctor,
        fecha_hora=INICIO + timedelta(days=2), estado=EstadoCita.CANCELADA,
    )

    repo = _repo(db_session)

    assert len(repo.listar(id_clinica, id_doctor=id_doctor)) == 2
    assert len(repo.listar(id_clinica, id_paciente=id_paciente)) == 3
    assert len(repo.listar(id_clinica, estado=EstadoCita.CANCELADA)) == 1


def test_listar_ordena_por_fecha_ascendente(db_session):
    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    crear_cita(
        db_session, id_clinica, id_paciente, id_doctor,
        fecha_hora=INICIO + timedelta(days=5),
    )
    crear_cita(db_session, id_clinica, id_paciente, id_doctor, fecha_hora=INICIO)

    resultado = _repo(db_session).listar(id_clinica)

    assert [c.fecha_hora for c in resultado] == [INICIO, INICIO + timedelta(days=5)]


def test_hay_solapamiento_de_doctor_detecta_el_cruce(db_session):
    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    crear_cita(
        db_session, id_clinica, id_paciente, id_doctor,
        fecha_hora=INICIO, duracion_minutos=60,
    )

    # 09:30-10:00 cae dentro de 09:00-10:00
    assert _repo(db_session).hay_solapamiento_de_doctor(
        id_clinica, id_doctor, INICIO + timedelta(minutes=30), INICIO + timedelta(hours=1)
    ) is True


def test_una_cita_pegada_a_otra_no_es_solapamiento(db_session):
    """El borde: 10:00-10:30 arranca justo cuando 09:00-10:00 termina."""
    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    crear_cita(
        db_session, id_clinica, id_paciente, id_doctor,
        fecha_hora=INICIO, duracion_minutos=60,
    )

    assert _repo(db_session).hay_solapamiento_de_doctor(
        id_clinica, id_doctor, INICIO + timedelta(hours=1), INICIO + timedelta(hours=2)
    ) is False


def test_una_cita_cancelada_no_cuenta_como_choque(db_session):
    from app.models import EstadoCita

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    crear_cita(
        db_session, id_clinica, id_paciente, id_doctor,
        fecha_hora=INICIO, duracion_minutos=60, estado=EstadoCita.CANCELADA,
    )

    assert _repo(db_session).hay_solapamiento_de_doctor(
        id_clinica, id_doctor, INICIO, INICIO + timedelta(hours=1)
    ) is False


def test_excluir_id_cita_evita_que_una_cita_choque_consigo_misma(db_session):
    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    cita = crear_cita(
        db_session, id_clinica, id_paciente, id_doctor,
        fecha_hora=INICIO, duracion_minutos=60,
    )
    repo = _repo(db_session)

    assert repo.hay_solapamiento_de_doctor(
        id_clinica, id_doctor, INICIO, INICIO + timedelta(hours=1)
    ) is True
    assert repo.hay_solapamiento_de_doctor(
        id_clinica, id_doctor, INICIO, INICIO + timedelta(hours=1),
        excluir_id_cita=cita.id_cita,
    ) is False


def test_una_cita_larga_que_empieza_mucho_antes_igual_se_detecta(db_session):
    """Blinda el prefiltro de _solapadas.

    La consulta prefiltra en SQL por una ventana de fechas antes de calcular el
    solapamiento en Python. Si esa ventana fuera mas corta que la duracion
    maxima de una cita, una cita larga que arranca mucho antes quedaria afuera
    del prefiltro y el choque no se detectaria: un falso negativo silencioso,
    que es el peor tipo de bug de agenda.
    """
    from app.repositories.cita_repository import DURACION_MAXIMA_MINUTOS

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    arranque = INICIO - timedelta(minutes=DURACION_MAXIMA_MINUTOS - 30)
    crear_cita(
        db_session, id_clinica, id_paciente, id_doctor,
        fecha_hora=arranque, duracion_minutos=DURACION_MAXIMA_MINUTOS,
    )

    # La cita larga sigue vigente 30 minutos despues de INICIO.
    assert _repo(db_session).hay_solapamiento_de_doctor(
        id_clinica, id_doctor, INICIO, INICIO + timedelta(minutes=15)
    ) is True


def test_el_solapamiento_de_doctor_no_cruza_clinicas(db_session):
    id_clinica_a, id_paciente_a, id_doctor_a = _escenario(db_session, "Dental A", "dra.a")
    clinica_b = crear_clinica(db_session, "Dental B")
    crear_cita(db_session, id_clinica_a, id_paciente_a, id_doctor_a, fecha_hora=INICIO)

    assert _repo(db_session).hay_solapamiento_de_doctor(
        clinica_b.id_clinica, id_doctor_a, INICIO, INICIO + timedelta(minutes=30)
    ) is False


def test_hay_solapamiento_de_consultorio(db_session):
    from app.repositories.consultorio_repository import ConsultorioRepository

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    consultorio = ConsultorioRepository(db_session).crear(id_clinica, {"nombre": "Sala 1"})
    otro_doctor = crear_doctor(db_session, id_clinica, "dr.otro")
    crear_cita(
        db_session, id_clinica, id_paciente, id_doctor,
        fecha_hora=INICIO, duracion_minutos=60,
        id_consultorio=consultorio.id_consultorio,
    )

    # Otro doctor, misma sala, mismo horario: choca igual.
    assert _repo(db_session).hay_solapamiento_de_consultorio(
        id_clinica, consultorio.id_consultorio, INICIO, INICIO + timedelta(minutes=30)
    ) is True
    assert otro_doctor.id_doctor != id_doctor


def test_obtener_de_otra_clinica_devuelve_none(db_session):
    id_clinica_a, id_paciente_a, id_doctor_a = _escenario(db_session, "Dental A", "dra.a")
    clinica_b = crear_clinica(db_session, "Dental B")
    cita = crear_cita(db_session, id_clinica_a, id_paciente_a, id_doctor_a)

    assert _repo(db_session).obtener(clinica_b.id_clinica, cita.id_cita) is None


def test_eliminar_no_esta_soportado(db_session):
    """Una cita no se borra, se cancela: perder el registro romperia el historial
    del paciente y las metricas del Modulo 7.
    """
    import pytest

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    cita = crear_cita(db_session, id_clinica, id_paciente, id_doctor)

    with pytest.raises(NotImplementedError):
        _repo(db_session).eliminar(id_clinica, cita.id_cita)
