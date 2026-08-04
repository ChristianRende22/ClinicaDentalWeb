from sqlalchemy.orm import Session

from app.exceptions import ReferenciaInvalidaError, UsernameYaExisteError
from app.models import RolUsuario, Usuario
from app.repositories.asistente_repository import AsistenteRepository
from app.repositories.doctor_repository import DoctorRepository
from app.repositories.especialidad_repository import EspecialidadRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.security.passwords import generar_password_temporal, hash_password


class PersonalService:
    """Alta y baja del personal de la clinica.

    Crea el Usuario y el perfil en UNA transaccion, con rollback explicito,
    copiando el patron de ClinicaService.crear_clinica_con_admin (Modulo 2). La
    alternativa (exigir que el Usuario exista de antes) obliga a un flujo de dos
    pasos que puede dejar usuarios huerfanos si el segundo falla.
    """

    def __init__(self, db: Session):
        self.db = db
        self.usuarios = UsuarioRepository(db)
        self.doctores = DoctorRepository(db)
        self.asistentes = AsistenteRepository(db)
        self.especialidades = EspecialidadRepository(db)

    def _crear_usuario(self, id_clinica: int, username: str, rol: RolUsuario) -> tuple:
        password_temporal = generar_password_temporal()
        usuario = Usuario(
            id_clinica=id_clinica,
            username=username,
            password_hash=hash_password(password_temporal),
            rol=rol,
            debe_cambiar_password=True,
        )
        self.db.add(usuario)
        self.db.flush()
        return usuario, password_temporal

    def validar_especialidad(self, id_clinica: int, id_especialidad: int | None) -> None:
        """Lanza ReferenciaInvalidaError si la especialidad no sirve para esta clinica.

        La usan el alta y la edicion de doctores: la regla es la misma y no
        conviene tenerla escrita dos veces.
        """
        if id_especialidad is None:
            return
        especialidad = self.especialidades.obtener(id_clinica, id_especialidad)
        if especialidad is None or not especialidad.activo:
            raise ReferenciaInvalidaError("La especialidad no existe en esta clinica")

    def crear_doctor(self, id_clinica: int, datos: dict) -> dict:
        campos = dict(datos)
        username = campos.pop("username")

        if self.usuarios.obtener_por_username(username) is not None:
            raise UsernameYaExisteError()

        self.validar_especialidad(id_clinica, campos.get("id_especialidad"))

        try:
            usuario, password_temporal = self._crear_usuario(
                id_clinica, username, RolUsuario.DOCTOR
            )
            perfil = self.doctores.crear(
                id_clinica, {"id_usuario": usuario.id_usuario, **campos}
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return {"perfil": perfil, "password_temporal": password_temporal}

    def crear_asistente(self, id_clinica: int, datos: dict) -> dict:
        campos = dict(datos)
        username = campos.pop("username")

        if self.usuarios.obtener_por_username(username) is not None:
            raise UsernameYaExisteError()

        try:
            usuario, password_temporal = self._crear_usuario(
                id_clinica, username, RolUsuario.ASISTENTE
            )
            perfil = self.asistentes.crear(
                id_clinica, {"id_usuario": usuario.id_usuario, **campos}
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return {"perfil": perfil, "password_temporal": password_temporal}

    def _cambiar_actividad(
        self, repositorio, id_clinica: int, id_perfil: int, activo: bool
    ) -> bool:
        """Activa o desactiva perfil y Usuario juntos, en una transaccion.

        Los dos sentidos van juntos a proposito: un profesional dado de baja no
        debe poder entrar al sistema, y uno reactivado tiene que poder entrar. Si
        se movieran por separado quedaria un medio-estado incoherente (un doctor
        que aparece en los listados y al que se le pueden agendar citas, pero que
        no puede loguearse).
        """
        perfil = repositorio.obtener(id_clinica, id_perfil)
        if perfil is None:
            return False
        try:
            if activo:
                perfil.activo = True
            else:
                # El borrado logico del perfil lo hace el repositorio; aca solo
                # se coordina la transaccion con la baja del Usuario.
                repositorio.eliminar(id_clinica, id_perfil)
            usuario = self.usuarios.obtener_por_id(perfil.id_usuario)
            if usuario is None:
                # Inalcanzable mientras la FK sea NOT NULL, pero si alguna vez
                # pasara no se puede devolver True: quedaria un perfil y un
                # login desincronizados.
                raise ReferenciaInvalidaError(
                    "El perfil no tiene un usuario asociado"
                )
            usuario.activo = activo
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return True

    def dar_de_baja_doctor(self, id_clinica: int, id_doctor: int) -> bool:
        return self._cambiar_actividad(self.doctores, id_clinica, id_doctor, False)

    def dar_de_baja_asistente(self, id_clinica: int, id_asistente: int) -> bool:
        return self._cambiar_actividad(self.asistentes, id_clinica, id_asistente, False)

    def reactivar_doctor(self, id_clinica: int, id_doctor: int) -> bool:
        return self._cambiar_actividad(self.doctores, id_clinica, id_doctor, True)

    def reactivar_asistente(self, id_clinica: int, id_asistente: int) -> bool:
        return self._cambiar_actividad(self.asistentes, id_clinica, id_asistente, True)
