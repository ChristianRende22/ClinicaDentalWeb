from calendar import monthrange
from datetime import date, datetime, time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_doctor_actual, resolve_clinica_id, require_roles
from app.db import get_db
from app.models import Doctor, EstadoCita, RolUsuario, Usuario
from app.repositories.cita_repository import CitaRepository
from app.schemas.dashboard import ResumenCitasResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

VER_CITAS = require_roles(
    RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.ASISTENTE, RolUsuario.DOCTOR
)
VER_FINANCIERO = require_roles(RolUsuario.SUPERADMIN, RolUsuario.ADMIN)


def _rango_mes_actual() -> tuple[date, date]:
    hoy = date.today()
    ultimo_dia = monthrange(hoy.year, hoy.month)[1]
    return date(hoy.year, hoy.month, 1), date(hoy.year, hoy.month, ultimo_dia)


def _completar_rango(desde: date | None, hasta: date | None) -> tuple[date, date]:
    desde_defecto, hasta_defecto = _rango_mes_actual()
    return desde or desde_defecto, hasta or hasta_defecto


@router.get("/citas/resumen", response_model=ResumenCitasResponse, dependencies=[Depends(VER_CITAS)])
def resumen_citas(
    desde: date | None = None,
    hasta: date | None = None,
    id_doctor: int | None = None,
    id_clinica: int = Depends(resolve_clinica_id),
    usuario: Usuario = Depends(get_current_user),
    doctor_actual: Doctor | None = Depends(get_doctor_actual),
    db: Session = Depends(get_db),
) -> ResumenCitasResponse:
    desde, hasta = _completar_rango(desde, hasta)

    if usuario.rol == RolUsuario.DOCTOR:
        if doctor_actual is None:
            return ResumenCitasResponse(
                desde=desde, hasta=hasta, total=0,
                por_estado={estado.value: 0 for estado in EstadoCita}, por_doctor=[],
            )
        resumen = CitaRepository(db).resumen_por_estado(
            id_clinica,
            desde=datetime.combine(desde, time.min),
            hasta=datetime.combine(hasta, time.max),
            id_doctor=doctor_actual.id_doctor,
            incluir_por_doctor=False,
        )
        return ResumenCitasResponse(desde=desde, hasta=hasta, **resumen)

    resumen = CitaRepository(db).resumen_por_estado(
        id_clinica,
        desde=datetime.combine(desde, time.min),
        hasta=datetime.combine(hasta, time.max),
        id_doctor=id_doctor,
    )
    return ResumenCitasResponse(desde=desde, hasta=hasta, **resumen)
