from app.exceptions import ReferenciaEnUsoError
from app.models import Tratamiento
from app.repositories.catalogo_repository import CatalogoRepository


class TratamientoRepository(CatalogoRepository[Tratamiento]):
    """Catalogo de procedimientos con precio. Hereda el CRUD de CatalogoRepository
    (nombre unico por clinica, borrado logico) y solo agrega el chequeo de uso
    antes de dar de baja -- ver seccion 1 del spec del Modulo 5.
    """

    model = Tratamiento

    def eliminar(self, id_clinica: int, id_: int) -> bool:
        # Import adentro del metodo para evitar el ciclo: plan_tratamiento_repository
        # no depende de este archivo, pero este necesita saber de aquel. Mismo
        # patron que validadores_por_defecto en validadores_cita.py.
        from app.repositories.plan_tratamiento_repository import (
            PlanTratamientoDetalleRepository,
        )

        if PlanTratamientoDetalleRepository(self.db).existe_activo_con_tratamiento(
            id_clinica, id_
        ):
            raise ReferenciaEnUsoError(
                "No se puede dar de baja: hay un plan de tratamiento activo que usa "
                "este tratamiento"
            )
        return super().eliminar(id_clinica, id_)
