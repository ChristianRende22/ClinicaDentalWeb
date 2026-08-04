from sqlalchemy import select

from app.models import Doctor
from app.repositories.base import BaseRepository


class DoctorRepository(BaseRepository[Doctor]):
    """CRUD de doctores con borrado logico y filtro por especialidad."""

    def listar(
        self,
        id_clinica: int,
        id_especialidad: int | None = None,
        incluir_inactivos: bool = False,
    ) -> list[Doctor]:
        stmt = select(Doctor).where(Doctor.id_clinica == id_clinica)
        if not incluir_inactivos:
            stmt = stmt.where(Doctor.activo.is_(True))
        if id_especialidad is not None:
            stmt = stmt.where(Doctor.id_especialidad == id_especialidad)
        stmt = stmt.order_by(Doctor.apellido, Doctor.nombre)
        return list(self.db.execute(stmt).scalars().all())

    def obtener(self, id_clinica: int, id_: int) -> Doctor | None:
        stmt = select(Doctor).where(
            Doctor.id_doctor == id_, Doctor.id_clinica == id_clinica
        )
        return self.db.execute(stmt).scalars().first()

    def obtener_por_usuario(self, id_usuario: int) -> Doctor | None:
        """Traduce un Usuario a su perfil de Doctor.

        NO recibe id_clinica, y es la misma excepcion documentada que
        UsuarioRepository.obtener_por_username: es el punto de entrada que
        resuelve el JWT, ocurre antes de saber la clinica de la sesion. Quien
        llame compara doctor.id_clinica con el id_clinica resuelto.
        """
        stmt = select(Doctor).where(Doctor.id_usuario == id_usuario)
        return self.db.execute(stmt).scalars().first()

    def crear(self, id_clinica: int, data: dict) -> Doctor:
        doctor = Doctor(id_clinica=id_clinica, **data)
        self.db.add(doctor)
        self.db.flush()
        return doctor

    def actualizar(self, id_clinica: int, id_: int, data: dict) -> Doctor | None:
        doctor = self.obtener(id_clinica, id_)
        if doctor is None:
            return None
        for campo, valor in data.items():
            setattr(doctor, campo, valor)
        self.db.flush()
        return doctor

    def eliminar(self, id_clinica: int, id_: int) -> bool:
        """Borrado logico del perfil. La desactivacion del Usuario asociado la
        coordina PersonalService, que es quien maneja la transaccion.
        """
        doctor = self.obtener(id_clinica, id_)
        if doctor is None:
            return False
        doctor.activo = False
        self.db.flush()
        return True
