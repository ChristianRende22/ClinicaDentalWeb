from decimal import Decimal


def _clinica(db_session, nombre="Dental A"):
    from app.models import Clinica

    clinica = Clinica(nombre=nombre)
    db_session.add(clinica)
    db_session.flush()
    return clinica


def _repo(db_session):
    from app.repositories.configuracion_repository import ConfiguracionClinicaRepository

    return ConfiguracionClinicaRepository(db_session)


def test_obtener_o_crear_crea_con_los_defaults(db_session):
    clinica = _clinica(db_session)

    config = _repo(db_session).obtener_o_crear(clinica.id_clinica)

    assert config.id_clinica == clinica.id_clinica
    assert config.duracion_cita_minutos == 30
    assert Decimal(config.porcentaje_impuesto) == Decimal("13.00")
    assert config.horas_minimas_cambio_cita == 24
    assert config.dias_minimos_reagendamiento == 3


def test_obtener_o_crear_es_idempotente(db_session):
    from app.models import ConfiguracionClinica

    clinica = _clinica(db_session)
    repo = _repo(db_session)

    primera = repo.obtener_o_crear(clinica.id_clinica)
    segunda = repo.obtener_o_crear(clinica.id_clinica)

    assert primera is segunda
    assert db_session.query(ConfiguracionClinica).count() == 1


def test_actualizar_aplica_solo_los_campos_presentes(db_session):
    clinica = _clinica(db_session)
    repo = _repo(db_session)
    repo.obtener_o_crear(clinica.id_clinica)

    config = repo.actualizar(clinica.id_clinica, {"duracion_cita_minutos": 45})

    assert config.duracion_cita_minutos == 45
    assert Decimal(config.porcentaje_impuesto) == Decimal("13.00")


def test_actualizar_sobre_una_clinica_sin_configuracion_la_crea(db_session):
    clinica = _clinica(db_session)

    config = _repo(db_session).actualizar(clinica.id_clinica, {"prefijo_factura": "FAC"})

    assert config.prefijo_factura == "FAC"
    assert config.duracion_cita_minutos == 30


def test_la_configuracion_de_una_clinica_no_afecta_a_otra(db_session):
    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    repo = _repo(db_session)

    repo.actualizar(clinica_a.id_clinica, {"duracion_cita_minutos": 60})

    assert repo.obtener_o_crear(clinica_b.id_clinica).duracion_cita_minutos == 30
