from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles, resolve_clinica_id
from app.db import get_db
from app.exceptions import ReferenciaInvalidaError, UsernameYaExisteError
from app.models import RolUsuario
from app.repositories.asistente_repository import AsistenteRepository
from app.schemas.personas import (
    AsistenteCreate,
    AsistenteCreateResponse,
    AsistenteResponse,
    AsistenteUpdate,
)
from app.services.personal_service import PersonalService

LECTURA = require_roles(
    RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.DOCTOR, RolUsuario.ASISTENTE
)
ESCRITURA = require_roles(RolUsuario.SUPERADMIN, RolUsuario.ADMIN)

router = APIRouter(prefix="/asistentes", tags=["asistentes"])

NO_ENCONTRADO = "Asistente no encontrado"
USERNAME_DUPLICADO = "Ya existe un usuario con ese username"


@router.get("", response_model=list[AsistenteResponse], dependencies=[Depends(LECTURA)])
def listar_asistentes(
    incluir_inactivos: bool = False,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> list[AsistenteResponse]:
    registros = AsistenteRepository(db).listar(id_clinica, incluir_inactivos)
    return [AsistenteResponse.model_validate(r) for r in registros]


@router.post(
    "",
    response_model=AsistenteCreateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(ESCRITURA)],
)
def crear_asistente(
    body: AsistenteCreate,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> AsistenteCreateResponse:
    try:
        resultado = PersonalService(db).crear_asistente(id_clinica, body.model_dump())
    except UsernameYaExisteError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=USERNAME_DUPLICADO
        )
    return AsistenteCreateResponse(
        asistente=AsistenteResponse.model_validate(resultado["perfil"]),
        password_temporal=resultado["password_temporal"],
    )


@router.get(
    "/{id_asistente}", response_model=AsistenteResponse, dependencies=[Depends(LECTURA)]
)
def obtener_asistente(
    id_asistente: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> AsistenteResponse:
    registro = AsistenteRepository(db).obtener(id_clinica, id_asistente)
    if registro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    return AsistenteResponse.model_validate(registro)


@router.put(
    "/{id_asistente}",
    response_model=AsistenteResponse,
    dependencies=[Depends(ESCRITURA)],
)
def actualizar_asistente(
    id_asistente: int,
    body: AsistenteUpdate,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> AsistenteResponse:
    datos = body.model_dump(exclude_unset=True)

    # 'activo' no se aplica por setattr: la actividad del perfil y la del
    # Usuario tienen que moverse juntas, y de eso se encarga PersonalService.
    # Se resuelve AL FINAL y no antes porque el servicio commitea adentro: si
    # se hiciera primero y despues fallara el resto del PUT, la baja quedaria
    # aplicada y el cliente recibiria un error creyendo que no se aplico nada.
    activo = datos.pop("activo", None)

    registro = AsistenteRepository(db).actualizar(id_clinica, id_asistente, datos)
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
                servicio.reactivar_asistente(id_clinica, id_asistente)
                if activo
                else servicio.dar_de_baja_asistente(id_clinica, id_asistente)
            )
        except ReferenciaInvalidaError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
            )
        if not cambio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO
            )

    return AsistenteResponse.model_validate(registro)


@router.delete(
    "/{id_asistente}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(ESCRITURA)],
)
def dar_de_baja_asistente(
    id_asistente: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> Response:
    try:
        dado_de_baja = PersonalService(db).dar_de_baja_asistente(id_clinica, id_asistente)
    except ReferenciaInvalidaError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        )
    if not dado_de_baja:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
