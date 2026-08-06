from sqlalchemy import select

from app.models import Factura, FacturaDetalle


class FacturaDetalleRepository:
    """No hereda BaseRepository: la llave de FacturaDetalle no incluye
    id_clinica, el aislamiento lo garantiza el JOIN contra Factura -- mismo
    criterio que PlanTratamientoDetalleRepository (Modulo 5).
    """

    def __init__(self, db):
        self.db = db

    def listar_de_factura(self, id_clinica: int, id_factura: int) -> list[FacturaDetalle]:
        stmt = (
            select(FacturaDetalle)
            .join(Factura, FacturaDetalle.id_factura == Factura.id_factura)
            .where(Factura.id_clinica == id_clinica, FacturaDetalle.id_factura == id_factura)
            .order_by(FacturaDetalle.id_detalle)
        )
        return list(self.db.execute(stmt).scalars().all())

    def crear(self, id_factura: int, data: dict) -> FacturaDetalle:
        detalle = FacturaDetalle(id_factura=id_factura, **data)
        self.db.add(detalle)
        self.db.flush()
        return detalle
