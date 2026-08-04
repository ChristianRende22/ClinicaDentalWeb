from tests.factories import crear_clinica, crear_usuario


def _repo(db_session):
    from app.repositories.doctor_repository import DoctorRepository

    return DoctorRepository(db_session)


def _datos(db_session, id_clinica, username="dra.perez", **campos):
    from app.models import RolUsuario

    usuario = crear_usuario(db_session, RolUsuario.DOCTOR, id_clinica, username)
    base = {
        "id_usuario": usuario.id_usuario,
        "nombre": "Marta",
        "apellido": "Perez",
        "telefono": "70003344",
    }
    base.update(campos)
    return base


def _especialidad(db_session, id_clinica, nombre="Ortodoncia"):
    from app.repositories.especialidad_repository import EspecialidadRepository

    return EspecialidadRepository(db_session).crear(id_clinica, {"nombre": nombre})


def test_crear_devuelve_el_doctor_activo_sin_especialidad(db_session):
    clinica = crear_clinica(db_session)

    creado = _repo(db_session).crear(
        clinica.id_clinica, _datos(db_session, clinica.id_clinica)
    )

    assert creado.id_doctor is not None
    assert creado.activo is True
    assert creado.id_especialidad is None


def test_listar_solo_devuelve_los_de_la_clinica_pedida(db_session):
    clinica_a = crear_clinica(db_session, "Dental A")
    clinica_b = crear_clinica(db_session, "Dental B")
    repo = _repo(db_session)
    repo.crear(clinica_a.id_clinica, _datos(db_session, clinica_a.id_clinica, "dra.a"))
    repo.crear(clinica_b.id_clinica, _datos(db_session, clinica_b.id_clinica, "dr.b"))

    assert len(repo.listar(clinica_a.id_clinica)) == 1


def test_listar_filtra_por_especialidad(db_session):
    clinica = crear_clinica(db_session)
    orto = _especialidad(db_session, clinica.id_clinica, "Ortodoncia")
    endo = _especialidad(db_session, clinica.id_clinica, "Endodoncia")
    repo = _repo(db_session)
    repo.crear(
        clinica.id_clinica,
        _datos(db_session, clinica.id_clinica, "dra.a", nombre="Ana",
               id_especialidad=orto.id_especialidad),
    )
    repo.crear(
        clinica.id_clinica,
        _datos(db_session, clinica.id_clinica, "dr.b", nombre="Beto",
               id_especialidad=endo.id_especialidad),
    )

    resultado = repo.listar(clinica.id_clinica, id_especialidad=orto.id_especialidad)

    assert [d.nombre for d in resultado] == ["Ana"]


def test_listar_ordena_por_apellido_y_nombre(db_session):
    clinica = crear_clinica(db_session)
    repo = _repo(db_session)
    repo.crear(
        clinica.id_clinica,
        _datos(db_session, clinica.id_clinica, "dr.z", nombre="Zoe", apellido="Ayala"),
    )
    repo.crear(
        clinica.id_clinica,
        _datos(db_session, clinica.id_clinica, "dra.a", nombre="Ana", apellido="Ayala"),
    )

    assert [d.nombre for d in repo.listar(clinica.id_clinica)] == ["Ana", "Zoe"]


def test_listar_omite_los_inactivos_por_defecto(db_session):
    clinica = crear_clinica(db_session)
    repo = _repo(db_session)
    creado = repo.crear(clinica.id_clinica, _datos(db_session, clinica.id_clinica))
    repo.eliminar(clinica.id_clinica, creado.id_doctor)

    assert repo.listar(clinica.id_clinica) == []
    assert len(repo.listar(clinica.id_clinica, incluir_inactivos=True)) == 1


def test_obtener_de_otra_clinica_devuelve_none(db_session):
    clinica_a = crear_clinica(db_session, "Dental A")
    clinica_b = crear_clinica(db_session, "Dental B")
    repo = _repo(db_session)
    de_a = repo.crear(clinica_a.id_clinica, _datos(db_session, clinica_a.id_clinica))

    assert repo.obtener(clinica_b.id_clinica, de_a.id_doctor) is None


def test_obtener_por_usuario_traduce_el_jwt_a_un_perfil(db_session):
    clinica = crear_clinica(db_session)
    repo = _repo(db_session)
    datos = _datos(db_session, clinica.id_clinica)
    creado = repo.crear(clinica.id_clinica, datos)

    encontrado = repo.obtener_por_usuario(datos["id_usuario"])

    assert encontrado.id_doctor == creado.id_doctor


def test_obtener_por_usuario_de_alguien_sin_perfil_devuelve_none(db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    usuario = crear_usuario(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")

    assert _repo(db_session).obtener_por_usuario(usuario.id_usuario) is None


def test_actualizar_aplica_solo_los_campos_presentes(db_session):
    clinica = crear_clinica(db_session)
    repo = _repo(db_session)
    creado = repo.crear(clinica.id_clinica, _datos(db_session, clinica.id_clinica))

    actualizado = repo.actualizar(
        clinica.id_clinica, creado.id_doctor, {"telefono": "70009999"}
    )

    assert actualizado.telefono == "70009999"
    assert actualizado.nombre == "Marta"


def test_eliminar_es_borrado_logico_y_no_cruza_clinicas(db_session):
    clinica_a = crear_clinica(db_session, "Dental A")
    clinica_b = crear_clinica(db_session, "Dental B")
    repo = _repo(db_session)
    de_a = repo.crear(clinica_a.id_clinica, _datos(db_session, clinica_a.id_clinica))

    assert repo.eliminar(clinica_b.id_clinica, de_a.id_doctor) is False
    assert repo.eliminar(clinica_a.id_clinica, de_a.id_doctor) is True
    assert repo.obtener(clinica_a.id_clinica, de_a.id_doctor).activo is False
