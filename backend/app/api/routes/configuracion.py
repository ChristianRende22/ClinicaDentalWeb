from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_roles, resolve_clinica_id
from app.db import get_db
from app.models import RolUsuario
from app.repositories.configuracion_repository import ConfiguracionClinicaRepository
from app.schemas.parametros import ConfiguracionResponse, ConfiguracionUpdateRequest

LECTURA = require_roles(
    RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.DOCTOR, RolUsuario.ASISTENTE
)
ESCRITURA = require_roles(RolUsuario.SUPERADMIN, RolUsuario.ADMIN)

router = APIRouter(prefix="/configuracion", tags=["configuracion de clinica"])


@router.get("", response_model=ConfiguracionResponse, dependencies=[Depends(LECTURA)])
def obtener_configuracion(
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> ConfiguracionResponse:
    """Si la clinica todavia no tiene configuracion, se crea con los defaults.

    Es la unica lectura del modulo que escribe: se decidio asi para no tocar
    ClinicaService (Modulo 2) ni migrar datos de las clinicas preexistentes.
    """
    config = ConfiguracionClinicaRepository(db).obtener_o_crear(id_clinica)
    db.commit()
    return ConfiguracionResponse.model_validate(config)


@router.put("", response_model=ConfiguracionResponse, dependencies=[Depends(ESCRITURA)])
def actualizar_configuracion(
    body: ConfiguracionUpdateRequest,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> ConfiguracionResponse:
    config = ConfiguracionClinicaRepository(db).actualizar(
        id_clinica, body.model_dump(exclude_unset=True)
    )
    db.commit()
    return ConfiguracionResponse.model_validate(config)
