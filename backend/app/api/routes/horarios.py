from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles, resolve_clinica_id
from app.db import get_db
from app.exceptions import HorarioInvalidoError
from app.models import HORARIO_POR_DEFECTO, DiaSemana, RolUsuario
from app.repositories.horario_clinica_repository import HorarioClinicaRepository
from app.schemas.parametros import HorarioDiaSchema, HorarioSemanaRequest

LECTURA = require_roles(
    RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.DOCTOR, RolUsuario.ASISTENTE
)
ESCRITURA = require_roles(RolUsuario.SUPERADMIN, RolUsuario.ADMIN)

router = APIRouter(prefix="/horarios", tags=["horario de atencion"])


def _semana_completa(filas) -> list[HorarioDiaSchema]:
    """Devuelve siempre los 7 dias: los que no tienen fila salen con el default,
    sin persistirlos. Asi el frontend nunca tiene que rellenar huecos.
    """
    existentes = {fila.dia_semana: fila for fila in filas}
    semana = []
    for dia in DiaSemana:
        fila = existentes.get(dia)
        if fila is None:
            semana.append(HorarioDiaSchema(dia_semana=dia, **HORARIO_POR_DEFECTO[dia]))
        else:
            semana.append(HorarioDiaSchema.model_validate(fila))
    return semana


@router.get("", response_model=list[HorarioDiaSchema], dependencies=[Depends(LECTURA)])
def obtener_horario(
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> list[HorarioDiaSchema]:
    return _semana_completa(HorarioClinicaRepository(db).listar_semana(id_clinica))


@router.put("", response_model=list[HorarioDiaSchema], dependencies=[Depends(ESCRITURA)])
def reemplazar_horario(
    body: HorarioSemanaRequest,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> list[HorarioDiaSchema]:
    try:
        filas = HorarioClinicaRepository(db).reemplazar_semana(
            id_clinica, [dia.model_dump() for dia in body.dias]
        )
    except HorarioInvalidoError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        )
    db.commit()
    return _semana_completa(filas)
