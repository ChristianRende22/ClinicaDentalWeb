# Módulo 3: Parámetros por Clínica — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir los parámetros que cada clínica configura para sí misma — catálogos de
especialidades, consultorios y métodos de pago; horario de atención por día de la semana; y la
configuración operativa (duración de cita, IVA, numeración de facturas, reglas de cambio de cita).

**Architecture:** Sigue el patrón de los Módulos 1 y 2 (FastAPI + SQLAlchemy 2.0 + repositorios,
sin capa de service porque son CRUDs de una sola entidad). La novedad es `CatalogoRepository[T]`,
que implementa **una sola vez** el CRUD compartido por los tres catálogos y hereda de
`BaseRepository` — las tres subclases concretas solo declaran su modelo. Es además el primer
módulo que consume `resolve_clinica_id`, así que el patrón que quede acá es el que van a copiar
los Módulos 4 a 8.

**Tech Stack:** Mismo stack de los Módulos 1 y 2 (Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic,
MySQL 8, pytest, SQLite en memoria para tests). **Sin dependencias nuevas.**

**Spec de referencia:** `docs/superpowers/specs/2026-07-31-modulo-3-parametros-clinica-design.md`

## Global Constraints

- **Nunca ejecutar comandos `git`.** Ni `add`, ni `commit`, ni `push`. Los pasos marcados como
  *Punto de commit* son para que Meli los ejecute a mano; el agente solo se detiene ahí y avisa.
- Todos los comandos se corren con `backend/` como directorio de trabajo, usando el venv del
  Módulo 1: `.venv/Scripts/python.exe -m pytest ...`
- **TDD estricto:** test primero, verlo fallar por la razón correcta, después la implementación
  mínima. Nunca implementación antes del test.
- Todo enum nuevo de SQLAlchemy se declara con
  `values_callable=lambda enum_cls: [e.value for e in enum_cls]`. Sin eso SQLAlchemy persiste
  `LUNES` en vez de `lunes` y el bug **no aparece en SQLite**, solo contra MySQL real.
- Los valores del enum `DiaSemana` van **sin tilde** (`miercoles`, `sabado`) para evitar problemas
  de encoding en el tipo ENUM de MySQL.
- Las comparaciones case-insensitive de `nombre` usan `func.lower()` **explícito** en la query. No
  confiar en el collation: SQLite es case-sensitive por defecto, MySQL con `utf8mb4_general_ci` no.
- Los repositorios hacen `.flush()`, **nunca** `.commit()`. El `.commit()` lo hace la ruta.
- Ningún `HTTPException` en repositorios ni modelos. Las excepciones de dominio viven en
  `app/exceptions.py`; las rutas las traducen a HTTP.
- Nombres de negocio en español. Inglés solo para patrones técnicos genéricos (`BaseRepository`).
- Ningún endpoint recibe `id_clinica` por URL ni por body: siempre
  `id_clinica: int = Depends(resolve_clinica_id)`.
- Permisos, una sola regla sin excepciones: **los 4 roles leen; solo `admin` y `superadmin`
  escriben.**
- Defaults de `ConfiguracionClinica`: `duracion_cita_minutos=30`, `porcentaje_impuesto=13.00`
  (IVA El Salvador), `prefijo_factura="F"`, `proximo_numero_factura=1`,
  `horas_minimas_cambio_cita=24`, `dias_minimos_reagendamiento=3`.
- Rangos de validación: `duracion_cita_minutos` 5–480; `porcentaje_impuesto` 0–100;
  `proximo_numero_factura` >= 1; `horas_minimas_cambio_cita` **1**–720;
  `dias_minimos_reagendamiento` **1**–90. Los mínimos son 1 y no 0 a propósito: la regla es
  configurable en intensidad pero no desactivable.
- Horario por defecto: lunes a viernes `08:00`–`17:00` abierto; sábado y domingo `cerrado=True`
  con horas en `NULL`.
- **No** se toca `MODULOS_DISPONIBLES` (`app/repositories/clinica_modulo_repository.py`): los
  parámetros no son un módulo toggleable.
- **No** se toca `ClinicaService` ni ningún archivo del Módulo 2: la fila de
  `ConfiguracionClinica` se crea al vuelo en el primer `GET`.
- Migración nueva: `0003_parametros_por_clinica.py`, `down_revision = "0002"`. Nunca editar una
  migración ya committeada.

---

## File Structure

```
backend/
  alembic/versions/
    0003_parametros_por_clinica.py                (create)
  app/
    models/
      parametros.py                               (create: 5 modelos + DiaSemana + HORARIO_POR_DEFECTO)
      __init__.py                                 (modify: exportar lo nuevo)
    exceptions.py                                 (modify: + 2 excepciones)
    repositories/
      catalogo_repository.py                      (create: CRUD compartido, hereda BaseRepository)
      especialidad_repository.py                  (create: 2 lineas)
      consultorio_repository.py                   (create: 2 lineas)
      metodo_pago_repository.py                   (create: 2 lineas)
      horario_clinica_repository.py               (create: llave compuesta, NO hereda)
      configuracion_repository.py                 (create: 1:1, NO hereda)
    schemas/
      parametros.py                               (create: schemas de los 5 recursos)
    api/routes/
      especialidades.py                           (create)
      consultorios.py                             (create)
      metodos_pago.py                             (create)
      horarios.py                                 (create)
      configuracion.py                            (create)
    main.py                                       (modify: incluir 5 routers)
  tests/
    test_parametros_models.py                     (create)
    test_catalogo_repository.py                    (create: el grueso de la logica)
    test_especialidad_repository.py                (create: smoke)
    test_consultorio_repository.py                 (create: smoke)
    test_metodo_pago_repository.py                 (create: smoke)
    test_horario_clinica_repository.py             (create)
    test_configuracion_repository.py               (create)
    test_especialidades_routes.py                  (create)
    test_consultorios_routes.py                    (create)
    test_metodos_pago_routes.py                    (create)
    test_horarios_routes.py                        (create)
    test_configuracion_routes.py                   (create)
```

**Por qué esta división:** los modelos van juntos en `parametros.py` porque son un grupo cohesivo
que cambia junto (convención del repo: un archivo por entidad o grupo relacionado). Los
repositorios van separados porque tienen contratos distintos: los tres catálogos comparten
implementación vía herencia, mientras `horario_clinica_repository` y `configuracion_repository`
tienen firmas propias. Las rutas se separan por recurso aunque se repitan: cada endpoint son 4-5
líneas, y a cambio `/docs` queda legible y los mensajes de error son específicos
("Especialidad no encontrada", no "Recurso no encontrado").

---

## Task 1: Modelos, enum y migración

**Files:**
- Create: `backend/app/models/parametros.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/0003_parametros_por_clinica.py`
- Test: `backend/tests/test_parametros_models.py`

**Interfaces:**
- Consumes: `app.models.base.Base`, `Clinica` (Módulo 1).
- Produces: `DiaSemana`, `Especialidad`, `Consultorio`, `MetodoPago`, `HorarioClinica`,
  `ConfiguracionClinica`, `HORARIO_POR_DEFECTO`. Los tres catálogos exponen `id_clinica: int`,
  `nombre: str`, `activo: bool` y una PK propia (`id_especialidad`, `id_consultorio`,
  `id_metodo_pago`). `HORARIO_POR_DEFECTO: dict[DiaSemana, dict]` con claves
  `hora_apertura`, `hora_cierre`, `cerrado`.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `backend/tests/test_parametros_models.py`:

```python
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError


def _clinica(db_session, nombre="Dental A"):
    from app.models import Clinica

    clinica = Clinica(nombre=nombre)
    db_session.add(clinica)
    db_session.flush()
    return clinica


def test_especialidad_nace_activa(db_session):
    from app.models import Especialidad

    clinica = _clinica(db_session)
    especialidad = Especialidad(id_clinica=clinica.id_clinica, nombre="Ortodoncia")
    db_session.add(especialidad)
    db_session.flush()

    assert especialidad.id_especialidad is not None
    assert especialidad.activo is True


def test_consultorio_y_metodo_pago_nacen_activos(db_session):
    from app.models import Consultorio, MetodoPago

    clinica = _clinica(db_session)
    consultorio = Consultorio(id_clinica=clinica.id_clinica, nombre="Consultorio 1")
    metodo = MetodoPago(id_clinica=clinica.id_clinica, nombre="Efectivo")
    db_session.add_all([consultorio, metodo])
    db_session.flush()

    assert consultorio.activo is True
    assert metodo.activo is True


def test_mismo_nombre_en_dos_clinicas_es_valido(db_session):
    from app.models import Especialidad

    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    db_session.add_all(
        [
            Especialidad(id_clinica=clinica_a.id_clinica, nombre="Ortodoncia"),
            Especialidad(id_clinica=clinica_b.id_clinica, nombre="Ortodoncia"),
        ]
    )

    db_session.flush()  # no debe explotar


def test_mismo_nombre_repetido_en_la_misma_clinica_viola_la_unicidad(db_session):
    from app.models import Especialidad

    clinica = _clinica(db_session)
    db_session.add_all(
        [
            Especialidad(id_clinica=clinica.id_clinica, nombre="Ortodoncia"),
            Especialidad(id_clinica=clinica.id_clinica, nombre="Ortodoncia"),
        ]
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_dia_semana_persiste_el_valor_en_minuscula_no_el_nombre(db_session):
    from datetime import time

    from app.models import DiaSemana, HorarioClinica

    clinica = _clinica(db_session)
    db_session.add(
        HorarioClinica(
            id_clinica=clinica.id_clinica,
            dia_semana=DiaSemana.LUNES,
            hora_apertura=time(8, 0),
            hora_cierre=time(17, 0),
            cerrado=False,
        )
    )
    db_session.flush()

    guardado = db_session.execute(text("SELECT dia_semana FROM horario_clinica")).scalar_one()
    assert guardado == "lunes"


def test_horario_clinica_no_admite_dos_filas_para_el_mismo_dia(db_session):
    from app.models import DiaSemana, HorarioClinica

    clinica = _clinica(db_session)
    db_session.add_all(
        [
            HorarioClinica(id_clinica=clinica.id_clinica, dia_semana=DiaSemana.LUNES),
            HorarioClinica(id_clinica=clinica.id_clinica, dia_semana=DiaSemana.LUNES),
        ]
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_configuracion_clinica_tiene_los_defaults_acordados(db_session):
    from decimal import Decimal

    from app.models import ConfiguracionClinica

    clinica = _clinica(db_session)
    config = ConfiguracionClinica(id_clinica=clinica.id_clinica)
    db_session.add(config)
    db_session.flush()

    assert config.duracion_cita_minutos == 30
    assert Decimal(config.porcentaje_impuesto) == Decimal("13.00")
    assert config.prefijo_factura == "F"
    assert config.proximo_numero_factura == 1
    assert config.horas_minimas_cambio_cita == 24
    assert config.dias_minimos_reagendamiento == 3


def test_horario_por_defecto_cubre_los_siete_dias_con_fin_de_semana_cerrado():
    from datetime import time

    from app.models import HORARIO_POR_DEFECTO, DiaSemana

    assert set(HORARIO_POR_DEFECTO) == set(DiaSemana)

    assert HORARIO_POR_DEFECTO[DiaSemana.LUNES] == {
        "hora_apertura": time(8, 0),
        "hora_cierre": time(17, 0),
        "cerrado": False,
    }
    for dia in (DiaSemana.SABADO, DiaSemana.DOMINGO):
        assert HORARIO_POR_DEFECTO[dia] == {
            "hora_apertura": None,
            "hora_cierre": None,
            "cerrado": True,
        }
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_parametros_models.py -v`
Expected: FAIL — `ImportError: cannot import name 'Especialidad' from 'app.models'`

- [ ] **Step 3: Escribir los modelos**

Crear `backend/app/models/parametros.py`:

```python
import enum
from datetime import datetime, time

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class DiaSemana(str, enum.Enum):
    LUNES = "lunes"
    MARTES = "martes"
    MIERCOLES = "miercoles"
    JUEVES = "jueves"
    VIERNES = "viernes"
    SABADO = "sabado"
    DOMINGO = "domingo"


class Especialidad(Base):
    __tablename__ = "especialidad"
    __table_args__ = (
        UniqueConstraint("id_clinica", "nombre", name="uq_especialidad_clinica_nombre"),
    )

    id_especialidad: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_clinica: Mapped[int] = mapped_column(
        ForeignKey("clinica.id_clinica"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")


class Consultorio(Base):
    __tablename__ = "consultorio"
    __table_args__ = (
        UniqueConstraint("id_clinica", "nombre", name="uq_consultorio_clinica_nombre"),
    )

    id_consultorio: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_clinica: Mapped[int] = mapped_column(
        ForeignKey("clinica.id_clinica"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")


class MetodoPago(Base):
    __tablename__ = "metodo_pago"
    __table_args__ = (
        UniqueConstraint("id_clinica", "nombre", name="uq_metodo_pago_clinica_nombre"),
    )

    id_metodo_pago: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_clinica: Mapped[int] = mapped_column(
        ForeignKey("clinica.id_clinica"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")


class HorarioClinica(Base):
    """Horario de atencion de la clinica, una fila por dia de la semana.

    Llave compuesta (id_clinica, dia_semana): impide a nivel de esquema que
    existan dos filas para el mismo dia. Mismo criterio que ClinicaModulo.
    """

    __tablename__ = "horario_clinica"

    id_clinica: Mapped[int] = mapped_column(
        ForeignKey("clinica.id_clinica"), primary_key=True
    )
    dia_semana: Mapped[DiaSemana] = mapped_column(
        SAEnum(
            DiaSemana,
            name="dia_semana",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        primary_key=True,
    )
    hora_apertura: Mapped[time | None] = mapped_column(Time, nullable=True)
    hora_cierre: Mapped[time | None] = mapped_column(Time, nullable=True)
    cerrado: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")


class ConfiguracionClinica(Base):
    """Parametros escalares de una clinica. 1:1 con Clinica: id_clinica es PK y FK
    a la vez, asi que el esquema mismo impide dos configuraciones por clinica.
    """

    __tablename__ = "configuracion_clinica"

    id_clinica: Mapped[int] = mapped_column(
        ForeignKey("clinica.id_clinica"), primary_key=True
    )
    duracion_cita_minutos: Mapped[int] = mapped_column(
        Integer, default=30, server_default="30"
    )
    porcentaje_impuesto: Mapped[str] = mapped_column(
        Numeric(5, 2), default="13.00", server_default="13.00"
    )
    prefijo_factura: Mapped[str] = mapped_column(
        String(10), default="F", server_default="F"
    )
    proximo_numero_factura: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1"
    )
    horas_minimas_cambio_cita: Mapped[int] = mapped_column(
        Integer, default=24, server_default="24"
    )
    dias_minimos_reagendamiento: Mapped[int] = mapped_column(
        Integer, default=3, server_default="3"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


#: Unica fuente de verdad de los defaults del horario de atencion.
#: La usan la ruta GET /horarios (para rellenar dias sin fila) y los tests.
HORARIO_POR_DEFECTO: dict[DiaSemana, dict] = {
    DiaSemana.LUNES: {"hora_apertura": time(8, 0), "hora_cierre": time(17, 0), "cerrado": False},
    DiaSemana.MARTES: {"hora_apertura": time(8, 0), "hora_cierre": time(17, 0), "cerrado": False},
    DiaSemana.MIERCOLES: {"hora_apertura": time(8, 0), "hora_cierre": time(17, 0), "cerrado": False},
    DiaSemana.JUEVES: {"hora_apertura": time(8, 0), "hora_cierre": time(17, 0), "cerrado": False},
    DiaSemana.VIERNES: {"hora_apertura": time(8, 0), "hora_cierre": time(17, 0), "cerrado": False},
    DiaSemana.SABADO: {"hora_apertura": None, "hora_cierre": None, "cerrado": True},
    DiaSemana.DOMINGO: {"hora_apertura": None, "hora_cierre": None, "cerrado": True},
}
```

- [ ] **Step 4: Exportar los modelos nuevos**

Modificar `backend/app/models/__init__.py` — queda así completo:

```python
from app.models.base import Base
from app.models.clinica import Clinica, ClinicaModulo, EstadoClinica
from app.models.parametros import (
    HORARIO_POR_DEFECTO,
    ConfiguracionClinica,
    Consultorio,
    DiaSemana,
    Especialidad,
    HorarioClinica,
    MetodoPago,
)
from app.models.usuario import RolUsuario, Usuario

__all__ = [
    "Base",
    "Clinica",
    "ClinicaModulo",
    "EstadoClinica",
    "Usuario",
    "RolUsuario",
    "DiaSemana",
    "Especialidad",
    "Consultorio",
    "MetodoPago",
    "HorarioClinica",
    "ConfiguracionClinica",
    "HORARIO_POR_DEFECTO",
]
```

- [ ] **Step 5: Correr los tests y verificar que pasan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_parametros_models.py -v`
Expected: PASS — 8 passed

- [ ] **Step 6: Correr la suite completa para confirmar que no se rompió nada**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: todos los tests de Módulos 1 y 2 siguen pasando.

- [ ] **Step 7: Escribir la migración**

Crear `backend/alembic/versions/0003_parametros_por_clinica.py`:

```python
"""parametros por clinica: especialidad, consultorio, metodo_pago, horario, configuracion

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-31
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def _tabla_catalogo(nombre_tabla: str, nombre_pk: str) -> None:
    op.create_table(
        nombre_tabla,
        sa.Column(nombre_pk, sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_clinica", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=50), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default="1", nullable=False),
        sa.ForeignKeyConstraint(["id_clinica"], ["clinica.id_clinica"]),
        sa.PrimaryKeyConstraint(nombre_pk),
        sa.UniqueConstraint(
            "id_clinica", "nombre", name=f"uq_{nombre_tabla}_clinica_nombre"
        ),
    )


def upgrade() -> None:
    _tabla_catalogo("especialidad", "id_especialidad")
    _tabla_catalogo("consultorio", "id_consultorio")
    _tabla_catalogo("metodo_pago", "id_metodo_pago")

    op.create_table(
        "horario_clinica",
        sa.Column("id_clinica", sa.Integer(), nullable=False),
        sa.Column(
            "dia_semana",
            sa.Enum(
                "lunes",
                "martes",
                "miercoles",
                "jueves",
                "viernes",
                "sabado",
                "domingo",
                name="dia_semana",
            ),
            nullable=False,
        ),
        sa.Column("hora_apertura", sa.Time(), nullable=True),
        sa.Column("hora_cierre", sa.Time(), nullable=True),
        sa.Column("cerrado", sa.Boolean(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(["id_clinica"], ["clinica.id_clinica"]),
        sa.PrimaryKeyConstraint("id_clinica", "dia_semana"),
    )

    op.create_table(
        "configuracion_clinica",
        sa.Column("id_clinica", sa.Integer(), nullable=False),
        sa.Column(
            "duracion_cita_minutos", sa.Integer(), server_default="30", nullable=False
        ),
        sa.Column(
            "porcentaje_impuesto",
            sa.Numeric(precision=5, scale=2),
            server_default="13.00",
            nullable=False,
        ),
        sa.Column(
            "prefijo_factura", sa.String(length=10), server_default="F", nullable=False
        ),
        sa.Column(
            "proximo_numero_factura", sa.Integer(), server_default="1", nullable=False
        ),
        sa.Column(
            "horas_minimas_cambio_cita", sa.Integer(), server_default="24", nullable=False
        ),
        sa.Column(
            "dias_minimos_reagendamiento", sa.Integer(), server_default="3", nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["id_clinica"], ["clinica.id_clinica"]),
        sa.PrimaryKeyConstraint("id_clinica"),
    )


def downgrade() -> None:
    op.drop_table("configuracion_clinica")
    op.drop_table("horario_clinica")
    op.drop_table("metodo_pago")
    op.drop_table("consultorio")
    op.drop_table("especialidad")
```

- [ ] **Step 8: Verificar que Alembic ve la migración y la cadena de revisiones está sana**

Run: `.venv/Scripts/python.exe -m alembic history`
Expected: aparece `0002 -> 0003 (head), parametros por clinica...`

La aplicación real contra MySQL se verifica en la Task 11 (no hace falta MySQL corriendo ahora).

- [ ] **Step 9: Punto de commit (lo ejecuta Meli, no el agente)**

```bash
git add backend/app/models/parametros.py backend/app/models/__init__.py \
        backend/alembic/versions/0003_parametros_por_clinica.py \
        backend/tests/test_parametros_models.py
git commit -m "feat(backend): modelos y migracion de parametros por clinica"
```

---

## Task 2: `CatalogoRepository` y excepciones de dominio

**Files:**
- Modify: `backend/app/exceptions.py`
- Create: `backend/app/repositories/catalogo_repository.py`
- Test: `backend/tests/test_catalogo_repository.py`

**Interfaces:**
- Consumes: `BaseRepository[T]` de `app/repositories/base.py` (firma con `id_clinica` obligatorio
  como primer parámetro); modelos de la Task 1.
- Produces:
  - `NombreDuplicadoEnClinicaError`, `HorarioInvalidoError` (la segunda se usa en la Task 7).
  - `CatalogoRepository[T]` con `model: type[T]` como atributo de clase y los métodos
    `listar(id_clinica, incluir_inactivos=False) -> list[T]`,
    `obtener(id_clinica, id_) -> T | None`,
    `crear(id_clinica, data: dict) -> T`,
    `actualizar(id_clinica, id_, data: dict) -> T | None`,
    `eliminar(id_clinica, id_) -> bool`.

> **Nota para quien implemente:** este es el corazón del módulo. Se testea **una sola vez, acá**,
> usando `Especialidad` como modelo de prueba. Las Tasks 3 en adelante solo hacen smoke tests,
> porque el comportamiento ya quedó cubierto.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `backend/tests/test_catalogo_repository.py`:

```python
import pytest


def _clinica(db_session, nombre="Dental A"):
    from app.models import Clinica

    clinica = Clinica(nombre=nombre)
    db_session.add(clinica)
    db_session.flush()
    return clinica


def _repo(db_session):
    from app.repositories.especialidad_repository import EspecialidadRepository

    return EspecialidadRepository(db_session)


def test_crear_devuelve_el_registro_con_la_clinica_correcta(db_session):
    clinica = _clinica(db_session)

    creada = _repo(db_session).crear(clinica.id_clinica, {"nombre": "Ortodoncia"})

    assert creada.id_especialidad is not None
    assert creada.id_clinica == clinica.id_clinica
    assert creada.nombre == "Ortodoncia"
    assert creada.activo is True


def test_crear_recorta_espacios_del_nombre(db_session):
    clinica = _clinica(db_session)

    creada = _repo(db_session).crear(clinica.id_clinica, {"nombre": "  Endodoncia  "})

    assert creada.nombre == "Endodoncia"


def test_crear_con_nombre_duplicado_en_la_misma_clinica_lanza_error(db_session):
    from app.exceptions import NombreDuplicadoEnClinicaError

    clinica = _clinica(db_session)
    repo = _repo(db_session)
    repo.crear(clinica.id_clinica, {"nombre": "Ortodoncia"})

    with pytest.raises(NombreDuplicadoEnClinicaError):
        repo.crear(clinica.id_clinica, {"nombre": "Ortodoncia"})


def test_el_duplicado_se_detecta_sin_importar_mayusculas(db_session):
    from app.exceptions import NombreDuplicadoEnClinicaError

    clinica = _clinica(db_session)
    repo = _repo(db_session)
    repo.crear(clinica.id_clinica, {"nombre": "Ortodoncia"})

    with pytest.raises(NombreDuplicadoEnClinicaError):
        repo.crear(clinica.id_clinica, {"nombre": "ORTODONCIA"})


def test_el_duplicado_se_detecta_tambien_contra_registros_inactivos(db_session):
    from app.exceptions import NombreDuplicadoEnClinicaError

    clinica = _clinica(db_session)
    repo = _repo(db_session)
    creada = repo.crear(clinica.id_clinica, {"nombre": "Ortodoncia"})
    repo.eliminar(clinica.id_clinica, creada.id_especialidad)

    with pytest.raises(NombreDuplicadoEnClinicaError):
        repo.crear(clinica.id_clinica, {"nombre": "Ortodoncia"})


def test_dos_clinicas_pueden_tener_el_mismo_nombre(db_session):
    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    repo = _repo(db_session)

    repo.crear(clinica_a.id_clinica, {"nombre": "Ortodoncia"})
    creada_b = repo.crear(clinica_b.id_clinica, {"nombre": "Ortodoncia"})

    assert creada_b.id_clinica == clinica_b.id_clinica


def test_listar_solo_devuelve_los_de_la_clinica_pedida(db_session):
    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    repo = _repo(db_session)
    repo.crear(clinica_a.id_clinica, {"nombre": "Ortodoncia"})
    repo.crear(clinica_b.id_clinica, {"nombre": "Endodoncia"})

    resultado = repo.listar(clinica_a.id_clinica)

    assert [e.nombre for e in resultado] == ["Ortodoncia"]


def test_listar_omite_los_inactivos_por_defecto(db_session):
    clinica = _clinica(db_session)
    repo = _repo(db_session)
    creada = repo.crear(clinica.id_clinica, {"nombre": "Ortodoncia"})
    repo.crear(clinica.id_clinica, {"nombre": "Endodoncia"})
    repo.eliminar(clinica.id_clinica, creada.id_especialidad)

    assert [e.nombre for e in repo.listar(clinica.id_clinica)] == ["Endodoncia"]


def test_listar_con_incluir_inactivos_devuelve_todos_ordenados_por_nombre(db_session):
    clinica = _clinica(db_session)
    repo = _repo(db_session)
    creada = repo.crear(clinica.id_clinica, {"nombre": "Ortodoncia"})
    repo.crear(clinica.id_clinica, {"nombre": "Endodoncia"})
    repo.eliminar(clinica.id_clinica, creada.id_especialidad)

    nombres = [e.nombre for e in repo.listar(clinica.id_clinica, incluir_inactivos=True)]

    assert nombres == ["Endodoncia", "Ortodoncia"]


def test_obtener_de_otra_clinica_devuelve_none(db_session):
    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    repo = _repo(db_session)
    de_a = repo.crear(clinica_a.id_clinica, {"nombre": "Ortodoncia"})

    assert repo.obtener(clinica_b.id_clinica, de_a.id_especialidad) is None
    assert repo.obtener(clinica_a.id_clinica, de_a.id_especialidad) is not None


def test_obtener_inexistente_devuelve_none(db_session):
    clinica = _clinica(db_session)

    assert _repo(db_session).obtener(clinica.id_clinica, 9999) is None


def test_actualizar_aplica_solo_los_campos_presentes(db_session):
    clinica = _clinica(db_session)
    repo = _repo(db_session)
    creada = repo.crear(clinica.id_clinica, {"nombre": "Ortodoncia"})

    actualizada = repo.actualizar(
        clinica.id_clinica, creada.id_especialidad, {"nombre": "Ortodoncia avanzada"}
    )

    assert actualizada.nombre == "Ortodoncia avanzada"
    assert actualizada.activo is True


def test_actualizar_permite_reactivar(db_session):
    clinica = _clinica(db_session)
    repo = _repo(db_session)
    creada = repo.crear(clinica.id_clinica, {"nombre": "Ortodoncia"})
    repo.eliminar(clinica.id_clinica, creada.id_especialidad)

    reactivada = repo.actualizar(
        clinica.id_clinica, creada.id_especialidad, {"activo": True}
    )

    assert reactivada.activo is True


def test_actualizar_a_un_nombre_ya_usado_lanza_error(db_session):
    from app.exceptions import NombreDuplicadoEnClinicaError

    clinica = _clinica(db_session)
    repo = _repo(db_session)
    repo.crear(clinica.id_clinica, {"nombre": "Ortodoncia"})
    otra = repo.crear(clinica.id_clinica, {"nombre": "Endodoncia"})

    with pytest.raises(NombreDuplicadoEnClinicaError):
        repo.actualizar(clinica.id_clinica, otra.id_especialidad, {"nombre": "Ortodoncia"})


def test_actualizar_con_su_propio_nombre_no_lanza_error(db_session):
    clinica = _clinica(db_session)
    repo = _repo(db_session)
    creada = repo.crear(clinica.id_clinica, {"nombre": "Ortodoncia"})

    actualizada = repo.actualizar(
        clinica.id_clinica, creada.id_especialidad, {"nombre": "Ortodoncia"}
    )

    assert actualizada.nombre == "Ortodoncia"


def test_actualizar_de_otra_clinica_devuelve_none(db_session):
    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    repo = _repo(db_session)
    de_a = repo.crear(clinica_a.id_clinica, {"nombre": "Ortodoncia"})

    assert repo.actualizar(clinica_b.id_clinica, de_a.id_especialidad, {"nombre": "X"}) is None


def test_eliminar_es_borrado_logico(db_session):
    clinica = _clinica(db_session)
    repo = _repo(db_session)
    creada = repo.crear(clinica.id_clinica, {"nombre": "Ortodoncia"})

    assert repo.eliminar(clinica.id_clinica, creada.id_especialidad) is True
    assert repo.obtener(clinica.id_clinica, creada.id_especialidad).activo is False


def test_eliminar_dos_veces_sigue_devolviendo_true(db_session):
    clinica = _clinica(db_session)
    repo = _repo(db_session)
    creada = repo.crear(clinica.id_clinica, {"nombre": "Ortodoncia"})
    repo.eliminar(clinica.id_clinica, creada.id_especialidad)

    assert repo.eliminar(clinica.id_clinica, creada.id_especialidad) is True


def test_eliminar_de_otra_clinica_devuelve_false_y_no_lo_toca(db_session):
    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    repo = _repo(db_session)
    de_a = repo.crear(clinica_a.id_clinica, {"nombre": "Ortodoncia"})

    assert repo.eliminar(clinica_b.id_clinica, de_a.id_especialidad) is False
    assert repo.obtener(clinica_a.id_clinica, de_a.id_especialidad).activo is True


def test_el_repositorio_no_hace_commit(db_session):
    """Los repositorios hacen flush; el commit lo hace la ruta."""
    from app.models import Clinica

    clinica = Clinica(nombre="Dental A")
    db_session.add(clinica)
    db_session.commit()  # la clinica SI queda persistida
    id_clinica = clinica.id_clinica

    _repo(db_session).crear(id_clinica, {"nombre": "Ortodoncia"})
    db_session.rollback()  # deshace lo que el repositorio solo flusheo

    assert _repo(db_session).listar(id_clinica) == []
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_catalogo_repository.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.repositories.especialidad_repository'`

- [ ] **Step 3: Agregar las excepciones de dominio**

Modificar `backend/app/exceptions.py` — agregar al final:

```python
class NombreDuplicadoEnClinicaError(Exception):
    """Ya existe un registro con ese nombre en esa clinica."""


class HorarioInvalidoError(Exception):
    """El horario de un dia es incoherente (cierre <= apertura, o falta una hora)."""
```

- [ ] **Step 4: Escribir `CatalogoRepository`**

Crear `backend/app/repositories/catalogo_repository.py`:

```python
from typing import TypeVar

from sqlalchemy import func, select

from app.exceptions import NombreDuplicadoEnClinicaError
from app.repositories.base import BaseRepository

T = TypeVar("T")


class CatalogoRepository(BaseRepository[T]):
    """CRUD de catalogos por clinica: nombre unico por clinica y borrado logico.

    Los tres catalogos del Modulo 3 (Especialidad, Consultorio, MetodoPago)
    comparten exactamente la forma (id, id_clinica, nombre, activo), asi que el
    CRUD se implementa una sola vez aca. Cada subclase solo declara su modelo.
    """

    model: type[T]

    def _pk(self):
        return self.model.__mapper__.primary_key[0]

    def _existe_nombre(
        self, id_clinica: int, nombre: str, excluir_id: int | None = None
    ) -> bool:
        """Compara con func.lower() explicito, no confiando en el collation:
        SQLite es case-sensitive por defecto y MySQL utf8mb4_general_ci no lo es.
        Considera tambien los inactivos: lo correcto ante un nombre dado de baja
        es reactivarlo, no crear un duplicado.
        """
        stmt = select(self.model).where(
            self.model.id_clinica == id_clinica,
            func.lower(self.model.nombre) == nombre.strip().lower(),
        )
        if excluir_id is not None:
            stmt = stmt.where(self._pk() != excluir_id)
        return self.db.execute(stmt).scalars().first() is not None

    def listar(self, id_clinica: int, incluir_inactivos: bool = False) -> list[T]:
        stmt = select(self.model).where(self.model.id_clinica == id_clinica)
        if not incluir_inactivos:
            stmt = stmt.where(self.model.activo.is_(True))
        stmt = stmt.order_by(self.model.nombre)
        return list(self.db.execute(stmt).scalars().all())

    def obtener(self, id_clinica: int, id_: int) -> T | None:
        stmt = select(self.model).where(
            self._pk() == id_, self.model.id_clinica == id_clinica
        )
        return self.db.execute(stmt).scalars().first()

    def crear(self, id_clinica: int, data: dict) -> T:
        datos = dict(data)
        datos["nombre"] = datos["nombre"].strip()
        if self._existe_nombre(id_clinica, datos["nombre"]):
            raise NombreDuplicadoEnClinicaError(datos["nombre"])

        registro = self.model(id_clinica=id_clinica, **datos)
        self.db.add(registro)
        self.db.flush()
        return registro

    def actualizar(self, id_clinica: int, id_: int, data: dict) -> T | None:
        registro = self.obtener(id_clinica, id_)
        if registro is None:
            return None

        datos = dict(data)
        if "nombre" in datos:
            datos["nombre"] = datos["nombre"].strip()
            if self._existe_nombre(id_clinica, datos["nombre"], excluir_id=id_):
                raise NombreDuplicadoEnClinicaError(datos["nombre"])

        for campo, valor in datos.items():
            setattr(registro, campo, valor)
        self.db.flush()
        return registro

    def eliminar(self, id_clinica: int, id_: int) -> bool:
        """Borrado logico: pone activo = False. Idempotente."""
        registro = self.obtener(id_clinica, id_)
        if registro is None:
            return False
        registro.activo = False
        self.db.flush()
        return True
```

- [ ] **Step 5: Crear `EspecialidadRepository` (necesario para que los tests corran)**

Crear `backend/app/repositories/especialidad_repository.py`:

```python
from app.models import Especialidad
from app.repositories.catalogo_repository import CatalogoRepository


class EspecialidadRepository(CatalogoRepository[Especialidad]):
    model = Especialidad
```

- [ ] **Step 6: Correr los tests y verificar que pasan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_catalogo_repository.py -v`
Expected: PASS — 20 passed

- [ ] **Step 7: Correr la suite completa**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: todo verde.

- [ ] **Step 8: Punto de commit (lo ejecuta Meli)**

```bash
git add backend/app/exceptions.py backend/app/repositories/catalogo_repository.py \
        backend/app/repositories/especialidad_repository.py \
        backend/tests/test_catalogo_repository.py
git commit -m "feat(backend): CatalogoRepository con aislamiento por clinica y borrado logico"
```

---

## Task 3: Los otros dos repositorios de catálogo

**Files:**
- Create: `backend/app/repositories/consultorio_repository.py`
- Create: `backend/app/repositories/metodo_pago_repository.py`
- Test: `backend/tests/test_especialidad_repository.py`
- Test: `backend/tests/test_consultorio_repository.py`
- Test: `backend/tests/test_metodo_pago_repository.py`

**Interfaces:**
- Consumes: `CatalogoRepository[T]` (Task 2), modelos `Consultorio` y `MetodoPago` (Task 1).
- Produces: `ConsultorioRepository`, `MetodoPagoRepository`. Ambos con la misma interfaz que
  `EspecialidadRepository`.

> Los tests acá son **smoke tests** a propósito: verifican que cada subclase apunta al modelo
> correcto y hereda el comportamiento. La lógica ya está cubierta en `test_catalogo_repository.py`
> y duplicarla sería justamente la repetición que este diseño evita.

- [ ] **Step 1: Escribir los tres tests smoke que fallan**

Crear `backend/tests/test_especialidad_repository.py`:

```python
def _clinica(db_session):
    from app.models import Clinica

    clinica = Clinica(nombre="Dental A")
    db_session.add(clinica)
    db_session.flush()
    return clinica


def test_apunta_al_modelo_especialidad():
    from app.models import Especialidad
    from app.repositories.especialidad_repository import EspecialidadRepository

    assert EspecialidadRepository.model is Especialidad


def test_hereda_el_crud_del_catalogo(db_session):
    from app.repositories.catalogo_repository import CatalogoRepository
    from app.repositories.especialidad_repository import EspecialidadRepository

    assert issubclass(EspecialidadRepository, CatalogoRepository)

    clinica = _clinica(db_session)
    repo = EspecialidadRepository(db_session)
    creada = repo.crear(clinica.id_clinica, {"nombre": "Ortodoncia"})

    assert repo.obtener(clinica.id_clinica, creada.id_especialidad) is creada
```

Crear `backend/tests/test_consultorio_repository.py`:

```python
def _clinica(db_session):
    from app.models import Clinica

    clinica = Clinica(nombre="Dental A")
    db_session.add(clinica)
    db_session.flush()
    return clinica


def test_apunta_al_modelo_consultorio():
    from app.models import Consultorio
    from app.repositories.consultorio_repository import ConsultorioRepository

    assert ConsultorioRepository.model is Consultorio


def test_hereda_el_crud_del_catalogo(db_session):
    from app.repositories.catalogo_repository import CatalogoRepository
    from app.repositories.consultorio_repository import ConsultorioRepository

    assert issubclass(ConsultorioRepository, CatalogoRepository)

    clinica = _clinica(db_session)
    repo = ConsultorioRepository(db_session)
    creado = repo.crear(clinica.id_clinica, {"nombre": "Consultorio 1"})

    assert repo.obtener(clinica.id_clinica, creado.id_consultorio) is creado
```

Crear `backend/tests/test_metodo_pago_repository.py`:

```python
def _clinica(db_session):
    from app.models import Clinica

    clinica = Clinica(nombre="Dental A")
    db_session.add(clinica)
    db_session.flush()
    return clinica


def test_apunta_al_modelo_metodo_pago():
    from app.models import MetodoPago
    from app.repositories.metodo_pago_repository import MetodoPagoRepository

    assert MetodoPagoRepository.model is MetodoPago


def test_hereda_el_crud_del_catalogo(db_session):
    from app.repositories.catalogo_repository import CatalogoRepository
    from app.repositories.metodo_pago_repository import MetodoPagoRepository

    assert issubclass(MetodoPagoRepository, CatalogoRepository)

    clinica = _clinica(db_session)
    repo = MetodoPagoRepository(db_session)
    creado = repo.crear(clinica.id_clinica, {"nombre": "Efectivo"})

    assert repo.obtener(clinica.id_clinica, creado.id_metodo_pago) is creado
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_especialidad_repository.py tests/test_consultorio_repository.py tests/test_metodo_pago_repository.py -v`
Expected: los de especialidad pasan (el repo ya existe de la Task 2); los otros cuatro fallan con
`ModuleNotFoundError: No module named 'app.repositories.consultorio_repository'`

- [ ] **Step 3: Escribir los dos repositorios**

Crear `backend/app/repositories/consultorio_repository.py`:

```python
from app.models import Consultorio
from app.repositories.catalogo_repository import CatalogoRepository


class ConsultorioRepository(CatalogoRepository[Consultorio]):
    model = Consultorio
```

Crear `backend/app/repositories/metodo_pago_repository.py`:

```python
from app.models import MetodoPago
from app.repositories.catalogo_repository import CatalogoRepository


class MetodoPagoRepository(CatalogoRepository[MetodoPago]):
    model = MetodoPago
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_especialidad_repository.py tests/test_consultorio_repository.py tests/test_metodo_pago_repository.py -v`
Expected: PASS — 6 passed

- [ ] **Step 5: Punto de commit (lo ejecuta Meli)**

```bash
git add backend/app/repositories/consultorio_repository.py \
        backend/app/repositories/metodo_pago_repository.py \
        backend/tests/test_especialidad_repository.py \
        backend/tests/test_consultorio_repository.py \
        backend/tests/test_metodo_pago_repository.py
git commit -m "feat(backend): repositorios de consultorio y metodo de pago"
```

---

## Task 4: Schemas de los catálogos

**Files:**
- Create: `backend/app/schemas/parametros.py`
- Test: (sin archivo propio — se cubren en los tests de rutas de las Tasks 5 y 6)

**Interfaces:**
- Consumes: nada de tasks anteriores.
- Produces: `CatalogoCreateRequest` (campo `nombre: str`), `CatalogoUpdateRequest`
  (`nombre: str | None`, `activo: bool | None`), y tres schemas de respuesta:
  `EspecialidadResponse` (`id_especialidad`, `nombre`, `activo`),
  `ConsultorioResponse` (`id_consultorio`, ...), `MetodoPagoResponse` (`id_metodo_pago`, ...).

> Los schemas de request se comparten entre los tres catálogos porque el contrato de entrada es
> idéntico (`nombre`). Los de respuesta son distintos porque cada recurso expone su propia PK, y
> eso es justo lo que hace que `/docs` sea legible.

- [ ] **Step 1: Escribir el archivo de schemas**

Crear `backend/app/schemas/parametros.py`:

```python
from pydantic import BaseModel, Field, field_validator


def _nombre_limpio(valor: str) -> str:
    limpio = valor.strip()
    if not limpio:
        raise ValueError("El nombre no puede estar vacio")
    return limpio


class CatalogoCreateRequest(BaseModel):
    """Contrato de entrada compartido por Especialidad, Consultorio y MetodoPago."""

    nombre: str = Field(min_length=1, max_length=50)

    @field_validator("nombre")
    @classmethod
    def _validar_nombre(cls, valor: str) -> str:
        return _nombre_limpio(valor)


class CatalogoUpdateRequest(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=50)
    activo: bool | None = None

    @field_validator("nombre")
    @classmethod
    def _validar_nombre(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return _nombre_limpio(valor)


class EspecialidadResponse(BaseModel):
    id_especialidad: int
    nombre: str
    activo: bool

    model_config = {"from_attributes": True}


class ConsultorioResponse(BaseModel):
    id_consultorio: int
    nombre: str
    activo: bool

    model_config = {"from_attributes": True}


class MetodoPagoResponse(BaseModel):
    id_metodo_pago: int
    nombre: str
    activo: bool

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Verificar que el módulo importa sin errores**

Run: `.venv/Scripts/python.exe -c "from app.schemas.parametros import CatalogoCreateRequest; print(CatalogoCreateRequest(nombre='  Ortodoncia  ').nombre)"`
Expected: imprime `Ortodoncia` (sin espacios)

- [ ] **Step 3: Punto de commit (lo ejecuta Meli)**

```bash
git add backend/app/schemas/parametros.py
git commit -m "feat(backend): schemas de los catalogos de parametros"
```

---

## Task 5: Router de especialidades (establece el patrón)

**Files:**
- Create: `backend/app/api/routes/especialidades.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_especialidades_routes.py`

**Interfaces:**
- Consumes: `EspecialidadRepository` (Task 2), schemas (Task 4), `resolve_clinica_id` y
  `require_roles` de `app/api/deps.py` (Módulo 1).
- Produces: el patrón de router que copian las Tasks 6, 8 y 10 — constantes `LECTURA` y
  `ESCRITURA` a nivel de módulo, `id_clinica: int = Depends(resolve_clinica_id)` en cada endpoint,
  `db.commit()` en las rutas de escritura.

> **Este es el task de referencia.** Es el primer consumidor real de `resolve_clinica_id` en todo
> el proyecto. Lo que quede acá lo van a copiar los Módulos 4 a 8, así que vale la pena que esté
> prolijo.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `backend/tests/test_especialidades_routes.py`:

```python
from datetime import timedelta

import pytest


def _clinica(db_session, nombre="Dental A"):
    from app.models import Clinica

    clinica = Clinica(nombre=nombre)
    db_session.add(clinica)
    db_session.commit()
    return clinica


def _token_para(db_session, rol, id_clinica=None, username="user.test"):
    from app.models import Usuario
    from app.security.jwt import create_access_token
    from app.security.passwords import hash_password

    usuario = Usuario(
        id_clinica=id_clinica,
        username=username,
        password_hash=hash_password("clave123"),
        rol=rol,
    )
    db_session.add(usuario)
    db_session.commit()

    return create_access_token(
        data={"sub": str(usuario.id_usuario), "id_clinica": id_clinica, "rol": rol.value},
        expires_delta=timedelta(minutes=10),
    )


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_listar_sin_token_devuelve_401(client):
    assert client.get("/especialidades").status_code == 401


def test_crear_y_listar_como_admin(client, db_session):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")

    creacion = client.post(
        "/especialidades", headers=_auth(token), json={"nombre": "Ortodoncia"}
    )
    assert creacion.status_code == 201
    assert creacion.json()["nombre"] == "Ortodoncia"
    assert creacion.json()["activo"] is True

    listado = client.get("/especialidades", headers=_auth(token))
    assert listado.status_code == 200
    assert [e["nombre"] for e in listado.json()] == ["Ortodoncia"]


def test_crear_nombre_duplicado_devuelve_409(client, db_session):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")
    client.post("/especialidades", headers=_auth(token), json={"nombre": "Ortodoncia"})

    repetida = client.post(
        "/especialidades", headers=_auth(token), json={"nombre": "ortodoncia"}
    )

    assert repetida.status_code == 409


def test_crear_con_nombre_vacio_devuelve_422(client, db_session):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")

    assert client.post(
        "/especialidades", headers=_auth(token), json={"nombre": "   "}
    ).status_code == 422


@pytest.mark.parametrize("rol_nombre", ["DOCTOR", "ASISTENTE"])
def test_doctor_y_asistente_pueden_leer(client, db_session, rol_nombre):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    token_admin = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")
    client.post("/especialidades", headers=_auth(token_admin), json={"nombre": "Ortodoncia"})

    rol = getattr(RolUsuario, rol_nombre)
    token = _token_para(db_session, rol, clinica.id_clinica, f"user.{rol_nombre.lower()}")

    respuesta = client.get("/especialidades", headers=_auth(token))

    assert respuesta.status_code == 200
    assert [e["nombre"] for e in respuesta.json()] == ["Ortodoncia"]


@pytest.mark.parametrize("rol_nombre", ["DOCTOR", "ASISTENTE"])
def test_doctor_y_asistente_no_pueden_escribir(client, db_session, rol_nombre):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    rol = getattr(RolUsuario, rol_nombre)
    token = _token_para(db_session, rol, clinica.id_clinica, f"user.{rol_nombre.lower()}")

    assert client.post(
        "/especialidades", headers=_auth(token), json={"nombre": "Ortodoncia"}
    ).status_code == 403


def test_superadmin_sin_header_de_clinica_devuelve_400(client, db_session):
    from app.models import RolUsuario

    token = _token_para(db_session, RolUsuario.SUPERADMIN, None, "superadmin")

    assert client.get("/especialidades", headers=_auth(token)).status_code == 400


def test_superadmin_con_header_opera_sobre_esa_clinica(client, db_session):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.SUPERADMIN, None, "superadmin")
    cabeceras = {**_auth(token), "X-Clinica-Id": str(clinica.id_clinica)}

    creacion = client.post("/especialidades", headers=cabeceras, json={"nombre": "Ortodoncia"})

    assert creacion.status_code == 201
    assert client.get("/especialidades", headers=cabeceras).json()[0]["nombre"] == "Ortodoncia"


def test_un_admin_no_ve_las_especialidades_de_otra_clinica(client, db_session):
    from app.models import RolUsuario

    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    token_a = _token_para(db_session, RolUsuario.ADMIN, clinica_a.id_clinica, "admin.a")
    token_b = _token_para(db_session, RolUsuario.ADMIN, clinica_b.id_clinica, "admin.b")

    creada = client.post(
        "/especialidades", headers=_auth(token_a), json={"nombre": "Ortodoncia"}
    ).json()

    assert client.get("/especialidades", headers=_auth(token_b)).json() == []
    assert client.get(
        f"/especialidades/{creada['id_especialidad']}", headers=_auth(token_b)
    ).status_code == 404


def test_un_admin_no_puede_editar_ni_borrar_lo_de_otra_clinica(client, db_session):
    from app.models import RolUsuario

    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    token_a = _token_para(db_session, RolUsuario.ADMIN, clinica_a.id_clinica, "admin.a")
    token_b = _token_para(db_session, RolUsuario.ADMIN, clinica_b.id_clinica, "admin.b")
    creada = client.post(
        "/especialidades", headers=_auth(token_a), json={"nombre": "Ortodoncia"}
    ).json()
    id_ajeno = creada["id_especialidad"]

    assert client.put(
        f"/especialidades/{id_ajeno}", headers=_auth(token_b), json={"nombre": "Hackeada"}
    ).status_code == 404
    assert client.delete(
        f"/especialidades/{id_ajeno}", headers=_auth(token_b)
    ).status_code == 404

    sigue_igual = client.get(f"/especialidades/{id_ajeno}", headers=_auth(token_a)).json()
    assert sigue_igual["nombre"] == "Ortodoncia"
    assert sigue_igual["activo"] is True


def test_el_header_de_clinica_se_ignora_para_roles_no_superadmin(client, db_session):
    from app.models import RolUsuario

    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    token_a = _token_para(db_session, RolUsuario.ADMIN, clinica_a.id_clinica, "admin.a")

    client.post(
        "/especialidades",
        headers={**_auth(token_a), "X-Clinica-Id": str(clinica_b.id_clinica)},
        json={"nombre": "Ortodoncia"},
    )

    token_b = _token_para(db_session, RolUsuario.ADMIN, clinica_b.id_clinica, "admin.b")
    assert client.get("/especialidades", headers=_auth(token_b)).json() == []


def test_actualizar_devuelve_200_y_404_si_no_existe(client, db_session):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")
    creada = client.post(
        "/especialidades", headers=_auth(token), json={"nombre": "Ortodoncia"}
    ).json()

    actualizada = client.put(
        f"/especialidades/{creada['id_especialidad']}",
        headers=_auth(token),
        json={"nombre": "Ortodoncia avanzada"},
    )

    assert actualizada.status_code == 200
    assert actualizada.json()["nombre"] == "Ortodoncia avanzada"
    assert client.put(
        "/especialidades/9999", headers=_auth(token), json={"nombre": "X"}
    ).status_code == 404


def test_eliminar_desactiva_y_desaparece_del_listado(client, db_session):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")
    creada = client.post(
        "/especialidades", headers=_auth(token), json={"nombre": "Ortodoncia"}
    ).json()

    borrado = client.delete(
        f"/especialidades/{creada['id_especialidad']}", headers=_auth(token)
    )

    assert borrado.status_code == 204
    assert client.get("/especialidades", headers=_auth(token)).json() == []

    con_inactivos = client.get(
        "/especialidades?incluir_inactivos=true", headers=_auth(token)
    ).json()
    assert con_inactivos[0]["activo"] is False
    assert client.delete("/especialidades/9999", headers=_auth(token)).status_code == 404
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_especialidades_routes.py -v`
Expected: FAIL — todos con `404 != 201/200`, porque el router todavía no existe.

- [ ] **Step 3: Escribir el router**

Crear `backend/app/api/routes/especialidades.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles, resolve_clinica_id
from app.db import get_db
from app.exceptions import NombreDuplicadoEnClinicaError
from app.models import RolUsuario
from app.repositories.especialidad_repository import EspecialidadRepository
from app.schemas.parametros import (
    CatalogoCreateRequest,
    CatalogoUpdateRequest,
    EspecialidadResponse,
)

# Regla unica del Modulo 3: los 4 roles leen, solo admin y superadmin escriben.
LECTURA = require_roles(
    RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.DOCTOR, RolUsuario.ASISTENTE
)
ESCRITURA = require_roles(RolUsuario.SUPERADMIN, RolUsuario.ADMIN)

router = APIRouter(prefix="/especialidades", tags=["especialidades"])

NO_ENCONTRADA = "Especialidad no encontrada"


@router.get("", response_model=list[EspecialidadResponse], dependencies=[Depends(LECTURA)])
def listar_especialidades(
    incluir_inactivos: bool = False,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> list[EspecialidadResponse]:
    registros = EspecialidadRepository(db).listar(id_clinica, incluir_inactivos)
    return [EspecialidadResponse.model_validate(r) for r in registros]


@router.post(
    "",
    response_model=EspecialidadResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(ESCRITURA)],
)
def crear_especialidad(
    body: CatalogoCreateRequest,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> EspecialidadResponse:
    try:
        registro = EspecialidadRepository(db).crear(id_clinica, body.model_dump())
    except NombreDuplicadoEnClinicaError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una especialidad con ese nombre en esta clinica",
        )
    db.commit()
    return EspecialidadResponse.model_validate(registro)


@router.get(
    "/{id_especialidad}", response_model=EspecialidadResponse, dependencies=[Depends(LECTURA)]
)
def obtener_especialidad(
    id_especialidad: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> EspecialidadResponse:
    registro = EspecialidadRepository(db).obtener(id_clinica, id_especialidad)
    if registro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADA)
    return EspecialidadResponse.model_validate(registro)


@router.put(
    "/{id_especialidad}", response_model=EspecialidadResponse, dependencies=[Depends(ESCRITURA)]
)
def actualizar_especialidad(
    id_especialidad: int,
    body: CatalogoUpdateRequest,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> EspecialidadResponse:
    try:
        registro = EspecialidadRepository(db).actualizar(
            id_clinica, id_especialidad, body.model_dump(exclude_unset=True)
        )
    except NombreDuplicadoEnClinicaError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una especialidad con ese nombre en esta clinica",
        )
    if registro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADA)
    db.commit()
    return EspecialidadResponse.model_validate(registro)


@router.delete(
    "/{id_especialidad}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(ESCRITURA)],
)
def eliminar_especialidad(
    id_especialidad: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> Response:
    """Borrado logico: pone activo = False, no borra la fila."""
    if not EspecialidadRepository(db).eliminar(id_clinica, id_especialidad):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADA)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 4: Registrar el router**

Modificar `backend/app/main.py` — queda así completo:

```python
from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.clinicas import router as clinicas_router
from app.api.routes.especialidades import router as especialidades_router

app = FastAPI(title="Clinica Dental Web API")
app.include_router(auth_router)
app.include_router(clinicas_router)
app.include_router(especialidades_router)
```

- [ ] **Step 5: Correr los tests y verificar que pasan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_especialidades_routes.py -v`
Expected: PASS — 15 passed

- [ ] **Step 6: Correr la suite completa**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: todo verde.

- [ ] **Step 7: Punto de commit (lo ejecuta Meli)**

```bash
git add backend/app/api/routes/especialidades.py backend/app/main.py \
        backend/tests/test_especialidades_routes.py
git commit -m "feat(backend): endpoints CRUD de especialidades por clinica"
```

---

## Task 6: Routers de consultorios y métodos de pago

**Files:**
- Create: `backend/app/api/routes/consultorios.py`
- Create: `backend/app/api/routes/metodos_pago.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_consultorios_routes.py`
- Test: `backend/tests/test_metodos_pago_routes.py`

**Interfaces:**
- Consumes: `ConsultorioRepository` y `MetodoPagoRepository` (Task 3), `ConsultorioResponse` y
  `MetodoPagoResponse` (Task 4), el patrón de router de la Task 5.
- Produces: rutas `/consultorios` y `/metodos-pago` con la misma forma que `/especialidades`.

> Los tests acá son más acotados que los de la Task 5: el aislamiento entre clínicas y la matriz
> de permisos ya se probaron a fondo en `test_especialidades_routes.py` sobre el mismo código
> compartido. Acá se verifica que cada router está bien cableado a su repositorio y que la regla
> de permisos se aplicó.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `backend/tests/test_consultorios_routes.py`:

```python
from datetime import timedelta

import pytest


def _clinica(db_session, nombre="Dental A"):
    from app.models import Clinica

    clinica = Clinica(nombre=nombre)
    db_session.add(clinica)
    db_session.commit()
    return clinica


def _token_para(db_session, rol, id_clinica=None, username="user.test"):
    from app.models import Usuario
    from app.security.jwt import create_access_token
    from app.security.passwords import hash_password

    usuario = Usuario(
        id_clinica=id_clinica,
        username=username,
        password_hash=hash_password("clave123"),
        rol=rol,
    )
    db_session.add(usuario)
    db_session.commit()

    return create_access_token(
        data={"sub": str(usuario.id_usuario), "id_clinica": id_clinica, "rol": rol.value},
        expires_delta=timedelta(minutes=10),
    )


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_ciclo_completo_de_consultorios(client, db_session):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")

    creado = client.post("/consultorios", headers=_auth(token), json={"nombre": "Consultorio 1"})
    assert creado.status_code == 201
    id_consultorio = creado.json()["id_consultorio"]

    assert client.get(
        f"/consultorios/{id_consultorio}", headers=_auth(token)
    ).json()["nombre"] == "Consultorio 1"

    renombrado = client.put(
        f"/consultorios/{id_consultorio}", headers=_auth(token), json={"nombre": "Sala A"}
    )
    assert renombrado.json()["nombre"] == "Sala A"

    assert client.delete(
        f"/consultorios/{id_consultorio}", headers=_auth(token)
    ).status_code == 204
    assert client.get("/consultorios", headers=_auth(token)).json() == []


def test_consultorio_duplicado_devuelve_409(client, db_session):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")
    client.post("/consultorios", headers=_auth(token), json={"nombre": "Consultorio 1"})

    repetido = client.post(
        "/consultorios", headers=_auth(token), json={"nombre": "Consultorio 1"}
    )

    assert repetido.status_code == 409


def test_consultorios_de_otra_clinica_no_se_ven(client, db_session):
    from app.models import RolUsuario

    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    token_a = _token_para(db_session, RolUsuario.ADMIN, clinica_a.id_clinica, "admin.a")
    token_b = _token_para(db_session, RolUsuario.ADMIN, clinica_b.id_clinica, "admin.b")
    creado = client.post(
        "/consultorios", headers=_auth(token_a), json={"nombre": "Consultorio 1"}
    ).json()

    assert client.get("/consultorios", headers=_auth(token_b)).json() == []
    assert client.get(
        f"/consultorios/{creado['id_consultorio']}", headers=_auth(token_b)
    ).status_code == 404


@pytest.mark.parametrize("rol_nombre", ["DOCTOR", "ASISTENTE"])
def test_permisos_de_consultorios(client, db_session, rol_nombre):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    rol = getattr(RolUsuario, rol_nombre)
    token = _token_para(db_session, rol, clinica.id_clinica, f"user.{rol_nombre.lower()}")

    assert client.get("/consultorios", headers=_auth(token)).status_code == 200
    assert client.post(
        "/consultorios", headers=_auth(token), json={"nombre": "Consultorio 1"}
    ).status_code == 403
```

Crear `backend/tests/test_metodos_pago_routes.py`:

```python
from datetime import timedelta

import pytest


def _clinica(db_session, nombre="Dental A"):
    from app.models import Clinica

    clinica = Clinica(nombre=nombre)
    db_session.add(clinica)
    db_session.commit()
    return clinica


def _token_para(db_session, rol, id_clinica=None, username="user.test"):
    from app.models import Usuario
    from app.security.jwt import create_access_token
    from app.security.passwords import hash_password

    usuario = Usuario(
        id_clinica=id_clinica,
        username=username,
        password_hash=hash_password("clave123"),
        rol=rol,
    )
    db_session.add(usuario)
    db_session.commit()

    return create_access_token(
        data={"sub": str(usuario.id_usuario), "id_clinica": id_clinica, "rol": rol.value},
        expires_delta=timedelta(minutes=10),
    )


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_ciclo_completo_de_metodos_de_pago(client, db_session):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")

    creado = client.post("/metodos-pago", headers=_auth(token), json={"nombre": "Efectivo"})
    assert creado.status_code == 201
    id_metodo = creado.json()["id_metodo_pago"]

    client.post("/metodos-pago", headers=_auth(token), json={"nombre": "Tarjeta"})
    assert [m["nombre"] for m in client.get("/metodos-pago", headers=_auth(token)).json()] == [
        "Efectivo",
        "Tarjeta",
    ]

    assert client.delete(f"/metodos-pago/{id_metodo}", headers=_auth(token)).status_code == 204
    assert [m["nombre"] for m in client.get("/metodos-pago", headers=_auth(token)).json()] == [
        "Tarjeta"
    ]


def test_metodo_pago_duplicado_devuelve_409(client, db_session):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")
    client.post("/metodos-pago", headers=_auth(token), json={"nombre": "Efectivo"})

    assert client.post(
        "/metodos-pago", headers=_auth(token), json={"nombre": "efectivo"}
    ).status_code == 409


def test_metodos_de_pago_de_otra_clinica_no_se_ven(client, db_session):
    from app.models import RolUsuario

    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    token_a = _token_para(db_session, RolUsuario.ADMIN, clinica_a.id_clinica, "admin.a")
    token_b = _token_para(db_session, RolUsuario.ADMIN, clinica_b.id_clinica, "admin.b")
    client.post("/metodos-pago", headers=_auth(token_a), json={"nombre": "Efectivo"})

    assert client.get("/metodos-pago", headers=_auth(token_b)).json() == []


@pytest.mark.parametrize("rol_nombre", ["DOCTOR", "ASISTENTE"])
def test_el_doctor_y_el_asistente_leen_metodos_de_pago_pero_no_escriben(
    client, db_session, rol_nombre
):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    rol = getattr(RolUsuario, rol_nombre)
    token = _token_para(db_session, rol, clinica.id_clinica, f"user.{rol_nombre.lower()}")

    assert client.get("/metodos-pago", headers=_auth(token)).status_code == 200
    assert client.post(
        "/metodos-pago", headers=_auth(token), json={"nombre": "Efectivo"}
    ).status_code == 403
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_consultorios_routes.py tests/test_metodos_pago_routes.py -v`
Expected: FAIL — `404` en todas las rutas, los routers no existen.

- [ ] **Step 3: Escribir el router de consultorios**

Crear `backend/app/api/routes/consultorios.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles, resolve_clinica_id
from app.db import get_db
from app.exceptions import NombreDuplicadoEnClinicaError
from app.models import RolUsuario
from app.repositories.consultorio_repository import ConsultorioRepository
from app.schemas.parametros import (
    CatalogoCreateRequest,
    CatalogoUpdateRequest,
    ConsultorioResponse,
)

LECTURA = require_roles(
    RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.DOCTOR, RolUsuario.ASISTENTE
)
ESCRITURA = require_roles(RolUsuario.SUPERADMIN, RolUsuario.ADMIN)

router = APIRouter(prefix="/consultorios", tags=["consultorios"])

NO_ENCONTRADO = "Consultorio no encontrado"
DUPLICADO = "Ya existe un consultorio con ese nombre en esta clinica"


@router.get("", response_model=list[ConsultorioResponse], dependencies=[Depends(LECTURA)])
def listar_consultorios(
    incluir_inactivos: bool = False,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> list[ConsultorioResponse]:
    registros = ConsultorioRepository(db).listar(id_clinica, incluir_inactivos)
    return [ConsultorioResponse.model_validate(r) for r in registros]


@router.post(
    "",
    response_model=ConsultorioResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(ESCRITURA)],
)
def crear_consultorio(
    body: CatalogoCreateRequest,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> ConsultorioResponse:
    try:
        registro = ConsultorioRepository(db).crear(id_clinica, body.model_dump())
    except NombreDuplicadoEnClinicaError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICADO)
    db.commit()
    return ConsultorioResponse.model_validate(registro)


@router.get(
    "/{id_consultorio}", response_model=ConsultorioResponse, dependencies=[Depends(LECTURA)]
)
def obtener_consultorio(
    id_consultorio: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> ConsultorioResponse:
    registro = ConsultorioRepository(db).obtener(id_clinica, id_consultorio)
    if registro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    return ConsultorioResponse.model_validate(registro)


@router.put(
    "/{id_consultorio}", response_model=ConsultorioResponse, dependencies=[Depends(ESCRITURA)]
)
def actualizar_consultorio(
    id_consultorio: int,
    body: CatalogoUpdateRequest,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> ConsultorioResponse:
    try:
        registro = ConsultorioRepository(db).actualizar(
            id_clinica, id_consultorio, body.model_dump(exclude_unset=True)
        )
    except NombreDuplicadoEnClinicaError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICADO)
    if registro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    db.commit()
    return ConsultorioResponse.model_validate(registro)


@router.delete(
    "/{id_consultorio}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(ESCRITURA)],
)
def eliminar_consultorio(
    id_consultorio: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> Response:
    if not ConsultorioRepository(db).eliminar(id_clinica, id_consultorio):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 4: Escribir el router de métodos de pago**

Crear `backend/app/api/routes/metodos_pago.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles, resolve_clinica_id
from app.db import get_db
from app.exceptions import NombreDuplicadoEnClinicaError
from app.models import RolUsuario
from app.repositories.metodo_pago_repository import MetodoPagoRepository
from app.schemas.parametros import (
    CatalogoCreateRequest,
    CatalogoUpdateRequest,
    MetodoPagoResponse,
)

LECTURA = require_roles(
    RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.DOCTOR, RolUsuario.ASISTENTE
)
ESCRITURA = require_roles(RolUsuario.SUPERADMIN, RolUsuario.ADMIN)

router = APIRouter(prefix="/metodos-pago", tags=["metodos de pago"])

NO_ENCONTRADO = "Metodo de pago no encontrado"
DUPLICADO = "Ya existe un metodo de pago con ese nombre en esta clinica"


@router.get("", response_model=list[MetodoPagoResponse], dependencies=[Depends(LECTURA)])
def listar_metodos_pago(
    incluir_inactivos: bool = False,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> list[MetodoPagoResponse]:
    registros = MetodoPagoRepository(db).listar(id_clinica, incluir_inactivos)
    return [MetodoPagoResponse.model_validate(r) for r in registros]


@router.post(
    "",
    response_model=MetodoPagoResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(ESCRITURA)],
)
def crear_metodo_pago(
    body: CatalogoCreateRequest,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> MetodoPagoResponse:
    try:
        registro = MetodoPagoRepository(db).crear(id_clinica, body.model_dump())
    except NombreDuplicadoEnClinicaError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICADO)
    db.commit()
    return MetodoPagoResponse.model_validate(registro)


@router.get(
    "/{id_metodo_pago}", response_model=MetodoPagoResponse, dependencies=[Depends(LECTURA)]
)
def obtener_metodo_pago(
    id_metodo_pago: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> MetodoPagoResponse:
    registro = MetodoPagoRepository(db).obtener(id_clinica, id_metodo_pago)
    if registro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    return MetodoPagoResponse.model_validate(registro)


@router.put(
    "/{id_metodo_pago}", response_model=MetodoPagoResponse, dependencies=[Depends(ESCRITURA)]
)
def actualizar_metodo_pago(
    id_metodo_pago: int,
    body: CatalogoUpdateRequest,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> MetodoPagoResponse:
    try:
        registro = MetodoPagoRepository(db).actualizar(
            id_clinica, id_metodo_pago, body.model_dump(exclude_unset=True)
        )
    except NombreDuplicadoEnClinicaError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICADO)
    if registro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    db.commit()
    return MetodoPagoResponse.model_validate(registro)


@router.delete(
    "/{id_metodo_pago}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(ESCRITURA)],
)
def eliminar_metodo_pago(
    id_metodo_pago: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> Response:
    if not MetodoPagoRepository(db).eliminar(id_clinica, id_metodo_pago):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 5: Registrar los dos routers**

Modificar `backend/app/main.py` — queda así completo:

```python
from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.clinicas import router as clinicas_router
from app.api.routes.consultorios import router as consultorios_router
from app.api.routes.especialidades import router as especialidades_router
from app.api.routes.metodos_pago import router as metodos_pago_router

app = FastAPI(title="Clinica Dental Web API")
app.include_router(auth_router)
app.include_router(clinicas_router)
app.include_router(especialidades_router)
app.include_router(consultorios_router)
app.include_router(metodos_pago_router)
```

- [ ] **Step 6: Correr los tests y verificar que pasan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_consultorios_routes.py tests/test_metodos_pago_routes.py -v`
Expected: PASS — 10 passed

- [ ] **Step 7: Punto de commit (lo ejecuta Meli)**

```bash
git add backend/app/api/routes/consultorios.py backend/app/api/routes/metodos_pago.py \
        backend/app/main.py backend/tests/test_consultorios_routes.py \
        backend/tests/test_metodos_pago_routes.py
git commit -m "feat(backend): endpoints de consultorios y metodos de pago"
```

---

## Task 7: `HorarioClinicaRepository`

**Files:**
- Create: `backend/app/repositories/horario_clinica_repository.py`
- Test: `backend/tests/test_horario_clinica_repository.py`

**Interfaces:**
- Consumes: `HorarioClinica`, `DiaSemana` (Task 1), `HorarioInvalidoError` (Task 2).
- Produces: `HorarioClinicaRepository(db)` con
  `listar_semana(id_clinica) -> list[HorarioClinica]` (ordenado lunes→domingo) y
  `reemplazar_semana(id_clinica, dias: list[dict]) -> list[HorarioClinica]`, donde cada dict tiene
  las claves `dia_semana: DiaSemana`, `hora_apertura: time | None`, `hora_cierre: time | None`,
  `cerrado: bool`.

> **No hereda de `BaseRepository`**, misma excepción documentada que `ClinicaModuloRepository`: la
> llave es compuesta (`id_clinica` + `dia_semana`), no un `int` simple como asume la firma base.
> Sí exige `id_clinica` como primer parámetro en todos sus métodos.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `backend/tests/test_horario_clinica_repository.py`:

```python
from datetime import time

import pytest


def _clinica(db_session, nombre="Dental A"):
    from app.models import Clinica

    clinica = Clinica(nombre=nombre)
    db_session.add(clinica)
    db_session.flush()
    return clinica


def _semana_laboral():
    from app.models import DiaSemana

    dias = []
    for dia in DiaSemana:
        if dia in (DiaSemana.SABADO, DiaSemana.DOMINGO):
            dias.append(
                {"dia_semana": dia, "hora_apertura": None, "hora_cierre": None, "cerrado": True}
            )
        else:
            dias.append(
                {
                    "dia_semana": dia,
                    "hora_apertura": time(8, 0),
                    "hora_cierre": time(17, 0),
                    "cerrado": False,
                }
            )
    return dias


def _repo(db_session):
    from app.repositories.horario_clinica_repository import HorarioClinicaRepository

    return HorarioClinicaRepository(db_session)


def test_listar_semana_sin_datos_devuelve_vacio(db_session):
    clinica = _clinica(db_session)

    assert _repo(db_session).listar_semana(clinica.id_clinica) == []


def test_reemplazar_semana_crea_los_siete_dias_ordenados(db_session):
    from app.models import DiaSemana

    clinica = _clinica(db_session)

    _repo(db_session).reemplazar_semana(clinica.id_clinica, _semana_laboral())

    guardados = _repo(db_session).listar_semana(clinica.id_clinica)
    assert [f.dia_semana for f in guardados] == list(DiaSemana)
    assert guardados[0].hora_apertura == time(8, 0)
    assert guardados[-1].cerrado is True


def test_reemplazar_semana_dos_veces_actualiza_en_vez_de_duplicar(db_session):
    clinica = _clinica(db_session)
    repo = _repo(db_session)
    repo.reemplazar_semana(clinica.id_clinica, _semana_laboral())

    nueva = _semana_laboral()
    nueva[0]["hora_cierre"] = time(20, 0)
    repo.reemplazar_semana(clinica.id_clinica, nueva)

    guardados = repo.listar_semana(clinica.id_clinica)
    assert len(guardados) == 7
    assert guardados[0].hora_cierre == time(20, 0)


def test_un_dia_cerrado_guarda_las_horas_en_null(db_session):
    from app.models import DiaSemana

    clinica = _clinica(db_session)
    dias = _semana_laboral()
    dias[0] = {
        "dia_semana": DiaSemana.LUNES,
        "hora_apertura": time(8, 0),
        "hora_cierre": time(17, 0),
        "cerrado": True,
    }

    _repo(db_session).reemplazar_semana(clinica.id_clinica, dias)

    lunes = _repo(db_session).listar_semana(clinica.id_clinica)[0]
    assert lunes.cerrado is True
    assert lunes.hora_apertura is None
    assert lunes.hora_cierre is None


def test_hora_de_cierre_anterior_a_la_de_apertura_lanza_error(db_session):
    from app.exceptions import HorarioInvalidoError

    clinica = _clinica(db_session)
    dias = _semana_laboral()
    dias[0]["hora_cierre"] = time(7, 0)

    with pytest.raises(HorarioInvalidoError):
        _repo(db_session).reemplazar_semana(clinica.id_clinica, dias)


def test_dia_abierto_sin_horas_lanza_error(db_session):
    from app.exceptions import HorarioInvalidoError

    clinica = _clinica(db_session)
    dias = _semana_laboral()
    dias[0]["hora_apertura"] = None

    with pytest.raises(HorarioInvalidoError):
        _repo(db_session).reemplazar_semana(clinica.id_clinica, dias)


def test_si_un_dia_es_invalido_no_se_guarda_ninguno(db_session):
    from app.exceptions import HorarioInvalidoError

    clinica = _clinica(db_session)
    dias = _semana_laboral()
    dias[4]["hora_cierre"] = time(1, 0)

    with pytest.raises(HorarioInvalidoError):
        _repo(db_session).reemplazar_semana(clinica.id_clinica, dias)

    assert _repo(db_session).listar_semana(clinica.id_clinica) == []


def test_el_horario_de_una_clinica_no_afecta_a_otra(db_session):
    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")

    _repo(db_session).reemplazar_semana(clinica_a.id_clinica, _semana_laboral())

    assert len(_repo(db_session).listar_semana(clinica_a.id_clinica)) == 7
    assert _repo(db_session).listar_semana(clinica_b.id_clinica) == []
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_horario_clinica_repository.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.repositories.horario_clinica_repository'`

- [ ] **Step 3: Escribir el repositorio**

Crear `backend/app/repositories/horario_clinica_repository.py`:

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import HorarioInvalidoError
from app.models import DiaSemana, HorarioClinica

_ORDEN_DIAS = {dia: indice for indice, dia in enumerate(DiaSemana)}


class HorarioClinicaRepository:
    """Horario de atencion de la clinica, una fila por dia.

    NO hereda de BaseRepository porque la llave es compuesta
    (id_clinica + dia_semana), no un int simple como asume esa firma. Misma
    excepcion documentada que ClinicaModuloRepository. Aun asi, todos sus
    metodos exigen id_clinica como primer parametro.
    """

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _validar_dia(dia: dict) -> None:
        if dia.get("cerrado", False):
            return

        apertura = dia.get("hora_apertura")
        cierre = dia.get("hora_cierre")
        nombre_dia = dia["dia_semana"].value

        if apertura is None or cierre is None:
            raise HorarioInvalidoError(
                f"{nombre_dia}: un dia abierto necesita hora de apertura y de cierre"
            )
        if cierre <= apertura:
            raise HorarioInvalidoError(
                f"{nombre_dia}: la hora de cierre debe ser posterior a la de apertura"
            )

    def listar_semana(self, id_clinica: int) -> list[HorarioClinica]:
        stmt = select(HorarioClinica).where(HorarioClinica.id_clinica == id_clinica)
        filas = list(self.db.execute(stmt).scalars().all())
        return sorted(filas, key=lambda fila: _ORDEN_DIAS[fila.dia_semana])

    def reemplazar_semana(self, id_clinica: int, dias: list[dict]) -> list[HorarioClinica]:
        """Upsert de los dias recibidos. Valida TODOS antes de escribir ninguno,
        para que un dia invalido no deje la semana a medias.
        """
        for dia in dias:
            self._validar_dia(dia)

        existentes = {fila.dia_semana: fila for fila in self.listar_semana(id_clinica)}

        for dia in dias:
            cerrado = dia.get("cerrado", False)
            apertura = None if cerrado else dia.get("hora_apertura")
            cierre = None if cerrado else dia.get("hora_cierre")

            fila = existentes.get(dia["dia_semana"])
            if fila is None:
                fila = HorarioClinica(
                    id_clinica=id_clinica,
                    dia_semana=dia["dia_semana"],
                    hora_apertura=apertura,
                    hora_cierre=cierre,
                    cerrado=cerrado,
                )
                self.db.add(fila)
            else:
                fila.hora_apertura = apertura
                fila.hora_cierre = cierre
                fila.cerrado = cerrado

        self.db.flush()
        return self.listar_semana(id_clinica)
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_horario_clinica_repository.py -v`
Expected: PASS — 8 passed

- [ ] **Step 5: Punto de commit (lo ejecuta Meli)**

```bash
git add backend/app/repositories/horario_clinica_repository.py \
        backend/tests/test_horario_clinica_repository.py
git commit -m "feat(backend): repositorio del horario de atencion por clinica"
```

---

## Task 8: Endpoints del horario de atención

**Files:**
- Modify: `backend/app/schemas/parametros.py`
- Create: `backend/app/api/routes/horarios.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_horarios_routes.py`

**Interfaces:**
- Consumes: `HorarioClinicaRepository` (Task 7), `HORARIO_POR_DEFECTO` y `DiaSemana` (Task 1).
- Produces: `HorarioDiaSchema` (`dia_semana`, `hora_apertura`, `hora_cierre`, `cerrado`) y
  `HorarioSemanaRequest` (`dias: list[HorarioDiaSchema]`, exactamente 7 sin repetidos).
  Rutas `GET /horarios` y `PUT /horarios`.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `backend/tests/test_horarios_routes.py`:

```python
from datetime import timedelta


def _clinica(db_session, nombre="Dental A"):
    from app.models import Clinica

    clinica = Clinica(nombre=nombre)
    db_session.add(clinica)
    db_session.commit()
    return clinica


def _token_para(db_session, rol, id_clinica=None, username="user.test"):
    from app.models import Usuario
    from app.security.jwt import create_access_token
    from app.security.passwords import hash_password

    usuario = Usuario(
        id_clinica=id_clinica,
        username=username,
        password_hash=hash_password("clave123"),
        rol=rol,
    )
    db_session.add(usuario)
    db_session.commit()

    return create_access_token(
        data={"sub": str(usuario.id_usuario), "id_clinica": id_clinica, "rol": rol.value},
        expires_delta=timedelta(minutes=10),
    )


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _cuerpo_semana():
    from app.models import DiaSemana

    dias = []
    for dia in DiaSemana:
        if dia in (DiaSemana.SABADO, DiaSemana.DOMINGO):
            dias.append(
                {
                    "dia_semana": dia.value,
                    "hora_apertura": None,
                    "hora_cierre": None,
                    "cerrado": True,
                }
            )
        else:
            dias.append(
                {
                    "dia_semana": dia.value,
                    "hora_apertura": "08:00:00",
                    "hora_cierre": "17:00:00",
                    "cerrado": False,
                }
            )
    return {"dias": dias}


def test_get_sin_datos_devuelve_los_siete_dias_con_defaults(client, db_session):
    from app.models import HorarioClinica, RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")

    respuesta = client.get("/horarios", headers=_auth(token))

    assert respuesta.status_code == 200
    dias = respuesta.json()
    assert [d["dia_semana"] for d in dias] == [
        "lunes",
        "martes",
        "miercoles",
        "jueves",
        "viernes",
        "sabado",
        "domingo",
    ]
    assert dias[0]["hora_apertura"] == "08:00:00"
    assert dias[0]["cerrado"] is False
    assert dias[5]["cerrado"] is True
    assert dias[5]["hora_apertura"] is None

    # el GET no debe persistir nada
    assert db_session.query(HorarioClinica).count() == 0


def test_put_guarda_la_semana_y_el_get_la_devuelve(client, db_session):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")
    cuerpo = _cuerpo_semana()
    cuerpo["dias"][5] = {
        "dia_semana": "sabado",
        "hora_apertura": "08:00:00",
        "hora_cierre": "12:00:00",
        "cerrado": False,
    }

    guardado = client.put("/horarios", headers=_auth(token), json=cuerpo)

    assert guardado.status_code == 200
    sabado = client.get("/horarios", headers=_auth(token)).json()[5]
    assert sabado["hora_cierre"] == "12:00:00"
    assert sabado["cerrado"] is False


def test_put_con_hora_de_cierre_invalida_devuelve_422(client, db_session):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")
    cuerpo = _cuerpo_semana()
    cuerpo["dias"][0]["hora_cierre"] = "07:00:00"

    assert client.put("/horarios", headers=_auth(token), json=cuerpo).status_code == 422


def test_put_con_menos_de_siete_dias_devuelve_422(client, db_session):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")
    cuerpo = _cuerpo_semana()
    cuerpo["dias"] = cuerpo["dias"][:5]

    assert client.put("/horarios", headers=_auth(token), json=cuerpo).status_code == 422


def test_el_horario_de_una_clinica_no_se_ve_desde_otra(client, db_session):
    from app.models import RolUsuario

    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    token_a = _token_para(db_session, RolUsuario.ADMIN, clinica_a.id_clinica, "admin.a")
    token_b = _token_para(db_session, RolUsuario.ADMIN, clinica_b.id_clinica, "admin.b")
    cuerpo = _cuerpo_semana()
    cuerpo["dias"][0]["hora_cierre"] = "20:00:00"
    client.put("/horarios", headers=_auth(token_a), json=cuerpo)

    lunes_b = client.get("/horarios", headers=_auth(token_b)).json()[0]

    assert lunes_b["hora_cierre"] == "17:00:00"  # sigue viendo el default


def test_el_doctor_lee_el_horario_pero_no_lo_edita(client, db_session):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.DOCTOR, clinica.id_clinica, "doc.a")

    assert client.get("/horarios", headers=_auth(token)).status_code == 200
    assert client.put(
        "/horarios", headers=_auth(token), json=_cuerpo_semana()
    ).status_code == 403
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_horarios_routes.py -v`
Expected: FAIL — `404`, el router no existe.

- [ ] **Step 3: Agregar los schemas del horario**

Agregar al final de `backend/app/schemas/parametros.py`:

```python
from datetime import time

from app.models import DiaSemana


class HorarioDiaSchema(BaseModel):
    dia_semana: DiaSemana
    hora_apertura: time | None = None
    hora_cierre: time | None = None
    cerrado: bool = False

    model_config = {"from_attributes": True}


class HorarioSemanaRequest(BaseModel):
    dias: list[HorarioDiaSchema]

    @field_validator("dias")
    @classmethod
    def _deben_ser_los_siete_dias(cls, valor: list[HorarioDiaSchema]) -> list[HorarioDiaSchema]:
        recibidos = [dia.dia_semana for dia in valor]
        if len(recibidos) != len(set(recibidos)) or set(recibidos) != set(DiaSemana):
            raise ValueError("Hay que enviar exactamente los 7 dias de la semana, sin repetidos")
        return valor
```

> Los `import` van arriba del archivo junto a los existentes, no al final: subí
> `from datetime import time` y `from app.models import DiaSemana` al bloque de imports.

- [ ] **Step 4: Escribir el router**

Crear `backend/app/api/routes/horarios.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles, resolve_clinica_id
from app.db import get_db
from app.exceptions import HorarioInvalidoError
from app.models import HORARIO_POR_DEFECTO, DiaSemana, RolUsuario
from app.repositories.horario_clinica_repository import HorarioClinicaRepository
from app.schemas.parametros import HorarioDiaSchema, HorarioSemanaRequest

LECTURA = require_roles(
    RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.DOCTOR, RolUsuario.ASISTENTE
)
ESCRITURA = require_roles(RolUsuario.SUPERADMIN, RolUsuario.ADMIN)

router = APIRouter(prefix="/horarios", tags=["horario de atencion"])


def _semana_completa(filas) -> list[HorarioDiaSchema]:
    """Devuelve siempre los 7 dias: los que no tienen fila salen con el default,
    sin persistirlos. Asi el frontend nunca tiene que rellenar huecos.
    """
    existentes = {fila.dia_semana: fila for fila in filas}
    semana = []
    for dia in DiaSemana:
        fila = existentes.get(dia)
        if fila is None:
            semana.append(HorarioDiaSchema(dia_semana=dia, **HORARIO_POR_DEFECTO[dia]))
        else:
            semana.append(HorarioDiaSchema.model_validate(fila))
    return semana


@router.get("", response_model=list[HorarioDiaSchema], dependencies=[Depends(LECTURA)])
def obtener_horario(
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> list[HorarioDiaSchema]:
    return _semana_completa(HorarioClinicaRepository(db).listar_semana(id_clinica))


@router.put("", response_model=list[HorarioDiaSchema], dependencies=[Depends(ESCRITURA)])
def reemplazar_horario(
    body: HorarioSemanaRequest,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> list[HorarioDiaSchema]:
    try:
        filas = HorarioClinicaRepository(db).reemplazar_semana(
            id_clinica, [dia.model_dump() for dia in body.dias]
        )
    except HorarioInvalidoError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        )
    db.commit()
    return _semana_completa(filas)
```

- [ ] **Step 5: Registrar el router**

Modificar `backend/app/main.py` — agregar el import y el `include_router`:

```python
from app.api.routes.horarios import router as horarios_router

app.include_router(horarios_router)
```

- [ ] **Step 6: Correr los tests y verificar que pasan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_horarios_routes.py -v`
Expected: PASS — 6 passed

- [ ] **Step 7: Punto de commit (lo ejecuta Meli)**

```bash
git add backend/app/schemas/parametros.py backend/app/api/routes/horarios.py \
        backend/app/main.py backend/tests/test_horarios_routes.py
git commit -m "feat(backend): endpoints del horario de atencion de la clinica"
```

---

## Task 9: `ConfiguracionClinicaRepository`

**Files:**
- Create: `backend/app/repositories/configuracion_repository.py`
- Test: `backend/tests/test_configuracion_repository.py`

**Interfaces:**
- Consumes: `ConfiguracionClinica` (Task 1).
- Produces: `ConfiguracionClinicaRepository(db)` con
  `obtener_o_crear(id_clinica) -> ConfiguracionClinica` y
  `actualizar(id_clinica, data: dict) -> ConfiguracionClinica`.

> **No hereda de `BaseRepository`**: la relación es 1:1 y la PK *es* `id_clinica`, así que
> `obtener(id_clinica, id_)` no tendría sentido. Los valores por defecto viven únicamente en el
> modelo; este repositorio no los repite.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `backend/tests/test_configuracion_repository.py`:

```python
from decimal import Decimal


def _clinica(db_session, nombre="Dental A"):
    from app.models import Clinica

    clinica = Clinica(nombre=nombre)
    db_session.add(clinica)
    db_session.flush()
    return clinica


def _repo(db_session):
    from app.repositories.configuracion_repository import ConfiguracionClinicaRepository

    return ConfiguracionClinicaRepository(db_session)


def test_obtener_o_crear_crea_con_los_defaults(db_session):
    clinica = _clinica(db_session)

    config = _repo(db_session).obtener_o_crear(clinica.id_clinica)

    assert config.id_clinica == clinica.id_clinica
    assert config.duracion_cita_minutos == 30
    assert Decimal(config.porcentaje_impuesto) == Decimal("13.00")
    assert config.horas_minimas_cambio_cita == 24
    assert config.dias_minimos_reagendamiento == 3


def test_obtener_o_crear_es_idempotente(db_session):
    from app.models import ConfiguracionClinica

    clinica = _clinica(db_session)
    repo = _repo(db_session)

    primera = repo.obtener_o_crear(clinica.id_clinica)
    segunda = repo.obtener_o_crear(clinica.id_clinica)

    assert primera is segunda
    assert db_session.query(ConfiguracionClinica).count() == 1


def test_actualizar_aplica_solo_los_campos_presentes(db_session):
    clinica = _clinica(db_session)
    repo = _repo(db_session)
    repo.obtener_o_crear(clinica.id_clinica)

    config = repo.actualizar(clinica.id_clinica, {"duracion_cita_minutos": 45})

    assert config.duracion_cita_minutos == 45
    assert Decimal(config.porcentaje_impuesto) == Decimal("13.00")


def test_actualizar_sobre_una_clinica_sin_configuracion_la_crea(db_session):
    clinica = _clinica(db_session)

    config = _repo(db_session).actualizar(clinica.id_clinica, {"prefijo_factura": "FAC"})

    assert config.prefijo_factura == "FAC"
    assert config.duracion_cita_minutos == 30


def test_la_configuracion_de_una_clinica_no_afecta_a_otra(db_session):
    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    repo = _repo(db_session)

    repo.actualizar(clinica_a.id_clinica, {"duracion_cita_minutos": 60})

    assert repo.obtener_o_crear(clinica_b.id_clinica).duracion_cita_minutos == 30
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_configuracion_repository.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.repositories.configuracion_repository'`

- [ ] **Step 3: Escribir el repositorio**

Crear `backend/app/repositories/configuracion_repository.py`:

```python
from sqlalchemy.orm import Session

from app.models import ConfiguracionClinica


class ConfiguracionClinicaRepository:
    """Configuracion 1:1 de una clinica.

    NO hereda de BaseRepository: la relacion es 1:1 y la PK ES id_clinica, asi
    que obtener(id_clinica, id_) no tendria sentido. Los valores por defecto
    viven unicamente en el modelo; aca no se repiten.
    """

    def __init__(self, db: Session):
        self.db = db

    def obtener_o_crear(self, id_clinica: int) -> ConfiguracionClinica:
        """Devuelve la configuracion de la clinica, creandola con los defaults del
        modelo si todavia no existe. Idempotente.
        """
        config = self.db.get(ConfiguracionClinica, id_clinica)
        if config is None:
            config = ConfiguracionClinica(id_clinica=id_clinica)
            self.db.add(config)
            self.db.flush()
        return config

    def actualizar(self, id_clinica: int, data: dict) -> ConfiguracionClinica:
        config = self.obtener_o_crear(id_clinica)
        for campo, valor in data.items():
            setattr(config, campo, valor)
        self.db.flush()
        return config
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_configuracion_repository.py -v`
Expected: PASS — 5 passed

- [ ] **Step 5: Punto de commit (lo ejecuta Meli)**

```bash
git add backend/app/repositories/configuracion_repository.py \
        backend/tests/test_configuracion_repository.py
git commit -m "feat(backend): repositorio de la configuracion por clinica"
```

---

## Task 10: Endpoints de configuración

**Files:**
- Modify: `backend/app/schemas/parametros.py`
- Create: `backend/app/api/routes/configuracion.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_configuracion_routes.py`

**Interfaces:**
- Consumes: `ConfiguracionClinicaRepository` (Task 9).
- Produces: `ConfiguracionResponse` (los 6 campos) y `ConfiguracionUpdateRequest` (los 6 campos
  opcionales con sus rangos). Rutas `GET /configuracion` y `PUT /configuracion`.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `backend/tests/test_configuracion_routes.py`:

```python
from datetime import timedelta

import pytest


def _clinica(db_session, nombre="Dental A"):
    from app.models import Clinica

    clinica = Clinica(nombre=nombre)
    db_session.add(clinica)
    db_session.commit()
    return clinica


def _token_para(db_session, rol, id_clinica=None, username="user.test"):
    from app.models import Usuario
    from app.security.jwt import create_access_token
    from app.security.passwords import hash_password

    usuario = Usuario(
        id_clinica=id_clinica,
        username=username,
        password_hash=hash_password("clave123"),
        rol=rol,
    )
    db_session.add(usuario)
    db_session.commit()

    return create_access_token(
        data={"sub": str(usuario.id_usuario), "id_clinica": id_clinica, "rol": rol.value},
        expires_delta=timedelta(minutes=10),
    )


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_get_crea_la_configuracion_al_vuelo_con_los_defaults(client, db_session):
    from app.models import ConfiguracionClinica, RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")

    respuesta = client.get("/configuracion", headers=_auth(token))

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["duracion_cita_minutos"] == 30
    assert float(cuerpo["porcentaje_impuesto"]) == 13.00
    assert cuerpo["prefijo_factura"] == "F"
    assert cuerpo["proximo_numero_factura"] == 1
    assert cuerpo["horas_minimas_cambio_cita"] == 24
    assert cuerpo["dias_minimos_reagendamiento"] == 3
    assert db_session.query(ConfiguracionClinica).count() == 1


def test_get_dos_veces_no_duplica_la_fila(client, db_session):
    from app.models import ConfiguracionClinica, RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")

    client.get("/configuracion", headers=_auth(token))
    client.get("/configuracion", headers=_auth(token))

    assert db_session.query(ConfiguracionClinica).count() == 1


def test_put_actualiza_solo_lo_enviado(client, db_session):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")

    respuesta = client.put(
        "/configuracion", headers=_auth(token), json={"duracion_cita_minutos": 45}
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["duracion_cita_minutos"] == 45
    assert float(respuesta.json()["porcentaje_impuesto"]) == 13.00


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("duracion_cita_minutos", 4),
        ("duracion_cita_minutos", 481),
        ("porcentaje_impuesto", -1),
        ("porcentaje_impuesto", 101),
        ("proximo_numero_factura", 0),
        ("horas_minimas_cambio_cita", 0),
        ("horas_minimas_cambio_cita", 721),
        ("dias_minimos_reagendamiento", 0),
        ("dias_minimos_reagendamiento", 91),
    ],
)
def test_valores_fuera_de_rango_devuelven_422(client, db_session, campo, valor):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")

    assert client.put(
        "/configuracion", headers=_auth(token), json={campo: valor}
    ).status_code == 422


def test_la_configuracion_de_una_clinica_no_se_ve_desde_otra(client, db_session):
    from app.models import RolUsuario

    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    token_a = _token_para(db_session, RolUsuario.ADMIN, clinica_a.id_clinica, "admin.a")
    token_b = _token_para(db_session, RolUsuario.ADMIN, clinica_b.id_clinica, "admin.b")
    client.put("/configuracion", headers=_auth(token_a), json={"duracion_cita_minutos": 60})

    assert client.get("/configuracion", headers=_auth(token_b)).json()[
        "duracion_cita_minutos"
    ] == 30


@pytest.mark.parametrize("rol_nombre", ["DOCTOR", "ASISTENTE"])
def test_doctor_y_asistente_leen_la_configuracion_pero_no_la_editan(
    client, db_session, rol_nombre
):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    rol = getattr(RolUsuario, rol_nombre)
    token = _token_para(db_session, rol, clinica.id_clinica, f"user.{rol_nombre.lower()}")

    assert client.get("/configuracion", headers=_auth(token)).status_code == 200
    assert client.put(
        "/configuracion", headers=_auth(token), json={"duracion_cita_minutos": 45}
    ).status_code == 403
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_configuracion_routes.py -v`
Expected: FAIL — `404`, el router no existe.

- [ ] **Step 3: Agregar los schemas de configuración**

Agregar al final de `backend/app/schemas/parametros.py` (el import de `Decimal` va arriba, con
los demás):

```python
from decimal import Decimal


class ConfiguracionResponse(BaseModel):
    duracion_cita_minutos: int
    porcentaje_impuesto: Decimal
    prefijo_factura: str
    proximo_numero_factura: int
    horas_minimas_cambio_cita: int
    dias_minimos_reagendamiento: int

    model_config = {"from_attributes": True}


class ConfiguracionUpdateRequest(BaseModel):
    """Actualizacion parcial: solo se aplican los campos presentes en el body.

    Los minimos de horas_minimas_cambio_cita y dias_minimos_reagendamiento son 1
    y no 0 a proposito: la regla es configurable en intensidad, pero no se puede
    desactivar.
    """

    duracion_cita_minutos: int | None = Field(default=None, ge=5, le=480)
    porcentaje_impuesto: Decimal | None = Field(default=None, ge=0, le=100)
    prefijo_factura: str | None = Field(default=None, max_length=10)
    proximo_numero_factura: int | None = Field(default=None, ge=1)
    horas_minimas_cambio_cita: int | None = Field(default=None, ge=1, le=720)
    dias_minimos_reagendamiento: int | None = Field(default=None, ge=1, le=90)
```

- [ ] **Step 4: Escribir el router**

Crear `backend/app/api/routes/configuracion.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_roles, resolve_clinica_id
from app.db import get_db
from app.models import RolUsuario
from app.repositories.configuracion_repository import ConfiguracionClinicaRepository
from app.schemas.parametros import ConfiguracionResponse, ConfiguracionUpdateRequest

LECTURA = require_roles(
    RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.DOCTOR, RolUsuario.ASISTENTE
)
ESCRITURA = require_roles(RolUsuario.SUPERADMIN, RolUsuario.ADMIN)

router = APIRouter(prefix="/configuracion", tags=["configuracion de clinica"])


@router.get("", response_model=ConfiguracionResponse, dependencies=[Depends(LECTURA)])
def obtener_configuracion(
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> ConfiguracionResponse:
    """Si la clinica todavia no tiene configuracion, se crea con los defaults.

    Es la unica lectura del modulo que escribe: se decidio asi para no tocar
    ClinicaService (Modulo 2) ni migrar datos de las clinicas preexistentes.
    """
    config = ConfiguracionClinicaRepository(db).obtener_o_crear(id_clinica)
    db.commit()
    return ConfiguracionResponse.model_validate(config)


@router.put("", response_model=ConfiguracionResponse, dependencies=[Depends(ESCRITURA)])
def actualizar_configuracion(
    body: ConfiguracionUpdateRequest,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> ConfiguracionResponse:
    config = ConfiguracionClinicaRepository(db).actualizar(
        id_clinica, body.model_dump(exclude_unset=True)
    )
    db.commit()
    return ConfiguracionResponse.model_validate(config)
```

- [ ] **Step 5: Registrar el router**

Modificar `backend/app/main.py` — queda así completo:

```python
from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.clinicas import router as clinicas_router
from app.api.routes.configuracion import router as configuracion_router
from app.api.routes.consultorios import router as consultorios_router
from app.api.routes.especialidades import router as especialidades_router
from app.api.routes.horarios import router as horarios_router
from app.api.routes.metodos_pago import router as metodos_pago_router

app = FastAPI(title="Clinica Dental Web API")
app.include_router(auth_router)
app.include_router(clinicas_router)
app.include_router(especialidades_router)
app.include_router(consultorios_router)
app.include_router(metodos_pago_router)
app.include_router(horarios_router)
app.include_router(configuracion_router)
```

- [ ] **Step 6: Correr los tests y verificar que pasan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_configuracion_routes.py -v`
Expected: PASS — 15 passed (6 casos sueltos + 9 parametrizados de rango + los de permisos)

- [ ] **Step 7: Punto de commit (lo ejecuta Meli)**

```bash
git add backend/app/schemas/parametros.py backend/app/api/routes/configuracion.py \
        backend/app/main.py backend/tests/test_configuracion_routes.py
git commit -m "feat(backend): endpoints de configuracion por clinica"
```

---

## Task 11: Verificación final contra MySQL real

**Files:**
- Ninguno nuevo. Es el gate de cierre del módulo.

**Interfaces:**
- Consumes: todo lo construido en las Tasks 1 a 10.
- Produces: la confirmación de que el módulo funciona contra MySQL, no solo contra SQLite.

> **Por qué existe este task:** los tests corren contra SQLite en memoria, que no tiene tipo `ENUM`
> nativo. El bug conocido #2 del `CONTEXTO-PROYECTO.md` (SQLAlchemy persistiendo `LUNES` en vez de
> `lunes`) **pasa en verde en SQLite y revienta contra MySQL**. Este módulo agrega un enum nuevo
> (`DiaSemana`), así que la verificación no es opcional.

- [ ] **Step 1: Correr la suite completa contra SQLite**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: todos los tests de Módulos 1, 2 y 3 en verde, sin warnings nuevos.

- [ ] **Step 2: Levantar el entorno Docker con MySQL**

Desde la raíz del repo:

```bash
docker compose build backend
docker compose up -d
```

Expected: los contenedores `backend` y `db` quedan corriendo (`docker compose ps` los muestra en
estado `running`).

- [ ] **Step 3: Aplicar las migraciones contra MySQL**

```bash
docker compose exec backend alembic upgrade head
```

Expected: `Running upgrade 0002 -> 0003, parametros por clinica...` sin errores.

- [ ] **Step 4: Verificar que el ENUM se creó con los valores en minúscula**

```bash
docker compose exec db mysql -uroot -p -e "SHOW COLUMNS FROM horario_clinica FROM clinica_dental LIKE 'dia_semana';"
```

Expected: el tipo es
`enum('lunes','martes','miercoles','jueves','viernes','sabado','domingo')`.
Si aparece `enum('LUNES',...)`, falta el `values_callable` en el modelo o los valores en la
migración — corregir antes de seguir.

> Si el nombre de la base o el usuario difieren, tomarlos de `.env` / `docker-compose.yml`.

- [ ] **Step 5: Probar el flujo completo contra MySQL desde `/docs`**

Abrir `http://localhost:8000/docs` y ejecutar en orden:

1. `POST /auth/login` con el superadmin → copiar el `access_token`.
2. `POST /clinicas` → crear una clínica de prueba y anotar su `id_clinica` y la
   `password_temporal` del admin.
3. `POST /auth/login` con ese admin → nuevo token.
4. `POST /especialidades` con `{"nombre": "Ortodoncia"}` → debe devolver `201`.
5. Repetir el mismo `POST` → debe devolver `409`.
6. `GET /horarios` → 7 días, sábado y domingo con `cerrado: true`.
7. `PUT /horarios` con el sábado abierto de 08:00 a 12:00 → `200`, y el `GET` siguiente lo refleja.
8. `GET /configuracion` → `porcentaje_impuesto: 13.00`.
9. `PUT /configuracion` con `{"dias_minimos_reagendamiento": 0}` → debe devolver `422`.

Expected: todos los pasos con el resultado indicado. Cualquier `500` acá es un bug que SQLite
ocultó.

- [ ] **Step 6: Verificar la respuesta de `GET /horarios` con datos reales en la BD**

```bash
docker compose exec db mysql -uroot -p -e "SELECT * FROM clinica_dental.horario_clinica;"
```

Expected: 7 filas para la clínica de prueba, con `dia_semana` en minúscula y sábado con
`hora_apertura = 08:00:00`.

- [ ] **Step 7: Bajar el entorno**

```bash
docker compose down
```

- [ ] **Step 8: Actualizar la documentación del proyecto**

Modificar `docs/CONTEXTO-PROYECTO.md`:

- En la tabla de la sección 2, cambiar el estado del Módulo 3 a `✅ Completo`.
- Agregar una sección "Qué existe ya — Módulo 3" siguiendo el formato de las secciones 5 y 6, que
  cubra: las 5 tablas nuevas, `CatalogoRepository` como el lugar donde se agrega cualquier catálogo
  nuevo por clínica, los dos repositorios que no heredan de `BaseRepository` y por qué, y la regla
  de permisos del módulo (los 4 roles leen, admin y superadmin escriben).
- En la sección 4 (estructura del repo), agregar los archivos nuevos.

- [ ] **Step 9: Punto de commit final (lo ejecuta Meli)**

```bash
git add docs/CONTEXTO-PROYECTO.md
git commit -m "docs: Modulo 3 completo, actualiza el contexto del proyecto"
```

---

## Checklist de cierre del módulo

- [ ] Los 12 archivos de test existen y pasan
- [ ] La suite completa (Módulos 1, 2 y 3) pasa contra SQLite
- [ ] `alembic upgrade head` corre limpio contra MySQL
- [ ] El ENUM `dia_semana` tiene los valores en minúscula en MySQL
- [ ] Ningún repositorio hace `.commit()`
- [ ] Ningún `HTTPException` fuera de `app/api/routes/`
- [ ] Ningún endpoint recibe `id_clinica` por URL o body
- [ ] `ClinicaService` y `MODULOS_DISPONIBLES` quedaron intactos
- [ ] Un admin de la clínica A no puede leer, editar ni borrar nada de la clínica B
- [ ] `docs/CONTEXTO-PROYECTO.md` actualizado
