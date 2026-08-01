from app.models import Especialidad
from app.repositories.catalogo_repository import CatalogoRepository


class EspecialidadRepository(CatalogoRepository[Especialidad]):
    model = Especialidad
