from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_doctor_actual, resolve_clinica_id, require_roles
from app.db import get_db
from app.exceptions import FacturaAnuladaError, FacturaConPagosError, PagoExcedeSaldoError
from app.models import Doctor, RolUsuario, Usuario
from app.repositories.asistente_repository import AsistenteRepository
from app.repositories.factura_repository import FacturaRepository
from app.repositories.pago_repository import PagoRepository
from app.schemas.factura import FacturaCreate, FacturaResponse, PagoCreate, PagoResponse
from app.services.factura_service import FacturaService
from app.services.pago_service import PagoService

LECTURA = require_roles(
    RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.DOCTOR, RolUsuario.ASISTENTE
)
ESCRITURA = require_roles(RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.ASISTENTE)

router = APIRouter(prefix="/facturas", tags=["facturas"])

NO_ENCONTRADO = "Factura no encontrada"

_A_409 = (FacturaAnuladaError, FacturaConPagosError)
_A_422 = (PagoExcedeSaldoError,)


def _traducir(error: Exception) -> HTTPException:
    if isinstance(error, _A_409):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error))


def _id_asistente_actual(usuario: Usuario, db: Session) -> int | None:
    # id_asistente sale del token, nunca del body: es un dato de auditoria y el
    # cliente no debe poder mentir sobre quien emitio/cobro. Mismo patron que
    # id_asistente en POST /citas (Modulo 4).
    if usuario.rol != RolUsuario.ASISTENTE:
        return None
    perfil = AsistenteRepository(db).obtener_por_usuario(usuario.id_usuario)
    return perfil.id_asistente if perfil else None


@router.get("", response_model=list[FacturaResponse], dependencies=[Depends(LECTURA)])
def listar_facturas(
    id_paciente: int | None = None,
    id_clinica: int = Depends(resolve_clinica_id),
    usuario: Usuario = Depends(get_current_user),
    doctor_actual: Doctor | None = Depends(get_doctor_actual),
    db: Session = Depends(get_db),
) -> list[FacturaResponse]:
    id_doctor = None
    if usuario.rol == RolUsuario.DOCTOR:
        if doctor_actual is None:
            return []
        id_doctor = doctor_actual.id_doctor

    registros = FacturaRepository(db).listar(id_clinica, id_paciente=id_paciente, id_doctor=id_doctor)
    return [FacturaResponse.model_validate(f) for f in registros]


@router.get("/{id_factura}", response_model=FacturaResponse, dependencies=[Depends(LECTURA)])
def obtener_factura(
    id_factura: int,
    id_clinica: int = Depends(resolve_clinica_id),
    usuario: Usuario = Depends(get_current_user),
    doctor_actual: Doctor | None = Depends(get_doctor_actual),
    db: Session = Depends(get_db),
) -> FacturaResponse:
    factura = FacturaRepository(db).obtener(id_clinica, id_factura)
    if factura is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    if usuario.rol == RolUsuario.DOCTOR:
        if doctor_actual is None or factura.id_doctor != doctor_actual.id_doctor:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    return FacturaResponse.model_validate(factura)


@router.post(
    "", response_model=FacturaResponse, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(ESCRITURA)],
)
def crear_factura_suelta(
    body: FacturaCreate,
    id_clinica: int = Depends(resolve_clinica_id),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FacturaResponse:
    id_asistente = _id_asistente_actual(usuario, db)
    factura = FacturaService(db).crear_suelta(
        id_clinica,
        body.id_paciente,
        body.id_doctor,
        [linea.model_dump() for linea in body.lineas],
        id_asistente,
    )
    return FacturaResponse.model_validate(factura)


@router.patch(
    "/{id_factura}/anular", response_model=FacturaResponse, dependencies=[Depends(ESCRITURA)]
)
def anular_factura(
    id_factura: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> FacturaResponse:
    try:
        factura = FacturaService(db).anular(id_clinica, id_factura)
    except _A_409 as error:
        raise _traducir(error)
    if factura is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    return FacturaResponse.model_validate(factura)


@router.get(
    "/{id_factura}/pagos", response_model=list[PagoResponse], dependencies=[Depends(LECTURA)]
)
def listar_pagos(
    id_factura: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> list[PagoResponse]:
    if FacturaRepository(db).obtener(id_clinica, id_factura) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    registros = PagoRepository(db).listar_de_factura(id_clinica, id_factura)
    return [PagoResponse.model_validate(p) for p in registros]


@router.post(
    "/{id_factura}/pagos", response_model=PagoResponse, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(ESCRITURA)],
)
def registrar_pago(
    id_factura: int,
    body: PagoCreate,
    id_clinica: int = Depends(resolve_clinica_id),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PagoResponse:
    id_asistente = _id_asistente_actual(usuario, db)
    try:
        pago = PagoService(db).registrar_pago(
            id_clinica, id_factura, body.monto, body.id_metodo_pago, id_asistente
        )
    except (*_A_409, *_A_422) as error:
        raise _traducir(error)
    if pago is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    return PagoResponse.model_validate(pago)
