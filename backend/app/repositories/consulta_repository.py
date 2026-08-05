from datetime import datetime

from sqlalchemy import select

from app.models import Consulta
from app.repositories.base import BaseRepository


class ConsultaRepository(BaseRepository[Consulta]):
    """CRUD del historial de consultas. eliminar() no esta implementado: una
    consulta es historial clinico permanente, igual que Cita.
    """

    def listar(
        self,
        id_clinica: int,
        id_paciente: int | None = None,
        id_doctor: int | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
    ) -> list[Consulta]:
        stmt = select(Consulta).where(Consulta.id_clinica == id_clinica)
        if id_paciente is not None:
            stmt = stmt.where(Consulta.id_paciente == id_paciente)
        if id_doctor is not None:
            stmt = stmt.where(Consulta.id_doctor == id_doctor)
        if desde is not None:
            stmt = stmt.where(Consulta.fecha_hora >= desde)
        if hasta is not None:
            stmt = stmt.where(Consulta.fecha_hora <= hasta)
        # Historial: lo mas reciente primero.
        stmt = stmt.order_by(Consulta.fecha_hora.desc())
        return list(self.db.execute(stmt).scalars().all())

    def obtener(self, id_clinica: int, id_: int) -> Consulta | None:
        stmt = select(Consulta).where(
            Consulta.id_consulta == id_, Consulta.id_clinica == id_clinica
        )
        return self.db.execute(stmt).scalars().first()

    def crear(self, id_clinica: int, data: dict) -> Consulta:
        consulta = Consulta(id_clinica=id_clinica, **data)
        self.db.add(consulta)
        self.db.flush()
        return consulta

    def actualizar(self, id_clinica: int, id_: int, data: dict) -> Consulta | None:
        consulta = self.obtener(id_clinica, id_)
        if consulta is None:
            return None
        for campo, valor in data.items():
            setattr(consulta, campo, valor)
        self.db.flush()
        return consulta

    def eliminar(self, id_clinica: int, id_: int) -> bool:
        raise NotImplementedError(
            "Las consultas no se borran: son el historial clinico del paciente"
        )
