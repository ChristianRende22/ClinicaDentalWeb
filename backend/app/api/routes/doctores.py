from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_doctor_actual, require_roles, resolve_clinica_id
from app.db import get_db
from app.exceptions import (
    HorarioInvalidoError,
    ReferenciaEnUsoError,
    ReferenciaInvalidaError,
    UsernameYaExisteError,
)
from app.models import RolUsuario, Usuario
from app.repositories.doctor_repository import DoctorRepository
from app.repositories.horario_doctor_repository import HorarioDoctorRepository
from app.schemas.personas import (
    BloqueHorarioSchema,
    DoctorCreate,
    DoctorCreateResponse,
    DoctorResponse,
    DoctorUpdate,
    HorarioDoctorRequest,
)
from app.services.personal_service import PersonalService

LECTURA = require_roles(
    RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.DOCTOR, RolUsuario.ASISTENTE
)
ESCRITURA = require_roles(RolUsuario.SUPERADMIN, RolUsuario.ADMIN)
# El horario lo escribe un admin, o el propio doctor sobre el suyo: la
# verificacion fina de "el suyo" se hace en el endpoint, porque depende del id
# de la URL y require_roles no lo ve.
ESCRITURA_HORARIO = require_roles(
    RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.DOCTOR
)

router = APIRouter(prefix="/doctores", tags=["doctores"])

NO_ENCONTRADO = "Doctor no encontrado"
USERNAME_DUPLICADO = "Ya existe un usuario con ese username"


@router.get("", response_model=list[DoctorResponse], dependencies=[Depends(LECTURA)])
def listar_doctores(
    id_especialidad: int | None = None,
    incluir_inactivos: bool = False,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> list[DoctorResponse]:
    registros = DoctorRepository(db).listar(
        id_clinica, id_especialidad, incluir_inactivos
    )
    return [DoctorResponse.model_validate(r) for r in registros]


@router.post(
    "",
    response_model=DoctorCreateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(ESCRITURA)],
)
def crear_doctor(
    body: DoctorCreate,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> DoctorCreateResponse:
    """La password temporal se devuelve UNA sola vez, aca."""
    try:
        resultado = PersonalService(db).crear_doctor(id_clinica, body.model_dump())
    except UsernameYaExisteError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=USERNAME_DUPLICADO
        )
    except ReferenciaInvalidaError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        )
    return DoctorCreateResponse(
        doctor=DoctorResponse.model_validate(resultado["perfil"]),
        password_temporal=resultado["password_temporal"],
    )


@router.get(
    "/{id_doctor}", response_model=DoctorResponse, dependencies=[Depends(LECTURA)]
)
def obtener_doctor(
    id_doctor: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> DoctorResponse:
    registro = DoctorRepository(db).obtener(id_clinica, id_doctor)
    if registro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    return DoctorResponse.model_validate(registro)


@router.put(
    "/{id_doctor}", response_model=DoctorResponse, dependencies=[Depends(ESCRITURA)]
)
def actualizar_doctor(
    id_doctor: int,
    body: DoctorUpdate,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> DoctorResponse:
    datos = body.model_dump(exclude_unset=True)
    try:
        PersonalService(db).validar_especialidad(id_clinica, datos.get("id_especialidad"))
    except ReferenciaInvalidaError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        )

    # 'activo' no se aplica por setattr: la actividad del perfil y la del
    # Usuario tienen que moverse juntas, y de eso se encarga PersonalService.
    # Se resuelve AL FINAL y no antes porque el servicio commitea adentro: si
    # se hiciera primero y despues fallara el resto del PUT, la baja quedaria
    # aplicada y el cliente recibiria un error creyendo que no se aplico nada.
    activo = datos.pop("activo", None)

    registro = DoctorRepository(db).actualizar(id_clinica, id_doctor, datos)
    if registro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)

    if activo is None:
        db.commit()
    else:
        # El servicio commitea, y arrastra en la misma transaccion los cambios
        # que el repositorio dejo flusheados. Un solo commit por request.
        servicio = PersonalService(db)
        try:
            cambio = (
                servicio.reactivar_doctor(id_clinica, id_doctor)
                if activo
                else servicio.dar_de_baja_doctor(id_clinica, id_doctor)
            )
        except ReferenciaInvalidaError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
            )
        except ReferenciaEnUsoError as error:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
        if not cambio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO
            )

    return DoctorResponse.model_validate(registro)


@router.delete(
    "/{id_doctor}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(ESCRITURA)],
)
def dar_de_baja_doctor(
    id_doctor: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> Response:
    """Desactiva el perfil Y el Usuario: un profesional dado de baja no debe
    poder seguir entrando al sistema.

    409 y no 422 si tiene un plan de tratamiento activo (Modulo 5): es un
    conflicto con el estado del sistema, no una regla sobre datos enviados.
    """
    try:
        dado_de_baja = PersonalService(db).dar_de_baja_doctor(id_clinica, id_doctor)
    except ReferenciaInvalidaError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        )
    except ReferenciaEnUsoError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    if not dado_de_baja:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{id_doctor}/horarios",
    response_model=list[BloqueHorarioSchema],
    dependencies=[Depends(LECTURA)],
)
def obtener_horarios(
    id_doctor: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> list[BloqueHorarioSchema]:
    if DoctorRepository(db).obtener(id_clinica, id_doctor) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    bloques = HorarioDoctorRepository(db).listar_de_doctor(id_clinica, id_doctor)
    return [BloqueHorarioSchema.model_validate(b) for b in bloques]


@router.put(
    "/{id_doctor}/horarios",
    response_model=list[BloqueHorarioSchema],
    dependencies=[Depends(ESCRITURA_HORARIO)],
)
def reemplazar_horarios(
    id_doctor: int,
    body: HorarioDoctorRequest,
    id_clinica: int = Depends(resolve_clinica_id),
    usuario: Usuario = Depends(get_current_user),
    doctor_actual=Depends(get_doctor_actual),
    db: Session = Depends(get_db),
) -> list[BloqueHorarioSchema]:
    """Reemplaza el conjunto completo de bloques. Un doctor solo puede tocar el
    suyo; un admin, el de cualquiera de su clinica.
    """
    if usuario.rol == RolUsuario.DOCTOR and (
        doctor_actual is None or doctor_actual.id_doctor != id_doctor
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo podes editar tu propio horario",
        )

    if DoctorRepository(db).obtener(id_clinica, id_doctor) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)

    try:
        bloques = HorarioDoctorRepository(db).reemplazar_de_doctor(
            id_clinica, id_doctor, [b.model_dump() for b in body.bloques]
        )
    except HorarioInvalidoError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        )
    db.commit()
    return [BloqueHorarioSchema.model_validate(b) for b in bloques]
