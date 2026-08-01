def _clinica(db_session):
    from app.models import Clinica

    clinica = Clinica(nombre="Dental A")
    db_session.add(clinica)
    db_session.flush()
    return clinica


def test_apunta_al_modelo_consultorio():
    from app.models import Consultorio
    from app.repositories.consultorio_repository import ConsultorioRepository

    assert ConsultorioRepository.model is Consultorio


def test_hereda_el_crud_del_catalogo(db_session):
    from app.repositories.catalogo_repository import CatalogoRepository
    from app.repositories.consultorio_repository import ConsultorioRepository

    assert issubclass(ConsultorioRepository, CatalogoRepository)

    clinica = _clinica(db_session)
    repo = ConsultorioRepository(db_session)
    creado = repo.crear(clinica.id_clinica, {"nombre": "Consultorio 1"})

    assert repo.obtener(clinica.id_clinica, creado.id_consultorio) is creado
