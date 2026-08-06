from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.exceptions import (
    FacturaConPagosError,
    PresupuestoNoAceptadoError,
    ReferenciaInvalidaError,
)
from app.models import EstadoDetallePlanTratamiento, EstadoFactura, EstadoPresupuesto, Factura
from app.repositories.configuracion_repository import ConfiguracionClinicaRepository
from app.repositories.factura_detalle_repository import FacturaDetalleRepository
from app.repositories.factura_repository import FacturaRepository
from app.repositories.pago_repository import PagoRepository
from app.repositories.plan_tratamiento_repository import (
    PlanTratamientoDetalleRepository,
    PlanTratamientoRepository,
)
from app.repositories.presupuesto_repository import PresupuestoRepository
from app.repositories.tratamiento_repository import TratamientoRepository


class FacturaService:
    def __init__(self, db: Session):
        self.db = db
        self.facturas = FacturaRepository(db)
        self.detalles = FacturaDetalleRepository(db)
        self.pagos = PagoRepository(db)
        self.configuracion = ConfiguracionClinicaRepository(db)

    def _emitir(
        self,
        id_clinica: int,
        id_paciente: int,
        id_doctor: int | None,
        id_asistente: int | None,
        id_plan: int | None,
        lineas: list[dict],
    ) -> Factura:
        config = self.configuracion.obtener_o_crear(id_clinica)

        subtotal = Decimal("0.00")
        for linea in lineas:
            subtotal += Decimal(str(linea["precio_unitario"])) * linea["cantidad"]
        porcentaje = Decimal(str(config.porcentaje_impuesto))
        impuesto = (subtotal * porcentaje / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        total = subtotal + impuesto

        numero_factura = f"{config.prefijo_factura}{config.proximo_numero_factura:06d}"

        try:
            self.configuracion.actualizar(
                id_clinica, {"proximo_numero_factura": config.proximo_numero_factura + 1}
            )
            factura = self.facturas.crear(
                id_clinica,
                {
                    "id_paciente": id_paciente,
                    "id_doctor": id_doctor,
                    "id_asistente": id_asistente,
                    "id_plan": id_plan,
                    "numero_factura": numero_factura,
                    "monto_subtotal": str(subtotal),
                    "monto_impuesto": str(impuesto),
                    "monto_total": str(total),
                },
            )
            for linea in lineas:
                self.detalles.crear(
                    factura.id_factura,
                    {
                        "id_tratamiento": linea["id_tratamiento"],
                        "cantidad": linea["cantidad"],
                        "precio_unitario": str(linea["precio_unitario"]),
                    },
                )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return factura

    def generar_desde_presupuesto(
        self, id_clinica: int, id_plan: int, id_asistente: int | None = None
    ) -> Factura | None:
        plan = PlanTratamientoRepository(self.db).obtener(id_clinica, id_plan)
        if plan is None:
            return None

        presupuesto = PresupuestoRepository(self.db).obtener_por_plan(id_clinica, id_plan)
        if presupuesto is None or presupuesto.estado != EstadoPresupuesto.ACEPTADO:
            raise PresupuestoNoAceptadoError(
                "El presupuesto de este plan todavia no fue aceptado por el paciente"
            )

        detalles_plan = PlanTratamientoDetalleRepository(self.db).listar_de_plan(id_clinica, id_plan)
        lineas = [
            {
                "id_tratamiento": d.id_tratamiento,
                "cantidad": d.cantidad,
                "precio_unitario": d.precio_unitario,
            }
            for d in detalles_plan
            if d.estado != EstadoDetallePlanTratamiento.CANCELADO
        ]

        return self._emitir(
            id_clinica, plan.id_paciente, plan.id_doctor, id_asistente, id_plan, lineas
        )

    def crear_suelta(
        self,
        id_clinica: int,
        id_paciente: int,
        id_doctor: int | None,
        lineas: list[dict],
        id_asistente: int | None = None,
    ) -> Factura:
        tratamientos = TratamientoRepository(self.db)
        lineas_con_precio = []
        for linea in lineas:
            tratamiento = tratamientos.obtener(id_clinica, linea["id_tratamiento"])
            if tratamiento is None:
                raise ReferenciaInvalidaError(
                    f"El tratamiento {linea['id_tratamiento']} no existe en esta clinica"
                )
            lineas_con_precio.append(
                {
                    "id_tratamiento": tratamiento.id_tratamiento,
                    "cantidad": linea["cantidad"],
                    "precio_unitario": tratamiento.precio,
                }
            )

        return self._emitir(
            id_clinica, id_paciente, id_doctor, id_asistente, None, lineas_con_precio
        )

    def anular(self, id_clinica: int, id_factura: int) -> Factura | None:
        factura = self.facturas.obtener(id_clinica, id_factura)
        if factura is None:
            return None
        if self.pagos.suma_pagada(id_clinica, id_factura) > Decimal("0.00"):
            raise FacturaConPagosError(
                "No se puede anular: esta factura ya tiene pagos registrados"
            )
        factura.estado = EstadoFactura.ANULADA
        self.db.commit()
        return factura
