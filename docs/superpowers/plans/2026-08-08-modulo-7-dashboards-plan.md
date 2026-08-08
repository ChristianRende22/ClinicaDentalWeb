# Módulo 7 — Dashboards y Métricas — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tres endpoints de solo lectura (`GET /dashboard/citas/resumen`, `GET /dashboard/ingresos`,
`GET /dashboard/facturas-pendientes`) que agregan datos ya existentes de `Cita`, `Factura` y `Pago`
para dar métricas operativas y financieras por clínica.

**Architecture:** Sin modelos, migraciones ni servicios nuevos. Se agregan métodos de agregación a
`CitaRepository`, `FacturaRepository` y `PagoRepository` (todos ya existen desde los Módulos 4 y 6),
más un router nuevo `app/api/routes/dashboards.py` que los llama directo — sin `DashboardService`,
porque son lecturas puras sin coordinar una transacción.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 (agregación con `func.count`/`func.sum`/`GROUP BY`),
Pydantic v2, pytest + SQLite en memoria para tests, verificación final contra MySQL en Docker.

## Global Constraints

- **TDD siempre:** test primero (falla por la razón correcta), después la implementación mínima.
- **Nombres en español** para todo lo de negocio; inglés solo para nombres de clases/patrones
  técnicos genéricos.
- **Repositorios hacen `.flush()`, nunca `.commit()`.** No aplica de lleno acá (son solo lecturas,
  sin escritura), pero ningún método nuevo debe llamar `.commit()`.
- **Excepciones de dominio en `app/exceptions.py`, nunca `HTTPException` en repositorio o servicio.**
  Este módulo no agrega excepciones nuevas — no hay casos de error de negocio, solo permisos (que
  ya maneja `require_roles`) y validación de query params (que ya maneja Pydantic/FastAPI).
- **Todo enum nuevo lleva `values_callable`.** No aplica: este módulo no agrega enums.
- **Aislamiento por clínica:** todo método nuevo recibe `id_clinica` como primer parámetro
  obligatorio, sin default — mismo criterio que `BaseRepository`, aunque estos métodos no heredan
  de esa clase (son agregaciones, no CRUD de una sola entidad).
- **Agrupación por semana/mes en SQL con rama por dialecto** (`db.bind.dialect.name`), no en
  Python — decisión explícita de la sección 2.4 del spec, con verificación Docker/MySQL obligatoria
  para `agrupar_por=semana` y `agrupar_por=mes` antes de cerrar el módulo.
- **Verificación contra Docker/MySQL real es obligatoria** antes de dar el módulo por terminado
  (ver Tarea 8).

---

## Contexto de archivos existentes que este plan reutiliza sin modificar

- `app/models/cita.py` — `Cita` (`id_cita`, `id_clinica`, `id_doctor`, `fecha_hora`, `estado`),
  `EstadoCita` (enum: `programada`, `confirmada`, `completada`, `cancelada`, `no_asistio`).
- `app/models/factura.py` — `Factura` (`id_factura`, `id_clinica`, `id_paciente`, `numero_factura`,
  `monto_total`, `estado`, `fecha_emision`), `EstadoFactura` (enum: `pendiente`, `parcial`,
  `pagada`, `anulada`), `Pago` (`id_pago`, `id_factura`, `id_metodo_pago`, `monto`, `fecha_pago`).
- `app/models/personas.py` — `Doctor` (`id_doctor`, `nombre`, `apellido`), `Paciente` (`id_paciente`,
  `nombre`, `apellido`).
- `app/models/parametros.py` — `MetodoPago` (`id_metodo_pago`, `id_clinica`, `nombre`).
- `app/api/deps.py` — `get_current_user`, `require_roles(*roles)`, `resolve_clinica_id`,
  `get_doctor_actual` (devuelve `Doctor | None`, `None` tanto si no es doctor como si es doctor sin
  perfil — la ausencia debe cerrar, no abrir).
- `tests/factories.py` — `crear_clinica(db, nombre=...)`, `crear_usuario(db, rol, id_clinica=None,
  username=...)`, `crear_doctor(db, id_clinica, username=..., **campos)`, `crear_asistente(db,
  id_clinica, username=..., **campos)`, `crear_paciente(db, id_clinica, **campos)`,
  `crear_cita(db, id_clinica, id_paciente, id_doctor, **campos)`, `crear_metodo_pago(db, id_clinica,
  **campos)`, `token_de(usuario) -> str`, `auth(token) -> dict`, `headers_de(db, id_clinica, rol) ->
  dict` (crea un usuario nuevo con ese rol y devuelve el header `Authorization` ya armado, con
  `X-Clinica-Id` si es superadmin).
- `tests/conftest.py` — fixtures `db_session` (SQLite en memoria, `StaticPool`) y `client`
  (`TestClient` con `get_db` sobreescrito a `db_session`).

---

### Task 1: `CitaRepository.resumen_por_estado`

**Files:**
- Modify: `backend/app/repositories/cita_repository.py`
- Test: `backend/tests/test_dashboard_repositorios.py` (crear)

**Interfaces:**
- Produces: `CitaRepository.resumen_por_estado(id_clinica: int, desde: datetime | None = None,
  hasta: datetime | None = None, id_doctor: int | None = None, incluir_por_doctor: bool = True) ->
  dict` con la forma:
  ```python
  {
      "total": int,
      "por_estado": {"programada": int, "confirmada": int, "completada": int,
                      "cancelada": int, "no_asistio": int},
      "por_doctor": [
          {"id_doctor": int, "nombre": str, "total": int, "por_estado": {...}}
      ],  # [] si incluir_por_doctor=False
  }
  ```
  `por_estado` siempre trae las 5 claves aunque el conteo sea 0. `nombre` en `por_doctor` es
  `f"{doctor.nombre} {doctor.apellido}"`.

- [ ] **Step 1: Write the failing test**

Crear `backend/tests/test_dashboard_repositorios.py`:

```python
from datetime import datetime

from tests.factories import crear_clinica, crear_cita, crear_doctor, crear_paciente


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
```

- [ ] **Step 2: Run test to verify it fails**

Run (desde `backend/`): `.venv/Scripts/python.exe -m pytest tests/test_dashboard_repositorios.py -v`
Expected: FAIL — `AttributeError: 'CitaRepository' object has no attribute 'resumen_por_estado'`

- [ ] **Step 3: Write minimal implementation**

En `backend/app/repositories/cita_repository.py`, agregar el import de `func` de SQLAlchemy y
`Doctor` de `app.models` al tope del archivo:

```python
from sqlalchemy import func, select

from app.models import ESTADOS_ACTIVOS, Cita, Doctor, EstadoCita
```

(reemplaza la línea `from sqlalchemy import select` y la línea
`from app.models import ESTADOS_ACTIVOS, Cita, EstadoCita` ya existentes)

Agregar el método nuevo dentro de la clase `CitaRepository`, después de
`hay_solapamiento_de_consultorio`:

```python
    def resumen_por_estado(
        self,
        id_clinica: int,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        id_doctor: int | None = None,
        incluir_por_doctor: bool = True,
    ) -> dict:
        """Cuenta citas agrupadas por estado (y opcionalmente por doctor) para
        el dashboard del Modulo 7. Mismos filtros que listar(), pero agregados
        en SQL con GROUP BY en vez de traer las filas y contarlas en Python.
        """
        filtros = [Cita.id_clinica == id_clinica]
        if desde is not None:
            filtros.append(Cita.fecha_hora >= desde)
        if hasta is not None:
            filtros.append(Cita.fecha_hora <= hasta)
        if id_doctor is not None:
            filtros.append(Cita.id_doctor == id_doctor)

        stmt_estado = (
            select(Cita.estado, func.count(Cita.id_cita)).where(*filtros).group_by(Cita.estado)
        )
        por_estado = {estado.value: 0 for estado in EstadoCita}
        total = 0
        for estado, conteo in self.db.execute(stmt_estado).all():
            por_estado[estado.value] = conteo
            total += conteo

        por_doctor: list[dict] = []
        if incluir_por_doctor:
            stmt_doctor = (
                select(Cita.id_doctor, Doctor.nombre, Doctor.apellido, Cita.estado, func.count(Cita.id_cita))
                .join(Doctor, Cita.id_doctor == Doctor.id_doctor)
                .where(*filtros)
                .group_by(Cita.id_doctor, Doctor.nombre, Doctor.apellido, Cita.estado)
            )
            acumulado: dict[int, dict] = {}
            for id_doc, nombre, apellido, estado, conteo in self.db.execute(stmt_doctor).all():
                entrada = acumulado.setdefault(
                    id_doc,
                    {
                        "id_doctor": id_doc,
                        "nombre": f"{nombre} {apellido}",
                        "total": 0,
                        "por_estado": {e.value: 0 for e in EstadoCita},
                    },
                )
                entrada["por_estado"][estado.value] = conteo
                entrada["total"] += conteo
            por_doctor = sorted(acumulado.values(), key=lambda d: d["id_doctor"])

        return {"total": total, "por_estado": por_estado, "por_doctor": por_doctor}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_dashboard_repositorios.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/repositories/cita_repository.py backend/tests/test_dashboard_repositorios.py
git commit -m "feat(backend): CitaRepository.resumen_por_estado para dashboard de citas"
```

---

### Task 2: `PagoRepository.totales_por_periodo`

**Files:**
- Modify: `backend/app/repositories/pago_repository.py`
- Test: `backend/tests/test_dashboard_repositorios.py` (agregar casos)

**Interfaces:**
- Consumes: nada de la Task 1.
- Produces: `PagoRepository.totales_por_periodo(id_clinica: int, desde: date | None = None, hasta:
  date | None = None, agrupar_por: str = "dia") -> dict` con la forma:
  ```python
  {
      "total": Decimal,
      "por_metodo_pago": [{"id_metodo_pago": int, "nombre": str, "monto": Decimal}],
      "serie": [{"periodo": str, "monto": Decimal}],
  }
  ```
  Lanza `ValueError` si `agrupar_por` no es `"dia"`, `"semana"` o `"mes"`.

- [ ] **Step 1: Write the failing test**

Agregar a `backend/tests/test_dashboard_repositorios.py`:

```python
from datetime import date
from decimal import Decimal

import pytest

from tests.factories import crear_metodo_pago


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_dashboard_repositorios.py -v`
Expected: los 7 tests nuevos FAIL — `AttributeError: 'PagoRepository' object has no attribute
'totales_por_periodo'`. Los 6 de la Task 1 siguen en PASS.

- [ ] **Step 3: Write minimal implementation**

Reescribir `backend/app/repositories/pago_repository.py` completo:

```python
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import func, select

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
        """
        dialecto = self.db.bind.dialect.name
        columna = Pago.fecha_pago
        formatos_sqlite = {"dia": "%Y-%m-%d", "semana": "%Y-%W", "mes": "%Y-%m"}
        formatos_mysql = {"dia": "%Y-%m-%d", "semana": "%Y-%u", "mes": "%Y-%m"}
        if dialecto == "sqlite":
            return func.strftime(formatos_sqlite[agrupar_por], columna)
        return func.date_format(columna, formatos_mysql[agrupar_por])

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

        base = select(Pago).select_from(Pago).join(Factura, Pago.id_factura == Factura.id_factura).where(*filtros)

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
            {"periodo": periodo, "monto": Decimal(str(monto))}
            for periodo, monto in self.db.execute(stmt_serie).all()
        ]

        return {
            "total": Decimal(str(total)) if total is not None else Decimal("0.00"),
            "por_metodo_pago": por_metodo_pago,
            "serie": serie,
        }
```

(la variable `base` queda sin usar tras simplificar — quitala si el linter se queja; se deja fuera
del snippet final, ver nota abajo)

**Nota:** al escribir el archivo real, omití la variable `base` (no se usa) — cada query arma su
propio `select(...).select_from(Pago).join(...)` explícito, como en el snippet de arriba salvo esa
línea intermedia.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_dashboard_repositorios.py -v`
Expected: PASS (13 tests: 6 de la Task 1 + 7 de esta)

- [ ] **Step 5: Commit**

```bash
git add backend/app/repositories/pago_repository.py backend/tests/test_dashboard_repositorios.py
git commit -m "feat(backend): PagoRepository.totales_por_periodo para dashboard de ingresos"
```

---

### Task 3: `FacturaRepository.listar_pendientes`

**Files:**
- Modify: `backend/app/repositories/factura_repository.py`
- Test: `backend/tests/test_dashboard_repositorios.py` (agregar casos)

**Interfaces:**
- Consumes: nada de las Tasks 1-2.
- Produces: `FacturaRepository.listar_pendientes(id_clinica: int, desde: date | None = None, hasta:
  date | None = None) -> dict` con la forma:
  ```python
  {
      "resumen": {"cantidad": int, "monto_pendiente_total": Decimal},
      "facturas": [
          {
              "id_factura": int, "numero_factura": str, "id_paciente": int, "paciente": str,
              "estado": str, "monto_total": Decimal, "monto_pagado": Decimal,
              "saldo_pendiente": Decimal, "fecha_emision": datetime,
          }
      ],
  }
  ```
  Solo incluye facturas en estado `pendiente` o `parcial`. `paciente` es
  `f"{paciente.nombre} {paciente.apellido}"`.

- [ ] **Step 1: Write the failing test**

Agregar a `backend/tests/test_dashboard_repositorios.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_dashboard_repositorios.py -v`
Expected: los 5 tests nuevos FAIL — `AttributeError: 'FacturaRepository' object has no attribute
'listar_pendientes'`. Los 13 anteriores siguen en PASS.

- [ ] **Step 3: Write minimal implementation**

En `backend/app/repositories/factura_repository.py`, reemplazar el import del tope:

```python
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import func, select

from app.models import EstadoFactura, Factura, Paciente, Pago
from app.repositories.base import BaseRepository
```

Agregar el método nuevo al final de la clase `FacturaRepository`, después de `obtener_por_plan`:

```python
    def listar_pendientes(
        self, id_clinica: int, desde: date | None = None, hasta: date | None = None
    ) -> dict:
        """Facturas en estado pendiente o parcial, con su saldo pendiente
        calculado -- lo que hay que cobrar HOY, sin importar cuando se
        emitieron (ver seccion 2.3 del spec del Modulo 7). desde/hasta filtran
        fecha_emision solo si se pasan.
        """
        subq_pagos = (
            select(Pago.id_factura, func.coalesce(func.sum(Pago.monto), 0).label("monto_pagado"))
            .group_by(Pago.id_factura)
            .subquery()
        )
        stmt = (
            select(Factura, Paciente, func.coalesce(subq_pagos.c.monto_pagado, 0))
            .join(Paciente, Factura.id_paciente == Paciente.id_paciente)
            .outerjoin(subq_pagos, Factura.id_factura == subq_pagos.c.id_factura)
            .where(
                Factura.id_clinica == id_clinica,
                Factura.estado.in_([EstadoFactura.PENDIENTE, EstadoFactura.PARCIAL]),
            )
        )
        if desde is not None:
            stmt = stmt.where(Factura.fecha_emision >= datetime.combine(desde, time.min))
        if hasta is not None:
            stmt = stmt.where(Factura.fecha_emision <= datetime.combine(hasta, time.max))
        stmt = stmt.order_by(Factura.fecha_emision)

        facturas = []
        cantidad = 0
        monto_pendiente_total = Decimal("0.00")
        for factura, paciente, monto_pagado in self.db.execute(stmt).all():
            monto_pagado = Decimal(str(monto_pagado))
            monto_total = Decimal(str(factura.monto_total))
            saldo_pendiente = monto_total - monto_pagado
            facturas.append(
                {
                    "id_factura": factura.id_factura,
                    "numero_factura": factura.numero_factura,
                    "id_paciente": factura.id_paciente,
                    "paciente": f"{paciente.nombre} {paciente.apellido}",
                    "estado": factura.estado.value,
                    "monto_total": monto_total,
                    "monto_pagado": monto_pagado,
                    "saldo_pendiente": saldo_pendiente,
                    "fecha_emision": factura.fecha_emision,
                }
            )
            cantidad += 1
            monto_pendiente_total += saldo_pendiente

        return {
            "resumen": {"cantidad": cantidad, "monto_pendiente_total": monto_pendiente_total},
            "facturas": facturas,
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_dashboard_repositorios.py -v`
Expected: PASS (18 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/repositories/factura_repository.py backend/tests/test_dashboard_repositorios.py
git commit -m "feat(backend): FacturaRepository.listar_pendientes para dashboard de cobros"
```

---

### Task 4: Schemas de respuesta (`app/schemas/dashboard.py`)

**Files:**
- Create: `backend/app/schemas/dashboard.py`
- Test: ninguno directo — los schemas se validan indirectamente en la Task 5 (rutas). Un schema
  Pydantic sin lógica propia no necesita test unitario aislado en este proyecto (mismo criterio que
  `app/schemas/factura.py`, que no tiene test propio).

**Interfaces:**
- Consumes: las formas de dict que devuelven `CitaRepository.resumen_por_estado` (Task 1),
  `PagoRepository.totales_por_periodo` (Task 2), `FacturaRepository.listar_pendientes` (Task 3).
- Produces: `ResumenCitasResponse`, `ResumenPorDoctor`, `ResumenIngresosResponse`,
  `TotalPorMetodoPago`, `PuntoSerie`, `FacturasPendientesResponse`, `ResumenFacturasPendientes`,
  `FacturaPendienteItem` — usados por la Task 5.

- [ ] **Step 1: Write the file** (sin test previo — ver justificación en Interfaces)

Crear `backend/app/schemas/dashboard.py`:

```python
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
```

- [ ] **Step 2: Verify it imports cleanly**

Run: `.venv/Scripts/python.exe -c "from app.schemas.dashboard import ResumenCitasResponse, ResumenIngresosResponse, FacturasPendientesResponse; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/dashboard.py
git commit -m "feat(backend): schemas de respuesta del dashboard"
```

---

### Task 5: Router `GET /dashboard/citas/resumen`

**Files:**
- Create: `backend/app/api/routes/dashboards.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_dashboards_routes.py` (crear)

**Interfaces:**
- Consumes: `CitaRepository.resumen_por_estado` (Task 1), `ResumenCitasResponse` (Task 4),
  `get_current_user`/`resolve_clinica_id`/`get_doctor_actual`/`require_roles` (`app/api/deps.py`,
  ya existen).
- Produces: endpoint `GET /dashboard/citas/resumen`, y el router `dashboards_router` que la Task 6
  y 7 seguirán poblando (mismo archivo, mismo router — no crear un archivo por endpoint).

- [ ] **Step 1: Write the failing test**

Crear `backend/tests/test_dashboards_routes.py`:

```python
from datetime import datetime

from tests.factories import crear_clinica, crear_cita, crear_doctor, crear_paciente, headers_de


def test_resumen_citas_requiere_login(client):
    respuesta = client.get("/dashboard/citas/resumen")

    assert respuesta.status_code == 401


def test_admin_ve_resumen_de_citas(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    crear_cita(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor,
        fecha_hora=datetime(2026, 8, 5, 9, 0), estado="completada",
    )
    db_session.commit()

    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.ADMIN)

    respuesta = client.get(
        "/dashboard/citas/resumen",
        params={"desde": "2026-08-01", "hasta": "2026-08-31"},
        headers=headers,
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["total"] == 1
    assert cuerpo["por_estado"]["completada"] == 1
    assert len(cuerpo["por_doctor"]) == 1


def test_doctor_ve_solo_sus_propias_citas(client, db_session):
    from app.models import RolUsuario
    from tests.factories import crear_usuario, token_de, auth

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

    usuario_doc_a = db_session.get(type(doc_a).id_usuario.class_, doc_a.id_usuario) if False else None
    from app.models import Usuario

    usuario_doc_a = db_session.get(Usuario, doc_a.id_usuario)
    headers = auth(token_de(usuario_doc_a))

    respuesta = client.get(
        "/dashboard/citas/resumen",
        params={"desde": "2026-08-01", "hasta": "2026-08-31"},
        headers=headers,
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["total"] == 1
    assert cuerpo["por_doctor"] == []


def test_doctor_sin_perfil_no_ve_citas(client, db_session):
    from app.models import RolUsuario
    from tests.factories import crear_usuario, token_de, auth

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica, username="doc.con.perfil")
    crear_cita(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor,
        fecha_hora=datetime(2026, 8, 5, 9, 0), estado="completada",
    )
    usuario_sin_perfil = crear_usuario(db_session, RolUsuario.DOCTOR, clinica.id_clinica, "doc.sin.perfil")
    db_session.commit()

    headers = auth(token_de(usuario_sin_perfil))

    respuesta = client.get("/dashboard/citas/resumen", headers=headers)

    assert respuesta.status_code == 200
    assert respuesta.json()["total"] == 0


def test_sin_fechas_usa_mes_actual(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    db_session.commit()
    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.ADMIN)

    respuesta = client.get("/dashboard/citas/resumen", headers=headers)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["desde"] is not None
    assert cuerpo["hasta"] is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_dashboards_routes.py -v`
Expected: FAIL — `404 Not Found` (la ruta todavía no existe / el router no está registrado).

- [ ] **Step 3: Write minimal implementation**

Crear `backend/app/api/routes/dashboards.py`:

```python
from calendar import monthrange
from datetime import date, datetime, time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_doctor_actual, resolve_clinica_id, require_roles
from app.db import get_db
from app.models import Doctor, EstadoCita, RolUsuario, Usuario
from app.repositories.cita_repository import CitaRepository
from app.schemas.dashboard import ResumenCitasResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

VER_CITAS = require_roles(
    RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.ASISTENTE, RolUsuario.DOCTOR
)
VER_FINANCIERO = require_roles(RolUsuario.SUPERADMIN, RolUsuario.ADMIN)


def _rango_mes_actual() -> tuple[date, date]:
    hoy = date.today()
    ultimo_dia = monthrange(hoy.year, hoy.month)[1]
    return date(hoy.year, hoy.month, 1), date(hoy.year, hoy.month, ultimo_dia)


def _completar_rango(desde: date | None, hasta: date | None) -> tuple[date, date]:
    desde_defecto, hasta_defecto = _rango_mes_actual()
    return desde or desde_defecto, hasta or hasta_defecto


@router.get("/citas/resumen", response_model=ResumenCitasResponse, dependencies=[Depends(VER_CITAS)])
def resumen_citas(
    desde: date | None = None,
    hasta: date | None = None,
    id_doctor: int | None = None,
    id_clinica: int = Depends(resolve_clinica_id),
    usuario: Usuario = Depends(get_current_user),
    doctor_actual: Doctor | None = Depends(get_doctor_actual),
    db: Session = Depends(get_db),
) -> ResumenCitasResponse:
    desde, hasta = _completar_rango(desde, hasta)

    if usuario.rol == RolUsuario.DOCTOR:
        if doctor_actual is None:
            return ResumenCitasResponse(
                desde=desde, hasta=hasta, total=0,
                por_estado={estado.value: 0 for estado in EstadoCita}, por_doctor=[],
            )
        resumen = CitaRepository(db).resumen_por_estado(
            id_clinica,
            desde=datetime.combine(desde, time.min),
            hasta=datetime.combine(hasta, time.max),
            id_doctor=doctor_actual.id_doctor,
            incluir_por_doctor=False,
        )
        return ResumenCitasResponse(desde=desde, hasta=hasta, **resumen)

    resumen = CitaRepository(db).resumen_por_estado(
        id_clinica,
        desde=datetime.combine(desde, time.min),
        hasta=datetime.combine(hasta, time.max),
        id_doctor=id_doctor,
    )
    return ResumenCitasResponse(desde=desde, hasta=hasta, **resumen)
```

En `backend/app/main.py`, agregar el import junto a los demás (orden alfabético, después de
`consultorios_router` y antes de `doctores_router` va `dashboards_router`):

```python
from app.api.routes.dashboards import router as dashboards_router
```

Y el `include_router` correspondiente, después de `app.include_router(consultorios_router)`:

```python
app.include_router(dashboards_router)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_dashboards_routes.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/dashboards.py backend/app/main.py backend/tests/test_dashboards_routes.py
git commit -m "feat(backend): endpoint GET /dashboard/citas/resumen"
```

---

### Task 6: Router `GET /dashboard/ingresos`

**Files:**
- Modify: `backend/app/api/routes/dashboards.py`
- Test: `backend/tests/test_dashboards_routes.py` (agregar casos)

**Interfaces:**
- Consumes: `PagoRepository.totales_por_periodo` (Task 2), `ResumenIngresosResponse` (Task 4),
  `VER_FINANCIERO`, `_completar_rango` (ya definidos en la Task 5, mismo archivo).
- Produces: endpoint `GET /dashboard/ingresos`.

- [ ] **Step 1: Write the failing test**

Agregar a `backend/tests/test_dashboards_routes.py`:

```python
def _factura_con_pago(db, id_clinica, id_paciente, id_metodo_pago, monto, fecha_pago, numero):
    from app.models import Factura, Pago

    factura = Factura(
        id_clinica=id_clinica, id_paciente=id_paciente, numero_factura=numero,
        monto_subtotal=monto, monto_impuesto="0.00", monto_total=monto,
    )
    db.add(factura)
    db.flush()
    db.add(Pago(id_factura=factura.id_factura, id_metodo_pago=id_metodo_pago, monto=monto, fecha_pago=fecha_pago))
    db.flush()
    return factura


def test_ingresos_requiere_login(client):
    respuesta = client.get("/dashboard/ingresos")

    assert respuesta.status_code == 401


def test_asistente_no_puede_ver_ingresos(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    db_session.commit()
    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.ASISTENTE)

    respuesta = client.get("/dashboard/ingresos", headers=headers)

    assert respuesta.status_code == 403


def test_doctor_no_puede_ver_ingresos(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    db_session.commit()
    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.DOCTOR)

    respuesta = client.get("/dashboard/ingresos", headers=headers)

    assert respuesta.status_code == 403


def test_admin_ve_ingresos_por_metodo_de_pago(client, db_session):
    from app.models import RolUsuario
    from tests.factories import crear_metodo_pago

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    metodo = crear_metodo_pago(db_session, clinica.id_clinica, nombre="Efectivo")
    _factura_con_pago(
        db_session, clinica.id_clinica, paciente.id_paciente, metodo.id_metodo_pago,
        "45.00", datetime(2026, 8, 5, 10, 0), "F000001",
    )
    db_session.commit()
    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.ADMIN)

    respuesta = client.get(
        "/dashboard/ingresos",
        params={"desde": "2026-08-01", "hasta": "2026-08-31", "agrupar_por": "dia"},
        headers=headers,
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["total"] == "45.00"
    assert cuerpo["por_metodo_pago"][0]["nombre"] == "Efectivo"
    assert len(cuerpo["serie"]) == 1


def test_ingresos_agrupar_por_invalido_da_422(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    db_session.commit()
    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.ADMIN)

    respuesta = client.get(
        "/dashboard/ingresos", params={"agrupar_por": "anio"}, headers=headers,
    )

    assert respuesta.status_code == 422
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_dashboards_routes.py -v`
Expected: los 5 tests nuevos FAIL con `404 Not Found`.

- [ ] **Step 3: Write minimal implementation**

En `backend/app/api/routes/dashboards.py`, agregar el import de `Literal` y `PagoRepository` /
`ResumenIngresosResponse` al tope:

```python
from typing import Literal
```

(agregar después de `from datetime import date, datetime, time`)

```python
from app.repositories.pago_repository import PagoRepository
```

(agregar después de `from app.repositories.cita_repository import CitaRepository`)

```python
from app.schemas.dashboard import ResumenCitasResponse, ResumenIngresosResponse
```

(reemplaza la línea `from app.schemas.dashboard import ResumenCitasResponse`)

Agregar el endpoint nuevo al final del archivo:

```python
@router.get("/ingresos", response_model=ResumenIngresosResponse, dependencies=[Depends(VER_FINANCIERO)])
def resumen_ingresos(
    desde: date | None = None,
    hasta: date | None = None,
    agrupar_por: Literal["dia", "semana", "mes"] = "dia",
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> ResumenIngresosResponse:
    desde, hasta = _completar_rango(desde, hasta)

    resultado = PagoRepository(db).totales_por_periodo(
        id_clinica, desde=desde, hasta=hasta, agrupar_por=agrupar_por
    )
    return ResumenIngresosResponse(desde=desde, hasta=hasta, agrupar_por=agrupar_por, **resultado)
```

`agrupar_por` está tipado `Literal["dia", "semana", "mes"]` en la firma del endpoint, así que
FastAPI/Pydantic devuelven `422` automáticamente para cualquier otro valor — el `ValueError` que
lanza `PagoRepository.totales_por_periodo` (Task 2) es una defensa adicional para quien llame al
repositorio directamente, no lo que dispara este `422` en la ruta.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_dashboards_routes.py -v`
Expected: PASS (10 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/dashboards.py backend/tests/test_dashboards_routes.py
git commit -m "feat(backend): endpoint GET /dashboard/ingresos"
```

---

### Task 7: Router `GET /dashboard/facturas-pendientes`

**Files:**
- Modify: `backend/app/api/routes/dashboards.py`
- Test: `backend/tests/test_dashboards_routes.py` (agregar casos)

**Interfaces:**
- Consumes: `FacturaRepository.listar_pendientes` (Task 3), `FacturasPendientesResponse` (Task 4),
  `VER_FINANCIERO` (ya definido).
- Produces: endpoint `GET /dashboard/facturas-pendientes`.

- [ ] **Step 1: Write the failing test**

Agregar a `backend/tests/test_dashboards_routes.py`:

```python
def test_facturas_pendientes_requiere_login(client):
    respuesta = client.get("/dashboard/facturas-pendientes")

    assert respuesta.status_code == 401


def test_asistente_no_puede_ver_facturas_pendientes(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    db_session.commit()
    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.ASISTENTE)

    respuesta = client.get("/dashboard/facturas-pendientes", headers=headers)

    assert respuesta.status_code == 403


def test_admin_ve_facturas_pendientes(client, db_session):
    from app.models import RolUsuario
    from app.repositories.factura_repository import FacturaRepository

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    FacturaRepository(db_session).crear(
        clinica.id_clinica,
        {"id_paciente": paciente.id_paciente, "numero_factura": "F000001",
         "monto_subtotal": "60.00", "monto_impuesto": "0.00", "monto_total": "60.00"},
    )
    db_session.commit()
    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.ADMIN)

    respuesta = client.get("/dashboard/facturas-pendientes", headers=headers)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["resumen"]["cantidad"] == 1
    assert cuerpo["facturas"][0]["saldo_pendiente"] == "60.00"


def test_facturas_pendientes_no_mezcla_clinicas(client, db_session):
    from app.models import RolUsuario
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
    headers = headers_de(db_session, clinica_a.id_clinica, RolUsuario.ADMIN)

    respuesta = client.get("/dashboard/facturas-pendientes", headers=headers)

    assert respuesta.status_code == 200
    assert respuesta.json()["resumen"]["cantidad"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_dashboards_routes.py -v`
Expected: los 4 tests nuevos FAIL con `404 Not Found`.

- [ ] **Step 3: Write minimal implementation**

En `backend/app/api/routes/dashboards.py`, agregar los imports que faltan al tope:

```python
from app.repositories.factura_repository import FacturaRepository
```

(agregar después de `from app.repositories.cita_repository import CitaRepository`)

```python
from app.schemas.dashboard import (
    FacturasPendientesResponse,
    ResumenCitasResponse,
    ResumenIngresosResponse,
)
```

(reemplaza la línea `from app.schemas.dashboard import ResumenCitasResponse, ResumenIngresosResponse`)

Agregar el endpoint nuevo al final del archivo:

```python
@router.get(
    "/facturas-pendientes", response_model=FacturasPendientesResponse,
    dependencies=[Depends(VER_FINANCIERO)],
)
def facturas_pendientes(
    desde: date | None = None,
    hasta: date | None = None,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> FacturasPendientesResponse:
    resultado = FacturaRepository(db).listar_pendientes(id_clinica, desde=desde, hasta=hasta)
    return FacturasPendientesResponse(**resultado)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_dashboards_routes.py -v`
Expected: PASS (14 tests)

Correr también la suite completa para confirmar que no se rompió nada de los Módulos 1-6:

Run: `.venv/Scripts/python.exe -m pytest -v`
Expected: PASS, todos los tests (los preexistentes + los 18 de `test_dashboard_repositorios.py` +
los 14 de `test_dashboards_routes.py`).

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/dashboards.py backend/tests/test_dashboards_routes.py
git commit -m "feat(backend): endpoint GET /dashboard/facturas-pendientes"
```

---

### Task 8: Verificación contra Docker/MySQL real

**Files:** ninguno (verificación manual, sin cambios de código salvo que aparezca un bug).

**Interfaces:** ninguna nueva — esta tarea prueba las Tasks 1-7 contra MySQL real.

Esta tarea es obligatoria (ver Global Constraints y sección 6 de `CONTEXTO-PROYECTO.md`): la
agrupación por semana/mes en `PagoRepository._expr_periodo` (Task 2) es SQL con rama por dialecto
que **nunca corrió contra MySQL real** hasta este punto — solo contra SQLite en los tests.

- [ ] **Step 1: Reconstruir y levantar el backend**

Desde la raíz del repo:

```bash
docker compose build backend
docker compose up -d
docker compose exec backend alembic upgrade head
```

Expected: `alembic upgrade head` corre limpio (no hay migraciones nuevas en este módulo, así que
debería quedar en la misma revisión que al cerrar el Módulo 6). Si el primer intento falla con
error 2003, reintentar a los pocos segundos (gotcha conocido, sección 9 de `CONTEXTO-PROYECTO.md`).

- [ ] **Step 2: Sembrar el superadmin si hace falta**

Si el volumen de MySQL es nuevo (`docker compose down -v` se corrió en algún momento):

```powershell
Get-Content backend/scripts/seed_superadmin_dev.sql | docker compose exec -T db mysql -u root -p<TU_DB_PASSWORD> clinica_dental_web
```

- [ ] **Step 3: Login y armar datos de prueba vía HTTP**

Loguearse como `superadmin`/`Superadmin123` contra `http://localhost:8000/auth/login`, crear una
clínica con `POST /clinicas` (da un admin con password temporal), loguearse como ese admin, crear
un doctor (`POST /doctores`), un paciente (`POST /pacientes`), un método de pago
(`POST /metodos-pago`), un tratamiento (`POST /tratamientos`), una factura suelta
(`POST /facturas`), y registrar dos o tres pagos parciales sobre ella en fechas distintas
(`POST /facturas/{id}/pagos`) — usar `fecha_pago` en distintos días si el endpoint de pagos lo
acepta, o revisar que `Pago.fecha_pago` tenga `server_default=func.now()` y por ende use la fecha
real del servidor al registrar cada pago (probablemente el mismo día; para probar `agrupar_por` con
más de un período real, registrar pagos en llamadas separadas en momentos distintos, o aceptar que
la serie tenga un solo punto y enfocar la verificación en que el query no rompa, no en que haya
múltiples períodos).

- [ ] **Step 4: Probar los tres endpoints, con foco en `agrupar_por`**

```
GET /dashboard/citas/resumen?desde=2026-08-01&hasta=2026-08-31
GET /dashboard/ingresos?agrupar_por=dia
GET /dashboard/ingresos?agrupar_por=semana
GET /dashboard/ingresos?agrupar_por=mes
GET /dashboard/facturas-pendientes
```

Expected: los cinco devuelven `200` con datos coherentes (el `total` de ingresos coincide con la
suma de pagos registrados, `facturas-pendientes` muestra la factura con su `saldo_pendiente`
correcto). Los tres `agrupar_por` en particular **no deben lanzar un error de SQL** — es el caso
que la suite de SQLite no puede probar, porque `func.date_format` no existe en SQLite y viceversa
`func.strftime` no existe en MySQL. Si alguno falla, es un bug real de la Task 2 a corregir antes
de continuar (no se documenta como deuda conocida — es la verificación que este módulo existe para
hacer).

- [ ] **Step 5: Confirmar permisos con otro rol**

Loguearse como el doctor o la asistente creados y confirmar que `GET /dashboard/ingresos` y
`GET /dashboard/facturas-pendientes` devuelven `403`, y que `GET /dashboard/citas/resumen` sí
funciona (filtrado a sus propias citas si es doctor).

- [ ] **Step 6: Registrar el resultado**

No hay commit de código en esta tarea salvo que se haya encontrado y corregido un bug (en cuyo
caso, commit normal describiendo el fix). Documentar la verificación en la Task 9 (actualización de
`CONTEXTO-PROYECTO.md`).

---

### Task 9: Documentación — actualizar `CONTEXTO-PROYECTO.md`, mapa de Obsidian y roadmap

**Files:**
- Modify: `docs/CONTEXTO-PROYECTO.md`
- Modify: `Obsidian/Clinica mapa/Clinica Dental/Modulo 7 - Dashboards.md`
- Modify: `Obsidian/Clinica mapa/Clinica Dental/ClinicaDentalWeb - Mapa del Proyecto.md`
- Modify: `Obsidian/Clinica mapa/Clinica Dental/Roadmap.md`

**Interfaces:** ninguna — solo documentación, sin código.

- [ ] **Step 1: Agregar la sección del Módulo 7 a `CONTEXTO-PROYECTO.md`**

Después de la sección "6quinquies. Qué existe ya — Módulo 6 (Facturación Extendida)" y antes de
"## 7. Convenciones a seguir", agregar:

```markdown
---

## 6sexies. Qué existe ya — Módulo 7 (Dashboards y Métricas)

**Sin modelos ni migraciones nuevas.** Los tres endpoints agregan datos ya existentes de `Cita`
(Módulo 4) y `Factura`/`Pago` (Módulo 6).

**Sin `DashboardService`.** Son lecturas puras que no coordinan una transacción — no encajan en el
criterio que el proyecto usa para justificar un service. Se agregaron métodos de agregación
directo a los repositorios existentes:

- `CitaRepository.resumen_por_estado(id_clinica, desde=None, hasta=None, id_doctor=None,
  incluir_por_doctor=True)` — cuenta citas por estado (`GROUP BY estado`) y opcionalmente por
  doctor, en SQL.
- `PagoRepository.totales_por_periodo(id_clinica, desde=None, hasta=None, agrupar_por="dia")` —
  ingresos **cobrados** (`SUM(Pago.monto)`, no facturado), por método de pago y en una serie
  temporal agrupable por día/semana/mes.
- `FacturaRepository.listar_pendientes(id_clinica, desde=None, hasta=None)` — facturas en estado
  `pendiente`/`parcial` con su saldo pendiente calculado (`monto_total - SUM(Pago.monto)`).

**Riesgo aceptado y verificado: agrupación de fechas en SQL con rama por dialecto.**
`PagoRepository._expr_periodo` usa `func.strftime` en SQLite (tests) y `func.date_format` en MySQL
(producción) para truncar `Pago.fecha_pago` a día/semana/mes. Es la misma familia de riesgo que
documenta `CitaRepository._solapadas` (que lo resuelve calculando en Python) — acá se aceptó el
riesgo por eficiencia, con la condición de que **la verificación Docker/MySQL de este módulo probó
explícitamente `agrupar_por=semana` y `agrupar_por=mes` contra MySQL real** antes de cerrarlo (no
solo SQLite). [Completar con el resultado real de la Task 8 al cerrar el módulo.]

**Permisos, divididos por tipo de métrica, no una regla única** (a diferencia del Módulo 3):

| Endpoint | Superadmin/Admin | Asistente | Doctor |
|---|---|---|---|
| `GET /dashboard/citas/resumen` | Sí, toda la clínica | Sí, toda la clínica | Sí, **solo lo suyo** |
| `GET /dashboard/ingresos` | Sí | No (`403`) | No (`403`) |
| `GET /dashboard/facturas-pendientes` | Sí | No (`403`) | No (`403`) |

Mismo criterio que Módulo 4/6 para el filtro del doctor: `WHERE id_doctor = <el suyo>` inyectado
vía `get_doctor_actual`, no un `403` — y la ausencia de perfil cierra a "no ve nada" (`total: 0`),
no abre a "ve todo".

**Rangos de fecha — dos comportamientos distintos a propósito:**
- `/dashboard/citas/resumen` y `/dashboard/ingresos`: `desde`/`hasta` con default el mes actual si
  no se pasan — el caso más común es "el dashboard de ahora".
- `/dashboard/facturas-pendientes`: `desde`/`hasta` opcionales **sin default** (sin límite si no se
  pasan) — una factura pendiente de hace meses sigue siendo cobrable hoy, no tiene sentido ocultarla
  por un filtro de fecha implícito.

**Endpoints:** `GET /dashboard/citas/resumen`, `GET /dashboard/ingresos`,
`GET /dashboard/facturas-pendientes` — los tres en `app/api/routes/dashboards.py`, prefijo
`/dashboard`.

**Deuda conocida y decidida a conciencia:** no se agregó una cuarta métrica de tratamientos/
consultas (`Consulta`, `PlanTratamientoDetalle.estado`) aunque los datos ya están listos desde el
Módulo 5 — decisión explícita del brainstorming para no ampliar el alcance original del módulo.
Queda disponible para una extensión futura si se pide.
```

- [ ] **Step 2: Actualizar la tabla del roadmap (sección 2 de `CONTEXTO-PROYECTO.md`)**

Cambiar la fila del Módulo 7 de `⬜ Pendiente` a `✅ Completo` y actualizar el párrafo siguiente:

```markdown
| 7 | Dashboards y métricas | Christian | ✅ Completo |
```

Y reemplazar el párrafo:

```markdown
**Módulos 1 a 7 completos.** Queda el 8 (Notificaciones), sin asignar formalmente — con Meli
habiendo cerrado hasta el Módulo 5 y Christian el 6 y el 7, le queda a quien lo tome primero salvo
que se reasigne.
```

- [ ] **Step 3: Actualizar `docs/superpowers/specs`/`docs/superpowers/plans` en la lista de la
  sección 1**

Agregar después de la línea del Módulo 6:

```markdown
- `docs/superpowers/specs/2026-08-08-modulo-7-dashboards-design.md` — spec del Módulo 7, incluye
  el split de permisos por tipo de métrica y la decisión de agregar fechas en SQL con rama por
  dialecto.
- `docs/superpowers/plans/2026-08-08-modulo-7-dashboards-plan.md` — plan TDD del Módulo 7.
```

- [ ] **Step 4: Actualizar la nota de Obsidian del Módulo 7**

Reescribir `Obsidian/Clinica mapa/Clinica Dental/Modulo 7 - Dashboards.md` completo:

```markdown
#modulo7 #backend #completo

# Módulo 7 — Dashboards

**Estado:** ✅ Completo · **Quién:** Christian
Enlaza a [[Roadmap]] · Depende de: [[Modulo 4 - Operacion Clinica Basica]],
[[Modulo 6 - Facturacion Extendida]]

## Qué construye

Tres endpoints de solo lectura en `app/api/routes/dashboards.py`, sin modelos ni migraciones
nuevas — todo se agrega sobre `Cita`, `Factura` y `Pago` ya existentes:

- `GET /dashboard/citas/resumen` — conteo de citas por estado, rango de fechas y doctor. Los 4
  roles, con el doctor forzado a sus propias citas (mismo criterio de [[Convenciones de
  Arquitectura]]: filtro por WHERE, no 403).
- `GET /dashboard/ingresos` — dinero **cobrado** (no facturado) por período y método de pago, con
  serie temporal agrupable por día/semana/mes. Solo superadmin/admin.
- `GET /dashboard/facturas-pendientes` — facturas en estado pendiente/parcial con saldo pendiente
  calculado. Solo superadmin/admin, sin filtro de fecha por default.

## Decisión que vale la pena recordar

`PagoRepository._expr_periodo` agrupa fechas en SQL con una rama explícita por dialecto
(`sqlite`/`mysql`) — a diferencia de `CitaRepository._solapadas` (Módulo 4), que resuelve el mismo
tipo de riesgo calculando en Python. Se aceptó el riesgo por eficiencia, verificado explícitamente
contra MySQL real antes de cerrar el módulo. Ver [[Bugs Conocidos]] si esto vuelve a morder.

## Deuda conocida

No incluye métricas de tratamientos/consultas (`Consulta`, `PlanTratamientoDetalle.estado`) —
alcance recortado a propósito en el brainstorming. Los datos ya están listos si se pide después.

## Detalle completo

`docs/CONTEXTO-PROYECTO.md` sección 6sexies. Spec:
`docs/superpowers/specs/2026-08-08-modulo-7-dashboards-design.md`. Plan:
`docs/superpowers/plans/2026-08-08-modulo-7-dashboards-plan.md`.
```

- [ ] **Step 5: Actualizar el mapa del proyecto y el roadmap de Obsidian**

En `Obsidian/Clinica mapa/Clinica Dental/ClinicaDentalWeb - Mapa del Proyecto.md`, cambiar:

```markdown
- [[Modulo 7 - Dashboards]] ⬜ siguiente
```

por:

```markdown
- [[Modulo 7 - Dashboards]] ✅
```

Y en la sección "Cómo arrancar la próxima sesión de Claude Code", actualizar el mensaje sugerido
para que diga "Vamos a seguir con el Módulo 8 (Notificaciones)" en vez del 7.

En `Obsidian/Clinica mapa/Clinica Dental/Roadmap.md`, actualizar la fila del Módulo 7 a completo
(mismo formato que ya tiene esa tabla para los Módulos 1-6 — revisar el archivo al editar para
copiar el formato exacto).

- [ ] **Step 6: Commit**

```bash
git add docs/CONTEXTO-PROYECTO.md "Obsidian/Clinica mapa/Clinica Dental/Modulo 7 - Dashboards.md" \
  "Obsidian/Clinica mapa/Clinica Dental/ClinicaDentalWeb - Mapa del Proyecto.md" \
  "Obsidian/Clinica mapa/Clinica Dental/Roadmap.md"
git commit -m "docs: cierra el Modulo 7 (Dashboards) en CONTEXTO-PROYECTO y el vault de Obsidian"
```

---

## Self-Review

**Cobertura del spec:** los 3 endpoints (sección 3.1-3.3) → Tasks 5-7. Sin `DashboardService`
(2.1) → confirmado en las Tasks 1-3 (métodos van directo en los repos existentes). Ingresos =
cobrado (2.2) → `PagoRepository.totales_por_periodo` suma `Pago.monto`, nunca `Factura.monto_total`
(Task 2). Rangos de fecha (2.3) → `_completar_rango`/`_rango_mes_actual` en Task 5, sin default en
`listar_pendientes` (Task 3/7). Agregación SQL con rama por dialecto (2.4) → `_expr_periodo` (Task
2) + verificación Docker obligatoria (Task 8). Permisos por tipo de métrica (2.5) → `VER_CITAS`/
`VER_FINANCIERO` (Task 5) con tests de `403` explícitos (Tasks 6-7). Testing (sección 5 del spec) →
Tasks 1-3 (repos), 5-7 (rutas + permisos + aislamiento entre clínicas), 8 (Docker/MySQL). Qué no
cambia (sección 6) → ningún archivo de los Módulos 1-6 se modifica salvo agregar métodos nuevos a
tres repositorios existentes, consistente con el plan.

**Placeholders:** ninguno — cada step tiene código completo, sin "TODO" ni "similar a la Task N".
La única nota entre corchetes ("[Completar con el resultado real de la Task 8...]") es intencional:
es contenido de documentación que depende de un resultado que todavía no existe al escribir el
plan, y la Task 9 la resuelve con el resultado real de la Task 8 — no es una laguna del plan.

**Consistencia de tipos:** `resumen_por_estado` devuelve siempre `{"total", "por_estado",
"por_doctor"}` (Task 1), consumido igual por `ResumenCitasResponse` (Task 4) y por la ruta (Task
5). `totales_por_periodo` devuelve `{"total", "por_metodo_pago", "serie"}` (Task 2), consumido por
`ResumenIngresosResponse` (Task 4) y la ruta (Task 6). `listar_pendientes` devuelve `{"resumen",
"facturas"}` (Task 3), consumido por `FacturasPendientesResponse` (Task 4) y la ruta (Task 7) — los
tres nombres de campo coinciden letra por letra entre el repositorio, el schema y el uso en la
ruta.
