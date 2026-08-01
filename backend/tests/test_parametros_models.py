import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError


def _clinica(db_session, nombre="Dental A"):
    from app.models import Clinica

    clinica = Clinica(nombre=nombre)
    db_session.add(clinica)
    db_session.flush()
    return clinica


def test_especialidad_nace_activa(db_session):
    from app.models import Especialidad

    clinica = _clinica(db_session)
    especialidad = Especialidad(id_clinica=clinica.id_clinica, nombre="Ortodoncia")
    db_session.add(especialidad)
    db_session.flush()

    assert especialidad.id_especialidad is not None
    assert especialidad.activo is True


def test_consultorio_y_metodo_pago_nacen_activos(db_session):
    from app.models import Consultorio, MetodoPago

    clinica = _clinica(db_session)
    consultorio = Consultorio(id_clinica=clinica.id_clinica, nombre="Consultorio 1")
    metodo = MetodoPago(id_clinica=clinica.id_clinica, nombre="Efectivo")
    db_session.add_all([consultorio, metodo])
    db_session.flush()

    assert consultorio.activo is True
    assert metodo.activo is True


def test_mismo_nombre_en_dos_clinicas_es_valido(db_session):
    from app.models import Especialidad

    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    db_session.add_all(
        [
            Especialidad(id_clinica=clinica_a.id_clinica, nombre="Ortodoncia"),
            Especialidad(id_clinica=clinica_b.id_clinica, nombre="Ortodoncia"),
        ]
    )

    db_session.flush()  # no debe explotar


def test_mismo_nombre_repetido_en_la_misma_clinica_viola_la_unicidad(db_session):
    from app.models import Especialidad

    clinica = _clinica(db_session)
    db_session.add_all(
        [
            Especialidad(id_clinica=clinica.id_clinica, nombre="Ortodoncia"),
            Especialidad(id_clinica=clinica.id_clinica, nombre="Ortodoncia"),
        ]
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_dia_semana_persiste_el_valor_en_minuscula_no_el_nombre(db_session):
    from datetime import time

    from app.models import DiaSemana, HorarioClinica

    clinica = _clinica(db_session)
    db_session.add(
        HorarioClinica(
            id_clinica=clinica.id_clinica,
            dia_semana=DiaSemana.LUNES,
            hora_apertura=time(8, 0),
            hora_cierre=time(17, 0),
            cerrado=False,
        )
    )
    db_session.flush()

    guardado = db_session.execute(text("SELECT dia_semana FROM horario_clinica")).scalar_one()
    assert guardado == "lunes"


def test_horario_clinica_no_admite_dos_filas_para_el_mismo_dia(db_session):
    from app.models import DiaSemana, HorarioClinica

    clinica = _clinica(db_session)
    db_session.add_all(
        [
            HorarioClinica(id_clinica=clinica.id_clinica, dia_semana=DiaSemana.LUNES),
            HorarioClinica(id_clinica=clinica.id_clinica, dia_semana=DiaSemana.LUNES),
        ]
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_configuracion_clinica_tiene_los_defaults_acordados(db_session):
    from decimal import Decimal

    from app.models import ConfiguracionClinica

    clinica = _clinica(db_session)
    config = ConfiguracionClinica(id_clinica=clinica.id_clinica)
    db_session.add(config)
    db_session.flush()

    assert config.duracion_cita_minutos == 30
    assert Decimal(config.porcentaje_impuesto) == Decimal("13.00")
    assert config.prefijo_factura == "F"
    assert config.proximo_numero_factura == 1
    assert config.horas_minimas_cambio_cita == 24
    assert config.dias_minimos_reagendamiento == 3


def test_horario_por_defecto_cubre_los_siete_dias_con_fin_de_semana_cerrado():
    from datetime import time

    from app.models import HORARIO_POR_DEFECTO, DiaSemana

    assert set(HORARIO_POR_DEFECTO) == set(DiaSemana)

    assert HORARIO_POR_DEFECTO[DiaSemana.LUNES] == {
        "hora_apertura": time(8, 0),
        "hora_cierre": time(17, 0),
        "cerrado": False,
    }
    for dia in (DiaSemana.SABADO, DiaSemana.DOMINGO):
        assert HORARIO_POR_DEFECTO[dia] == {
            "hora_apertura": None,
            "hora_cierre": None,
            "cerrado": True,
        }
