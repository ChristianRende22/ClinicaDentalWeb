from datetime import date, datetime
from decimal import Decimal

import pytest

from tests.factories import crear_clinica, crear_cita, crear_doctor, crear_paciente, crear_metodo_pago


def test_resumen_por_estado_cuenta_por_estado_y_total(db_session):
    from app.repositories.cita_repository import CitaRepository

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    crear_cita(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor,
        fecha_hora=datetime(2026, 8, 5, 9, 0), estado="programada",
    )
    crear_cita(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor,
        fecha_hora=datetime(2026, 8, 6, 9, 0), estado="completada",
    )
    crear_cita(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor,
        fecha_hora=datetime(2026, 8, 7, 9, 0), estado="completada",
    )
    db_session.commit()

    resumen = CitaRepository(db_session).resumen_por_estado(clinica.id_clinica)

    assert resumen["total"] == 3
    assert resumen["por_estado"]["programada"] == 1
    assert resumen["por_estado"]["completada"] == 2
    assert resumen["por_estado"]["cancelada"] == 0


def test_resumen_por_estado_filtra_por_rango_de_fechas(db_session):
    from app.repositories.cita_repository import CitaRepository

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    crear_cita(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor,
        fecha_hora=datetime(2026, 7, 1, 9, 0), estado="completada",
    )
    crear_cita(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor,
        fecha_hora=datetime(2026, 8, 5, 9, 0), estado="completada",
    )
    db_session.commit()

    resumen = CitaRepository(db_session).resumen_por_estado(
        clinica.id_clinica, desde=datetime(2026, 8, 1), hasta=datetime(2026, 8, 31, 23, 59, 59),
    )

    assert resumen["total"] == 1


def test_resumen_por_estado_desglosa_por_doctor(db_session):
    from app.repositories.cita_repository import CitaRepository

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doc_a = crear_doctor(db_session, clinica.id_clinica, username="doc.a", nombre="Marta", apellido="Perez")
    doc_b = crear_doctor(db_session, clinica.id_clinica, username="doc.b", nombre="Luis", apellido="Gomez")
    crear_cita(
        db_session, clinica.id_clinica, paciente.id_paciente, doc_a.id_doctor,
        fecha_hora=datetime(2026, 8, 5, 9, 0), estado="completada",
    )
    crear_cita(
        db_session, clinica.id_clinica, paciente.id_paciente, doc_b.id_doctor,
        fecha_hora=datetime(2026, 8, 6, 9, 0), estado="programada",
    )
    db_session.commit()

    resumen = CitaRepository(db_session).resumen_por_estado(clinica.id_clinica)

    por_doctor = {fila["id_doctor"]: fila for fila in resumen["por_doctor"]}
    assert por_doctor[doc_a.id_doctor]["nombre"] == "Marta Perez"
    assert por_doctor[doc_a.id_doctor]["total"] == 1
    assert por_doctor[doc_a.id_doctor]["por_estado"]["completada"] == 1
    assert por_doctor[doc_b.id_doctor]["por_estado"]["programada"] == 1


def test_resumen_por_estado_sin_incluir_por_doctor(db_session):
    from app.repositories.cita_repository import CitaRepository

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    crear_cita(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor,
        fecha_hora=datetime(2026, 8, 5, 9, 0), estado="completada",
    )
    db_session.commit()

    resumen = CitaRepository(db_session).resumen_por_estado(
        clinica.id_clinica, incluir_por_doctor=False,
    )

    assert resumen["por_doctor"] == []


def test_resumen_por_estado_filtra_por_id_doctor(db_session):
    from app.repositories.cita_repository import CitaRepository

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doc_a = crear_doctor(db_session, clinica.id_clinica, username="doc.a")
    doc_b = crear_doctor(db_session, clinica.id_clinica, username="doc.b")
    crear_cita(
        db_session, clinica.id_clinica, paciente.id_paciente, doc_a.id_doctor,
        fecha_hora=datetime(2026, 8, 5, 9, 0), estado="completada",
    )
    crear_cita(
        db_session, clinica.id_clinica, paciente.id_paciente, doc_b.id_doctor,
        fecha_hora=datetime(2026, 8, 6, 9, 0), estado="completada",
    )
    db_session.commit()

    resumen = CitaRepository(db_session).resumen_por_estado(
        clinica.id_clinica, id_doctor=doc_a.id_doctor,
    )

    assert resumen["total"] == 1


def test_resumen_por_estado_no_mezcla_clinicas(db_session):
    from app.repositories.cita_repository import CitaRepository

    clinica_a = crear_clinica(db_session, nombre="Dental A")
    clinica_b = crear_clinica(db_session, nombre="Dental B")
    paciente_a = crear_paciente(db_session, clinica_a.id_clinica)
    doctor_a = crear_doctor(db_session, clinica_a.id_clinica, username="doc.a")
    paciente_b = crear_paciente(db_session, clinica_b.id_clinica)
    doctor_b = crear_doctor(db_session, clinica_b.id_clinica, username="doc.b")
    crear_cita(
        db_session, clinica_a.id_clinica, paciente_a.id_paciente, doctor_a.id_doctor,
        fecha_hora=datetime(2026, 8, 5, 9, 0), estado="completada",
    )
    crear_cita(
        db_session, clinica_b.id_clinica, paciente_b.id_paciente, doctor_b.id_doctor,
        fecha_hora=datetime(2026, 8, 5, 9, 0), estado="completada",
    )
    db_session.commit()

    resumen = CitaRepository(db_session).resumen_por_estado(clinica_a.id_clinica)

    assert resumen["total"] == 1


def _crear_factura_con_pago(db, id_clinica, id_paciente, id_metodo_pago, monto, fecha_pago, numero="F000001"):
    from app.models import Factura, Pago

    factura = Factura(
        id_clinica=id_clinica, id_paciente=id_paciente, numero_factura=numero,
        monto_subtotal=monto, monto_impuesto="0.00", monto_total=monto,
    )
    db.add(factura)
    db.flush()
    pago = Pago(
        id_factura=factura.id_factura, id_metodo_pago=id_metodo_pago, monto=monto,
        fecha_pago=fecha_pago,
    )
    db.add(pago)
    db.flush()
    return factura, pago


def test_totales_por_periodo_suma_el_total(db_session):
    from app.repositories.pago_repository import PagoRepository

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    metodo = crear_metodo_pago(db_session, clinica.id_clinica)
    _crear_factura_con_pago(
        db_session, clinica.id_clinica, paciente.id_paciente, metodo.id_metodo_pago,
        "50.00", datetime(2026, 8, 5, 10, 0), numero="F000001",
    )
    _crear_factura_con_pago(
        db_session, clinica.id_clinica, paciente.id_paciente, metodo.id_metodo_pago,
        "30.00", datetime(2026, 8, 6, 10, 0), numero="F000002",
    )
    db_session.commit()

    resultado = PagoRepository(db_session).totales_por_periodo(
        clinica.id_clinica, desde=date(2026, 8, 1), hasta=date(2026, 8, 31),
    )

    assert resultado["total"] == Decimal("80.00")


def test_totales_por_periodo_sin_pagos_es_cero(db_session):
    from app.repositories.pago_repository import PagoRepository

    clinica = crear_clinica(db_session)
    db_session.commit()

    resultado = PagoRepository(db_session).totales_por_periodo(clinica.id_clinica)

    assert resultado["total"] == Decimal("0.00")
    assert resultado["por_metodo_pago"] == []
    assert resultado["serie"] == []


def test_totales_por_periodo_desglosa_por_metodo_de_pago(db_session):
    from app.repositories.pago_repository import PagoRepository

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    efectivo = crear_metodo_pago(db_session, clinica.id_clinica, nombre="Efectivo")
    tarjeta = crear_metodo_pago(db_session, clinica.id_clinica, nombre="Tarjeta")
    _crear_factura_con_pago(
        db_session, clinica.id_clinica, paciente.id_paciente, efectivo.id_metodo_pago,
        "50.00", datetime(2026, 8, 5, 10, 0), numero="F000001",
    )
    _crear_factura_con_pago(
        db_session, clinica.id_clinica, paciente.id_paciente, tarjeta.id_metodo_pago,
        "30.00", datetime(2026, 8, 6, 10, 0), numero="F000002",
    )
    db_session.commit()

    resultado = PagoRepository(db_session).totales_por_periodo(clinica.id_clinica)

    por_metodo = {fila["id_metodo_pago"]: fila["monto"] for fila in resultado["por_metodo_pago"]}
    assert por_metodo[efectivo.id_metodo_pago] == Decimal("50.00")
    assert por_metodo[tarjeta.id_metodo_pago] == Decimal("30.00")


def test_totales_por_periodo_filtra_por_rango(db_session):
    from app.repositories.pago_repository import PagoRepository

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    metodo = crear_metodo_pago(db_session, clinica.id_clinica)
    _crear_factura_con_pago(
        db_session, clinica.id_clinica, paciente.id_paciente, metodo.id_metodo_pago,
        "50.00", datetime(2026, 7, 5, 10, 0), numero="F000001",
    )
    _crear_factura_con_pago(
        db_session, clinica.id_clinica, paciente.id_paciente, metodo.id_metodo_pago,
        "30.00", datetime(2026, 8, 5, 10, 0), numero="F000002",
    )
    db_session.commit()

    resultado = PagoRepository(db_session).totales_por_periodo(
        clinica.id_clinica, desde=date(2026, 8, 1), hasta=date(2026, 8, 31),
    )

    assert resultado["total"] == Decimal("30.00")


def test_totales_por_periodo_serie_agrupada_por_dia(db_session):
    from app.repositories.pago_repository import PagoRepository

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    metodo = crear_metodo_pago(db_session, clinica.id_clinica)
    _crear_factura_con_pago(
        db_session, clinica.id_clinica, paciente.id_paciente, metodo.id_metodo_pago,
        "20.00", datetime(2026, 8, 5, 9, 0), numero="F000001",
    )
    _crear_factura_con_pago(
        db_session, clinica.id_clinica, paciente.id_paciente, metodo.id_metodo_pago,
        "15.00", datetime(2026, 8, 5, 17, 0), numero="F000002",
    )
    _crear_factura_con_pago(
        db_session, clinica.id_clinica, paciente.id_paciente, metodo.id_metodo_pago,
        "10.00", datetime(2026, 8, 6, 9, 0), numero="F000003",
    )
    db_session.commit()

    resultado = PagoRepository(db_session).totales_por_periodo(
        clinica.id_clinica, agrupar_por="dia",
    )

    serie = {fila["periodo"]: fila["monto"] for fila in resultado["serie"]}
    assert len(serie) == 2
    assert sum(serie.values()) == Decimal("45.00")


def test_totales_por_periodo_agrupar_por_invalido_lanza_value_error(db_session):
    from app.repositories.pago_repository import PagoRepository

    clinica = crear_clinica(db_session)
    db_session.commit()

    with pytest.raises(ValueError):
        PagoRepository(db_session).totales_por_periodo(clinica.id_clinica, agrupar_por="anio")


def test_totales_por_periodo_no_mezcla_clinicas(db_session):
    from app.repositories.pago_repository import PagoRepository

    clinica_a = crear_clinica(db_session, nombre="Dental A")
    clinica_b = crear_clinica(db_session, nombre="Dental B")
    paciente_a = crear_paciente(db_session, clinica_a.id_clinica)
    paciente_b = crear_paciente(db_session, clinica_b.id_clinica)
    metodo_a = crear_metodo_pago(db_session, clinica_a.id_clinica)
    metodo_b = crear_metodo_pago(db_session, clinica_b.id_clinica)
    _crear_factura_con_pago(
        db_session, clinica_a.id_clinica, paciente_a.id_paciente, metodo_a.id_metodo_pago,
        "50.00", datetime(2026, 8, 5, 10, 0), numero="F000001",
    )
    _crear_factura_con_pago(
        db_session, clinica_b.id_clinica, paciente_b.id_paciente, metodo_b.id_metodo_pago,
        "999.00", datetime(2026, 8, 5, 10, 0), numero="F000001",
    )
    db_session.commit()

    resultado = PagoRepository(db_session).totales_por_periodo(clinica_a.id_clinica)

    assert resultado["total"] == Decimal("50.00")


def test_listar_pendientes_incluye_pendiente_y_parcial(db_session):
    from app.repositories.factura_repository import FacturaRepository
    from app.repositories.pago_repository import PagoRepository

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    metodo = crear_metodo_pago(db_session, clinica.id_clinica)
    repo_factura = FacturaRepository(db_session)
    f_pendiente = repo_factura.crear(
        clinica.id_clinica,
        {"id_paciente": paciente.id_paciente, "numero_factura": "F000001",
         "monto_subtotal": "100.00", "monto_impuesto": "0.00", "monto_total": "100.00"},
    )
    f_parcial = repo_factura.crear(
        clinica.id_clinica,
        {"id_paciente": paciente.id_paciente, "numero_factura": "F000002",
         "monto_subtotal": "50.00", "monto_impuesto": "0.00", "monto_total": "50.00"},
    )
    f_pagada = repo_factura.crear(
        clinica.id_clinica,
        {"id_paciente": paciente.id_paciente, "numero_factura": "F000003",
         "monto_subtotal": "20.00", "monto_impuesto": "0.00", "monto_total": "20.00"},
    )
    db_session.flush()
    from app.models import EstadoFactura

    PagoRepository(db_session).crear(
        f_parcial.id_factura, {"id_metodo_pago": metodo.id_metodo_pago, "monto": "20.00"}
    )
    f_parcial.estado = EstadoFactura.PARCIAL
    PagoRepository(db_session).crear(
        f_pagada.id_factura, {"id_metodo_pago": metodo.id_metodo_pago, "monto": "20.00"}
    )
    f_pagada.estado = EstadoFactura.PAGADA
    db_session.commit()

    resultado = FacturaRepository(db_session).listar_pendientes(clinica.id_clinica)

    ids = {f["id_factura"] for f in resultado["facturas"]}
    assert ids == {f_pendiente.id_factura, f_parcial.id_factura}
    assert resultado["resumen"]["cantidad"] == 2


def test_listar_pendientes_calcula_saldo_pendiente(db_session):
    from app.repositories.factura_repository import FacturaRepository
    from app.repositories.pago_repository import PagoRepository

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica, nombre="Juan", apellido="Perez")
    metodo = crear_metodo_pago(db_session, clinica.id_clinica)
    repo_factura = FacturaRepository(db_session)
    factura = repo_factura.crear(
        clinica.id_clinica,
        {"id_paciente": paciente.id_paciente, "numero_factura": "F000001",
         "monto_subtotal": "100.00", "monto_impuesto": "0.00", "monto_total": "100.00"},
    )
    db_session.flush()
    PagoRepository(db_session).crear(
        factura.id_factura, {"id_metodo_pago": metodo.id_metodo_pago, "monto": "30.00"}
    )
    from app.models import EstadoFactura

    factura.estado = EstadoFactura.PARCIAL
    db_session.commit()

    resultado = FacturaRepository(db_session).listar_pendientes(clinica.id_clinica)

    fila = resultado["facturas"][0]
    assert fila["monto_pagado"] == Decimal("30.00")
    assert fila["saldo_pendiente"] == Decimal("70.00")
    assert fila["paciente"] == "Juan Perez"
    assert resultado["resumen"]["monto_pendiente_total"] == Decimal("70.00")


def test_listar_pendientes_sin_pagos(db_session):
    from app.repositories.factura_repository import FacturaRepository

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    FacturaRepository(db_session).crear(
        clinica.id_clinica,
        {"id_paciente": paciente.id_paciente, "numero_factura": "F000001",
         "monto_subtotal": "40.00", "monto_impuesto": "0.00", "monto_total": "40.00"},
    )
    db_session.commit()

    resultado = FacturaRepository(db_session).listar_pendientes(clinica.id_clinica)

    fila = resultado["facturas"][0]
    assert fila["monto_pagado"] == Decimal("0.00")
    assert fila["saldo_pendiente"] == Decimal("40.00")


def test_listar_pendientes_filtra_por_fecha_emision(db_session):
    from app.repositories.factura_repository import FacturaRepository

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    repo = FacturaRepository(db_session)
    vieja = repo.crear(
        clinica.id_clinica,
        {"id_paciente": paciente.id_paciente, "numero_factura": "F000001",
         "monto_subtotal": "10.00", "monto_impuesto": "0.00", "monto_total": "10.00"},
    )
    vieja.fecha_emision = datetime(2026, 1, 1)
    nueva = repo.crear(
        clinica.id_clinica,
        {"id_paciente": paciente.id_paciente, "numero_factura": "F000002",
         "monto_subtotal": "10.00", "monto_impuesto": "0.00", "monto_total": "10.00"},
    )
    nueva.fecha_emision = datetime(2026, 8, 5)
    db_session.commit()

    resultado = FacturaRepository(db_session).listar_pendientes(
        clinica.id_clinica, desde=date(2026, 8, 1), hasta=date(2026, 8, 31),
    )

    ids = {f["id_factura"] for f in resultado["facturas"]}
    assert ids == {nueva.id_factura}


def test_listar_pendientes_no_mezcla_clinicas(db_session):
    from app.repositories.factura_repository import FacturaRepository

    clinica_a = crear_clinica(db_session, nombre="Dental A")
    clinica_b = crear_clinica(db_session, nombre="Dental B")
    paciente_a = crear_paciente(db_session, clinica_a.id_clinica)
    paciente_b = crear_paciente(db_session, clinica_b.id_clinica)
    FacturaRepository(db_session).crear(
        clinica_a.id_clinica,
        {"id_paciente": paciente_a.id_paciente, "numero_factura": "F000001",
         "monto_subtotal": "10.00", "monto_impuesto": "0.00", "monto_total": "10.00"},
    )
    FacturaRepository(db_session).crear(
        clinica_b.id_clinica,
        {"id_paciente": paciente_b.id_paciente, "numero_factura": "F000001",
         "monto_subtotal": "999.00", "monto_impuesto": "0.00", "monto_total": "999.00"},
    )
    db_session.commit()

    resultado = FacturaRepository(db_session).listar_pendientes(clinica_a.id_clinica)

    assert resultado["resumen"]["cantidad"] == 1
    assert resultado["facturas"][0]["monto_total"] == Decimal("10.00")
