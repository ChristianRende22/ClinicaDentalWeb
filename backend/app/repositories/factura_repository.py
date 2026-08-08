from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import func, select

from app.models import EstadoFactura, Factura, Paciente, Pago
from app.repositories.base import BaseRepository


class FacturaRepository(BaseRepository[Factura]):
    def listar(
        self, id_clinica: int, id_paciente: int | None = None, id_doctor: int | None = None
    ) -> list[Factura]:
        stmt = select(Factura).where(Factura.id_clinica == id_clinica)
        if id_paciente is not None:
            stmt = stmt.where(Factura.id_paciente == id_paciente)
        if id_doctor is not None:
            stmt = stmt.where(Factura.id_doctor == id_doctor)
        stmt = stmt.order_by(Factura.fecha_emision.desc())
        return list(self.db.execute(stmt).scalars().all())

    def obtener(self, id_clinica: int, id_: int) -> Factura | None:
        stmt = select(Factura).where(Factura.id_factura == id_, Factura.id_clinica == id_clinica)
        return self.db.execute(stmt).scalars().first()

    def crear(self, id_clinica: int, data: dict) -> Factura:
        factura = Factura(id_clinica=id_clinica, **data)
        self.db.add(factura)
        self.db.flush()
        return factura

    def actualizar(self, id_clinica: int, id_: int, data: dict) -> Factura | None:
        factura = self.obtener(id_clinica, id_)
        if factura is None:
            return None
        for campo, valor in data.items():
            setattr(factura, campo, valor)
        self.db.flush()
        return factura

    def eliminar(self, id_clinica: int, id_: int) -> bool:
        raise NotImplementedError(
            "Las facturas no se borran: usar FacturaService.anular()"
        )

    def obtener_por_plan(self, id_clinica: int, id_plan: int) -> Factura | None:
        stmt = select(Factura).where(
            Factura.id_clinica == id_clinica, Factura.id_plan == id_plan
        )
        return self.db.execute(stmt).scalars().first()

    def listar_pendientes(
        self, id_clinica: int, desde: date | None = None, hasta: date | None = None
    ) -> dict:
        """Facturas en estado pendiente o parcial, con su saldo pendiente
        calculado -- lo que hay que cobrar HOY, sin importar cuando se
        emitieron (ver seccion 2.3 del spec del Modulo 7). desde/hasta filtran
        fecha_emision solo si se pasan.
        """
        subq_pagos = (
            select(Pago.id_factura, func.coalesce(func.sum(Pago.monto), 0).label("monto_pagado"))
            .group_by(Pago.id_factura)
            .subquery()
        )
        stmt = (
            select(Factura, Paciente, func.coalesce(subq_pagos.c.monto_pagado, 0))
            .join(Paciente, Factura.id_paciente == Paciente.id_paciente)
            .outerjoin(subq_pagos, Factura.id_factura == subq_pagos.c.id_factura)
            .where(
                Factura.id_clinica == id_clinica,
                Factura.estado.in_([EstadoFactura.PENDIENTE, EstadoFactura.PARCIAL]),
            )
        )
        if desde is not None:
            stmt = stmt.where(Factura.fecha_emision >= datetime.combine(desde, time.min))
        if hasta is not None:
            stmt = stmt.where(Factura.fecha_emision <= datetime.combine(hasta, time.max))
        stmt = stmt.order_by(Factura.fecha_emision)

        facturas = []
        cantidad = 0
        monto_pendiente_total = Decimal("0.00")
        for factura, paciente, monto_pagado in self.db.execute(stmt).all():
            monto_pagado = Decimal(str(monto_pagado))
            monto_total = Decimal(str(factura.monto_total))
            saldo_pendiente = monto_total - monto_pagado
            facturas.append(
                {
                    "id_factura": factura.id_factura,
                    "numero_factura": factura.numero_factura,
                    "id_paciente": factura.id_paciente,
                    "paciente": f"{paciente.nombre} {paciente.apellido}",
                    "estado": factura.estado.value,
                    "monto_total": monto_total,
                    "monto_pagado": monto_pagado,
                    "saldo_pendiente": saldo_pendiente,
                    "fecha_emision": factura.fecha_emision,
                }
            )
            cantidad += 1
            monto_pendiente_total += saldo_pendiente

        return {
            "resumen": {"cantidad": cantidad, "monto_pendiente_total": monto_pendiente_total},
            "facturas": facturas,
        }
