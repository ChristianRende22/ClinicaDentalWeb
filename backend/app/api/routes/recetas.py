from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles, resolve_clinica_id
from app.db import get_db
from app.exceptions import ReferenciaInvalidaError
from app.models import RolUsuario
from app.repositories.receta_repository import RecetaDetalleRepository, RecetaRepository
from app.schemas.receta import RecetaCreate, RecetaResponse
from app.services.receta_service import RecetaService

# Solo un doctor emite una receta: ni el admin ni la asistente prescriben
# medicamentos (a diferencia de Consulta/PlanTratamiento, donde si escriben).
LECTURA = require_roles(
    RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.DOCTOR, RolUsuario.ASISTENTE
)
ESCRITURA = require_roles(RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.DOCTOR)

router = APIRouter(prefix="/recetas", tags=["recetas"])

NO_ENCONTRADA = "Receta no encontrada"


def _con_detalles(db: Session, id_clinica: int, receta) -> RecetaResponse:
    from app.schemas.receta import RecetaDetalleResponse

    detalles = RecetaDetalleRepository(db).listar_de_receta(id_clinica, receta.id_receta)
    respuesta = RecetaResponse.model_validate(receta)
    respuesta.medicamentos = [RecetaDetalleResponse.model_validate(d) for d in detalles]
    return respuesta


@router.get("", response_model=list[RecetaResponse], dependencies=[Depends(LECTURA)])
def listar_recetas(
    id_paciente: int | None = None,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> list[RecetaResponse]:
    registros = RecetaRepository(db).listar(id_clinica, id_paciente=id_paciente)
    return [_con_detalles(db, id_clinica, r) for r in registros]


@router.post(
    "", response_model=RecetaResponse, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(ESCRITURA)],
)
def crear_receta(
    body: RecetaCreate,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> RecetaResponse:
    try:
        receta = RecetaService(db).crear(id_clinica, body.model_dump())
    except ReferenciaInvalidaError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        )
    return _con_detalles(db, id_clinica, receta)


@router.get("/{id_receta}", response_model=RecetaResponse, dependencies=[Depends(LECTURA)])
def obtener_receta(
    id_receta: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> RecetaResponse:
    registro = RecetaRepository(db).obtener(id_clinica, id_receta)
    if registro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADA)
    return _con_detalles(db, id_clinica, registro)
