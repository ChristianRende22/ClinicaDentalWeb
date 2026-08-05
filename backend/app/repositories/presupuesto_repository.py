from sqlalchemy import select

from app.models import Presupuesto
from app.repositories.base import BaseRepository


class PresupuestoRepository(BaseRepository[Presupuesto]):
    def listar(self, id_clinica: int) -> list[Presupuesto]:
        stmt = select(Presupuesto).where(Presupuesto.id_clinica == id_clinica)
        return list(self.db.execute(stmt).scalars().all())

    def obtener(self, id_clinica: int, id_: int) -> Presupuesto | None:
        stmt = select(Presupuesto).where(
            Presupuesto.id_presupuesto == id_, Presupuesto.id_clinica == id_clinica
        )
        return self.db.execute(stmt).scalars().first()

    def obtener_por_plan(self, id_clinica: int, id_plan: int) -> Presupuesto | None:
        stmt = select(Presupuesto).where(
            Presupuesto.id_clinica == id_clinica, Presupuesto.id_plan == id_plan
        )
        return self.db.execute(stmt).scalars().first()

    def crear(self, id_clinica: int, data: dict) -> Presupuesto:
        presupuesto = Presupuesto(id_clinica=id_clinica, **data)
        self.db.add(presupuesto)
        self.db.flush()
        return presupuesto

    def actualizar(self, id_clinica: int, id_: int, data: dict) -> Presupuesto | None:
        presupuesto = self.obtener(id_clinica, id_)
        if presupuesto is None:
            return None
        for campo, valor in data.items():
            setattr(presupuesto, campo, valor)
        self.db.flush()
        return presupuesto

    def eliminar(self, id_clinica: int, id_: int) -> bool:
        """Un presupuesto no se borra: se regenera (decision 2 del spec) o se
        marca rechazado/vencido. Igual que Cita, se niega en vez de dejar un
        metodo que destruya el registro en silencio.
        """
        raise NotImplementedError(
            "Los presupuestos no se borran: usar PresupuestoService"
        )
