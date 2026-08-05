from sqlalchemy import func, or_, select

from app.exceptions import ReferenciaEnUsoError
from app.models import Paciente
from app.repositories.base import BaseRepository


class PacienteRepository(BaseRepository[Paciente]):
    """CRUD de pacientes con borrado logico y busqueda por nombre o apellido.

    Hereda de BaseRepository: es exactamente el caso para el que se diseno, un
    recurso que vive dentro de una clinica.
    """

    def listar(
        self,
        id_clinica: int,
        buscar: str | None = None,
        incluir_inactivos: bool = False,
    ) -> list[Paciente]:
        stmt = select(Paciente).where(Paciente.id_clinica == id_clinica)
        if not incluir_inactivos:
            stmt = stmt.where(Paciente.activo.is_(True))
        if buscar:
            # func.lower() explicito para no depender del collation del motor.
            #
            # OJO, no confundir con el caso de CatalogoRepository: alla el
            # lower() es imprescindible porque compara con ==, y SQLite si es
            # case-sensitive con ==. Aca la comparacion es LIKE, y tanto SQLite
            # como MySQL ya pliegan mayusculas ASCII en LIKE por su cuenta. El
            # lower() se mantiene igual porque hace explicita la intencion y no
            # deja el comportamiento a merced del collation configurado.
            #
            # Limitacion conocida, y aplica a nombres salvadorenos reales
            # (Pena, Munoz, Nunez): ni el LIKE de SQLite ni su lower() pliegan
            # caracteres no-ASCII, asi que buscar "MUNOZ" con enie mayuscula no
            # encuentra "Munoz" con enie minuscula en los tests. Contra MySQL
            # con utf8mb4_general_ci si funciona. Es una diferencia entre el
            # entorno de test y produccion, no un bug de esta query.
            patron = f"%{buscar.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Paciente.nombre).like(patron),
                    func.lower(Paciente.apellido).like(patron),
                )
            )
        stmt = stmt.order_by(Paciente.apellido, Paciente.nombre)
        return list(self.db.execute(stmt).scalars().all())

    def obtener(self, id_clinica: int, id_: int) -> Paciente | None:
        stmt = select(Paciente).where(
            Paciente.id_paciente == id_, Paciente.id_clinica == id_clinica
        )
        return self.db.execute(stmt).scalars().first()

    def crear(self, id_clinica: int, data: dict) -> Paciente:
        paciente = Paciente(id_clinica=id_clinica, **data)
        self.db.add(paciente)
        self.db.flush()
        return paciente

    def actualizar(self, id_clinica: int, id_: int, data: dict) -> Paciente | None:
        paciente = self.obtener(id_clinica, id_)
        if paciente is None:
            return None
        for campo, valor in data.items():
            setattr(paciente, campo, valor)
        self.db.flush()
        return paciente

    def eliminar(self, id_clinica: int, id_: int) -> bool:
        """Borrado logico: pone activo = False. Idempotente.

        Bloquea si el paciente tiene un PlanTratamiento activo (seccion 1 del
        spec del Modulo 5): dar de baja a alguien con un tratamiento en curso
        deja el plan colgando de un paciente al que ya no se le puede
        agendar nada nuevo. Import adentro del metodo para evitar el ciclo
        (plan_tratamiento_repository no depende de este archivo).
        """
        paciente = self.obtener(id_clinica, id_)
        if paciente is None:
            return False

        from app.repositories.plan_tratamiento_repository import PlanTratamientoRepository

        if PlanTratamientoRepository(self.db).existe_plan_activo_de_paciente(id_clinica, id_):
            raise ReferenciaEnUsoError(
                "No se puede dar de baja: el paciente tiene un plan de tratamiento activo"
            )

        paciente.activo = False
        self.db.flush()
        return True
