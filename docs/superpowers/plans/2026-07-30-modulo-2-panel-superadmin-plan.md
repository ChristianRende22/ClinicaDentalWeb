# Módulo 2: Panel Superadministrador — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir el CRUD de clínicas para el superadmin — crear/editar/activar/suspender
clínicas, asignar admin principal con password temporal forzada a cambiar, y controlar qué
módulos tiene habilitados cada clínica.

**Architecture:** Sigue el mismo patrón del Módulo 1 (FastAPI + SQLAlchemy + repositorios +
servicios), con dos repositorios nuevos que **no** heredan de `BaseRepository` porque operan a
nivel de plataforma (`Clinica`) o con llave compuesta no-entera (`ClinicaModulo`), y un
`ClinicaService` que orquesta la creación atómica de clínica + módulos + admin.

**Tech Stack:** Mismo stack del Módulo 1 (FastAPI, SQLAlchemy 2.0, Alembic, MySQL, JWT, bcrypt,
pytest) + `email-validator` (nuevo, para `pydantic.EmailStr`).

## Global Constraints

- Todas las rutas de `/clinicas` requieren `rol == superadmin` (usa `require_roles` del Módulo 1,
  sin cambios).
- `Usuario.debe_cambiar_password` nuevo campo, default `True`.
- `ClinicaRepository` y `ClinicaModuloRepository` **no** heredan de `BaseRepository` (documentado
  en el spec, sección 6) — son repositorios de plataforma / llave compuesta, no recursos
  tenant-scoped con PK entera simple.
- `MODULOS_DISPONIBLES` (constante, única fuente de verdad): `pacientes`, `citas`,
  `odontogramas`, `presupuestos`, `recetas`, `facturacion`, `dashboards`, `notificaciones`.
- `POST /clinicas` es atómico: si falla cualquier paso, no debe quedar una `Clinica` huérfana sin
  admin ni módulos.
- `correo` en los requests usa `pydantic.EmailStr`, no una regex hecha a mano.
- `admin_username` duplicado → `409 Conflict` (nueva excepción `UsernameYaExisteError`).
- El backend **no** bloquea otros endpoints mientras `debe_cambiar_password == True` — es
  responsabilidad del frontend redirigir. Solo se expone el flag en `/auth/login` y `/auth/me`.
- Fuera de alcance: `ConfiguracionClinica`/`Especialidad`/`Consultorio` (Módulo 3), dashboards
  (Módulo 7), reset de password perdida.

Todos los comandos se ejecutan con `backend/` como directorio de trabajo, usando el venv ya
creado en el Módulo 1 (`.venv/Scripts/python.exe`).

---

## File Structure

```
backend/
  requirements.txt                              (modify: + email-validator)
  alembic/versions/
    0002_usuario_debe_cambiar_password.py        (create)
  app/
    models/
      usuario.py                                 (modify: + debe_cambiar_password)
    exceptions.py                                 (modify: + UsernameYaExisteError)
    security/
      passwords.py                                (modify: + generar_password_temporal)
    repositories/
      clinica_repository.py                       (create)
      clinica_modulo_repository.py                (create)
    services/
      auth_service.py                             (modify: + cambiar_password)
      clinica_service.py                          (create)
    schemas/
      auth.py                                     (modify: + debe_cambiar_password, CambiarPasswordRequest)
      clinica.py                                   (create)
    api/routes/
      auth.py                                      (modify: + POST /auth/cambiar-password)
      clinicas.py                                   (create)
    main.py                                        (modify: registra router de clinicas)
  tests/
    test_models.py                                 (modify: + test debe_cambiar_password)
    test_passwords.py                              (modify: + tests password temporal)
    test_clinica_schemas.py                        (create)
    test_clinica_repository.py                     (create)
    test_clinica_modulo_repository.py              (create)
    test_clinica_service.py                        (create)
    test_auth_service.py                           (modify: + tests cambiar_password)
    test_auth_routes.py                            (modify: + tests /auth/cambiar-password)
    test_clinicas_routes.py                        (create)
```

---

### Task 1: `Usuario.debe_cambiar_password` + migración

**Files:**
- Modify: `backend/app/models/usuario.py`
- Modify: `backend/tests/test_models.py`
- Create: `backend/alembic/versions/0002_usuario_debe_cambiar_password.py`

**Interfaces:**
- Produces: `Usuario.debe_cambiar_password: bool` (default `True`), usado por Task 6 (servicio)
  y Task 7 (auth service / schemas).

- [ ] **Step 1: Escribir el test (falla primero)**

Agregar al final de `backend/tests/test_models.py`:

```python
def test_usuario_debe_cambiar_password_por_defecto(db_session):
    from app.models import RolUsuario, Usuario

    usuario = Usuario(
        id_clinica=None,
        username="nuevo.usuario",
        password_hash="hash",
        rol=RolUsuario.ADMIN,
    )
    db_session.add(usuario)
    db_session.commit()

    assert usuario.debe_cambiar_password is True
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_models.py -v`
Expected: FAIL con `AttributeError: 'Usuario' object has no attribute 'debe_cambiar_password'`

- [ ] **Step 3: Modificar `app/models/usuario.py`**

Reemplazar el bloque de columnas de la clase `Usuario` (desde `activo` hasta `created_at`) por:

```python
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    debe_cambiar_password: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 4: Ejecutar el test y verificar que pasa**

Run: `.venv/Scripts/python.exe -m pytest tests/test_models.py -v`
Expected: `3 passed`

- [ ] **Step 5: Escribir la migración**

`backend/alembic/versions/0002_usuario_debe_cambiar_password.py`:

```python
"""agrega debe_cambiar_password a usuario

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-31
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "usuario",
        sa.Column(
            "debe_cambiar_password",
            sa.Boolean(),
            nullable=False,
            server_default="1",
        ),
    )


def downgrade() -> None:
    op.drop_column("usuario", "debe_cambiar_password")
```

- [ ] **Step 6: Verificar que la migración es válida**

Run: `.venv/Scripts/python.exe -m alembic history --verbose`
Expected: muestra `0002 (head)` con `Revises: 0001`, sin errores de sintaxis.

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/usuario.py backend/tests/test_models.py backend/alembic/versions/0002_usuario_debe_cambiar_password.py
git commit -m "feat(backend): agrega debe_cambiar_password a Usuario"
```

---

### Task 2: `email-validator` + schemas de `Clinica`

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/app/schemas/clinica.py`
- Create: `backend/tests/test_clinica_schemas.py`

**Interfaces:**
- Consumes: `app.models.EstadoClinica`.
- Produces: `ClinicaCreateRequest`, `ClinicaResponse`, `AdminCreadoResponse`,
  `ClinicaCreateResponse`, `ClinicaUpdateRequest`, `EstadoUpdateRequest`, `ModuloUpdateRequest`
  (usados por Task 9, rutas).

- [ ] **Step 1: Agregar la dependencia e instalarla**

Agregar a `backend/requirements.txt` (después de `pydantic-settings`):

```
email-validator>=2.0,<3.0
```

Run: `.venv/Scripts/python.exe -m pip install email-validator>=2.0,<3.0`
Expected: `Successfully installed email-validator-...`

- [ ] **Step 2: Escribir el test (falla primero)**

`backend/tests/test_clinica_schemas.py`:

```python
import pytest
from pydantic import ValidationError


def test_clinica_create_request_rechaza_correo_invalido():
    from app.schemas.clinica import ClinicaCreateRequest

    with pytest.raises(ValidationError):
        ClinicaCreateRequest(
            nombre="Dental Test",
            admin_username="admin.test",
            correo="no-es-un-correo",
        )


def test_clinica_create_request_acepta_correo_valido():
    from app.schemas.clinica import ClinicaCreateRequest

    request = ClinicaCreateRequest(
        nombre="Dental Test",
        admin_username="admin.test",
        correo="contacto@dentaltest.com",
    )

    assert request.correo == "contacto@dentaltest.com"


def test_clinica_create_request_correo_es_opcional():
    from app.schemas.clinica import ClinicaCreateRequest

    request = ClinicaCreateRequest(nombre="Dental Test", admin_username="admin.test")

    assert request.correo is None
```

- [ ] **Step 3: Ejecutar el test y verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_clinica_schemas.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.schemas.clinica'`

- [ ] **Step 4: Implementar `app/schemas/clinica.py`**

```python
from pydantic import BaseModel, EmailStr

from app.models import EstadoClinica


class ClinicaCreateRequest(BaseModel):
    nombre: str
    direccion: str | None = None
    telefono: str | None = None
    correo: EmailStr | None = None
    admin_username: str


class ClinicaResponse(BaseModel):
    id_clinica: int
    nombre: str
    direccion: str | None
    telefono: str | None
    correo: str | None
    estado: EstadoClinica

    model_config = {"from_attributes": True}


class AdminCreadoResponse(BaseModel):
    id_usuario: int
    username: str

    model_config = {"from_attributes": True}


class ClinicaCreateResponse(BaseModel):
    clinica: ClinicaResponse
    admin: AdminCreadoResponse
    password_temporal: str


class ClinicaUpdateRequest(BaseModel):
    nombre: str | None = None
    direccion: str | None = None
    telefono: str | None = None
    correo: EmailStr | None = None


class EstadoUpdateRequest(BaseModel):
    estado: EstadoClinica


class ModuloUpdateRequest(BaseModel):
    habilitado: bool
```

- [ ] **Step 5: Ejecutar el test y verificar que pasa**

Run: `.venv/Scripts/python.exe -m pytest tests/test_clinica_schemas.py -v`
Expected: `3 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/requirements.txt backend/app/schemas/clinica.py backend/tests/test_clinica_schemas.py
git commit -m "feat(backend): schemas de Clinica con validacion de correo"
```

---

### Task 3: `ClinicaRepository`

**Files:**
- Create: `backend/app/repositories/clinica_repository.py`
- Create: `backend/tests/test_clinica_repository.py`

**Interfaces:**
- Consumes: `app.models.Clinica`, `app.models.EstadoClinica`.
- Produces: `ClinicaRepository.listar(estado: EstadoClinica | None = None) -> list[Clinica]`,
  `.obtener(id_clinica: int) -> Clinica | None`, `.crear(data: dict) -> Clinica`,
  `.actualizar(id_clinica: int, data: dict) -> Clinica | None`,
  `.cambiar_estado(id_clinica: int, estado: EstadoClinica) -> Clinica | None`.
  Usado por Task 6 (`ClinicaService`) y Task 9 (rutas).

- [ ] **Step 1: Escribir el test (falla primero)**

`backend/tests/test_clinica_repository.py`:

```python
def test_crear_y_obtener(db_session):
    from app.repositories.clinica_repository import ClinicaRepository

    repo = ClinicaRepository(db_session)
    clinica = repo.crear({"nombre": "Dental Uno"})
    db_session.commit()

    encontrada = repo.obtener(clinica.id_clinica)

    assert encontrada is not None
    assert encontrada.nombre == "Dental Uno"


def test_obtener_inexistente_devuelve_none(db_session):
    from app.repositories.clinica_repository import ClinicaRepository

    repo = ClinicaRepository(db_session)

    assert repo.obtener(999) is None


def test_listar_todas(db_session):
    from app.repositories.clinica_repository import ClinicaRepository

    repo = ClinicaRepository(db_session)
    repo.crear({"nombre": "Dental Uno"})
    repo.crear({"nombre": "Dental Dos"})
    db_session.commit()

    todas = repo.listar()

    assert len(todas) == 2


def test_listar_filtra_por_estado(db_session):
    from app.models import EstadoClinica
    from app.repositories.clinica_repository import ClinicaRepository

    repo = ClinicaRepository(db_session)
    activa = repo.crear({"nombre": "Dental Activa"})
    suspendida = repo.crear({"nombre": "Dental Suspendida", "estado": EstadoClinica.SUSPENDIDA})
    db_session.commit()

    solo_activas = repo.listar(EstadoClinica.ACTIVA)

    assert [c.id_clinica for c in solo_activas] == [activa.id_clinica]
    assert suspendida.id_clinica not in [c.id_clinica for c in solo_activas]


def test_actualizar_campos(db_session):
    from app.repositories.clinica_repository import ClinicaRepository

    repo = ClinicaRepository(db_session)
    clinica = repo.crear({"nombre": "Dental Original"})
    db_session.commit()

    actualizada = repo.actualizar(clinica.id_clinica, {"nombre": "Dental Renombrada"})
    db_session.commit()

    assert actualizada.nombre == "Dental Renombrada"


def test_cambiar_estado(db_session):
    from app.models import EstadoClinica
    from app.repositories.clinica_repository import ClinicaRepository

    repo = ClinicaRepository(db_session)
    clinica = repo.crear({"nombre": "Dental Uno"})
    db_session.commit()

    actualizada = repo.cambiar_estado(clinica.id_clinica, EstadoClinica.SUSPENDIDA)
    db_session.commit()

    assert actualizada.estado == EstadoClinica.SUSPENDIDA
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_clinica_repository.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.repositories.clinica_repository'`

- [ ] **Step 3: Implementar `app/repositories/clinica_repository.py`**

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Clinica, EstadoClinica


class ClinicaRepository:
    """Repositorio de plataforma: Clinica es la unidad de tenancy en si misma,
    por lo que sus metodos NO reciben id_clinica como filtro (a diferencia de
    BaseRepository, pensado para recursos DENTRO de una clinica).
    """

    def __init__(self, db: Session):
        self.db = db

    def listar(self, estado: EstadoClinica | None = None) -> list[Clinica]:
        stmt = select(Clinica)
        if estado is not None:
            stmt = stmt.where(Clinica.estado == estado)
        return list(self.db.execute(stmt).scalars().all())

    def obtener(self, id_clinica: int) -> Clinica | None:
        return self.db.get(Clinica, id_clinica)

    def crear(self, data: dict) -> Clinica:
        clinica = Clinica(**data)
        self.db.add(clinica)
        self.db.flush()
        return clinica

    def actualizar(self, id_clinica: int, data: dict) -> Clinica | None:
        clinica = self.obtener(id_clinica)
        if clinica is None:
            return None
        for campo, valor in data.items():
            setattr(clinica, campo, valor)
        self.db.flush()
        return clinica

    def cambiar_estado(self, id_clinica: int, estado: EstadoClinica) -> Clinica | None:
        clinica = self.obtener(id_clinica)
        if clinica is None:
            return None
        clinica.estado = estado
        self.db.flush()
        return clinica
```

- [ ] **Step 4: Ejecutar el test y verificar que pasa**

Run: `.venv/Scripts/python.exe -m pytest tests/test_clinica_repository.py -v`
Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/repositories/clinica_repository.py backend/tests/test_clinica_repository.py
git commit -m "feat(backend): ClinicaRepository"
```

---

### Task 4: `ClinicaModuloRepository`

**Files:**
- Create: `backend/app/repositories/clinica_modulo_repository.py`
- Create: `backend/tests/test_clinica_modulo_repository.py`

**Interfaces:**
- Consumes: `app.models.ClinicaModulo`.
- Produces: `MODULOS_DISPONIBLES: list[str]` (8 strings),
  `ClinicaModuloRepository.sembrar_modulos_default(id_clinica: int) -> None`,
  `.listar(id_clinica: int) -> list[ClinicaModulo]`,
  `.actualizar_estado(id_clinica: int, modulo: str, habilitado: bool) -> ClinicaModulo | None`.
  Usado por Task 6 (`ClinicaService`) y Task 9 (rutas).

- [ ] **Step 1: Escribir el test (falla primero)**

`backend/tests/test_clinica_modulo_repository.py`:

```python
def _crear_clinica(db_session, nombre="Dental Uno"):
    from app.models import Clinica

    clinica = Clinica(nombre=nombre)
    db_session.add(clinica)
    db_session.flush()
    return clinica


def test_sembrar_modulos_default_crea_8_filas_habilitadas(db_session):
    from app.repositories.clinica_modulo_repository import (
        MODULOS_DISPONIBLES,
        ClinicaModuloRepository,
    )

    clinica = _crear_clinica(db_session)
    repo = ClinicaModuloRepository(db_session)

    repo.sembrar_modulos_default(clinica.id_clinica)
    db_session.commit()

    modulos = repo.listar(clinica.id_clinica)

    assert len(modulos) == 8
    assert len(MODULOS_DISPONIBLES) == 8
    assert all(m.habilitado is True for m in modulos)
    assert {m.modulo for m in modulos} == set(MODULOS_DISPONIBLES)


def test_listar_solo_los_de_esa_clinica(db_session):
    from app.repositories.clinica_modulo_repository import ClinicaModuloRepository

    clinica_a = _crear_clinica(db_session, "Dental A")
    clinica_b = _crear_clinica(db_session, "Dental B")
    repo = ClinicaModuloRepository(db_session)

    repo.sembrar_modulos_default(clinica_a.id_clinica)
    repo.sembrar_modulos_default(clinica_b.id_clinica)
    db_session.commit()

    modulos_a = repo.listar(clinica_a.id_clinica)

    assert len(modulos_a) == 8
    assert all(m.id_clinica == clinica_a.id_clinica for m in modulos_a)


def test_actualizar_estado_deshabilita_modulo(db_session):
    from app.repositories.clinica_modulo_repository import ClinicaModuloRepository

    clinica = _crear_clinica(db_session)
    repo = ClinicaModuloRepository(db_session)
    repo.sembrar_modulos_default(clinica.id_clinica)
    db_session.commit()

    actualizado = repo.actualizar_estado(clinica.id_clinica, "recetas", False)
    db_session.commit()

    assert actualizado.habilitado is False


def test_actualizar_estado_modulo_inexistente_devuelve_none(db_session):
    from app.repositories.clinica_modulo_repository import ClinicaModuloRepository

    clinica = _crear_clinica(db_session)
    repo = ClinicaModuloRepository(db_session)

    assert repo.actualizar_estado(clinica.id_clinica, "no-existe", False) is None
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_clinica_modulo_repository.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.repositories.clinica_modulo_repository'`

- [ ] **Step 3: Implementar `app/repositories/clinica_modulo_repository.py`**

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ClinicaModulo

MODULOS_DISPONIBLES = [
    "pacientes",
    "citas",
    "odontogramas",
    "presupuestos",
    "recetas",
    "facturacion",
    "dashboards",
    "notificaciones",
]


class ClinicaModuloRepository:
    """No hereda de BaseRepository: la llave de ClinicaModulo es compuesta
    (id_clinica + modulo, un string), no un int como asume BaseRepository.
    Igual exige id_clinica como primer parametro en todos sus metodos.
    """

    def __init__(self, db: Session):
        self.db = db

    def sembrar_modulos_default(self, id_clinica: int) -> None:
        for modulo in MODULOS_DISPONIBLES:
            self.db.add(
                ClinicaModulo(id_clinica=id_clinica, modulo=modulo, habilitado=True)
            )
        self.db.flush()

    def listar(self, id_clinica: int) -> list[ClinicaModulo]:
        stmt = select(ClinicaModulo).where(ClinicaModulo.id_clinica == id_clinica)
        return list(self.db.execute(stmt).scalars().all())

    def actualizar_estado(
        self, id_clinica: int, modulo: str, habilitado: bool
    ) -> ClinicaModulo | None:
        registro = self.db.get(ClinicaModulo, (id_clinica, modulo))
        if registro is None:
            return None
        registro.habilitado = habilitado
        self.db.flush()
        return registro
```

- [ ] **Step 4: Ejecutar el test y verificar que pasa**

Run: `.venv/Scripts/python.exe -m pytest tests/test_clinica_modulo_repository.py -v`
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/repositories/clinica_modulo_repository.py backend/tests/test_clinica_modulo_repository.py
git commit -m "feat(backend): ClinicaModuloRepository con feature flags por clinica"
```

---

### Task 5: Generar password temporal

**Files:**
- Modify: `backend/app/security/passwords.py`
- Modify: `backend/tests/test_passwords.py`

**Interfaces:**
- Produces: `app.security.passwords.generar_password_temporal() -> str`. Usado por Task 6
  (`ClinicaService`).

- [ ] **Step 1: Escribir el test (falla primero)**

Agregar al final de `backend/tests/test_passwords.py`:

```python
def test_generar_password_temporal_tiene_longitud_razonable():
    from app.security.passwords import generar_password_temporal

    password = generar_password_temporal()

    assert isinstance(password, str)
    assert len(password) >= 12


def test_generar_password_temporal_no_repite_valores():
    from app.security.passwords import generar_password_temporal

    generadas = {generar_password_temporal() for _ in range(20)}

    assert len(generadas) == 20
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_passwords.py -v`
Expected: FAIL con `ImportError: cannot import name 'generar_password_temporal'`

- [ ] **Step 3: Implementar en `app/security/passwords.py`**

Agregar al inicio del archivo (junto a los demás imports) y al final:

```python
import secrets

from passlib.context import CryptContext
```

```python
def generar_password_temporal() -> str:
    return secrets.token_urlsafe(12)
```

- [ ] **Step 4: Ejecutar el test y verificar que pasa**

Run: `.venv/Scripts/python.exe -m pytest tests/test_passwords.py -v`
Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/security/passwords.py backend/tests/test_passwords.py
git commit -m "feat(backend): genera passwords temporales seguras"
```

---

### Task 6: `ClinicaService` (crea clínica + módulos + admin, atómico)

**Files:**
- Modify: `backend/app/exceptions.py`
- Create: `backend/app/services/clinica_service.py`
- Create: `backend/tests/test_clinica_service.py`

**Interfaces:**
- Consumes: `ClinicaRepository`, `ClinicaModuloRepository`, `UsuarioRepository`,
  `generar_password_temporal`, `hash_password`.
- Produces: `app.exceptions.UsernameYaExisteError`,
  `ClinicaService.crear_clinica_con_admin(nombre: str, admin_username: str, direccion: str | None = None, telefono: str | None = None, correo: str | None = None) -> dict`
  con claves `clinica` (`Clinica`), `admin` (`Usuario`), `password_temporal` (`str`). Usado por
  Task 9 (rutas).

- [ ] **Step 1: Escribir el test (falla primero)**

`backend/tests/test_clinica_service.py`:

```python
import pytest


def test_crear_clinica_con_admin_devuelve_todo(db_session):
    from app.services.clinica_service import ClinicaService

    resultado = ClinicaService(db_session).crear_clinica_con_admin(
        nombre="Dental Smiling", admin_username="admin.dentalsmiling"
    )

    assert resultado["clinica"].nombre == "Dental Smiling"
    assert resultado["admin"].username == "admin.dentalsmiling"
    assert resultado["admin"].debe_cambiar_password is True
    assert isinstance(resultado["password_temporal"], str)
    assert len(resultado["password_temporal"]) >= 12


def test_crear_clinica_con_admin_siembra_8_modulos_habilitados(db_session):
    from app.repositories.clinica_modulo_repository import ClinicaModuloRepository
    from app.services.clinica_service import ClinicaService

    resultado = ClinicaService(db_session).crear_clinica_con_admin(
        nombre="Dental Smiling", admin_username="admin.dentalsmiling"
    )

    modulos = ClinicaModuloRepository(db_session).listar(resultado["clinica"].id_clinica)

    assert len(modulos) == 8
    assert all(m.habilitado is True for m in modulos)


def test_crear_clinica_con_admin_password_es_verificable(db_session):
    from app.security.passwords import verify_password
    from app.services.clinica_service import ClinicaService

    resultado = ClinicaService(db_session).crear_clinica_con_admin(
        nombre="Dental Smiling", admin_username="admin.dentalsmiling"
    )

    assert verify_password(resultado["password_temporal"], resultado["admin"].password_hash)


def test_crear_clinica_con_admin_username_duplicado_lanza_error(db_session):
    from app.exceptions import UsernameYaExisteError
    from app.services.clinica_service import ClinicaService

    ClinicaService(db_session).crear_clinica_con_admin(
        nombre="Dental Uno", admin_username="admin.repetido"
    )

    with pytest.raises(UsernameYaExisteError):
        ClinicaService(db_session).crear_clinica_con_admin(
            nombre="Dental Dos", admin_username="admin.repetido"
        )


def test_crear_clinica_con_admin_hace_rollback_si_falla(db_session, monkeypatch):
    from app.repositories.clinica_repository import ClinicaRepository
    import app.services.clinica_service as clinica_service_module

    def _falla(*args, **kwargs):
        raise RuntimeError("fallo simulado")

    monkeypatch.setattr(clinica_service_module, "generar_password_temporal", _falla)

    with pytest.raises(RuntimeError):
        clinica_service_module.ClinicaService(db_session).crear_clinica_con_admin(
            nombre="Dental Que No Debe Quedar", admin_username="admin.fallido"
        )

    assert ClinicaRepository(db_session).listar() == []
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_clinica_service.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.services.clinica_service'`

- [ ] **Step 3: Agregar la excepción en `app/exceptions.py`**

Agregar al final del archivo:

```python
class UsernameYaExisteError(Exception):
    """Ya existe un Usuario con ese username."""
```

- [ ] **Step 4: Implementar `app/services/clinica_service.py`**

```python
from sqlalchemy.orm import Session

from app.exceptions import UsernameYaExisteError
from app.models import RolUsuario, Usuario
from app.repositories.clinica_modulo_repository import ClinicaModuloRepository
from app.repositories.clinica_repository import ClinicaRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.security.passwords import generar_password_temporal, hash_password


class ClinicaService:
    def __init__(self, db: Session):
        self.db = db
        self.clinicas = ClinicaRepository(db)
        self.modulos = ClinicaModuloRepository(db)
        self.usuarios = UsuarioRepository(db)

    def crear_clinica_con_admin(
        self,
        nombre: str,
        admin_username: str,
        direccion: str | None = None,
        telefono: str | None = None,
        correo: str | None = None,
    ) -> dict:
        if self.usuarios.obtener_por_username(admin_username) is not None:
            raise UsernameYaExisteError()

        try:
            clinica = self.clinicas.crear(
                {
                    "nombre": nombre,
                    "direccion": direccion,
                    "telefono": telefono,
                    "correo": correo,
                }
            )
            self.modulos.sembrar_modulos_default(clinica.id_clinica)

            password_temporal = generar_password_temporal()
            admin = Usuario(
                id_clinica=clinica.id_clinica,
                username=admin_username,
                password_hash=hash_password(password_temporal),
                rol=RolUsuario.ADMIN,
                debe_cambiar_password=True,
            )
            self.db.add(admin)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return {
            "clinica": clinica,
            "admin": admin,
            "password_temporal": password_temporal,
        }
```

- [ ] **Step 5: Ejecutar el test y verificar que pasa**

Run: `.venv/Scripts/python.exe -m pytest tests/test_clinica_service.py -v`
Expected: `5 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/app/exceptions.py backend/app/services/clinica_service.py backend/tests/test_clinica_service.py
git commit -m "feat(backend): ClinicaService crea clinica+modulos+admin de forma atomica"
```

---

### Task 7: `AuthService.cambiar_password` + exponer `debe_cambiar_password`

**Files:**
- Modify: `backend/app/services/auth_service.py`
- Modify: `backend/app/schemas/auth.py`
- Modify: `backend/tests/test_auth_service.py`

**Interfaces:**
- Consumes: `verify_password`, `hash_password` (ya existentes desde Módulo 1).
- Produces: `AuthService.cambiar_password(usuario: Usuario, password_actual: str, password_nueva: str) -> None`
  (lanza `InvalidCredentialsError` si `password_actual` no coincide). `UsuarioResponse` ahora
  incluye `debe_cambiar_password: bool`. Nuevo schema `CambiarPasswordRequest`. Usado por Task 8
  (endpoint).

- [ ] **Step 1: Escribir el test (falla primero)**

Agregar al final de `backend/tests/test_auth_service.py`:

```python
def test_cambiar_password_exitoso_actualiza_hash_y_flag(db_session):
    from app.models import RolUsuario
    from app.security.passwords import verify_password
    from app.services.auth_service import AuthService

    clinica = _crear_clinica_activa(db_session)
    usuario = _crear_usuario(db_session, clinica, "admin.dental", RolUsuario.ADMIN)

    AuthService(db_session).cambiar_password(usuario, "clave123", "clave-nueva-456")

    assert usuario.debe_cambiar_password is False
    assert verify_password("clave-nueva-456", usuario.password_hash)


def test_cambiar_password_con_actual_incorrecta_lanza_invalid_credentials(db_session):
    from app.exceptions import InvalidCredentialsError
    from app.models import RolUsuario
    from app.services.auth_service import AuthService

    clinica = _crear_clinica_activa(db_session)
    usuario = _crear_usuario(db_session, clinica, "admin.dental", RolUsuario.ADMIN)

    with pytest.raises(InvalidCredentialsError):
        AuthService(db_session).cambiar_password(usuario, "clave-equivocada", "clave-nueva")
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_auth_service.py -v`
Expected: FAIL con `AttributeError: 'AuthService' object has no attribute 'cambiar_password'`

- [ ] **Step 3: Modificar `app/services/auth_service.py`**

Cambiar la línea de import de passwords:

```python
from app.security.passwords import hash_password, verify_password
```

Agregar el método a la clase `AuthService` (después de `login`):

```python
    def cambiar_password(
        self, usuario, password_actual: str, password_nueva: str
    ) -> None:
        if not verify_password(password_actual, usuario.password_hash):
            raise InvalidCredentialsError()
        usuario.password_hash = hash_password(password_nueva)
        usuario.debe_cambiar_password = False
        self.db.commit()
```

- [ ] **Step 4: Ejecutar el test y verificar que pasa**

Run: `.venv/Scripts/python.exe -m pytest tests/test_auth_service.py -v`
Expected: `7 passed`

- [ ] **Step 5: Modificar `app/schemas/auth.py`**

Reemplazar la clase `UsuarioResponse` y agregar `CambiarPasswordRequest`:

```python
class UsuarioResponse(BaseModel):
    id_usuario: int
    username: str
    rol: str
    id_clinica: int | None
    debe_cambiar_password: bool

    model_config = {"from_attributes": True}


class CambiarPasswordRequest(BaseModel):
    password_actual: str
    password_nueva: str
```

- [ ] **Step 6: Confirmar que las rutas de auth existentes siguen pasando**

Run: `.venv/Scripts/python.exe -m pytest tests/test_auth_routes.py -v`
Expected: `5 passed` (el campo nuevo en `UsuarioResponse` no rompe los tests existentes, que no
verifican ausencia de campos extra).

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/auth_service.py backend/app/schemas/auth.py backend/tests/test_auth_service.py
git commit -m "feat(backend): AuthService.cambiar_password y flag debe_cambiar_password"
```

---

### Task 8: Endpoint `POST /auth/cambiar-password`

**Files:**
- Modify: `backend/app/api/routes/auth.py`
- Modify: `backend/tests/test_auth_routes.py`

**Interfaces:**
- Consumes: `AuthService.cambiar_password`, `CambiarPasswordRequest`, `get_current_user`.
- Produces: endpoint `POST /auth/cambiar-password`.

- [ ] **Step 1: Escribir los tests (fallan primero)**

Agregar al final de `backend/tests/test_auth_routes.py`:

```python
def test_login_expone_debe_cambiar_password(client, db_session):
    _crear_clinica_y_admin(db_session)

    respuesta = client.post(
        "/auth/login", json={"username": "admin.dental", "password": "clave123"}
    )

    assert respuesta.json()["usuario"]["debe_cambiar_password"] is True


def test_cambiar_password_exitoso(client, db_session):
    _crear_clinica_y_admin(db_session)
    login = client.post(
        "/auth/login", json={"username": "admin.dental", "password": "clave123"}
    )
    token = login.json()["access_token"]

    respuesta = client.post(
        "/auth/cambiar-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"password_actual": "clave123", "password_nueva": "clave-nueva-456"},
    )

    assert respuesta.status_code == 200

    segundo_login = client.post(
        "/auth/login", json={"username": "admin.dental", "password": "clave-nueva-456"}
    )
    assert segundo_login.status_code == 200
    assert segundo_login.json()["usuario"]["debe_cambiar_password"] is False


def test_cambiar_password_actual_incorrecta_devuelve_401(client, db_session):
    _crear_clinica_y_admin(db_session)
    login = client.post(
        "/auth/login", json={"username": "admin.dental", "password": "clave123"}
    )
    token = login.json()["access_token"]

    respuesta = client.post(
        "/auth/cambiar-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"password_actual": "mala-clave", "password_nueva": "clave-nueva"},
    )

    assert respuesta.status_code == 401
```

- [ ] **Step 2: Ejecutar los tests y verificar que fallan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_auth_routes.py -v`
Expected: FAIL — `test_cambiar_password_exitoso` y
`test_cambiar_password_actual_incorrecta_devuelve_401` con `404 Not Found` (la ruta no existe
todavía); `test_login_expone_debe_cambiar_password` ya pasa desde el Task 7.

- [ ] **Step 3: Modificar `app/api/routes/auth.py`**

Agregar al import de schemas:

```python
from app.schemas.auth import CambiarPasswordRequest, LoginRequest, TokenResponse, UsuarioResponse
```

Agregar la ruta al final del archivo:

```python
@router.post("/cambiar-password")
def cambiar_password(
    body: CambiarPasswordRequest,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        AuthService(db).cambiar_password(usuario, body.password_actual, body.password_nueva)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La contrasena actual no es correcta",
        )
    return {"detail": "Contrasena actualizada"}
```

- [ ] **Step 4: Ejecutar los tests y verificar que pasan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_auth_routes.py -v`
Expected: `8 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/auth.py backend/tests/test_auth_routes.py
git commit -m "feat(backend): endpoint POST /auth/cambiar-password"
```

---

### Task 9: Rutas `/clinicas` + registro en la app

**Files:**
- Create: `backend/app/api/routes/clinicas.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_clinicas_routes.py`

**Interfaces:**
- Consumes: `ClinicaService`, `ClinicaRepository`, `ClinicaModuloRepository`, `require_roles`,
  schemas de `app.schemas.clinica`.
- Produces: endpoints `POST /clinicas`, `GET /clinicas`, `GET /clinicas/{id_clinica}`,
  `PUT /clinicas/{id_clinica}`, `PATCH /clinicas/{id_clinica}/estado`,
  `PATCH /clinicas/{id_clinica}/modulos/{modulo}`.

- [ ] **Step 1: Escribir los tests (fallan primero)**

`backend/tests/test_clinicas_routes.py`:

```python
from datetime import timedelta


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


def _token_superadmin(db_session):
    from app.models import RolUsuario

    return _token_para(db_session, RolUsuario.SUPERADMIN, username="superadmin")


def test_crear_clinica_sin_token_devuelve_401(client):
    respuesta = client.post("/clinicas", json={"nombre": "Dental X", "admin_username": "x"})

    assert respuesta.status_code == 401


def test_crear_clinica_con_rol_no_superadmin_devuelve_403(client, db_session):
    from app.models import RolUsuario

    token = _token_para(db_session, RolUsuario.ADMIN, id_clinica=None, username="admin.normal")

    respuesta = client.post(
        "/clinicas",
        headers={"Authorization": f"Bearer {token}"},
        json={"nombre": "Dental X", "admin_username": "x"},
    )

    assert respuesta.status_code == 403


def test_crear_clinica_exitoso(client, db_session):
    token = _token_superadmin(db_session)

    respuesta = client.post(
        "/clinicas",
        headers={"Authorization": f"Bearer {token}"},
        json={"nombre": "Dental Smiling", "admin_username": "admin.dentalsmiling"},
    )

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["clinica"]["nombre"] == "Dental Smiling"
    assert cuerpo["clinica"]["estado"] == "activa"
    assert cuerpo["admin"]["username"] == "admin.dentalsmiling"
    assert len(cuerpo["password_temporal"]) >= 12


def test_crear_clinica_username_duplicado_devuelve_409(client, db_session):
    token = _token_superadmin(db_session)
    client.post(
        "/clinicas",
        headers={"Authorization": f"Bearer {token}"},
        json={"nombre": "Dental Uno", "admin_username": "admin.repetido"},
    )

    respuesta = client.post(
        "/clinicas",
        headers={"Authorization": f"Bearer {token}"},
        json={"nombre": "Dental Dos", "admin_username": "admin.repetido"},
    )

    assert respuesta.status_code == 409


def test_listar_clinicas(client, db_session):
    token = _token_superadmin(db_session)
    client.post(
        "/clinicas",
        headers={"Authorization": f"Bearer {token}"},
        json={"nombre": "Dental Uno", "admin_username": "admin.uno"},
    )

    respuesta = client.get("/clinicas", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 1


def test_obtener_clinica_inexistente_devuelve_404(client, db_session):
    token = _token_superadmin(db_session)

    respuesta = client.get("/clinicas/999", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 404


def test_actualizar_clinica(client, db_session):
    token = _token_superadmin(db_session)
    creada = client.post(
        "/clinicas",
        headers={"Authorization": f"Bearer {token}"},
        json={"nombre": "Dental Original", "admin_username": "admin.original"},
    ).json()

    respuesta = client.put(
        f"/clinicas/{creada['clinica']['id_clinica']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"nombre": "Dental Renombrada"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Dental Renombrada"


def test_cambiar_estado_clinica(client, db_session):
    token = _token_superadmin(db_session)
    creada = client.post(
        "/clinicas",
        headers={"Authorization": f"Bearer {token}"},
        json={"nombre": "Dental Uno", "admin_username": "admin.uno"},
    ).json()

    respuesta = client.patch(
        f"/clinicas/{creada['clinica']['id_clinica']}/estado",
        headers={"Authorization": f"Bearer {token}"},
        json={"estado": "suspendida"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "suspendida"


def test_actualizar_modulo_deshabilita(client, db_session):
    token = _token_superadmin(db_session)
    creada = client.post(
        "/clinicas",
        headers={"Authorization": f"Bearer {token}"},
        json={"nombre": "Dental Uno", "admin_username": "admin.uno"},
    ).json()

    respuesta = client.patch(
        f"/clinicas/{creada['clinica']['id_clinica']}/modulos/recetas",
        headers={"Authorization": f"Bearer {token}"},
        json={"habilitado": False},
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"modulo": "recetas", "habilitado": False}


def test_actualizar_modulo_inexistente_devuelve_404(client, db_session):
    token = _token_superadmin(db_session)
    creada = client.post(
        "/clinicas",
        headers={"Authorization": f"Bearer {token}"},
        json={"nombre": "Dental Uno", "admin_username": "admin.uno"},
    ).json()

    respuesta = client.patch(
        f"/clinicas/{creada['clinica']['id_clinica']}/modulos/no-existe",
        headers={"Authorization": f"Bearer {token}"},
        json={"habilitado": False},
    )

    assert respuesta.status_code == 404
```

- [ ] **Step 2: Ejecutar los tests y verificar que fallan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_clinicas_routes.py -v`
Expected: FAIL — todas con `404 Not Found` (el router de `/clinicas` no existe todavía, y
`test_crear_clinica_sin_token_devuelve_401` también falla porque FastAPI devuelve 404 antes de
evaluar auth para una ruta que no existe).

- [ ] **Step 3: Implementar `app/api/routes/clinicas.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db import get_db
from app.exceptions import UsernameYaExisteError
from app.models import EstadoClinica, RolUsuario
from app.repositories.clinica_modulo_repository import ClinicaModuloRepository
from app.repositories.clinica_repository import ClinicaRepository
from app.schemas.clinica import (
    ClinicaCreateRequest,
    ClinicaCreateResponse,
    ClinicaResponse,
    ClinicaUpdateRequest,
    EstadoUpdateRequest,
    ModuloUpdateRequest,
)
from app.services.clinica_service import ClinicaService

router = APIRouter(
    prefix="/clinicas",
    tags=["clinicas"],
    dependencies=[Depends(require_roles(RolUsuario.SUPERADMIN))],
)


@router.post("", response_model=ClinicaCreateResponse, status_code=status.HTTP_201_CREATED)
def crear_clinica(
    body: ClinicaCreateRequest, db: Session = Depends(get_db)
) -> ClinicaCreateResponse:
    try:
        resultado = ClinicaService(db).crear_clinica_con_admin(
            nombre=body.nombre,
            admin_username=body.admin_username,
            direccion=body.direccion,
            telefono=body.telefono,
            correo=body.correo,
        )
    except UsernameYaExisteError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese username",
        )
    return ClinicaCreateResponse(
        clinica=ClinicaResponse.model_validate(resultado["clinica"]),
        admin=resultado["admin"],
        password_temporal=resultado["password_temporal"],
    )


@router.get("", response_model=list[ClinicaResponse])
def listar_clinicas(
    estado: EstadoClinica | None = None, db: Session = Depends(get_db)
) -> list[ClinicaResponse]:
    clinicas = ClinicaRepository(db).listar(estado)
    return [ClinicaResponse.model_validate(c) for c in clinicas]


@router.get("/{id_clinica}", response_model=ClinicaResponse)
def obtener_clinica(id_clinica: int, db: Session = Depends(get_db)) -> ClinicaResponse:
    clinica = ClinicaRepository(db).obtener(id_clinica)
    if clinica is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Clinica no encontrada"
        )
    return ClinicaResponse.model_validate(clinica)


@router.put("/{id_clinica}", response_model=ClinicaResponse)
def actualizar_clinica(
    id_clinica: int, body: ClinicaUpdateRequest, db: Session = Depends(get_db)
) -> ClinicaResponse:
    datos = body.model_dump(exclude_unset=True)
    clinica = ClinicaRepository(db).actualizar(id_clinica, datos)
    if clinica is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Clinica no encontrada"
        )
    db.commit()
    return ClinicaResponse.model_validate(clinica)


@router.patch("/{id_clinica}/estado", response_model=ClinicaResponse)
def cambiar_estado_clinica(
    id_clinica: int, body: EstadoUpdateRequest, db: Session = Depends(get_db)
) -> ClinicaResponse:
    clinica = ClinicaRepository(db).cambiar_estado(id_clinica, body.estado)
    if clinica is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Clinica no encontrada"
        )
    db.commit()
    return ClinicaResponse.model_validate(clinica)


@router.patch("/{id_clinica}/modulos/{modulo}")
def actualizar_modulo(
    id_clinica: int, modulo: str, body: ModuloUpdateRequest, db: Session = Depends(get_db)
) -> dict:
    registro = ClinicaModuloRepository(db).actualizar_estado(
        id_clinica, modulo, body.habilitado
    )
    if registro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Modulo no encontrado para esta clinica",
        )
    db.commit()
    return {"modulo": registro.modulo, "habilitado": registro.habilitado}
```

- [ ] **Step 4: Registrar el router en `app/main.py`**

Reemplazar el contenido completo de `backend/app/main.py`:

```python
from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.clinicas import router as clinicas_router

app = FastAPI(title="Clinica Dental Web API")
app.include_router(auth_router)
app.include_router(clinicas_router)
```

- [ ] **Step 5: Ejecutar los tests y verificar que pasan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_clinicas_routes.py -v`
Expected: `10 passed`

- [ ] **Step 6: Correr toda la suite del proyecto**

Run: `.venv/Scripts/python.exe -m pytest -v`
Expected: todos los tests (Módulo 1 + Módulo 2) pasan, sin regresiones.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/routes/clinicas.py backend/app/main.py backend/tests/test_clinicas_routes.py
git commit -m "feat(backend): endpoints CRUD de Clinica para el superadmin"
```

---

## Self-Review

**Cobertura del spec:**
- Migración + campo `debe_cambiar_password` → Task 1 ✅
- Schemas con `EmailStr` → Task 2 ✅
- `ClinicaRepository` sin heredar `BaseRepository` → Task 3 ✅ (documentado en el docstring)
- `ClinicaModuloRepository` sin heredar `BaseRepository`, `MODULOS_DISPONIBLES` como única fuente
  de verdad → Task 4 ✅
- Password temporal generada de forma segura → Task 5 ✅
- Creación atómica clínica+módulos+admin, con rollback en fallo, `UsernameYaExisteError` → 409 →
  Task 6 ✅ (rollback probado explícitamente con monkeypatch)
- `AuthService.cambiar_password`, flag expuesto en `/auth/me` y `/auth/login` → Task 7 ✅
- Endpoint `POST /auth/cambiar-password` → Task 8 ✅
- Endpoints CRUD de `/clinicas`, todos protegidos con `require_roles(SUPERADMIN)` → Task 9 ✅
- "No bloquear otros endpoints por `debe_cambiar_password`" → decisión respetada: ningún task
  agrega ese bloqueo.

**Placeholders:** revisado, no hay "TBD" ni pasos sin código real.

**Consistencia de tipos:** `ClinicaService.crear_clinica_con_admin` devuelve
`{"clinica": Clinica, "admin": Usuario, "password_temporal": str}` en Task 6, y Task 9 lo consume
exactamente con esas claves. `MODULOS_DISPONIBLES` se define una sola vez en Task 4 y Task 6 solo
lo usa indirectamente vía `ClinicaModuloRepository.sembrar_modulos_default` (no lo duplica).
`ClinicaRepository`/`ClinicaModuloRepository` firmas usadas en Task 9 coinciden exactamente con
las definidas en Task 3 y Task 4.
