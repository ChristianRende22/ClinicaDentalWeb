import pytest


def _clinica(db_session, nombre="Dental A"):
    from app.models import Clinica

    clinica = Clinica(nombre=nombre)
    db_session.add(clinica)
    db_session.flush()
    return clinica


def _repo(db_session):
    from app.repositories.especialidad_repository import EspecialidadRepository

    return EspecialidadRepository(db_session)


def test_crear_devuelve_el_registro_con_la_clinica_correcta(db_session):
    clinica = _clinica(db_session)

    creada = _repo(db_session).crear(clinica.id_clinica, {"nombre": "Ortodoncia"})

    assert creada.id_especialidad is not None
    assert creada.id_clinica == clinica.id_clinica
    assert creada.nombre == "Ortodoncia"
    assert creada.activo is True


def test_crear_recorta_espacios_del_nombre(db_session):
    clinica = _clinica(db_session)

    creada = _repo(db_session).crear(clinica.id_clinica, {"nombre": "  Endodoncia  "})

    assert creada.nombre == "Endodoncia"


def test_crear_con_nombre_duplicado_en_la_misma_clinica_lanza_error(db_session):
    from app.exceptions import NombreDuplicadoEnClinicaError

    clinica = _clinica(db_session)
    repo = _repo(db_session)
    repo.crear(clinica.id_clinica, {"nombre": "Ortodoncia"})

    with pytest.raises(NombreDuplicadoEnClinicaError):
        repo.crear(clinica.id_clinica, {"nombre": "Ortodoncia"})


def test_el_duplicado_se_detecta_sin_importar_mayusculas(db_session):
    from app.exceptions import NombreDuplicadoEnClinicaError

    clinica = _clinica(db_session)
    repo = _repo(db_session)
    repo.crear(clinica.id_clinica, {"nombre": "Ortodoncia"})

    with pytest.raises(NombreDuplicadoEnClinicaError):
        repo.crear(clinica.id_clinica, {"nombre": "ORTODONCIA"})


def test_el_duplicado_se_detecta_tambien_contra_registros_inactivos(db_session):
    from app.exceptions import NombreDuplicadoEnClinicaError

    clinica = _clinica(db_session)
    repo = _repo(db_session)
    creada = repo.crear(clinica.id_clinica, {"nombre": "Ortodoncia"})
    repo.eliminar(clinica.id_clinica, creada.id_especialidad)

    with pytest.raises(NombreDuplicadoEnClinicaError):
        repo.crear(clinica.id_clinica, {"nombre": "Ortodoncia"})


def test_dos_clinicas_pueden_tener_el_mismo_nombre(db_session):
    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    repo = _repo(db_session)

    repo.crear(clinica_a.id_clinica, {"nombre": "Ortodoncia"})
    creada_b = repo.crear(clinica_b.id_clinica, {"nombre": "Ortodoncia"})

    assert creada_b.id_clinica == clinica_b.id_clinica


def test_listar_solo_devuelve_los_de_la_clinica_pedida(db_session):
    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    repo = _repo(db_session)
    repo.crear(clinica_a.id_clinica, {"nombre": "Ortodoncia"})
    repo.crear(clinica_b.id_clinica, {"nombre": "Endodoncia"})

    resultado = repo.listar(clinica_a.id_clinica)

    assert [e.nombre for e in resultado] == ["Ortodoncia"]


def test_listar_omite_los_inactivos_por_defecto(db_session):
    clinica = _clinica(db_session)
    repo = _repo(db_session)
    creada = repo.crear(clinica.id_clinica, {"nombre": "Ortodoncia"})
    repo.crear(clinica.id_clinica, {"nombre": "Endodoncia"})
    repo.eliminar(clinica.id_clinica, creada.id_especialidad)

    assert [e.nombre for e in repo.listar(clinica.id_clinica)] == ["Endodoncia"]


def test_listar_con_incluir_inactivos_devuelve_todos_ordenados_por_nombre(db_session):
    clinica = _clinica(db_session)
    repo = _repo(db_session)
    creada = repo.crear(clinica.id_clinica, {"nombre": "Ortodoncia"})
    repo.crear(clinica.id_clinica, {"nombre": "Endodoncia"})
    repo.eliminar(clinica.id_clinica, creada.id_especialidad)

    nombres = [e.nombre for e in repo.listar(clinica.id_clinica, incluir_inactivos=True)]

    assert nombres == ["Endodoncia", "Ortodoncia"]


def test_obtener_de_otra_clinica_devuelve_none(db_session):
    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    repo = _repo(db_session)
    de_a = repo.crear(clinica_a.id_clinica, {"nombre": "Ortodoncia"})

    assert repo.obtener(clinica_b.id_clinica, de_a.id_especialidad) is None
    assert repo.obtener(clinica_a.id_clinica, de_a.id_especialidad) is not None


def test_obtener_inexistente_devuelve_none(db_session):
    clinica = _clinica(db_session)

    assert _repo(db_session).obtener(clinica.id_clinica, 9999) is None


def test_actualizar_aplica_solo_los_campos_presentes(db_session):
    clinica = _clinica(db_session)
    repo = _repo(db_session)
    creada = repo.crear(clinica.id_clinica, {"nombre": "Ortodoncia"})

    actualizada = repo.actualizar(
        clinica.id_clinica, creada.id_especialidad, {"nombre": "Ortodoncia avanzada"}
    )

    assert actualizada.nombre == "Ortodoncia avanzada"
    assert actualizada.activo is True


def test_actualizar_permite_reactivar(db_session):
    clinica = _clinica(db_session)
    repo = _repo(db_session)
    creada = repo.crear(clinica.id_clinica, {"nombre": "Ortodoncia"})
    repo.eliminar(clinica.id_clinica, creada.id_especialidad)

    reactivada = repo.actualizar(
        clinica.id_clinica, creada.id_especialidad, {"activo": True}
    )

    assert reactivada.activo is True


def test_actualizar_a_un_nombre_ya_usado_lanza_error(db_session):
    from app.exceptions import NombreDuplicadoEnClinicaError

    clinica = _clinica(db_session)
    repo = _repo(db_session)
    repo.crear(clinica.id_clinica, {"nombre": "Ortodoncia"})
    otra = repo.crear(clinica.id_clinica, {"nombre": "Endodoncia"})

    with pytest.raises(NombreDuplicadoEnClinicaError):
        repo.actualizar(clinica.id_clinica, otra.id_especialidad, {"nombre": "Ortodoncia"})


def test_actualizar_con_su_propio_nombre_no_lanza_error(db_session):
    clinica = _clinica(db_session)
    repo = _repo(db_session)
    creada = repo.crear(clinica.id_clinica, {"nombre": "Ortodoncia"})

    actualizada = repo.actualizar(
        clinica.id_clinica, creada.id_especialidad, {"nombre": "Ortodoncia"}
    )

    assert actualizada.nombre == "Ortodoncia"


def test_actualizar_de_otra_clinica_devuelve_none(db_session):
    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    repo = _repo(db_session)
    de_a = repo.crear(clinica_a.id_clinica, {"nombre": "Ortodoncia"})

    assert repo.actualizar(clinica_b.id_clinica, de_a.id_especialidad, {"nombre": "X"}) is None


def test_eliminar_es_borrado_logico(db_session):
    clinica = _clinica(db_session)
    repo = _repo(db_session)
    creada = repo.crear(clinica.id_clinica, {"nombre": "Ortodoncia"})

    assert repo.eliminar(clinica.id_clinica, creada.id_especialidad) is True
    assert repo.obtener(clinica.id_clinica, creada.id_especialidad).activo is False


def test_eliminar_dos_veces_sigue_devolviendo_true(db_session):
    clinica = _clinica(db_session)
    repo = _repo(db_session)
    creada = repo.crear(clinica.id_clinica, {"nombre": "Ortodoncia"})
    repo.eliminar(clinica.id_clinica, creada.id_especialidad)

    assert repo.eliminar(clinica.id_clinica, creada.id_especialidad) is True


def test_eliminar_de_otra_clinica_devuelve_false_y_no_lo_toca(db_session):
    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    repo = _repo(db_session)
    de_a = repo.crear(clinica_a.id_clinica, {"nombre": "Ortodoncia"})

    assert repo.eliminar(clinica_b.id_clinica, de_a.id_especialidad) is False
    assert repo.obtener(clinica_a.id_clinica, de_a.id_especialidad).activo is True


def test_el_repositorio_no_hace_commit(db_session):
    """Los repositorios hacen flush; el commit lo hace la ruta."""
    from app.models import Clinica

    clinica = Clinica(nombre="Dental A")
    db_session.add(clinica)
    db_session.commit()  # la clinica SI queda persistida
    id_clinica = clinica.id_clinica

    _repo(db_session).crear(id_clinica, {"nombre": "Ortodoncia"})
    db_session.rollback()  # deshace lo que el repositorio solo flusheo

    assert _repo(db_session).listar(id_clinica) == []
