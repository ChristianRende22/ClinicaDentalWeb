from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Usuario


class UsuarioRepository:
    """Repositorio de identidad: busca usuarios por username/id para login.

    A diferencia de BaseRepository, no exige id_clinica porque el login
    ocurre ANTES de saber a que clinica pertenece la sesion: es el punto de
    entrada que determina esa clinica, no un recurso ya aislado por tenant.
    """

    def __init__(self, db: Session):
        self.db = db

    def obtener_por_username(self, username: str) -> Usuario | None:
        stmt = select(Usuario).where(Usuario.username == username)
        return self.db.execute(stmt).scalar_one_or_none()

    def obtener_por_id(self, id_usuario: int) -> Usuario | None:
        return self.db.get(Usuario, id_usuario)
