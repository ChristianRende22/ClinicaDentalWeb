# Módulo 4: Operación Clínica Básica — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir la operación diaria de la clínica — pacientes, doctores, asistentes, la agenda
de disponibilidad de cada doctor, y las citas con todas sus reglas de agendamiento y su máquina de
estados.

**Architecture:** Sigue el patrón de los Módulos 1 a 3 (FastAPI + SQLAlchemy 2.0 + repositorios que
heredan de `BaseRepository`, rutas que consumen `resolve_clinica_id`). Dos novedades. Primera:
aparecen servicios de verdad — `PersonalService` (alta transaccional de `Usuario` + perfil, copiando
`ClinicaService`) y `CitaService`. Segunda, y es el corazón del módulo: las siete reglas de
agendamiento son **objetos validadores independientes** con una interfaz común, y `CitaService` solo
recorre una lista. Agregar una regla es un archivo nuevo, no editar `CitaService`.

**Tech Stack:** Mismo stack de los Módulos 1 a 3 (Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic,
MySQL 8, pytest, SQLite en memoria para tests). **Sin dependencias nuevas.**

**Spec de referencia:** `docs/superpowers/specs/2026-08-02-modulo-4-operacion-clinica-design.md`

## Global Constraints

- **Nunca ejecutar comandos `git`.** Ni `add`, ni `commit`, ni `push`. Los pasos marcados como
  *Punto de commit* son para que Meli los ejecute a mano; el agente solo se detiene ahí y avisa.
- Todos los comandos se corren con `backend/` como directorio de trabajo, usando el venv del
  Módulo 1: `.venv/Scripts/python.exe -m pytest ...`
- **TDD estricto:** test primero, verlo fallar por la razón correcta, después la implementación
  mínima. Nunca implementación antes del test.
- Todo enum nuevo de SQLAlchemy se declara con
  `values_callable=lambda enum_cls: [e.value for e in enum_cls]`. Sin eso SQLAlchemy persiste
  `PROGRAMADA` en vez de `programada`, y el bug **no aparece en SQLite**, solo contra MySQL real
  (bug conocido #2 del `CONTEXTO-PROYECTO.md`).
- Los valores de los enums van **sin tilde** (`no_asistio`), por encoding del tipo ENUM de MySQL.
- `HorarioDoctor.dia_semana` **reutiliza** el enum `DiaSemana` del Módulo 3. No se crea uno nuevo.
- Las comparaciones case-insensitive de texto usan `func.lower()` **explícito** en la query. No
  confiar en el collation: SQLite es case-sensitive por defecto, MySQL con `utf8mb4_general_ci` no.
- Los repositorios hacen `.flush()`, **nunca** `.commit()`. El `.commit()` lo hace la ruta, o el
  servicio cuando coordina una transacción (`PersonalService`).
- Ningún `HTTPException` en repositorios, servicios, validadores ni modelos. Las excepciones de
  dominio viven en `app/exceptions.py`; las rutas las traducen a HTTP.
- Traducción a HTTP: conflicto con el estado del sistema → `409` (`ChoqueDeCitaError`,
  `TransicionInvalidaError`, `UsernameYaExisteError`). Violación de una regla sobre los datos
  enviados → `422` (el resto).
- Nombres de negocio en español. Inglés solo para patrones técnicos genéricos (`BaseRepository`).
- Ningún endpoint recibe `id_clinica` por URL ni por body: siempre
  `id_clinica: int = Depends(resolve_clinica_id)`.
- **Permisos, y acá el Módulo 4 rompe la regla única del Módulo 3 a propósito:** pacientes los
  escriben `admin`, `asistente` y `doctor` (baja solo `admin`); doctores y asistentes solo `admin`;
  citas las crean `admin` y `asistente`; el estado de una cita lo cambian `admin`, `asistente` y el
  doctor de esa cita. `superadmin` puede todo, con `X-Clinica-Id`.
- **El rol `doctor` solo ve sus propias citas, y el filtro es un `WHERE`, no un `403`.**
  `GET /citas` le inyecta `id_doctor = <el suyo>`; `GET /citas/{id}` de una cita ajena devuelve
  `404`. Un `403` le confirmaría que la cita existe.
- Rangos de validación nuevos: `anticipacion_minima_reserva_horas` **1**–720 (mínimo 1, no 0: la
  regla es configurable en intensidad pero no desactivable, mismo criterio que el Módulo 3);
  `duracion_minutos` de una cita 5–480; `telefono` 8–15 caracteres.
- Default de `anticipacion_minima_reserva_horas`: **24**.
- Solo se toca **un** archivo de los Módulos 1 a 3: `app/api/deps.py`, para agregar
  `get_doctor_actual`. **No** se toca `ClinicaService`, `AuthService`, `MODULOS_DISPONIBLES`, ni
  ninguna migración ya aplicada.
- Migración nueva: `0004_operacion_clinica.py`, `down_revision = "0003"`.

---

## File Structure

```
backend/
  alembic/versions/
    0004_operacion_clinica.py                    (create)
  app/
    models/
      personas.py                                (create: Paciente, Doctor, Asistente, HorarioDoctor)
      cita.py                                    (create: Cita, EstadoCita, TRANSICIONES_PERMITIDAS)
      parametros.py                              (modify: + anticipacion_minima_reserva_horas)
      __init__.py                                (modify: exportar lo nuevo)
    exceptions.py                                (modify: + 7 excepciones)
    repositories/
      paciente_repository.py                     (create: hereda BaseRepository, + busqueda)
      doctor_repository.py                       (create: hereda BaseRepository)
      asistente_repository.py                    (create: hereda BaseRepository)
      horario_doctor_repository.py               (create: anidado bajo doctor, NO hereda)
      cita_repository.py                         (create: hereda BaseRepository, + rango y solapamientos)
    services/
      validadores_cita.py                        (create: ContextoCita + 7 validadores)
      cita_service.py                            (create: orquesta validadores y transiciones)
      personal_service.py                        (create: alta transaccional Usuario + perfil)
    schemas/
      personas.py                                (create)
      cita.py                                    (create)
      parametros.py                              (modify: + campo en configuracion)
    api/
      deps.py                                    (modify: + get_doctor_actual)
      routes/
        pacientes.py                             (create)
        doctores.py                              (create: CRUD + horarios anidados)
        asistentes.py                            (create)
        citas.py                                 (create)
    main.py                                      (modify: incluir 4 routers)
  tests/
    test_personas_models.py                      (create)
    test_cita_model.py                           (create)
    test_paciente_repository.py                  (create)
    test_doctor_repository.py                    (create)
    test_asistente_repository.py                 (create)
    test_horario_doctor_repository.py            (create)
    test_cita_repository.py                      (create)
    test_validadores_cita.py                     (create: sin base de datos)
    test_cita_service.py                         (create)
    test_personal_service.py                     (create)
    test_pacientes_routes.py                     (create)
    test_doctores_routes.py                      (create)
    test_asistentes_routes.py                    (create)
    test_citas_routes.py                         (create)
    test_schemas_modulo4.py                      (create)
    test_configuracion_routes.py                 (modify: + campo nuevo)
    factories.py                                 (create: helpers compartidos de los tests)
docs/
  postman/
    ClinicaDentalWeb-Modulo4.postman_collection.json   (create: un archivo por modulo)
  CONTEXTO-PROYECTO.md                                 (modify: seccion 6ter)
```

**Por qué esta división.** Los modelos se parten en dos archivos porque son dos grupos que cambian
por razones distintas: las personas son datos, la cita tiene una máquina de estados y suficiente
lógica propia. Los validadores van todos juntos en un archivo porque son siete clases de diez
líneas que se leen como una unidad — separarlos en siete archivos sería ceremonia. `factories.py`
es nuevo respecto de los Módulos 1 a 3: los helpers `_clinica()`, `_token_para()` y compañía se
venían copiando en cada archivo de test, y este módulo tiene catorce archivos de test que necesitan
además crear pacientes, doctores y citas. Centralizarlos ahora evita repetir el mismo bloque
catorce veces.

---

## Task 1: Modelos, enums y migración

**Files:**
- Create: `backend/app/models/personas.py`
- Create: `backend/app/models/cita.py`
- Modify: `backend/app/models/parametros.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/0004_operacion_clinica.py`
- Test: `backend/tests/test_personas_models.py`
- Test: `backend/tests/test_cita_model.py`

**Interfaces:**
- Consumes: `app.models.base.Base`, `Clinica` y `Usuario` (Módulo 1), `Especialidad`, `Consultorio`
  y `DiaSemana` (Módulo 3).
- Produces: `Paciente` (PK `id_paciente`), `Doctor` (PK `id_doctor`), `Asistente` (PK
  `id_asistente`), `HorarioDoctor` (PK `id_horario`), `Cita` (PK `id_cita`), `EstadoCita`,
  `TRANSICIONES_PERMITIDAS: dict[EstadoCita, set[EstadoCita]]`,
  `ESTADOS_ACTIVOS: frozenset[EstadoCita]`, y
  `ConfiguracionClinica.anticipacion_minima_reserva_horas: int`.

- [ ] **Step 1: Escribir los tests de personas que fallan**

Crear `backend/tests/test_personas_models.py`:

```python
from datetime import time

import pytest
from sqlalchemy.exc import IntegrityError


def _clinica(db_session, nombre="Dental A"):
    from app.models import Clinica

    clinica = Clinica(nombre=nombre)
    db_session.add(clinica)
    db_session.flush()
    return clinica


def _usuario(db_session, id_clinica, username="dra.perez"):
    from app.models import RolUsuario, Usuario

    usuario = Usuario(
        id_clinica=id_clinica,
        username=username,
        password_hash="x",
        rol=RolUsuario.DOCTOR,
    )
    db_session.add(usuario)
    db_session.flush()
    return usuario


def test_paciente_nace_activo_y_sin_fecha_de_nacimiento(db_session):
    from app.models import Paciente

    clinica = _clinica(db_session)
    paciente = Paciente(
        id_clinica=clinica.id_clinica,
        nombre="Ana",
        apellido="Lopez",
        telefono="70001122",
    )
    db_session.add(paciente)
    db_session.flush()

    assert paciente.id_paciente is not None
    assert paciente.activo is True
    assert paciente.fecha_nacimiento is None
    assert paciente.correo is None


def test_paciente_no_tiene_columna_edad(db_session):
    """La edad es un dato derivado de fecha_nacimiento, no se almacena."""
    from app.models import Paciente

    assert "edad" not in Paciente.__table__.columns


def test_paciente_no_tiene_columna_id_usuario(db_session):
    """El paciente no se loguea: la clinica opera el sistema en su nombre."""
    from app.models import Paciente

    assert "id_usuario" not in Paciente.__table__.columns


def test_doctor_exige_usuario_y_admite_especialidad_nula(db_session):
    from app.models import Doctor

    clinica = _clinica(db_session)
    usuario = _usuario(db_session, clinica.id_clinica)
    doctor = Doctor(
        id_clinica=clinica.id_clinica,
        id_usuario=usuario.id_usuario,
        nombre="Marta",
        apellido="Perez",
        telefono="70001122",
    )
    db_session.add(doctor)
    db_session.flush()

    assert doctor.id_doctor is not None
    assert doctor.id_especialidad is None
    assert doctor.activo is True


def test_un_usuario_no_puede_tener_dos_doctores(db_session):
    from app.models import Doctor

    clinica = _clinica(db_session)
    usuario = _usuario(db_session, clinica.id_clinica)
    db_session.add_all(
        [
            Doctor(
                id_clinica=clinica.id_clinica,
                id_usuario=usuario.id_usuario,
                nombre="Marta",
                apellido="Perez",
                telefono="70001122",
            ),
            Doctor(
                id_clinica=clinica.id_clinica,
                id_usuario=usuario.id_usuario,
                nombre="Otra",
                apellido="Persona",
                telefono="70003344",
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_asistente_tambien_exige_usuario_unico(db_session):
    from app.models import Asistente

    clinica = _clinica(db_session)
    usuario = _usuario(db_session, clinica.id_clinica, "recepcion")
    db_session.add_all(
        [
            Asistente(
                id_clinica=clinica.id_clinica,
                id_usuario=usuario.id_usuario,
                nombre="Rosa",
                apellido="Diaz",
                telefono="70005566",
            ),
            Asistente(
                id_clinica=clinica.id_clinica,
                id_usuario=usuario.id_usuario,
                nombre="Otra",
                apellido="Persona",
                telefono="70007788",
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_un_doctor_puede_tener_varios_bloques_el_mismo_dia(db_session):
    """A diferencia de HorarioClinica: el doctor atiende manana y tarde."""
    from app.models import DiaSemana, Doctor, HorarioDoctor

    clinica = _clinica(db_session)
    usuario = _usuario(db_session, clinica.id_clinica)
    doctor = Doctor(
        id_clinica=clinica.id_clinica,
        id_usuario=usuario.id_usuario,
        nombre="Marta",
        apellido="Perez",
        telefono="70001122",
    )
    db_session.add(doctor)
    db_session.flush()

    db_session.add_all(
        [
            HorarioDoctor(
                id_doctor=doctor.id_doctor,
                dia_semana=DiaSemana.LUNES,
                hora_inicio=time(8, 0),
                hora_fin=time(12, 0),
            ),
            HorarioDoctor(
                id_doctor=doctor.id_doctor,
                dia_semana=DiaSemana.LUNES,
                hora_inicio=time(14, 0),
                hora_fin=time(18, 0),
            ),
        ]
    )

    db_session.flush()  # no debe explotar


def test_dos_bloques_con_el_mismo_inicio_el_mismo_dia_violan_la_unicidad(db_session):
    from app.models import DiaSemana, Doctor, HorarioDoctor

    clinica = _clinica(db_session)
    usuario = _usuario(db_session, clinica.id_clinica)
    doctor = Doctor(
        id_clinica=clinica.id_clinica,
        id_usuario=usuario.id_usuario,
        nombre="Marta",
        apellido="Perez",
        telefono="70001122",
    )
    db_session.add(doctor)
    db_session.flush()

    db_session.add_all(
        [
            HorarioDoctor(
                id_doctor=doctor.id_doctor,
                dia_semana=DiaSemana.LUNES,
                hora_inicio=time(8, 0),
                hora_fin=time(12, 0),
            ),
            HorarioDoctor(
                id_doctor=doctor.id_doctor,
                dia_semana=DiaSemana.LUNES,
                hora_inicio=time(8, 0),
                hora_fin=time(9, 0),
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_horario_doctor_nace_disponible(db_session):
    from app.models import DiaSemana, Doctor, HorarioDoctor

    clinica = _clinica(db_session)
    usuario = _usuario(db_session, clinica.id_clinica)
    doctor = Doctor(
        id_clinica=clinica.id_clinica,
        id_usuario=usuario.id_usuario,
        nombre="Marta",
        apellido="Perez",
        telefono="70001122",
    )
    db_session.add(doctor)
    db_session.flush()

    bloque = HorarioDoctor(
        id_doctor=doctor.id_doctor,
        dia_semana=DiaSemana.MARTES,
        hora_inicio=time(8, 0),
        hora_fin=time(12, 0),
    )
    db_session.add(bloque)
    db_session.flush()

    assert bloque.disponible is True


def test_configuracion_gana_anticipacion_minima_con_default_24(db_session):
    from app.models import ConfiguracionClinica

    clinica = _clinica(db_session)
    config = ConfiguracionClinica(id_clinica=clinica.id_clinica)
    db_session.add(config)
    db_session.flush()

    assert config.anticipacion_minima_reserva_horas == 24
```

- [ ] **Step 2: Escribir los tests de cita que fallan**

Crear `backend/tests/test_cita_model.py`:

```python
from datetime import datetime

from sqlalchemy import text


def _clinica_con_gente(db_session):
    """Devuelve (clinica, paciente, doctor) listos para colgarles una cita."""
    from app.models import Clinica, Doctor, Paciente, RolUsuario, Usuario

    clinica = Clinica(nombre="Dental A")
    db_session.add(clinica)
    db_session.flush()

    usuario = Usuario(
        id_clinica=clinica.id_clinica,
        username="dra.perez",
        password_hash="x",
        rol=RolUsuario.DOCTOR,
    )
    paciente = Paciente(
        id_clinica=clinica.id_clinica,
        nombre="Ana",
        apellido="Lopez",
        telefono="70001122",
    )
    db_session.add_all([usuario, paciente])
    db_session.flush()

    doctor = Doctor(
        id_clinica=clinica.id_clinica,
        id_usuario=usuario.id_usuario,
        nombre="Marta",
        apellido="Perez",
        telefono="70003344",
    )
    db_session.add(doctor)
    db_session.flush()
    return clinica, paciente, doctor


def test_cita_nace_programada_sin_reagendamientos(db_session):
    from app.models import Cita, EstadoCita

    clinica, paciente, doctor = _clinica_con_gente(db_session)
    cita = Cita(
        id_clinica=clinica.id_clinica,
        id_paciente=paciente.id_paciente,
        id_doctor=doctor.id_doctor,
        fecha_hora=datetime(2026, 9, 1, 9, 0),
        duracion_minutos=30,
    )
    db_session.add(cita)
    db_session.flush()

    assert cita.id_cita is not None
    assert cita.estado == EstadoCita.PROGRAMADA
    assert cita.veces_reagendada == 0
    assert cita.id_consultorio is None
    assert cita.id_asistente is None


def test_estado_cita_persiste_el_valor_en_minuscula_no_el_nombre(db_session):
    """Bug conocido #2: sin values_callable, MySQL guardaria 'PROGRAMADA'."""
    from app.models import Cita

    clinica, paciente, doctor = _clinica_con_gente(db_session)
    db_session.add(
        Cita(
            id_clinica=clinica.id_clinica,
            id_paciente=paciente.id_paciente,
            id_doctor=doctor.id_doctor,
            fecha_hora=datetime(2026, 9, 1, 9, 0),
            duracion_minutos=30,
        )
    )
    db_session.flush()

    guardado = db_session.execute(text("SELECT estado FROM cita")).scalar_one()
    assert guardado == "programada"


def test_transiciones_permitidas_cubre_los_cinco_estados():
    from app.models import TRANSICIONES_PERMITIDAS, EstadoCita

    assert set(TRANSICIONES_PERMITIDAS) == set(EstadoCita)


def test_los_tres_estados_terminales_no_admiten_transiciones():
    from app.models import TRANSICIONES_PERMITIDAS, EstadoCita

    for terminal in (EstadoCita.COMPLETADA, EstadoCita.CANCELADA, EstadoCita.NO_ASISTIO):
        assert TRANSICIONES_PERMITIDAS[terminal] == set()


def test_solo_se_completa_o_se_marca_ausente_desde_confirmada():
    from app.models import TRANSICIONES_PERMITIDAS, EstadoCita

    assert TRANSICIONES_PERMITIDAS[EstadoCita.PROGRAMADA] == {
        EstadoCita.CONFIRMADA,
        EstadoCita.CANCELADA,
    }
    assert TRANSICIONES_PERMITIDAS[EstadoCita.CONFIRMADA] == {
        EstadoCita.COMPLETADA,
        EstadoCita.NO_ASISTIO,
        EstadoCita.CANCELADA,
    }


def test_estados_activos_son_los_que_ocupan_agenda():
    from app.models import ESTADOS_ACTIVOS, EstadoCita

    assert ESTADOS_ACTIVOS == frozenset({EstadoCita.PROGRAMADA, EstadoCita.CONFIRMADA})
```

- [ ] **Step 3: Correr los tests y verificar que fallan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_personas_models.py tests/test_cita_model.py -v`
Expected: FAIL — `ImportError: cannot import name 'Paciente' from 'app.models'`

- [ ] **Step 4: Escribir los modelos de personas**

Crear `backend/app/models/personas.py`:

```python
from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base
from app.models.parametros import DiaSemana


class Paciente(Base):
    """Ficha de la persona que la clinica atiende. No tiene login: el paciente
    no opera el sistema, lo opera la clinica en su nombre.

    La edad NO se almacena: es un dato derivado de fecha_nacimiento y guardarla
    la vuelve mentira al dia siguiente del cumpleanos.
    """

    __tablename__ = "paciente"

    id_paciente: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_clinica: Mapped[int] = mapped_column(
        ForeignKey("clinica.id_clinica"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    apellido: Mapped[str] = mapped_column(String(50), nullable=False)
    fecha_nacimiento: Mapped[date | None] = mapped_column(Date, nullable=True)
    telefono: Mapped[str] = mapped_column(String(15), nullable=False)
    # varchar100 y no varchar25 como el legacy: el ERD as-is documenta que
    # varchar25 "trunca correos largos". Es un bug, no una convencion.
    correo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    direccion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Doctor(Base):
    """Perfil profesional. 1:1 con un Usuario de rol 'doctor': id_usuario es
    NOT NULL y unico, tal como lo define el ERD to-be.

    id_especialidad es nullable a proposito: una clinica recien creada no tiene
    el catalogo cargado, y exigirla bloquearia el alta del primer doctor.
    """

    __tablename__ = "doctor"
    # El constraint va nombrado y no como unique=True inline, para que coincida
    # con el nombre que le da la migracion y --autogenerate no marque una
    # diferencia falsa.
    __table_args__ = (
        UniqueConstraint("id_usuario", name="uq_doctor_usuario"),
    )

    id_doctor: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_clinica: Mapped[int] = mapped_column(
        ForeignKey("clinica.id_clinica"), nullable=False
    )
    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("usuario.id_usuario"), nullable=False
    )
    id_especialidad: Mapped[int | None] = mapped_column(
        ForeignKey("especialidad.id_especialidad"), nullable=True
    )
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    apellido: Mapped[str] = mapped_column(String(50), nullable=False)
    telefono: Mapped[str] = mapped_column(String(15), nullable=False)
    correo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")


class Asistente(Base):
    """Perfil del personal de recepcion. 1:1 con un Usuario de rol 'asistente'."""

    __tablename__ = "asistente"
    __table_args__ = (
        UniqueConstraint("id_usuario", name="uq_asistente_usuario"),
    )

    id_asistente: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_clinica: Mapped[int] = mapped_column(
        ForeignKey("clinica.id_clinica"), nullable=False
    )
    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("usuario.id_usuario"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    apellido: Mapped[str] = mapped_column(String(50), nullable=False)
    telefono: Mapped[str] = mapped_column(String(15), nullable=False)
    correo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")


class HorarioDoctor(Base):
    """Bloque de disponibilidad semanal de un doctor.

    A diferencia de HorarioClinica, tiene PK propia y NO llave compuesta
    (id_doctor, dia_semana): un doctor atiende de 08:00 a 12:00, almuerza, y
    vuelve de 14:00 a 18:00. Con llave compuesta eso seria imposible.

    No lleva id_clinica: la clinica se deduce del doctor, y duplicarla abriria
    la posibilidad de que las dos columnas se contradigan. El aislamiento lo
    garantiza el repositorio con un join contra Doctor.
    """

    __tablename__ = "horario_doctor"
    __table_args__ = (
        UniqueConstraint(
            "id_doctor", "dia_semana", "hora_inicio", name="uq_horario_doctor_dia_inicio"
        ),
    )

    id_horario: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_doctor: Mapped[int] = mapped_column(
        ForeignKey("doctor.id_doctor"), nullable=False
    )
    dia_semana: Mapped[DiaSemana] = mapped_column(
        SAEnum(
            DiaSemana,
            name="dia_semana",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
    )
    hora_inicio: Mapped[time] = mapped_column(Time, nullable=False)
    hora_fin: Mapped[time] = mapped_column(Time, nullable=False)
    disponible: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
```

- [ ] **Step 5: Escribir el modelo de cita**

Crear `backend/app/models/cita.py`:

```python
import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class EstadoCita(str, enum.Enum):
    PROGRAMADA = "programada"
    CONFIRMADA = "confirmada"
    COMPLETADA = "completada"
    CANCELADA = "cancelada"
    NO_ASISTIO = "no_asistio"


#: Maquina de estados en una sola tabla, en vez de condicionales repartidos.
#: Agregar un estado es una entrada aca; el conjunto vacio expresa "terminal"
#: sin necesitar un if especial.
#:
#: Solo se completa o se marca ausente desde 'confirmada': una cita que el
#: paciente nunca confirmo y a la que no vino es informacion distinta de una
#: que confirmo y no honro.
#:
#: Reagendar queda deliberadamente fuera de esta tabla. No es una transicion de
#: estado sino un movimiento de datos: la cita cambia de fecha y su estado se
#: RESETEA a 'programada' porque la confirmacion era para la hora vieja. Modelarlo
#: como transicion obligaria a permitir 'confirmada -> programada' en general, y
#: eso habilitaria des-confirmar una cita sin moverla, que no es una operacion
#: que el negocio tenga. CitaService.reagendar solo consulta esta tabla para
#: saber si el estado actual es terminal (conjunto vacio).
TRANSICIONES_PERMITIDAS: dict[EstadoCita, set[EstadoCita]] = {
    EstadoCita.PROGRAMADA: {EstadoCita.CONFIRMADA, EstadoCita.CANCELADA},
    EstadoCita.CONFIRMADA: {
        EstadoCita.COMPLETADA,
        EstadoCita.NO_ASISTIO,
        EstadoCita.CANCELADA,
    },
    EstadoCita.COMPLETADA: set(),
    EstadoCita.CANCELADA: set(),
    EstadoCita.NO_ASISTIO: set(),
}

#: Los estados que ocupan un lugar en la agenda. Una cita cancelada, completada
#: o marcada como ausente libera el horario y no cuenta para los choques.
ESTADOS_ACTIVOS: frozenset[EstadoCita] = frozenset(
    {EstadoCita.PROGRAMADA, EstadoCita.CONFIRMADA}
)


class Cita(Base):
    """El agendamiento. Toda la logica de validacion vive en CitaService y en
    los validadores; este modelo solo guarda el dato.
    """

    __tablename__ = "cita"
    __table_args__ = (
        # La agenda de un doctor en un rango de fechas es la consulta central
        # del modulo. El indice tiene que estar tambien aca y no solo en la
        # migracion: si no, los tests corren contra un esquema sin indice.
        Index("ix_cita_doctor_fecha", "id_doctor", "fecha_hora"),
    )

    id_cita: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # id_clinica explicito aunque sea derivable del paciente o del doctor: todos
    # los repositorios tenant-scoped filtran por id_clinica directo, y derivarlo
    # con un join haria que el aislamiento dependa de la correccion de ese join.
    id_clinica: Mapped[int] = mapped_column(
        ForeignKey("clinica.id_clinica"), nullable=False
    )
    id_paciente: Mapped[int] = mapped_column(
        ForeignKey("paciente.id_paciente"), nullable=False
    )
    id_doctor: Mapped[int] = mapped_column(
        ForeignKey("doctor.id_doctor"), nullable=False
    )
    id_consultorio: Mapped[int | None] = mapped_column(
        ForeignKey("consultorio.id_consultorio"), nullable=True
    )
    #: Quien la agendo. Nullable porque un admin (que no tiene fila en Asistente)
    #: tambien puede agendar.
    id_asistente: Mapped[int | None] = mapped_column(
        ForeignKey("asistente.id_asistente"), nullable=True
    )
    fecha_hora: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    #: Foto del momento en que se agendo. Si la clinica cambia la duracion por
    #: defecto, las citas ya agendadas no deben estirarse solas ni empezar a
    #: chocar entre si retroactivamente.
    duracion_minutos: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[EstadoCita] = mapped_column(
        SAEnum(
            EstadoCita,
            name="estado_cita",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        default=EstadoCita.PROGRAMADA,
        server_default="programada",
        nullable=False,
    )
    motivo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    #: Contador en vez de un estado 'reagendada': reagendar es una transicion,
    #: no una situacion. Un estado 'reagendada' no responde "esta confirmada o
    #: no?" y ensuciaria todos los filtros de agenda activa.
    veces_reagendada: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 6: Agregar la columna nueva a `ConfiguracionClinica`**

Modificar `backend/app/models/parametros.py` — dentro de la clase `ConfiguracionClinica`, agregar
esta columna justo después de `dias_minimos_reagendamiento` y antes de `updated_at`:

```python
    #: Anticipacion minima para CREAR una cita nueva. Minimo 1 y no 0, igual que
    #: los otros dos parametros de cambio de cita: la regla es configurable en
    #: intensidad pero no desactivable. El default de 24 refleja la practica de
    #: las clinicas dentales salvadorenas, donde no se atiende sin cita previa.
    anticipacion_minima_reserva_horas: Mapped[int] = mapped_column(
        Integer, default=24, server_default="24"
    )
```

- [ ] **Step 7: Exportar todo lo nuevo**

Modificar `backend/app/models/__init__.py` — queda así completo:

```python
from app.models.base import Base
from app.models.cita import (
    ESTADOS_ACTIVOS,
    TRANSICIONES_PERMITIDAS,
    Cita,
    EstadoCita,
)
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
from app.models.personas import Asistente, Doctor, HorarioDoctor, Paciente
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
    "Paciente",
    "Doctor",
    "Asistente",
    "HorarioDoctor",
    "Cita",
    "EstadoCita",
    "TRANSICIONES_PERMITIDAS",
    "ESTADOS_ACTIVOS",
]
```

- [ ] **Step 8: Correr los tests y verificar que pasan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_personas_models.py tests/test_cita_model.py -v`
Expected: PASS — 15 passed

- [ ] **Step 9: Correr la suite completa**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: todos los tests de Módulos 1 a 3 siguen pasando.

- [ ] **Step 10: Escribir la migración**

Crear `backend/alembic/versions/0004_operacion_clinica.py`:

```python
"""operacion clinica: paciente, doctor, asistente, horario_doctor, cita

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-02
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

_DIAS = ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo")
_ESTADOS = ("programada", "confirmada", "completada", "cancelada", "no_asistio")


def _columnas_de_persona() -> list[sa.Column]:
    return [
        sa.Column("nombre", sa.String(length=50), nullable=False),
        sa.Column("apellido", sa.String(length=50), nullable=False),
        sa.Column("telefono", sa.String(length=15), nullable=False),
        sa.Column("correo", sa.String(length=100), nullable=True),
        sa.Column("activo", sa.Boolean(), server_default="1", nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "paciente",
        sa.Column("id_paciente", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_clinica", sa.Integer(), nullable=False),
        sa.Column("fecha_nacimiento", sa.Date(), nullable=True),
        sa.Column("direccion", sa.String(length=200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        *_columnas_de_persona(),
        sa.ForeignKeyConstraint(["id_clinica"], ["clinica.id_clinica"]),
        sa.PrimaryKeyConstraint("id_paciente"),
    )

    op.create_table(
        "doctor",
        sa.Column("id_doctor", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_clinica", sa.Integer(), nullable=False),
        sa.Column("id_usuario", sa.Integer(), nullable=False),
        sa.Column("id_especialidad", sa.Integer(), nullable=True),
        *_columnas_de_persona(),
        sa.ForeignKeyConstraint(["id_clinica"], ["clinica.id_clinica"]),
        sa.ForeignKeyConstraint(["id_usuario"], ["usuario.id_usuario"]),
        sa.ForeignKeyConstraint(["id_especialidad"], ["especialidad.id_especialidad"]),
        sa.PrimaryKeyConstraint("id_doctor"),
        sa.UniqueConstraint("id_usuario", name="uq_doctor_usuario"),
    )

    op.create_table(
        "asistente",
        sa.Column("id_asistente", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_clinica", sa.Integer(), nullable=False),
        sa.Column("id_usuario", sa.Integer(), nullable=False),
        *_columnas_de_persona(),
        sa.ForeignKeyConstraint(["id_clinica"], ["clinica.id_clinica"]),
        sa.ForeignKeyConstraint(["id_usuario"], ["usuario.id_usuario"]),
        sa.PrimaryKeyConstraint("id_asistente"),
        sa.UniqueConstraint("id_usuario", name="uq_asistente_usuario"),
    )

    op.create_table(
        "horario_doctor",
        sa.Column("id_horario", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_doctor", sa.Integer(), nullable=False),
        sa.Column("dia_semana", sa.Enum(*_DIAS, name="dia_semana"), nullable=False),
        sa.Column("hora_inicio", sa.Time(), nullable=False),
        sa.Column("hora_fin", sa.Time(), nullable=False),
        sa.Column("disponible", sa.Boolean(), server_default="1", nullable=False),
        sa.ForeignKeyConstraint(["id_doctor"], ["doctor.id_doctor"]),
        sa.PrimaryKeyConstraint("id_horario"),
        sa.UniqueConstraint(
            "id_doctor", "dia_semana", "hora_inicio", name="uq_horario_doctor_dia_inicio"
        ),
    )

    op.create_table(
        "cita",
        sa.Column("id_cita", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_clinica", sa.Integer(), nullable=False),
        sa.Column("id_paciente", sa.Integer(), nullable=False),
        sa.Column("id_doctor", sa.Integer(), nullable=False),
        sa.Column("id_consultorio", sa.Integer(), nullable=True),
        sa.Column("id_asistente", sa.Integer(), nullable=True),
        sa.Column("fecha_hora", sa.DateTime(), nullable=False),
        sa.Column("duracion_minutos", sa.Integer(), nullable=False),
        sa.Column(
            "estado",
            sa.Enum(*_ESTADOS, name="estado_cita"),
            server_default="programada",
            nullable=False,
        ),
        sa.Column("motivo", sa.String(length=255), nullable=True),
        sa.Column("veces_reagendada", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["id_clinica"], ["clinica.id_clinica"]),
        sa.ForeignKeyConstraint(["id_paciente"], ["paciente.id_paciente"]),
        sa.ForeignKeyConstraint(["id_doctor"], ["doctor.id_doctor"]),
        sa.ForeignKeyConstraint(["id_consultorio"], ["consultorio.id_consultorio"]),
        sa.ForeignKeyConstraint(["id_asistente"], ["asistente.id_asistente"]),
        sa.PrimaryKeyConstraint("id_cita"),
    )
    # Indice para el caso de uso central: la agenda de un doctor en un rango.
    op.create_index("ix_cita_doctor_fecha", "cita", ["id_doctor", "fecha_hora"])

    op.add_column(
        "configuracion_clinica",
        sa.Column(
            "anticipacion_minima_reserva_horas",
            sa.Integer(),
            server_default="24",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("configuracion_clinica", "anticipacion_minima_reserva_horas")
    op.drop_index("ix_cita_doctor_fecha", table_name="cita")
    op.drop_table("cita")
    op.drop_table("horario_doctor")
    op.drop_table("asistente")
    op.drop_table("doctor")
    op.drop_table("paciente")
```

- [ ] **Step 11: Verificar que la cadena de revisiones está sana**

Run: `.venv/Scripts/python.exe -m alembic history`
Expected: aparece `0003 -> 0004 (head), operacion clinica...`

La aplicación real contra MySQL se verifica en la Task 13.

- [ ] **Step 12: Punto de commit (lo ejecuta Meli, no el agente)**

```bash
git add backend/app/models/personas.py backend/app/models/cita.py \
        backend/app/models/parametros.py backend/app/models/__init__.py \
        backend/alembic/versions/0004_operacion_clinica.py \
        backend/tests/test_personas_models.py backend/tests/test_cita_model.py
git commit -m "feat(backend): modelos y migracion de operacion clinica"
```

---

## Task 2: Helpers de test compartidos

**Files:**
- Create: `backend/tests/factories.py`

**Interfaces:**
- Consumes: modelos de la Task 1, `create_access_token` y `hash_password` (Módulo 1).
- Produces: `crear_clinica(db, nombre="Dental A") -> Clinica`;
  `crear_usuario(db, rol, id_clinica=None, username="user.test") -> Usuario`;
  `token_de(usuario) -> str`; `auth(token) -> dict[str, str]`;
  `crear_paciente(db, id_clinica, **campos) -> Paciente`;
  `crear_doctor(db, id_clinica, username="dra.perez", **campos) -> Doctor`;
  `crear_asistente(db, id_clinica, username="recepcion", **campos) -> Asistente`;
  `crear_cita(db, id_clinica, id_paciente, id_doctor, **campos) -> Cita`.

> No hay TDD acá: es infraestructura de test, no código de producción. Se valida usándola en la
> Task 3. Existe porque este módulo tiene catorce archivos de test que necesitan la misma gente de
> mentira, y copiar el bloque catorce veces es exactamente la duplicación que el resto del plan
> evita.

- [ ] **Step 1: Escribir el archivo de factories**

Crear `backend/tests/factories.py`:

```python
"""Helpers compartidos por los tests del Modulo 4.

Todos hacen flush(), no commit(): quien necesite persistir de verdad (los tests
de rutas, que corren el endpoint en otro hilo) hace el commit explicito.
"""
from datetime import datetime, timedelta


def crear_clinica(db, nombre="Dental A"):
    from app.models import Clinica

    clinica = Clinica(nombre=nombre)
    db.add(clinica)
    db.flush()
    return clinica


def crear_usuario(db, rol, id_clinica=None, username="user.test"):
    from app.models import Usuario

    usuario = Usuario(
        id_clinica=id_clinica,
        username=username,
        password_hash="hash-de-mentira",
        rol=rol,
    )
    db.add(usuario)
    db.flush()
    return usuario


def token_de(usuario) -> str:
    from app.security.jwt import create_access_token

    return create_access_token(
        data={
            "sub": str(usuario.id_usuario),
            "id_clinica": usuario.id_clinica,
            "rol": usuario.rol.value,
        },
        expires_delta=timedelta(minutes=10),
    )


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def crear_paciente(db, id_clinica, **campos):
    from app.models import Paciente

    datos = {"nombre": "Ana", "apellido": "Lopez", "telefono": "70001122"}
    datos.update(campos)
    paciente = Paciente(id_clinica=id_clinica, **datos)
    db.add(paciente)
    db.flush()
    return paciente


def crear_doctor(db, id_clinica, username="dra.perez", **campos):
    from app.models import Doctor, RolUsuario

    usuario = crear_usuario(db, RolUsuario.DOCTOR, id_clinica, username)
    datos = {"nombre": "Marta", "apellido": "Perez", "telefono": "70003344"}
    datos.update(campos)
    doctor = Doctor(id_clinica=id_clinica, id_usuario=usuario.id_usuario, **datos)
    db.add(doctor)
    db.flush()
    return doctor


def crear_asistente(db, id_clinica, username="recepcion", **campos):
    from app.models import Asistente, RolUsuario

    usuario = crear_usuario(db, RolUsuario.ASISTENTE, id_clinica, username)
    datos = {"nombre": "Rosa", "apellido": "Diaz", "telefono": "70005566"}
    datos.update(campos)
    asistente = Asistente(id_clinica=id_clinica, id_usuario=usuario.id_usuario, **datos)
    db.add(asistente)
    db.flush()
    return asistente


def crear_cita(db, id_clinica, id_paciente, id_doctor, **campos):
    from app.models import Cita

    datos = {"fecha_hora": datetime(2026, 9, 1, 9, 0), "duracion_minutos": 30}
    datos.update(campos)
    cita = Cita(
        id_clinica=id_clinica,
        id_paciente=id_paciente,
        id_doctor=id_doctor,
        **datos,
    )
    db.add(cita)
    db.flush()
    return cita
```

- [ ] **Step 2: Verificar que el módulo importa**

Run: `.venv/Scripts/python.exe -c "import tests.factories; print('ok')"`
Expected: imprime `ok`

- [ ] **Step 3: Punto de commit (lo ejecuta Meli)**

```bash
git add backend/tests/factories.py
git commit -m "test(backend): helpers compartidos para los tests del modulo 4"
```

---

## Task 3: `PacienteRepository`

**Files:**
- Create: `backend/app/repositories/paciente_repository.py`
- Test: `backend/tests/test_paciente_repository.py`

**Interfaces:**
- Consumes: `BaseRepository[T]`, `Paciente` (Task 1), factories (Task 2).
- Produces: `PacienteRepository(db)` con
  `listar(id_clinica, buscar: str | None = None, incluir_inactivos: bool = False) -> list[Paciente]`,
  `obtener(id_clinica, id_) -> Paciente | None`, `crear(id_clinica, data: dict) -> Paciente`,
  `actualizar(id_clinica, id_, data: dict) -> Paciente | None`,
  `eliminar(id_clinica, id_) -> bool`.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `backend/tests/test_paciente_repository.py`:

```python
from tests.factories import crear_clinica


def _repo(db_session):
    from app.repositories.paciente_repository import PacienteRepository

    return PacienteRepository(db_session)


def _datos(**campos):
    base = {"nombre": "Ana", "apellido": "Lopez", "telefono": "70001122"}
    base.update(campos)
    return base


def test_crear_devuelve_el_paciente_activo_en_su_clinica(db_session):
    clinica = crear_clinica(db_session)

    creado = _repo(db_session).crear(clinica.id_clinica, _datos())

    assert creado.id_paciente is not None
    assert creado.id_clinica == clinica.id_clinica
    assert creado.activo is True


def test_listar_solo_devuelve_los_de_la_clinica_pedida(db_session):
    clinica_a = crear_clinica(db_session, "Dental A")
    clinica_b = crear_clinica(db_session, "Dental B")
    repo = _repo(db_session)
    repo.crear(clinica_a.id_clinica, _datos(nombre="Ana"))
    repo.crear(clinica_b.id_clinica, _datos(nombre="Beto"))

    assert [p.nombre for p in repo.listar(clinica_a.id_clinica)] == ["Ana"]


def test_listar_ordena_por_apellido_y_nombre(db_session):
    clinica = crear_clinica(db_session)
    repo = _repo(db_session)
    repo.crear(clinica.id_clinica, _datos(nombre="Zoe", apellido="Ayala"))
    repo.crear(clinica.id_clinica, _datos(nombre="Ana", apellido="Zamora"))
    repo.crear(clinica.id_clinica, _datos(nombre="Ana", apellido="Ayala"))

    resultado = repo.listar(clinica.id_clinica)

    assert [(p.apellido, p.nombre) for p in resultado] == [
        ("Ayala", "Ana"),
        ("Ayala", "Zoe"),
        ("Zamora", "Ana"),
    ]


def test_buscar_encuentra_por_nombre_o_apellido_sin_importar_mayusculas(db_session):
    clinica = crear_clinica(db_session)
    repo = _repo(db_session)
    repo.crear(clinica.id_clinica, _datos(nombre="Ana", apellido="Lopez"))
    repo.crear(clinica.id_clinica, _datos(nombre="Beto", apellido="Martinez"))

    assert [p.nombre for p in repo.listar(clinica.id_clinica, buscar="LOP")] == ["Ana"]
    assert [p.nombre for p in repo.listar(clinica.id_clinica, buscar="bet")] == ["Beto"]


def test_buscar_no_cruza_clinicas(db_session):
    clinica_a = crear_clinica(db_session, "Dental A")
    clinica_b = crear_clinica(db_session, "Dental B")
    repo = _repo(db_session)
    repo.crear(clinica_b.id_clinica, _datos(nombre="Ana", apellido="Lopez"))

    assert repo.listar(clinica_a.id_clinica, buscar="Lopez") == []


def test_listar_omite_los_inactivos_por_defecto(db_session):
    clinica = crear_clinica(db_session)
    repo = _repo(db_session)
    creado = repo.crear(clinica.id_clinica, _datos(nombre="Ana"))
    repo.crear(clinica.id_clinica, _datos(nombre="Beto"))
    repo.eliminar(clinica.id_clinica, creado.id_paciente)

    assert [p.nombre for p in repo.listar(clinica.id_clinica)] == ["Beto"]
    assert len(repo.listar(clinica.id_clinica, incluir_inactivos=True)) == 2


def test_obtener_de_otra_clinica_devuelve_none(db_session):
    clinica_a = crear_clinica(db_session, "Dental A")
    clinica_b = crear_clinica(db_session, "Dental B")
    repo = _repo(db_session)
    de_a = repo.crear(clinica_a.id_clinica, _datos())

    assert repo.obtener(clinica_b.id_clinica, de_a.id_paciente) is None
    assert repo.obtener(clinica_a.id_clinica, de_a.id_paciente) is not None


def test_actualizar_aplica_solo_los_campos_presentes(db_session):
    clinica = crear_clinica(db_session)
    repo = _repo(db_session)
    creado = repo.crear(clinica.id_clinica, _datos())

    actualizado = repo.actualizar(
        clinica.id_clinica, creado.id_paciente, {"telefono": "70009999"}
    )

    assert actualizado.telefono == "70009999"
    assert actualizado.nombre == "Ana"


def test_actualizar_de_otra_clinica_devuelve_none(db_session):
    clinica_a = crear_clinica(db_session, "Dental A")
    clinica_b = crear_clinica(db_session, "Dental B")
    repo = _repo(db_session)
    de_a = repo.crear(clinica_a.id_clinica, _datos())

    assert repo.actualizar(clinica_b.id_clinica, de_a.id_paciente, {"nombre": "X"}) is None


def test_eliminar_es_borrado_logico_e_idempotente(db_session):
    clinica = crear_clinica(db_session)
    repo = _repo(db_session)
    creado = repo.crear(clinica.id_clinica, _datos())

    assert repo.eliminar(clinica.id_clinica, creado.id_paciente) is True
    assert repo.obtener(clinica.id_clinica, creado.id_paciente).activo is False
    assert repo.eliminar(clinica.id_clinica, creado.id_paciente) is True


def test_eliminar_de_otra_clinica_devuelve_false_y_no_lo_toca(db_session):
    clinica_a = crear_clinica(db_session, "Dental A")
    clinica_b = crear_clinica(db_session, "Dental B")
    repo = _repo(db_session)
    de_a = repo.crear(clinica_a.id_clinica, _datos())

    assert repo.eliminar(clinica_b.id_clinica, de_a.id_paciente) is False
    assert repo.obtener(clinica_a.id_clinica, de_a.id_paciente).activo is True


def test_el_repositorio_no_hace_commit(db_session):
    clinica = crear_clinica(db_session)
    db_session.commit()
    id_clinica = clinica.id_clinica

    _repo(db_session).crear(id_clinica, _datos())
    db_session.rollback()

    assert _repo(db_session).listar(id_clinica) == []
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_paciente_repository.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.repositories.paciente_repository'`

- [ ] **Step 3: Escribir el repositorio**

Crear `backend/app/repositories/paciente_repository.py`:

```python
from sqlalchemy import func, or_, select

from app.models import Paciente
from app.repositories.base import BaseRepository


class PacienteRepository(BaseRepository[Paciente]):
    """CRUD de pacientes con borrado logico y busqueda por nombre o apellido.

    Hereda de BaseRepository: es exactamente el caso para el que se diseno, un
    recurso que vive dentro de una clinica.
    """

    def listar(
        self,
        id_clinica: int,
        buscar: str | None = None,
        incluir_inactivos: bool = False,
    ) -> list[Paciente]:
        stmt = select(Paciente).where(Paciente.id_clinica == id_clinica)
        if not incluir_inactivos:
            stmt = stmt.where(Paciente.activo.is_(True))
        if buscar:
            # func.lower() explicito y no confiando en el collation: SQLite es
            # case-sensitive por defecto y MySQL utf8mb4_general_ci no lo es, asi
            # que sin esto el test pasaria con un comportamiento distinto al de
            # produccion.
            patron = f"%{buscar.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Paciente.nombre).like(patron),
                    func.lower(Paciente.apellido).like(patron),
                )
            )
        stmt = stmt.order_by(Paciente.apellido, Paciente.nombre)
        return list(self.db.execute(stmt).scalars().all())

    def obtener(self, id_clinica: int, id_: int) -> Paciente | None:
        stmt = select(Paciente).where(
            Paciente.id_paciente == id_, Paciente.id_clinica == id_clinica
        )
        return self.db.execute(stmt).scalars().first()

    def crear(self, id_clinica: int, data: dict) -> Paciente:
        paciente = Paciente(id_clinica=id_clinica, **data)
        self.db.add(paciente)
        self.db.flush()
        return paciente

    def actualizar(self, id_clinica: int, id_: int, data: dict) -> Paciente | None:
        paciente = self.obtener(id_clinica, id_)
        if paciente is None:
            return None
        for campo, valor in data.items():
            setattr(paciente, campo, valor)
        self.db.flush()
        return paciente

    def eliminar(self, id_clinica: int, id_: int) -> bool:
        """Borrado logico: pone activo = False. Idempotente."""
        paciente = self.obtener(id_clinica, id_)
        if paciente is None:
            return False
        paciente.activo = False
        self.db.flush()
        return True
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_paciente_repository.py -v`
Expected: PASS — 12 passed

- [ ] **Step 5: Punto de commit (lo ejecuta Meli)**

```bash
git add backend/app/repositories/paciente_repository.py \
        backend/tests/test_paciente_repository.py
git commit -m "feat(backend): repositorio de pacientes con busqueda y borrado logico"
```

---

## Task 4: `DoctorRepository` y `AsistenteRepository`

**Files:**
- Create: `backend/app/repositories/doctor_repository.py`
- Create: `backend/app/repositories/asistente_repository.py`
- Test: `backend/tests/test_doctor_repository.py`
- Test: `backend/tests/test_asistente_repository.py`

**Interfaces:**
- Consumes: `BaseRepository[T]`, `Doctor` y `Asistente` (Task 1), factories (Task 2).
- Produces: `DoctorRepository(db)` con la interfaz de `BaseRepository` más
  `listar(id_clinica, id_especialidad: int | None = None, incluir_inactivos: bool = False)` y
  `obtener_por_usuario(id_usuario: int) -> Doctor | None`.
  `AsistenteRepository(db)` con la interfaz de `BaseRepository` más
  `listar(id_clinica, incluir_inactivos: bool = False)` y
  `obtener_por_usuario(id_usuario: int) -> Asistente | None`.

> **No** se crea un `PersonalRepository[T]` compartido. El Módulo 3 justificó `CatalogoRepository`
> con **tres** casos idénticos y presentes; acá hay dos, y `Doctor` ya diverge (especialidad,
> horarios, aparece en las citas y en `get_doctor_actual`). Una base compartida crecería con
> excepciones para el doctor casi de inmediato.

> `obtener_por_usuario` **no** recibe `id_clinica`: es el punto de entrada que traduce el JWT a un
> perfil, y ocurre antes de saber la clínica — la misma excepción documentada que
> `UsuarioRepository.obtener_por_username`. El aislamiento lo aplica el llamador comparando
> `doctor.id_clinica` con el `id_clinica` resuelto.

- [ ] **Step 1: Escribir los tests de doctor que fallan**

Crear `backend/tests/test_doctor_repository.py`:

```python
from tests.factories import crear_clinica, crear_usuario


def _repo(db_session):
    from app.repositories.doctor_repository import DoctorRepository

    return DoctorRepository(db_session)


def _datos(db_session, id_clinica, username="dra.perez", **campos):
    from app.models import RolUsuario

    usuario = crear_usuario(db_session, RolUsuario.DOCTOR, id_clinica, username)
    base = {
        "id_usuario": usuario.id_usuario,
        "nombre": "Marta",
        "apellido": "Perez",
        "telefono": "70003344",
    }
    base.update(campos)
    return base


def _especialidad(db_session, id_clinica, nombre="Ortodoncia"):
    from app.repositories.especialidad_repository import EspecialidadRepository

    return EspecialidadRepository(db_session).crear(id_clinica, {"nombre": nombre})


def test_crear_devuelve_el_doctor_activo_sin_especialidad(db_session):
    clinica = crear_clinica(db_session)

    creado = _repo(db_session).crear(
        clinica.id_clinica, _datos(db_session, clinica.id_clinica)
    )

    assert creado.id_doctor is not None
    assert creado.activo is True
    assert creado.id_especialidad is None


def test_listar_solo_devuelve_los_de_la_clinica_pedida(db_session):
    clinica_a = crear_clinica(db_session, "Dental A")
    clinica_b = crear_clinica(db_session, "Dental B")
    repo = _repo(db_session)
    repo.crear(clinica_a.id_clinica, _datos(db_session, clinica_a.id_clinica, "dra.a"))
    repo.crear(clinica_b.id_clinica, _datos(db_session, clinica_b.id_clinica, "dr.b"))

    assert len(repo.listar(clinica_a.id_clinica)) == 1


def test_listar_filtra_por_especialidad(db_session):
    clinica = crear_clinica(db_session)
    orto = _especialidad(db_session, clinica.id_clinica, "Ortodoncia")
    endo = _especialidad(db_session, clinica.id_clinica, "Endodoncia")
    repo = _repo(db_session)
    repo.crear(
        clinica.id_clinica,
        _datos(db_session, clinica.id_clinica, "dra.a", nombre="Ana",
               id_especialidad=orto.id_especialidad),
    )
    repo.crear(
        clinica.id_clinica,
        _datos(db_session, clinica.id_clinica, "dr.b", nombre="Beto",
               id_especialidad=endo.id_especialidad),
    )

    resultado = repo.listar(clinica.id_clinica, id_especialidad=orto.id_especialidad)

    assert [d.nombre for d in resultado] == ["Ana"]


def test_listar_ordena_por_apellido_y_nombre(db_session):
    clinica = crear_clinica(db_session)
    repo = _repo(db_session)
    repo.crear(
        clinica.id_clinica,
        _datos(db_session, clinica.id_clinica, "dr.z", nombre="Zoe", apellido="Ayala"),
    )
    repo.crear(
        clinica.id_clinica,
        _datos(db_session, clinica.id_clinica, "dra.a", nombre="Ana", apellido="Ayala"),
    )

    assert [d.nombre for d in repo.listar(clinica.id_clinica)] == ["Ana", "Zoe"]


def test_listar_omite_los_inactivos_por_defecto(db_session):
    clinica = crear_clinica(db_session)
    repo = _repo(db_session)
    creado = repo.crear(clinica.id_clinica, _datos(db_session, clinica.id_clinica))
    repo.eliminar(clinica.id_clinica, creado.id_doctor)

    assert repo.listar(clinica.id_clinica) == []
    assert len(repo.listar(clinica.id_clinica, incluir_inactivos=True)) == 1


def test_obtener_de_otra_clinica_devuelve_none(db_session):
    clinica_a = crear_clinica(db_session, "Dental A")
    clinica_b = crear_clinica(db_session, "Dental B")
    repo = _repo(db_session)
    de_a = repo.crear(clinica_a.id_clinica, _datos(db_session, clinica_a.id_clinica))

    assert repo.obtener(clinica_b.id_clinica, de_a.id_doctor) is None


def test_obtener_por_usuario_traduce_el_jwt_a_un_perfil(db_session):
    clinica = crear_clinica(db_session)
    repo = _repo(db_session)
    datos = _datos(db_session, clinica.id_clinica)
    creado = repo.crear(clinica.id_clinica, datos)

    encontrado = repo.obtener_por_usuario(datos["id_usuario"])

    assert encontrado.id_doctor == creado.id_doctor


def test_obtener_por_usuario_de_alguien_sin_perfil_devuelve_none(db_session):
    from app.models import RolUsuario

    clinica = crear_clinica(db_session)
    usuario = crear_usuario(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")

    assert _repo(db_session).obtener_por_usuario(usuario.id_usuario) is None


def test_actualizar_aplica_solo_los_campos_presentes(db_session):
    clinica = crear_clinica(db_session)
    repo = _repo(db_session)
    creado = repo.crear(clinica.id_clinica, _datos(db_session, clinica.id_clinica))

    actualizado = repo.actualizar(
        clinica.id_clinica, creado.id_doctor, {"telefono": "70009999"}
    )

    assert actualizado.telefono == "70009999"
    assert actualizado.nombre == "Marta"


def test_eliminar_es_borrado_logico_y_no_cruza_clinicas(db_session):
    clinica_a = crear_clinica(db_session, "Dental A")
    clinica_b = crear_clinica(db_session, "Dental B")
    repo = _repo(db_session)
    de_a = repo.crear(clinica_a.id_clinica, _datos(db_session, clinica_a.id_clinica))

    assert repo.eliminar(clinica_b.id_clinica, de_a.id_doctor) is False
    assert repo.eliminar(clinica_a.id_clinica, de_a.id_doctor) is True
    assert repo.obtener(clinica_a.id_clinica, de_a.id_doctor).activo is False
```

- [ ] **Step 2: Escribir los tests de asistente que fallan**

Crear `backend/tests/test_asistente_repository.py`:

```python
from tests.factories import crear_clinica, crear_usuario


def _repo(db_session):
    from app.repositories.asistente_repository import AsistenteRepository

    return AsistenteRepository(db_session)


def _datos(db_session, id_clinica, username="recepcion", **campos):
    from app.models import RolUsuario

    usuario = crear_usuario(db_session, RolUsuario.ASISTENTE, id_clinica, username)
    base = {
        "id_usuario": usuario.id_usuario,
        "nombre": "Rosa",
        "apellido": "Diaz",
        "telefono": "70005566",
    }
    base.update(campos)
    return base


def test_crear_devuelve_el_asistente_activo(db_session):
    clinica = crear_clinica(db_session)

    creado = _repo(db_session).crear(
        clinica.id_clinica, _datos(db_session, clinica.id_clinica)
    )

    assert creado.id_asistente is not None
    assert creado.activo is True


def test_listar_solo_devuelve_los_de_la_clinica_pedida(db_session):
    clinica_a = crear_clinica(db_session, "Dental A")
    clinica_b = crear_clinica(db_session, "Dental B")
    repo = _repo(db_session)
    repo.crear(clinica_a.id_clinica, _datos(db_session, clinica_a.id_clinica, "rec.a"))
    repo.crear(clinica_b.id_clinica, _datos(db_session, clinica_b.id_clinica, "rec.b"))

    assert len(repo.listar(clinica_a.id_clinica)) == 1


def test_listar_omite_los_inactivos_por_defecto(db_session):
    clinica = crear_clinica(db_session)
    repo = _repo(db_session)
    creado = repo.crear(clinica.id_clinica, _datos(db_session, clinica.id_clinica))
    repo.eliminar(clinica.id_clinica, creado.id_asistente)

    assert repo.listar(clinica.id_clinica) == []
    assert len(repo.listar(clinica.id_clinica, incluir_inactivos=True)) == 1


def test_obtener_por_usuario_traduce_el_jwt_a_un_perfil(db_session):
    clinica = crear_clinica(db_session)
    repo = _repo(db_session)
    datos = _datos(db_session, clinica.id_clinica)
    creado = repo.crear(clinica.id_clinica, datos)

    assert repo.obtener_por_usuario(datos["id_usuario"]).id_asistente == creado.id_asistente


def test_obtener_de_otra_clinica_devuelve_none(db_session):
    clinica_a = crear_clinica(db_session, "Dental A")
    clinica_b = crear_clinica(db_session, "Dental B")
    repo = _repo(db_session)
    de_a = repo.crear(clinica_a.id_clinica, _datos(db_session, clinica_a.id_clinica))

    assert repo.obtener(clinica_b.id_clinica, de_a.id_asistente) is None
```

- [ ] **Step 3: Correr los tests y verificar que fallan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_doctor_repository.py tests/test_asistente_repository.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.repositories.doctor_repository'`

- [ ] **Step 4: Escribir `DoctorRepository`**

Crear `backend/app/repositories/doctor_repository.py`:

```python
from sqlalchemy import select

from app.models import Doctor
from app.repositories.base import BaseRepository


class DoctorRepository(BaseRepository[Doctor]):
    """CRUD de doctores con borrado logico y filtro por especialidad."""

    def listar(
        self,
        id_clinica: int,
        id_especialidad: int | None = None,
        incluir_inactivos: bool = False,
    ) -> list[Doctor]:
        stmt = select(Doctor).where(Doctor.id_clinica == id_clinica)
        if not incluir_inactivos:
            stmt = stmt.where(Doctor.activo.is_(True))
        if id_especialidad is not None:
            stmt = stmt.where(Doctor.id_especialidad == id_especialidad)
        stmt = stmt.order_by(Doctor.apellido, Doctor.nombre)
        return list(self.db.execute(stmt).scalars().all())

    def obtener(self, id_clinica: int, id_: int) -> Doctor | None:
        stmt = select(Doctor).where(
            Doctor.id_doctor == id_, Doctor.id_clinica == id_clinica
        )
        return self.db.execute(stmt).scalars().first()

    def obtener_por_usuario(self, id_usuario: int) -> Doctor | None:
        """Traduce un Usuario a su perfil de Doctor.

        NO recibe id_clinica, y es la misma excepcion documentada que
        UsuarioRepository.obtener_por_username: es el punto de entrada que
        resuelve el JWT, ocurre antes de saber la clinica de la sesion. Quien
        llame compara doctor.id_clinica con el id_clinica resuelto.
        """
        stmt = select(Doctor).where(Doctor.id_usuario == id_usuario)
        return self.db.execute(stmt).scalars().first()

    def crear(self, id_clinica: int, data: dict) -> Doctor:
        doctor = Doctor(id_clinica=id_clinica, **data)
        self.db.add(doctor)
        self.db.flush()
        return doctor

    def actualizar(self, id_clinica: int, id_: int, data: dict) -> Doctor | None:
        doctor = self.obtener(id_clinica, id_)
        if doctor is None:
            return None
        for campo, valor in data.items():
            setattr(doctor, campo, valor)
        self.db.flush()
        return doctor

    def eliminar(self, id_clinica: int, id_: int) -> bool:
        """Borrado logico del perfil. La desactivacion del Usuario asociado la
        coordina PersonalService, que es quien maneja la transaccion.
        """
        doctor = self.obtener(id_clinica, id_)
        if doctor is None:
            return False
        doctor.activo = False
        self.db.flush()
        return True
```

- [ ] **Step 5: Escribir `AsistenteRepository`**

Crear `backend/app/repositories/asistente_repository.py`:

```python
from sqlalchemy import select

from app.models import Asistente
from app.repositories.base import BaseRepository


class AsistenteRepository(BaseRepository[Asistente]):
    """CRUD de asistentes con borrado logico.

    Deliberadamente NO comparte una clase base con DoctorRepository: son dos
    casos, no tres, y Doctor ya diverge (especialidad, horarios, citas).
    """

    def listar(
        self, id_clinica: int, incluir_inactivos: bool = False
    ) -> list[Asistente]:
        stmt = select(Asistente).where(Asistente.id_clinica == id_clinica)
        if not incluir_inactivos:
            stmt = stmt.where(Asistente.activo.is_(True))
        stmt = stmt.order_by(Asistente.apellido, Asistente.nombre)
        return list(self.db.execute(stmt).scalars().all())

    def obtener(self, id_clinica: int, id_: int) -> Asistente | None:
        stmt = select(Asistente).where(
            Asistente.id_asistente == id_, Asistente.id_clinica == id_clinica
        )
        return self.db.execute(stmt).scalars().first()

    def obtener_por_usuario(self, id_usuario: int) -> Asistente | None:
        stmt = select(Asistente).where(Asistente.id_usuario == id_usuario)
        return self.db.execute(stmt).scalars().first()

    def crear(self, id_clinica: int, data: dict) -> Asistente:
        asistente = Asistente(id_clinica=id_clinica, **data)
        self.db.add(asistente)
        self.db.flush()
        return asistente

    def actualizar(self, id_clinica: int, id_: int, data: dict) -> Asistente | None:
        asistente = self.obtener(id_clinica, id_)
        if asistente is None:
            return None
        for campo, valor in data.items():
            setattr(asistente, campo, valor)
        self.db.flush()
        return asistente

    def eliminar(self, id_clinica: int, id_: int) -> bool:
        asistente = self.obtener(id_clinica, id_)
        if asistente is None:
            return False
        asistente.activo = False
        self.db.flush()
        return True
```

- [ ] **Step 6: Correr los tests y verificar que pasan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_doctor_repository.py tests/test_asistente_repository.py -v`
Expected: PASS — 15 passed

- [ ] **Step 7: Punto de commit (lo ejecuta Meli)**

```bash
git add backend/app/repositories/doctor_repository.py \
        backend/app/repositories/asistente_repository.py \
        backend/tests/test_doctor_repository.py \
        backend/tests/test_asistente_repository.py
git commit -m "feat(backend): repositorios de doctor y asistente"
```

---

## Task 5: `HorarioDoctorRepository`

**Files:**
- Create: `backend/app/repositories/horario_doctor_repository.py`
- Test: `backend/tests/test_horario_doctor_repository.py`

**Interfaces:**
- Consumes: `HorarioDoctor` y `Doctor` (Task 1), `DiaSemana` (Módulo 3), `HorarioInvalidoError`
  (Módulo 3), factories (Task 2).
- Produces: `HorarioDoctorRepository(db)` con
  `listar_de_doctor(id_clinica: int, id_doctor: int) -> list[HorarioDoctor]` y
  `reemplazar_de_doctor(id_clinica: int, id_doctor: int, bloques: list[dict]) -> list[HorarioDoctor]`.
  Cada dict de `bloques` tiene las claves `dia_semana: DiaSemana`, `hora_inicio: time`,
  `hora_fin: time`, `disponible: bool`.

> **No hereda de `BaseRepository`** — tercera excepción documentada, con el mismo criterio que
> `HorarioClinicaRepository` y `ConfiguracionClinicaRepository`: es un recurso anidado bajo doctor,
> su identidad es `(id_clinica, id_doctor)` más el bloque, no un `int` simple. Igual exige
> `id_clinica` como primer parámetro.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `backend/tests/test_horario_doctor_repository.py`:

```python
from datetime import time

import pytest

from tests.factories import crear_clinica, crear_doctor


def _repo(db_session):
    from app.repositories.horario_doctor_repository import HorarioDoctorRepository

    return HorarioDoctorRepository(db_session)


def _bloque(dia, inicio=(8, 0), fin=(12, 0), disponible=True):
    return {
        "dia_semana": dia,
        "hora_inicio": time(*inicio),
        "hora_fin": time(*fin),
        "disponible": disponible,
    }


def test_reemplazar_crea_los_bloques(db_session):
    from app.models import DiaSemana

    clinica = crear_clinica(db_session)
    doctor = crear_doctor(db_session, clinica.id_clinica)

    creados = _repo(db_session).reemplazar_de_doctor(
        clinica.id_clinica,
        doctor.id_doctor,
        [_bloque(DiaSemana.LUNES), _bloque(DiaSemana.LUNES, (14, 0), (18, 0))],
    )

    assert len(creados) == 2


def test_reemplazar_borra_los_bloques_anteriores(db_session):
    from app.models import DiaSemana

    clinica = crear_clinica(db_session)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    repo = _repo(db_session)
    repo.reemplazar_de_doctor(
        clinica.id_clinica, doctor.id_doctor, [_bloque(DiaSemana.LUNES)]
    )

    repo.reemplazar_de_doctor(
        clinica.id_clinica, doctor.id_doctor, [_bloque(DiaSemana.MARTES)]
    )

    dias = [b.dia_semana for b in repo.listar_de_doctor(clinica.id_clinica, doctor.id_doctor)]
    assert dias == [DiaSemana.MARTES]


def test_listar_ordena_de_lunes_a_domingo_y_por_hora(db_session):
    from app.models import DiaSemana

    clinica = crear_clinica(db_session)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    repo = _repo(db_session)
    repo.reemplazar_de_doctor(
        clinica.id_clinica,
        doctor.id_doctor,
        [
            _bloque(DiaSemana.MIERCOLES),
            _bloque(DiaSemana.LUNES, (14, 0), (18, 0)),
            _bloque(DiaSemana.LUNES, (8, 0), (12, 0)),
        ],
    )

    resultado = repo.listar_de_doctor(clinica.id_clinica, doctor.id_doctor)

    assert [(b.dia_semana, b.hora_inicio) for b in resultado] == [
        (DiaSemana.LUNES, time(8, 0)),
        (DiaSemana.LUNES, time(14, 0)),
        (DiaSemana.MIERCOLES, time(8, 0)),
    ]


def test_listar_un_doctor_de_otra_clinica_devuelve_lista_vacia(db_session):
    from app.models import DiaSemana

    clinica_a = crear_clinica(db_session, "Dental A")
    clinica_b = crear_clinica(db_session, "Dental B")
    doctor_a = crear_doctor(db_session, clinica_a.id_clinica, "dra.a")
    repo = _repo(db_session)
    repo.reemplazar_de_doctor(
        clinica_a.id_clinica, doctor_a.id_doctor, [_bloque(DiaSemana.LUNES)]
    )

    assert repo.listar_de_doctor(clinica_b.id_clinica, doctor_a.id_doctor) == []


def test_reemplazar_el_horario_de_un_doctor_ajeno_no_lo_toca(db_session):
    from app.models import DiaSemana

    clinica_a = crear_clinica(db_session, "Dental A")
    clinica_b = crear_clinica(db_session, "Dental B")
    doctor_a = crear_doctor(db_session, clinica_a.id_clinica, "dra.a")
    repo = _repo(db_session)
    repo.reemplazar_de_doctor(
        clinica_a.id_clinica, doctor_a.id_doctor, [_bloque(DiaSemana.LUNES)]
    )

    resultado = repo.reemplazar_de_doctor(
        clinica_b.id_clinica, doctor_a.id_doctor, [_bloque(DiaSemana.MARTES)]
    )

    assert resultado == []
    dias = [b.dia_semana for b in repo.listar_de_doctor(clinica_a.id_clinica, doctor_a.id_doctor)]
    assert dias == [DiaSemana.LUNES]


def test_bloque_con_fin_menor_o_igual_al_inicio_es_invalido(db_session):
    from app.exceptions import HorarioInvalidoError
    from app.models import DiaSemana

    clinica = crear_clinica(db_session)
    doctor = crear_doctor(db_session, clinica.id_clinica)

    with pytest.raises(HorarioInvalidoError):
        _repo(db_session).reemplazar_de_doctor(
            clinica.id_clinica,
            doctor.id_doctor,
            [_bloque(DiaSemana.LUNES, (12, 0), (8, 0))],
        )


def test_dos_bloques_solapados_el_mismo_dia_son_invalidos(db_session):
    from app.exceptions import HorarioInvalidoError
    from app.models import DiaSemana

    clinica = crear_clinica(db_session)
    doctor = crear_doctor(db_session, clinica.id_clinica)

    with pytest.raises(HorarioInvalidoError):
        _repo(db_session).reemplazar_de_doctor(
            clinica.id_clinica,
            doctor.id_doctor,
            [
                _bloque(DiaSemana.LUNES, (8, 0), (12, 0)),
                _bloque(DiaSemana.LUNES, (11, 0), (14, 0)),
            ],
        )


def test_dos_bloques_pegados_el_mismo_dia_son_validos(db_session):
    """Uno que termina justo cuando arranca el otro no se solapa."""
    from app.models import DiaSemana

    clinica = crear_clinica(db_session)
    doctor = crear_doctor(db_session, clinica.id_clinica)

    creados = _repo(db_session).reemplazar_de_doctor(
        clinica.id_clinica,
        doctor.id_doctor,
        [
            _bloque(DiaSemana.LUNES, (8, 0), (12, 0)),
            _bloque(DiaSemana.LUNES, (12, 0), (16, 0)),
        ],
    )

    assert len(creados) == 2


def test_valida_todos_los_bloques_antes_de_escribir_ninguno(db_session):
    from app.exceptions import HorarioInvalidoError
    from app.models import DiaSemana

    clinica = crear_clinica(db_session)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    repo = _repo(db_session)

    with pytest.raises(HorarioInvalidoError):
        repo.reemplazar_de_doctor(
            clinica.id_clinica,
            doctor.id_doctor,
            [_bloque(DiaSemana.LUNES), _bloque(DiaSemana.MARTES, (12, 0), (8, 0))],
        )

    assert repo.listar_de_doctor(clinica.id_clinica, doctor.id_doctor) == []
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_horario_doctor_repository.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.repositories.horario_doctor_repository'`

- [ ] **Step 3: Escribir el repositorio**

Crear `backend/app/repositories/horario_doctor_repository.py`:

```python
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.exceptions import HorarioInvalidoError
from app.models import DiaSemana, Doctor, HorarioDoctor

#: Orden natural de la semana, para ordenar en SQL sin depender de como el
#: motor ordene el tipo ENUM (SQLite lo guarda como texto y ordenaria alfabetico).
_ORDEN_DIA = {dia: indice for indice, dia in enumerate(DiaSemana)}


class HorarioDoctorRepository:
    """Bloques de disponibilidad de un doctor.

    NO hereda de BaseRepository: es un recurso anidado bajo doctor, su identidad
    es (id_clinica, id_doctor) mas el bloque, no un int simple como asume la
    firma de la clase base. Misma excepcion documentada que
    HorarioClinicaRepository y ConfiguracionClinicaRepository.

    Igual exige id_clinica como primer parametro, y lo aplica verificando que el
    doctor pertenezca a esa clinica antes de tocar nada.
    """

    def __init__(self, db: Session):
        self.db = db

    def _doctor_de_la_clinica(self, id_clinica: int, id_doctor: int) -> Doctor | None:
        stmt = select(Doctor).where(
            Doctor.id_doctor == id_doctor, Doctor.id_clinica == id_clinica
        )
        return self.db.execute(stmt).scalars().first()

    def listar_de_doctor(self, id_clinica: int, id_doctor: int) -> list[HorarioDoctor]:
        """Lista vacia si el doctor no existe o es de otra clinica."""
        if self._doctor_de_la_clinica(id_clinica, id_doctor) is None:
            return []
        stmt = select(HorarioDoctor).where(HorarioDoctor.id_doctor == id_doctor)
        bloques = list(self.db.execute(stmt).scalars().all())
        # Ordenar en Python y no en SQL: el ENUM se guarda como texto y el motor
        # ordenaria alfabeticamente (domingo antes que lunes).
        bloques.sort(key=lambda b: (_ORDEN_DIA[b.dia_semana], b.hora_inicio))
        return bloques

    @staticmethod
    def _validar(bloques: list[dict]) -> None:
        """Valida TODOS los bloques antes de que se escriba ninguno, para que el
        horario no pueda quedar en un estado intermedio inconsistente.
        """
        for bloque in bloques:
            if bloque["hora_fin"] <= bloque["hora_inicio"]:
                raise HorarioInvalidoError(
                    f"{bloque['dia_semana'].value}: la hora de fin debe ser posterior "
                    f"a la de inicio"
                )

        por_dia: dict[DiaSemana, list[dict]] = {}
        for bloque in bloques:
            por_dia.setdefault(bloque["dia_semana"], []).append(bloque)

        for dia, del_dia in por_dia.items():
            ordenados = sorted(del_dia, key=lambda b: b["hora_inicio"])
            for anterior, siguiente in zip(ordenados, ordenados[1:]):
                if siguiente["hora_inicio"] < anterior["hora_fin"]:
                    raise HorarioInvalidoError(
                        f"{dia.value}: hay dos bloques solapados"
                    )

    def reemplazar_de_doctor(
        self, id_clinica: int, id_doctor: int, bloques: list[dict]
    ) -> list[HorarioDoctor]:
        """Reemplaza el conjunto completo de bloques del doctor.

        Devuelve lista vacia sin tocar nada si el doctor es de otra clinica.
        """
        if self._doctor_de_la_clinica(id_clinica, id_doctor) is None:
            return []

        self._validar(bloques)

        self.db.execute(delete(HorarioDoctor).where(HorarioDoctor.id_doctor == id_doctor))
        for bloque in bloques:
            self.db.add(HorarioDoctor(id_doctor=id_doctor, **bloque))
        self.db.flush()
        return self.listar_de_doctor(id_clinica, id_doctor)
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_horario_doctor_repository.py -v`
Expected: PASS — 9 passed

- [ ] **Step 5: Punto de commit (lo ejecuta Meli)**

```bash
git add backend/app/repositories/horario_doctor_repository.py \
        backend/tests/test_horario_doctor_repository.py
git commit -m "feat(backend): repositorio de horarios por doctor"
```

---

## Task 6: `CitaRepository`

**Files:**
- Create: `backend/app/repositories/cita_repository.py`
- Test: `backend/tests/test_cita_repository.py`

**Interfaces:**
- Consumes: `BaseRepository[T]`, `Cita`, `EstadoCita`, `ESTADOS_ACTIVOS` (Task 1), factories
  (Task 2).
- Produces: `CitaRepository(db)` con la interfaz de `BaseRepository` más:
  - `listar(id_clinica, desde: datetime | None = None, hasta: datetime | None = None, id_doctor: int | None = None, id_paciente: int | None = None, estado: EstadoCita | None = None) -> list[Cita]`
  - `hay_solapamiento_de_doctor(id_clinica, id_doctor, inicio: datetime, fin: datetime, excluir_id_cita: int | None = None) -> bool`
  - `hay_solapamiento_de_consultorio(id_clinica, id_consultorio, inicio: datetime, fin: datetime, excluir_id_cita: int | None = None) -> bool`

> El solapamiento va en el repositorio y no en el validador porque es una **consulta**, no una
> regla: el validador decide qué hacer con la respuesta. `excluir_id_cita` existe para el
> reagendamiento — sin él una cita chocaría contra sí misma al verificar su horario nuevo.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `backend/tests/test_cita_repository.py`:

```python
from datetime import datetime, timedelta

from tests.factories import crear_cita, crear_clinica, crear_doctor, crear_paciente

INICIO = datetime(2026, 9, 1, 9, 0)


def _repo(db_session):
    from app.repositories.cita_repository import CitaRepository

    return CitaRepository(db_session)


def _escenario(db_session, nombre="Dental A", username="dra.perez"):
    """Devuelve (id_clinica, id_paciente, id_doctor)."""
    clinica = crear_clinica(db_session, nombre)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica, username)
    return clinica.id_clinica, paciente.id_paciente, doctor.id_doctor


def test_crear_devuelve_la_cita_programada(db_session):
    from app.models import EstadoCita

    id_clinica, id_paciente, id_doctor = _escenario(db_session)

    creada = _repo(db_session).crear(
        id_clinica,
        {
            "id_paciente": id_paciente,
            "id_doctor": id_doctor,
            "fecha_hora": INICIO,
            "duracion_minutos": 30,
        },
    )

    assert creada.id_cita is not None
    assert creada.estado == EstadoCita.PROGRAMADA


def test_listar_solo_devuelve_las_de_la_clinica_pedida(db_session):
    id_clinica_a, id_paciente_a, id_doctor_a = _escenario(db_session, "Dental A", "dra.a")
    id_clinica_b, id_paciente_b, id_doctor_b = _escenario(db_session, "Dental B", "dr.b")
    crear_cita(db_session, id_clinica_a, id_paciente_a, id_doctor_a)
    crear_cita(db_session, id_clinica_b, id_paciente_b, id_doctor_b)

    assert len(_repo(db_session).listar(id_clinica_a)) == 1


def test_listar_filtra_por_rango_de_fechas(db_session):
    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    crear_cita(db_session, id_clinica, id_paciente, id_doctor, fecha_hora=INICIO)
    crear_cita(
        db_session, id_clinica, id_paciente, id_doctor,
        fecha_hora=INICIO + timedelta(days=10),
    )

    resultado = _repo(db_session).listar(
        id_clinica, desde=INICIO - timedelta(hours=1), hasta=INICIO + timedelta(hours=1)
    )

    assert len(resultado) == 1


def test_listar_filtra_por_doctor_paciente_y_estado(db_session):
    from app.models import EstadoCita

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    otro_doctor = crear_doctor(db_session, id_clinica, "dr.otro")
    crear_cita(db_session, id_clinica, id_paciente, id_doctor)
    crear_cita(
        db_session, id_clinica, id_paciente, otro_doctor.id_doctor,
        fecha_hora=INICIO + timedelta(days=1),
    )
    crear_cita(
        db_session, id_clinica, id_paciente, id_doctor,
        fecha_hora=INICIO + timedelta(days=2), estado=EstadoCita.CANCELADA,
    )

    repo = _repo(db_session)

    assert len(repo.listar(id_clinica, id_doctor=id_doctor)) == 2
    assert len(repo.listar(id_clinica, id_paciente=id_paciente)) == 3
    assert len(repo.listar(id_clinica, estado=EstadoCita.CANCELADA)) == 1


def test_listar_ordena_por_fecha_ascendente(db_session):
    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    crear_cita(
        db_session, id_clinica, id_paciente, id_doctor,
        fecha_hora=INICIO + timedelta(days=5),
    )
    crear_cita(db_session, id_clinica, id_paciente, id_doctor, fecha_hora=INICIO)

    resultado = _repo(db_session).listar(id_clinica)

    assert [c.fecha_hora for c in resultado] == [INICIO, INICIO + timedelta(days=5)]


def test_hay_solapamiento_de_doctor_detecta_el_cruce(db_session):
    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    crear_cita(
        db_session, id_clinica, id_paciente, id_doctor,
        fecha_hora=INICIO, duracion_minutos=60,
    )

    # 09:30-10:00 cae dentro de 09:00-10:00
    assert _repo(db_session).hay_solapamiento_de_doctor(
        id_clinica, id_doctor, INICIO + timedelta(minutes=30), INICIO + timedelta(hours=1)
    ) is True


def test_una_cita_pegada_a_otra_no_es_solapamiento(db_session):
    """El borde: 10:00-10:30 arranca justo cuando 09:00-10:00 termina."""
    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    crear_cita(
        db_session, id_clinica, id_paciente, id_doctor,
        fecha_hora=INICIO, duracion_minutos=60,
    )

    assert _repo(db_session).hay_solapamiento_de_doctor(
        id_clinica, id_doctor, INICIO + timedelta(hours=1), INICIO + timedelta(hours=2)
    ) is False


def test_una_cita_cancelada_no_cuenta_como_choque(db_session):
    from app.models import EstadoCita

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    crear_cita(
        db_session, id_clinica, id_paciente, id_doctor,
        fecha_hora=INICIO, duracion_minutos=60, estado=EstadoCita.CANCELADA,
    )

    assert _repo(db_session).hay_solapamiento_de_doctor(
        id_clinica, id_doctor, INICIO, INICIO + timedelta(hours=1)
    ) is False


def test_excluir_id_cita_evita_que_una_cita_choque_consigo_misma(db_session):
    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    cita = crear_cita(
        db_session, id_clinica, id_paciente, id_doctor,
        fecha_hora=INICIO, duracion_minutos=60,
    )
    repo = _repo(db_session)

    assert repo.hay_solapamiento_de_doctor(
        id_clinica, id_doctor, INICIO, INICIO + timedelta(hours=1)
    ) is True
    assert repo.hay_solapamiento_de_doctor(
        id_clinica, id_doctor, INICIO, INICIO + timedelta(hours=1),
        excluir_id_cita=cita.id_cita,
    ) is False


def test_una_cita_larga_que_empieza_mucho_antes_igual_se_detecta(db_session):
    """Blinda el prefiltro de _solapadas.

    La consulta prefiltra en SQL por una ventana de fechas antes de calcular el
    solapamiento en Python. Si esa ventana fuera mas corta que la duracion
    maxima de una cita, una cita larga que arranca mucho antes quedaria afuera
    del prefiltro y el choque no se detectaria: un falso negativo silencioso,
    que es el peor tipo de bug de agenda.
    """
    from app.repositories.cita_repository import DURACION_MAXIMA_MINUTOS

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    arranque = INICIO - timedelta(minutes=DURACION_MAXIMA_MINUTOS - 30)
    crear_cita(
        db_session, id_clinica, id_paciente, id_doctor,
        fecha_hora=arranque, duracion_minutos=DURACION_MAXIMA_MINUTOS,
    )

    # La cita larga sigue vigente 30 minutos despues de INICIO.
    assert _repo(db_session).hay_solapamiento_de_doctor(
        id_clinica, id_doctor, INICIO, INICIO + timedelta(minutes=15)
    ) is True


def test_el_solapamiento_de_doctor_no_cruza_clinicas(db_session):
    id_clinica_a, id_paciente_a, id_doctor_a = _escenario(db_session, "Dental A", "dra.a")
    clinica_b = crear_clinica(db_session, "Dental B")
    crear_cita(db_session, id_clinica_a, id_paciente_a, id_doctor_a, fecha_hora=INICIO)

    assert _repo(db_session).hay_solapamiento_de_doctor(
        clinica_b.id_clinica, id_doctor_a, INICIO, INICIO + timedelta(minutes=30)
    ) is False


def test_hay_solapamiento_de_consultorio(db_session):
    from app.repositories.consultorio_repository import ConsultorioRepository

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    consultorio = ConsultorioRepository(db_session).crear(id_clinica, {"nombre": "Sala 1"})
    otro_doctor = crear_doctor(db_session, id_clinica, "dr.otro")
    crear_cita(
        db_session, id_clinica, id_paciente, id_doctor,
        fecha_hora=INICIO, duracion_minutos=60,
        id_consultorio=consultorio.id_consultorio,
    )

    # Otro doctor, misma sala, mismo horario: choca igual.
    assert _repo(db_session).hay_solapamiento_de_consultorio(
        id_clinica, consultorio.id_consultorio, INICIO, INICIO + timedelta(minutes=30)
    ) is True
    assert otro_doctor.id_doctor != id_doctor


def test_obtener_de_otra_clinica_devuelve_none(db_session):
    id_clinica_a, id_paciente_a, id_doctor_a = _escenario(db_session, "Dental A", "dra.a")
    clinica_b = crear_clinica(db_session, "Dental B")
    cita = crear_cita(db_session, id_clinica_a, id_paciente_a, id_doctor_a)

    assert _repo(db_session).obtener(clinica_b.id_clinica, cita.id_cita) is None


def test_eliminar_no_esta_soportado(db_session):
    """Una cita no se borra, se cancela: perder el registro romperia el historial
    del paciente y las metricas del Modulo 7.
    """
    import pytest

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    cita = crear_cita(db_session, id_clinica, id_paciente, id_doctor)

    with pytest.raises(NotImplementedError):
        _repo(db_session).eliminar(id_clinica, cita.id_cita)
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_cita_repository.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.repositories.cita_repository'`

- [ ] **Step 3: Escribir el repositorio**

Crear `backend/app/repositories/cita_repository.py`:

```python
from datetime import datetime, timedelta

from sqlalchemy import select

from app.models import ESTADOS_ACTIVOS, Cita, EstadoCita
from app.repositories.base import BaseRepository

#: Duracion maxima que puede tener una cita, en minutos. Es el mismo tope que
#: valida el schema CitaCreate (5 a 480, o sea hasta 8 horas).
#:
#: El prefiltro de _solapadas necesita este numero: para encontrar todas las
#: citas que puedan pisar un rango dado, alcanza con mirar las que empiezan
#: hasta DURACION_MAXIMA_MINUTOS antes del inicio de ese rango. Una cita que
#: empiece antes que eso ya termino con seguridad.
#:
#: Si alguna vez se sube el tope del schema, hay que subir este numero tambien
#: o el prefiltro empieza a dejar afuera solapamientos reales.
DURACION_MAXIMA_MINUTOS = 480


class CitaRepository(BaseRepository[Cita]):
    """CRUD de citas mas las consultas de agenda y solapamiento.

    Los metodos de solapamiento viven aca y no en los validadores porque son
    consultas, no reglas: el validador decide que hacer con la respuesta.
    """

    def listar(
        self,
        id_clinica: int,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        id_doctor: int | None = None,
        id_paciente: int | None = None,
        estado: EstadoCita | None = None,
    ) -> list[Cita]:
        stmt = select(Cita).where(Cita.id_clinica == id_clinica)
        if desde is not None:
            stmt = stmt.where(Cita.fecha_hora >= desde)
        if hasta is not None:
            stmt = stmt.where(Cita.fecha_hora <= hasta)
        if id_doctor is not None:
            stmt = stmt.where(Cita.id_doctor == id_doctor)
        if id_paciente is not None:
            stmt = stmt.where(Cita.id_paciente == id_paciente)
        if estado is not None:
            stmt = stmt.where(Cita.estado == estado)
        stmt = stmt.order_by(Cita.fecha_hora)
        return list(self.db.execute(stmt).scalars().all())

    def obtener(self, id_clinica: int, id_: int) -> Cita | None:
        stmt = select(Cita).where(Cita.id_cita == id_, Cita.id_clinica == id_clinica)
        return self.db.execute(stmt).scalars().first()

    def crear(self, id_clinica: int, data: dict) -> Cita:
        cita = Cita(id_clinica=id_clinica, **data)
        self.db.add(cita)
        self.db.flush()
        return cita

    def actualizar(self, id_clinica: int, id_: int, data: dict) -> Cita | None:
        cita = self.obtener(id_clinica, id_)
        if cita is None:
            return None
        for campo, valor in data.items():
            setattr(cita, campo, valor)
        self.db.flush()
        return cita

    def eliminar(self, id_clinica: int, id_: int) -> bool:
        """Una cita no se borra, se cancela.

        Borrarla perderia el registro de que existio, que es justamente lo que la
        clinica necesita para el historial del paciente y para las metricas del
        Modulo 7. Se implementa para cumplir el contrato de BaseRepository y se
        niega explicitamente, en vez de dejar un metodo que silenciosamente
        destruya datos.
        """
        raise NotImplementedError(
            "Las citas no se borran: usar CitaService.cancelar()"
        )

    def _solapadas(self, id_clinica: int, inicio: datetime, fin: datetime, excluir_id_cita):
        """Condicion clasica de solapamiento: inicio_a < fin_b AND inicio_b < fin_a.

        Como la duracion se guarda en minutos y no hay columna fecha_fin, el fin
        de cada cita hay que calcularlo sumando duracion_minutos. Eso se hace en
        Python y no en SQL porque la aritmetica de fechas tiene sintaxis distinta
        en SQLite y en MySQL, y no queremos que el comportamiento difiera entre
        los tests y produccion.

        Para no traer toda la tabla a Python, primero se prefiltra en SQL por
        clinica, estado y una ventana de fechas. La ventana hacia atras es
        DURACION_MAXIMA_MINUTOS y no un numero al azar: una cita que empieza
        antes que eso ya termino con seguridad, asi que no puede pisar el rango
        consultado. Si el tope de duracion sube, este prefiltro empieza a dejar
        afuera solapamientos reales — por eso son la misma constante.
        """
        margen = timedelta(minutes=DURACION_MAXIMA_MINUTOS)
        stmt = select(Cita).where(
            Cita.id_clinica == id_clinica,
            Cita.estado.in_(ESTADOS_ACTIVOS),
            Cita.fecha_hora >= inicio - margen,
            Cita.fecha_hora <= fin + margen,
        )
        if excluir_id_cita is not None:
            stmt = stmt.where(Cita.id_cita != excluir_id_cita)
        candidatas = self.db.execute(stmt).scalars().all()
        return [
            c
            for c in candidatas
            if c.fecha_hora < fin
            and inicio < c.fecha_hora + timedelta(minutes=c.duracion_minutos)
        ]

    def hay_solapamiento_de_doctor(
        self,
        id_clinica: int,
        id_doctor: int,
        inicio: datetime,
        fin: datetime,
        excluir_id_cita: int | None = None,
    ) -> bool:
        solapadas = self._solapadas(id_clinica, inicio, fin, excluir_id_cita)
        return any(c.id_doctor == id_doctor for c in solapadas)

    def hay_solapamiento_de_consultorio(
        self,
        id_clinica: int,
        id_consultorio: int,
        inicio: datetime,
        fin: datetime,
        excluir_id_cita: int | None = None,
    ) -> bool:
        solapadas = self._solapadas(id_clinica, inicio, fin, excluir_id_cita)
        return any(c.id_consultorio == id_consultorio for c in solapadas)
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_cita_repository.py -v`
Expected: PASS — 13 passed

- [ ] **Step 5: Correr la suite completa**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: todo verde.

- [ ] **Step 6: Punto de commit (lo ejecuta Meli)**

```bash
git add backend/app/repositories/cita_repository.py backend/tests/test_cita_repository.py
git commit -m "feat(backend): repositorio de citas con consultas de agenda y solapamiento"
```

---

## Task 7: Excepciones de dominio y validadores de cita

**Files:**
- Modify: `backend/app/exceptions.py`
- Create: `backend/app/services/validadores_cita.py`
- Test: `backend/tests/test_validadores_cita.py`

**Interfaces:**
- Consumes: repositorios de las Tasks 3 a 6, `HORARIO_POR_DEFECTO` y `DiaSemana` (Módulo 3),
  `HorarioClinicaRepository` (Módulo 3).
- Produces:
  - Excepciones: `ReferenciaInvalidaError`, `CitaEnElPasadoError`, `AnticipacionInsuficienteError`,
    `FueraDeHorarioClinicaError`, `DoctorNoDisponibleError`, `ChoqueDeCitaError`,
    `TransicionInvalidaError`.
  - `ContextoCita` (dataclass frozen) con los campos `id_clinica`, `id_paciente`, `id_doctor`,
    `id_consultorio`, `fecha_hora`, `duracion_minutos`, `configuracion`, `ahora`,
    `excluir_id_cita`, y las propiedades `fin: datetime` y `dia_semana: DiaSemana`.
  - `ValidadorDeCita` (Protocol) con `validar(ctx: ContextoCita) -> None`.
  - Las siete clases validadoras y `validadores_por_defecto(db) -> list[ValidadorDeCita]`.

> **Este es el corazón del módulo.** Cada regla es un objeto chico e independiente que se testea sin
> base de datos y sin servicio: se arma un `ContextoCita` a mano y se le pasan dobles a los
> validadores que consultan. Agregar una regla en el futuro es un archivo nuevo y un renglón en
> `validadores_por_defecto`, no editar `CitaService`.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `backend/tests/test_validadores_cita.py`:

```python
"""Tests de los validadores: SIN base de datos y SIN servicio.

Ese es el premio de haberlos separado. El contexto se arma a mano y los
validadores que consultan reciben dobles.
"""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

import pytest

AHORA = datetime(2026, 9, 1, 8, 0)  # martes
MANANA_9 = datetime(2026, 9, 2, 9, 0)  # miercoles 09:00


@dataclass
class _Config:
    anticipacion_minima_reserva_horas: int = 24
    duracion_cita_minutos: int = 30
    horas_minimas_cambio_cita: int = 24
    dias_minimos_reagendamiento: int = 3


@dataclass
class _Fila:
    """Sirve como paciente, doctor o consultorio de mentira."""
    activo: bool = True


@dataclass
class _Bloque:
    dia_semana: object
    hora_inicio: time
    hora_fin: time
    disponible: bool = True


class _RepoDeUno:
    """Doble que devuelve siempre lo mismo desde obtener()."""

    def __init__(self, valor):
        self.valor = valor

    def obtener(self, id_clinica, id_):
        return self.valor


class _HorariosClinica:
    def __init__(self, filas):
        self.filas = filas

    def listar_semana(self, id_clinica):
        return self.filas


class _HorariosDoctor:
    def __init__(self, bloques):
        self.bloques = bloques

    def listar_de_doctor(self, id_clinica, id_doctor):
        return self.bloques


class _Citas:
    def __init__(self, choca_doctor=False, choca_consultorio=False):
        self.choca_doctor = choca_doctor
        self.choca_consultorio = choca_consultorio
        self.ultima_exclusion = "no-llamado"

    def hay_solapamiento_de_doctor(self, id_clinica, id_doctor, inicio, fin, excluir_id_cita=None):
        self.ultima_exclusion = excluir_id_cita
        return self.choca_doctor

    def hay_solapamiento_de_consultorio(
        self, id_clinica, id_consultorio, inicio, fin, excluir_id_cita=None
    ):
        return self.choca_consultorio


def _ctx(**campos):
    from app.services.validadores_cita import ContextoCita

    base = {
        "id_clinica": 1,
        "id_paciente": 10,
        "id_doctor": 20,
        "id_consultorio": None,
        "fecha_hora": MANANA_9,
        "duracion_minutos": 30,
        "configuracion": _Config(),
        "ahora": AHORA,
    }
    base.update(campos)
    return ContextoCita(**base)


# --- ContextoCita ---------------------------------------------------------

def test_el_contexto_calcula_el_fin_y_el_dia_de_la_semana():
    from app.models import DiaSemana

    ctx = _ctx(fecha_hora=MANANA_9, duracion_minutos=45)

    assert ctx.fin == MANANA_9 + timedelta(minutes=45)
    assert ctx.dia_semana == DiaSemana.MIERCOLES


# --- 1. ReferenciasDeLaMismaClinica ---------------------------------------

def _referencias(paciente=_Fila(), doctor=_Fila(), consultorio=_Fila()):
    from app.services.validadores_cita import ReferenciasDeLaMismaClinica

    return ReferenciasDeLaMismaClinica(
        _RepoDeUno(paciente), _RepoDeUno(doctor), _RepoDeUno(consultorio)
    )


def test_referencias_validas_no_lanzan_nada():
    _referencias().validar(_ctx())


def test_paciente_inexistente_es_referencia_invalida():
    from app.exceptions import ReferenciaInvalidaError

    with pytest.raises(ReferenciaInvalidaError):
        _referencias(paciente=None).validar(_ctx())


def test_paciente_inactivo_es_referencia_invalida():
    from app.exceptions import ReferenciaInvalidaError

    with pytest.raises(ReferenciaInvalidaError):
        _referencias(paciente=_Fila(activo=False)).validar(_ctx())


def test_doctor_inexistente_o_inactivo_es_referencia_invalida():
    from app.exceptions import ReferenciaInvalidaError

    with pytest.raises(ReferenciaInvalidaError):
        _referencias(doctor=None).validar(_ctx())
    with pytest.raises(ReferenciaInvalidaError):
        _referencias(doctor=_Fila(activo=False)).validar(_ctx())


def test_el_consultorio_solo_se_valida_si_vino():
    from app.exceptions import ReferenciaInvalidaError

    _referencias(consultorio=None).validar(_ctx(id_consultorio=None))

    with pytest.raises(ReferenciaInvalidaError):
        _referencias(consultorio=None).validar(_ctx(id_consultorio=5))


# --- 2. NoEnElPasado ------------------------------------------------------

def test_una_cita_futura_pasa_y_una_pasada_no():
    from app.exceptions import CitaEnElPasadoError
    from app.services.validadores_cita import NoEnElPasado

    NoEnElPasado().validar(_ctx(fecha_hora=AHORA + timedelta(minutes=1)))

    with pytest.raises(CitaEnElPasadoError):
        NoEnElPasado().validar(_ctx(fecha_hora=AHORA - timedelta(minutes=1)))


def test_una_cita_exactamente_ahora_esta_en_el_pasado():
    from app.exceptions import CitaEnElPasadoError
    from app.services.validadores_cita import NoEnElPasado

    with pytest.raises(CitaEnElPasadoError):
        NoEnElPasado().validar(_ctx(fecha_hora=AHORA))


# --- 3. AnticipacionMinima ------------------------------------------------

def test_anticipacion_justa_pasa_y_una_hora_menos_no():
    from app.exceptions import AnticipacionInsuficienteError
    from app.services.validadores_cita import AnticipacionMinima

    validador = AnticipacionMinima()
    validador.validar(_ctx(fecha_hora=AHORA + timedelta(hours=24)))

    with pytest.raises(AnticipacionInsuficienteError):
        validador.validar(_ctx(fecha_hora=AHORA + timedelta(hours=23)))


def test_la_anticipacion_sale_de_la_configuracion_de_la_clinica():
    from app.services.validadores_cita import AnticipacionMinima

    permisiva = _Config(anticipacion_minima_reserva_horas=2)

    AnticipacionMinima().validar(
        _ctx(fecha_hora=AHORA + timedelta(hours=2), configuracion=permisiva)
    )


# --- 4. DentroDelHorarioDeLaClinica ---------------------------------------

def _horario_clinica(filas):
    from app.services.validadores_cita import DentroDelHorarioDeLaClinica

    return DentroDelHorarioDeLaClinica(_HorariosClinica(filas))


@dataclass
class _FilaHorario:
    dia_semana: object
    hora_apertura: time | None
    hora_cierre: time | None
    cerrado: bool = False


def test_sin_filas_usa_el_horario_por_defecto_y_el_miercoles_esta_abierto():
    _horario_clinica([]).validar(_ctx(fecha_hora=MANANA_9))


def test_sin_filas_el_domingo_esta_cerrado_por_defecto():
    from app.exceptions import FueraDeHorarioClinicaError

    domingo_9 = datetime(2026, 9, 6, 9, 0)

    with pytest.raises(FueraDeHorarioClinicaError):
        _horario_clinica([]).validar(_ctx(fecha_hora=domingo_9))


def test_una_cita_que_termina_despues_del_cierre_no_pasa():
    from app.exceptions import FueraDeHorarioClinicaError
    from app.models import DiaSemana

    filas = [_FilaHorario(DiaSemana.MIERCOLES, time(8, 0), time(17, 0))]
    validador = _horario_clinica(filas)

    validador.validar(_ctx(fecha_hora=datetime(2026, 9, 2, 16, 30), duracion_minutos=30))

    with pytest.raises(FueraDeHorarioClinicaError):
        validador.validar(
            _ctx(fecha_hora=datetime(2026, 9, 2, 16, 45), duracion_minutos=30)
        )


def test_una_cita_antes_de_la_apertura_no_pasa():
    from app.exceptions import FueraDeHorarioClinicaError
    from app.models import DiaSemana

    filas = [_FilaHorario(DiaSemana.MIERCOLES, time(8, 0), time(17, 0))]

    with pytest.raises(FueraDeHorarioClinicaError):
        _horario_clinica(filas).validar(_ctx(fecha_hora=datetime(2026, 9, 2, 7, 30)))


def test_un_dia_marcado_cerrado_no_pasa():
    from app.exceptions import FueraDeHorarioClinicaError
    from app.models import DiaSemana

    filas = [_FilaHorario(DiaSemana.MIERCOLES, None, None, cerrado=True)]

    with pytest.raises(FueraDeHorarioClinicaError):
        _horario_clinica(filas).validar(_ctx(fecha_hora=MANANA_9))


# --- 5. DentroDelHorarioDelDoctor -----------------------------------------

def _horario_doctor(bloques):
    from app.services.validadores_cita import DentroDelHorarioDelDoctor

    return DentroDelHorarioDelDoctor(_HorariosDoctor(bloques))


def test_un_doctor_sin_bloques_cargados_no_esta_disponible():
    from app.exceptions import DoctorNoDisponibleError

    with pytest.raises(DoctorNoDisponibleError):
        _horario_doctor([]).validar(_ctx())


def test_la_cita_debe_caer_entera_dentro_de_un_mismo_bloque():
    from app.exceptions import DoctorNoDisponibleError
    from app.models import DiaSemana

    bloques = [
        _Bloque(DiaSemana.MIERCOLES, time(8, 0), time(12, 0)),
        _Bloque(DiaSemana.MIERCOLES, time(14, 0), time(18, 0)),
    ]
    validador = _horario_doctor(bloques)

    validador.validar(_ctx(fecha_hora=datetime(2026, 9, 2, 11, 30), duracion_minutos=30))

    # 11:45-12:15 se sale del bloque de la manana y no entra en el de la tarde.
    with pytest.raises(DoctorNoDisponibleError):
        validador.validar(
            _ctx(fecha_hora=datetime(2026, 9, 2, 11, 45), duracion_minutos=30)
        )


def test_un_bloque_marcado_no_disponible_no_sirve():
    from app.exceptions import DoctorNoDisponibleError
    from app.models import DiaSemana

    bloques = [_Bloque(DiaSemana.MIERCOLES, time(8, 0), time(12, 0), disponible=False)]

    with pytest.raises(DoctorNoDisponibleError):
        _horario_doctor(bloques).validar(_ctx())


def test_un_bloque_de_otro_dia_no_sirve():
    from app.exceptions import DoctorNoDisponibleError
    from app.models import DiaSemana

    bloques = [_Bloque(DiaSemana.LUNES, time(8, 0), time(12, 0))]

    with pytest.raises(DoctorNoDisponibleError):
        _horario_doctor(bloques).validar(_ctx(fecha_hora=MANANA_9))


# --- 6 y 7. Choques -------------------------------------------------------

def test_sin_choque_de_doctor_pasa_y_con_choque_no():
    from app.exceptions import ChoqueDeCitaError
    from app.services.validadores_cita import SinChoqueDeDoctor

    SinChoqueDeDoctor(_Citas(choca_doctor=False)).validar(_ctx())

    with pytest.raises(ChoqueDeCitaError):
        SinChoqueDeDoctor(_Citas(choca_doctor=True)).validar(_ctx())


def test_el_choque_de_doctor_propaga_excluir_id_cita():
    """Sin esto, al reagendar la cita chocaria contra si misma."""
    from app.services.validadores_cita import SinChoqueDeDoctor

    citas = _Citas()
    SinChoqueDeDoctor(citas).validar(_ctx(excluir_id_cita=77))

    assert citas.ultima_exclusion == 77


def test_el_choque_de_consultorio_se_saltea_si_no_hay_consultorio():
    from app.services.validadores_cita import SinChoqueDeConsultorio

    validador = SinChoqueDeConsultorio(_Citas(choca_consultorio=True))

    validador.validar(_ctx(id_consultorio=None))  # no debe lanzar


def test_el_choque_de_consultorio_se_detecta_cuando_hay_consultorio():
    from app.exceptions import ChoqueDeCitaError
    from app.services.validadores_cita import SinChoqueDeConsultorio

    with pytest.raises(ChoqueDeCitaError):
        SinChoqueDeConsultorio(_Citas(choca_consultorio=True)).validar(
            _ctx(id_consultorio=5)
        )


# --- La lista por defecto -------------------------------------------------

def test_validadores_por_defecto_devuelve_los_siete_en_orden(db_session):
    from app.services.validadores_cita import (
        AnticipacionMinima,
        DentroDelHorarioDeLaClinica,
        DentroDelHorarioDelDoctor,
        NoEnElPasado,
        ReferenciasDeLaMismaClinica,
        SinChoqueDeConsultorio,
        SinChoqueDeDoctor,
        validadores_por_defecto,
    )

    tipos = [type(v) for v in validadores_por_defecto(db_session)]

    assert tipos == [
        ReferenciasDeLaMismaClinica,
        NoEnElPasado,
        AnticipacionMinima,
        DentroDelHorarioDeLaClinica,
        DentroDelHorarioDelDoctor,
        SinChoqueDeDoctor,
        SinChoqueDeConsultorio,
    ]
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_validadores_cita.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.validadores_cita'`

- [ ] **Step 3: Agregar las excepciones de dominio**

Modificar `backend/app/exceptions.py` — agregar al final:

```python
class ReferenciaInvalidaError(Exception):
    """Una FK apunta a algo que no existe, esta inactivo, o es de otra clinica."""


class CitaEnElPasadoError(Exception):
    """La fecha y hora de la cita ya paso."""


class AnticipacionInsuficienteError(Exception):
    """No se respeta la anticipacion minima configurada por la clinica."""


class FueraDeHorarioClinicaError(Exception):
    """La cita no cae dentro del horario de atencion de la clinica."""


class DoctorNoDisponibleError(Exception):
    """El doctor no tiene un bloque disponible que cubra ese horario."""


class ChoqueDeCitaError(Exception):
    """Ya hay una cita solapada para ese doctor o ese consultorio."""


class TransicionInvalidaError(Exception):
    """El estado actual de la cita no admite esa transicion."""
```

- [ ] **Step 4: Escribir los validadores**

Crear `backend/app/services/validadores_cita.py`:

```python
"""Las reglas de agendamiento, una clase por regla.

Cada validador es un objeto chico e independiente con la misma interfaz. Se
testean de a uno, sin base de datos ni servicio alrededor. Agregar una regla es
un archivo nuevo (o una clase mas aca) y un renglon en validadores_por_defecto:
no hay que volver a abrir CitaService. Esto es OCP, y es el mismo criterio con
el que el Modulo 3 justifico MetodoPago como tabla en vez de columnas booleanas.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from sqlalchemy.orm import Session

from app.exceptions import (
    AnticipacionInsuficienteError,
    ChoqueDeCitaError,
    CitaEnElPasadoError,
    DoctorNoDisponibleError,
    FueraDeHorarioClinicaError,
    ReferenciaInvalidaError,
)
from app.models import HORARIO_POR_DEFECTO, DiaSemana

#: datetime.weekday() devuelve 0 para lunes y 6 para domingo, que es exactamente
#: el orden de declaracion de DiaSemana.
_DIA_POR_INDICE = list(DiaSemana)


@dataclass(frozen=True)
class ContextoCita:
    """Todo lo que los validadores necesitan saber, en un solo objeto inmutable.

    excluir_id_cita es lo que hace que los mismos validadores sirvan para crear
    y para reagendar: al reagendar se excluye la propia cita del chequeo de
    solapamiento, si no chocaria contra si misma.
    """

    id_clinica: int
    id_paciente: int
    id_doctor: int
    id_consultorio: int | None
    fecha_hora: datetime
    duracion_minutos: int
    configuracion: object
    ahora: datetime
    excluir_id_cita: int | None = None

    @property
    def fin(self) -> datetime:
        return self.fecha_hora + timedelta(minutes=self.duracion_minutos)

    @property
    def dia_semana(self) -> DiaSemana:
        return _DIA_POR_INDICE[self.fecha_hora.weekday()]

    @property
    def cruza_medianoche(self) -> bool:
        return self.fin.date() != self.fecha_hora.date()


class ValidadorDeCita(Protocol):
    def validar(self, ctx: ContextoCita) -> None:
        """Lanza una excepcion de dominio si la cita no es valida."""
        ...


class ReferenciasDeLaMismaClinica:
    """1. Paciente, doctor y consultorio existen, estan activos y son de esta clinica."""

    def __init__(self, pacientes, doctores, consultorios):
        self.pacientes = pacientes
        self.doctores = doctores
        self.consultorios = consultorios

    def validar(self, ctx: ContextoCita) -> None:
        paciente = self.pacientes.obtener(ctx.id_clinica, ctx.id_paciente)
        if paciente is None or not paciente.activo:
            raise ReferenciaInvalidaError("El paciente no existe en esta clinica")

        doctor = self.doctores.obtener(ctx.id_clinica, ctx.id_doctor)
        if doctor is None or not doctor.activo:
            raise ReferenciaInvalidaError("El doctor no existe en esta clinica")

        if ctx.id_consultorio is not None:
            consultorio = self.consultorios.obtener(ctx.id_clinica, ctx.id_consultorio)
            if consultorio is None or not consultorio.activo:
                raise ReferenciaInvalidaError(
                    "El consultorio no existe en esta clinica"
                )


class NoEnElPasado:
    """2. La cita no puede quedar en el pasado ni exactamente ahora."""

    def validar(self, ctx: ContextoCita) -> None:
        if ctx.fecha_hora <= ctx.ahora:
            raise CitaEnElPasadoError("No se puede agendar una cita en el pasado")


class AnticipacionMinima:
    """3. Se respeta la anticipacion minima que configuro la clinica."""

    def validar(self, ctx: ContextoCita) -> None:
        horas = ctx.configuracion.anticipacion_minima_reserva_horas
        if ctx.fecha_hora < ctx.ahora + timedelta(hours=horas):
            raise AnticipacionInsuficienteError(
                f"Hay que agendar con al menos {horas} horas de anticipacion"
            )


class DentroDelHorarioDeLaClinica:
    """4. Inicio y fin caen dentro del horario de atencion del dia."""

    def __init__(self, horarios_clinica):
        self.horarios_clinica = horarios_clinica

    def validar(self, ctx: ContextoCita) -> None:
        filas = {
            fila.dia_semana: fila
            for fila in self.horarios_clinica.listar_semana(ctx.id_clinica)
        }
        fila = filas.get(ctx.dia_semana)
        if fila is None:
            # Mismo relleno con defaults que hace GET /horarios del Modulo 3.
            defecto = HORARIO_POR_DEFECTO[ctx.dia_semana]
            cerrado = defecto["cerrado"]
            apertura = defecto["hora_apertura"]
            cierre = defecto["hora_cierre"]
        else:
            cerrado, apertura, cierre = fila.cerrado, fila.hora_apertura, fila.hora_cierre

        if cerrado or apertura is None or cierre is None:
            raise FueraDeHorarioClinicaError(
                f"La clinica no atiende los {ctx.dia_semana.value}"
            )

        if ctx.cruza_medianoche or ctx.fecha_hora.time() < apertura or ctx.fin.time() > cierre:
            raise FueraDeHorarioClinicaError(
                f"El horario de atencion del {ctx.dia_semana.value} es de "
                f"{apertura} a {cierre}"
            )


class DentroDelHorarioDelDoctor:
    """5. La cita cae entera dentro de UN MISMO bloque disponible del doctor.

    Un doctor sin ningun bloque cargado se considera no disponible. La
    alternativa (sin bloques = disponible en todo el horario de la clinica) es
    mas comoda pero silenciosa: nadie se entera de que falta configurar algo.
    """

    def __init__(self, horarios_doctor):
        self.horarios_doctor = horarios_doctor

    def validar(self, ctx: ContextoCita) -> None:
        bloques = [
            bloque
            for bloque in self.horarios_doctor.listar_de_doctor(
                ctx.id_clinica, ctx.id_doctor
            )
            if bloque.dia_semana == ctx.dia_semana and bloque.disponible
        ]
        inicio, fin = ctx.fecha_hora.time(), ctx.fin.time()
        entra = not ctx.cruza_medianoche and any(
            bloque.hora_inicio <= inicio and fin <= bloque.hora_fin for bloque in bloques
        )
        if not entra:
            raise DoctorNoDisponibleError(
                "El doctor no atiende en ese horario"
            )


class SinChoqueDeDoctor:
    """6. El doctor no tiene otra cita activa solapada."""

    def __init__(self, citas):
        self.citas = citas

    def validar(self, ctx: ContextoCita) -> None:
        if self.citas.hay_solapamiento_de_doctor(
            ctx.id_clinica,
            ctx.id_doctor,
            ctx.fecha_hora,
            ctx.fin,
            excluir_id_cita=ctx.excluir_id_cita,
        ):
            raise ChoqueDeCitaError("El doctor ya tiene una cita en ese horario")


class SinChoqueDeConsultorio:
    """7. El consultorio no esta ocupado. Se saltea si la cita no lleva sala."""

    def __init__(self, citas):
        self.citas = citas

    def validar(self, ctx: ContextoCita) -> None:
        if ctx.id_consultorio is None:
            return
        if self.citas.hay_solapamiento_de_consultorio(
            ctx.id_clinica,
            ctx.id_consultorio,
            ctx.fecha_hora,
            ctx.fin,
            excluir_id_cita=ctx.excluir_id_cita,
        ):
            raise ChoqueDeCitaError("El consultorio ya esta ocupado en ese horario")


def validadores_por_defecto(db: Session) -> list[ValidadorDeCita]:
    """El orden importa: se corta en el primero que falla, y no tiene sentido
    chequear solapamientos si el paciente ni siquiera existe.
    """
    from app.repositories.cita_repository import CitaRepository
    from app.repositories.consultorio_repository import ConsultorioRepository
    from app.repositories.doctor_repository import DoctorRepository
    from app.repositories.horario_clinica_repository import HorarioClinicaRepository
    from app.repositories.horario_doctor_repository import HorarioDoctorRepository
    from app.repositories.paciente_repository import PacienteRepository

    citas = CitaRepository(db)
    return [
        ReferenciasDeLaMismaClinica(
            PacienteRepository(db), DoctorRepository(db), ConsultorioRepository(db)
        ),
        NoEnElPasado(),
        AnticipacionMinima(),
        DentroDelHorarioDeLaClinica(HorarioClinicaRepository(db)),
        DentroDelHorarioDelDoctor(HorarioDoctorRepository(db)),
        SinChoqueDeDoctor(citas),
        SinChoqueDeConsultorio(citas),
    ]
```

- [ ] **Step 5: Correr los tests y verificar que pasan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_validadores_cita.py -v`
Expected: PASS — 22 passed

- [ ] **Step 6: Punto de commit (lo ejecuta Meli)**

```bash
git add backend/app/exceptions.py backend/app/services/validadores_cita.py \
        backend/tests/test_validadores_cita.py
git commit -m "feat(backend): validadores independientes de agendamiento de citas"
```

---

## Task 8: `CitaService`

**Files:**
- Create: `backend/app/services/cita_service.py`
- Test: `backend/tests/test_cita_service.py`

**Interfaces:**
- Consumes: `CitaRepository` (Task 6), `ConfiguracionClinicaRepository` (Módulo 3), validadores
  (Task 7), `TRANSICIONES_PERMITIDAS` y `EstadoCita` (Task 1).
- Produces: `CitaService(db, validadores=None)` con:
  - `crear(id_clinica: int, datos: dict, id_asistente: int | None = None, ahora: datetime | None = None) -> Cita`
  - `cambiar_estado(id_clinica: int, id_cita: int, nuevo: EstadoCita) -> Cita | None`
  - `cancelar(id_clinica: int, id_cita: int, ahora: datetime | None = None) -> Cita | None`
  - `reagendar(id_clinica: int, id_cita: int, fecha_hora: datetime, id_consultorio: int | None = None, ahora: datetime | None = None) -> Cita | None`

  Los cuatro devuelven `None` si la cita no existe en esa clínica. `ahora` es inyectable para que
  los tests sean deterministas; en producción se omite y usa `datetime.now()`.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `backend/tests/test_cita_service.py`:

```python
from datetime import datetime, timedelta

import pytest

from tests.factories import crear_cita, crear_clinica, crear_doctor, crear_paciente

AHORA = datetime(2026, 9, 1, 8, 0)  # martes
EN_UNA_SEMANA = datetime(2026, 9, 8, 9, 0)  # martes siguiente


class _ValidadorQueCuenta:
    def __init__(self, nombre, registro, explota=None):
        self.nombre = nombre
        self.registro = registro
        self.explota = explota

    def validar(self, ctx):
        self.registro.append(self.nombre)
        if self.explota is not None:
            raise self.explota


def _servicio(db_session, validadores=None):
    from app.services.cita_service import CitaService

    return CitaService(db_session, validadores=validadores if validadores is not None else [])


def _escenario(db_session):
    clinica = crear_clinica(db_session)
    paciente = crear_paciente(db_session, clinica.id_clinica)
    doctor = crear_doctor(db_session, clinica.id_clinica)
    return clinica.id_clinica, paciente.id_paciente, doctor.id_doctor


def _datos(id_paciente, id_doctor, **campos):
    base = {
        "id_paciente": id_paciente,
        "id_doctor": id_doctor,
        "fecha_hora": EN_UNA_SEMANA,
    }
    base.update(campos)
    return base


# --- crear ----------------------------------------------------------------

def test_crear_devuelve_una_cita_programada(db_session):
    from app.models import EstadoCita

    id_clinica, id_paciente, id_doctor = _escenario(db_session)

    cita = _servicio(db_session).crear(
        id_clinica, _datos(id_paciente, id_doctor), ahora=AHORA
    )

    assert cita.id_cita is not None
    assert cita.estado == EstadoCita.PROGRAMADA
    assert cita.veces_reagendada == 0


def test_la_duracion_sale_de_la_configuracion_cuando_no_viene(db_session):
    id_clinica, id_paciente, id_doctor = _escenario(db_session)

    cita = _servicio(db_session).crear(
        id_clinica, _datos(id_paciente, id_doctor), ahora=AHORA
    )

    assert cita.duracion_minutos == 30  # default de ConfiguracionClinica


def test_la_duracion_del_request_gana_sobre_la_configuracion(db_session):
    id_clinica, id_paciente, id_doctor = _escenario(db_session)

    cita = _servicio(db_session).crear(
        id_clinica,
        _datos(id_paciente, id_doctor, duracion_minutos=45),
        ahora=AHORA,
    )

    assert cita.duracion_minutos == 45


def test_el_asistente_se_toma_del_parametro_y_no_del_body(db_session):
    from tests.factories import crear_asistente

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    asistente = crear_asistente(db_session, id_clinica)

    cita = _servicio(db_session).crear(
        id_clinica,
        _datos(id_paciente, id_doctor),
        id_asistente=asistente.id_asistente,
        ahora=AHORA,
    )

    assert cita.id_asistente == asistente.id_asistente


def test_los_validadores_corren_en_orden(db_session):
    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    registro = []
    validadores = [
        _ValidadorQueCuenta("uno", registro),
        _ValidadorQueCuenta("dos", registro),
        _ValidadorQueCuenta("tres", registro),
    ]

    _servicio(db_session, validadores).crear(
        id_clinica, _datos(id_paciente, id_doctor), ahora=AHORA
    )

    assert registro == ["uno", "dos", "tres"]


def test_se_corta_en_el_primer_validador_que_falla(db_session):
    from app.exceptions import CitaEnElPasadoError

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    registro = []
    validadores = [
        _ValidadorQueCuenta("uno", registro),
        _ValidadorQueCuenta("dos", registro, explota=CitaEnElPasadoError()),
        _ValidadorQueCuenta("tres", registro),
    ]

    with pytest.raises(CitaEnElPasadoError):
        _servicio(db_session, validadores).crear(
            id_clinica, _datos(id_paciente, id_doctor), ahora=AHORA
        )

    assert registro == ["uno", "dos"]


def test_si_un_validador_falla_no_se_crea_ninguna_cita(db_session):
    from app.exceptions import ChoqueDeCitaError
    from app.repositories.cita_repository import CitaRepository

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    validadores = [_ValidadorQueCuenta("uno", [], explota=ChoqueDeCitaError())]

    with pytest.raises(ChoqueDeCitaError):
        _servicio(db_session, validadores).crear(
            id_clinica, _datos(id_paciente, id_doctor), ahora=AHORA
        )

    assert CitaRepository(db_session).listar(id_clinica) == []


# --- cambiar_estado -------------------------------------------------------

def test_cambiar_estado_permitido(db_session):
    from app.models import EstadoCita

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    cita = crear_cita(db_session, id_clinica, id_paciente, id_doctor)

    actualizada = _servicio(db_session).cambiar_estado(
        id_clinica, cita.id_cita, EstadoCita.CONFIRMADA
    )

    assert actualizada.estado == EstadoCita.CONFIRMADA


def test_no_se_puede_completar_una_cita_solo_programada(db_session):
    from app.exceptions import TransicionInvalidaError
    from app.models import EstadoCita

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    cita = crear_cita(db_session, id_clinica, id_paciente, id_doctor)

    with pytest.raises(TransicionInvalidaError):
        _servicio(db_session).cambiar_estado(
            id_clinica, cita.id_cita, EstadoCita.COMPLETADA
        )


def test_una_cita_cancelada_no_admite_mas_transiciones(db_session):
    from app.exceptions import TransicionInvalidaError
    from app.models import EstadoCita

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    cita = crear_cita(
        db_session, id_clinica, id_paciente, id_doctor, estado=EstadoCita.CANCELADA
    )

    with pytest.raises(TransicionInvalidaError):
        _servicio(db_session).cambiar_estado(
            id_clinica, cita.id_cita, EstadoCita.CONFIRMADA
        )


def test_cambiar_estado_de_una_cita_de_otra_clinica_devuelve_none(db_session):
    from app.models import EstadoCita

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    otra = crear_clinica(db_session, "Dental B")
    cita = crear_cita(db_session, id_clinica, id_paciente, id_doctor)

    assert _servicio(db_session).cambiar_estado(
        otra.id_clinica, cita.id_cita, EstadoCita.CONFIRMADA
    ) is None


# --- cancelar -------------------------------------------------------------

def test_cancelar_con_anticipacion_suficiente(db_session):
    from app.models import EstadoCita

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    cita = crear_cita(
        db_session, id_clinica, id_paciente, id_doctor, fecha_hora=EN_UNA_SEMANA
    )

    cancelada = _servicio(db_session).cancelar(id_clinica, cita.id_cita, ahora=AHORA)

    assert cancelada.estado == EstadoCita.CANCELADA


def test_cancelar_sobre_la_hora_no_se_puede(db_session):
    from app.exceptions import AnticipacionInsuficienteError

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    cita = crear_cita(
        db_session, id_clinica, id_paciente, id_doctor,
        fecha_hora=AHORA + timedelta(hours=2),
    )

    with pytest.raises(AnticipacionInsuficienteError):
        _servicio(db_session).cancelar(id_clinica, cita.id_cita, ahora=AHORA)


def test_no_se_puede_cancelar_una_cita_ya_completada(db_session):
    from app.exceptions import TransicionInvalidaError
    from app.models import EstadoCita

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    cita = crear_cita(
        db_session, id_clinica, id_paciente, id_doctor,
        fecha_hora=EN_UNA_SEMANA, estado=EstadoCita.COMPLETADA,
    )

    with pytest.raises(TransicionInvalidaError):
        _servicio(db_session).cancelar(id_clinica, cita.id_cita, ahora=AHORA)


# --- reagendar ------------------------------------------------------------

def test_reagendar_mueve_la_cita_incrementa_el_contador_y_baja_el_estado(db_session):
    from app.models import EstadoCita

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    cita = crear_cita(
        db_session, id_clinica, id_paciente, id_doctor,
        fecha_hora=EN_UNA_SEMANA, estado=EstadoCita.CONFIRMADA,
    )
    nueva_fecha = EN_UNA_SEMANA + timedelta(days=7)

    movida = _servicio(db_session).reagendar(
        id_clinica, cita.id_cita, nueva_fecha, ahora=AHORA
    )

    assert movida.id_cita == cita.id_cita  # es la misma fila, no una nueva
    assert movida.fecha_hora == nueva_fecha
    assert movida.veces_reagendada == 1
    assert movida.estado == EstadoCita.PROGRAMADA


def test_reagendar_sin_anticipacion_respecto_de_la_cita_vieja_no_se_puede(db_session):
    from app.exceptions import AnticipacionInsuficienteError

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    cita = crear_cita(
        db_session, id_clinica, id_paciente, id_doctor,
        fecha_hora=AHORA + timedelta(hours=2),
    )

    with pytest.raises(AnticipacionInsuficienteError):
        _servicio(db_session).reagendar(
            id_clinica, cita.id_cita, EN_UNA_SEMANA, ahora=AHORA
        )


def test_la_fecha_nueva_debe_respetar_los_dias_minimos_de_reagendamiento(db_session):
    from app.exceptions import AnticipacionInsuficienteError

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    cita = crear_cita(
        db_session, id_clinica, id_paciente, id_doctor, fecha_hora=EN_UNA_SEMANA
    )
    # El default es 3 dias; mananas es demasiado pronto.
    pasado_manana = AHORA + timedelta(days=2)

    with pytest.raises(AnticipacionInsuficienteError):
        _servicio(db_session).reagendar(
            id_clinica, cita.id_cita, pasado_manana, ahora=AHORA
        )


def test_no_se_puede_reagendar_una_cita_terminal(db_session):
    from app.exceptions import TransicionInvalidaError
    from app.models import EstadoCita

    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    cita = crear_cita(
        db_session, id_clinica, id_paciente, id_doctor,
        fecha_hora=EN_UNA_SEMANA, estado=EstadoCita.CANCELADA,
    )

    with pytest.raises(TransicionInvalidaError):
        _servicio(db_session).reagendar(
            id_clinica, cita.id_cita, EN_UNA_SEMANA + timedelta(days=7), ahora=AHORA
        )


def test_reagendar_pasa_excluir_id_cita_a_los_validadores(db_session):
    """Sin esto, la cita chocaria contra si misma al validar su horario nuevo."""
    id_clinica, id_paciente, id_doctor = _escenario(db_session)
    cita = crear_cita(
        db_session, id_clinica, id_paciente, id_doctor, fecha_hora=EN_UNA_SEMANA
    )
    vistos = []

    class _Espia:
        def validar(self, ctx):
            vistos.append(ctx.excluir_id_cita)

    _servicio(db_session, [_Espia()]).reagendar(
        id_clinica, cita.id_cita, EN_UNA_SEMANA + timedelta(days=7), ahora=AHORA
    )

    assert vistos == [cita.id_cita]
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_cita_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.cita_service'`

- [ ] **Step 3: Escribir el servicio**

Crear `backend/app/services/cita_service.py`:

```python
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.exceptions import AnticipacionInsuficienteError, TransicionInvalidaError
from app.models import TRANSICIONES_PERMITIDAS, Cita, EstadoCita
from app.repositories.cita_repository import CitaRepository
from app.repositories.configuracion_repository import ConfiguracionClinicaRepository
from app.services.validadores_cita import (
    ContextoCita,
    ValidadorDeCita,
    validadores_por_defecto,
)


class CitaService:
    """Toda la logica de agendamiento. Ninguna ruta valida una cita por su cuenta.

    Los validadores se inyectan para poder testear la orquestacion sin depender
    de las siete reglas reales.
    """

    def __init__(self, db: Session, validadores: list[ValidadorDeCita] | None = None):
        self.db = db
        self.citas = CitaRepository(db)
        self.configuraciones = ConfiguracionClinicaRepository(db)
        self.validadores = (
            validadores if validadores is not None else validadores_por_defecto(db)
        )

    @staticmethod
    def _ahora(ahora: datetime | None) -> datetime:
        """Inyectable para que los tests sean deterministas."""
        return ahora if ahora is not None else datetime.now()

    def _validar(self, ctx: ContextoCita) -> None:
        """Corre los validadores en orden y corta en el primero que falla: el
        mensaje util es el de la primera regla violada, no una lista de siete.
        """
        for validador in self.validadores:
            validador.validar(ctx)

    def crear(
        self,
        id_clinica: int,
        datos: dict,
        id_asistente: int | None = None,
        ahora: datetime | None = None,
    ) -> Cita:
        configuracion = self.configuraciones.obtener_o_crear(id_clinica)
        pedida = datos.get("duracion_minutos")
        duracion = pedida if pedida is not None else configuracion.duracion_cita_minutos

        ctx = ContextoCita(
            id_clinica=id_clinica,
            id_paciente=datos["id_paciente"],
            id_doctor=datos["id_doctor"],
            id_consultorio=datos.get("id_consultorio"),
            fecha_hora=datos["fecha_hora"],
            duracion_minutos=duracion,
            configuracion=configuracion,
            ahora=self._ahora(ahora),
        )
        self._validar(ctx)

        return self.citas.crear(
            id_clinica,
            {
                "id_paciente": ctx.id_paciente,
                "id_doctor": ctx.id_doctor,
                "id_consultorio": ctx.id_consultorio,
                "id_asistente": id_asistente,
                "fecha_hora": ctx.fecha_hora,
                "duracion_minutos": duracion,
                "motivo": datos.get("motivo"),
            },
        )

    @staticmethod
    def _exigir_transicion(actual: EstadoCita, nuevo: EstadoCita) -> None:
        if nuevo not in TRANSICIONES_PERMITIDAS[actual]:
            raise TransicionInvalidaError(
                f"Una cita en estado '{actual.value}' no puede pasar a '{nuevo.value}'"
            )

    def cambiar_estado(
        self,
        id_clinica: int,
        id_cita: int,
        nuevo: EstadoCita,
        ahora: datetime | None = None,
    ) -> Cita | None:
        """Cancelar NO se atiende aca, se delega en cancelar().

        La tabla de transiciones permite pasar a 'cancelada', pero cancelar
        tiene ademas una regla propia (horas_minimas_cambio_cita) que este
        metodo no conoce. Si no se delegara, cualquiera podria cancelar sobre
        la hora pidiendo el cambio de estado por esta via y la regla quedaria
        decorativa.
        """
        if nuevo is EstadoCita.CANCELADA:
            return self.cancelar(id_clinica, id_cita, ahora=ahora)

        cita = self.citas.obtener(id_clinica, id_cita)
        if cita is None:
            return None
        self._exigir_transicion(cita.estado, nuevo)
        cita.estado = nuevo
        self.db.flush()
        return cita

    def _exigir_anticipacion_de_cambio(
        self, cita: Cita, configuracion, ahora: datetime
    ) -> None:
        """Mide con cuanta anticipacion avisas, respecto de la cita VIGENTE."""
        horas = configuracion.horas_minimas_cambio_cita
        if cita.fecha_hora - ahora < timedelta(hours=horas):
            raise AnticipacionInsuficienteError(
                f"Hay que avisar con al menos {horas} horas de anticipacion"
            )

    def cancelar(
        self, id_clinica: int, id_cita: int, ahora: datetime | None = None
    ) -> Cita | None:
        cita = self.citas.obtener(id_clinica, id_cita)
        if cita is None:
            return None

        self._exigir_transicion(cita.estado, EstadoCita.CANCELADA)
        configuracion = self.configuraciones.obtener_o_crear(id_clinica)
        self._exigir_anticipacion_de_cambio(cita, configuracion, self._ahora(ahora))

        cita.estado = EstadoCita.CANCELADA
        self.db.flush()
        return cita

    def reagendar(
        self,
        id_clinica: int,
        id_cita: int,
        fecha_hora: datetime,
        id_consultorio: int | None = None,
        ahora: datetime | None = None,
    ) -> Cita | None:
        """Mueve la cita en su lugar. No cancela ni crea otra: una cita del mundo
        real que se corre de dia sigue siendo la misma cita.
        """
        cita = self.citas.obtener(id_clinica, id_cita)
        if cita is None:
            return None

        # Terminalidad derivada de la tabla, que la expresa como conjunto
        # vacio. NO se usa ESTADOS_ACTIVOS: esa constante es para detectar
        # choques de agenda, y que hoy coincida con "no terminal" es
        # accidental — si manana no_asistio pasara a ocupar el slot para las
        # metricas del Modulo 7, se volveria reagendable una cita a la que el
        # paciente no vino.
        if not TRANSICIONES_PERMITIDAS[cita.estado]:
            raise TransicionInvalidaError(
                f"Una cita en estado '{cita.estado.value}' no se puede reagendar"
            )

        momento = self._ahora(ahora)
        configuracion = self.configuraciones.obtener_o_crear(id_clinica)

        # Regla 1: anticipacion respecto de la cita vieja (cuando avisas).
        self._exigir_anticipacion_de_cambio(cita, configuracion, momento)

        # Regla 2: distancia respecto de la cita nueva (para cuando la moves).
        # Son dos reglas distintas, con unidades distintas, tal como las
        # justifico el Modulo 3.
        dias = configuracion.dias_minimos_reagendamiento
        if fecha_hora - momento < timedelta(days=dias):
            raise AnticipacionInsuficienteError(
                f"La cita nueva debe quedar a {dias} dias o mas de hoy"
            )

        # Regla 3: las siete validaciones de siempre, contra la fecha nueva y
        # excluyendo esta cita del chequeo de solapamiento.
        ctx = ContextoCita(
            id_clinica=id_clinica,
            id_paciente=cita.id_paciente,
            id_doctor=cita.id_doctor,
            id_consultorio=(
                id_consultorio if id_consultorio is not None else cita.id_consultorio
            ),
            fecha_hora=fecha_hora,
            duracion_minutos=cita.duracion_minutos,
            configuracion=configuracion,
            ahora=momento,
            excluir_id_cita=cita.id_cita,
        )
        self._validar(ctx)

        cita.fecha_hora = fecha_hora
        cita.id_consultorio = ctx.id_consultorio
        cita.veces_reagendada += 1
        # La confirmacion era para la hora vieja: mantenerla afirmaria algo que
        # nadie confirmo.
        cita.estado = EstadoCita.PROGRAMADA
        self.db.flush()
        return cita
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_cita_service.py -v`
Expected: PASS — 19 passed

- [ ] **Step 5: Correr la suite completa**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: todo verde.

- [ ] **Step 6: Punto de commit (lo ejecuta Meli)**

```bash
git add backend/app/services/cita_service.py backend/tests/test_cita_service.py
git commit -m "feat(backend): CitaService con maquina de estados y reglas de cambio"
```

---

## Task 9: `PersonalService`

**Files:**
- Create: `backend/app/services/personal_service.py`
- Test: `backend/tests/test_personal_service.py`

**Interfaces:**
- Consumes: `DoctorRepository` y `AsistenteRepository` (Task 4), `UsuarioRepository` y
  `EspecialidadRepository` (Módulos 1 y 3), `generar_password_temporal` y `hash_password`
  (Módulo 1), `UsernameYaExisteError` (Módulo 1), `ReferenciaInvalidaError` (Task 7).
- Produces: `PersonalService(db)` con:
  - `crear_doctor(id_clinica: int, datos: dict) -> dict` — el dict tiene las claves `perfil`
    (`Doctor`) y `password_temporal` (`str`).
  - `crear_asistente(id_clinica: int, datos: dict) -> dict` — ídem con un `Asistente`.
  - `dar_de_baja_doctor(id_clinica: int, id_doctor: int) -> bool`
  - `dar_de_baja_asistente(id_clinica: int, id_asistente: int) -> bool`

  `datos` lleva `username`, `nombre`, `apellido`, `telefono`, y opcionalmente `correo` y (solo
  doctor) `id_especialidad`.

> Copia el patrón de `ClinicaService.crear_clinica_con_admin` del Módulo 2: `try` / `except` con
> `db.rollback()` explícito. Es el **único** servicio de este módulo que hace `commit()`, porque es
> el único que coordina varias escrituras que deben ser atómicas.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `backend/tests/test_personal_service.py`:

```python
import pytest

from tests.factories import crear_clinica


def _servicio(db_session):
    from app.services.personal_service import PersonalService

    return PersonalService(db_session)


def _datos(**campos):
    base = {
        "username": "dra.perez",
        "nombre": "Marta",
        "apellido": "Perez",
        "telefono": "70003344",
    }
    base.update(campos)
    return base


def test_crear_doctor_crea_usuario_y_perfil_juntos(db_session):
    from app.models import RolUsuario
    from app.repositories.usuario_repository import UsuarioRepository

    clinica = crear_clinica(db_session)

    resultado = _servicio(db_session).crear_doctor(clinica.id_clinica, _datos())

    perfil = resultado["perfil"]
    assert perfil.id_doctor is not None
    usuario = UsuarioRepository(db_session).obtener_por_username("dra.perez")
    assert usuario is not None
    assert usuario.rol == RolUsuario.DOCTOR
    assert usuario.id_clinica == clinica.id_clinica
    assert perfil.id_usuario == usuario.id_usuario


def test_crear_doctor_devuelve_una_password_temporal_usable(db_session):
    from app.repositories.usuario_repository import UsuarioRepository
    from app.security.passwords import verify_password

    clinica = crear_clinica(db_session)

    resultado = _servicio(db_session).crear_doctor(clinica.id_clinica, _datos())

    temporal = resultado["password_temporal"]
    assert isinstance(temporal, str) and len(temporal) >= 12
    usuario = UsuarioRepository(db_session).obtener_por_username("dra.perez")
    assert verify_password(temporal, usuario.password_hash)


def test_el_usuario_nuevo_debe_cambiar_la_password(db_session):
    from app.repositories.usuario_repository import UsuarioRepository

    clinica = crear_clinica(db_session)
    _servicio(db_session).crear_doctor(clinica.id_clinica, _datos())

    usuario = UsuarioRepository(db_session).obtener_por_username("dra.perez")
    assert usuario.debe_cambiar_password is True


def test_la_password_temporal_nunca_se_guarda_en_claro(db_session):
    from app.repositories.usuario_repository import UsuarioRepository

    clinica = crear_clinica(db_session)

    resultado = _servicio(db_session).crear_doctor(clinica.id_clinica, _datos())

    usuario = UsuarioRepository(db_session).obtener_por_username("dra.perez")
    assert usuario.password_hash != resultado["password_temporal"]


def test_username_repetido_lanza_error(db_session):
    from app.exceptions import UsernameYaExisteError

    clinica = crear_clinica(db_session)
    servicio = _servicio(db_session)
    servicio.crear_doctor(clinica.id_clinica, _datos())

    with pytest.raises(UsernameYaExisteError):
        servicio.crear_doctor(clinica.id_clinica, _datos(nombre="Otra"))


def test_una_especialidad_de_otra_clinica_es_referencia_invalida(db_session):
    from app.exceptions import ReferenciaInvalidaError
    from app.repositories.especialidad_repository import EspecialidadRepository

    clinica_a = crear_clinica(db_session, "Dental A")
    clinica_b = crear_clinica(db_session, "Dental B")
    de_b = EspecialidadRepository(db_session).crear(
        clinica_b.id_clinica, {"nombre": "Ortodoncia"}
    )

    with pytest.raises(ReferenciaInvalidaError):
        _servicio(db_session).crear_doctor(
            clinica_a.id_clinica, _datos(id_especialidad=de_b.id_especialidad)
        )


def test_si_el_perfil_falla_no_queda_el_usuario_huerfano(db_session, monkeypatch):
    """El test mas importante de esta task: la transaccion es real."""
    from app.repositories.usuario_repository import UsuarioRepository

    clinica = crear_clinica(db_session)
    servicio = _servicio(db_session)

    def _explotar(*args, **kwargs):
        raise RuntimeError("fallo al crear el perfil")

    monkeypatch.setattr(servicio.doctores, "crear", _explotar)

    with pytest.raises(RuntimeError):
        servicio.crear_doctor(clinica.id_clinica, _datos())

    assert UsuarioRepository(db_session).obtener_por_username("dra.perez") is None


def test_crear_asistente_funciona_igual_con_rol_asistente(db_session):
    from app.models import RolUsuario
    from app.repositories.usuario_repository import UsuarioRepository

    clinica = crear_clinica(db_session)

    resultado = _servicio(db_session).crear_asistente(
        clinica.id_clinica,
        {
            "username": "recepcion",
            "nombre": "Rosa",
            "apellido": "Diaz",
            "telefono": "70005566",
        },
    )

    assert resultado["perfil"].id_asistente is not None
    usuario = UsuarioRepository(db_session).obtener_por_username("recepcion")
    assert usuario.rol == RolUsuario.ASISTENTE


def test_dar_de_baja_desactiva_perfil_y_usuario(db_session):
    from app.repositories.usuario_repository import UsuarioRepository

    clinica = crear_clinica(db_session)
    servicio = _servicio(db_session)
    perfil = servicio.crear_doctor(clinica.id_clinica, _datos())["perfil"]

    assert servicio.dar_de_baja_doctor(clinica.id_clinica, perfil.id_doctor) is True

    assert perfil.activo is False
    usuario = UsuarioRepository(db_session).obtener_por_username("dra.perez")
    assert usuario.activo is False


def test_dar_de_baja_un_doctor_de_otra_clinica_devuelve_false(db_session):
    clinica_a = crear_clinica(db_session, "Dental A")
    clinica_b = crear_clinica(db_session, "Dental B")
    servicio = _servicio(db_session)
    perfil = servicio.crear_doctor(clinica_a.id_clinica, _datos())["perfil"]

    assert servicio.dar_de_baja_doctor(clinica_b.id_clinica, perfil.id_doctor) is False
    assert perfil.activo is True
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_personal_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.personal_service'`

- [ ] **Step 3: Escribir el servicio**

Crear `backend/app/services/personal_service.py`:

```python
from sqlalchemy.orm import Session

from app.exceptions import ReferenciaInvalidaError, UsernameYaExisteError
from app.models import RolUsuario, Usuario
from app.repositories.asistente_repository import AsistenteRepository
from app.repositories.doctor_repository import DoctorRepository
from app.repositories.especialidad_repository import EspecialidadRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.security.passwords import generar_password_temporal, hash_password


class PersonalService:
    """Alta y baja del personal de la clinica.

    Crea el Usuario y el perfil en UNA transaccion, con rollback explicito,
    copiando el patron de ClinicaService.crear_clinica_con_admin (Modulo 2). La
    alternativa (exigir que el Usuario exista de antes) obliga a un flujo de dos
    pasos que puede dejar usuarios huerfanos si el segundo falla.
    """

    def __init__(self, db: Session):
        self.db = db
        self.usuarios = UsuarioRepository(db)
        self.doctores = DoctorRepository(db)
        self.asistentes = AsistenteRepository(db)
        self.especialidades = EspecialidadRepository(db)

    def _crear_usuario(self, id_clinica: int, username: str, rol: RolUsuario) -> tuple:
        password_temporal = generar_password_temporal()
        usuario = Usuario(
            id_clinica=id_clinica,
            username=username,
            password_hash=hash_password(password_temporal),
            rol=rol,
            debe_cambiar_password=True,
        )
        self.db.add(usuario)
        self.db.flush()
        return usuario, password_temporal

    def crear_doctor(self, id_clinica: int, datos: dict) -> dict:
        campos = dict(datos)
        username = campos.pop("username")

        if self.usuarios.obtener_por_username(username) is not None:
            raise UsernameYaExisteError()

        id_especialidad = campos.get("id_especialidad")
        if id_especialidad is not None:
            especialidad = self.especialidades.obtener(id_clinica, id_especialidad)
            if especialidad is None or not especialidad.activo:
                raise ReferenciaInvalidaError(
                    "La especialidad no existe en esta clinica"
                )

        try:
            usuario, password_temporal = self._crear_usuario(
                id_clinica, username, RolUsuario.DOCTOR
            )
            perfil = self.doctores.crear(
                id_clinica, {"id_usuario": usuario.id_usuario, **campos}
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return {"perfil": perfil, "password_temporal": password_temporal}

    def crear_asistente(self, id_clinica: int, datos: dict) -> dict:
        campos = dict(datos)
        username = campos.pop("username")

        if self.usuarios.obtener_por_username(username) is not None:
            raise UsernameYaExisteError()

        try:
            usuario, password_temporal = self._crear_usuario(
                id_clinica, username, RolUsuario.ASISTENTE
            )
            perfil = self.asistentes.crear(
                id_clinica, {"id_usuario": usuario.id_usuario, **campos}
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return {"perfil": perfil, "password_temporal": password_temporal}

    def _dar_de_baja(self, repositorio, id_clinica: int, id_perfil: int) -> bool:
        """Desactiva perfil y Usuario juntos: un profesional dado de baja no debe
        poder seguir entrando al sistema.
        """
        perfil = repositorio.obtener(id_clinica, id_perfil)
        if perfil is None:
            return False
        try:
            # El borrado logico del perfil lo hace el repositorio; aca solo se
            # coordina la transaccion con la baja del Usuario.
            repositorio.eliminar(id_clinica, id_perfil)
            usuario = self.usuarios.obtener_por_id(perfil.id_usuario)
            if usuario is None:
                # Inalcanzable mientras la FK sea NOT NULL, pero si alguna vez
                # pasara no se puede devolver True: el profesional seguiria
                # pudiendo entrar al sistema.
                raise ReferenciaInvalidaError(
                    "El perfil no tiene un usuario asociado"
                )
            usuario.activo = False
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return True

    def dar_de_baja_doctor(self, id_clinica: int, id_doctor: int) -> bool:
        return self._dar_de_baja(self.doctores, id_clinica, id_doctor)

    def dar_de_baja_asistente(self, id_clinica: int, id_asistente: int) -> bool:
        return self._dar_de_baja(self.asistentes, id_clinica, id_asistente)
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_personal_service.py -v`
Expected: PASS — 10 passed

- [ ] **Step 5: Punto de commit (lo ejecuta Meli)**

```bash
git add backend/app/services/personal_service.py backend/tests/test_personal_service.py
git commit -m "feat(backend): PersonalService con alta transaccional de usuario y perfil"
```

---

## Task 10: Schemas

**Files:**
- Create: `backend/app/schemas/personas.py`
- Create: `backend/app/schemas/cita.py`
- Modify: `backend/app/schemas/parametros.py`
- Test: `backend/tests/test_schemas_modulo4.py`

**Interfaces:**
- Consumes: `DiaSemana` (Módulo 3), `EstadoCita` (Task 1).
- Produces:
  - `personas.py`: `PacienteCreate`, `PacienteUpdate`, `PacienteResponse` (con `edad: int | None`
    calculada), `DoctorCreate`, `DoctorUpdate`, `DoctorResponse`, `DoctorCreateResponse`,
    `AsistenteCreate`, `AsistenteUpdate`, `AsistenteResponse`, `AsistenteCreateResponse`,
    `BloqueHorarioSchema`, `HorarioDoctorRequest`.
  - `cita.py`: `CitaCreate`, `CitaResponse`, `CambiarEstadoRequest`, `ReagendarRequest`.
  - `parametros.py`: `anticipacion_minima_reserva_horas` en `ConfiguracionResponse` y en
    `ConfiguracionUpdateRequest` (`ge=1, le=720`).

- [ ] **Step 1: Escribir los tests que fallan**

Crear `backend/tests/test_schemas_modulo4.py`:

```python
from datetime import date, datetime, time

import pytest
from pydantic import ValidationError


def test_el_nombre_se_recorta_y_no_puede_quedar_vacio():
    from app.schemas.personas import PacienteCreate

    creado = PacienteCreate(nombre="  Ana  ", apellido="Lopez", telefono="70001122")
    assert creado.nombre == "Ana"

    with pytest.raises(ValidationError):
        PacienteCreate(nombre="   ", apellido="Lopez", telefono="70001122")


def test_el_telefono_se_normaliza_quitando_espacios_y_guiones():
    from app.schemas.personas import PacienteCreate

    creado = PacienteCreate(nombre="Ana", apellido="Lopez", telefono="7000-1122")
    assert creado.telefono == "70001122"


def test_un_telefono_con_letras_es_invalido():
    from app.schemas.personas import PacienteCreate

    with pytest.raises(ValidationError):
        PacienteCreate(nombre="Ana", apellido="Lopez", telefono="7000abcd")


def test_un_telefono_demasiado_corto_es_invalido():
    from app.schemas.personas import PacienteCreate

    with pytest.raises(ValidationError):
        PacienteCreate(nombre="Ana", apellido="Lopez", telefono="7000")


def test_la_fecha_de_nacimiento_no_puede_ser_futura():
    from app.schemas.personas import PacienteCreate

    with pytest.raises(ValidationError):
        PacienteCreate(
            nombre="Ana",
            apellido="Lopez",
            telefono="70001122",
            fecha_nacimiento=date.today().replace(year=date.today().year + 1),
        )


def test_un_correo_mal_formado_es_invalido():
    from app.schemas.personas import PacienteCreate

    with pytest.raises(ValidationError):
        PacienteCreate(
            nombre="Ana", apellido="Lopez", telefono="70001122", correo="no-es-correo"
        )


def test_la_respuesta_del_paciente_calcula_la_edad():
    from app.schemas.personas import PacienteResponse

    class _Paciente:
        id_paciente = 1
        nombre = "Ana"
        apellido = "Lopez"
        fecha_nacimiento = date(2000, 1, 1)
        telefono = "70001122"
        correo = None
        direccion = None
        activo = True

    respuesta = PacienteResponse.model_validate(_Paciente())

    esperada = date.today().year - 2000 - (
        (date.today().month, date.today().day) < (1, 1)
    )
    assert respuesta.edad == esperada


def test_sin_fecha_de_nacimiento_la_edad_es_none():
    from app.schemas.personas import PacienteResponse

    class _Paciente:
        id_paciente = 1
        nombre = "Ana"
        apellido = "Lopez"
        fecha_nacimiento = None
        telefono = "70001122"
        correo = None
        direccion = None
        activo = True

    assert PacienteResponse.model_validate(_Paciente()).edad is None


def test_un_bloque_con_fin_menor_al_inicio_es_invalido():
    from app.models import DiaSemana
    from app.schemas.personas import BloqueHorarioSchema

    with pytest.raises(ValidationError):
        BloqueHorarioSchema(
            dia_semana=DiaSemana.LUNES, hora_inicio=time(12, 0), hora_fin=time(8, 0)
        )


def test_la_duracion_de_la_cita_respeta_el_rango():
    from app.schemas.cita import CitaCreate

    CitaCreate(
        id_paciente=1, id_doctor=1, fecha_hora=datetime(2026, 9, 1, 9, 0),
        duracion_minutos=30,
    )

    with pytest.raises(ValidationError):
        CitaCreate(
            id_paciente=1, id_doctor=1, fecha_hora=datetime(2026, 9, 1, 9, 0),
            duracion_minutos=4,
        )
    with pytest.raises(ValidationError):
        CitaCreate(
            id_paciente=1, id_doctor=1, fecha_hora=datetime(2026, 9, 1, 9, 0),
            duracion_minutos=481,
        )


def test_la_duracion_de_la_cita_es_opcional():
    from app.schemas.cita import CitaCreate

    creada = CitaCreate(
        id_paciente=1, id_doctor=1, fecha_hora=datetime(2026, 9, 1, 9, 0)
    )
    assert creada.duracion_minutos is None


def test_la_anticipacion_minima_no_puede_ser_cero():
    from app.schemas.parametros import ConfiguracionUpdateRequest

    ConfiguracionUpdateRequest(anticipacion_minima_reserva_horas=1)

    with pytest.raises(ValidationError):
        ConfiguracionUpdateRequest(anticipacion_minima_reserva_horas=0)
    with pytest.raises(ValidationError):
        ConfiguracionUpdateRequest(anticipacion_minima_reserva_horas=721)
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_schemas_modulo4.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.schemas.personas'`

- [ ] **Step 3: Escribir los schemas de personas**

Crear `backend/app/schemas/personas.py`:

```python
import re
from datetime import date, time

from pydantic import BaseModel, EmailStr, Field, computed_field, field_validator, model_validator

from app.models import DiaSemana

_SOLO_TELEFONO = re.compile(r"^[0-9+]{8,15}$")
_EDAD_MAXIMA = 120


def _texto_limpio(valor: str) -> str:
    limpio = valor.strip()
    if not limpio:
        raise ValueError("No puede estar vacio")
    return limpio


def _telefono_limpio(valor: str) -> str:
    """Normaliza antes de validar: '7000-1122' y '7000 1122' son el mismo numero."""
    limpio = valor.replace(" ", "").replace("-", "")
    if not _SOLO_TELEFONO.match(limpio):
        raise ValueError("El telefono debe tener entre 8 y 15 digitos")
    return limpio


def _fecha_de_nacimiento_valida(valor: date | None) -> date | None:
    if valor is None:
        return None
    hoy = date.today()
    if valor > hoy:
        raise ValueError("La fecha de nacimiento no puede ser futura")
    if valor.year < hoy.year - _EDAD_MAXIMA:
        raise ValueError(f"La fecha de nacimiento no puede ser de hace mas de {_EDAD_MAXIMA} anos")
    return valor


class _DatosDePersona(BaseModel):
    """Campos comunes a paciente, doctor y asistente en los requests de alta."""

    nombre: str = Field(min_length=1, max_length=50)
    apellido: str = Field(min_length=1, max_length=50)
    telefono: str
    correo: EmailStr | None = Field(default=None, max_length=100)

    @field_validator("nombre", "apellido")
    @classmethod
    def _validar_texto(cls, valor: str) -> str:
        return _texto_limpio(valor)

    @field_validator("telefono")
    @classmethod
    def _validar_telefono(cls, valor: str) -> str:
        return _telefono_limpio(valor)


class PacienteCreate(_DatosDePersona):
    fecha_nacimiento: date | None = None
    direccion: str | None = Field(default=None, max_length=200)

    @field_validator("fecha_nacimiento")
    @classmethod
    def _validar_fecha(cls, valor: date | None) -> date | None:
        return _fecha_de_nacimiento_valida(valor)


class PacienteUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=50)
    apellido: str | None = Field(default=None, min_length=1, max_length=50)
    telefono: str | None = None
    correo: EmailStr | None = Field(default=None, max_length=100)
    fecha_nacimiento: date | None = None
    direccion: str | None = Field(default=None, max_length=200)
    activo: bool | None = None

    @field_validator("nombre", "apellido")
    @classmethod
    def _validar_texto(cls, valor: str | None) -> str | None:
        return None if valor is None else _texto_limpio(valor)

    @field_validator("telefono")
    @classmethod
    def _validar_telefono(cls, valor: str | None) -> str | None:
        return None if valor is None else _telefono_limpio(valor)

    @field_validator("fecha_nacimiento")
    @classmethod
    def _validar_fecha(cls, valor: date | None) -> date | None:
        return _fecha_de_nacimiento_valida(valor)


class PacienteResponse(BaseModel):
    id_paciente: int
    nombre: str
    apellido: str
    fecha_nacimiento: date | None
    telefono: str
    correo: str | None
    direccion: str | None
    activo: bool

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def edad(self) -> int | None:
        """Derivada, nunca almacenada: guardarla la volveria mentira al dia
        siguiente del cumpleanos.
        """
        if self.fecha_nacimiento is None:
            return None
        hoy = date.today()
        return (
            hoy.year
            - self.fecha_nacimiento.year
            - ((hoy.month, hoy.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day))
        )


class DoctorCreate(_DatosDePersona):
    username: str = Field(min_length=3, max_length=30)
    id_especialidad: int | None = Field(default=None, gt=0)

    @field_validator("username")
    @classmethod
    def _validar_username(cls, valor: str) -> str:
        return _texto_limpio(valor)


class DoctorUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=50)
    apellido: str | None = Field(default=None, min_length=1, max_length=50)
    telefono: str | None = None
    correo: EmailStr | None = Field(default=None, max_length=100)
    id_especialidad: int | None = Field(default=None, gt=0)
    activo: bool | None = None

    @field_validator("nombre", "apellido")
    @classmethod
    def _validar_texto(cls, valor: str | None) -> str | None:
        return None if valor is None else _texto_limpio(valor)

    @field_validator("telefono")
    @classmethod
    def _validar_telefono(cls, valor: str | None) -> str | None:
        return None if valor is None else _telefono_limpio(valor)


class DoctorResponse(BaseModel):
    id_doctor: int
    id_usuario: int
    id_especialidad: int | None
    nombre: str
    apellido: str
    telefono: str
    correo: str | None
    activo: bool

    model_config = {"from_attributes": True}


class DoctorCreateResponse(BaseModel):
    """La password temporal se expone UNA sola vez, aca. Ningun GET la devuelve."""

    doctor: DoctorResponse
    password_temporal: str


class AsistenteCreate(_DatosDePersona):
    username: str = Field(min_length=3, max_length=30)

    @field_validator("username")
    @classmethod
    def _validar_username(cls, valor: str) -> str:
        return _texto_limpio(valor)


class AsistenteUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=50)
    apellido: str | None = Field(default=None, min_length=1, max_length=50)
    telefono: str | None = None
    correo: EmailStr | None = Field(default=None, max_length=100)
    activo: bool | None = None

    @field_validator("nombre", "apellido")
    @classmethod
    def _validar_texto(cls, valor: str | None) -> str | None:
        return None if valor is None else _texto_limpio(valor)

    @field_validator("telefono")
    @classmethod
    def _validar_telefono(cls, valor: str | None) -> str | None:
        return None if valor is None else _telefono_limpio(valor)


class AsistenteResponse(BaseModel):
    id_asistente: int
    id_usuario: int
    nombre: str
    apellido: str
    telefono: str
    correo: str | None
    activo: bool

    model_config = {"from_attributes": True}


class AsistenteCreateResponse(BaseModel):
    asistente: AsistenteResponse
    password_temporal: str


class BloqueHorarioSchema(BaseModel):
    dia_semana: DiaSemana
    hora_inicio: time
    hora_fin: time
    disponible: bool = True

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def _fin_posterior_al_inicio(self) -> "BloqueHorarioSchema":
        if self.hora_fin <= self.hora_inicio:
            raise ValueError("La hora de fin debe ser posterior a la de inicio")
        return self


class HorarioDoctorRequest(BaseModel):
    """Reemplaza el conjunto completo de bloques del doctor.

    Se edita y se valida como una unidad, por el mismo motivo que
    PUT /horarios del Modulo 3: asi no puede quedar en un estado intermedio
    (un bloque movido y el que le sigue no, solapandose).
    """

    bloques: list[BloqueHorarioSchema]
```

- [ ] **Step 4: Escribir los schemas de cita**

Crear `backend/app/schemas/cita.py`:

```python
from datetime import datetime

from pydantic import BaseModel, Field

from app.models import EstadoCita


class CitaCreate(BaseModel):
    """Las reglas de negocio (pasado, anticipacion, horario, choques) NO se
    validan aca: dependen de la configuracion de la clinica y de la base, y
    viven en los validadores. El schema solo valida la forma del request.

    id_asistente no esta en el body a proposito: sale del usuario autenticado.
    """

    id_paciente: int = Field(gt=0)
    id_doctor: int = Field(gt=0)
    id_consultorio: int | None = Field(default=None, gt=0)
    fecha_hora: datetime
    # El tope de 480 esta acoplado a DURACION_MAXIMA_MINUTOS de
    # cita_repository.py: el prefiltro de solapamiento asume que ninguna cita
    # dura mas que eso. Si se sube uno, hay que subir el otro.
    duracion_minutos: int | None = Field(default=None, ge=5, le=480)
    motivo: str | None = Field(default=None, max_length=255)


class CitaResponse(BaseModel):
    id_cita: int
    id_paciente: int
    id_doctor: int
    id_consultorio: int | None
    id_asistente: int | None
    fecha_hora: datetime
    duracion_minutos: int
    estado: EstadoCita
    motivo: str | None
    veces_reagendada: int

    model_config = {"from_attributes": True}


class CambiarEstadoRequest(BaseModel):
    estado: EstadoCita


class ReagendarRequest(BaseModel):
    fecha_hora: datetime
    id_consultorio: int | None = Field(default=None, gt=0)
```

- [ ] **Step 5: Agregar el campo nuevo a los schemas de configuración**

Modificar `backend/app/schemas/parametros.py`:

En `ConfiguracionResponse`, agregar después de `dias_minimos_reagendamiento`:

```python
    anticipacion_minima_reserva_horas: int
```

En `ConfiguracionUpdateRequest`, agregar después de `dias_minimos_reagendamiento`:

```python
    anticipacion_minima_reserva_horas: int | None = Field(default=None, ge=1, le=720)
```

- [ ] **Step 6: Correr los tests y verificar que pasan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_schemas_modulo4.py -v`
Expected: PASS — 13 passed

- [ ] **Step 7: Actualizar el test de configuración del Módulo 3**

Modificar `backend/tests/test_configuracion_routes.py` — agregar al final:

```python
def test_la_configuracion_incluye_la_anticipacion_minima_con_default_24(client, db_session):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")

    respuesta = client.get("/configuracion", headers=_auth(token))

    assert respuesta.status_code == 200
    assert respuesta.json()["anticipacion_minima_reserva_horas"] == 24


def test_la_anticipacion_minima_no_se_puede_poner_en_cero(client, db_session):
    from app.models import RolUsuario

    clinica = _clinica(db_session)
    token = _token_para(db_session, RolUsuario.ADMIN, clinica.id_clinica, "admin.a")

    respuesta = client.put(
        "/configuracion",
        headers=_auth(token),
        json={"anticipacion_minima_reserva_horas": 0},
    )

    assert respuesta.status_code == 422
```

> Si los helpers `_clinica`, `_token_para` y `_auth` de ese archivo tienen otra firma, adaptá la
> llamada; no los reescribas, son del Módulo 3 y los usan el resto de sus tests.

- [ ] **Step 8: Correr la suite completa**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: todo verde.

- [ ] **Step 9: Punto de commit (lo ejecuta Meli)**

```bash
git add backend/app/schemas/personas.py backend/app/schemas/cita.py \
        backend/app/schemas/parametros.py backend/tests/test_schemas_modulo4.py \
        backend/tests/test_configuracion_routes.py
git commit -m "feat(backend): schemas de personas y citas"
```

---

## Task 11: `get_doctor_actual` y router de pacientes

**Files:**
- Modify: `backend/app/api/deps.py`
- Create: `backend/app/api/routes/pacientes.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_pacientes_routes.py`

**Interfaces:**
- Consumes: `PacienteRepository` (Task 3), schemas (Task 10), `require_roles` y
  `resolve_clinica_id` (Módulo 1).
- Produces: `get_doctor_actual(usuario, db) -> Doctor | None` en `deps.py`; el router de
  `/pacientes`, y el patrón de router de este módulo (constantes `LECTURA`, `ESCRITURA` y `BAJA` a
  nivel de módulo) que copian las Tasks 12 y 13.

> **Este es el único archivo de los Módulos 1 a 3 que se modifica en todo el plan.**

- [ ] **Step 1: Escribir los tests que fallan**

Crear `backend/tests/test_pacientes_routes.py`:

```python
import pytest

from tests.factories import auth, crear_clinica, crear_usuario, token_de


def _token(db_session, rol_nombre, id_clinica=None, username=None):
    from app.models import RolUsuario

    rol = getattr(RolUsuario, rol_nombre)
    usuario = crear_usuario(
        db_session, rol, id_clinica, username or f"user.{rol_nombre.lower()}"
    )
    db_session.commit()
    return token_de(usuario)


def _clinica(db_session, nombre="Dental A"):
    clinica = crear_clinica(db_session, nombre)
    db_session.commit()
    return clinica


_NUEVO = {"nombre": "Ana", "apellido": "Lopez", "telefono": "70001122"}


def test_listar_sin_token_devuelve_401(client):
    assert client.get("/pacientes").status_code == 401


def test_crear_y_listar_como_admin(client, db_session):
    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")

    creacion = client.post("/pacientes", headers=auth(token), json=_NUEVO)
    assert creacion.status_code == 201
    assert creacion.json()["nombre"] == "Ana"
    assert creacion.json()["activo"] is True

    listado = client.get("/pacientes", headers=auth(token))
    assert listado.status_code == 200
    assert [p["apellido"] for p in listado.json()] == ["Lopez"]


def test_la_respuesta_incluye_la_edad_calculada(client, db_session):
    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")

    creacion = client.post(
        "/pacientes",
        headers=auth(token),
        json={**_NUEVO, "fecha_nacimiento": "2000-01-01"},
    )

    assert creacion.json()["edad"] >= 26


def test_buscar_filtra_el_listado(client, db_session):
    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    client.post("/pacientes", headers=auth(token), json=_NUEVO)
    client.post(
        "/pacientes",
        headers=auth(token),
        json={"nombre": "Beto", "apellido": "Martinez", "telefono": "70003344"},
    )

    respuesta = client.get("/pacientes?buscar=marti", headers=auth(token))

    assert [p["nombre"] for p in respuesta.json()] == ["Beto"]


def test_telefono_invalido_devuelve_422(client, db_session):
    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")

    respuesta = client.post(
        "/pacientes", headers=auth(token), json={**_NUEVO, "telefono": "abc"}
    )

    assert respuesta.status_code == 422


@pytest.mark.parametrize("rol_nombre", ["ADMIN", "ASISTENTE", "DOCTOR"])
def test_admin_asistente_y_doctor_pueden_registrar_pacientes(client, db_session, rol_nombre):
    clinica = _clinica(db_session)
    token = _token(db_session, rol_nombre, clinica.id_clinica)

    respuesta = client.post("/pacientes", headers=auth(token), json=_NUEVO)

    assert respuesta.status_code == 201


@pytest.mark.parametrize("rol_nombre", ["ASISTENTE", "DOCTOR"])
def test_asistente_y_doctor_no_pueden_dar_de_baja(client, db_session, rol_nombre):
    clinica = _clinica(db_session)
    token_admin = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    creado = client.post("/pacientes", headers=auth(token_admin), json=_NUEVO).json()
    token = _token(db_session, rol_nombre, clinica.id_clinica)

    respuesta = client.delete(
        f"/pacientes/{creado['id_paciente']}", headers=auth(token)
    )

    assert respuesta.status_code == 403


@pytest.mark.parametrize("rol_nombre", ["ASISTENTE", "DOCTOR"])
def test_el_put_no_es_una_puerta_trasera_al_delete(client, db_session, rol_nombre):
    """Quien no puede dar de baja tampoco puede desactivar por PUT."""
    clinica = _clinica(db_session)
    token_admin = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    creado = client.post("/pacientes", headers=auth(token_admin), json=_NUEVO).json()
    token = _token(db_session, rol_nombre, clinica.id_clinica)

    respuesta = client.put(
        f"/pacientes/{creado['id_paciente']}",
        headers=auth(token),
        json={"activo": False},
    )

    assert respuesta.status_code == 403
    sigue = client.get(f"/pacientes/{creado['id_paciente']}", headers=auth(token_admin))
    assert sigue.json()["activo"] is True


@pytest.mark.parametrize("rol_nombre", ["ASISTENTE", "DOCTOR"])
def test_el_asistente_y_el_doctor_si_pueden_editar_los_demas_campos(
    client, db_session, rol_nombre
):
    """El chequeo de 'activo' no debe bloquear la edicion normal."""
    clinica = _clinica(db_session)
    token_admin = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    creado = client.post("/pacientes", headers=auth(token_admin), json=_NUEVO).json()
    token = _token(db_session, rol_nombre, clinica.id_clinica)

    respuesta = client.put(
        f"/pacientes/{creado['id_paciente']}",
        headers=auth(token),
        json={"telefono": "70009999"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["telefono"] == "70009999"


def test_el_admin_si_puede_reactivar_por_put(client, db_session):
    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    creado = client.post("/pacientes", headers=auth(token), json=_NUEVO).json()
    client.delete(f"/pacientes/{creado['id_paciente']}", headers=auth(token))

    respuesta = client.put(
        f"/pacientes/{creado['id_paciente']}",
        headers=auth(token),
        json={"activo": True},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["activo"] is True


def test_el_admin_da_de_baja_y_el_paciente_desaparece_del_listado(client, db_session):
    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    creado = client.post("/pacientes", headers=auth(token), json=_NUEVO).json()

    baja = client.delete(f"/pacientes/{creado['id_paciente']}", headers=auth(token))

    assert baja.status_code == 204
    assert client.get("/pacientes", headers=auth(token)).json() == []
    con_inactivos = client.get("/pacientes?incluir_inactivos=true", headers=auth(token))
    assert len(con_inactivos.json()) == 1


def test_un_admin_no_puede_ver_un_paciente_de_otra_clinica(client, db_session):
    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    token_b = _token(db_session, "ADMIN", clinica_b.id_clinica, "admin.b")
    creado = client.post("/pacientes", headers=auth(token_b), json=_NUEVO).json()
    token_a = _token(db_session, "ADMIN", clinica_a.id_clinica, "admin.a")

    assert client.get(
        f"/pacientes/{creado['id_paciente']}", headers=auth(token_a)
    ).status_code == 404
    assert client.put(
        f"/pacientes/{creado['id_paciente']}",
        headers=auth(token_a),
        json={"nombre": "Hackeado"},
    ).status_code == 404
    assert client.delete(
        f"/pacientes/{creado['id_paciente']}", headers=auth(token_a)
    ).status_code == 404


def test_el_header_x_clinica_id_se_ignora_para_roles_no_superadmin(client, db_session):
    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    token_b = _token(db_session, "ADMIN", clinica_b.id_clinica, "admin.b")
    client.post("/pacientes", headers=auth(token_b), json=_NUEVO)
    token_a = _token(db_session, "ADMIN", clinica_a.id_clinica, "admin.a")

    respuesta = client.get(
        "/pacientes",
        headers={**auth(token_a), "X-Clinica-Id": str(clinica_b.id_clinica)},
    )

    assert respuesta.json() == []


def test_el_superadmin_opera_con_x_clinica_id(client, db_session):
    clinica = _clinica(db_session)
    token = _token(db_session, "SUPERADMIN", None, "super")

    respuesta = client.post(
        "/pacientes",
        headers={**auth(token), "X-Clinica-Id": str(clinica.id_clinica)},
        json=_NUEVO,
    )

    assert respuesta.status_code == 201


def test_el_superadmin_sin_x_clinica_id_recibe_400(client, db_session):
    _clinica(db_session)
    token = _token(db_session, "SUPERADMIN", None, "super")

    assert client.get("/pacientes", headers=auth(token)).status_code == 400
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_pacientes_routes.py -v`
Expected: FAIL — todos con `404 Not Found`, porque el router no existe todavía.

- [ ] **Step 3: Agregar `get_doctor_actual` a `deps.py`**

Modificar `backend/app/api/deps.py`.

Primero, en el import de modelos que ya está arriba del archivo, agregar `Doctor`:

```python
from app.models import Doctor, RolUsuario, Usuario
```

Después, agregar al final del archivo:

```python
def get_doctor_actual(
    usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)
) -> Doctor | None:
    """Traduce el Usuario del JWT a su fila Doctor. None si no es doctor.

    Lo usan los endpoints de citas para inyectar el filtro id_doctor: un doctor
    solo ve las suyas. El filtro es un WHERE y no un 403 a proposito — un 403 le
    confirmaria que la cita existe, que ya es informacion sobre un paciente que
    no atiende.

    El import del repositorio va adentro de la funcion para evitar un ciclo:
    deps.py lo importan las rutas, y el repositorio importa modelos que a su vez
    no deben depender de deps.
    """
    from app.repositories.doctor_repository import DoctorRepository

    if usuario.rol != RolUsuario.DOCTOR:
        return None
    return DoctorRepository(db).obtener_por_usuario(usuario.id_usuario)
```

- [ ] **Step 4: Escribir el router de pacientes**

Crear `backend/app/api/routes/pacientes.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles, resolve_clinica_id
from app.db import get_db
from app.models import RolUsuario, Usuario
from app.repositories.paciente_repository import PacienteRepository
from app.schemas.personas import PacienteCreate, PacienteResponse, PacienteUpdate

# El Modulo 4 rompe la regla unica del Modulo 3 a proposito: aquel era
# configuracion, esto es la operacion diaria. Una asistente que no puede
# registrar un paciente no puede hacer su trabajo.
LECTURA = require_roles(
    RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.DOCTOR, RolUsuario.ASISTENTE
)
ESCRITURA = require_roles(
    RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.ASISTENTE, RolUsuario.DOCTOR
)
#: Quien puede activar o desactivar un paciente. Se declara como conjunto y no
#: solo como dependencia porque el PUT tambien lo necesita: el campo 'activo'
#: viaja en el body y hay que chequearlo a mano.
ROLES_BAJA = (RolUsuario.SUPERADMIN, RolUsuario.ADMIN)
BAJA = require_roles(*ROLES_BAJA)

router = APIRouter(prefix="/pacientes", tags=["pacientes"])

NO_ENCONTRADO = "Paciente no encontrado"


@router.get("", response_model=list[PacienteResponse], dependencies=[Depends(LECTURA)])
def listar_pacientes(
    buscar: str | None = None,
    incluir_inactivos: bool = False,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> list[PacienteResponse]:
    registros = PacienteRepository(db).listar(id_clinica, buscar, incluir_inactivos)
    return [PacienteResponse.model_validate(r) for r in registros]


@router.post(
    "",
    response_model=PacienteResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(ESCRITURA)],
)
def crear_paciente(
    body: PacienteCreate,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> PacienteResponse:
    registro = PacienteRepository(db).crear(id_clinica, body.model_dump())
    db.commit()
    return PacienteResponse.model_validate(registro)


@router.get(
    "/{id_paciente}", response_model=PacienteResponse, dependencies=[Depends(LECTURA)]
)
def obtener_paciente(
    id_paciente: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> PacienteResponse:
    registro = PacienteRepository(db).obtener(id_clinica, id_paciente)
    if registro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    return PacienteResponse.model_validate(registro)


@router.put(
    "/{id_paciente}", response_model=PacienteResponse, dependencies=[Depends(ESCRITURA)]
)
def actualizar_paciente(
    id_paciente: int,
    body: PacienteUpdate,
    id_clinica: int = Depends(resolve_clinica_id),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PacienteResponse:
    datos = body.model_dump(exclude_unset=True)

    # Sin esto, el PUT seria una puerta trasera al DELETE: 'activo' viaja en el
    # body y el repositorio lo aplica con setattr, asi que un asistente o un
    # doctor (que pueden editar, pero NO dar de baja) podrian desactivar un
    # paciente mandando {"activo": false} y esquivar la regla de permisos.
    # El campo se queda en el schema porque reactivar a alguien dado de baja
    # tambien pasa por aca, pero solo lo puede tocar quien tiene la baja.
    #
    # Este chequeo NO hace falta en los routers de doctores y asistentes: ahi
    # ESCRITURA y la baja son el mismo conjunto de roles (superadmin y admin),
    # asi que no hay privilegio que escalar.
    if "activo" in datos and usuario.rol not in ROLES_BAJA:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un administrador puede activar o desactivar un paciente",
        )

    registro = PacienteRepository(db).actualizar(id_clinica, id_paciente, datos)
    if registro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    db.commit()
    return PacienteResponse.model_validate(registro)


@router.delete(
    "/{id_paciente}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(BAJA)],
)
def dar_de_baja_paciente(
    id_paciente: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> Response:
    """Borrado logico: pone activo = False, no borra la fila."""
    if not PacienteRepository(db).eliminar(id_clinica, id_paciente):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 5: Registrar el router**

Modificar `backend/app/main.py` — agregar el import y el `include_router`:

```python
from app.api.routes.pacientes import router as pacientes_router
```

```python
app.include_router(pacientes_router)
```

- [ ] **Step 6: Correr los tests y verificar que pasan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_pacientes_routes.py -v`
Expected: PASS — 16 passed (los `parametrize` cuentan por variante)

- [ ] **Step 7: Punto de commit (lo ejecuta Meli)**

```bash
git add backend/app/api/deps.py backend/app/api/routes/pacientes.py \
        backend/app/main.py backend/tests/test_pacientes_routes.py
git commit -m "feat(backend): endpoints de pacientes y dependencia get_doctor_actual"
```

---

## Task 12: Routers de doctores y asistentes

**Files:**
- Create: `backend/app/api/routes/doctores.py`
- Create: `backend/app/api/routes/asistentes.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_doctores_routes.py`
- Test: `backend/tests/test_asistentes_routes.py`

**Interfaces:**
- Consumes: `PersonalService` (Task 9), `DoctorRepository` y `AsistenteRepository` (Task 4),
  `HorarioDoctorRepository` (Task 5), schemas (Task 10), `get_doctor_actual` (Task 11).
- Produces: los routers `/doctores` (CRUD + `GET`/`PUT /doctores/{id}/horarios`) y `/asistentes`
  (CRUD).

- [ ] **Step 1: Escribir los tests de doctores que fallan**

Crear `backend/tests/test_doctores_routes.py`:

```python
import pytest

from tests.factories import auth, crear_clinica, crear_usuario, token_de


def _clinica(db_session, nombre="Dental A"):
    clinica = crear_clinica(db_session, nombre)
    db_session.commit()
    return clinica


def _token(db_session, rol_nombre, id_clinica=None, username=None):
    from app.models import RolUsuario

    rol = getattr(RolUsuario, rol_nombre)
    usuario = crear_usuario(
        db_session, rol, id_clinica, username or f"user.{rol_nombre.lower()}"
    )
    db_session.commit()
    return token_de(usuario)


_NUEVO = {
    "username": "dra.perez",
    "nombre": "Marta",
    "apellido": "Perez",
    "telefono": "70003344",
}


def test_crear_doctor_devuelve_201_y_la_password_temporal(client, db_session):
    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")

    respuesta = client.post("/doctores", headers=auth(token), json=_NUEVO)

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["doctor"]["nombre"] == "Marta"
    assert len(cuerpo["password_temporal"]) >= 12


def test_el_listado_nunca_devuelve_la_password(client, db_session):
    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    client.post("/doctores", headers=auth(token), json=_NUEVO)

    listado = client.get("/doctores", headers=auth(token)).json()

    assert "password_temporal" not in listado[0]


def test_username_repetido_devuelve_409(client, db_session):
    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    client.post("/doctores", headers=auth(token), json=_NUEVO)

    repetido = client.post("/doctores", headers=auth(token), json=_NUEVO)

    assert repetido.status_code == 409


def test_una_especialidad_de_otra_clinica_devuelve_422(client, db_session):
    from app.repositories.especialidad_repository import EspecialidadRepository

    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    de_b = EspecialidadRepository(db_session).crear(
        clinica_b.id_clinica, {"nombre": "Ortodoncia"}
    )
    db_session.commit()
    token_a = _token(db_session, "ADMIN", clinica_a.id_clinica, "admin.a")

    respuesta = client.post(
        "/doctores",
        headers=auth(token_a),
        json={**_NUEVO, "id_especialidad": de_b.id_especialidad},
    )

    assert respuesta.status_code == 422


@pytest.mark.parametrize("rol_nombre", ["DOCTOR", "ASISTENTE"])
def test_doctor_y_asistente_leen_pero_no_dan_de_alta(client, db_session, rol_nombre):
    clinica = _clinica(db_session)
    token = _token(db_session, rol_nombre, clinica.id_clinica)

    assert client.get("/doctores", headers=auth(token)).status_code == 200
    assert client.post("/doctores", headers=auth(token), json=_NUEVO).status_code == 403


def test_la_baja_desactiva_tambien_el_usuario(client, db_session):
    from app.repositories.usuario_repository import UsuarioRepository

    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    creado = client.post("/doctores", headers=auth(token), json=_NUEVO).json()

    baja = client.delete(
        f"/doctores/{creado['doctor']['id_doctor']}", headers=auth(token)
    )

    assert baja.status_code == 204
    usuario = UsuarioRepository(db_session).obtener_por_username("dra.perez")
    assert usuario.activo is False


def test_no_se_puede_ver_un_doctor_de_otra_clinica(client, db_session):
    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    token_b = _token(db_session, "ADMIN", clinica_b.id_clinica, "admin.b")
    creado = client.post("/doctores", headers=auth(token_b), json=_NUEVO).json()
    token_a = _token(db_session, "ADMIN", clinica_a.id_clinica, "admin.a")

    assert client.get(
        f"/doctores/{creado['doctor']['id_doctor']}", headers=auth(token_a)
    ).status_code == 404


def test_filtrar_el_listado_por_especialidad(client, db_session):
    from app.repositories.especialidad_repository import EspecialidadRepository

    clinica = _clinica(db_session)
    orto = EspecialidadRepository(db_session).crear(
        clinica.id_clinica, {"nombre": "Ortodoncia"}
    )
    db_session.commit()
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    client.post(
        "/doctores",
        headers=auth(token),
        json={**_NUEVO, "id_especialidad": orto.id_especialidad},
    )
    client.post(
        "/doctores",
        headers=auth(token),
        json={**_NUEVO, "username": "dr.otro", "nombre": "Otro"},
    )

    filtrado = client.get(
        f"/doctores?id_especialidad={orto.id_especialidad}", headers=auth(token)
    ).json()

    assert [d["nombre"] for d in filtrado] == ["Marta"]


# --- horarios anidados ----------------------------------------------------

_BLOQUES = {
    "bloques": [
        {"dia_semana": "lunes", "hora_inicio": "08:00:00", "hora_fin": "12:00:00"},
        {"dia_semana": "lunes", "hora_inicio": "14:00:00", "hora_fin": "18:00:00"},
    ]
}


def test_el_admin_carga_el_horario_de_un_doctor(client, db_session):
    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    creado = client.post("/doctores", headers=auth(token), json=_NUEVO).json()
    id_doctor = creado["doctor"]["id_doctor"]

    puesto = client.put(
        f"/doctores/{id_doctor}/horarios", headers=auth(token), json=_BLOQUES
    )

    assert puesto.status_code == 200
    assert len(puesto.json()) == 2
    assert client.get(
        f"/doctores/{id_doctor}/horarios", headers=auth(token)
    ).json() == puesto.json()


def test_bloques_solapados_devuelven_422(client, db_session):
    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    creado = client.post("/doctores", headers=auth(token), json=_NUEVO).json()

    respuesta = client.put(
        f"/doctores/{creado['doctor']['id_doctor']}/horarios",
        headers=auth(token),
        json={
            "bloques": [
                {"dia_semana": "lunes", "hora_inicio": "08:00:00", "hora_fin": "12:00:00"},
                {"dia_semana": "lunes", "hora_inicio": "11:00:00", "hora_fin": "14:00:00"},
            ]
        },
    )

    assert respuesta.status_code == 422


def test_un_doctor_edita_su_propio_horario_pero_no_el_de_otro(client, db_session):
    clinica = _clinica(db_session)
    token_admin = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    propio = client.post("/doctores", headers=auth(token_admin), json=_NUEVO).json()
    ajeno = client.post(
        "/doctores",
        headers=auth(token_admin),
        json={**_NUEVO, "username": "dr.otro", "nombre": "Otro"},
    ).json()

    # El token del doctor propio: su Usuario es el que creo PersonalService.
    from app.repositories.usuario_repository import UsuarioRepository

    usuario = UsuarioRepository(db_session).obtener_por_username("dra.perez")
    token_doctor = token_de(usuario)

    propio_ok = client.put(
        f"/doctores/{propio['doctor']['id_doctor']}/horarios",
        headers=auth(token_doctor),
        json=_BLOQUES,
    )
    ajeno_no = client.put(
        f"/doctores/{ajeno['doctor']['id_doctor']}/horarios",
        headers=auth(token_doctor),
        json=_BLOQUES,
    )

    assert propio_ok.status_code == 200
    assert ajeno_no.status_code == 403


def test_los_horarios_de_un_doctor_de_otra_clinica_devuelven_404(client, db_session):
    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    token_b = _token(db_session, "ADMIN", clinica_b.id_clinica, "admin.b")
    creado = client.post("/doctores", headers=auth(token_b), json=_NUEVO).json()
    token_a = _token(db_session, "ADMIN", clinica_a.id_clinica, "admin.a")

    assert client.get(
        f"/doctores/{creado['doctor']['id_doctor']}/horarios", headers=auth(token_a)
    ).status_code == 404
```

- [ ] **Step 2: Escribir los tests de asistentes que fallan**

Crear `backend/tests/test_asistentes_routes.py`:

```python
import pytest

from tests.factories import auth, crear_clinica, crear_usuario, token_de


def _clinica(db_session, nombre="Dental A"):
    clinica = crear_clinica(db_session, nombre)
    db_session.commit()
    return clinica


def _token(db_session, rol_nombre, id_clinica=None, username=None):
    from app.models import RolUsuario

    rol = getattr(RolUsuario, rol_nombre)
    usuario = crear_usuario(
        db_session, rol, id_clinica, username or f"user.{rol_nombre.lower()}"
    )
    db_session.commit()
    return token_de(usuario)


_NUEVO = {
    "username": "recepcion",
    "nombre": "Rosa",
    "apellido": "Diaz",
    "telefono": "70005566",
}


def test_crear_asistente_devuelve_201_y_la_password_temporal(client, db_session):
    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")

    respuesta = client.post("/asistentes", headers=auth(token), json=_NUEVO)

    assert respuesta.status_code == 201
    assert respuesta.json()["asistente"]["nombre"] == "Rosa"
    assert len(respuesta.json()["password_temporal"]) >= 12


def test_username_repetido_devuelve_409(client, db_session):
    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    client.post("/asistentes", headers=auth(token), json=_NUEVO)

    assert client.post(
        "/asistentes", headers=auth(token), json=_NUEVO
    ).status_code == 409


@pytest.mark.parametrize("rol_nombre", ["DOCTOR", "ASISTENTE"])
def test_doctor_y_asistente_leen_pero_no_dan_de_alta(client, db_session, rol_nombre):
    clinica = _clinica(db_session)
    token = _token(db_session, rol_nombre, clinica.id_clinica)

    assert client.get("/asistentes", headers=auth(token)).status_code == 200
    assert client.post(
        "/asistentes", headers=auth(token), json=_NUEVO
    ).status_code == 403


def test_la_baja_desactiva_tambien_el_usuario(client, db_session):
    from app.repositories.usuario_repository import UsuarioRepository

    clinica = _clinica(db_session)
    token = _token(db_session, "ADMIN", clinica.id_clinica, "admin.a")
    creado = client.post("/asistentes", headers=auth(token), json=_NUEVO).json()

    baja = client.delete(
        f"/asistentes/{creado['asistente']['id_asistente']}", headers=auth(token)
    )

    assert baja.status_code == 204
    assert UsuarioRepository(db_session).obtener_por_username("recepcion").activo is False


def test_no_se_puede_ver_un_asistente_de_otra_clinica(client, db_session):
    clinica_a = _clinica(db_session, "Dental A")
    clinica_b = _clinica(db_session, "Dental B")
    token_b = _token(db_session, "ADMIN", clinica_b.id_clinica, "admin.b")
    creado = client.post("/asistentes", headers=auth(token_b), json=_NUEVO).json()
    token_a = _token(db_session, "ADMIN", clinica_a.id_clinica, "admin.a")

    assert client.get(
        f"/asistentes/{creado['asistente']['id_asistente']}", headers=auth(token_a)
    ).status_code == 404
```

- [ ] **Step 3: Correr los tests y verificar que fallan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_doctores_routes.py tests/test_asistentes_routes.py -v`
Expected: FAIL — todos con `404 Not Found`, los routers no existen.

- [ ] **Step 4: Escribir el router de doctores**

Crear `backend/app/api/routes/doctores.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_doctor_actual, require_roles, resolve_clinica_id
from app.db import get_db
from app.exceptions import (
    HorarioInvalidoError,
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
    registro = DoctorRepository(db).actualizar(
        id_clinica, id_doctor, body.model_dump(exclude_unset=True)
    )
    if registro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    db.commit()
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
    """
    if not PersonalService(db).dar_de_baja_doctor(id_clinica, id_doctor):
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
```

- [ ] **Step 5: Escribir el router de asistentes**

Crear `backend/app/api/routes/asistentes.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles, resolve_clinica_id
from app.db import get_db
from app.exceptions import UsernameYaExisteError
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
    registro = AsistenteRepository(db).actualizar(
        id_clinica, id_asistente, body.model_dump(exclude_unset=True)
    )
    if registro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    db.commit()
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
    if not PersonalService(db).dar_de_baja_asistente(id_clinica, id_asistente):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 6: Registrar los routers**

Modificar `backend/app/main.py` — agregar los imports y los `include_router`:

```python
from app.api.routes.asistentes import router as asistentes_router
from app.api.routes.doctores import router as doctores_router
```

```python
app.include_router(doctores_router)
app.include_router(asistentes_router)
```

- [ ] **Step 7: Correr los tests y verificar que pasan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_doctores_routes.py tests/test_asistentes_routes.py -v`
Expected: PASS — 21 passed

- [ ] **Step 8: Punto de commit (lo ejecuta Meli)**

```bash
git add backend/app/api/routes/doctores.py backend/app/api/routes/asistentes.py \
        backend/app/main.py backend/tests/test_doctores_routes.py \
        backend/tests/test_asistentes_routes.py
git commit -m "feat(backend): endpoints de doctores, asistentes y horarios por doctor"
```

---

## Task 13: Router de citas

**Files:**
- Create: `backend/app/api/routes/citas.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_citas_routes.py`

**Interfaces:**
- Consumes: `CitaService` (Task 8), `CitaRepository` (Task 6), `AsistenteRepository` (Task 4),
  schemas de cita (Task 10), `get_doctor_actual` (Task 11).
- Produces: el router `/citas` con `GET`, `POST`, `GET /{id}`, `PATCH /{id}/estado`,
  `PATCH /{id}/cancelar` y `PATCH /{id}/reagendar`.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `backend/tests/test_citas_routes.py`:

```python
from datetime import datetime, timedelta

from tests.factories import auth, crear_clinica, crear_usuario, token_de


def _clinica(db_session, nombre="Dental A"):
    clinica = crear_clinica(db_session, nombre)
    db_session.commit()
    return clinica


def _token(db_session, rol_nombre, id_clinica=None, username=None):
    from app.models import RolUsuario

    rol = getattr(RolUsuario, rol_nombre)
    usuario = crear_usuario(
        db_session, rol, id_clinica, username or f"user.{rol_nombre.lower()}"
    )
    db_session.commit()
    return token_de(usuario)


def _futuro(dias=7, hora=9):
    """Un martes futuro a las 9, dentro del horario por defecto (L-V 08-17)."""
    base = datetime.now() + timedelta(days=dias)
    while base.weekday() != 1:  # martes
        base += timedelta(days=1)
    return base.replace(hour=hora, minute=0, second=0, microsecond=0)


def _clinica_lista(client, db_session, nombre="Dental A", sufijo="a"):
    """Crea clinica, admin, paciente y doctor CON horario cargado.

    Devuelve (clinica, token_admin, id_paciente, id_doctor).
    """
    clinica = _clinica(db_session, nombre)
    token = _token(db_session, "ADMIN", clinica.id_clinica, f"admin.{sufijo}")

    paciente = client.post(
        "/pacientes",
        headers=auth(token),
        json={"nombre": "Ana", "apellido": "Lopez", "telefono": "70001122"},
    ).json()
    doctor = client.post(
        "/doctores",
        headers=auth(token),
        json={
            "username": f"dra.{sufijo}",
            "nombre": "Marta",
            "apellido": "Perez",
            "telefono": "70003344",
        },
    ).json()["doctor"]
    client.put(
        f"/doctores/{doctor['id_doctor']}/horarios",
        headers=auth(token),
        json={
            "bloques": [
                {"dia_semana": dia, "hora_inicio": "08:00:00", "hora_fin": "17:00:00"}
                for dia in ("lunes", "martes", "miercoles", "jueves", "viernes")
            ]
        },
    )
    return clinica, token, paciente["id_paciente"], doctor["id_doctor"]


def _cuerpo(id_paciente, id_doctor, cuando=None, **campos):
    base = {
        "id_paciente": id_paciente,
        "id_doctor": id_doctor,
        "fecha_hora": (cuando or _futuro()).isoformat(),
    }
    base.update(campos)
    return base


def test_agendar_una_cita_valida(client, db_session):
    _, token, id_paciente, id_doctor = _clinica_lista(client, db_session)

    respuesta = client.post(
        "/citas", headers=auth(token), json=_cuerpo(id_paciente, id_doctor)
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["estado"] == "programada"
    assert respuesta.json()["duracion_minutos"] == 30


def test_agendar_en_el_pasado_devuelve_422(client, db_session):
    _, token, id_paciente, id_doctor = _clinica_lista(client, db_session)
    ayer = datetime.now() - timedelta(days=1)

    respuesta = client.post(
        "/citas", headers=auth(token), json=_cuerpo(id_paciente, id_doctor, ayer)
    )

    assert respuesta.status_code == 422


def test_agendar_sin_la_anticipacion_minima_devuelve_422(client, db_session):
    _, token, id_paciente, id_doctor = _clinica_lista(client, db_session)
    en_dos_horas = datetime.now() + timedelta(hours=2)

    respuesta = client.post(
        "/citas", headers=auth(token), json=_cuerpo(id_paciente, id_doctor, en_dos_horas)
    )

    assert respuesta.status_code == 422


def test_agendar_fuera_del_horario_de_la_clinica_devuelve_422(client, db_session):
    _, token, id_paciente, id_doctor = _clinica_lista(client, db_session)
    a_las_seis = _futuro(hora=6)

    respuesta = client.post(
        "/citas", headers=auth(token), json=_cuerpo(id_paciente, id_doctor, a_las_seis)
    )

    assert respuesta.status_code == 422


def test_un_doctor_sin_horario_cargado_devuelve_422(client, db_session):
    clinica, token, id_paciente, _ = _clinica_lista(client, db_session)
    sin_horario = client.post(
        "/doctores",
        headers=auth(token),
        json={
            "username": "dr.nuevo",
            "nombre": "Nuevo",
            "apellido": "Doctor",
            "telefono": "70009999",
        },
    ).json()["doctor"]

    respuesta = client.post(
        "/citas",
        headers=auth(token),
        json=_cuerpo(id_paciente, sin_horario["id_doctor"]),
    )

    assert respuesta.status_code == 422


def test_dos_citas_solapadas_del_mismo_doctor_devuelven_409(client, db_session):
    _, token, id_paciente, id_doctor = _clinica_lista(client, db_session)
    cuando = _futuro()
    client.post("/citas", headers=auth(token), json=_cuerpo(id_paciente, id_doctor, cuando))

    repetida = client.post(
        "/citas",
        headers=auth(token),
        json=_cuerpo(id_paciente, id_doctor, cuando + timedelta(minutes=15)),
    )

    assert repetida.status_code == 409


def test_un_paciente_de_otra_clinica_devuelve_422(client, db_session):
    _, token_a, _, id_doctor_a = _clinica_lista(client, db_session, "Dental A", "a")
    _, _, id_paciente_b, _ = _clinica_lista(client, db_session, "Dental B", "b")

    respuesta = client.post(
        "/citas", headers=auth(token_a), json=_cuerpo(id_paciente_b, id_doctor_a)
    )

    assert respuesta.status_code == 422


def test_el_asistente_agenda_y_queda_registrado_como_quien_agendo(client, db_session):
    from app.repositories.usuario_repository import UsuarioRepository

    clinica, token_admin, id_paciente, id_doctor = _clinica_lista(client, db_session)
    creado = client.post(
        "/asistentes",
        headers=auth(token_admin),
        json={
            "username": "recepcion",
            "nombre": "Rosa",
            "apellido": "Diaz",
            "telefono": "70005566",
        },
    ).json()
    usuario = UsuarioRepository(db_session).obtener_por_username("recepcion")
    token_asistente = token_de(usuario)

    respuesta = client.post(
        "/citas", headers=auth(token_asistente), json=_cuerpo(id_paciente, id_doctor)
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["id_asistente"] == creado["asistente"]["id_asistente"]


def test_un_doctor_no_puede_agendar(client, db_session):
    clinica, token_admin, id_paciente, id_doctor = _clinica_lista(client, db_session)
    from app.repositories.usuario_repository import UsuarioRepository

    usuario = UsuarioRepository(db_session).obtener_por_username("dra.a")
    token_doctor = token_de(usuario)

    respuesta = client.post(
        "/citas", headers=auth(token_doctor), json=_cuerpo(id_paciente, id_doctor)
    )

    assert respuesta.status_code == 403


def test_un_doctor_solo_ve_sus_propias_citas(client, db_session):
    from app.repositories.usuario_repository import UsuarioRepository

    clinica, token, id_paciente, id_doctor = _clinica_lista(client, db_session)
    otro = client.post(
        "/doctores",
        headers=auth(token),
        json={
            "username": "dr.otro",
            "nombre": "Otro",
            "apellido": "Doctor",
            "telefono": "70009999",
        },
    ).json()["doctor"]
    client.put(
        f"/doctores/{otro['id_doctor']}/horarios",
        headers=auth(token),
        json={
            "bloques": [
                {"dia_semana": "martes", "hora_inicio": "08:00:00", "hora_fin": "17:00:00"}
            ]
        },
    )
    mia = client.post(
        "/citas", headers=auth(token), json=_cuerpo(id_paciente, id_doctor)
    ).json()
    ajena = client.post(
        "/citas",
        headers=auth(token),
        json=_cuerpo(id_paciente, otro["id_doctor"], _futuro(dias=14)),
    ).json()

    usuario = UsuarioRepository(db_session).obtener_por_username("dra.a")
    token_doctor = token_de(usuario)

    listado = client.get("/citas", headers=auth(token_doctor)).json()

    assert [c["id_cita"] for c in listado] == [mia["id_cita"]]
    assert ajena["id_cita"] != mia["id_cita"]


def test_un_doctor_pide_una_cita_ajena_y_recibe_404_no_403(client, db_session):
    """404 y no 403: un 403 le confirmaria que la cita existe, que ya es
    informacion sobre un paciente que no atiende.
    """
    from app.repositories.usuario_repository import UsuarioRepository

    clinica, token, id_paciente, id_doctor = _clinica_lista(client, db_session)
    otro = client.post(
        "/doctores",
        headers=auth(token),
        json={
            "username": "dr.otro",
            "nombre": "Otro",
            "apellido": "Doctor",
            "telefono": "70009999",
        },
    ).json()["doctor"]
    client.put(
        f"/doctores/{otro['id_doctor']}/horarios",
        headers=auth(token),
        json={
            "bloques": [
                {"dia_semana": "martes", "hora_inicio": "08:00:00", "hora_fin": "17:00:00"}
            ]
        },
    )
    ajena = client.post(
        "/citas", headers=auth(token), json=_cuerpo(id_paciente, otro["id_doctor"])
    ).json()

    usuario = UsuarioRepository(db_session).obtener_por_username("dra.a")
    token_doctor = token_de(usuario)

    respuesta = client.get(f"/citas/{ajena['id_cita']}", headers=auth(token_doctor))

    assert respuesta.status_code == 404


def test_confirmar_y_completar_una_cita(client, db_session):
    _, token, id_paciente, id_doctor = _clinica_lista(client, db_session)
    cita = client.post(
        "/citas", headers=auth(token), json=_cuerpo(id_paciente, id_doctor)
    ).json()

    confirmada = client.patch(
        f"/citas/{cita['id_cita']}/estado",
        headers=auth(token),
        json={"estado": "confirmada"},
    )
    completada = client.patch(
        f"/citas/{cita['id_cita']}/estado",
        headers=auth(token),
        json={"estado": "completada"},
    )

    assert confirmada.json()["estado"] == "confirmada"
    assert completada.json()["estado"] == "completada"


def test_completar_una_cita_sin_confirmar_devuelve_409(client, db_session):
    _, token, id_paciente, id_doctor = _clinica_lista(client, db_session)
    cita = client.post(
        "/citas", headers=auth(token), json=_cuerpo(id_paciente, id_doctor)
    ).json()

    respuesta = client.patch(
        f"/citas/{cita['id_cita']}/estado",
        headers=auth(token),
        json={"estado": "completada"},
    )

    assert respuesta.status_code == 409


def test_cancelar_con_anticipacion_suficiente(client, db_session):
    _, token, id_paciente, id_doctor = _clinica_lista(client, db_session)
    cita = client.post(
        "/citas", headers=auth(token), json=_cuerpo(id_paciente, id_doctor)
    ).json()

    respuesta = client.patch(f"/citas/{cita['id_cita']}/cancelar", headers=auth(token))

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "cancelada"


def test_reagendar_mueve_la_cita_y_cuenta_el_movimiento(client, db_session):
    _, token, id_paciente, id_doctor = _clinica_lista(client, db_session)
    cita = client.post(
        "/citas", headers=auth(token), json=_cuerpo(id_paciente, id_doctor)
    ).json()

    respuesta = client.patch(
        f"/citas/{cita['id_cita']}/reagendar",
        headers=auth(token),
        json={"fecha_hora": _futuro(dias=21).isoformat()},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["id_cita"] == cita["id_cita"]
    assert cuerpo["veces_reagendada"] == 1
    assert cuerpo["estado"] == "programada"


def test_reagendar_demasiado_pronto_devuelve_422(client, db_session):
    _, token, id_paciente, id_doctor = _clinica_lista(client, db_session)
    cita = client.post(
        "/citas", headers=auth(token), json=_cuerpo(id_paciente, id_doctor)
    ).json()
    manana = datetime.now() + timedelta(days=1)

    respuesta = client.patch(
        f"/citas/{cita['id_cita']}/reagendar",
        headers=auth(token),
        json={"fecha_hora": manana.isoformat()},
    )

    assert respuesta.status_code == 422


def test_una_cita_de_otra_clinica_devuelve_404(client, db_session):
    _, token_a, _, _ = _clinica_lista(client, db_session, "Dental A", "a")
    _, token_b, id_paciente_b, id_doctor_b = _clinica_lista(
        client, db_session, "Dental B", "b"
    )
    de_b = client.post(
        "/citas", headers=auth(token_b), json=_cuerpo(id_paciente_b, id_doctor_b)
    ).json()

    assert client.get(
        f"/citas/{de_b['id_cita']}", headers=auth(token_a)
    ).status_code == 404
    assert client.patch(
        f"/citas/{de_b['id_cita']}/cancelar", headers=auth(token_a)
    ).status_code == 404


def test_no_existe_delete_de_citas(client, db_session):
    """Una cita no se borra, se cancela."""
    _, token, id_paciente, id_doctor = _clinica_lista(client, db_session)
    cita = client.post(
        "/citas", headers=auth(token), json=_cuerpo(id_paciente, id_doctor)
    ).json()

    respuesta = client.delete(f"/citas/{cita['id_cita']}", headers=auth(token))

    assert respuesta.status_code == 405
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_citas_routes.py -v`
Expected: FAIL — todos con `404 Not Found`, el router no existe.

- [ ] **Step 3: Escribir el router de citas**

Crear `backend/app/api/routes/citas.py`:

```python
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_doctor_actual, require_roles, resolve_clinica_id
from app.db import get_db
from app.exceptions import (
    AnticipacionInsuficienteError,
    ChoqueDeCitaError,
    CitaEnElPasadoError,
    DoctorNoDisponibleError,
    FueraDeHorarioClinicaError,
    ReferenciaInvalidaError,
    TransicionInvalidaError,
)
from app.models import EstadoCita, RolUsuario, Usuario
from app.repositories.asistente_repository import AsistenteRepository
from app.repositories.cita_repository import CitaRepository
from app.schemas.cita import (
    CambiarEstadoRequest,
    CitaCreate,
    CitaResponse,
    ReagendarRequest,
)
from app.services.cita_service import CitaService

LECTURA = require_roles(
    RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.DOCTOR, RolUsuario.ASISTENTE
)
AGENDAR = require_roles(
    RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.ASISTENTE
)
CAMBIAR_ESTADO = require_roles(
    RolUsuario.SUPERADMIN, RolUsuario.ADMIN, RolUsuario.ASISTENTE, RolUsuario.DOCTOR
)

router = APIRouter(prefix="/citas", tags=["citas"])

NO_ENCONTRADA = "Cita no encontrada"

#: Las reglas que chocan con el estado del sistema van a 409; las que violan una
#: regla sobre los datos enviados, a 422.
_A_409 = (ChoqueDeCitaError, TransicionInvalidaError)
_A_422 = (
    ReferenciaInvalidaError,
    CitaEnElPasadoError,
    AnticipacionInsuficienteError,
    FueraDeHorarioClinicaError,
    DoctorNoDisponibleError,
)


def _traducir(error: Exception) -> HTTPException:
    if isinstance(error, _A_409):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
    )


def _cita_visible(db: Session, id_clinica: int, id_cita: int, doctor_actual):
    """Devuelve la cita si el usuario puede verla, o None.

    Para el rol doctor, una cita ajena devuelve None y la ruta responde 404, no
    403: un 403 le confirmaria que la cita existe.
    """
    cita = CitaRepository(db).obtener(id_clinica, id_cita)
    if cita is None:
        return None
    if doctor_actual is not None and cita.id_doctor != doctor_actual.id_doctor:
        return None
    return cita


@router.get("", response_model=list[CitaResponse], dependencies=[Depends(LECTURA)])
def listar_citas(
    desde: datetime | None = None,
    hasta: datetime | None = None,
    id_doctor: int | None = None,
    id_paciente: int | None = None,
    estado: EstadoCita | None = None,
    id_clinica: int = Depends(resolve_clinica_id),
    doctor_actual=Depends(get_doctor_actual),
    db: Session = Depends(get_db),
) -> list[CitaResponse]:
    # El filtro del doctor es un WHERE inyectado, no un 403.
    if doctor_actual is not None:
        id_doctor = doctor_actual.id_doctor

    registros = CitaRepository(db).listar(
        id_clinica,
        desde=desde,
        hasta=hasta,
        id_doctor=id_doctor,
        id_paciente=id_paciente,
        estado=estado,
    )
    return [CitaResponse.model_validate(c) for c in registros]


@router.post(
    "",
    response_model=CitaResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(AGENDAR)],
)
def agendar_cita(
    body: CitaCreate,
    id_clinica: int = Depends(resolve_clinica_id),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CitaResponse:
    # id_asistente sale del token, nunca del body: es un dato de auditoria y el
    # cliente no debe poder mentir sobre quien agendo.
    id_asistente = None
    if usuario.rol == RolUsuario.ASISTENTE:
        perfil = AsistenteRepository(db).obtener_por_usuario(usuario.id_usuario)
        id_asistente = perfil.id_asistente if perfil else None

    try:
        cita = CitaService(db).crear(id_clinica, body.model_dump(), id_asistente)
    except (*_A_409, *_A_422) as error:
        raise _traducir(error)
    db.commit()
    return CitaResponse.model_validate(cita)


@router.get("/{id_cita}", response_model=CitaResponse, dependencies=[Depends(LECTURA)])
def obtener_cita(
    id_cita: int,
    id_clinica: int = Depends(resolve_clinica_id),
    doctor_actual=Depends(get_doctor_actual),
    db: Session = Depends(get_db),
) -> CitaResponse:
    cita = _cita_visible(db, id_clinica, id_cita, doctor_actual)
    if cita is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADA)
    return CitaResponse.model_validate(cita)


@router.patch(
    "/{id_cita}/estado",
    response_model=CitaResponse,
    dependencies=[Depends(CAMBIAR_ESTADO)],
)
def cambiar_estado_cita(
    id_cita: int,
    body: CambiarEstadoRequest,
    id_clinica: int = Depends(resolve_clinica_id),
    doctor_actual=Depends(get_doctor_actual),
    db: Session = Depends(get_db),
) -> CitaResponse:
    if _cita_visible(db, id_clinica, id_cita, doctor_actual) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADA)

    try:
        cita = CitaService(db).cambiar_estado(id_clinica, id_cita, body.estado)
    except (*_A_409, *_A_422) as error:
        raise _traducir(error)
    db.commit()
    return CitaResponse.model_validate(cita)


@router.patch(
    "/{id_cita}/cancelar",
    response_model=CitaResponse,
    dependencies=[Depends(CAMBIAR_ESTADO)],
)
def cancelar_cita(
    id_cita: int,
    id_clinica: int = Depends(resolve_clinica_id),
    doctor_actual=Depends(get_doctor_actual),
    db: Session = Depends(get_db),
) -> CitaResponse:
    if _cita_visible(db, id_clinica, id_cita, doctor_actual) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADA)

    try:
        cita = CitaService(db).cancelar(id_clinica, id_cita)
    except (*_A_409, *_A_422) as error:
        raise _traducir(error)
    db.commit()
    return CitaResponse.model_validate(cita)


@router.patch(
    "/{id_cita}/reagendar", response_model=CitaResponse, dependencies=[Depends(AGENDAR)]
)
def reagendar_cita(
    id_cita: int,
    body: ReagendarRequest,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> CitaResponse:
    """Mueve la cita en su lugar: misma fila, fecha nueva, contador +1, estado
    de vuelta a 'programada'.
    """
    try:
        cita = CitaService(db).reagendar(
            id_clinica, id_cita, body.fecha_hora, body.id_consultorio
        )
    except (*_A_409, *_A_422) as error:
        raise _traducir(error)
    if cita is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADA)
    db.commit()
    return CitaResponse.model_validate(cita)
```

- [ ] **Step 4: Registrar el router**

Modificar `backend/app/main.py` — agregar el import y el `include_router`:

```python
from app.api.routes.citas import router as citas_router
```

```python
app.include_router(citas_router)
```

- [ ] **Step 5: Correr los tests y verificar que pasan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_citas_routes.py -v`
Expected: PASS — 18 passed

- [ ] **Step 6: Correr la suite completa**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: todo verde, incluidos los Módulos 1 a 3.

- [ ] **Step 7: Punto de commit (lo ejecuta Meli)**

```bash
git add backend/app/api/routes/citas.py backend/app/main.py \
        backend/tests/test_citas_routes.py
git commit -m "feat(backend): endpoints de citas con agendamiento, cancelacion y reagendamiento"
```

---

## Task 14: Colección de Postman del Módulo 4

**Files:**
- Create: `docs/postman/ClinicaDentalWeb-Modulo4.postman_collection.json`

**Interfaces:**
- Consumes: todos los endpoints de las Tasks 11 a 13.
- Produces: una colección ejecutable de punta a punta con **Run Collection**, con el mismo formato
  que `ClinicaDentalWeb-Modulo3.postman_collection.json`: un archivo por módulo, variables de
  colección que encadenan los tokens y los ids, y `pm.test(...)` en cada request.

> Un archivo nuevo, **no** se edita el del Módulo 3. Cada módulo tiene su colección, igual que tiene
> su spec y su plan: así se puede correr la verificación de un módulo sin arrastrar los demás, y el
> historial de cada uno queda claro.
>
> Los tests con SQLite no ejercitan la serialización real de `datetime` ni de los enums contra
> MySQL. Esta colección corre contra el backend real en Docker y es lo que se usa en la Task 15.

- [ ] **Step 1: Copiar la estructura base de la colección del Módulo 3**

Abrir `docs/postman/ClinicaDentalWeb-Modulo3.postman_collection.json` y reutilizar tal cual:

- El bloque `info` (cambiando `name` a `"ClinicaDentalWeb - Modulo 4 (Operacion clinica basica)"` y
  la `description` al flujo de este módulo).
- La carpeta `0. Setup` completa: `Login superadmin` → `Crear clinica` → `Login admin`. Ya guarda
  `tokenSuperadmin`, `tokenAdmin`, `idClinica`, `adminUsername` y `adminPassword` en variables de
  colección.

Al bloque `variable`, agregar las de este módulo:

```json
{ "key": "idPaciente", "value": "" },
{ "key": "idDoctor", "value": "" },
{ "key": "idAsistente", "value": "" },
{ "key": "idCita", "value": "" },
{ "key": "doctorUsername", "value": "dra.perez" },
{ "key": "doctorPassword", "value": "" },
{ "key": "tokenDoctor", "value": "" },
{ "key": "fechaCita", "value": "" },
{ "key": "fechaReagenda", "value": "" }
```

- [ ] **Step 2: Agregar un pre-request script de colección que calcule las fechas**

Las citas tienen que caer en un día hábil futuro y dentro del horario. Calcularlas a mano hace que
la colección se venza. En el `event` de nivel colección, agregar un `prerequest`:

```javascript
const proximoDiaHabil = (diasDesdeHoy, hora) => {
  const fecha = new Date();
  fecha.setDate(fecha.getDate() + diasDesdeHoy);
  while (fecha.getDay() === 0 || fecha.getDay() === 6) {
    fecha.setDate(fecha.getDate() + 1);
  }
  fecha.setHours(hora, 0, 0, 0);
  const pad = (n) => String(n).padStart(2, '0');
  return `${fecha.getFullYear()}-${pad(fecha.getMonth() + 1)}-${pad(fecha.getDate())}` +
         `T${pad(fecha.getHours())}:00:00`;
};

pm.collectionVariables.set('fechaCita', proximoDiaHabil(7, 9));
pm.collectionVariables.set('fechaReagenda', proximoDiaHabil(21, 10));
pm.collectionVariables.set('fechaTemprana', proximoDiaHabil(7, 6));
pm.collectionVariables.set('fechaPasada', '2020-01-01T09:00:00');
pm.collectionVariables.set('fechaManana', proximoDiaHabil(1, 9));
```

- [ ] **Step 3: Carpeta "1. Pacientes"**

Cinco requests, todos con `Authorization: Bearer {{tokenAdmin}}`:

| Request | Método y URL | Body | Tests |
|---|---|---|---|
| Crear paciente | `POST {{baseUrl}}/pacientes` | `{"nombre":"Ana","apellido":"Lopez","telefono":"7000-1122","fecha_nacimiento":"2000-01-15","correo":"ana@ejemplo.com"}` | `status 201`; `activo === true`; `telefono === "70001122"` (se normalizó); `edad` es number; guarda `idPaciente` |
| Listar pacientes | `GET {{baseUrl}}/pacientes` | — | `status 200`; el array tiene al menos 1 |
| Buscar por apellido | `GET {{baseUrl}}/pacientes?buscar=LOP` | — | `status 200`; hay al menos 1 resultado (la búsqueda ignora mayúsculas) |
| Teléfono inválido | `POST {{baseUrl}}/pacientes` | `{"nombre":"X","apellido":"Y","telefono":"abc"}` | `status 422` |
| Obtener paciente | `GET {{baseUrl}}/pacientes/{{idPaciente}}` | — | `status 200`; `id_paciente` coincide |

Script del primero:

```javascript
pm.test('status 201', () => pm.response.to.have.status(201));
const body = pm.response.json();
pm.test('nace activo', () => pm.expect(body.activo).to.eql(true));
pm.test('el telefono se normaliza', () => pm.expect(body.telefono).to.eql('70001122'));
pm.test('la edad viene calculada', () => pm.expect(body.edad).to.be.a('number'));
pm.collectionVariables.set('idPaciente', body.id_paciente);
```

- [ ] **Step 4: Carpeta "2. Doctores y horarios"**

| Request | Método y URL | Body | Tests |
|---|---|---|---|
| Crear doctor | `POST {{baseUrl}}/doctores` | `{"username":"{{doctorUsername}}","nombre":"Marta","apellido":"Perez","telefono":"70003344"}` | `status 201`; `password_temporal` es string de 12+ chars; guarda `idDoctor` y `doctorPassword` |
| Username repetido | `POST {{baseUrl}}/doctores` | el mismo body | `status 409` |
| Cargar horario | `PUT {{baseUrl}}/doctores/{{idDoctor}}/horarios` | los 5 días hábiles de `08:00:00` a `17:00:00` | `status 200`; el array tiene 5 elementos |
| Bloques solapados | `PUT {{baseUrl}}/doctores/{{idDoctor}}/horarios` | dos bloques del lunes que se pisan | `status 422` |
| Recargar horario válido | `PUT {{baseUrl}}/doctores/{{idDoctor}}/horarios` | de nuevo los 5 días | `status 200` — deja el horario sano para la carpeta 4 |
| Login del doctor | `POST {{baseUrl}}/auth/login` | `{"username":"{{doctorUsername}}","password":"{{doctorPassword}}"}` en JSON — `/auth/login` recibe un `LoginRequest` de Pydantic, **no** form-urlencoded | `status 200`; `debe_cambiar_password === true`; guarda `tokenDoctor` |

Script del primero:

```javascript
pm.test('status 201', () => pm.response.to.have.status(201));
const body = pm.response.json();
pm.test('devuelve la password temporal una sola vez',
  () => pm.expect(body.password_temporal).to.be.a('string').with.length.of.at.least(12));
pm.collectionVariables.set('idDoctor', body.doctor.id_doctor);
pm.collectionVariables.set('doctorPassword', body.password_temporal);
```

Script del login del doctor — verifica el flujo de password temporal de punta a punta:

```javascript
pm.test('status 200', () => pm.response.to.have.status(200));
const body = pm.response.json();
pm.test('el rol es doctor', () => pm.expect(body.usuario.rol).to.eql('doctor'));
pm.test('debe cambiar la password temporal',
  () => pm.expect(body.usuario.debe_cambiar_password).to.eql(true));
pm.collectionVariables.set('tokenDoctor', body.access_token);
```

- [ ] **Step 5: Carpeta "3. Asistentes"**

| Request | Método y URL | Body | Tests |
|---|---|---|---|
| Crear asistente | `POST {{baseUrl}}/asistentes` | `{"username":"recepcion","nombre":"Rosa","apellido":"Diaz","telefono":"70005566"}` | `status 201`; hay `password_temporal`; guarda `idAsistente` |
| Listar asistentes | `GET {{baseUrl}}/asistentes` | — | `status 200`; ninguno expone `password_temporal` |

Script del segundo:

```javascript
pm.test('status 200', () => pm.response.to.have.status(200));
const body = pm.response.json();
pm.test('el listado nunca expone la password',
  () => body.forEach((a) => pm.expect(a).to.not.have.property('password_temporal')));
```

- [ ] **Step 6: Carpeta "4. Citas — camino feliz"**

| Request | Método y URL | Body | Tests |
|---|---|---|---|
| Agendar cita | `POST {{baseUrl}}/citas` | `{"id_paciente":{{idPaciente}},"id_doctor":{{idDoctor}},"fecha_hora":"{{fechaCita}}","motivo":"Control"}` | `status 201`; `estado === "programada"`; `duracion_minutos === 30` (viene de la configuración); `veces_reagendada === 0`; guarda `idCita` |
| Listar la agenda | `GET {{baseUrl}}/citas` | — | `status 200`; al menos 1 |
| Confirmar | `PATCH {{baseUrl}}/citas/{{idCita}}/estado` | `{"estado":"confirmada"}` | `status 200`; `estado === "confirmada"` |
| Reagendar | `PATCH {{baseUrl}}/citas/{{idCita}}/reagendar` | `{"fecha_hora":"{{fechaReagenda}}"}` | `status 200`; **`id_cita` sigue siendo el mismo** (movió la fila, no creó otra); `veces_reagendada === 1`; `estado === "programada"` |
| Confirmar de nuevo | `PATCH {{baseUrl}}/citas/{{idCita}}/estado` | `{"estado":"confirmada"}` | `status 200` |
| Completar | `PATCH {{baseUrl}}/citas/{{idCita}}/estado` | `{"estado":"completada"}` | `status 200`; `estado === "completada"` |

Script del reagendamiento, que es el que verifica la decisión de diseño:

```javascript
pm.test('status 200', () => pm.response.to.have.status(200));
const body = pm.response.json();
pm.test('es la misma cita, no una nueva',
  () => pm.expect(String(body.id_cita)).to.eql(String(pm.collectionVariables.get('idCita'))));
pm.test('cuenta el reagendamiento', () => pm.expect(body.veces_reagendada).to.eql(1));
pm.test('pierde la confirmacion', () => pm.expect(body.estado).to.eql('programada'));
```

- [ ] **Step 7: Carpeta "5. Citas — reglas que deben fallar"**

Es la carpeta más valiosa: verifica que cada validador dispara con el código correcto contra MySQL
real. Todas usan `{{tokenAdmin}}`.

| Request | Body relevante | Test |
|---|---|---|
| En el pasado | `"fecha_hora":"{{fechaPasada}}"` | `status 422` |
| Sin anticipación mínima | `"fecha_hora":"{{fechaManana}}"` (a menos de 24 h) | `status 422` |
| Fuera del horario de la clínica | `"fecha_hora":"{{fechaTemprana}}"` (06:00) | `status 422` |
| Paciente inexistente | `"id_paciente": 999999` | `status 422` |
| Choque de doctor | agendar dos veces en `{{fechaCita}}` con 15 minutos de diferencia | la segunda, `status 409` |
| Transición inválida | `PATCH .../estado` con `{"estado":"completada"}` sobre una cita recién creada | `status 409` |
| Reagendar demasiado pronto | `{"fecha_hora":"{{fechaManana}}"}` | `status 422` |
| Borrar una cita | `DELETE {{baseUrl}}/citas/{{idCita}}` | `status 405` — las citas no se borran, se cancelan |

Para el choque hace falta agendar una cita "cebo" antes; usá `{{fechaCita}}` + otra a los 15
minutos y verificá el `409` en la segunda.

- [ ] **Step 8: Carpeta "6. Aislamiento y permisos"**

| Request | Headers | Test |
|---|---|---|
| El doctor solo ve sus citas | `Bearer {{tokenDoctor}}` en `GET /citas` | `status 200`; **todas** las citas del array tienen `id_doctor === {{idDoctor}}` |
| El doctor no puede agendar | `Bearer {{tokenDoctor}}` en `POST /citas` | `status 403` |
| El doctor no puede dar de alta doctores | `Bearer {{tokenDoctor}}` en `POST /doctores` | `status 403` |
| El admin no puede usar X-Clinica-Id | `Bearer {{tokenAdmin}}` + `X-Clinica-Id: 999` en `GET /pacientes` | `status 200` y devuelve **sus** pacientes: el header se ignora para roles no-superadmin |
| El superadmin necesita X-Clinica-Id | `Bearer {{tokenSuperadmin}}` en `GET /pacientes` sin header | `status 400` |
| El superadmin con X-Clinica-Id | `Bearer {{tokenSuperadmin}}` + `X-Clinica-Id: {{idClinica}}` | `status 200` |
| Sin token | `GET /citas` sin `Authorization` | `status 401` |

Script del primero:

```javascript
pm.test('status 200', () => pm.response.to.have.status(200));
const body = pm.response.json();
const idDoctor = String(pm.collectionVariables.get('idDoctor'));
pm.test('un doctor solo ve sus propias citas',
  () => body.forEach((c) => pm.expect(String(c.id_doctor)).to.eql(idDoctor)));
```

- [ ] **Step 9: Verificar que el JSON es válido**

Run, desde la raíz del repo:
```bash
python -c "import json; json.load(open('docs/postman/ClinicaDentalWeb-Modulo4.postman_collection.json', encoding='utf-8')); print('JSON valido')"
```
Expected: imprime `JSON valido`

La ejecución real de la colección va en la Task 15, que es donde el backend corre contra MySQL.

- [ ] **Step 10: Punto de commit (lo ejecuta Meli)**

```bash
git add docs/postman/ClinicaDentalWeb-Modulo4.postman_collection.json
git commit -m "test(postman): coleccion de verificacion del Modulo 4"
```

---

## Task 15: Verificación contra MySQL real y cierre

**Files:**
- Modify: `docs/CONTEXTO-PROYECTO.md`

**Interfaces:**
- Consumes: todo lo anterior.
- Produces: el módulo verificado contra MySQL y la documentación actualizada para el Módulo 5.

> **Esta task no es opcional.** El `CONTEXTO-PROYECTO.md` documenta dos bugs reales que **solo
> aparecen contra MySQL**, y el enum `EstadoCita` es exactamente el tipo de cosa que los dispara.
> Las comparaciones de rango sobre columnas `DateTime` también se comportan distinto entre SQLite y
> MySQL.

- [ ] **Step 1: Levantar el entorno con MySQL**

Run, desde la raíz del repo:
```bash
docker compose build backend
docker compose up -d
```
Expected: los dos contenedores (`backend` y `db`) quedan arriba.

> Si `alembic upgrade head` falla con error 2003 en el primer intento, es el bug de infraestructura
> ya documentado en la página `Plannig` de Notion (el healthcheck de `db` da `Healthy` durante el
> servidor temporal de inicialización de MySQL). Esperá unos segundos y reintentá. No lo arregles
> acá: es del Módulo 1 y es de Christian.

- [ ] **Step 2: Aplicar las migraciones**

Run: `docker compose exec backend alembic upgrade head`
Expected: aplica `0004` sin errores y queda en head.

- [ ] **Step 3: Verificar que los enums nuevos quedaron en minúscula en el esquema real**

Run:
```bash
docker compose exec db mysql -u root -p -e "SHOW COLUMNS FROM cita LIKE 'estado'; SHOW COLUMNS FROM horario_doctor LIKE 'dia_semana';" clinica
```
Expected: el tipo de `estado` es
`enum('programada','confirmada','completada','cancelada','no_asistio')` y el de `dia_semana` es
`enum('lunes','martes','miercoles','jueves','viernes','sabado','domingo')` — **todo en minúscula**.
Si aparecen en mayúscula, falta el `values_callable` en algún modelo (bug conocido #2).

- [ ] **Step 4: Correr la suite completa dentro del contenedor**

Run: `docker compose exec backend python -m pytest -q`
Expected: todo verde.

- [ ] **Step 5: Correr la colección de Postman contra MySQL**

Importar `docs/postman/ClinicaDentalWeb-Modulo4.postman_collection.json` (Task 14) y usar **Run
Collection** sobre las seis carpetas en orden, con el backend en `http://localhost:8000`.

Expected: **todos** los `pm.test` en verde, cero fallidos. Esto valida el camino que los tests con
SQLite no recorren: serialización real de `datetime` y de los enums contra MySQL, y el flujo
completo de password temporal (crear doctor → loguearse con la temporal → `debe_cambiar_password`
en `true`).

Si preferís correrla desde la terminal, con `newman` instalado:

```bash
newman run docs/postman/ClinicaDentalWeb-Modulo4.postman_collection.json
```

Si algún test falla, **no lo arregles editando la colección**: la colección describe el
comportamiento esperado según el spec. El que está mal es el backend.

- [ ] **Step 6: Actualizar `CONTEXTO-PROYECTO.md`**

Modificar `docs/CONTEXTO-PROYECTO.md`:

1. En la tabla del roadmap (sección 2), poner el Módulo 4 en `✅ Completo` y el 5 en `⬜ Siguiente`.
2. En la lista de documentación de diseño (sección 1), agregar las dos entradas nuevas:

```markdown
- `docs/superpowers/specs/2026-08-02-modulo-4-operacion-clinica-design.md` — spec del Módulo 4,
  incluye la máquina de estados de la cita y la justificación del diseño de validadores.
- `docs/superpowers/plans/2026-08-02-modulo-4-operacion-clinica-plan.md` — plan TDD del Módulo 4.
```

3. Agregar una sección `## 6ter. Qué existe ya — Módulo 4 (Operación Clínica Básica)`, siguiendo el
   formato de la sección `6bis` del Módulo 3, que cubra:
   - Los cinco modelos nuevos y la columna nueva de `ConfiguracionClinica`.
   - Que `Doctor` y `Asistente` son 1:1 con `Usuario` y se dan de alta por `PersonalService`, que
     devuelve la password temporal una sola vez.
   - Que `HorarioDoctor` tiene PK propia (varios bloques por día) a diferencia de `HorarioClinica`.
   - **El diseño de validadores**: dónde viven, cuál es la interfaz, y que agregar una regla es un
     archivo nuevo más un renglón en `validadores_por_defecto`, no editar `CitaService`.
   - La máquina de estados y que `TRANSICIONES_PERMITIDAS` es la única fuente de verdad.
   - Que reagendar mueve la fila, incrementa `veces_reagendada` y baja el estado a `programada`.
   - **Que este módulo rompe la regla de permisos única del Módulo 3, y por qué.**
   - Que el rol `doctor` ve solo sus citas mediante un `WHERE`, y que una cita ajena da `404` y no
     `403`.
   - Las siete excepciones nuevas y su traducción a HTTP.
   - Qué habilita para el Módulo 5.
4. En la sección 8 (bugs reales), agregar como punto 3:

```markdown
3. **`Cita.duracion_minutos` se guarda, no se deriva de la configuración.** Si se leyera de
   `ConfiguracionClinica` al mostrar la cita, cambiar la duración por defecto movería
   retroactivamente todas las citas ya agendadas y podría hacerlas chocar entre sí. La duración es
   una foto del momento en que se agendó. Si en el Módulo 5 o 6 aparece la tentación de derivarla,
   no lo hagas.
```

- [ ] **Step 7: Bajar el entorno**

Run: `docker compose down`
Expected: los contenedores se detienen.

- [ ] **Step 8: Punto de commit final (lo ejecuta Meli)**

```bash
git add docs/CONTEXTO-PROYECTO.md
git commit -m "docs: documentar el Modulo 4 en el contexto del proyecto"
```

- [ ] **Step 9: Actualizar Notion (lo hace Meli)**

Poner BE-04 en `Done` en la base de Features y en la tabla `Distribución` de la página `Plannig`.

---

## Apéndice: correcciones que salieron de las revisiones

Cada task se implementó y después pasó por una revisión de código independiente. Las revisiones
encontraron **cinco defectos críticos**, y los cinco eran fallas de este plan, no del implementador:
el código estaba escrito exactamente como acá se pedía.

Los bloques de código de las Tasks 1 a 11 ya están corregidos arriba. Este apéndice registra el
diagnóstico de cada uno —que es la parte que vale conservar— y trae el código final de las Tasks 12
y 13, cuyas correcciones no se reflejaron en los bloques originales.

### Los cinco críticos

| # | Task | Qué estaba mal | Por qué importaba |
|---|---|---|---|
| 1 | 1 | La migración creaba el índice `ix_cita_doctor_fecha` y el modelo `Cita` no lo declaraba | Los tests corren sobre `Base.metadata.create_all()`, así que validaban un esquema sin índice mientras producción corría con uno. Divergencia modelo/migración, el tipo de bug que solo aparece en producción. |
| 2 | 8 | `cambiar_estado` aceptaba pasar a `cancelada` consultando solo `TRANSICIONES_PERMITIDAS` | La tabla permite `programada → cancelada`, así que con el endpoint `PATCH /citas/{id}/estado` cancelar sobre la hora era un simple PATCH: se salteaba `horas_minimas_cambio_cita` y toda la regla de anticipación quedaba decorativa. Ahora delega en `cancelar()`. |
| 3 | 8 | `reagendar` decidía la terminalidad con `ESTADOS_ACTIVOS` en vez de con la tabla de transiciones | `ESTADOS_ACTIVOS` es una constante de detección de choques de agenda; que coincidiera con "no terminal" era accidental. Si `no_asistio` pasara a ocupar el slot para las métricas del Módulo 7, se volvería reagendable una cita a la que el paciente no vino. |
| 4 | 11 | `PacienteUpdate` acepta `activo`, y el `PUT` lo pueden usar `asistente` y `doctor`, que no tienen permiso de baja | Escalada de privilegio: desactivar un paciente con `{"activo": false}` por `PUT` esquivaba la regla de que solo un admin da de baja. El revisor lo reprodujo en vivo. |
| 5 | 13 | El filtro de visibilidad del doctor sobre las citas decidía por `doctor_actual is not None` | **Falla abierta.** `get_doctor_actual` devuelve `None` tanto para "no es doctor" como para "es doctor sin fila `Doctor`". En el segundo caso el filtro se desactivaba y el doctor veía **todas las citas de la clínica**. El estado es alcanzable: cualquier alta hecha fuera de `PersonalService` lo produce. Ahora decide por rol y, ante la duda, cierra. |

**El patrón que se repite:** cuatro de los cinco son la misma clase de error — un campo o una regla
que viaja por un camino distinto al que el diseño previó (el body de un `PUT`, una constante
prestada de otro concepto, un `None` con dos significados). Ninguno lo habría encontrado la suite de
tests tal como estaba escrita: los cinco necesitaron que alguien leyera el código preguntándose "¿y
si esto llega por otro lado?".

### Importantes y menores, en una línea cada uno

- La búsqueda de pacientes justificaba su `func.lower()` con un comentario copiado de
  `CatalogoRepository`, donde aplica a `==`. Sobre un `LIKE`, SQLite ya pliega ASCII: el comentario
  afirmaba una protección que ahí no existía.
- El prefiltro de `_solapadas` usaba una ventana de 24 horas hardcodeada que asumía en silencio que
  ninguna cita dura más que eso. Ahora es `DURACION_MAXIMA_MINUTOS`, acoplada al tope del schema y
  documentada en los dos lados.
- `_dar_de_baja` toleraba en silencio un `Usuario` ausente y devolvía `True`, o sea informaba éxito
  habiendo dejado al profesional con login activo.
- `CitaService` compara contra `datetime.now()`, que es *naive*. Una `fecha_hora` con zona horaria
  producía `TypeError` y un **500** en vez de un 422. Se rechaza en los schemas de cita.
- `PUT /doctores/{id}` no validaba `id_especialidad`: aceptaba una de otra clínica y una inexistente
  (que contra MySQL con las FK activas sería un `IntegrityError` sin atrapar, o sea un 500).
- El `PUT` podía reactivar el perfil dejando el `Usuario` desactivado: un doctor que aparece en los
  listados y al que se le pueden agendar citas, pero que no puede entrar al sistema.
- Faltaban tests del override por query string, del 404 del doctor al cambiar el estado de una cita
  ajena, y del camino positivo (que el doctor **de esa cita** sí puede cambiarlo). Y el test del 404
  no ancla el control: sin verificar que el admin sí la ve con 200, pasaría igual si el endpoint
  devolviera 404 siempre.

### Deuda registrada, no corregida

- La búsqueda de pacientes no escapa los comodines `%` y `_` del término que escribe el usuario. Sin
  riesgo de inyección (la query está parametrizada); solo hace que buscar `"50%"` no busque el
  literal.
- Ningún test cubre la búsqueda con caracteres no-ASCII (eñes, tildes), y **no se puede cubrir en
  SQLite**: no pliega no-ASCII ni en `LIKE` ni en `lower()`. Contra MySQL con `utf8mb4_general_ci`
  funciona. Verificar a mano en la Task 15.
- El chequeo de `username` es *read-then-write*, así que dos altas concurrentes con el mismo username
  dan `IntegrityError` (500) en vez de `UsernameYaExisteError` (409). Heredado del Módulo 2.
- `db.rollback()` en `PersonalService` descarta trabajo pendiente de la misma sesión. Heredado del
  Módulo 2; documentarlo antes de que alguna ruta combine `PersonalService` con otra escritura.
- Los schemas `Update` no fijan `extra="forbid"`, así que un typo del cliente (`activo_flag`) se
  acepta con 200 y sin efecto. No hay escalada (se verificó que `id_usuario` e `id_clinica` en el
  body se descartan), pero es un fallo silencioso.
- `datetime.now()` es la hora local del contenedor, mientras `created_at` usa `func.now()` (hora del
  motor). Si el contenedor corre en UTC y la clínica está en El Salvador, las tres reglas de
  anticipación se corren 6 horas. Conviene una única función "ahora de la clínica".

### Código final de las Tasks 12 y 13

Reemplaza lo que dicen los bloques de esas tasks más arriba.

**`app/api/routes/citas.py`** — `_cita_visible` recibe el usuario y decide por rol; `listar_citas`
devuelve lista vacía para un doctor sin perfil. `obtener_cita`, `cambiar_estado_cita` y
`cancelar_cita` reciben también `usuario: Usuario = Depends(get_current_user)` y se lo pasan a
`_cita_visible`. Los dos últimos agregan `if cita is None: raise HTTPException(404, NO_ENCONTRADA)`
después del `try/except`, por consistencia con `reagendar_cita` (el servicio puede devolver `None`
en una carrera entre dos requests).

```python
def _cita_visible(
    db: Session, id_clinica: int, id_cita: int, usuario: Usuario, doctor_actual
):
    """Devuelve la cita si el usuario puede verla, o None.

    Para el rol doctor, una cita ajena devuelve None y la ruta responde 404, no
    403: un 403 le confirmaria que la cita existe, que ya es informacion sobre
    un paciente que no atiende.

    El chequeo se hace por ROL y no por "tiene perfil": un Usuario con rol
    doctor pero sin fila Doctor (posible si el alta no paso por PersonalService)
    no debe ver nada, en vez de ver todo. La falla tiene que cerrar, no abrir.
    """
    cita = CitaRepository(db).obtener(id_clinica, id_cita)
    if cita is None:
        return None
    if usuario.rol == RolUsuario.DOCTOR:
        if doctor_actual is None or cita.id_doctor != doctor_actual.id_doctor:
            return None
    return cita


@router.get("", response_model=list[CitaResponse], dependencies=[Depends(LECTURA)])
def listar_citas(
    desde: datetime | None = None,
    hasta: datetime | None = None,
    id_doctor: int | None = None,
    id_paciente: int | None = None,
    estado: EstadoCita | None = None,
    id_clinica: int = Depends(resolve_clinica_id),
    usuario: Usuario = Depends(get_current_user),
    doctor_actual=Depends(get_doctor_actual),
    db: Session = Depends(get_db),
) -> list[CitaResponse]:
    # El filtro del doctor es un WHERE inyectado, no un 403. Se decide por rol:
    # un doctor sin perfil no ve nada, en vez de ver todo.
    if usuario.rol == RolUsuario.DOCTOR:
        if doctor_actual is None:
            return []
        id_doctor = doctor_actual.id_doctor

    registros = CitaRepository(db).listar(
        id_clinica,
        desde=desde,
        hasta=hasta,
        id_doctor=id_doctor,
        id_paciente=id_paciente,
        estado=estado,
    )
    return [CitaResponse.model_validate(c) for c in registros]
```

**`app/services/personal_service.py`** — la validación de especialidad se extrae a un método
público que usan el alta y la edición, y `_dar_de_baja` se generaliza a `_cambiar_actividad`, que
mueve la actividad del perfil y la del `Usuario` juntas **en los dos sentidos**.

```python
    def validar_especialidad(self, id_clinica: int, id_especialidad: int | None) -> None:
        """Lanza ReferenciaInvalidaError si la especialidad no sirve para esta clinica.

        La usan el alta y la edicion de doctores: la regla es la misma y no
        conviene tenerla escrita dos veces.
        """
        if id_especialidad is None:
            return
        especialidad = self.especialidades.obtener(id_clinica, id_especialidad)
        if especialidad is None or not especialidad.activo:
            raise ReferenciaInvalidaError("La especialidad no existe en esta clinica")

    def _cambiar_actividad(
        self, repositorio, id_clinica: int, id_perfil: int, activo: bool
    ) -> bool:
        """Activa o desactiva perfil y Usuario juntos, en una transaccion.

        Los dos sentidos van juntos a proposito: un profesional dado de baja no
        debe poder entrar al sistema, y uno reactivado tiene que poder entrar. Si
        se movieran por separado quedaria un medio-estado incoherente (un doctor
        que aparece en los listados y al que se le pueden agendar citas, pero que
        no puede loguearse).
        """
        perfil = repositorio.obtener(id_clinica, id_perfil)
        if perfil is None:
            return False
        try:
            if activo:
                perfil.activo = True
            else:
                # El borrado logico del perfil lo hace el repositorio; aca solo
                # se coordina la transaccion con la baja del Usuario.
                repositorio.eliminar(id_clinica, id_perfil)
            usuario = self.usuarios.obtener_por_id(perfil.id_usuario)
            if usuario is None:
                # Inalcanzable mientras la FK sea NOT NULL, pero si alguna vez
                # pasara no se puede devolver True: quedaria un perfil y un
                # login desincronizados.
                raise ReferenciaInvalidaError(
                    "El perfil no tiene un usuario asociado"
                )
            usuario.activo = activo
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return True

    def dar_de_baja_doctor(self, id_clinica: int, id_doctor: int) -> bool:
        return self._cambiar_actividad(self.doctores, id_clinica, id_doctor, False)

    def dar_de_baja_asistente(self, id_clinica: int, id_asistente: int) -> bool:
        return self._cambiar_actividad(self.asistentes, id_clinica, id_asistente, False)

    def reactivar_doctor(self, id_clinica: int, id_doctor: int) -> bool:
        return self._cambiar_actividad(self.doctores, id_clinica, id_doctor, True)

    def reactivar_asistente(self, id_clinica: int, id_asistente: int) -> bool:
        return self._cambiar_actividad(self.asistentes, id_clinica, id_asistente, True)
```

En `crear_doctor`, el bloque de validación de especialidad se reemplaza por una línea:

```python
        self.validar_especialidad(id_clinica, campos.get("id_especialidad"))
```

**`app/api/routes/doctores.py`** — `actualizar_doctor` valida la especialidad y delega `activo` al
servicio; el `DELETE` atrapa `ReferenciaInvalidaError`. `asistentes.py` es igual, sin la parte de
especialidad.

```python
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
    activo = datos.pop("activo", None)
    if activo is not None:
        servicio = PersonalService(db)
        cambio = (
            servicio.reactivar_doctor(id_clinica, id_doctor)
            if activo
            else servicio.dar_de_baja_doctor(id_clinica, id_doctor)
        )
        if not cambio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO
            )

    registro = DoctorRepository(db).actualizar(id_clinica, id_doctor, datos)
    if registro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    db.commit()
    return DoctorResponse.model_validate(registro)


def dar_de_baja_doctor(
    id_doctor: int,
    id_clinica: int = Depends(resolve_clinica_id),
    db: Session = Depends(get_db),
) -> Response:
    """Desactiva el perfil Y el Usuario: un profesional dado de baja no debe
    poder seguir entrando al sistema.
    """
    try:
        dado_de_baja = PersonalService(db).dar_de_baja_doctor(id_clinica, id_doctor)
    except ReferenciaInvalidaError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        )
    if not dado_de_baja:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NO_ENCONTRADO)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

Los tests que acompañan a estas correcciones están en el repo, en
`tests/test_citas_routes.py`, `tests/test_doctores_routes.py` y `tests/test_asistentes_routes.py`.

---
