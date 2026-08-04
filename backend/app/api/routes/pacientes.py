from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles, resolve_clinica_id
from app.db import get_db
from app.models import RolUsuario, Usuario
from app.repositories.paciente_repository import PacienteRepository
from app.schemas.personas import PacienteCreate, PacienteResponse, PacienteUpdate

# El Modulo 4 rompe la regla unica del Modulo 3 a proposito: aquel era
# configuracion, esto es la operacion diaria. Una asistente que no puede
# registrar un paciente no puede hacer su trabajo.
LECTURA = require_roles(
    RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.DOCTOR, RolUsuario.ASISTENTE
)
ESCRITURA = require_roles(
    RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.ASISTENTE, RolUsuario.DOCTOR
)
#: Quien puede activar o desactivar un paciente. Se declara como conjunto y no
#: solo como dependencia porque el PUT tambien lo necesita: el campo 'activo'
#: viaja en el body y hay que chequearlo a mano.
ROLES_BAJA = (RolUsuario.SUPERADMIN, RolUsuario.ADMIN)
BAJA = require_roles(*ROLES_BAJA)

router = APIRouter(prefix="/pacientes", tags=["pacientes"])

NO_ENCONTRADO = "Paciente no encontrado"


@router.get("", response_model=list[PacienteResponse], dependencies=[Depends(LECTURA)])
def listar_pacientes(
    buscar: str | None = None,
    incluir_inactivos: bool = False,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> list[PacienteResponse]:
    registros = PacienteRepository(db).listar(id_clinica, buscar, incluir_inactivos)
    return [PacienteResponse.model_validate(r) for r in registros]


@router.post(
    "",
    response_model=PacienteResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(ESCRITURA)],
)
def crear_paciente(
    body: PacienteCreate,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> PacienteResponse:
    registro = PacienteRepository(db).crear(id_clinica, body.model_dump())
    db.commit()
    return PacienteResponse.model_validate(registro)


@router.get(
    "/{id_paciente}", response_model=PacienteResponse, dependencies=[Depends(LECTURA)]
)
def obtener_paciente(
    id_paciente: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> PacienteResponse:
    registro = PacienteRepository(db).obtener(id_clinica, id_paciente)
    if registro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    return PacienteResponse.model_validate(registro)


@router.put(
    "/{id_paciente}", response_model=PacienteResponse, dependencies=[Depends(ESCRITURA)]
)
def actualizar_paciente(
    id_paciente: int,
    body: PacienteUpdate,
    id_clinica: int = Depends(resolve_clinica_id),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PacienteResponse:
    datos = body.model_dump(exclude_unset=True)

    # Sin esto, el PUT seria una puerta trasera al DELETE: 'activo' viaja en el
    # body y el repositorio lo aplica con setattr, asi que un asistente o un
    # doctor (que pueden editar, pero NO dar de baja) podrian desactivar un
    # paciente mandando {"activo": false} y esquivar la regla de permisos.
    # El campo se queda en el schema porque reactivar a alguien dado de baja
    # tambien pasa por aca, pero solo lo puede tocar quien tiene la baja.
    if "activo" in datos and usuario.rol not in ROLES_BAJA:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un administrador puede activar o desactivar un paciente",
        )

    registro = PacienteRepository(db).actualizar(id_clinica, id_paciente, datos)
    if registro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    db.commit()
    return PacienteResponse.model_validate(registro)


@router.delete(
    "/{id_paciente}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(BAJA)],
)
def dar_de_baja_paciente(
    id_paciente: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> Response:
    """Borrado logico: pone activo = False, no borra la fila."""
    if not PacienteRepository(db).eliminar(id_clinica, id_paciente):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
