from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Clinica, EstadoClinica


class ClinicaRepository:
    """Repositorio de plataforma: Clinica es la unidad de tenancy en si misma,
    por lo que sus metodos NO reciben id_clinica como filtro (a diferencia de
    BaseRepository, pensado para recursos DENTRO de una clinica).
    """

    def __init__(self, db: Session):
        self.db = db

    def listar(self, estado: EstadoClinica | None = None) -> list[Clinica]:
        stmt = select(Clinica)
        if estado is not None:
            stmt = stmt.where(Clinica.estado == estado)
        return list(self.db.execute(stmt).scalars().all())

    def obtener(self, id_clinica: int) -> Clinica | None:
        return self.db.get(Clinica, id_clinica)

    def crear(self, data: dict) -> Clinica:
        clinica = Clinica(**data)
        self.db.add(clinica)
        self.db.flush()
        return clinica

    def actualizar(self, id_clinica: int, data: dict) -> Clinica | None:
        clinica = self.obtener(id_clinica)
        if clinica is None:
            return None
        for campo, valor in data.items():
            setattr(clinica, campo, valor)
        self.db.flush()
        return clinica

    def cambiar_estado(self, id_clinica: int, estado: EstadoClinica) -> Clinica | None:
        clinica = self.obtener(id_clinica)
        if clinica is None:
            return None
        clinica.estado = estado
        self.db.flush()
        return clinica
