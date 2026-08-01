def _clinica(db_session):
    from app.models import Clinica

    clinica = Clinica(nombre="Dental A")
    db_session.add(clinica)
    db_session.flush()
    return clinica


def test_apunta_al_modelo_especialidad():
    from app.models import Especialidad
    from app.repositories.especialidad_repository import EspecialidadRepository

    assert EspecialidadRepository.model is Especialidad


def test_hereda_el_crud_del_catalogo(db_session):
    from app.repositories.catalogo_repository import CatalogoRepository
    from app.repositories.especialidad_repository import EspecialidadRepository

    assert issubclass(EspecialidadRepository, CatalogoRepository)

    clinica = _clinica(db_session)
    repo = EspecialidadRepository(db_session)
    creada = repo.crear(clinica.id_clinica, {"nombre": "Ortodoncia"})

    assert repo.obtener(clinica.id_clinica, creada.id_especialidad) is creada
