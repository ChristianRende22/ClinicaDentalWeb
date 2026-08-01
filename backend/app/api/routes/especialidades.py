from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles, resolve_clinica_id
from app.db import get_db
from app.exceptions import NombreDuplicadoEnClinicaError
from app.models import RolUsuario
from app.repositories.especialidad_repository import EspecialidadRepository
from app.schemas.parametros import (
    CatalogoCreateRequest,
    CatalogoUpdateRequest,
    EspecialidadResponse,
)

# Regla unica del Modulo 3: los 4 roles leen, solo admin y superadmin escriben.
LECTURA = require_roles(
    RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.DOCTOR, RolUsuario.ASISTENTE
)
ESCRITURA = require_roles(RolUsuario.SUPERADMIN, RolUsuario.ADMIN)

router = APIRouter(prefix="/especialidades", tags=["especialidades"])

NO_ENCONTRADA = "Especialidad no encontrada"
DUPLICADA = "Ya existe una especialidad con ese nombre en esta clinica"


@router.get("", response_model=list[EspecialidadResponse], dependencies=[Depends(LECTURA)])
def listar_especialidades(
    incluir_inactivos: bool = False,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> list[EspecialidadResponse]:
    registros = EspecialidadRepository(db).listar(id_clinica, incluir_inactivos)
    return [EspecialidadResponse.model_validate(r) for r in registros]


@router.post(
    "",
    response_model=EspecialidadResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(ESCRITURA)],
)
def crear_especialidad(
    body: CatalogoCreateRequest,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> EspecialidadResponse:
    try:
        registro = EspecialidadRepository(db).crear(id_clinica, body.model_dump())
    except NombreDuplicadoEnClinicaError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICADA)
    db.commit()
    return EspecialidadResponse.model_validate(registro)


@router.get(
    "/{id_especialidad}", response_model=EspecialidadResponse, dependencies=[Depends(LECTURA)]
)
def obtener_especialidad(
    id_especialidad: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> EspecialidadResponse:
    registro = EspecialidadRepository(db).obtener(id_clinica, id_especialidad)
    if registro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADA)
    return EspecialidadResponse.model_validate(registro)


@router.put(
    "/{id_especialidad}", response_model=EspecialidadResponse, dependencies=[Depends(ESCRITURA)]
)
def actualizar_especialidad(
    id_especialidad: int,
    body: CatalogoUpdateRequest,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> EspecialidadResponse:
    try:
        registro = EspecialidadRepository(db).actualizar(
            id_clinica, id_especialidad, body.model_dump(exclude_unset=True)
        )
    except NombreDuplicadoEnClinicaError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICADA)
    if registro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADA)
    db.commit()
    return EspecialidadResponse.model_validate(registro)


@router.delete(
    "/{id_especialidad}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(ESCRITURA)],
)
def eliminar_especialidad(
    id_especialidad: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> Response:
    """Borrado logico: pone activo = False, no borra la fila."""
    if not EspecialidadRepository(db).eliminar(id_clinica, id_especialidad):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADA)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
