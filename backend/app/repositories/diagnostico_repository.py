from sqlalchemy import select

from app.models import Diagnostico
from app.repositories.base import BaseRepository


class DiagnosticoRepository(BaseRepository[Diagnostico]):
    """CRUD simple. Sin eliminar real: un diagnostico registrado no se borra,
    es historial -- si estaba mal, se corrige con un PUT o se agrega uno
    nuevo que lo corrija.
    """

    def listar(self, id_clinica: int, id_consulta: int | None = None) -> list[Diagnostico]:
        stmt = select(Diagnostico).where(Diagnostico.id_clinica == id_clinica)
        if id_consulta is not None:
            stmt = stmt.where(Diagnostico.id_consulta == id_consulta)
        stmt = stmt.order_by(Diagnostico.created_at)
        return list(self.db.execute(stmt).scalars().all())

    def obtener(self, id_clinica: int, id_: int) -> Diagnostico | None:
        stmt = select(Diagnostico).where(
            Diagnostico.id_diagnostico == id_, Diagnostico.id_clinica == id_clinica
        )
        return self.db.execute(stmt).scalars().first()

    def crear(self, id_clinica: int, data: dict) -> Diagnostico:
        diagnostico = Diagnostico(id_clinica=id_clinica, **data)
        self.db.add(diagnostico)
        self.db.flush()
        return diagnostico

    def actualizar(self, id_clinica: int, id_: int, data: dict) -> Diagnostico | None:
        diagnostico = self.obtener(id_clinica, id_)
        if diagnostico is None:
            return None
        for campo, valor in data.items():
            setattr(diagnostico, campo, valor)
        self.db.flush()
        return diagnostico

    def eliminar(self, id_clinica: int, id_: int) -> bool:
        raise NotImplementedError("Los diagnosticos no se borran: son historial clinico")
