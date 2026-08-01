from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles, resolve_clinica_id
from app.db import get_db
from app.exceptions import NombreDuplicadoEnClinicaError
from app.models import RolUsuario
from app.repositories.consultorio_repository import ConsultorioRepository
from app.schemas.parametros import (
    CatalogoCreateRequest,
    CatalogoUpdateRequest,
    ConsultorioResponse,
)

LECTURA = require_roles(
    RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.DOCTOR, RolUsuario.ASISTENTE
)
ESCRITURA = require_roles(RolUsuario.SUPERADMIN, RolUsuario.ADMIN)

router = APIRouter(prefix="/consultorios", tags=["consultorios"])

NO_ENCONTRADO = "Consultorio no encontrado"
DUPLICADO = "Ya existe un consultorio con ese nombre en esta clinica"


@router.get("", response_model=list[ConsultorioResponse], dependencies=[Depends(LECTURA)])
def listar_consultorios(
    incluir_inactivos: bool = False,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> list[ConsultorioResponse]:
    registros = ConsultorioRepository(db).listar(id_clinica, incluir_inactivos)
    return [ConsultorioResponse.model_validate(r) for r in registros]


@router.post(
    "",
    response_model=ConsultorioResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(ESCRITURA)],
)
def crear_consultorio(
    body: CatalogoCreateRequest,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> ConsultorioResponse:
    try:
        registro = ConsultorioRepository(db).crear(id_clinica, body.model_dump())
    except NombreDuplicadoEnClinicaError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICADO)
    db.commit()
    return ConsultorioResponse.model_validate(registro)


@router.get(
    "/{id_consultorio}", response_model=ConsultorioResponse, dependencies=[Depends(LECTURA)]
)
def obtener_consultorio(
    id_consultorio: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> ConsultorioResponse:
    registro = ConsultorioRepository(db).obtener(id_clinica, id_consultorio)
    if registro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    return ConsultorioResponse.model_validate(registro)


@router.put(
    "/{id_consultorio}", response_model=ConsultorioResponse, dependencies=[Depends(ESCRITURA)]
)
def actualizar_consultorio(
    id_consultorio: int,
    body: CatalogoUpdateRequest,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> ConsultorioResponse:
    try:
        registro = ConsultorioRepository(db).actualizar(
            id_clinica, id_consultorio, body.model_dump(exclude_unset=True)
        )
    except NombreDuplicadoEnClinicaError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICADO)
    if registro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    db.commit()
    return ConsultorioResponse.model_validate(registro)


@router.delete(
    "/{id_consultorio}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(ESCRITURA)],
)
def eliminar_consultorio(
    id_consultorio: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> Response:
    if not ConsultorioRepository(db).eliminar(id_clinica, id_consultorio):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
