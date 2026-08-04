from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_doctor_actual, require_roles, resolve_clinica_id
from app.db import get_db
from app.exceptions import (
    AnticipacionInsuficienteError,
    ChoqueDeCitaError,
    CitaEnElPasadoError,
    DoctorNoDisponibleError,
    FueraDeHorarioClinicaError,
    ReferenciaInvalidaError,
    TransicionInvalidaError,
)
from app.models import EstadoCita, RolUsuario, Usuario
from app.repositories.asistente_repository import AsistenteRepository
from app.repositories.cita_repository import CitaRepository
from app.schemas.cita import (
    CambiarEstadoRequest,
    CitaCreate,
    CitaResponse,
    ReagendarRequest,
)
from app.services.cita_service import CitaService

LECTURA = require_roles(
    RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.DOCTOR, RolUsuario.ASISTENTE
)
AGENDAR = require_roles(
    RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.ASISTENTE
)
CAMBIAR_ESTADO = require_roles(
    RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.ASISTENTE, RolUsuario.DOCTOR
)

router = APIRouter(prefix="/citas", tags=["citas"])

NO_ENCONTRADA = "Cita no encontrada"

#: Las reglas que chocan con el estado del sistema van a 409; las que violan una
#: regla sobre los datos enviados, a 422.
_A_409 = (ChoqueDeCitaError, TransicionInvalidaError)
_A_422 = (
    ReferenciaInvalidaError,
    CitaEnElPasadoError,
    AnticipacionInsuficienteError,
    FueraDeHorarioClinicaError,
    DoctorNoDisponibleError,
)


def _traducir(error: Exception) -> HTTPException:
    if isinstance(error, _A_409):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
    )


def _cita_visible(
    db: Session, id_clinica: int, id_cita: int, usuario: Usuario, doctor_actual
):
    """Devuelve la cita si el usuario puede verla, o None.

    Para el rol doctor, una cita ajena devuelve None y la ruta responde 404, no
    403: un 403 le confirmaria que la cita existe, que ya es informacion sobre
    un paciente que no atiende.

    El chequeo se hace por ROL y no por "tiene perfil": un Usuario con rol
    doctor pero sin fila Doctor (posible si el alta no paso por PersonalService)
    no debe ver nada, en vez de ver todo. La falla tiene que cerrar, no abrir.
    """
    cita = CitaRepository(db).obtener(id_clinica, id_cita)
    if cita is None:
        return None
    if usuario.rol == RolUsuario.DOCTOR:
        if doctor_actual is None or cita.id_doctor != doctor_actual.id_doctor:
            return None
    return cita


@router.get("", response_model=list[CitaResponse], dependencies=[Depends(LECTURA)])
def listar_citas(
    desde: datetime | None = None,
    hasta: datetime | None = None,
    id_doctor: int | None = None,
    id_paciente: int | None = None,
    estado: EstadoCita | None = None,
    id_clinica: int = Depends(resolve_clinica_id),
    usuario: Usuario = Depends(get_current_user),
    doctor_actual=Depends(get_doctor_actual),
    db: Session = Depends(get_db),
) -> list[CitaResponse]:
    # El filtro del doctor es un WHERE inyectado, no un 403. Se decide por rol:
    # un doctor sin perfil no ve nada, en vez de ver todo.
    if usuario.rol == RolUsuario.DOCTOR:
        if doctor_actual is None:
            return []
        id_doctor = doctor_actual.id_doctor

    registros = CitaRepository(db).listar(
        id_clinica,
        desde=desde,
        hasta=hasta,
        id_doctor=id_doctor,
        id_paciente=id_paciente,
        estado=estado,
    )
    return [CitaResponse.model_validate(c) for c in registros]


@router.post(
    "",
    response_model=CitaResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(AGENDAR)],
)
def agendar_cita(
    body: CitaCreate,
    id_clinica: int = Depends(resolve_clinica_id),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CitaResponse:
    # id_asistente sale del token, nunca del body: es un dato de auditoria y el
    # cliente no debe poder mentir sobre quien agendo.
    id_asistente = None
    if usuario.rol == RolUsuario.ASISTENTE:
        perfil = AsistenteRepository(db).obtener_por_usuario(usuario.id_usuario)
        id_asistente = perfil.id_asistente if perfil else None

    try:
        cita = CitaService(db).crear(id_clinica, body.model_dump(), id_asistente)
    except (*_A_409, *_A_422) as error:
        raise _traducir(error)
    db.commit()
    return CitaResponse.model_validate(cita)


@router.get("/{id_cita}", response_model=CitaResponse, dependencies=[Depends(LECTURA)])
def obtener_cita(
    id_cita: int,
    id_clinica: int = Depends(resolve_clinica_id),
    usuario: Usuario = Depends(get_current_user),
    doctor_actual=Depends(get_doctor_actual),
    db: Session = Depends(get_db),
) -> CitaResponse:
    cita = _cita_visible(db, id_clinica, id_cita, usuario, doctor_actual)
    if cita is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADA)
    return CitaResponse.model_validate(cita)


@router.patch(
    "/{id_cita}/estado",
    response_model=CitaResponse,
    dependencies=[Depends(CAMBIAR_ESTADO)],
)
def cambiar_estado_cita(
    id_cita: int,
    body: CambiarEstadoRequest,
    id_clinica: int = Depends(resolve_clinica_id),
    usuario: Usuario = Depends(get_current_user),
    doctor_actual=Depends(get_doctor_actual),
    db: Session = Depends(get_db),
) -> CitaResponse:
    if _cita_visible(db, id_clinica, id_cita, usuario, doctor_actual) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADA)

    try:
        cita = CitaService(db).cambiar_estado(id_clinica, id_cita, body.estado)
    except (*_A_409, *_A_422) as error:
        raise _traducir(error)
    if cita is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADA)
    db.commit()
    return CitaResponse.model_validate(cita)


@router.patch(
    "/{id_cita}/cancelar",
    response_model=CitaResponse,
    dependencies=[Depends(CAMBIAR_ESTADO)],
)
def cancelar_cita(
    id_cita: int,
    id_clinica: int = Depends(resolve_clinica_id),
    usuario: Usuario = Depends(get_current_user),
    doctor_actual=Depends(get_doctor_actual),
    db: Session = Depends(get_db),
) -> CitaResponse:
    if _cita_visible(db, id_clinica, id_cita, usuario, doctor_actual) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADA)

    try:
        cita = CitaService(db).cancelar(id_clinica, id_cita)
    except (*_A_409, *_A_422) as error:
        raise _traducir(error)
    if cita is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADA)
    db.commit()
    return CitaResponse.model_validate(cita)


@router.patch(
    "/{id_cita}/reagendar", response_model=CitaResponse, dependencies=[Depends(AGENDAR)]
)
def reagendar_cita(
    id_cita: int,
    body: ReagendarRequest,
    id_clinica: int = Depends(resolve_clinica_id),
    usuario: Usuario = Depends(get_current_user),
    doctor_actual=Depends(get_doctor_actual),
    db: Session = Depends(get_db),
) -> CitaResponse:
    """Mueve la cita en su lugar: misma fila, fecha nueva, contador +1, estado
    de vuelta a 'programada'.

    Pasa por _cita_visible igual que los otros tres endpoints, aunque hoy el rol
    doctor no llegue nunca aca (no esta en AGENDAR). Es para que el patron sea
    uniforme: si alguna vez se le da permiso de reagendar a un doctor, el filtro
    ya esta puesto y no hay que acordarse de agregarlo.
    """
    if _cita_visible(db, id_clinica, id_cita, usuario, doctor_actual) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADA)

    try:
        cita = CitaService(db).reagendar(
            id_clinica, id_cita, body.fecha_hora, body.id_consultorio
        )
    except (*_A_409, *_A_422) as error:
        raise _traducir(error)
    if cita is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADA)
    db.commit()
    return CitaResponse.model_validate(cita)
