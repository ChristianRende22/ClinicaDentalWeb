from app.models import Consultorio
from app.repositories.catalogo_repository import CatalogoRepository


class ConsultorioRepository(CatalogoRepository[Consultorio]):
    model = Consultorio
