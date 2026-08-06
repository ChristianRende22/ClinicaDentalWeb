from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles, resolve_clinica_id
from app.db import get_db
from app.exceptions import (
    PresupuestoNoAceptadoError,
    ReferenciaInvalidaError,
    TransicionInvalidaError,
)
from app.models import RolUsuario
from app.repositories.asistente_repository import AsistenteRepository
from app.repositories.plan_tratamiento_repository import (
    PlanTratamientoDetalleRepository,
    PlanTratamientoRepository,
)
from app.schemas.factura import FacturaResponse
from app.schemas.plan_tratamiento import (
    CambiarEstadoDetalleRequest,
    CambiarEstadoPlanRequest,
    DetalleCreate,
    DetalleResponse,
    PlanTratamientoCreate,
    PlanTratamientoResponse,
)
from app.schemas.presupuesto import PresupuestoResponse
from app.services.factura_service import FacturaService
from app.services.plan_tratamiento_service import PlanTratamientoService
from app.services.presupuesto_service import PresupuestoService

# Mismo criterio que Consulta/Cita: quien atiende registra.
LECTURA = require_roles(
    RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.DOCTOR, RolUsuario.ASISTENTE
)
ESCRITURA = require_roles(RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.ASISTENTE, RolUsuario.DOCTOR)
#: Generar el presupuesto es tarea de recepcion, no del doctor (tabla de la
#: seccion 5 del spec).
ESCRITURA_PRESUPUESTO = require_roles(RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.ASISTENTE)

router = APIRouter(prefix="/planes-tratamiento", tags=["planes-tratamiento"])

NO_ENCONTRADO = "Plan de tratamiento no encontrado"
DETALLE_NO_ENCONTRADO = "Detalle no encontrado"

_A_409 = (TransicionInvalidaError, PresupuestoNoAceptadoError)
_A_422 = (ReferenciaInvalidaError,)


def _traducir(error: Exception) -> HTTPException:
    if isinstance(error, _A_409):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error))


@router.get("", response_model=list[PlanTratamientoResponse], dependencies=[Depends(LECTURA)])
def listar_planes(
    id_paciente: int | None = None,
    id_doctor: int | None = None,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> list[PlanTratamientoResponse]:
    registros = PlanTratamientoRepository(db).listar(
        id_clinica, id_paciente=id_paciente, id_doctor=id_doctor
    )
    return [PlanTratamientoResponse.model_validate(r) for r in registros]


@router.post(
    "", response_model=PlanTratamientoResponse, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(ESCRITURA)],
)
def crear_plan(
    body: PlanTratamientoCreate,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> PlanTratamientoResponse:
    try:
        plan = PlanTratamientoService(db).crear(id_clinica, body.model_dump())
    except (*_A_409, *_A_422) as error:
        raise _traducir(error)
    db.commit()
    return PlanTratamientoResponse.model_validate(plan)


@router.get("/{id_plan}", response_model=PlanTratamientoResponse, dependencies=[Depends(LECTURA)])
def obtener_plan(
    id_plan: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> PlanTratamientoResponse:
    registro = PlanTratamientoRepository(db).obtener(id_clinica, id_plan)
    if registro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    return PlanTratamientoResponse.model_validate(registro)


@router.patch(
    "/{id_plan}/estado", response_model=PlanTratamientoResponse, dependencies=[Depends(ESCRITURA)]
)
def cambiar_estado_plan(
    id_plan: int,
    body: CambiarEstadoPlanRequest,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> PlanTratamientoResponse:
    try:
        plan = PlanTratamientoService(db).cambiar_estado(id_clinica, id_plan, body.estado)
    except (*_A_409, *_A_422) as error:
        raise _traducir(error)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    db.commit()
    return PlanTratamientoResponse.model_validate(plan)


@router.get(
    "/{id_plan}/detalles", response_model=list[DetalleResponse], dependencies=[Depends(LECTURA)]
)
def listar_detalles(
    id_plan: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> list[DetalleResponse]:
    if PlanTratamientoRepository(db).obtener(id_clinica, id_plan) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    registros = PlanTratamientoDetalleRepository(db).listar_de_plan(id_clinica, id_plan)
    return [DetalleResponse.model_validate(r) for r in registros]


@router.post(
    "/{id_plan}/detalles",
    response_model=DetalleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(ESCRITURA)],
)
def agregar_detalle(
    id_plan: int,
    body: DetalleCreate,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> DetalleResponse:
    try:
        detalle = PlanTratamientoService(db).agregar_detalle(
            id_clinica, id_plan, body.model_dump()
        )
    except (*_A_409, *_A_422) as error:
        raise _traducir(error)
    if detalle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    db.commit()
    return DetalleResponse.model_validate(detalle)


@router.patch(
    "/{id_plan}/detalles/{id_detalle}",
    response_model=DetalleResponse,
    dependencies=[Depends(ESCRITURA)],
)
def cambiar_estado_detalle(
    id_plan: int,
    id_detalle: int,
    body: CambiarEstadoDetalleRequest,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> DetalleResponse:
    try:
        detalle = PlanTratamientoService(db).cambiar_estado_detalle(
            id_clinica, id_plan, id_detalle, body.estado
        )
    except (*_A_409, *_A_422) as error:
        raise _traducir(error)
    if detalle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=DETALLE_NO_ENCONTRADO)
    db.commit()
    return DetalleResponse.model_validate(detalle)


@router.get(
    "/{id_plan}/presupuesto",
    response_model=PresupuestoResponse,
    dependencies=[Depends(LECTURA)],
)
def obtener_presupuesto(
    id_plan: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> PresupuestoResponse:
    from app.repositories.presupuesto_repository import PresupuestoRepository

    if PlanTratamientoRepository(db).obtener(id_clinica, id_plan) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    presupuesto = PresupuestoRepository(db).obtener_por_plan(id_clinica, id_plan)
    if presupuesto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Este plan todavia no tiene un presupuesto generado",
        )
    return PresupuestoResponse.model_validate(presupuesto)


@router.post(
    "/{id_plan}/presupuesto",
    response_model=PresupuestoResponse,
    dependencies=[Depends(ESCRITURA_PRESUPUESTO)],
)
def generar_presupuesto(
    id_plan: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> PresupuestoResponse:
    """Regenera si ya existia (decision 2 del spec): mismo id_presupuesto,
    monto_total actualizado.
    """
    if PlanTratamientoRepository(db).obtener(id_clinica, id_plan) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    presupuesto = PresupuestoService(db).generar_o_regenerar(id_clinica, id_plan)
    db.commit()
    return PresupuestoResponse.model_validate(presupuesto)


@router.post(
    "/{id_plan}/factura",
    response_model=FacturaResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(ESCRITURA_PRESUPUESTO)],
)
def generar_factura(
    id_plan: int,
    id_clinica: int = Depends(resolve_clinica_id),
    usuario=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FacturaResponse:
    id_asistente = None
    if usuario.rol.value == "asistente":
        perfil = AsistenteRepository(db).obtener_por_usuario(usuario.id_usuario)
        id_asistente = perfil.id_asistente if perfil else None

    try:
        factura = FacturaService(db).generar_desde_presupuesto(id_clinica, id_plan, id_asistente)
    except (*_A_409, *_A_422) as error:
        raise _traducir(error)
    if factura is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    return FacturaResponse.model_validate(factura)
