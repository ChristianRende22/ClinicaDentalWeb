from decimal import Decimal

from sqlalchemy import select

from app.models import Factura, Pago


class PagoRepository:
    """No hereda BaseRepository, mismo criterio que FacturaDetalleRepository:
    aislamiento por JOIN contra Factura.
    """

    def __init__(self, db):
        self.db = db

    def listar_de_factura(self, id_clinica: int, id_factura: int) -> list[Pago]:
        stmt = (
            select(Pago)
            .join(Factura, Pago.id_factura == Factura.id_factura)
            .where(Factura.id_clinica == id_clinica, Pago.id_factura == id_factura)
            .order_by(Pago.fecha_pago)
        )
        return list(self.db.execute(stmt).scalars().all())

    def crear(self, id_factura: int, data: dict) -> Pago:
        pago = Pago(id_factura=id_factura, **data)
        self.db.add(pago)
        self.db.flush()
        return pago

    def suma_pagada(self, id_clinica: int, id_factura: int) -> Decimal:
        total = Decimal("0.00")
        for pago in self.listar_de_factura(id_clinica, id_factura):
            total += Decimal(str(pago.monto))
        return total
