from app.models import MetodoPago
from app.repositories.catalogo_repository import CatalogoRepository


class MetodoPagoRepository(CatalogoRepository[MetodoPago]):
    model = MetodoPago
