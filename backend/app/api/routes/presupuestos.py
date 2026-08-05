from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles, resolve_clinica_id
from app.db import get_db
from app.exceptions import TransicionInvalidaError
from app.models import RolUsuario
from app.schemas.presupuesto import CambiarEstadoPresupuestoRequest, PresupuestoResponse
from app.services.presupuesto_service import PresupuestoService

LECTURA = require_roles(
    RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.DOCTOR, RolUsuario.ASISTENTE
)
ESCRITURA = require_roles(RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.ASISTENTE)

router = APIRouter(prefix="/presupuestos", tags=["presupuestos"])

NO_ENCONTRADO = "Presupuesto no encontrado"


@router.get("", response_model=list[PresupuestoResponse], dependencies=[Depends(LECTURA)])
def listar_presupuestos(
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> list[PresupuestoResponse]:
    from app.repositories.presupuesto_repository import PresupuestoRepository

    registros = PresupuestoRepository(db).listar(id_clinica)
    return [PresupuestoResponse.model_validate(r) for r in registros]


@router.get(
    "/{id_presupuesto}", response_model=PresupuestoResponse, dependencies=[Depends(LECTURA)]
)
def obtener_presupuesto(
    id_presupuesto: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> PresupuestoResponse:
    from app.repositories.presupuesto_repository import PresupuestoRepository

    registro = PresupuestoRepository(db).obtener(id_clinica, id_presupuesto)
    if registro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    return PresupuestoResponse.model_validate(registro)


@router.patch(
    "/{id_presupuesto}/estado",
    response_model=PresupuestoResponse,
    dependencies=[Depends(ESCRITURA)],
)
def cambiar_estado_presupuesto(
    id_presupuesto: int,
    body: CambiarEstadoPresupuestoRequest,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> PresupuestoResponse:
    try:
        registro = PresupuestoService(db).cambiar_estado(
            id_clinica, id_presupuesto, body.estado
        )
    except TransicionInvalidaError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    if registro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    db.commit()
    return PresupuestoResponse.model_validate(registro)
