import pytest

from tests.factories import crear_clinica, crear_paciente


def _repo(db):
    from app.repositories.odontograma_repository import OdontogramaRepository

    return OdontogramaRepository(db)


def test_obtener_o_crear_es_idempotente(db_session):
    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)

    primero = _repo(db_session).obtener_o_crear(clinica.id_clinica, paciente.id_paciente)
    segundo = _repo(db_session).obtener_o_crear(clinica.id_clinica, paciente.id_paciente)
    assert primero.id_odontograma == segundo.id_odontograma


def test_listar_piezas_sin_tocar_devuelve_32_todas_sanas(db_session):
    from app.models import EstadoPiezaDental

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)

    piezas = _repo(db_session).listar_piezas(clinica.id_clinica, paciente.id_paciente)
    assert len(piezas) == 32
    assert {p.numero_pieza for p in piezas} == set(range(1, 33))
    assert all(p.estado == EstadoPiezaDental.SANO for p in piezas)


def test_actualizar_pieza_crea_si_no_existe_y_actualiza_si_existe(db_session):
    from app.models import EstadoPiezaDental

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)

    _repo(db_session).actualizar_pieza(
        clinica.id_clinica, paciente.id_paciente, 8, {"estado": EstadoPiezaDental.CARIADO}
    )
    piezas = _repo(db_session).listar_piezas(clinica.id_clinica, paciente.id_paciente)
    pieza_8 = next(p for p in piezas if p.numero_pieza == 8)
    assert pieza_8.estado == EstadoPiezaDental.CARIADO

    _repo(db_session).actualizar_pieza(
        clinica.id_clinica, paciente.id_paciente, 8, {"estado": EstadoPiezaDental.OBTURADO}
    )
    piezas = _repo(db_session).listar_piezas(clinica.id_clinica, paciente.id_paciente)
    assert len([p for p in piezas if p.numero_pieza == 8]) == 1
    pieza_8 = next(p for p in piezas if p.numero_pieza == 8)
    assert pieza_8.estado == EstadoPiezaDental.OBTURADO


def test_actualizar_pieza_no_toca_las_demas(db_session):
    from app.models import EstadoPiezaDental

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)

    _repo(db_session).actualizar_pieza(
        clinica.id_clinica, paciente.id_paciente, 8, {"estado": EstadoPiezaDental.CARIADO}
    )
    piezas = _repo(db_session).listar_piezas(clinica.id_clinica, paciente.id_paciente)
    otras = [p for p in piezas if p.numero_pieza != 8]
    assert all(p.estado == EstadoPiezaDental.SANO for p in otras)


def test_numero_pieza_fuera_de_rango_lanza_value_error(db_session):
    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)

    with pytest.raises(ValueError):
        _repo(db_session).actualizar_pieza(clinica.id_clinica, paciente.id_paciente, 33, {})
    with pytest.raises(ValueError):
        _repo(db_session).actualizar_pieza(clinica.id_clinica, paciente.id_paciente, 0, {})


def test_listar_piezas_de_un_paciente_no_ve_las_de_otro(db_session):
    from app.models import EstadoPiezaDental

    clinica = crear_clinica(db_session)
    paciente_1 = crear_paciente(db_session, clinica.id_clinica, telefono="70001111")
    paciente_2 = crear_paciente(db_session, clinica.id_clinica, telefono="70002222")

    _repo(db_session).actualizar_pieza(
        clinica.id_clinica, paciente_1.id_paciente, 8, {"estado": EstadoPiezaDental.CARIADO}
    )
    piezas_2 = _repo(db_session).listar_piezas(clinica.id_clinica, paciente_2.id_paciente)
    assert all(p.estado == EstadoPiezaDental.SANO for p in piezas_2)


def test_repositorio_no_valida_que_el_paciente_sea_de_la_clinica(db_session):
    """Documenta una decision, no un bug: igual que HorarioDoctorRepository,
    este repositorio no valida que id_paciente pertenezca a id_clinica -- esa
    verificacion es responsabilidad de la ruta (obtener el Paciente primero
    con PacienteRepository.obtener(id_clinica, id_paciente) y 404 si no
    existe), igual que ya hacen doctores.py y asistentes.py con el horario.
    """
    clinica_a = crear_clinica(db_session, nombre="A")
    clinica_b = crear_clinica(db_session, nombre="B")
    paciente = crear_paciente(db_session, clinica_a.id_clinica)

    _repo(db_session).obtener_o_crear(clinica_a.id_clinica, paciente.id_paciente)
    # id_paciente es UNIQUE (1:1): un segundo intento con otra clinica choca
    # contra el mismo paciente en vez de crear un odontograma nuevo.
    from sqlalchemy.exc import IntegrityError

    try:
        _repo(db_session).obtener_o_crear(clinica_b.id_clinica, paciente.id_paciente)
        assert False, "debia lanzar IntegrityError"
    except IntegrityError:
        db_session.rollback()
