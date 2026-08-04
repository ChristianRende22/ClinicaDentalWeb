from sqlalchemy import select

from app.models import Asistente
from app.repositories.base import BaseRepository


class AsistenteRepository(BaseRepository[Asistente]):
    """CRUD de asistentes con borrado logico.

    Deliberadamente NO comparte una clase base con DoctorRepository: son dos
    casos, no tres, y Doctor ya diverge (especialidad, horarios, citas).
    """

    def listar(
        self, id_clinica: int, incluir_inactivos: bool = False
    ) -> list[Asistente]:
        stmt = select(Asistente).where(Asistente.id_clinica == id_clinica)
        if not incluir_inactivos:
            stmt = stmt.where(Asistente.activo.is_(True))
        stmt = stmt.order_by(Asistente.apellido, Asistente.nombre)
        return list(self.db.execute(stmt).scalars().all())

    def obtener(self, id_clinica: int, id_: int) -> Asistente | None:
        stmt = select(Asistente).where(
            Asistente.id_asistente == id_, Asistente.id_clinica == id_clinica
        )
        return self.db.execute(stmt).scalars().first()

    def obtener_por_usuario(self, id_usuario: int) -> Asistente | None:
        """Traduce un Usuario a su perfil de Asistente.

        NO recibe id_clinica, misma excepcion documentada que
        DoctorRepository.obtener_por_usuario y UsuarioRepository.obtener_por_username:
        resuelve el JWT y ocurre antes de saber la clinica de la sesion.
        """
        stmt = select(Asistente).where(Asistente.id_usuario == id_usuario)
        return self.db.execute(stmt).scalars().first()

    def crear(self, id_clinica: int, data: dict) -> Asistente:
        asistente = Asistente(id_clinica=id_clinica, **data)
        self.db.add(asistente)
        self.db.flush()
        return asistente

    def actualizar(self, id_clinica: int, id_: int, data: dict) -> Asistente | None:
        asistente = self.obtener(id_clinica, id_)
        if asistente is None:
            return None
        for campo, valor in data.items():
            setattr(asistente, campo, valor)
        self.db.flush()
        return asistente

    def eliminar(self, id_clinica: int, id_: int) -> bool:
        asistente = self.obtener(id_clinica, id_)
        if asistente is None:
            return False
        asistente.activo = False
        self.db.flush()
        return True
