from sqlalchemy import select

from app.models import Factura
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
