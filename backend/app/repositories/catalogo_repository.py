from typing import TypeVar

from sqlalchemy import func, select

from app.exceptions import NombreDuplicadoEnClinicaError
from app.repositories.base import BaseRepository

T = TypeVar("T")


class CatalogoRepository(BaseRepository[T]):
    """CRUD de catalogos por clinica: nombre unico por clinica y borrado logico.

    Los tres catalogos del Modulo 3 (Especialidad, Consultorio, MetodoPago)
    comparten exactamente la forma (id, id_clinica, nombre, activo), asi que el
    CRUD se implementa una sola vez aca. Cada subclase solo declara su modelo.
    """

    model: type[T]

    def _pk(self):
        return self.model.__mapper__.primary_key[0]

    def _existe_nombre(
        self, id_clinica: int, nombre: str, excluir_id: int | None = None
    ) -> bool:
        """Compara con func.lower() explicito, no confiando en el collation:
        SQLite es case-sensitive por defecto y MySQL utf8mb4_general_ci no lo es.
        Considera tambien los inactivos: lo correcto ante un nombre dado de baja
        es reactivarlo, no crear un duplicado.
        """
        stmt = select(self.model).where(
            self.model.id_clinica == id_clinica,
            func.lower(self.model.nombre) == nombre.strip().lower(),
        )
        if excluir_id is not None:
            stmt = stmt.where(self._pk() != excluir_id)
        return self.db.execute(stmt).scalars().first() is not None

    def listar(self, id_clinica: int, incluir_inactivos: bool = False) -> list[T]:
        stmt = select(self.model).where(self.model.id_clinica == id_clinica)
        if not incluir_inactivos:
            stmt = stmt.where(self.model.activo.is_(True))
        stmt = stmt.order_by(self.model.nombre)
        return list(self.db.execute(stmt).scalars().all())

    def obtener(self, id_clinica: int, id_: int) -> T | None:
        stmt = select(self.model).where(
            self._pk() == id_, self.model.id_clinica == id_clinica
        )
        return self.db.execute(stmt).scalars().first()

    def crear(self, id_clinica: int, data: dict) -> T:
        datos = dict(data)
        datos["nombre"] = datos["nombre"].strip()
        if self._existe_nombre(id_clinica, datos["nombre"]):
            raise NombreDuplicadoEnClinicaError(datos["nombre"])

        registro = self.model(id_clinica=id_clinica, **datos)
        self.db.add(registro)
        self.db.flush()
        return registro

    def actualizar(self, id_clinica: int, id_: int, data: dict) -> T | None:
        registro = self.obtener(id_clinica, id_)
        if registro is None:
            return None

        datos = dict(data)
        if "nombre" in datos:
            datos["nombre"] = datos["nombre"].strip()
            if self._existe_nombre(id_clinica, datos["nombre"], excluir_id=id_):
                raise NombreDuplicadoEnClinicaError(datos["nombre"])

        for campo, valor in datos.items():
            setattr(registro, campo, valor)
        self.db.flush()
        return registro

    def eliminar(self, id_clinica: int, id_: int) -> bool:
        """Borrado logico: pone activo = False. Idempotente."""
        registro = self.obtener(id_clinica, id_)
        if registro is None:
            return False
        registro.activo = False
        self.db.flush()
        return True
