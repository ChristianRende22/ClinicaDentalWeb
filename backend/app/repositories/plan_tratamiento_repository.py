from sqlalchemy import select

from app.models import (
    ESTADOS_DETALLE_ACTIVOS,
    ESTADOS_PLAN_ACTIVOS,
    PlanTratamiento,
    PlanTratamientoDetalle,
)
from app.repositories.base import BaseRepository


class PlanTratamientoRepository(BaseRepository[PlanTratamiento]):
    """CRUD de planes de tratamiento, mas las dos consultas que sostienen la
    politica de bajas del Modulo 5 (seccion 1 del spec).
    """

    def listar(
        self,
        id_clinica: int,
        id_paciente: int | None = None,
        id_doctor: int | None = None,
    ) -> list[PlanTratamiento]:
        stmt = select(PlanTratamiento).where(PlanTratamiento.id_clinica == id_clinica)
        if id_paciente is not None:
            stmt = stmt.where(PlanTratamiento.id_paciente == id_paciente)
        if id_doctor is not None:
            stmt = stmt.where(PlanTratamiento.id_doctor == id_doctor)
        stmt = stmt.order_by(PlanTratamiento.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def obtener(self, id_clinica: int, id_: int) -> PlanTratamiento | None:
        stmt = select(PlanTratamiento).where(
            PlanTratamiento.id_plan == id_, PlanTratamiento.id_clinica == id_clinica
        )
        return self.db.execute(stmt).scalars().first()

    def crear(self, id_clinica: int, data: dict) -> PlanTratamiento:
        plan = PlanTratamiento(id_clinica=id_clinica, **data)
        self.db.add(plan)
        self.db.flush()
        return plan

    def actualizar(self, id_clinica: int, id_: int, data: dict) -> PlanTratamiento | None:
        plan = self.obtener(id_clinica, id_)
        if plan is None:
            return None
        for campo, valor in data.items():
            setattr(plan, campo, valor)
        self.db.flush()
        return plan

    def eliminar(self, id_clinica: int, id_: int) -> bool:
        """Un plan no se borra, se cancela (misma razon que Cita): perderlo
        borraria el historial clinico del paciente.
        """
        raise NotImplementedError(
            "Los planes de tratamiento no se borran: usar PlanTratamientoService.cambiar_estado()"
        )

    def existe_plan_activo_de_paciente(self, id_clinica: int, id_paciente: int) -> bool:
        """Usa PacienteRepository.eliminar para bloquear la baja (seccion 1 del spec)."""
        stmt = select(PlanTratamiento.id_plan).where(
            PlanTratamiento.id_clinica == id_clinica,
            PlanTratamiento.id_paciente == id_paciente,
            PlanTratamiento.estado.in_(ESTADOS_PLAN_ACTIVOS),
        )
        return self.db.execute(stmt).scalars().first() is not None

    def existe_plan_activo_de_doctor(self, id_clinica: int, id_doctor: int) -> bool:
        """Usa PersonalService.dar_de_baja_doctor para bloquear la baja."""
        stmt = select(PlanTratamiento.id_plan).where(
            PlanTratamiento.id_clinica == id_clinica,
            PlanTratamiento.id_doctor == id_doctor,
            PlanTratamiento.estado.in_(ESTADOS_PLAN_ACTIVOS),
        )
        return self.db.execute(stmt).scalars().first() is not None


class PlanTratamientoDetalleRepository:
    """No hereda BaseRepository: el aislamiento por clinica lo garantiza el
    join contra PlanTratamiento (mismo criterio que HorarioDoctorRepository
    con Doctor). Todos los metodos igual exigen id_clinica.
    """

    def __init__(self, db):
        self.db = db

    def listar_de_plan(
        self, id_clinica: int, id_plan: int
    ) -> list[PlanTratamientoDetalle]:
        stmt = (
            select(PlanTratamientoDetalle)
            .join(PlanTratamiento, PlanTratamientoDetalle.id_plan == PlanTratamiento.id_plan)
            .where(
                PlanTratamiento.id_clinica == id_clinica,
                PlanTratamientoDetalle.id_plan == id_plan,
            )
            .order_by(PlanTratamientoDetalle.orden, PlanTratamientoDetalle.id_detalle)
        )
        return list(self.db.execute(stmt).scalars().all())

    def obtener(
        self, id_clinica: int, id_plan: int, id_detalle: int
    ) -> PlanTratamientoDetalle | None:
        stmt = (
            select(PlanTratamientoDetalle)
            .join(PlanTratamiento, PlanTratamientoDetalle.id_plan == PlanTratamiento.id_plan)
            .where(
                PlanTratamiento.id_clinica == id_clinica,
                PlanTratamientoDetalle.id_plan == id_plan,
                PlanTratamientoDetalle.id_detalle == id_detalle,
            )
        )
        return self.db.execute(stmt).scalars().first()

    def crear(self, id_plan: int, data: dict) -> PlanTratamientoDetalle:
        detalle = PlanTratamientoDetalle(id_plan=id_plan, **data)
        self.db.add(detalle)
        self.db.flush()
        return detalle

    def actualizar_estado(
        self, id_clinica: int, id_plan: int, id_detalle: int, estado
    ) -> PlanTratamientoDetalle | None:
        detalle = self.obtener(id_clinica, id_plan, id_detalle)
        if detalle is None:
            return None
        detalle.estado = estado
        self.db.flush()
        return detalle

    def existe_activo_con_tratamiento(self, id_clinica: int, id_tratamiento: int) -> bool:
        """Usa TratamientoRepository.eliminar para bloquear la baja de un
        tratamiento del catalogo (seccion 1 del spec).
        """
        stmt = (
            select(PlanTratamientoDetalle.id_detalle)
            .join(PlanTratamiento, PlanTratamientoDetalle.id_plan == PlanTratamiento.id_plan)
            .where(
                PlanTratamiento.id_clinica == id_clinica,
                PlanTratamientoDetalle.id_tratamiento == id_tratamiento,
                PlanTratamientoDetalle.estado.in_(ESTADOS_DETALLE_ACTIVOS),
            )
        )
        return self.db.execute(stmt).scalars().first() is not None
