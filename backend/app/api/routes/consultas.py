from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles, resolve_clinica_id
from app.db import get_db
from app.exceptions import ReferenciaInvalidaError
from app.models import RolUsuario
from app.repositories.consulta_repository import ConsultaRepository
from app.repositories.diagnostico_repository import DiagnosticoRepository
from app.schemas.consulta import (
    ConsultaCreate,
    ConsultaResponse,
    DiagnosticoCreate,
    DiagnosticoResponse,
)
from app.services.consulta_service import ConsultaService

# Mismo criterio que Paciente/Cita del Modulo 4: quien atiende registra.
LECTURA = require_roles(
    RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.DOCTOR, RolUsuario.ASISTENTE
)
ESCRITURA = require_roles(RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.ASISTENTE, RolUsuario.DOCTOR)

router = APIRouter(prefix="/consultas", tags=["consultas"])

NO_ENCONTRADA = "Consulta no encontrada"


@router.get("", response_model=list[ConsultaResponse], dependencies=[Depends(LECTURA)])
def listar_consultas(
    id_paciente: int | None = None,
    id_doctor: int | None = None,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> list[ConsultaResponse]:
    registros = ConsultaRepository(db).listar(
        id_clinica, id_paciente=id_paciente, id_doctor=id_doctor
    )
    return [ConsultaResponse.model_validate(r) for r in registros]


@router.post(
    "", response_model=ConsultaResponse, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(ESCRITURA)],
)
def crear_consulta(
    body: ConsultaCreate,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> ConsultaResponse:
    try:
        consulta = ConsultaService(db).crear(id_clinica, body.model_dump())
    except ReferenciaInvalidaError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        )
    db.commit()
    return ConsultaResponse.model_validate(consulta)


@router.get("/{id_consulta}", response_model=ConsultaResponse, dependencies=[Depends(LECTURA)])
def obtener_consulta(
    id_consulta: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> ConsultaResponse:
    registro = ConsultaRepository(db).obtener(id_clinica, id_consulta)
    if registro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADA)
    return ConsultaResponse.model_validate(registro)


@router.get(
    "/{id_consulta}/diagnosticos",
    response_model=list[DiagnosticoResponse],
    dependencies=[Depends(LECTURA)],
)
def listar_diagnosticos(
    id_consulta: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> list[DiagnosticoResponse]:
    if ConsultaRepository(db).obtener(id_clinica, id_consulta) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADA)
    registros = DiagnosticoRepository(db).listar(id_clinica, id_consulta=id_consulta)
    return [DiagnosticoResponse.model_validate(r) for r in registros]


@router.post(
    "/{id_consulta}/diagnosticos",
    response_model=DiagnosticoResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(ESCRITURA)],
)
def crear_diagnostico(
    id_consulta: int,
    body: DiagnosticoCreate,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> DiagnosticoResponse:
    if ConsultaRepository(db).obtener(id_clinica, id_consulta) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADA)
    registro = DiagnosticoRepository(db).crear(
        id_clinica, {"id_consulta": id_consulta, **body.model_dump()}
    )
    db.commit()
    return DiagnosticoResponse.model_validate(registro)
