from sqlalchemy.orm import Session

from app.exceptions import ReferenciaInvalidaError, TransicionInvalidaError
from app.models import (
    TRANSICIONES_DETALLE_PERMITIDAS,
    TRANSICIONES_PLAN_PERMITIDAS,
    EstadoDetallePlanTratamiento,
    EstadoPlanTratamiento,
    PlanTratamiento,
    PlanTratamientoDetalle,
)
from app.repositories.doctor_repository import DoctorRepository
from app.repositories.paciente_repository import PacienteRepository
from app.repositories.plan_tratamiento_repository import (
    PlanTratamientoDetalleRepository,
    PlanTratamientoRepository,
)
from app.repositories.tratamiento_repository import TratamientoRepository
from app.services.consulta_service import validar_doctor_activo, validar_paciente_activo


class PlanTratamientoService:
    """Crea planes, agrega/edita/cancela detalles (copiando el precio del
    catalogo al agregar) y mueve el estado del plan y del detalle con sus
    respectivas tablas de transiciones. Ver seccion 4 del spec.
    """

    def __init__(self, db: Session):
        self.db = db
        self.planes = PlanTratamientoRepository(db)
        self.detalles = PlanTratamientoDetalleRepository(db)
        self.pacientes = PacienteRepository(db)
        self.doctores = DoctorRepository(db)
        self.tratamientos = TratamientoRepository(db)

    def crear(self, id_clinica: int, datos: dict) -> PlanTratamiento:
        validar_paciente_activo(self.pacientes, id_clinica, datos["id_paciente"])
        validar_doctor_activo(self.doctores, id_clinica, datos["id_doctor"])
        return self.planes.crear(id_clinica, datos)

    def _validar_tratamiento(self, id_clinica: int, id_tratamiento: int):
        tratamiento = self.tratamientos.obtener(id_clinica, id_tratamiento)
        if tratamiento is None:
            raise ReferenciaInvalidaError("El tratamiento no existe en esta clinica")
        if not tratamiento.activo:
            raise ReferenciaInvalidaError("El tratamiento esta dado de baja")
        return tratamiento

    def agregar_detalle(
        self, id_clinica: int, id_plan: int, datos: dict
    ) -> PlanTratamientoDetalle | None:
        plan = self.planes.obtener(id_clinica, id_plan)
        if plan is None:
            return None
        tratamiento = self._validar_tratamiento(id_clinica, datos["id_tratamiento"])

        campos = dict(datos)
        # El precio se copia AHORA, del catalogo. Si el catalogo cambia
        # despues, este detalle no se mueve (decision 1 del spec).
        campos["precio_unitario"] = tratamiento.precio
        return self.detalles.crear(id_plan, campos)

    @staticmethod
    def _exigir_transicion_detalle(
        actual: EstadoDetallePlanTratamiento, nuevo: EstadoDetallePlanTratamiento
    ) -> None:
        if nuevo not in TRANSICIONES_DETALLE_PERMITIDAS[actual]:
            raise TransicionInvalidaError(
                f"Un detalle en estado '{actual.value}' no puede pasar a '{nuevo.value}'"
            )

    def cambiar_estado_detalle(
        self,
        id_clinica: int,
        id_plan: int,
        id_detalle: int,
        nuevo: EstadoDetallePlanTratamiento,
    ) -> PlanTratamientoDetalle | None:
        detalle = self.detalles.obtener(id_clinica, id_plan, id_detalle)
        if detalle is None:
            return None
        self._exigir_transicion_detalle(detalle.estado, nuevo)
        return self.detalles.actualizar_estado(id_clinica, id_plan, id_detalle, nuevo)

    @staticmethod
    def _exigir_transicion_plan(
        actual: EstadoPlanTratamiento, nuevo: EstadoPlanTratamiento
    ) -> None:
        if nuevo not in TRANSICIONES_PLAN_PERMITIDAS[actual]:
            raise TransicionInvalidaError(
                f"Un plan en estado '{actual.value}' no puede pasar a '{nuevo.value}'"
            )

    def cambiar_estado(
        self, id_clinica: int, id_plan: int, nuevo: EstadoPlanTratamiento
    ) -> PlanTratamiento | None:
        plan = self.planes.obtener(id_clinica, id_plan)
        if plan is None:
            return None
        self._exigir_transicion_plan(plan.estado, nuevo)
        plan.estado = nuevo
        self.db.flush()
        return plan
