from sqlalchemy.orm import Session

from app.exceptions import UsernameYaExisteError
from app.models import RolUsuario, Usuario
from app.repositories.clinica_modulo_repository import ClinicaModuloRepository
from app.repositories.clinica_repository import ClinicaRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.security.passwords import generar_password_temporal, hash_password


class ClinicaService:
    def __init__(self, db: Session):
        self.db = db
        self.clinicas = ClinicaRepository(db)
        self.modulos = ClinicaModuloRepository(db)
        self.usuarios = UsuarioRepository(db)

    def crear_clinica_con_admin(
        self,
        nombre: str,
        admin_username: str,
        direccion: str | None = None,
        telefono: str | None = None,
        correo: str | None = None,
    ) -> dict:
        if self.usuarios.obtener_por_username(admin_username) is not None:
            raise UsernameYaExisteError()

        try:
            clinica = self.clinicas.crear(
                {
                    "nombre": nombre,
                    "direccion": direccion,
                    "telefono": telefono,
                    "correo": correo,
                }
            )
            self.modulos.sembrar_modulos_default(clinica.id_clinica)

            password_temporal = generar_password_temporal()
            admin = Usuario(
                id_clinica=clinica.id_clinica,
                username=admin_username,
                password_hash=hash_password(password_temporal),
                rol=RolUsuario.ADMIN,
                debe_cambiar_password=True,
            )
            self.db.add(admin)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return {
            "clinica": clinica,
            "admin": admin,
            "password_temporal": password_temporal,
        }
