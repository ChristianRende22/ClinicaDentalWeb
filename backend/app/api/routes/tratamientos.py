from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles, resolve_clinica_id
from app.db import get_db
from app.exceptions import NombreDuplicadoEnClinicaError, ReferenciaEnUsoError
from app.models import RolUsuario
from app.repositories.tratamiento_repository import TratamientoRepository
from app.schemas.tratamiento import TratamientoCreate, TratamientoResponse, TratamientoUpdate

# Tratamiento es catalogo con precio: mismo criterio de permisos que
# MetodoPago del Modulo 3 (es dinero), no el de Paciente/Cita del Modulo 4.
LECTURA = require_roles(
    RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.DOCTOR, RolUsuario.ASISTENTE
)
ESCRITURA = require_roles(RolUsuario.SUPERADMIN, RolUsuario.ADMIN)

router = APIRouter(prefix="/tratamientos", tags=["tratamientos"])

NO_ENCONTRADO = "Tratamiento no encontrado"


@router.get("", response_model=list[TratamientoResponse], dependencies=[Depends(LECTURA)])
def listar_tratamientos(
    incluir_inactivos: bool = False,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> list[TratamientoResponse]:
    registros = TratamientoRepository(db).listar(id_clinica, incluir_inactivos)
    return [TratamientoResponse.model_validate(r) for r in registros]


@router.post(
    "",
    response_model=TratamientoResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(ESCRITURA)],
)
def crear_tratamiento(
    body: TratamientoCreate,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> TratamientoResponse:
    try:
        registro = TratamientoRepository(db).crear(id_clinica, body.model_dump())
    except NombreDuplicadoEnClinicaError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    db.commit()
    return TratamientoResponse.model_validate(registro)


@router.get(
    "/{id_tratamiento}", response_model=TratamientoResponse, dependencies=[Depends(LECTURA)]
)
def obtener_tratamiento(
    id_tratamiento: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> TratamientoResponse:
    registro = TratamientoRepository(db).obtener(id_clinica, id_tratamiento)
    if registro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    return TratamientoResponse.model_validate(registro)


@router.put(
    "/{id_tratamiento}", response_model=TratamientoResponse, dependencies=[Depends(ESCRITURA)]
)
def actualizar_tratamiento(
    id_tratamiento: int,
    body: TratamientoUpdate,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> TratamientoResponse:
    datos = body.model_dump(exclude_unset=True)
    try:
        registro = TratamientoRepository(db).actualizar(id_clinica, id_tratamiento, datos)
    except NombreDuplicadoEnClinicaError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    if registro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    db.commit()
    return TratamientoResponse.model_validate(registro)


@router.delete(
    "/{id_tratamiento}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(ESCRITURA)],
)
def dar_de_baja_tratamiento(
    id_tratamiento: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> Response:
    """409 y no 422 si esta en uso: es un conflicto con el estado del
    sistema, no una regla sobre datos enviados (mismo criterio que
    ChoqueDeCitaError en el Modulo 4).
    """
    try:
        dado_de_baja = TratamientoRepository(db).eliminar(id_clinica, id_tratamiento)
    except ReferenciaEnUsoError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    if not dado_de_baja:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
