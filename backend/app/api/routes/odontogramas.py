from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles, resolve_clinica_id
from app.db import get_db
from app.models import RolUsuario
from app.repositories.odontograma_repository import OdontogramaRepository
from app.repositories.paciente_repository import PacienteRepository
from app.schemas.odontograma import OdontogramaUpdateRequest, PiezaDentalResponse

# Un asistente no diagnostica (ver tabla de permisos, seccion 5 del spec),
# aunque si puede agendar y registrar pacientes.
LECTURA = require_roles(
    RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.DOCTOR, RolUsuario.ASISTENTE
)
ESCRITURA = require_roles(RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.DOCTOR)

router = APIRouter(prefix="/pacientes/{id_paciente}/odontograma", tags=["odontogramas"])

PACIENTE_NO_ENCONTRADO = "Paciente no encontrado"


def _exigir_paciente(db: Session, id_clinica: int, id_paciente: int) -> None:
    """El repositorio de odontograma no valida que el paciente sea de esta
    clinica (documentado en el propio repositorio); la ruta lo hace, igual
    que doctores.py valida al doctor antes de tocar su horario.
    """
    if PacienteRepository(db).obtener(id_clinica, id_paciente) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=PACIENTE_NO_ENCONTRADO
        )


@router.get("", response_model=list[PiezaDentalResponse], dependencies=[Depends(LECTURA)])
def obtener_odontograma(
    id_paciente: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> list[PiezaDentalResponse]:
    _exigir_paciente(db, id_clinica, id_paciente)
    piezas = OdontogramaRepository(db).listar_piezas(id_clinica, id_paciente)
    return [PiezaDentalResponse.model_validate(p) for p in piezas]


@router.put("", response_model=list[PiezaDentalResponse], dependencies=[Depends(ESCRITURA)])
def actualizar_odontograma(
    id_paciente: int,
    body: OdontogramaUpdateRequest,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> list[PiezaDentalResponse]:
    """Upsert parcial: solo las piezas del body se tocan (decision 4 del
    spec). No hace falta reenviar las 32.
    """
    _exigir_paciente(db, id_clinica, id_paciente)
    repo = OdontogramaRepository(db)
    for pieza in body.piezas:
        repo.actualizar_pieza(
            id_clinica,
            id_paciente,
            pieza.numero_pieza,
            {"estado": pieza.estado, "observaciones": pieza.observaciones},
        )
    db.commit()
    piezas = repo.listar_piezas(id_clinica, id_paciente)
    return [PiezaDentalResponse.model_validate(p) for p in piezas]
