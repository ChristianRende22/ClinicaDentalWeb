# Módulo 6: Facturación Extendida — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convertir un `Presupuesto` aceptado (Módulo 5) en una `Factura` real, o facturar suelto
sin plan de tratamiento; aplicar impuesto y numeración de `ConfiguracionClinica` (Módulo 3);
registrar pagos parciales hasta saldar el total; anular facturas sin pagos.

**Architecture:** Mismo patrón del resto del proyecto: modelos SQLAlchemy con `values_callable`
en el enum nuevo, `FacturaRepository` heredando `BaseRepository` (recurso tenant-scoped con PK
simple), `FacturaDetalleRepository`/`PagoRepository` **sin** heredar (child de `Factura`,
aislados por `JOIN`, igual que `PlanTratamientoDetalleRepository` del Módulo 5), y dos servicios
(`FacturaService`, `PagoService`) que orquestan transacciones multi-tabla con
`try`/`except`+`db.rollback()` explícito, igual que `ClinicaService`/`PersonalService`.

**Tech Stack:** El mismo del proyecto (FastAPI, SQLAlchemy 2.0, Alembic, MySQL, pytest). Sin
dependencias nuevas.

## Global Constraints

- `Factura.numero_factura` es un correlativo **interno**, no un DTE (Documento Tributario
  Electrónico) — sección 2 del spec. Ningún campo de facturación electrónica se agrega en este
  módulo.
- `FacturaDetalle` y `Pago` **no** llevan `id_clinica` propio — se aíslan vía `JOIN` contra
  `Factura`, mismo criterio que `PlanTratamientoDetalle` (confirmado leyendo
  `plan_tratamiento_repository.py` antes de escribir este plan).
- Todo enum nuevo (`EstadoFactura`) lleva `values_callable=lambda enum_cls: [e.value for e in enum_cls]` desde el día uno — bug #2 de la sección 8 de `docs/CONTEXTO-PROYECTO.md`.
- `monto_impuesto`/`monto_subtotal`/`monto_total` se calculan y se **guardan** al emitir; no se
  recalculan si `ConfiguracionClinica.porcentaje_impuesto` cambia después.
- `id_asistente` en `Factura`/`Pago` sale del JWT (`get_current_user` + `AsistenteRepository.obtener_por_usuario`), nunca del body — mismo patrón que `id_asistente` en `POST /citas` (Módulo 4).
- Doctor: **solo lectura**, y solo de sus propias facturas (`WHERE id_doctor = <el suyo>`, una
  factura ajena por id da **404** no 403 — mismo criterio que `GET /citas` del Módulo 4).
- Anular una factura solo si no tiene pagos registrados. Un pago no puede exceder el saldo
  pendiente de la factura.

Todos los comandos se ejecutan con `backend/` como directorio de trabajo, usando
`.venv/Scripts/python.exe`.

---

## File Structure

```
backend/
  alembic/versions/0006_facturacion.py           (create)
  app/
    exceptions.py                                 (modify: +4 excepciones)
    models/
      factura.py                                   (create: Factura, FacturaDetalle, Pago, EstadoFactura)
      __init__.py                                   (modify: exporta lo nuevo)
    repositories/
      factura_repository.py                         (create)
      factura_detalle_repository.py                 (create)
      pago_repository.py                            (create)
    services/
      factura_service.py                            (create)
      pago_service.py                               (create)
    schemas/
      factura.py                                     (create)
    api/routes/
      planes_tratamiento.py                          (modify: + POST /{id_plan}/factura)
      facturas.py                                     (create)
    main.py                                          (modify: registra el router de facturas)
  tests/
    factories.py                                     (modify: +3 helpers)
    test_factura_models.py                           (create)
    test_factura_repository.py                       (create)
    test_factura_detalle_repository.py                (create)
    test_pago_repository.py                          (create)
    test_factura_service.py                          (create)
    test_pago_service.py                             (create)
    test_facturas_routes.py                          (create)
```

---

### Task 1: Modelos, excepciones y migración

**Files:**
- Create: `backend/app/models/factura.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/exceptions.py`
- Create: `backend/tests/test_factura_models.py`
- Create: `backend/alembic/versions/0006_facturacion.py`

**Interfaces:**
- Produces: `Factura`, `FacturaDetalle`, `Pago`, `EstadoFactura` (`app.models`).
  `PresupuestoNoAceptadoError`, `FacturaConPagosError`, `FacturaAnuladaError`,
  `PagoExcedeSaldoError` (`app.exceptions`).

- [ ] **Step 1: Escribir el test (falla primero)**

`backend/tests/test_factura_models.py`:

```python
def _crear_clinica(db):
    from app.models import Clinica

    clinica = Clinica(nombre="Dental Uno")
    db.add(clinica)
    db.flush()
    return clinica


def _crear_paciente(db, id_clinica):
    from app.models import Paciente

    paciente = Paciente(id_clinica=id_clinica, nombre="Ana", apellido="Lopez", telefono="70001122")
    db.add(paciente)
    db.flush()
    return paciente


def _crear_tratamiento(db, id_clinica):
    from app.models import Tratamiento

    tratamiento = Tratamiento(id_clinica=id_clinica, nombre="Limpieza", precio="25.00")
    db.add(tratamiento)
    db.flush()
    return tratamiento


def test_crear_factura_con_detalle_y_pago(db_session):
    from app.models import EstadoFactura, Factura, FacturaDetalle, Pago

    clinica = _crear_clinica(db_session)
    paciente = _crear_paciente(db_session, clinica.id_clinica)
    tratamiento = _crear_tratamiento(db_session, clinica.id_clinica)

    factura = Factura(
        id_clinica=clinica.id_clinica,
        id_paciente=paciente.id_paciente,
        numero_factura="F000001",
        monto_subtotal="25.00",
        monto_impuesto="3.25",
        monto_total="28.25",
    )
    db_session.add(factura)
    db_session.flush()

    assert factura.id_factura is not None
    assert factura.estado == EstadoFactura.PENDIENTE

    detalle = FacturaDetalle(
        id_factura=factura.id_factura,
        id_tratamiento=tratamiento.id_tratamiento,
        cantidad=1,
        precio_unitario="25.00",
    )
    db_session.add(detalle)

    from app.models import MetodoPago

    metodo = MetodoPago(id_clinica=clinica.id_clinica, nombre="Efectivo")
    db_session.add(metodo)
    db_session.flush()

    pago = Pago(id_factura=factura.id_factura, id_metodo_pago=metodo.id_metodo_pago, monto="28.25")
    db_session.add(pago)
    db_session.commit()

    assert detalle.id_detalle is not None
    assert pago.id_pago is not None


def test_numero_factura_es_unico_por_clinica(db_session):
    from app.models import Factura
    from sqlalchemy.exc import IntegrityError
    import pytest

    clinica = _crear_clinica(db_session)
    paciente = _crear_paciente(db_session, clinica.id_clinica)

    db_session.add(
        Factura(
            id_clinica=clinica.id_clinica,
            id_paciente=paciente.id_paciente,
            numero_factura="F000001",
            monto_subtotal="10.00",
            monto_impuesto="1.30",
            monto_total="11.30",
        )
    )
    db_session.commit()

    db_session.add(
        Factura(
            id_clinica=clinica.id_clinica,
            id_paciente=paciente.id_paciente,
            numero_factura="F000001",
            monto_subtotal="20.00",
            monto_impuesto="2.60",
            monto_total="22.60",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_factura_models.py -v`
Expected: FAIL con `ImportError: cannot import name 'Factura' from 'app.models'`

- [ ] **Step 3: Implementar `app/models/factura.py`**

```python
import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class EstadoFactura(str, enum.Enum):
    PENDIENTE = "pendiente"
    PARCIAL = "parcial"
    PAGADA = "pagada"
    ANULADA = "anulada"


class Factura(Base):
    """Factura interna de la clinica -- NO es un Documento Tributario
    Electronico (DTE). numero_factura es un correlativo propio de
    ConfiguracionClinica (prefijo_factura + proximo_numero_factura, Modulo 3),
    no un codigo de generacion de Hacienda. Ver seccion 2 del spec del
    Modulo 6: un modulo futuro de facturacion electronica puede agregar esos
    campos (codigo_generacion, sello_recibido, etc.) con una migracion nueva
    de columnas nullable, sin romper nada de esto.

    monto_subtotal/monto_impuesto/monto_total se calculan y se CONGELAN al
    emitir -- misma foto-del-momento que Cita.duracion_minutos (Modulo 4) y
    PlanTratamientoDetalle.precio_unitario (Modulo 5): si el % de impuesto de
    la clinica cambia despues, las facturas ya emitidas no se mueven.
    """

    __tablename__ = "factura"
    __table_args__ = (
        UniqueConstraint("id_clinica", "numero_factura", name="uq_factura_clinica_numero"),
    )

    id_factura: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_clinica: Mapped[int] = mapped_column(ForeignKey("clinica.id_clinica"), nullable=False)
    id_paciente: Mapped[int] = mapped_column(ForeignKey("paciente.id_paciente"), nullable=False)
    #: Nullable: nulo en un cargo administrativo suelto sin tratamiento clinico
    #: asociado. Cuando tiene valor, es el filtro de "solo mis facturas" del
    #: doctor (ver GET /facturas).
    id_doctor: Mapped[int | None] = mapped_column(ForeignKey("doctor.id_doctor"), nullable=True)
    #: Quien la emitio. Sale del JWT en la ruta, nunca del body.
    id_asistente: Mapped[int | None] = mapped_column(
        ForeignKey("asistente.id_asistente"), nullable=True
    )
    #: 1:1 opcional: solo si esta factura nacio de un Presupuesto aceptado.
    id_plan: Mapped[int | None] = mapped_column(
        ForeignKey("plan_tratamiento.id_plan"), nullable=True, unique=True
    )
    numero_factura: Mapped[str] = mapped_column(String(20), nullable=False)
    monto_subtotal: Mapped[str] = mapped_column(Numeric(10, 2), nullable=False)
    monto_impuesto: Mapped[str] = mapped_column(Numeric(10, 2), nullable=False)
    monto_total: Mapped[str] = mapped_column(Numeric(10, 2), nullable=False)
    estado: Mapped[EstadoFactura] = mapped_column(
        SAEnum(
            EstadoFactura,
            name="estado_factura",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        default=EstadoFactura.PENDIENTE,
        server_default="pendiente",
        nullable=False,
    )
    fecha_emision: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class FacturaDetalle(Base):
    """Linea de una factura: un tratamiento con precio congelado al momento
    de facturar. NO lleva id_clinica propio -- se aisla via JOIN contra
    Factura, mismo criterio que PlanTratamientoDetalle del Modulo 5.
    """

    __tablename__ = "factura_detalle"

    id_detalle: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_factura: Mapped[int] = mapped_column(ForeignKey("factura.id_factura"), nullable=False)
    id_tratamiento: Mapped[int] = mapped_column(
        ForeignKey("tratamiento.id_tratamiento"), nullable=False
    )
    cantidad: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    precio_unitario: Mapped[str] = mapped_column(Numeric(10, 2), nullable=False)


class Pago(Base):
    """Un pago (parcial o total) contra una factura. NO lleva id_clinica
    propio, mismo criterio que FacturaDetalle.
    """

    __tablename__ = "pago"

    id_pago: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_factura: Mapped[int] = mapped_column(ForeignKey("factura.id_factura"), nullable=False)
    id_metodo_pago: Mapped[int] = mapped_column(
        ForeignKey("metodo_pago.id_metodo_pago"), nullable=False
    )
    id_asistente: Mapped[int | None] = mapped_column(
        ForeignKey("asistente.id_asistente"), nullable=True
    )
    monto: Mapped[str] = mapped_column(Numeric(10, 2), nullable=False)
    fecha_pago: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 4: Actualizar `app/models/__init__.py`**

Agregar el import y los tres nombres nuevos al `__all__`:

```python
from app.models.factura import EstadoFactura, Factura, FacturaDetalle, Pago
```

```python
    "Factura",
    "FacturaDetalle",
    "Pago",
    "EstadoFactura",
```

(Insertar el import junto a los demás `from app.models.<archivo> import ...` en orden
alfabético del nombre de archivo, y las cuatro entradas al final de la lista `__all__`, igual
que se hizo con `Receta`/`RecetaDetalle` del Módulo 5.)

- [ ] **Step 5: Agregar las excepciones en `app/exceptions.py`**

Agregar al final del archivo:

```python
class PresupuestoNoAceptadoError(Exception):
    """No se puede generar una factura: el presupuesto de este plan todavia
    no fue aceptado por el paciente."""


class FacturaConPagosError(Exception):
    """No se puede anular: la factura ya tiene pagos registrados."""


class FacturaAnuladaError(Exception):
    """No se pueden registrar pagos sobre una factura anulada."""


class PagoExcedeSaldoError(Exception):
    """El monto del pago es mayor al saldo pendiente de la factura."""
```

- [ ] **Step 6: Ejecutar el test y verificar que pasa**

Run: `.venv/Scripts/python.exe -m pytest tests/test_factura_models.py -v`
Expected: `2 passed`

- [ ] **Step 7: Escribir la migración**

`backend/alembic/versions/0006_facturacion.py`:

```python
"""facturacion: factura, factura_detalle, pago

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-06
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

_ESTADOS_FACTURA = ("pendiente", "parcial", "pagada", "anulada")


def upgrade() -> None:
    op.create_table(
        "factura",
        sa.Column("id_factura", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_clinica", sa.Integer(), nullable=False),
        sa.Column("id_paciente", sa.Integer(), nullable=False),
        sa.Column("id_doctor", sa.Integer(), nullable=True),
        sa.Column("id_asistente", sa.Integer(), nullable=True),
        sa.Column("id_plan", sa.Integer(), nullable=True),
        sa.Column("numero_factura", sa.String(length=20), nullable=False),
        sa.Column("monto_subtotal", sa.Numeric(10, 2), nullable=False),
        sa.Column("monto_impuesto", sa.Numeric(10, 2), nullable=False),
        sa.Column("monto_total", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "estado",
            sa.Enum(*_ESTADOS_FACTURA, name="estado_factura"),
            server_default="pendiente",
            nullable=False,
        ),
        sa.Column(
            "fecha_emision", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.ForeignKeyConstraint(["id_clinica"], ["clinica.id_clinica"]),
        sa.ForeignKeyConstraint(["id_paciente"], ["paciente.id_paciente"]),
        sa.ForeignKeyConstraint(["id_doctor"], ["doctor.id_doctor"]),
        sa.ForeignKeyConstraint(["id_asistente"], ["asistente.id_asistente"]),
        sa.ForeignKeyConstraint(["id_plan"], ["plan_tratamiento.id_plan"]),
        sa.PrimaryKeyConstraint("id_factura"),
        sa.UniqueConstraint("id_clinica", "numero_factura", name="uq_factura_clinica_numero"),
        sa.UniqueConstraint("id_plan", name="uq_factura_plan"),
    )

    op.create_table(
        "factura_detalle",
        sa.Column("id_detalle", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_factura", sa.Integer(), nullable=False),
        sa.Column("id_tratamiento", sa.Integer(), nullable=False),
        sa.Column("cantidad", sa.Integer(), server_default="1", nullable=False),
        sa.Column("precio_unitario", sa.Numeric(10, 2), nullable=False),
        sa.ForeignKeyConstraint(["id_factura"], ["factura.id_factura"]),
        sa.ForeignKeyConstraint(["id_tratamiento"], ["tratamiento.id_tratamiento"]),
        sa.PrimaryKeyConstraint("id_detalle"),
    )

    op.create_table(
        "pago",
        sa.Column("id_pago", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_factura", sa.Integer(), nullable=False),
        sa.Column("id_metodo_pago", sa.Integer(), nullable=False),
        sa.Column("id_asistente", sa.Integer(), nullable=True),
        sa.Column("monto", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "fecha_pago", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.ForeignKeyConstraint(["id_factura"], ["factura.id_factura"]),
        sa.ForeignKeyConstraint(["id_metodo_pago"], ["metodo_pago.id_metodo_pago"]),
        sa.ForeignKeyConstraint(["id_asistente"], ["asistente.id_asistente"]),
        sa.PrimaryKeyConstraint("id_pago"),
    )


def downgrade() -> None:
    op.drop_table("pago")
    op.drop_table("factura_detalle")
    op.drop_table("factura")
```

- [ ] **Step 8: Verificar que la migración es válida**

Run: `.venv/Scripts/python.exe -m alembic history --verbose`
Expected: muestra `0006 (head)` con `Revises: 0005`, sin errores.

- [ ] **Step 9: Commit**

```bash
git add backend/app/models/factura.py backend/app/models/__init__.py backend/app/exceptions.py backend/tests/test_factura_models.py backend/alembic/versions/0006_facturacion.py
git commit -m "feat(backend): modelos Factura/FacturaDetalle/Pago y migracion"
```

---

### Task 2: `FacturaRepository`

**Files:**
- Create: `backend/app/repositories/factura_repository.py`
- Create: `backend/tests/test_factura_repository.py`

**Interfaces:**
- Produces: `FacturaRepository(BaseRepository[Factura])` con `listar(id_clinica, id_paciente=None, id_doctor=None)`, `obtener(id_clinica, id_)`, `crear(id_clinica, data)`, `actualizar(id_clinica, id_, data)`, `eliminar` (lanza `NotImplementedError`), `obtener_por_plan(id_clinica, id_plan)`. Usado por Task 5 en adelante.

- [ ] **Step 1: Escribir el test (falla primero)**

`backend/tests/test_factura_repository.py`:

```python
def _clinica_y_paciente(db):
    from app.models import Clinica, Paciente

    clinica = Clinica(nombre="Dental Uno")
    db.add(clinica)
    db.flush()
    paciente = Paciente(id_clinica=clinica.id_clinica, nombre="Ana", apellido="Lopez", telefono="70001122")
    db.add(paciente)
    db.flush()
    return clinica, paciente


def test_crear_y_obtener(db_session):
    from app.repositories.factura_repository import FacturaRepository

    clinica, paciente = _clinica_y_paciente(db_session)
    repo = FacturaRepository(db_session)
    factura = repo.crear(
        clinica.id_clinica,
        {
            "id_paciente": paciente.id_paciente,
            "numero_factura": "F000001",
            "monto_subtotal": "25.00",
            "monto_impuesto": "3.25",
            "monto_total": "28.25",
        },
    )
    db_session.commit()

    encontrada = repo.obtener(clinica.id_clinica, factura.id_factura)

    assert encontrada is not None
    assert encontrada.numero_factura == "F000001"


def test_obtener_de_otra_clinica_devuelve_none(db_session):
    from app.repositories.factura_repository import FacturaRepository
    from app.models import Clinica

    clinica, paciente = _clinica_y_paciente(db_session)
    otra_clinica = Clinica(nombre="Dental Dos")
    db_session.add(otra_clinica)
    db_session.flush()

    repo = FacturaRepository(db_session)
    factura = repo.crear(
        clinica.id_clinica,
        {
            "id_paciente": paciente.id_paciente,
            "numero_factura": "F000001",
            "monto_subtotal": "25.00",
            "monto_impuesto": "3.25",
            "monto_total": "28.25",
        },
    )
    db_session.commit()

    assert repo.obtener(otra_clinica.id_clinica, factura.id_factura) is None


def test_listar_filtra_por_paciente_y_doctor(db_session):
    from app.models import Doctor, RolUsuario, Usuario
    from app.repositories.factura_repository import FacturaRepository

    clinica, paciente = _clinica_y_paciente(db_session)
    usuario = Usuario(id_clinica=clinica.id_clinica, username="dra.perez", password_hash="x", rol=RolUsuario.DOCTOR)
    db_session.add(usuario)
    db_session.flush()
    doctor = Doctor(id_clinica=clinica.id_clinica, id_usuario=usuario.id_usuario, nombre="Marta", apellido="Perez", telefono="70003344")
    db_session.add(doctor)
    db_session.flush()

    repo = FacturaRepository(db_session)
    repo.crear(
        clinica.id_clinica,
        {
            "id_paciente": paciente.id_paciente,
            "id_doctor": doctor.id_doctor,
            "numero_factura": "F000001",
            "monto_subtotal": "25.00",
            "monto_impuesto": "3.25",
            "monto_total": "28.25",
        },
    )
    repo.crear(
        clinica.id_clinica,
        {
            "id_paciente": paciente.id_paciente,
            "numero_factura": "F000002",
            "monto_subtotal": "10.00",
            "monto_impuesto": "1.30",
            "monto_total": "11.30",
        },
    )
    db_session.commit()

    solo_del_doctor = repo.listar(clinica.id_clinica, id_doctor=doctor.id_doctor)

    assert len(solo_del_doctor) == 1
    assert solo_del_doctor[0].numero_factura == "F000001"


def test_eliminar_lanza_not_implemented(db_session):
    import pytest
    from app.repositories.factura_repository import FacturaRepository

    with pytest.raises(NotImplementedError):
        FacturaRepository(db_session).eliminar(1, 1)
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_factura_repository.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.repositories.factura_repository'`

- [ ] **Step 3: Implementar `app/repositories/factura_repository.py`**

```python
from sqlalchemy import select

from app.models import Factura
from app.repositories.base import BaseRepository


class FacturaRepository(BaseRepository[Factura]):
    def listar(
        self, id_clinica: int, id_paciente: int | None = None, id_doctor: int | None = None
    ) -> list[Factura]:
        stmt = select(Factura).where(Factura.id_clinica == id_clinica)
        if id_paciente is not None:
            stmt = stmt.where(Factura.id_paciente == id_paciente)
        if id_doctor is not None:
            stmt = stmt.where(Factura.id_doctor == id_doctor)
        stmt = stmt.order_by(Factura.fecha_emision.desc())
        return list(self.db.execute(stmt).scalars().all())

    def obtener(self, id_clinica: int, id_: int) -> Factura | None:
        stmt = select(Factura).where(Factura.id_factura == id_, Factura.id_clinica == id_clinica)
        return self.db.execute(stmt).scalars().first()

    def crear(self, id_clinica: int, data: dict) -> Factura:
        factura = Factura(id_clinica=id_clinica, **data)
        self.db.add(factura)
        self.db.flush()
        return factura

    def actualizar(self, id_clinica: int, id_: int, data: dict) -> Factura | None:
        factura = self.obtener(id_clinica, id_)
        if factura is None:
            return None
        for campo, valor in data.items():
            setattr(factura, campo, valor)
        self.db.flush()
        return factura

    def eliminar(self, id_clinica: int, id_: int) -> bool:
        raise NotImplementedError(
            "Las facturas no se borran: usar FacturaService.anular()"
        )

    def obtener_por_plan(self, id_clinica: int, id_plan: int) -> Factura | None:
        stmt = select(Factura).where(
            Factura.id_clinica == id_clinica, Factura.id_plan == id_plan
        )
        return self.db.execute(stmt).scalars().first()
```

- [ ] **Step 4: Ejecutar el test y verificar que pasa**

Run: `.venv/Scripts/python.exe -m pytest tests/test_factura_repository.py -v`
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/repositories/factura_repository.py backend/tests/test_factura_repository.py
git commit -m "feat(backend): FacturaRepository"
```

---

### Task 3: `FacturaDetalleRepository`

**Files:**
- Create: `backend/app/repositories/factura_detalle_repository.py`
- Create: `backend/tests/test_factura_detalle_repository.py`
- Modify: `backend/tests/factories.py` (+ `crear_tratamiento`)

**Interfaces:**
- Consumes: `FacturaRepository` (Task 2).
- Produces: `FacturaDetalleRepository.listar_de_factura(id_clinica, id_factura) -> list[FacturaDetalle]`, `.crear(id_factura, data) -> FacturaDetalle`. Usado por Task 5 en adelante. `crear_tratamiento(db, id_clinica, **campos)` en `factories.py`.

- [ ] **Step 1: Agregar el factory helper**

Agregar al final de `backend/tests/factories.py`:

```python
def crear_tratamiento(db, id_clinica, **campos):
    from app.models import Tratamiento

    datos = {"nombre": "Limpieza dental", "precio": "25.00"}
    datos.update(campos)
    tratamiento = Tratamiento(id_clinica=id_clinica, **datos)
    db.add(tratamiento)
    db.flush()
    return tratamiento
```

- [ ] **Step 2: Escribir el test (falla primero)**

`backend/tests/test_factura_detalle_repository.py`:

```python
from tests.factories import crear_clinica, crear_paciente, crear_tratamiento


def _crear_factura(db, id_clinica, id_paciente):
    from app.repositories.factura_repository import FacturaRepository

    return FacturaRepository(db).crear(
        id_clinica,
        {
            "id_paciente": id_paciente,
            "numero_factura": "F000001",
            "monto_subtotal": "25.00",
            "monto_impuesto": "3.25",
            "monto_total": "28.25",
        },
    )


def test_crear_y_listar_de_factura(db_session):
    from app.repositories.factura_detalle_repository import FacturaDetalleRepository

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica)
    factura = _crear_factura(db_session, clinica.id_clinica, paciente.id_paciente)

    repo = FacturaDetalleRepository(db_session)
    repo.crear(
        factura.id_factura,
        {"id_tratamiento": tratamiento.id_tratamiento, "cantidad": 2, "precio_unitario": "25.00"},
    )
    db_session.commit()

    detalles = repo.listar_de_factura(clinica.id_clinica, factura.id_factura)

    assert len(detalles) == 1
    assert detalles[0].cantidad == 2


def test_listar_de_factura_de_otra_clinica_devuelve_vacio(db_session):
    from app.models import Clinica
    from app.repositories.factura_detalle_repository import FacturaDetalleRepository

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica)
    factura = _crear_factura(db_session, clinica.id_clinica, paciente.id_paciente)

    repo = FacturaDetalleRepository(db_session)
    repo.crear(
        factura.id_factura,
        {"id_tratamiento": tratamiento.id_tratamiento, "cantidad": 1, "precio_unitario": "25.00"},
    )
    db_session.commit()

    otra_clinica = Clinica(nombre="Dental Dos")
    db_session.add(otra_clinica)
    db_session.commit()

    assert repo.listar_de_factura(otra_clinica.id_clinica, factura.id_factura) == []
```

- [ ] **Step 3: Ejecutar el test y verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_factura_detalle_repository.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.repositories.factura_detalle_repository'`

- [ ] **Step 4: Implementar `app/repositories/factura_detalle_repository.py`**

```python
from sqlalchemy import select

from app.models import Factura, FacturaDetalle


class FacturaDetalleRepository:
    """No hereda BaseRepository: la llave de FacturaDetalle no incluye
    id_clinica, el aislamiento lo garantiza el JOIN contra Factura -- mismo
    criterio que PlanTratamientoDetalleRepository (Modulo 5).
    """

    def __init__(self, db):
        self.db = db

    def listar_de_factura(self, id_clinica: int, id_factura: int) -> list[FacturaDetalle]:
        stmt = (
            select(FacturaDetalle)
            .join(Factura, FacturaDetalle.id_factura == Factura.id_factura)
            .where(Factura.id_clinica == id_clinica, FacturaDetalle.id_factura == id_factura)
            .order_by(FacturaDetalle.id_detalle)
        )
        return list(self.db.execute(stmt).scalars().all())

    def crear(self, id_factura: int, data: dict) -> FacturaDetalle:
        detalle = FacturaDetalle(id_factura=id_factura, **data)
        self.db.add(detalle)
        self.db.flush()
        return detalle
```

- [ ] **Step 5: Ejecutar el test y verificar que pasa**

Run: `.venv/Scripts/python.exe -m pytest tests/test_factura_detalle_repository.py -v`
Expected: `2 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/app/repositories/factura_detalle_repository.py backend/tests/test_factura_detalle_repository.py backend/tests/factories.py
git commit -m "feat(backend): FacturaDetalleRepository"
```

---

### Task 4: `PagoRepository`

**Files:**
- Create: `backend/app/repositories/pago_repository.py`
- Create: `backend/tests/test_pago_repository.py`
- Modify: `backend/tests/factories.py` (+ `crear_metodo_pago`)

**Interfaces:**
- Consumes: `FacturaRepository` (Task 2).
- Produces: `PagoRepository.listar_de_factura(id_clinica, id_factura) -> list[Pago]`,
  `.crear(id_factura, data) -> Pago`, `.suma_pagada(id_clinica, id_factura) -> Decimal`. Usado por
  Task 7 (`FacturaService.anular`) y Task 8 (`PagoService`).

- [ ] **Step 1: Agregar el factory helper**

Agregar al final de `backend/tests/factories.py`:

```python
def crear_metodo_pago(db, id_clinica, **campos):
    from app.models import MetodoPago

    datos = {"nombre": "Efectivo"}
    datos.update(campos)
    metodo = MetodoPago(id_clinica=id_clinica, **datos)
    db.add(metodo)
    db.flush()
    return metodo
```

- [ ] **Step 2: Escribir el test (falla primero)**

`backend/tests/test_pago_repository.py`:

```python
from decimal import Decimal

from tests.factories import crear_clinica, crear_metodo_pago, crear_paciente


def _crear_factura(db, id_clinica, id_paciente, monto_total="28.25"):
    from app.repositories.factura_repository import FacturaRepository

    return FacturaRepository(db).crear(
        id_clinica,
        {
            "id_paciente": id_paciente,
            "numero_factura": "F000001",
            "monto_subtotal": "25.00",
            "monto_impuesto": "3.25",
            "monto_total": monto_total,
        },
    )


def test_crear_y_listar_pagos(db_session):
    from app.repositories.pago_repository import PagoRepository

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    metodo = crear_metodo_pago(db_session, clinica.id_clinica)
    factura = _crear_factura(db_session, clinica.id_clinica, paciente.id_paciente)

    repo = PagoRepository(db_session)
    repo.crear(factura.id_factura, {"id_metodo_pago": metodo.id_metodo_pago, "monto": "10.00"})
    repo.crear(factura.id_factura, {"id_metodo_pago": metodo.id_metodo_pago, "monto": "18.25"})
    db_session.commit()

    pagos = repo.listar_de_factura(clinica.id_clinica, factura.id_factura)

    assert len(pagos) == 2


def test_suma_pagada(db_session):
    from app.repositories.pago_repository import PagoRepository

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    metodo = crear_metodo_pago(db_session, clinica.id_clinica)
    factura = _crear_factura(db_session, clinica.id_clinica, paciente.id_paciente)

    repo = PagoRepository(db_session)
    repo.crear(factura.id_factura, {"id_metodo_pago": metodo.id_metodo_pago, "monto": "10.00"})
    repo.crear(factura.id_factura, {"id_metodo_pago": metodo.id_metodo_pago, "monto": "18.25"})
    db_session.commit()

    assert repo.suma_pagada(clinica.id_clinica, factura.id_factura) == Decimal("28.25")


def test_suma_pagada_sin_pagos_es_cero(db_session):
    from app.repositories.pago_repository import PagoRepository

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    factura = _crear_factura(db_session, clinica.id_clinica, paciente.id_paciente)
    db_session.commit()

    assert PagoRepository(db_session).suma_pagada(clinica.id_clinica, factura.id_factura) == Decimal("0.00")
```

- [ ] **Step 3: Ejecutar el test y verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_pago_repository.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.repositories.pago_repository'`

- [ ] **Step 4: Implementar `app/repositories/pago_repository.py`**

```python
from decimal import Decimal

from sqlalchemy import select

from app.models import Factura, Pago


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
```

- [ ] **Step 5: Ejecutar el test y verificar que pasa**

Run: `.venv/Scripts/python.exe -m pytest tests/test_pago_repository.py -v`
Expected: `3 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/app/repositories/pago_repository.py backend/tests/test_pago_repository.py backend/tests/factories.py
git commit -m "feat(backend): PagoRepository"
```

---

### Task 5: `FacturaService.generar_desde_presupuesto`

**Files:**
- Create: `backend/app/services/factura_service.py`
- Create: `backend/tests/test_factura_service.py`
- Modify: `backend/tests/factories.py` (+ `crear_plan_aceptado_con_presupuesto`)

**Interfaces:**
- Consumes: `FacturaRepository`, `FacturaDetalleRepository`, `ConfiguracionClinicaRepository`
  (`app.repositories.configuracion_repository`, ya existe desde el Módulo 3),
  `PlanTratamientoRepository`, `PlanTratamientoDetalleRepository`, `PresupuestoRepository`
  (Módulo 5).
- Produces: `FacturaService.generar_desde_presupuesto(id_clinica, id_plan, id_asistente=None) -> Factura | None` (lanza `PresupuestoNoAceptadoError`). Método privado `_emitir(...)` reutilizado por
  Task 6 (`crear_suelta`).

- [ ] **Step 1: Agregar el factory helper**

Agregar al final de `backend/tests/factories.py`:

```python
def crear_plan_aceptado_con_presupuesto(db, id_clinica, id_paciente, id_doctor, id_tratamiento, cantidad=1):
    """Arma un PlanTratamiento con un detalle y su Presupuesto ya en estado
    ACEPTADO -- el punto de partida que FacturaService.generar_desde_presupuesto
    necesita.
    """
    from decimal import Decimal

    from app.models import (
        EstadoPresupuesto,
        PlanTratamiento,
        PlanTratamientoDetalle,
        Presupuesto,
        Tratamiento,
    )

    plan = PlanTratamiento(id_clinica=id_clinica, id_paciente=id_paciente, id_doctor=id_doctor)
    db.add(plan)
    db.flush()

    tratamiento = db.get(Tratamiento, id_tratamiento)
    detalle = PlanTratamientoDetalle(
        id_plan=plan.id_plan,
        id_tratamiento=id_tratamiento,
        cantidad=cantidad,
        precio_unitario=tratamiento.precio,
    )
    db.add(detalle)

    presupuesto = Presupuesto(
        id_clinica=id_clinica,
        id_plan=plan.id_plan,
        monto_total=str(Decimal(str(tratamiento.precio)) * cantidad),
        estado=EstadoPresupuesto.ACEPTADO,
    )
    db.add(presupuesto)
    db.flush()
    return plan, detalle, presupuesto
```

- [ ] **Step 2: Escribir el test (falla primero)**

`backend/tests/test_factura_service.py`:

```python
from decimal import Decimal

import pytest

from tests.factories import (
    crear_clinica,
    crear_doctor,
    crear_paciente,
    crear_plan_aceptado_con_presupuesto,
    crear_tratamiento,
)


def test_generar_desde_presupuesto_calcula_impuesto_y_numera(db_session):
    from app.services.factura_service import FacturaService

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica, precio="100.00")
    plan, detalle, presupuesto = crear_plan_aceptado_con_presupuesto(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor,
        tratamiento.id_tratamiento, cantidad=2,
    )
    db_session.commit()

    factura = FacturaService(db_session).generar_desde_presupuesto(clinica.id_clinica, plan.id_plan)

    assert factura.numero_factura == "F000001"
    assert Decimal(str(factura.monto_subtotal)) == Decimal("200.00")
    # ConfiguracionClinica.porcentaje_impuesto default = 13.00
    assert Decimal(str(factura.monto_impuesto)) == Decimal("26.00")
    assert Decimal(str(factura.monto_total)) == Decimal("226.00")
    assert factura.id_paciente == paciente.id_paciente
    assert factura.id_doctor == doctor.id_doctor
    assert factura.id_plan == plan.id_plan


def test_generar_desde_presupuesto_copia_las_lineas_del_plan(db_session):
    from app.repositories.factura_detalle_repository import FacturaDetalleRepository
    from app.services.factura_service import FacturaService

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica, precio="50.00")
    plan, _, _ = crear_plan_aceptado_con_presupuesto(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor,
        tratamiento.id_tratamiento, cantidad=1,
    )
    db_session.commit()

    factura = FacturaService(db_session).generar_desde_presupuesto(clinica.id_clinica, plan.id_plan)

    detalles = FacturaDetalleRepository(db_session).listar_de_factura(clinica.id_clinica, factura.id_factura)
    assert len(detalles) == 1
    assert detalles[0].id_tratamiento == tratamiento.id_tratamiento
    assert Decimal(str(detalles[0].precio_unitario)) == Decimal("50.00")


def test_generar_desde_presupuesto_incrementa_el_correlativo(db_session):
    from app.services.factura_service import FacturaService

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica, precio="10.00")
    plan_1, _, _ = crear_plan_aceptado_con_presupuesto(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor, tratamiento.id_tratamiento,
    )
    plan_2, _, _ = crear_plan_aceptado_con_presupuesto(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor, tratamiento.id_tratamiento,
    )
    db_session.commit()

    servicio = FacturaService(db_session)
    factura_1 = servicio.generar_desde_presupuesto(clinica.id_clinica, plan_1.id_plan)
    factura_2 = servicio.generar_desde_presupuesto(clinica.id_clinica, plan_2.id_plan)

    assert factura_1.numero_factura == "F000001"
    assert factura_2.numero_factura == "F000002"


def test_generar_desde_presupuesto_sin_aceptar_lanza_error(db_session):
    from app.exceptions import PresupuestoNoAceptadoError
    from app.models import EstadoPresupuesto
    from app.services.factura_service import FacturaService

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica)
    plan, _, presupuesto = crear_plan_aceptado_con_presupuesto(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor, tratamiento.id_tratamiento,
    )
    presupuesto.estado = EstadoPresupuesto.VIGENTE
    db_session.commit()

    with pytest.raises(PresupuestoNoAceptadoError):
        FacturaService(db_session).generar_desde_presupuesto(clinica.id_clinica, plan.id_plan)


def test_generar_desde_presupuesto_plan_inexistente_devuelve_none(db_session):
    from app.services.factura_service import FacturaService

    clinica = crear_clinica(db_session)

    assert FacturaService(db_session).generar_desde_presupuesto(clinica.id_clinica, 999) is None
```

- [ ] **Step 3: Ejecutar el test y verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_factura_service.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.services.factura_service'`

- [ ] **Step 4: Implementar `app/services/factura_service.py`**

```python
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.exceptions import PresupuestoNoAceptadoError, ReferenciaInvalidaError
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
```

- [ ] **Step 5: Ejecutar el test y verificar que pasa**

Run: `.venv/Scripts/python.exe -m pytest tests/test_factura_service.py -v`
Expected: `5 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/factura_service.py backend/tests/test_factura_service.py backend/tests/factories.py
git commit -m "feat(backend): FacturaService.generar_desde_presupuesto"
```

---

### Task 6: `FacturaService.crear_suelta`

**Files:**
- Modify: `backend/app/services/factura_service.py`
- Modify: `backend/tests/test_factura_service.py`

**Interfaces:**
- Consumes: `TratamientoRepository` (Módulo 5, ya existe), `_emitir` (Task 5).
- Produces: `FacturaService.crear_suelta(id_clinica, id_paciente, id_doctor, lineas, id_asistente=None) -> Factura` (`lineas: list[dict]` con `id_tratamiento`/`cantidad`; lanza `ReferenciaInvalidaError` si un tratamiento no existe en la clínica).

- [ ] **Step 1: Escribir el test (falla primero)**

Agregar al final de `backend/tests/test_factura_service.py`:

```python
def test_crear_suelta_calcula_desde_el_catalogo(db_session):
    from app.services.factura_service import FacturaService

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica, precio="40.00")
    db_session.commit()

    factura = FacturaService(db_session).crear_suelta(
        clinica.id_clinica, paciente.id_paciente, None,
        [{"id_tratamiento": tratamiento.id_tratamiento, "cantidad": 3}],
    )

    assert Decimal(str(factura.monto_subtotal)) == Decimal("120.00")
    assert factura.id_plan is None
    assert factura.numero_factura == "F000001"


def test_crear_suelta_con_tratamiento_de_otra_clinica_lanza_error(db_session):
    from app.exceptions import ReferenciaInvalidaError
    from app.models import Clinica
    from app.services.factura_service import FacturaService

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    otra_clinica = Clinica(nombre="Dental Dos")
    db_session.add(otra_clinica)
    db_session.flush()
    tratamiento_ajeno = crear_tratamiento(db_session, otra_clinica.id_clinica)
    db_session.commit()

    with pytest.raises(ReferenciaInvalidaError):
        FacturaService(db_session).crear_suelta(
            clinica.id_clinica, paciente.id_paciente, None,
            [{"id_tratamiento": tratamiento_ajeno.id_tratamiento, "cantidad": 1}],
        )
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_factura_service.py -v`
Expected: FAIL con `AttributeError: 'FacturaService' object has no attribute 'crear_suelta'`

- [ ] **Step 3: Agregar el método a `app/services/factura_service.py`**

Agregar el import al inicio del archivo:

```python
from app.repositories.tratamiento_repository import TratamientoRepository
```

(ya está en la lista de imports del Task 5 -- si seguiste el plan en orden, confirmá que ya
está antes de seguir.)

Agregar el método a la clase `FacturaService`, después de `generar_desde_presupuesto`:

```python
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
```

- [ ] **Step 4: Ejecutar el test y verificar que pasa**

Run: `.venv/Scripts/python.exe -m pytest tests/test_factura_service.py -v`
Expected: `7 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/factura_service.py backend/tests/test_factura_service.py
git commit -m "feat(backend): FacturaService.crear_suelta"
```

---

### Task 7: `FacturaService.anular`

**Files:**
- Modify: `backend/app/services/factura_service.py`
- Modify: `backend/tests/test_factura_service.py`

**Interfaces:**
- Consumes: `self.pagos.suma_pagada` (Task 4).
- Produces: `FacturaService.anular(id_clinica, id_factura) -> Factura | None` (lanza `FacturaConPagosError`).

- [ ] **Step 1: Escribir el test (falla primero)**

Agregar al final de `backend/tests/test_factura_service.py`:

```python
def test_anular_sin_pagos(db_session):
    from app.models import EstadoFactura
    from app.services.factura_service import FacturaService

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica)
    db_session.commit()

    servicio = FacturaService(db_session)
    factura = servicio.crear_suelta(
        clinica.id_clinica, paciente.id_paciente, None,
        [{"id_tratamiento": tratamiento.id_tratamiento, "cantidad": 1}],
    )

    anulada = servicio.anular(clinica.id_clinica, factura.id_factura)

    assert anulada.estado == EstadoFactura.ANULADA


def test_anular_con_pagos_lanza_error(db_session):
    from app.exceptions import FacturaConPagosError
    from app.repositories.pago_repository import PagoRepository
    from app.services.factura_service import FacturaService
    from tests.factories import crear_metodo_pago

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica)
    metodo = crear_metodo_pago(db_session, clinica.id_clinica)
    db_session.commit()

    servicio = FacturaService(db_session)
    factura = servicio.crear_suelta(
        clinica.id_clinica, paciente.id_paciente, None,
        [{"id_tratamiento": tratamiento.id_tratamiento, "cantidad": 1}],
    )
    PagoRepository(db_session).crear(
        factura.id_factura, {"id_metodo_pago": metodo.id_metodo_pago, "monto": "10.00"}
    )
    db_session.commit()

    with pytest.raises(FacturaConPagosError):
        servicio.anular(clinica.id_clinica, factura.id_factura)


def test_anular_factura_inexistente_devuelve_none(db_session):
    from app.services.factura_service import FacturaService

    clinica = crear_clinica(db_session)

    assert FacturaService(db_session).anular(clinica.id_clinica, 999) is None
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_factura_service.py -v`
Expected: FAIL con `AttributeError: 'FacturaService' object has no attribute 'anular'`

- [ ] **Step 3: Agregar el método**

Agregar el import al inicio de `app/services/factura_service.py`:

```python
from app.exceptions import FacturaConPagosError, PresupuestoNoAceptadoError, ReferenciaInvalidaError
```

(reemplaza la línea de import de excepciones existente, agregando `FacturaConPagosError`.)

Agregar el método a la clase `FacturaService`, después de `crear_suelta`:

```python
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
```

- [ ] **Step 4: Ejecutar el test y verificar que pasa**

Run: `.venv/Scripts/python.exe -m pytest tests/test_factura_service.py -v`
Expected: `10 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/factura_service.py backend/tests/test_factura_service.py
git commit -m "feat(backend): FacturaService.anular"
```

---

### Task 8: `PagoService.registrar_pago`

**Files:**
- Create: `backend/app/services/pago_service.py`
- Create: `backend/tests/test_pago_service.py`

**Interfaces:**
- Consumes: `FacturaRepository`, `PagoRepository`.
- Produces: `PagoService.registrar_pago(id_clinica, id_factura, monto, id_metodo_pago, id_asistente=None) -> Pago | None` (lanza `FacturaAnuladaError`, `PagoExcedeSaldoError`).

- [ ] **Step 1: Escribir el test (falla primero)**

`backend/tests/test_pago_service.py`:

```python
from decimal import Decimal

import pytest

from tests.factories import crear_clinica, crear_metodo_pago, crear_paciente, crear_tratamiento


def _crear_factura_suelta(db, id_clinica, id_paciente, precio="100.00"):
    from app.services.factura_service import FacturaService

    tratamiento = crear_tratamiento(db, id_clinica, precio=precio)
    db.commit()
    return FacturaService(db).crear_suelta(
        id_clinica, id_paciente, None, [{"id_tratamiento": tratamiento.id_tratamiento, "cantidad": 1}]
    )


def test_registrar_pago_parcial_deja_la_factura_en_parcial(db_session):
    from app.models import EstadoFactura
    from app.services.pago_service import PagoService

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    metodo = crear_metodo_pago(db_session, clinica.id_clinica)
    factura = _crear_factura_suelta(db_session, clinica.id_clinica, paciente.id_paciente, precio="100.00")
    # monto_total = 113.00 (100 + 13% de impuesto)

    pago = PagoService(db_session).registrar_pago(
        clinica.id_clinica, factura.id_factura, Decimal("50.00"), metodo.id_metodo_pago
    )

    assert pago.id_pago is not None
    db_session.refresh(factura)
    assert factura.estado == EstadoFactura.PARCIAL


def test_registrar_pago_que_completa_el_saldo_deja_la_factura_pagada(db_session):
    from app.models import EstadoFactura
    from app.services.pago_service import PagoService

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    metodo = crear_metodo_pago(db_session, clinica.id_clinica)
    factura = _crear_factura_suelta(db_session, clinica.id_clinica, paciente.id_paciente, precio="100.00")

    servicio = PagoService(db_session)
    servicio.registrar_pago(clinica.id_clinica, factura.id_factura, Decimal("113.00"), metodo.id_metodo_pago)

    db_session.refresh(factura)
    assert factura.estado == EstadoFactura.PAGADA


def test_registrar_pago_que_excede_el_saldo_lanza_error(db_session):
    from app.exceptions import PagoExcedeSaldoError
    from app.services.pago_service import PagoService

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    metodo = crear_metodo_pago(db_session, clinica.id_clinica)
    factura = _crear_factura_suelta(db_session, clinica.id_clinica, paciente.id_paciente, precio="100.00")

    with pytest.raises(PagoExcedeSaldoError):
        PagoService(db_session).registrar_pago(
            clinica.id_clinica, factura.id_factura, Decimal("999.00"), metodo.id_metodo_pago
        )


def test_registrar_pago_sobre_factura_anulada_lanza_error(db_session):
    from app.exceptions import FacturaAnuladaError
    from app.services.factura_service import FacturaService
    from app.services.pago_service import PagoService

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    metodo = crear_metodo_pago(db_session, clinica.id_clinica)
    factura = _crear_factura_suelta(db_session, clinica.id_clinica, paciente.id_paciente, precio="100.00")
    FacturaService(db_session).anular(clinica.id_clinica, factura.id_factura)

    with pytest.raises(FacturaAnuladaError):
        PagoService(db_session).registrar_pago(
            clinica.id_clinica, factura.id_factura, Decimal("10.00"), metodo.id_metodo_pago
        )


def test_registrar_pago_factura_inexistente_devuelve_none(db_session):
    from app.services.pago_service import PagoService

    clinica = crear_clinica(db_session)
    metodo = crear_metodo_pago(db_session, clinica.id_clinica)
    db_session.commit()

    resultado = PagoService(db_session).registrar_pago(
        clinica.id_clinica, 999, Decimal("10.00"), metodo.id_metodo_pago
    )

    assert resultado is None
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_pago_service.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.services.pago_service'`

- [ ] **Step 3: Implementar `app/services/pago_service.py`**

```python
from decimal import Decimal

from sqlalchemy.orm import Session

from app.exceptions import FacturaAnuladaError, PagoExcedeSaldoError
from app.models import EstadoFactura, Pago
from app.repositories.factura_repository import FacturaRepository
from app.repositories.pago_repository import PagoRepository


class PagoService:
    def __init__(self, db: Session):
        self.db = db
        self.facturas = FacturaRepository(db)
        self.pagos = PagoRepository(db)

    def registrar_pago(
        self,
        id_clinica: int,
        id_factura: int,
        monto: Decimal,
        id_metodo_pago: int,
        id_asistente: int | None = None,
    ) -> Pago | None:
        factura = self.facturas.obtener(id_clinica, id_factura)
        if factura is None:
            return None
        if factura.estado == EstadoFactura.ANULADA:
            raise FacturaAnuladaError("No se pueden registrar pagos sobre una factura anulada")

        ya_pagado = self.pagos.suma_pagada(id_clinica, id_factura)
        saldo_pendiente = Decimal(str(factura.monto_total)) - ya_pagado
        monto_decimal = Decimal(str(monto))
        if monto_decimal > saldo_pendiente:
            raise PagoExcedeSaldoError(
                f"El pago ({monto_decimal}) excede el saldo pendiente ({saldo_pendiente})"
            )

        pago = self.pagos.crear(
            id_factura,
            {
                "id_metodo_pago": id_metodo_pago,
                "id_asistente": id_asistente,
                "monto": str(monto_decimal),
            },
        )

        nuevo_pagado = ya_pagado + monto_decimal
        factura.estado = (
            EstadoFactura.PAGADA
            if nuevo_pagado >= Decimal(str(factura.monto_total))
            else EstadoFactura.PARCIAL
        )
        self.db.commit()
        return pago
```

- [ ] **Step 4: Ejecutar el test y verificar que pasa**

Run: `.venv/Scripts/python.exe -m pytest tests/test_pago_service.py -v`
Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/pago_service.py backend/tests/test_pago_service.py
git commit -m "feat(backend): PagoService.registrar_pago"
```

---

### Task 9: Schemas

**Files:**
- Create: `backend/app/schemas/factura.py`

**Interfaces:**
- Produces: `LineaFacturaCreate`, `FacturaCreate`, `FacturaDetalleResponse`, `FacturaResponse`,
  `PagoCreate`, `PagoResponse`. Usados por Task 10.

Este task no lleva ciclo TDD propio (son schemas Pydantic sin lógica propia que testear en
aislamiento) — se verifica indirectamente en Task 10 a través de las rutas. Sí hay que crear el
archivo antes de Task 10.

- [ ] **Step 1: Implementar `app/schemas/factura.py`**

```python
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models import EstadoFactura


class LineaFacturaCreate(BaseModel):
    id_tratamiento: int = Field(gt=0)
    cantidad: int = Field(default=1, ge=1)


class FacturaCreate(BaseModel):
    id_paciente: int = Field(gt=0)
    id_doctor: int | None = None
    lineas: list[LineaFacturaCreate] = Field(min_length=1)


class FacturaDetalleResponse(BaseModel):
    id_detalle: int
    id_factura: int
    id_tratamiento: int
    cantidad: int
    precio_unitario: Decimal

    model_config = {"from_attributes": True}


class FacturaResponse(BaseModel):
    id_factura: int
    id_paciente: int
    id_doctor: int | None
    id_asistente: int | None
    id_plan: int | None
    numero_factura: str
    monto_subtotal: Decimal
    monto_impuesto: Decimal
    monto_total: Decimal
    estado: EstadoFactura
    fecha_emision: datetime

    model_config = {"from_attributes": True}


class PagoCreate(BaseModel):
    id_metodo_pago: int = Field(gt=0)
    monto: Decimal = Field(gt=0)


class PagoResponse(BaseModel):
    id_pago: int
    id_factura: int
    id_metodo_pago: int
    id_asistente: int | None
    monto: Decimal
    fecha_pago: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Verificar que importa sin errores**

Run: `.venv/Scripts/python.exe -c "from app.schemas.factura import FacturaCreate, FacturaResponse, PagoCreate, PagoResponse; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/factura.py
git commit -m "feat(backend): schemas de Factura y Pago"
```

---

### Task 10: Endpoints, registro en la app, y tests end-to-end

**Files:**
- Create: `backend/app/api/routes/facturas.py`
- Modify: `backend/app/api/routes/planes_tratamiento.py` (+ `POST /{id_plan}/factura`)
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_facturas_routes.py`

**Interfaces:**
- Consumes: `FacturaService`, `PagoService`, `FacturaRepository`, `PagoRepository`,
  `AsistenteRepository.obtener_por_usuario` (ya existe), `get_doctor_actual` (Módulo 4),
  `resolve_clinica_id`, `require_roles` (Módulo 1).
- Produces: endpoints `POST /planes-tratamiento/{id_plan}/factura`, `POST /facturas`,
  `GET /facturas`, `GET /facturas/{id_factura}`, `PATCH /facturas/{id_factura}/anular`,
  `POST /facturas/{id_factura}/pagos`, `GET /facturas/{id_factura}/pagos`.

- [ ] **Step 1: Escribir los tests (fallan primero)**

`backend/tests/test_facturas_routes.py`:

```python
from tests.factories import (
    crear_clinica,
    crear_doctor,
    crear_metodo_pago,
    crear_paciente,
    crear_plan_aceptado_con_presupuesto,
    crear_tratamiento,
    headers_de,
)


def test_crear_factura_suelta_requiere_login(client):
    respuesta = client.post("/facturas", json={"id_paciente": 1, "lineas": []})

    assert respuesta.status_code == 401


def test_doctor_no_puede_crear_factura(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica)
    db_session.commit()

    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.DOCTOR)

    respuesta = client.post(
        "/facturas",
        headers=headers,
        json={
            "id_paciente": paciente.id_paciente,
            "lineas": [{"id_tratamiento": tratamiento.id_tratamiento, "cantidad": 1}],
        },
    )

    assert respuesta.status_code == 403


def test_asistente_crea_factura_suelta(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica, precio="40.00")
    db_session.commit()

    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.ASISTENTE)

    respuesta = client.post(
        "/facturas",
        headers=headers,
        json={
            "id_paciente": paciente.id_paciente,
            "lineas": [{"id_tratamiento": tratamiento.id_tratamiento, "cantidad": 2}],
        },
    )

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["numero_factura"] == "F000001"
    assert cuerpo["monto_subtotal"] == "80.00"


def test_generar_factura_desde_plan(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica, precio="100.00")
    plan, _, _ = crear_plan_aceptado_con_presupuesto(
        db_session, clinica.id_clinica, paciente.id_paciente, doctor.id_doctor,
        tratamiento.id_tratamiento,
    )
    db_session.commit()

    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.ASISTENTE)

    respuesta = client.post(f"/planes-tratamiento/{plan.id_plan}/factura", headers=headers)

    assert respuesta.status_code == 201
    assert respuesta.json()["id_plan"] == plan.id_plan


def test_generar_factura_desde_plan_sin_presupuesto_aceptado_da_409(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    db_session.commit()

    from app.models import PlanTratamiento

    plan = PlanTratamiento(id_clinica=clinica.id_clinica, id_paciente=paciente.id_paciente, id_doctor=doctor.id_doctor)
    db_session.add(plan)
    db_session.commit()

    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.ASISTENTE)

    respuesta = client.post(f"/planes-tratamiento/{plan.id_plan}/factura", headers=headers)

    assert respuesta.status_code == 409


def test_doctor_solo_ve_sus_propias_facturas(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor_a = crear_doctor(db_session, clinica.id_clinica, username="dra.a")
    doctor_b = crear_doctor(db_session, clinica.id_clinica, username="dr.b")
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica, precio="20.00")
    db_session.commit()

    headers_asistente = headers_de(db_session, clinica.id_clinica, RolUsuario.ASISTENTE)
    client.post(
        "/facturas", headers=headers_asistente,
        json={
            "id_paciente": paciente.id_paciente, "id_doctor": doctor_a.id_doctor,
            "lineas": [{"id_tratamiento": tratamiento.id_tratamiento, "cantidad": 1}],
        },
    )
    creada_b = client.post(
        "/facturas", headers=headers_asistente,
        json={
            "id_paciente": paciente.id_paciente, "id_doctor": doctor_b.id_doctor,
            "lineas": [{"id_tratamiento": tratamiento.id_tratamiento, "cantidad": 1}],
        },
    ).json()

    from app.repositories.doctor_repository import DoctorRepository
    from app.security.jwt import create_access_token
    from datetime import timedelta

    perfil_b = DoctorRepository(db_session).obtener(clinica.id_clinica, doctor_b.id_doctor)
    token_doctor_b = create_access_token(
        data={"sub": str(perfil_b.id_usuario), "id_clinica": clinica.id_clinica, "rol": "doctor"},
        expires_delta=timedelta(minutes=10),
    )

    respuesta = client.get("/facturas", headers={"Authorization": f"Bearer {token_doctor_b}"})

    assert respuesta.status_code == 200
    numeros = [f["numero_factura"] for f in respuesta.json()]
    assert creada_b["numero_factura"] in numeros
    assert len(respuesta.json()) == 1


def test_anular_factura_sin_pagos(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica)
    db_session.commit()

    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.ASISTENTE)
    creada = client.post(
        "/facturas", headers=headers,
        json={
            "id_paciente": paciente.id_paciente,
            "lineas": [{"id_tratamiento": tratamiento.id_tratamiento, "cantidad": 1}],
        },
    ).json()

    respuesta = client.patch(f"/facturas/{creada['id_factura']}/anular", headers=headers)

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "anulada"


def test_registrar_pago_y_consultar_historial(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica, precio="100.00")
    metodo = crear_metodo_pago(db_session, clinica.id_clinica)
    db_session.commit()

    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.ASISTENTE)
    creada = client.post(
        "/facturas", headers=headers,
        json={
            "id_paciente": paciente.id_paciente,
            "lineas": [{"id_tratamiento": tratamiento.id_tratamiento, "cantidad": 1}],
        },
    ).json()

    pago = client.post(
        f"/facturas/{creada['id_factura']}/pagos", headers=headers,
        json={"id_metodo_pago": metodo.id_metodo_pago, "monto": "50.00"},
    )
    assert pago.status_code == 201

    historial = client.get(f"/facturas/{creada['id_factura']}/pagos", headers=headers)
    assert historial.status_code == 200
    assert len(historial.json()) == 1


def test_registrar_pago_que_excede_saldo_da_422(client, db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    tratamiento = crear_tratamiento(db_session, clinica.id_clinica, precio="10.00")
    metodo = crear_metodo_pago(db_session, clinica.id_clinica)
    db_session.commit()

    headers = headers_de(db_session, clinica.id_clinica, RolUsuario.ASISTENTE)
    creada = client.post(
        "/facturas", headers=headers,
        json={
            "id_paciente": paciente.id_paciente,
            "lineas": [{"id_tratamiento": tratamiento.id_tratamiento, "cantidad": 1}],
        },
    ).json()

    respuesta = client.post(
        f"/facturas/{creada['id_factura']}/pagos", headers=headers,
        json={"id_metodo_pago": metodo.id_metodo_pago, "monto": "9999.00"},
    )

    assert respuesta.status_code == 422
```

- [ ] **Step 2: Ejecutar los tests y verificar que fallan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_facturas_routes.py -v`
Expected: FAIL — todas con `404 Not Found` (el router de `/facturas` no existe todavía, y el
endpoint nuevo de `/planes-tratamiento/{id_plan}/factura` tampoco).

- [ ] **Step 3: Implementar `app/api/routes/facturas.py`**

```python
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
```

- [ ] **Step 4: Agregar el endpoint nuevo a `app/api/routes/planes_tratamiento.py`**

Agregar a la lista de imports (junto a los demás `from app.exceptions import ...`):

```python
from app.exceptions import (
    PresupuestoNoAceptadoError,
    ReferenciaInvalidaError,
    TransicionInvalidaError,
)
```

Agregar también:

```python
from app.api.deps import get_current_user, require_roles, resolve_clinica_id
from app.repositories.asistente_repository import AsistenteRepository
from app.schemas.factura import FacturaResponse
from app.services.factura_service import FacturaService
```

(`get_current_user` se suma a lo que ya importaba ese archivo desde `app.api.deps`.)

Ampliar la tupla de errores 409 (busca la línea `_A_409 = (TransicionInvalidaError,)` y
reemplázala):

```python
_A_409 = (TransicionInvalidaError, PresupuestoNoAceptadoError)
```

Agregar al final del archivo:

```python
@router.post(
    "/{id_plan}/factura",
    response_model=FacturaResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(ESCRITURA_PRESUPUESTO)],
)
def generar_factura(
    id_plan: int,
    id_clinica: int = Depends(resolve_clinica_id),
    usuario=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FacturaResponse:
    id_asistente = None
    if usuario.rol.value == "asistente":
        perfil = AsistenteRepository(db).obtener_por_usuario(usuario.id_usuario)
        id_asistente = perfil.id_asistente if perfil else None

    try:
        factura = FacturaService(db).generar_desde_presupuesto(id_clinica, id_plan, id_asistente)
    except (*_A_409, *_A_422) as error:
        raise _traducir(error)
    if factura is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    return FacturaResponse.model_validate(factura)
```

- [ ] **Step 5: Registrar el router en `app/main.py`**

Agregar el import:

```python
from app.api.routes.facturas import router as facturas_router
```

Agregar el registro (después de `app.include_router(recetas_router)` o el último que exista):

```python
app.include_router(facturas_router)
```

- [ ] **Step 6: Ejecutar los tests y verificar que pasan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_facturas_routes.py -v`
Expected: `10 passed`

- [ ] **Step 7: Correr toda la suite del proyecto**

Run: `.venv/Scripts/python.exe -m pytest -v`
Expected: todos los tests (Módulos 1 a 6) pasan, sin regresiones.

- [ ] **Step 8: Commit**

```bash
git add backend/app/api/routes/facturas.py backend/app/api/routes/planes_tratamiento.py backend/app/main.py backend/tests/test_facturas_routes.py
git commit -m "feat(backend): endpoints de facturacion y pagos - modulo 6"
```

---

## Self-Review

**Cobertura del spec:**
- Modelos `Factura`/`FacturaDetalle`/`Pago`, `EstadoFactura` con `values_callable` → Task 1 ✅
- Nota de "no es DTE" en el docstring del modelo, sin campos especulativos → Task 1 ✅
- `FacturaRepository` hereda `BaseRepository` → Task 2 ✅
- `FacturaDetalleRepository`/`PagoRepository` sin heredar, aislados por `JOIN` → Task 3, 4 ✅
- Generar desde presupuesto aceptado, copiar líneas, calcular impuesto, numeración atómica,
  transacción con rollback → Task 5 ✅ (rollback no se prueba con un test dedicado porque no hay
  forma de forzar un fallo a mitad de `_emitir` sin mockear — igual que Módulo 2, donde sí se
  mockeó `generar_password_temporal`; acá no hay un punto de fallo natural para inyectar, y forzar
  uno sería una prueba frágil que no vale la complejidad. El resto del método usa exactamente el
  patrón `try`/`except`/`rollback` ya probado en Módulo 2.)
- Facturar suelta con líneas estructuradas → Task 6 ✅
- Anular solo sin pagos → Task 7 ✅
- Pagos parciales, estado derivado, no exceder saldo → Task 8 ✅
- Endpoints, permisos (doctor solo lectura de las suyas, resto de roles según spec) → Task 10 ✅
- `POST /planes-tratamiento/{id_plan}/factura` anidado (no `/facturas/desde-plan/...`) → Task 10 ✅

**Placeholders:** revisado, no hay "TBD" ni pasos sin código real.

**Consistencia de tipos:** `FacturaService._emitir` devuelve `Factura` y es usado tanto por
`generar_desde_presupuesto` como por `crear_suelta` con la misma firma de `lineas: list[dict]`
(`id_tratamiento`, `cantidad`, `precio_unitario`) en Task 5 y Task 6. `PagoService.registrar_pago`
en Task 8 usa `FacturaRepository`/`PagoRepository` con las firmas exactas definidas en Task 2 y
Task 4. Las rutas de Task 10 consumen `FacturaService`/`PagoService` con las firmas exactas de
Task 5-8, y `FacturaResponse`/`PagoResponse` de Task 9 coinciden campo por campo con los modelos
de Task 1.
