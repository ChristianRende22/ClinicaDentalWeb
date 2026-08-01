from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles, resolve_clinica_id
from app.db import get_db
from app.exceptions import NombreDuplicadoEnClinicaError
from app.models import RolUsuario
from app.repositories.metodo_pago_repository import MetodoPagoRepository
from app.schemas.parametros import (
    CatalogoCreateRequest,
    CatalogoUpdateRequest,
    MetodoPagoResponse,
)

LECTURA = require_roles(
    RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.DOCTOR, RolUsuario.ASISTENTE
)
ESCRITURA = require_roles(RolUsuario.SUPERADMIN, RolUsuario.ADMIN)

router = APIRouter(prefix="/metodos-pago", tags=["metodos de pago"])

NO_ENCONTRADO = "Metodo de pago no encontrado"
DUPLICADO = "Ya existe un metodo de pago con ese nombre en esta clinica"


@router.get("", response_model=list[MetodoPagoResponse], dependencies=[Depends(LECTURA)])
def listar_metodos_pago(
    incluir_inactivos: bool = False,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> list[MetodoPagoResponse]:
    registros = MetodoPagoRepository(db).listar(id_clinica, incluir_inactivos)
    return [MetodoPagoResponse.model_validate(r) for r in registros]


@router.post(
    "",
    response_model=MetodoPagoResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(ESCRITURA)],
)
def crear_metodo_pago(
    body: CatalogoCreateRequest,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> MetodoPagoResponse:
    try:
        registro = MetodoPagoRepository(db).crear(id_clinica, body.model_dump())
    except NombreDuplicadoEnClinicaError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICADO)
    db.commit()
    return MetodoPagoResponse.model_validate(registro)


@router.get(
    "/{id_metodo_pago}", response_model=MetodoPagoResponse, dependencies=[Depends(LECTURA)]
)
def obtener_metodo_pago(
    id_metodo_pago: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> MetodoPagoResponse:
    registro = MetodoPagoRepository(db).obtener(id_clinica, id_metodo_pago)
    if registro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    return MetodoPagoResponse.model_validate(registro)


@router.put(
    "/{id_metodo_pago}", response_model=MetodoPagoResponse, dependencies=[Depends(ESCRITURA)]
)
def actualizar_metodo_pago(
    id_metodo_pago: int,
    body: CatalogoUpdateRequest,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> MetodoPagoResponse:
    try:
        registro = MetodoPagoRepository(db).actualizar(
            id_clinica, id_metodo_pago, body.model_dump(exclude_unset=True)
        )
    except NombreDuplicadoEnClinicaError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICADO)
    if registro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    db.commit()
    return MetodoPagoResponse.model_validate(registro)


@router.delete(
    "/{id_metodo_pago}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(ESCRITURA)],
)
def eliminar_metodo_pago(
    id_metodo_pago: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> Response:
    if not MetodoPagoRepository(db).eliminar(id_clinica, id_metodo_pago):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
