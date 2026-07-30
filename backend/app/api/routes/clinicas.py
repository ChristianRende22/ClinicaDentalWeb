from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db import get_db
from app.exceptions import UsernameYaExisteError
from app.models import EstadoClinica, RolUsuario
from app.repositories.clinica_modulo_repository import ClinicaModuloRepository
from app.repositories.clinica_repository import ClinicaRepository
from app.schemas.clinica import (
    ClinicaCreateRequest,
    ClinicaCreateResponse,
    ClinicaResponse,
    ClinicaUpdateRequest,
    EstadoUpdateRequest,
    ModuloUpdateRequest,
)
from app.services.clinica_service import ClinicaService

router = APIRouter(
    prefix="/clinicas",
    tags=["clinicas"],
    dependencies=[Depends(require_roles(RolUsuario.SUPERADMIN))],
)


@router.post("", response_model=ClinicaCreateResponse, status_code=status.HTTP_201_CREATED)
def crear_clinica(
    body: ClinicaCreateRequest, db: Session = Depends(get_db)
) -> ClinicaCreateResponse:
    try:
        resultado = ClinicaService(db).crear_clinica_con_admin(
            nombre=body.nombre,
            admin_username=body.admin_username,
            direccion=body.direccion,
            telefono=body.telefono,
            correo=body.correo,
        )
    except UsernameYaExisteError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese username",
        )
    return ClinicaCreateResponse(
        clinica=ClinicaResponse.model_validate(resultado["clinica"]),
        admin=resultado["admin"],
        password_temporal=resultado["password_temporal"],
    )


@router.get("", response_model=list[ClinicaResponse])
def listar_clinicas(
    estado: EstadoClinica | None = None, db: Session = Depends(get_db)
) -> list[ClinicaResponse]:
    clinicas = ClinicaRepository(db).listar(estado)
    return [ClinicaResponse.model_validate(c) for c in clinicas]


@router.get("/{id_clinica}", response_model=ClinicaResponse)
def obtener_clinica(id_clinica: int, db: Session = Depends(get_db)) -> ClinicaResponse:
    clinica = ClinicaRepository(db).obtener(id_clinica)
    if clinica is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Clinica no encontrada"
        )
    return ClinicaResponse.model_validate(clinica)


@router.put("/{id_clinica}", response_model=ClinicaResponse)
def actualizar_clinica(
    id_clinica: int, body: ClinicaUpdateRequest, db: Session = Depends(get_db)
) -> ClinicaResponse:
    datos = body.model_dump(exclude_unset=True)
    clinica = ClinicaRepository(db).actualizar(id_clinica, datos)
    if clinica is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Clinica no encontrada"
        )
    db.commit()
    return ClinicaResponse.model_validate(clinica)


@router.patch("/{id_clinica}/estado", response_model=ClinicaResponse)
def cambiar_estado_clinica(
    id_clinica: int, body: EstadoUpdateRequest, db: Session = Depends(get_db)
) -> ClinicaResponse:
    clinica = ClinicaRepository(db).cambiar_estado(id_clinica, body.estado)
    if clinica is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Clinica no encontrada"
        )
    db.commit()
    return ClinicaResponse.model_validate(clinica)


@router.patch("/{id_clinica}/modulos/{modulo}")
def actualizar_modulo(
    id_clinica: int, modulo: str, body: ModuloUpdateRequest, db: Session = Depends(get_db)
) -> dict:
    registro = ClinicaModuloRepository(db).actualizar_estado(
        id_clinica, modulo, body.habilitado
    )
    if registro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Modulo no encontrado para esta clinica",
        )
    db.commit()
    return {"modulo": registro.modulo, "habilitado": registro.habilitado}
