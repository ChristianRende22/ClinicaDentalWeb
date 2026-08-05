from decimal import Decimal

from sqlalchemy.orm import Session

from app.exceptions import TransicionInvalidaError
from app.models import (
    TRANSICIONES_PRESUPUESTO_PERMITIDAS,
    EstadoDetallePlanTratamiento,
    EstadoPresupuesto,
    Presupuesto,
)
from app.repositories.plan_tratamiento_repository import PlanTratamientoDetalleRepository
from app.repositories.presupuesto_repository import PresupuestoRepository


class PresupuestoService:
    """generar_o_regenerar hace upsert (decision 2 del spec: un presupuesto es
    la foto del total de un plan en un momento dado, no se versiona).
    """

    def __init__(self, db: Session):
        self.db = db
        self.presupuestos = PresupuestoRepository(db)
        self.detalles = PlanTratamientoDetalleRepository(db)

    def _calcular_total(self, id_clinica: int, id_plan: int) -> Decimal:
        """Suma todos los detalles NO cancelados: pendiente, en_progreso y
        completado. Un detalle cancelado es trabajo que no se va a hacer ni a
        cobrar, y no aporta al total.
        """
        detalles = self.detalles.listar_de_plan(id_clinica, id_plan)
        total = Decimal("0.00")
        for detalle in detalles:
            if detalle.estado == EstadoDetallePlanTratamiento.CANCELADO:
                continue
            total += Decimal(str(detalle.precio_unitario)) * detalle.cantidad
        return total

    def generar_o_regenerar(self, id_clinica: int, id_plan: int) -> Presupuesto:
        total = self._calcular_total(id_clinica, id_plan)
        existente = self.presupuestos.obtener_por_plan(id_clinica, id_plan)
        if existente is None:
            return self.presupuestos.crear(
                id_clinica, {"id_plan": id_plan, "monto_total": str(total)}
            )
        return self.presupuestos.actualizar(
            id_clinica, existente.id_presupuesto, {"monto_total": str(total)}
        )

    @staticmethod
    def _exigir_transicion(actual: EstadoPresupuesto, nuevo: EstadoPresupuesto) -> None:
        if nuevo not in TRANSICIONES_PRESUPUESTO_PERMITIDAS[actual]:
            raise TransicionInvalidaError(
                f"Un presupuesto en estado '{actual.value}' no puede pasar a '{nuevo.value}'"
            )

    def cambiar_estado(
        self, id_clinica: int, id_presupuesto: int, nuevo: EstadoPresupuesto
    ) -> Presupuesto | None:
        presupuesto = self.presupuestos.obtener(id_clinica, id_presupuesto)
        if presupuesto is None:
            return None
        self._exigir_transicion(presupuesto.estado, nuevo)
        presupuesto.estado = nuevo
        self.db.flush()
        return presupuesto
