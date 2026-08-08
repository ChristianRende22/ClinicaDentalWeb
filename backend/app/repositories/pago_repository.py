from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import func, select, text

from app.models import Factura, MetodoPago, Pago

AGRUPACIONES_VALIDAS = ("dia", "semana", "mes")


class PagoRepository:
    """No hereda BaseRepository, mismo criterio que FacturaDetalleRepository:
    aislamiento por JOIN contra Factura.
    """

    def __init__(self, db):
        self.db = db

    def listar_de_factura(self, id_clinica: int, id_factura: int) -> list[Pago]:
        stmt = (
            select(Pago)
            .join(Factura, Pago.id_factura == Factura.id_factura)
            .where(Factura.id_clinica == id_clinica, Pago.id_factura == id_factura)
            .order_by(Pago.fecha_pago)
        )
        return list(self.db.execute(stmt).scalars().all())

    def crear(self, id_factura: int, data: dict) -> Pago:
        pago = Pago(id_factura=id_factura, **data)
        self.db.add(pago)
        self.db.flush()
        return pago

    def suma_pagada(self, id_clinica: int, id_factura: int) -> Decimal:
        total = Decimal("0.00")
        for pago in self.listar_de_factura(id_clinica, id_factura):
            total += Decimal(str(pago.monto))
        return total

    def _expr_periodo(self, agrupar_por: str):
        """Trunca Pago.fecha_pago al periodo pedido, en SQL.

        Rama por dialecto (sqlite en tests, mysql en produccion) porque las
        funciones de fecha no son portables entre los dos motores -- mismo
        riesgo que documenta CitaRepository._solapadas, pero aca se acepta a
        proposito por eficiencia (ver seccion 2.4 del spec del Modulo 7). La
        verificacion Docker/MySQL antes de cerrar el modulo prueba
        explicitamente 'semana' y 'mes' contra MySQL real.

        'semana' usa la fecha del lunes que inicia esa semana como clave, no
        "anio-numero_de_semana": una clave 'anio-numero_de_semana' mezcla
        pagos de anios distintos en el limite de anio, porque %W (sqlite) y
        %u (mysql) numeran las semanas cerca del limite de forma distinta y
        ninguna de las dos coincide de forma segura con %Y (anio calendario).
        La fecha del lunes es inequivoca en los dos dialectos.
        """
        dialecto = self.db.bind.dialect.name
        columna = Pago.fecha_pago
        if agrupar_por == "dia":
            if dialecto == "sqlite":
                return func.strftime("%Y-%m-%d", columna)
            return func.date_format(columna, "%Y-%m-%d")
        if agrupar_por == "semana":
            if dialecto == "sqlite":
                return func.date(columna, "weekday 0", "-6 days")
            return func.date_sub(func.date(columna), text("INTERVAL WEEKDAY(fecha_pago) DAY"))
        if agrupar_por == "mes":
            if dialecto == "sqlite":
                return func.strftime("%Y-%m", columna)
            return func.date_format(columna, "%Y-%m")
        raise ValueError(
            f"agrupar_por invalido: {agrupar_por!r}, debe ser uno de {AGRUPACIONES_VALIDAS}"
        )

    def totales_por_periodo(
        self,
        id_clinica: int,
        desde: date | None = None,
        hasta: date | None = None,
        agrupar_por: str = "dia",
    ) -> dict:
        if agrupar_por not in AGRUPACIONES_VALIDAS:
            raise ValueError(
                f"agrupar_por invalido: {agrupar_por!r}, debe ser uno de {AGRUPACIONES_VALIDAS}"
            )

        filtros = [Factura.id_clinica == id_clinica]
        if desde is not None:
            filtros.append(Pago.fecha_pago >= datetime.combine(desde, time.min))
        if hasta is not None:
            filtros.append(Pago.fecha_pago <= datetime.combine(hasta, time.max))

        total = self.db.execute(
            select(func.coalesce(func.sum(Pago.monto), 0))
            .select_from(Pago)
            .join(Factura, Pago.id_factura == Factura.id_factura)
            .where(*filtros)
        ).scalar()

        stmt_metodo = (
            select(MetodoPago.id_metodo_pago, MetodoPago.nombre, func.sum(Pago.monto))
            .select_from(Pago)
            .join(Factura, Pago.id_factura == Factura.id_factura)
            .join(MetodoPago, Pago.id_metodo_pago == MetodoPago.id_metodo_pago)
            .where(*filtros)
            .group_by(MetodoPago.id_metodo_pago, MetodoPago.nombre)
        )
        por_metodo_pago = [
            {"id_metodo_pago": id_, "nombre": nombre, "monto": Decimal(str(monto))}
            for id_, nombre, monto in self.db.execute(stmt_metodo).all()
        ]

        periodo_expr = self._expr_periodo(agrupar_por)
        stmt_serie = (
            select(periodo_expr, func.sum(Pago.monto))
            .select_from(Pago)
            .join(Factura, Pago.id_factura == Factura.id_factura)
            .where(*filtros)
            .group_by(periodo_expr)
            .order_by(periodo_expr)
        )
        serie = [
            {"periodo": str(periodo), "monto": Decimal(str(monto))}
            for periodo, monto in self.db.execute(stmt_serie).all()
        ]

        return {
            "total": Decimal(str(total)) if total is not None else Decimal("0.00"),
            "por_metodo_pago": por_metodo_pago,
            "serie": serie,
        }
