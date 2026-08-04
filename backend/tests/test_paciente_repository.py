from tests.factories import crear_clinica


def _repo(db_session):
    from app.repositories.paciente_repository import PacienteRepository

    return PacienteRepository(db_session)


def _datos(**campos):
    base = {"nombre": "Ana", "apellido": "Lopez", "telefono": "70001122"}
    base.update(campos)
    return base


def test_crear_devuelve_el_paciente_activo_en_su_clinica(db_session):
    clinica = crear_clinica(db_session)

    creado = _repo(db_session).crear(clinica.id_clinica, _datos())

    assert creado.id_paciente is not None
    assert creado.id_clinica == clinica.id_clinica
    assert creado.activo is True


def test_listar_solo_devuelve_los_de_la_clinica_pedida(db_session):
    clinica_a = crear_clinica(db_session, "Dental A")
    clinica_b = crear_clinica(db_session, "Dental B")
    repo = _repo(db_session)
    repo.crear(clinica_a.id_clinica, _datos(nombre="Ana"))
    repo.crear(clinica_b.id_clinica, _datos(nombre="Beto"))

    assert [p.nombre for p in repo.listar(clinica_a.id_clinica)] == ["Ana"]


def test_listar_ordena_por_apellido_y_nombre(db_session):
    clinica = crear_clinica(db_session)
    repo = _repo(db_session)
    repo.crear(clinica.id_clinica, _datos(nombre="Zoe", apellido="Ayala"))
    repo.crear(clinica.id_clinica, _datos(nombre="Ana", apellido="Zamora"))
    repo.crear(clinica.id_clinica, _datos(nombre="Ana", apellido="Ayala"))

    resultado = repo.listar(clinica.id_clinica)

    assert [(p.apellido, p.nombre) for p in resultado] == [
        ("Ayala", "Ana"),
        ("Ayala", "Zoe"),
        ("Zamora", "Ana"),
    ]


def test_buscar_encuentra_por_nombre_o_apellido_sin_importar_mayusculas(db_session):
    clinica = crear_clinica(db_session)
    repo = _repo(db_session)
    repo.crear(clinica.id_clinica, _datos(nombre="Ana", apellido="Lopez"))
    repo.crear(clinica.id_clinica, _datos(nombre="Beto", apellido="Martinez"))

    assert [p.nombre for p in repo.listar(clinica.id_clinica, buscar="LOP")] == ["Ana"]
    assert [p.nombre for p in repo.listar(clinica.id_clinica, buscar="bet")] == ["Beto"]


def test_buscar_no_cruza_clinicas(db_session):
    clinica_a = crear_clinica(db_session, "Dental A")
    clinica_b = crear_clinica(db_session, "Dental B")
    repo = _repo(db_session)
    repo.crear(clinica_b.id_clinica, _datos(nombre="Ana", apellido="Lopez"))

    assert repo.listar(clinica_a.id_clinica, buscar="Lopez") == []


def test_listar_omite_los_inactivos_por_defecto(db_session):
    clinica = crear_clinica(db_session)
    repo = _repo(db_session)
    creado = repo.crear(clinica.id_clinica, _datos(nombre="Ana"))
    repo.crear(clinica.id_clinica, _datos(nombre="Beto"))
    repo.eliminar(clinica.id_clinica, creado.id_paciente)

    assert [p.nombre for p in repo.listar(clinica.id_clinica)] == ["Beto"]
    assert len(repo.listar(clinica.id_clinica, incluir_inactivos=True)) == 2


def test_obtener_de_otra_clinica_devuelve_none(db_session):
    clinica_a = crear_clinica(db_session, "Dental A")
    clinica_b = crear_clinica(db_session, "Dental B")
    repo = _repo(db_session)
    de_a = repo.crear(clinica_a.id_clinica, _datos())

    assert repo.obtener(clinica_b.id_clinica, de_a.id_paciente) is None
    assert repo.obtener(clinica_a.id_clinica, de_a.id_paciente) is not None


def test_actualizar_aplica_solo_los_campos_presentes(db_session):
    clinica = crear_clinica(db_session)
    repo = _repo(db_session)
    creado = repo.crear(clinica.id_clinica, _datos())

    actualizado = repo.actualizar(
        clinica.id_clinica, creado.id_paciente, {"telefono": "70009999"}
    )

    assert actualizado.telefono == "70009999"
    assert actualizado.nombre == "Ana"


def test_actualizar_de_otra_clinica_devuelve_none(db_session):
    clinica_a = crear_clinica(db_session, "Dental A")
    clinica_b = crear_clinica(db_session, "Dental B")
    repo = _repo(db_session)
    de_a = repo.crear(clinica_a.id_clinica, _datos())

    assert repo.actualizar(clinica_b.id_clinica, de_a.id_paciente, {"nombre": "X"}) is None


def test_eliminar_es_borrado_logico_e_idempotente(db_session):
    clinica = crear_clinica(db_session)
    repo = _repo(db_session)
    creado = repo.crear(clinica.id_clinica, _datos())

    assert repo.eliminar(clinica.id_clinica, creado.id_paciente) is True
    assert repo.obtener(clinica.id_clinica, creado.id_paciente).activo is False
    assert repo.eliminar(clinica.id_clinica, creado.id_paciente) is True


def test_eliminar_de_otra_clinica_devuelve_false_y_no_lo_toca(db_session):
    clinica_a = crear_clinica(db_session, "Dental A")
    clinica_b = crear_clinica(db_session, "Dental B")
    repo = _repo(db_session)
    de_a = repo.crear(clinica_a.id_clinica, _datos())

    assert repo.eliminar(clinica_b.id_clinica, de_a.id_paciente) is False
    assert repo.obtener(clinica_a.id_clinica, de_a.id_paciente).activo is True


def test_el_repositorio_no_hace_commit(db_session):
    clinica = crear_clinica(db_session)
    db_session.commit()
    id_clinica = clinica.id_clinica

    _repo(db_session).crear(id_clinica, _datos())
    db_session.rollback()

    assert _repo(db_session).listar(id_clinica) == []
