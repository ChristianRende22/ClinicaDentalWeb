from decimal import Decimal

from sqlalchemy.orm import Session

from app.exceptions import FacturaAnuladaError, PagoExcedeSaldoError
from app.models import EstadoFactura, Pago
from app.repositories.factura_repository import FacturaRepository
from app.repositories.pago_repository import PagoRepository


class PagoService:
    def __init__(self, db: Session):
        self.db = db
        self.facturas = FacturaRepository(db)
        self.pagos = PagoRepository(db)

    def registrar_pago(
        self,
        id_clinica: int,
        id_factura: int,
        monto: Decimal,
        id_metodo_pago: int,
        id_asistente: int | None = None,
    ) -> Pago | None:
        factura = self.facturas.obtener(id_clinica, id_factura)
        if factura is None:
            return None
        if factura.estado == EstadoFactura.ANULADA:
            raise FacturaAnuladaError("No se pueden registrar pagos sobre una factura anulada")

        ya_pagado = self.pagos.suma_pagada(id_clinica, id_factura)
        saldo_pendiente = Decimal(str(factura.monto_total)) - ya_pagado
        monto_decimal = Decimal(str(monto))
        if monto_decimal > saldo_pendiente:
            raise PagoExcedeSaldoError(
                f"El pago ({monto_decimal}) excede el saldo pendiente ({saldo_pendiente})"
            )

        pago = self.pagos.crear(
            id_factura,
            {
                "id_metodo_pago": id_metodo_pago,
                "id_asistente": id_asistente,
                "monto": str(monto_decimal),
            },
        )

        nuevo_pagado = ya_pagado + monto_decimal
        factura.estado = (
            EstadoFactura.PAGADA
            if nuevo_pagado >= Decimal(str(factura.monto_total))
            else EstadoFactura.PARCIAL
        )
        self.db.commit()
        return pago
