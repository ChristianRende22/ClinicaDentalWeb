def _clinica(db_session):
    from app.models import Clinica

    clinica = Clinica(nombre="Dental A")
    db_session.add(clinica)
    db_session.flush()
    return clinica


def test_apunta_al_modelo_metodo_pago():
    from app.models import MetodoPago
    from app.repositories.metodo_pago_repository import MetodoPagoRepository

    assert MetodoPagoRepository.model is MetodoPago


def test_hereda_el_crud_del_catalogo(db_session):
    from app.repositories.catalogo_repository import CatalogoRepository
    from app.repositories.metodo_pago_repository import MetodoPagoRepository

    assert issubclass(MetodoPagoRepository, CatalogoRepository)

    clinica = _clinica(db_session)
    repo = MetodoPagoRepository(db_session)
    creado = repo.crear(clinica.id_clinica, {"nombre": "Efectivo"})

    assert repo.obtener(clinica.id_clinica, creado.id_metodo_pago) is creado
