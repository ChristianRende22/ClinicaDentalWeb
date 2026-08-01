from datetime import time

import pytest


def _clinica(db_session, nombre="Dental A"):
    from app.models import Clinica

    clinica = Clinica(nombre=nombre)
    db_session.add(clinica)
    db_session.flush()
    return clinica


def _semana_laboral():
    from app.models import DiaSemana

    dias = []
    for dia in DiaSemana:
        if dia in (DiaSemana.SABADO, DiaSemana.DOMINGO):
            dias.append(
                {"dia_semana": dia, "hora_apertura": None, "hora_cierre": None, "cerrado": True}
            )
        else:
            dias.append(
                {
                    "dia_semana": dia,
                    "hora_apertura": time(8, 0),
                    "hora_cierre": time(17, 0),
                    "cerrado": False,
                }
            )
    return dias


def _repo(db_session):
    from app.repositories.horario_clinica_repository import HorarioClinicaRepository

    return HorarioClinicaRepository(db_session)


def test_listar_semana_sin_datos_devuelve_vacio(db_session):
    clinica = _clinica(db_session)

    assert _repo(db_session).listar_semana(clinica.id_clinica) == []


def test_reemplazar_semana_crea_los_siete_dias_ordenados(db_session):
    from app.models import DiaSemana

    clinica = _clinica(db_session)

    _repo(db_session).reemplazar_semana(clinica.id_clinica, _semana_laboral())

    guardados = _repo(db_session).listar_semana(clinica.id_clinica)
    assert [f.dia_semana for f in guardados] == list(DiaSemana)
    assert guardados[0].hora_apertura == time(8, 0)
    assert guardados[-1].cerrado is True


def test_reemplazar_semana_dos_veces_actualiza_en_vez_de_duplicar(db_session):
    clinica = _clinica(db_session)
    repo = _repo(db_session)
    repo.reemplazar_semana(clinica.id_clinica, _semana_laboral())

    nueva = _semana_laboral()
    nueva[0]["hora_cierre"] = time(20, 0)
    repo.reemplazar_semana(clinica.id_clinica, nueva)

    guardados = repo.listar_semana(clinica.id_clinica)
    assert len(guardados) == 7
    assert guardados[0].hora_cierre == time(20, 0)


def test_un_dia_cerrado_guarda_las_horas_en_null(db_session):
    from app.models import DiaSemana

    clinica = _clinica(db_session)
    dias = _semana_laboral()
    dias[0] = {
        "dia_semana": DiaSemana.LUNES,
        "hora_apertura": time(8, 0),
        "hora_cierre": time(17, 0),
        "cerrado": True,
    }

    _repo(db_session).reemplazar_semana(clinica.id_clinica, dias)

    lunes = _repo(db_session).listar_semana(clinica.id_clinica)[0]
    assert lunes.cerrado is True
    assert lunes.hora_apertura is None
    assert lunes.hora_cierre is None


def test_hora_de_cierre_anterior_a_la_de_apertura_lanza_error(db_session):
    from app.exceptions import HorarioInvalidoError

    clinica = _clinica(db_session)
    dias = _semana_laboral()
    dias[0]["hora_cierre"] = time(7, 0)

    with pytest.raises(HorarioInvalidoError):
        _repo(db_session).reemplazar_semana(clinica.id_clinica, dias)


def test_dia_abierto_sin_horas_lanza_error(db_session):
    from app.exceptions import HorarioInvalidoError

    clinica = _clinica(db_session)
    dias = _semana_laboral()
    dias[0]["hora_apertura"] = None

    with pytest.raises(HorarioInvalidoError):
        _repo(db_session).reemplazar_semana(clinica.id_clinica, dias)


def test_si_un_dia_es_invalido_no_se_guarda_ninguno(db_session):
    from app.exceptions import HorarioInvalidoError

    clinica = _clinica(db_session)
    dias = _semana_laboral()
    dias[4]["hora_cierre"] = time(1, 0)

    with pytest.raises(HorarioInvalidoError):
        _repo(db_session).reemplazar_semana(clinica.id_clinica, dias)

    assert _repo(db_session).listar_semana(clinica.id_clinica) == []


def test_el_horario_de_una_clinica_no_afecta_a_otra(db_session):
    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")

    _repo(db_session).reemplazar_semana(clinica_a.id_clinica, _semana_laboral())

    assert len(_repo(db_session).listar_semana(clinica_a.id_clinica)) == 7
    assert _repo(db_session).listar_semana(clinica_b.id_clinica) == []
