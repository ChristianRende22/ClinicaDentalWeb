from sqlalchemy import select

from app.models import Receta, RecetaDetalle
from app.repositories.base import BaseRepository


class RecetaRepository(BaseRepository[Receta]):
    """CRUD de recetas. No hay eliminar real: una receta emitida es historial
    clinico, igual que Consulta y Diagnostico.
    """

    def listar(self, id_clinica: int, id_paciente: int | None = None) -> list[Receta]:
        stmt = select(Receta).where(Receta.id_clinica == id_clinica)
        if id_paciente is not None:
            stmt = stmt.where(Receta.id_paciente == id_paciente)
        stmt = stmt.order_by(Receta.fecha_emision.desc())
        return list(self.db.execute(stmt).scalars().all())

    def obtener(self, id_clinica: int, id_: int) -> Receta | None:
        stmt = select(Receta).where(Receta.id_receta == id_, Receta.id_clinica == id_clinica)
        return self.db.execute(stmt).scalars().first()

    def crear(self, id_clinica: int, data: dict) -> Receta:
        receta = Receta(id_clinica=id_clinica, **data)
        self.db.add(receta)
        self.db.flush()
        return receta

    def actualizar(self, id_clinica: int, id_: int, data: dict) -> Receta | None:
        receta = self.obtener(id_clinica, id_)
        if receta is None:
            return None
        for campo, valor in data.items():
            setattr(receta, campo, valor)
        self.db.flush()
        return receta

    def eliminar(self, id_clinica: int, id_: int) -> bool:
        raise NotImplementedError("Las recetas no se borran: son historial clinico")


class RecetaDetalleRepository:
    """No hereda BaseRepository: el aislamiento se garantiza con el join
    contra Receta, mismo criterio que PlanTratamientoDetalleRepository.
    """

    def __init__(self, db):
        self.db = db

    def listar_de_receta(self, id_clinica: int, id_receta: int) -> list[RecetaDetalle]:
        stmt = (
            select(RecetaDetalle)
            .join(Receta, RecetaDetalle.id_receta == Receta.id_receta)
            .where(Receta.id_clinica == id_clinica, RecetaDetalle.id_receta == id_receta)
        )
        return list(self.db.execute(stmt).scalars().all())

    def crear(self, id_receta: int, data: dict) -> RecetaDetalle:
        detalle = RecetaDetalle(id_receta=id_receta, **data)
        self.db.add(detalle)
        self.db.flush()
        return detalle
