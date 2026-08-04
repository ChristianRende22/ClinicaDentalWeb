from datetime import time

import pytest

from tests.factories import crear_clinica, crear_doctor


def _repo(db_session):
    from app.repositories.horario_doctor_repository import HorarioDoctorRepository

    return HorarioDoctorRepository(db_session)


def _bloque(dia, inicio=(8, 0), fin=(12, 0), disponible=True):
    return {
        "dia_semana": dia,
        "hora_inicio": time(*inicio),
        "hora_fin": time(*fin),
        "disponible": disponible,
    }


def test_reemplazar_crea_los_bloques(db_session):
    from app.models import DiaSemana

    clinica = crear_clinica(db_session)
    doctor = crear_doctor(db_session, clinica.id_clinica)

    creados = _repo(db_session).reemplazar_de_doctor(
        clinica.id_clinica,
        doctor.id_doctor,
        [_bloque(DiaSemana.LUNES), _bloque(DiaSemana.LUNES, (14, 0), (18, 0))],
    )

    assert len(creados) == 2


def test_reemplazar_borra_los_bloques_anteriores(db_session):
    from app.models import DiaSemana

    clinica = crear_clinica(db_session)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    repo = _repo(db_session)
    repo.reemplazar_de_doctor(
        clinica.id_clinica, doctor.id_doctor, [_bloque(DiaSemana.LUNES)]
    )

    repo.reemplazar_de_doctor(
        clinica.id_clinica, doctor.id_doctor, [_bloque(DiaSemana.MARTES)]
    )

    dias = [b.dia_semana for b in repo.listar_de_doctor(clinica.id_clinica, doctor.id_doctor)]
    assert dias == [DiaSemana.MARTES]


def test_listar_ordena_de_lunes_a_domingo_y_por_hora(db_session):
    from app.models import DiaSemana

    clinica = crear_clinica(db_session)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    repo = _repo(db_session)
    repo.reemplazar_de_doctor(
        clinica.id_clinica,
        doctor.id_doctor,
        [
            _bloque(DiaSemana.MIERCOLES),
            _bloque(DiaSemana.LUNES, (14, 0), (18, 0)),
            _bloque(DiaSemana.LUNES, (8, 0), (12, 0)),
        ],
    )

    resultado = repo.listar_de_doctor(clinica.id_clinica, doctor.id_doctor)

    assert [(b.dia_semana, b.hora_inicio) for b in resultado] == [
        (DiaSemana.LUNES, time(8, 0)),
        (DiaSemana.LUNES, time(14, 0)),
        (DiaSemana.MIERCOLES, time(8, 0)),
    ]


def test_listar_un_doctor_de_otra_clinica_devuelve_lista_vacia(db_session):
    from app.models import DiaSemana

    clinica_a = crear_clinica(db_session, "Dental A")
    clinica_b = crear_clinica(db_session, "Dental B")
    doctor_a = crear_doctor(db_session, clinica_a.id_clinica, "dra.a")
    repo = _repo(db_session)
    repo.reemplazar_de_doctor(
        clinica_a.id_clinica, doctor_a.id_doctor, [_bloque(DiaSemana.LUNES)]
    )

    assert repo.listar_de_doctor(clinica_b.id_clinica, doctor_a.id_doctor) == []


def test_reemplazar_el_horario_de_un_doctor_ajeno_no_lo_toca(db_session):
    from app.models import DiaSemana

    clinica_a = crear_clinica(db_session, "Dental A")
    clinica_b = crear_clinica(db_session, "Dental B")
    doctor_a = crear_doctor(db_session, clinica_a.id_clinica, "dra.a")
    repo = _repo(db_session)
    repo.reemplazar_de_doctor(
        clinica_a.id_clinica, doctor_a.id_doctor, [_bloque(DiaSemana.LUNES)]
    )

    resultado = repo.reemplazar_de_doctor(
        clinica_b.id_clinica, doctor_a.id_doctor, [_bloque(DiaSemana.MARTES)]
    )

    assert resultado == []
    dias = [b.dia_semana for b in repo.listar_de_doctor(clinica_a.id_clinica, doctor_a.id_doctor)]
    assert dias == [DiaSemana.LUNES]


def test_bloque_con_fin_menor_o_igual_al_inicio_es_invalido(db_session):
    from app.exceptions import HorarioInvalidoError
    from app.models import DiaSemana

    clinica = crear_clinica(db_session)
    doctor = crear_doctor(db_session, clinica.id_clinica)

    with pytest.raises(HorarioInvalidoError):
        _repo(db_session).reemplazar_de_doctor(
            clinica.id_clinica,
            doctor.id_doctor,
            [_bloque(DiaSemana.LUNES, (12, 0), (8, 0))],
        )


def test_dos_bloques_solapados_el_mismo_dia_son_invalidos(db_session):
    from app.exceptions import HorarioInvalidoError
    from app.models import DiaSemana

    clinica = crear_clinica(db_session)
    doctor = crear_doctor(db_session, clinica.id_clinica)

    with pytest.raises(HorarioInvalidoError):
        _repo(db_session).reemplazar_de_doctor(
            clinica.id_clinica,
            doctor.id_doctor,
            [
                _bloque(DiaSemana.LUNES, (8, 0), (12, 0)),
                _bloque(DiaSemana.LUNES, (11, 0), (14, 0)),
            ],
        )


def test_dos_bloques_pegados_el_mismo_dia_son_validos(db_session):
    """Uno que termina justo cuando arranca el otro no se solapa."""
    from app.models import DiaSemana

    clinica = crear_clinica(db_session)
    doctor = crear_doctor(db_session, clinica.id_clinica)

    creados = _repo(db_session).reemplazar_de_doctor(
        clinica.id_clinica,
        doctor.id_doctor,
        [
            _bloque(DiaSemana.LUNES, (8, 0), (12, 0)),
            _bloque(DiaSemana.LUNES, (12, 0), (16, 0)),
        ],
    )

    assert len(creados) == 2


def test_valida_todos_los_bloques_antes_de_escribir_ninguno(db_session):
    from app.exceptions import HorarioInvalidoError
    from app.models import DiaSemana

    clinica = crear_clinica(db_session)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    repo = _repo(db_session)

    with pytest.raises(HorarioInvalidoError):
        repo.reemplazar_de_doctor(
            clinica.id_clinica,
            doctor.id_doctor,
            [_bloque(DiaSemana.LUNES), _bloque(DiaSemana.MARTES, (12, 0), (8, 0))],
        )

    assert repo.listar_de_doctor(clinica.id_clinica, doctor.id_doctor) == []
