from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class ResumenPorDoctor(BaseModel):
    id_doctor: int
    nombre: str
    total: int
    por_estado: dict[str, int]


class ResumenCitasResponse(BaseModel):
    desde: date
    hasta: date
    total: int
    por_estado: dict[str, int]
    por_doctor: list[ResumenPorDoctor]


class TotalPorMetodoPago(BaseModel):
    id_metodo_pago: int
    nombre: str
    monto: Decimal


class PuntoSerie(BaseModel):
    periodo: str
    monto: Decimal


class ResumenIngresosResponse(BaseModel):
    desde: date
    hasta: date
    agrupar_por: Literal["dia", "semana", "mes"]
    total: Decimal
    por_metodo_pago: list[TotalPorMetodoPago]
    serie: list[PuntoSerie]


class FacturaPendienteItem(BaseModel):
    id_factura: int
    numero_factura: str
    id_paciente: int
    paciente: str
    estado: str
    monto_total: Decimal
    monto_pagado: Decimal
    saldo_pendiente: Decimal
    fecha_emision: datetime


class ResumenFacturasPendientes(BaseModel):
    cantidad: int
    monto_pendiente_total: Decimal


class FacturasPendientesResponse(BaseModel):
    resumen: ResumenFacturasPendientes
    facturas: list[FacturaPendienteItem]
