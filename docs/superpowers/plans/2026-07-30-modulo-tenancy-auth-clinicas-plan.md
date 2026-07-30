# Módulo 1: Tenancy + Auth Core — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir el núcleo multi-tenant del backend nuevo (`Clinica`, `Usuario`, aislamiento
por clínica) con login vía JWT y contraseñas hasheadas, como base para todos los módulos
siguientes del sistema de administración de clínicas.

**Architecture:** FastAPI + SQLAlchemy 2.0 (ORM) + Alembic (migraciones) sobre MySQL, con capa
de repositorios que fuerza el filtro por `id_clinica`, un `AuthService` que emite JWT, y
dependencias de FastAPI (`app/api/deps.py`) que resuelven el usuario y la clínica actuales en
cada request.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2.0, Alembic, `mysql-connector-python`,
`passlib[bcrypt]`, `PyJWT`, `pydantic` v2 / `pydantic-settings`, `pytest`, `httpx` (TestClient).
Los tests usan SQLite en memoria (no requieren un MySQL corriendo) — es la única desviación
intencional del motor de producción, documentada en cada task.

## Global Constraints

- `Correo` usa `VARCHAR(100)` en toda tabla que lo tenga (spec: ERD to-be).
- Toda PK nueva es `INT AUTO_INCREMENT` (spec: decisiones de diseño).
- `Usuario.id_clinica` es `NULLABLE`; `NULL` significa rol `superadmin` (spec: sección 3).
- `Clinica.estado` es `ENUM('activa','suspendida','inactiva')`, default `'activa'` (spec: ERD to-be).
- Las contraseñas se guardan con `bcrypt`, nunca en texto plano (mejora crítica original).
- Las sesiones se manejan con JWT (mejora crítica original).
- Ningún repositorio de un recurso aislado por clínica puede exponer un método sin `id_clinica`
  como primer parámetro obligatorio (spec: sección 4, regla dura de diseño).
- Suspender/desactivar una clínica (`estado != 'activa'`) bloquea el login de todos sus usuarios
  de inmediato (spec: decisiones de diseño).
- Toda configuración sensible (credenciales de BD, secreto JWT) sale de variables de entorno /
  `.env`, nunca hardcodeada (mejora crítica original).
- Fuera de alcance de este plan: CRUD de clínicas (Módulo 2), `ConfiguracionClinica` /
  `Especialidad` / `Consultorio` (Módulo 3), migración de datos reales del legacy, blacklist de
  JWT, Docker/CI (se evalúan en una fase de infraestructura posterior, no en este módulo).

Todos los comandos de este plan se ejecutan con `backend/` como directorio de trabajo actual.

---

## File Structure

```
ClinicaDentalWeb/
  backend/
    requirements.txt
    .env.example
    pytest.ini
    alembic.ini
    alembic/
      env.py
      script.py.mako
      versions/
        0001_create_clinica_usuario.py
    app/
      __init__.py
      config.py
      db.py
      exceptions.py
      main.py
      models/
        __init__.py
        base.py
        clinica.py
        usuario.py
      security/
        __init__.py
        passwords.py
        jwt.py
      repositories/
        __init__.py
        base.py
        usuario_repository.py
      services/
        __init__.py
        auth_service.py
      schemas/
        __init__.py
        auth.py
      api/
        __init__.py
        deps.py
        routes/
          __init__.py
          auth.py
    tests/
      conftest.py
      test_config.py
      test_db.py
      test_models.py
      test_passwords.py
      test_jwt.py
      test_base_repository.py
      test_usuario_repository.py
      test_auth_service.py
      test_auth_routes.py
```

---

### Task 1: Scaffolding, configuración y sesión de BD

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/pytest.ini`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/db.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_config.py`
- Create: `backend/tests/test_db.py`

**Interfaces:**
- Produces: `app.config.settings` (instancia de `Settings`, atributos `db_host`, `db_port`,
  `db_user`, `db_password`, `db_name`, `jwt_secret_key`, `jwt_algorithm`, `jwt_expire_minutes`,
  property `database_url: str`).
- Produces: `app.db.get_db() -> Generator[Session, None, None]`, `app.db.engine`,
  `app.db.SessionLocal`.
- Produces: fixture `db_session` en `tests/conftest.py` (Session de SQLAlchemy sobre SQLite en
  memoria, usada por todas las tareas siguientes).

- [ ] **Step 1: Crear la estructura de carpetas y `requirements.txt`**

```bash
mkdir -p backend/app/models backend/app/security backend/app/repositories backend/app/services backend/app/schemas backend/app/api/routes backend/tests
touch backend/app/__init__.py backend/app/models/__init__.py backend/app/security/__init__.py backend/app/repositories/__init__.py backend/app/services/__init__.py backend/app/schemas/__init__.py backend/app/api/__init__.py backend/app/api/routes/__init__.py
```

`backend/requirements.txt`:

```
fastapi>=0.115,<1.0
uvicorn[standard]>=0.30,<1.0
sqlalchemy>=2.0,<3.0
alembic>=1.13,<2.0
mysql-connector-python>=9.0,<10.0
passlib[bcrypt]>=1.7,<2.0
PyJWT>=2.9,<3.0
pydantic>=2.7,<3.0
pydantic-settings>=2.4,<3.0
pytest>=8.0,<9.0
httpx>=0.27,<1.0
```

- [ ] **Step 2: Crear `.env.example` y `pytest.ini`**

`backend/.env.example`:

```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=clinica_dental_web
JWT_SECRET_KEY=change-me-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60
```

`backend/pytest.ini`:

```ini
[pytest]
pythonpath = .
```

- [ ] **Step 3: Escribir el test de `Settings` (falla primero)**

`backend/tests/test_config.py`:

```python
def test_settings_reads_from_env(monkeypatch):
    monkeypatch.setenv("DB_HOST", "db.example.com")
    monkeypatch.setenv("DB_PORT", "3307")
    monkeypatch.setenv("DB_USER", "dental_user")
    monkeypatch.setenv("DB_PASSWORD", "s3cret")
    monkeypatch.setenv("DB_NAME", "clinica_test")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")

    from app.config import Settings

    settings = Settings()

    assert settings.db_host == "db.example.com"
    assert settings.db_port == 3307
    assert settings.jwt_algorithm == "HS256"
    assert settings.jwt_expire_minutes == 60


def test_settings_database_url_format(monkeypatch):
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "3306")
    monkeypatch.setenv("DB_USER", "root")
    monkeypatch.setenv("DB_PASSWORD", "")
    monkeypatch.setenv("DB_NAME", "clinica_test")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")

    from app.config import Settings

    settings = Settings()

    assert settings.database_url == "mysql+mysqlconnector://root:@localhost:3306/clinica_test"
```

- [ ] **Step 4: Ejecutar el test y verificar que falla**

Run: `cd backend && pytest tests/test_config.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.config'`

- [ ] **Step 5: Implementar `app/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = ""
    db_name: str = "clinica_dental_web"

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    @property
    def database_url(self) -> str:
        return (
            f"mysql+mysqlconnector://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
```

- [ ] **Step 6: Ejecutar el test y verificar que pasa**

Run: `cd backend && pytest tests/test_config.py -v`
Expected: `2 passed`

- [ ] **Step 7: Escribir el test de `get_db` (falla primero)**

`backend/tests/test_db.py`:

```python
import pytest


def test_get_db_yields_session_and_closes_it(monkeypatch):
    import app.db as db_module

    closed = {"value": False}

    class FakeSession:
        def close(self):
            closed["value"] = True

    monkeypatch.setattr(db_module, "SessionLocal", lambda: FakeSession())

    gen = db_module.get_db()
    session = next(gen)

    assert isinstance(session, FakeSession)
    assert closed["value"] is False

    with pytest.raises(StopIteration):
        next(gen)

    assert closed["value"] is True
```

- [ ] **Step 8: Ejecutar el test y verificar que falla**

Run: `cd backend && pytest tests/test_db.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.db'`

- [ ] **Step 9: Implementar `app/db.py`**

```python
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 10: Ejecutar el test y verificar que pasa**

Run: `cd backend && JWT_SECRET_KEY=test pytest tests/test_db.py -v`
Expected: `1 passed`

*(`JWT_SECRET_KEY=test` es necesario porque `app.db` importa `app.config.settings`, y
`Settings()` exige esa variable al no tener default. En el resto del plan, `tests/conftest.py`
ya deja esto resuelto automáticamente.)*

- [ ] **Step 11: Crear `tests/conftest.py` con la fixture compartida `db_session`**

```python
import os

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_NAME", "clinica_test")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture()
def db_session():
    from app.models import Base

    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
```

- [ ] **Step 12: Confirmar que la suite completa sigue en verde**

Run: `cd backend && pytest -v`
Expected: los tests de `test_config.py` y `test_db.py` pasan (`test_models` etc. no existen
todavía, así que no aparecen).

- [ ] **Step 13: Commit**

```bash
git add backend/requirements.txt backend/.env.example backend/pytest.ini backend/app/__init__.py backend/app/config.py backend/app/db.py backend/tests/conftest.py backend/tests/test_config.py backend/tests/test_db.py
git commit -m "feat(backend): scaffolding, settings y sesion de BD"
```

---

### Task 2: Modelos SQLAlchemy (`Clinica`, `ClinicaModulo`, `Usuario`) + migración Alembic

**Files:**
- Create: `backend/app/models/base.py`
- Create: `backend/app/models/clinica.py`
- Create: `backend/app/models/usuario.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/tests/test_models.py`
- Create: `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/0001_create_clinica_usuario.py`

**Interfaces:**
- Consumes: `app.db` (nada directo, pero comparte el mismo `Base`).
- Produces: `app.models.Base`, `app.models.Clinica`, `app.models.EstadoClinica`,
  `app.models.ClinicaModulo`, `app.models.Usuario`, `app.models.RolUsuario`.

- [ ] **Step 1: Escribir el test de modelos (falla primero)**

`backend/tests/test_models.py`:

```python
def test_crear_clinica_usuario_y_modulo(db_session):
    from app.models import Clinica, ClinicaModulo, EstadoClinica, RolUsuario, Usuario

    clinica = Clinica(nombre="Dental Smiling", correo="contacto@dentalsmiling.com")
    db_session.add(clinica)
    db_session.flush()

    assert clinica.id_clinica is not None
    assert clinica.estado == EstadoClinica.ACTIVA

    modulo = ClinicaModulo(id_clinica=clinica.id_clinica, modulo="recetas", habilitado=False)
    db_session.add(modulo)

    usuario = Usuario(
        id_clinica=clinica.id_clinica,
        username="admin.dentalsmiling",
        password_hash="hash-de-prueba",
        rol=RolUsuario.ADMIN,
    )
    db_session.add(usuario)
    db_session.commit()

    assert usuario.activo is True
    assert usuario.clinica.nombre == "Dental Smiling"
    assert clinica.modulos[0].modulo == "recetas"
    assert clinica.modulos[0].habilitado is False


def test_usuario_superadmin_sin_clinica(db_session):
    from app.models import RolUsuario, Usuario

    superadmin = Usuario(
        id_clinica=None,
        username="superadmin",
        password_hash="hash-de-prueba",
        rol=RolUsuario.SUPERADMIN,
    )
    db_session.add(superadmin)
    db_session.commit()

    assert superadmin.id_clinica is None
    assert superadmin.clinica is None
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `cd backend && pytest tests/test_models.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.models'` (o `ImportError`)

- [ ] **Step 3: Implementar `app/models/base.py`**

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

- [ ] **Step 4: Implementar `app/models/clinica.py`**

```python
import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base


class EstadoClinica(str, enum.Enum):
    ACTIVA = "activa"
    SUSPENDIDA = "suspendida"
    INACTIVA = "inactiva"


class Clinica(Base):
    __tablename__ = "clinica"

    id_clinica: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    direccion: Mapped[str | None] = mapped_column(String(150), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(8), nullable=True)
    correo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    estado: Mapped[EstadoClinica] = mapped_column(
        SAEnum(EstadoClinica, name="estado_clinica"),
        nullable=False,
        default=EstadoClinica.ACTIVA,
        server_default=EstadoClinica.ACTIVA.value,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="clinica")
    modulos: Mapped[list["ClinicaModulo"]] = relationship(back_populates="clinica")


class ClinicaModulo(Base):
    __tablename__ = "clinica_modulo"

    id_clinica: Mapped[int] = mapped_column(
        ForeignKey("clinica.id_clinica"), primary_key=True
    )
    modulo: Mapped[str] = mapped_column(String(50), primary_key=True)
    habilitado: Mapped[bool] = mapped_column(default=True, server_default="1")

    clinica: Mapped["Clinica"] = relationship(back_populates="modulos")
```

- [ ] **Step 5: Implementar `app/models/usuario.py`**

```python
import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base


class RolUsuario(str, enum.Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    DOCTOR = "doctor"
    ASISTENTE = "asistente"


class Usuario(Base):
    __tablename__ = "usuario"

    id_usuario: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_clinica: Mapped[int | None] = mapped_column(
        ForeignKey("clinica.id_clinica"), nullable=True
    )
    username: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[RolUsuario] = mapped_column(
        SAEnum(RolUsuario, name="rol_usuario"), nullable=False
    )
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    clinica: Mapped["Clinica | None"] = relationship(back_populates="usuarios")
```

- [ ] **Step 6: Actualizar `app/models/__init__.py`**

```python
from app.models.base import Base
from app.models.clinica import Clinica, ClinicaModulo, EstadoClinica
from app.models.usuario import RolUsuario, Usuario

__all__ = [
    "Base",
    "Clinica",
    "ClinicaModulo",
    "EstadoClinica",
    "Usuario",
    "RolUsuario",
]
```

- [ ] **Step 7: Ejecutar el test y verificar que pasa**

Run: `cd backend && pytest tests/test_models.py -v`
Expected: `2 passed`

- [ ] **Step 8: Inicializar Alembic**

Run: `cd backend && alembic init alembic`
Expected: crea `backend/alembic.ini`, `backend/alembic/env.py`,
`backend/alembic/script.py.mako`, `backend/alembic/versions/` (vacío).

- [ ] **Step 9: Reemplazar `backend/alembic/env.py` para usar `settings` y `Base.metadata`**

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import settings
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 10: Escribir la migración inicial a mano**

`backend/alembic/versions/0001_create_clinica_usuario.py`:

```python
"""create clinica, clinica_modulo y usuario

Revision ID: 0001
Revises:
Create Date: 2026-07-30
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "clinica",
        sa.Column("id_clinica", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("direccion", sa.String(length=150), nullable=True),
        sa.Column("telefono", sa.String(length=8), nullable=True),
        sa.Column("correo", sa.String(length=100), nullable=True),
        sa.Column(
            "estado",
            sa.Enum("activa", "suspendida", "inactiva", name="estado_clinica"),
            nullable=False,
            server_default="activa",
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "clinica_modulo",
        sa.Column(
            "id_clinica",
            sa.Integer(),
            sa.ForeignKey("clinica.id_clinica"),
            primary_key=True,
        ),
        sa.Column("modulo", sa.String(length=50), primary_key=True),
        sa.Column("habilitado", sa.Boolean(), nullable=False, server_default="1"),
    )

    op.create_table(
        "usuario",
        sa.Column("id_usuario", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "id_clinica", sa.Integer(), sa.ForeignKey("clinica.id_clinica"), nullable=True
        ),
        sa.Column("username", sa.String(length=30), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "rol",
            sa.Enum("superadmin", "admin", "doctor", "asistente", name="rol_usuario"),
            nullable=False,
        ),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("usuario")
    op.drop_table("clinica_modulo")
    op.drop_table("clinica")
```

*(Esta migración se corre manualmente contra un MySQL real cuando exista uno disponible:
`alembic upgrade head`. Los tests de este plan no dependen de MySQL, así que no se automatiza
esa verificación aquí.)*

- [ ] **Step 11: Commit**

```bash
git add backend/app/models backend/tests/test_models.py backend/alembic.ini backend/alembic/env.py backend/alembic/versions/0001_create_clinica_usuario.py
git commit -m "feat(backend): modelos Clinica/ClinicaModulo/Usuario y migracion inicial"
```

---

### Task 3: Hashing de contraseñas (bcrypt)

**Files:**
- Create: `backend/app/security/passwords.py`
- Create: `backend/tests/test_passwords.py`

**Interfaces:**
- Produces: `app.security.passwords.hash_password(plain: str) -> str`,
  `app.security.passwords.verify_password(plain: str, password_hash: str) -> bool`.

- [ ] **Step 1: Escribir el test (falla primero)**

`backend/tests/test_passwords.py`:

```python
def test_hash_password_no_devuelve_texto_plano():
    from app.security.passwords import hash_password

    resultado = hash_password("clave123")

    assert resultado != "clave123"
    assert resultado.startswith("$2b$")


def test_verify_password_acepta_la_clave_correcta():
    from app.security.passwords import hash_password, verify_password

    hashed = hash_password("clave123")

    assert verify_password("clave123", hashed) is True


def test_verify_password_rechaza_clave_incorrecta():
    from app.security.passwords import hash_password, verify_password

    hashed = hash_password("clave123")

    assert verify_password("otra-clave", hashed) is False
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `cd backend && pytest tests/test_passwords.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.security.passwords'`

- [ ] **Step 3: Implementar `app/security/passwords.py`**

```python
from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return _pwd_context.verify(plain_password, password_hash)
```

- [ ] **Step 4: Ejecutar el test y verificar que pasa**

Run: `cd backend && pytest tests/test_passwords.py -v`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/security/passwords.py backend/tests/test_passwords.py
git commit -m "feat(backend): hashing de contrasenas con bcrypt"
```

---

### Task 4: Emisión y verificación de JWT

**Files:**
- Create: `backend/app/security/jwt.py`
- Create: `backend/tests/test_jwt.py`

**Interfaces:**
- Consumes: `app.config.settings` (`jwt_secret_key`, `jwt_algorithm`).
- Produces: `app.security.jwt.create_access_token(data: dict, expires_delta: timedelta) -> str`,
  `app.security.jwt.decode_access_token(token: str) -> dict`, excepción
  `app.security.jwt.TokenError`.

- [ ] **Step 1: Escribir el test (falla primero)**

`backend/tests/test_jwt.py`:

```python
from datetime import timedelta

import pytest


def test_create_and_decode_access_token():
    from app.security.jwt import create_access_token, decode_access_token

    token = create_access_token(
        data={"sub": "42", "id_clinica": 7, "rol": "admin"},
        expires_delta=timedelta(minutes=10),
    )
    payload = decode_access_token(token)

    assert payload["sub"] == "42"
    assert payload["id_clinica"] == 7
    assert payload["rol"] == "admin"
    assert "exp" in payload


def test_decode_access_token_expirado_lanza_token_error():
    from app.security.jwt import TokenError, create_access_token, decode_access_token

    token = create_access_token(
        data={"sub": "42", "id_clinica": None, "rol": "superadmin"},
        expires_delta=timedelta(minutes=-1),
    )

    with pytest.raises(TokenError):
        decode_access_token(token)


def test_decode_access_token_invalido_lanza_token_error():
    from app.security.jwt import TokenError, decode_access_token

    with pytest.raises(TokenError):
        decode_access_token("token-que-no-es-un-jwt-valido")
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `cd backend && pytest tests/test_jwt.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.security.jwt'`

- [ ] **Step 3: Implementar `app/security/jwt.py`**

```python
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings


class TokenError(Exception):
    """Token invalido, mal formado o expirado."""


def create_access_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except jwt.PyJWTError as exc:
        raise TokenError(str(exc)) from exc
```

- [ ] **Step 4: Ejecutar el test y verificar que pasa**

Run: `cd backend && pytest tests/test_jwt.py -v`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/security/jwt.py backend/tests/test_jwt.py
git commit -m "feat(backend): emision y verificacion de JWT"
```

---

### Task 5: `BaseRepository` (contrato) + `UsuarioRepository`

**Files:**
- Create: `backend/app/repositories/base.py`
- Create: `backend/app/repositories/usuario_repository.py`
- Create: `backend/tests/test_base_repository.py`
- Create: `backend/tests/test_usuario_repository.py`

**Interfaces:**
- Consumes: `app.models.Usuario` (modelo), fixture `db_session`.
- Produces: `app.repositories.base.BaseRepository[T]` (ABC genérica, para recursos futuros
  aislados por clínica — Módulos 3+), `app.repositories.usuario_repository.UsuarioRepository`
  con `obtener_por_username(username: str) -> Usuario | None` y
  `obtener_por_id(id_usuario: int) -> Usuario | None`.

- [ ] **Step 1: Escribir el test de `BaseRepository` (falla primero)**

`backend/tests/test_base_repository.py`:

```python
import pytest


def test_base_repository_no_se_puede_instanciar_directamente(db_session):
    from app.repositories.base import BaseRepository

    with pytest.raises(TypeError):
        BaseRepository(db_session)


def test_subclase_concreta_debe_implementar_todos_los_metodos(db_session):
    from app.repositories.base import BaseRepository

    class RepositorioIncompleto(BaseRepository):
        def listar(self, id_clinica):
            return []

    with pytest.raises(TypeError):
        RepositorioIncompleto(db_session)
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `cd backend && pytest tests/test_base_repository.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.repositories.base'`

- [ ] **Step 3: Implementar `app/repositories/base.py`**

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from sqlalchemy.orm import Session

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """Repositorio base para recursos aislados por clinica.

    Todo metodo recibe id_clinica como primer parametro obligatorio, sin
    default. Ningun repositorio de un recurso tenant-scoped (Paciente,
    Doctor, Cita, etc. en modulos futuros) puede heredar de esta clase y
    omitir el filtro de clinica en sus queries.
    """

    def __init__(self, db: Session):
        self.db = db

    @abstractmethod
    def listar(self, id_clinica: int) -> list[T]:
        ...

    @abstractmethod
    def obtener(self, id_clinica: int, id_: int) -> T | None:
        ...

    @abstractmethod
    def crear(self, id_clinica: int, data: dict) -> T:
        ...

    @abstractmethod
    def actualizar(self, id_clinica: int, id_: int, data: dict) -> T | None:
        ...

    @abstractmethod
    def eliminar(self, id_clinica: int, id_: int) -> bool:
        ...
```

- [ ] **Step 4: Ejecutar el test y verificar que pasa**

Run: `cd backend && pytest tests/test_base_repository.py -v`
Expected: `2 passed`

- [ ] **Step 5: Escribir el test de `UsuarioRepository` (falla primero)**

`backend/tests/test_usuario_repository.py`:

```python
def test_obtener_por_username_encuentra_el_usuario(db_session):
    from app.models import RolUsuario, Usuario
    from app.repositories.usuario_repository import UsuarioRepository

    usuario = Usuario(
        id_clinica=None,
        username="superadmin",
        password_hash="hash",
        rol=RolUsuario.SUPERADMIN,
    )
    db_session.add(usuario)
    db_session.commit()

    repo = UsuarioRepository(db_session)
    encontrado = repo.obtener_por_username("superadmin")

    assert encontrado is not None
    assert encontrado.id_usuario == usuario.id_usuario


def test_obtener_por_username_devuelve_none_si_no_existe(db_session):
    from app.repositories.usuario_repository import UsuarioRepository

    repo = UsuarioRepository(db_session)

    assert repo.obtener_por_username("no-existe") is None


def test_obtener_por_id_encuentra_el_usuario(db_session):
    from app.models import RolUsuario, Usuario
    from app.repositories.usuario_repository import UsuarioRepository

    usuario = Usuario(
        id_clinica=None,
        username="superadmin",
        password_hash="hash",
        rol=RolUsuario.SUPERADMIN,
    )
    db_session.add(usuario)
    db_session.commit()

    repo = UsuarioRepository(db_session)
    encontrado = repo.obtener_por_id(usuario.id_usuario)

    assert encontrado is not None
    assert encontrado.username == "superadmin"
```

- [ ] **Step 6: Ejecutar el test y verificar que falla**

Run: `cd backend && pytest tests/test_usuario_repository.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.repositories.usuario_repository'`

- [ ] **Step 7: Implementar `app/repositories/usuario_repository.py`**

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Usuario


class UsuarioRepository:
    """Repositorio de identidad: busca usuarios por username/id para login.

    A diferencia de BaseRepository, no exige id_clinica porque el login
    ocurre ANTES de saber a que clinica pertenece la sesion: es el punto de
    entrada que determina esa clinica, no un recurso ya aislado por tenant.
    """

    def __init__(self, db: Session):
        self.db = db

    def obtener_por_username(self, username: str) -> Usuario | None:
        stmt = select(Usuario).where(Usuario.username == username)
        return self.db.execute(stmt).scalar_one_or_none()

    def obtener_por_id(self, id_usuario: int) -> Usuario | None:
        return self.db.get(Usuario, id_usuario)
```

- [ ] **Step 8: Ejecutar el test y verificar que pasa**

Run: `cd backend && pytest tests/test_usuario_repository.py -v`
Expected: `3 passed`

- [ ] **Step 9: Commit**

```bash
git add backend/app/repositories backend/tests/test_base_repository.py backend/tests/test_usuario_repository.py
git commit -m "feat(backend): BaseRepository y UsuarioRepository"
```

---

### Task 6: Excepciones de dominio + `AuthService`

**Files:**
- Create: `backend/app/exceptions.py`
- Create: `backend/app/services/auth_service.py`
- Create: `backend/tests/test_auth_service.py`

**Interfaces:**
- Consumes: `UsuarioRepository`, `hash_password`/`verify_password`, `create_access_token`,
  `settings.jwt_expire_minutes`.
- Produces: `app.exceptions.InvalidCredentialsError`, `app.exceptions.ClinicaInactivaError`,
  `app.services.auth_service.AuthService.login(username: str, password: str) -> dict` (con
  claves `access_token`, `token_type`, `usuario`).

- [ ] **Step 1: Escribir el test (falla primero)**

`backend/tests/test_auth_service.py`:

```python
import pytest


def _crear_clinica_activa(db_session):
    from app.models import Clinica

    clinica = Clinica(nombre="Dental Smiling")
    db_session.add(clinica)
    db_session.flush()
    return clinica


def _crear_usuario(db_session, clinica, username, rol, password="clave123"):
    from app.models import Usuario
    from app.security.passwords import hash_password

    usuario = Usuario(
        id_clinica=clinica.id_clinica if clinica else None,
        username=username,
        password_hash=hash_password(password),
        rol=rol,
    )
    db_session.add(usuario)
    db_session.commit()
    return usuario


def test_login_exitoso_devuelve_token_y_usuario(db_session):
    from app.models import RolUsuario
    from app.services.auth_service import AuthService

    clinica = _crear_clinica_activa(db_session)
    _crear_usuario(db_session, clinica, "admin.dental", RolUsuario.ADMIN)

    resultado = AuthService(db_session).login("admin.dental", "clave123")

    assert resultado["token_type"] == "bearer"
    assert resultado["usuario"].username == "admin.dental"
    assert isinstance(resultado["access_token"], str) and len(resultado["access_token"]) > 0


def test_login_con_password_incorrecta_lanza_invalid_credentials(db_session):
    from app.exceptions import InvalidCredentialsError
    from app.models import RolUsuario
    from app.services.auth_service import AuthService

    clinica = _crear_clinica_activa(db_session)
    _crear_usuario(db_session, clinica, "admin.dental", RolUsuario.ADMIN)

    with pytest.raises(InvalidCredentialsError):
        AuthService(db_session).login("admin.dental", "clave-equivocada")


def test_login_usuario_inexistente_lanza_invalid_credentials(db_session):
    from app.exceptions import InvalidCredentialsError
    from app.services.auth_service import AuthService

    with pytest.raises(InvalidCredentialsError):
        AuthService(db_session).login("no-existe", "cualquier-clave")


def test_login_con_clinica_suspendida_lanza_clinica_inactiva(db_session):
    from app.exceptions import ClinicaInactivaError
    from app.models import EstadoClinica, RolUsuario
    from app.services.auth_service import AuthService

    clinica = _crear_clinica_activa(db_session)
    clinica.estado = EstadoClinica.SUSPENDIDA
    db_session.commit()
    _crear_usuario(db_session, clinica, "admin.dental", RolUsuario.ADMIN)

    with pytest.raises(ClinicaInactivaError):
        AuthService(db_session).login("admin.dental", "clave123")


def test_login_superadmin_no_requiere_clinica_activa(db_session):
    from app.models import RolUsuario
    from app.services.auth_service import AuthService

    _crear_usuario(db_session, None, "superadmin", RolUsuario.SUPERADMIN)

    resultado = AuthService(db_session).login("superadmin", "clave123")

    assert resultado["usuario"].rol == RolUsuario.SUPERADMIN
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `cd backend && pytest tests/test_auth_service.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.exceptions'`

- [ ] **Step 3: Implementar `app/exceptions.py`**

```python
class InvalidCredentialsError(Exception):
    """El usuario no existe, esta inactivo, o la contrasena no coincide."""


class ClinicaInactivaError(Exception):
    """La clinica del usuario no esta en estado 'activa'."""
```

- [ ] **Step 4: Implementar `app/services/auth_service.py`**

```python
from datetime import timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.exceptions import ClinicaInactivaError, InvalidCredentialsError
from app.models import EstadoClinica, RolUsuario
from app.repositories.usuario_repository import UsuarioRepository
from app.security.jwt import create_access_token
from app.security.passwords import verify_password


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.usuarios = UsuarioRepository(db)

    def login(self, username: str, password: str) -> dict:
        usuario = self.usuarios.obtener_por_username(username)
        if usuario is None or not usuario.activo:
            raise InvalidCredentialsError()
        if not verify_password(password, usuario.password_hash):
            raise InvalidCredentialsError()

        if usuario.rol != RolUsuario.SUPERADMIN:
            if usuario.clinica is None or usuario.clinica.estado != EstadoClinica.ACTIVA:
                raise ClinicaInactivaError()

        token = create_access_token(
            data={
                "sub": str(usuario.id_usuario),
                "id_clinica": usuario.id_clinica,
                "rol": usuario.rol.value,
            },
            expires_delta=timedelta(minutes=settings.jwt_expire_minutes),
        )
        return {
            "access_token": token,
            "token_type": "bearer",
            "usuario": usuario,
        }
```

- [ ] **Step 5: Ejecutar el test y verificar que pasa**

Run: `cd backend && pytest tests/test_auth_service.py -v`
Expected: `5 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/app/exceptions.py backend/app/services/auth_service.py backend/tests/test_auth_service.py
git commit -m "feat(backend): AuthService con login y validacion de clinica activa"
```

---

### Task 7: Dependencias de FastAPI (`TenantContext`)

**Files:**
- Create: `backend/app/api/deps.py`
- Create: `backend/tests/test_api_deps.py`

**Interfaces:**
- Consumes: `app.security.jwt.decode_access_token`, `UsuarioRepository`, `app.db.get_db`.
- Produces: `app.api.deps.oauth2_scheme`, `app.api.deps.get_current_user`,
  `app.api.deps.require_roles(*roles)`, `app.api.deps.resolve_clinica_id`.

- [ ] **Step 1: Escribir el test (falla primero)**

`backend/tests/test_api_deps.py`:

```python
from datetime import timedelta

import pytest
from fastapi import HTTPException


def _crear_usuario_con_token(db_session, rol, id_clinica=None, username="user1"):
    from app.models import RolUsuario, Usuario
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

    token = create_access_token(
        data={"sub": str(usuario.id_usuario), "id_clinica": id_clinica, "rol": rol.value},
        expires_delta=timedelta(minutes=10),
    )
    return usuario, token


def test_get_current_user_devuelve_el_usuario_del_token(db_session):
    from app.api.deps import get_current_user
    from app.models import RolUsuario

    usuario, token = _crear_usuario_con_token(db_session, RolUsuario.ADMIN, id_clinica=None)

    resultado = get_current_user(token=token, db=db_session)

    assert resultado.id_usuario == usuario.id_usuario


def test_get_current_user_con_token_invalido_lanza_401(db_session):
    from app.api.deps import get_current_user

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token="token-invalido", db=db_session)

    assert exc_info.value.status_code == 401


def test_require_roles_permite_rol_correcto(db_session):
    from app.api.deps import require_roles
    from app.models import RolUsuario

    usuario, _ = _crear_usuario_con_token(db_session, RolUsuario.SUPERADMIN)

    dependencia = require_roles(RolUsuario.SUPERADMIN)
    resultado = dependencia(usuario=usuario)

    assert resultado is usuario


def test_require_roles_rechaza_rol_incorrecto(db_session):
    from app.api.deps import require_roles
    from app.models import RolUsuario

    usuario, _ = _crear_usuario_con_token(db_session, RolUsuario.ASISTENTE)

    dependencia = require_roles(RolUsuario.SUPERADMIN)

    with pytest.raises(HTTPException) as exc_info:
        dependencia(usuario=usuario)

    assert exc_info.value.status_code == 403


def test_resolve_clinica_id_usuario_normal_usa_su_propia_clinica(db_session):
    from app.api.deps import resolve_clinica_id
    from app.models import RolUsuario

    usuario, _ = _crear_usuario_con_token(db_session, RolUsuario.ADMIN, id_clinica=7)

    assert resolve_clinica_id(usuario=usuario, x_clinica_id=99) == 7


def test_resolve_clinica_id_superadmin_requiere_header(db_session):
    from app.api.deps import resolve_clinica_id
    from app.models import RolUsuario

    usuario, _ = _crear_usuario_con_token(db_session, RolUsuario.SUPERADMIN)

    with pytest.raises(HTTPException) as exc_info:
        resolve_clinica_id(usuario=usuario, x_clinica_id=None)
    assert exc_info.value.status_code == 400

    assert resolve_clinica_id(usuario=usuario, x_clinica_id=3) == 3
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `cd backend && pytest tests/test_api_deps.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.api.deps'`

- [ ] **Step 3: Implementar `app/api/deps.py`**

```python
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import RolUsuario, Usuario
from app.repositories.usuario_repository import UsuarioRepository
from app.security.jwt import TokenError, decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> Usuario:
    try:
        payload = decode_access_token(token)
    except TokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido o expirado",
        )

    id_usuario = int(payload["sub"])
    usuario = UsuarioRepository(db).obtener_por_id(id_usuario)
    if usuario is None or not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo",
        )
    return usuario


def require_roles(*roles: RolUsuario):
    def _dependency(usuario: Usuario = Depends(get_current_user)) -> Usuario:
        if usuario.rol not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tenes permiso para esta accion",
            )
        return usuario

    return _dependency


def resolve_clinica_id(
    usuario: Usuario = Depends(get_current_user),
    x_clinica_id: int | None = Header(default=None),
) -> int:
    if usuario.rol == RolUsuario.SUPERADMIN:
        if x_clinica_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un superadmin debe indicar X-Clinica-Id para operar sobre una clinica",
            )
        return x_clinica_id

    return usuario.id_clinica
```

- [ ] **Step 4: Ejecutar el test y verificar que pasa**

Run: `cd backend && pytest tests/test_api_deps.py -v`
Expected: `7 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/deps.py backend/tests/test_api_deps.py
git commit -m "feat(backend): dependencias de FastAPI para auth y aislamiento por clinica"
```

---

### Task 8: Schemas, rutas de auth, app FastAPI y tests end-to-end

**Files:**
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/api/routes/auth.py`
- Create: `backend/app/main.py`
- Modify: `backend/tests/conftest.py` (agrega fixture `client`)
- Create: `backend/tests/test_auth_routes.py`

**Interfaces:**
- Consumes: `AuthService`, `get_current_user`, `get_db`.
- Produces: endpoints `POST /auth/login`, `GET /auth/me`, `POST /auth/logout`; app FastAPI
  `app.main.app`.

- [ ] **Step 1: Agregar la fixture `client` a `tests/conftest.py`**

Agregar al final de `backend/tests/conftest.py`:

```python
@pytest.fixture()
def client(db_session):
    from fastapi.testclient import TestClient

    from app.db import get_db
    from app.main import app

    def _get_db_override():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
```

- [ ] **Step 2: Escribir los tests end-to-end (fallan primero)**

`backend/tests/test_auth_routes.py`:

```python
def _crear_clinica_y_admin(db_session, estado="activa"):
    from app.models import Clinica, EstadoClinica, RolUsuario, Usuario
    from app.security.passwords import hash_password

    clinica = Clinica(nombre="Dental Smiling", estado=EstadoClinica(estado))
    db_session.add(clinica)
    db_session.flush()

    usuario = Usuario(
        id_clinica=clinica.id_clinica,
        username="admin.dental",
        password_hash=hash_password("clave123"),
        rol=RolUsuario.ADMIN,
    )
    db_session.add(usuario)
    db_session.commit()
    return clinica, usuario


def test_login_exitoso(client, db_session):
    _crear_clinica_y_admin(db_session)

    respuesta = client.post(
        "/auth/login", json={"username": "admin.dental", "password": "clave123"}
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["token_type"] == "bearer"
    assert cuerpo["usuario"]["username"] == "admin.dental"
    assert "access_token" in cuerpo


def test_login_con_password_incorrecta_devuelve_401(client, db_session):
    _crear_clinica_y_admin(db_session)

    respuesta = client.post(
        "/auth/login", json={"username": "admin.dental", "password": "mala-clave"}
    )

    assert respuesta.status_code == 401


def test_login_con_clinica_suspendida_devuelve_403(client, db_session):
    _crear_clinica_y_admin(db_session, estado="suspendida")

    respuesta = client.post(
        "/auth/login", json={"username": "admin.dental", "password": "clave123"}
    )

    assert respuesta.status_code == 403


def test_me_con_token_valido_devuelve_datos_del_usuario(client, db_session):
    _crear_clinica_y_admin(db_session)

    login = client.post(
        "/auth/login", json={"username": "admin.dental", "password": "clave123"}
    )
    token = login.json()["access_token"]

    respuesta = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    assert respuesta.json()["username"] == "admin.dental"


def test_me_sin_token_devuelve_401(client):
    respuesta = client.get("/auth/me")

    assert respuesta.status_code == 401
```

- [ ] **Step 3: Ejecutar los tests y verificar que fallan**

Run: `cd backend && pytest tests/test_auth_routes.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.main'`

- [ ] **Step 4: Implementar `app/schemas/auth.py`**

```python
from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class UsuarioResponse(BaseModel):
    id_usuario: int
    username: str
    rol: str
    id_clinica: int | None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    usuario: UsuarioResponse
```

- [ ] **Step 5: Implementar `app/api/routes/auth.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db
from app.exceptions import ClinicaInactivaError, InvalidCredentialsError
from app.models import Usuario
from app.schemas.auth import LoginRequest, TokenResponse, UsuarioResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(credenciales: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        resultado = AuthService(db).login(credenciales.username, credenciales.password)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contrasena incorrectos",
        )
    except ClinicaInactivaError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La clinica de este usuario no esta activa",
        )
    return TokenResponse(
        access_token=resultado["access_token"],
        token_type=resultado["token_type"],
        usuario=UsuarioResponse.model_validate(resultado["usuario"]),
    )


@router.get("/me", response_model=UsuarioResponse)
def me(usuario: Usuario = Depends(get_current_user)) -> UsuarioResponse:
    return UsuarioResponse.model_validate(usuario)


@router.post("/logout")
def logout() -> dict:
    return {"detail": "Sesion cerrada"}
```

- [ ] **Step 6: Implementar `app/main.py`**

```python
from fastapi import FastAPI

from app.api.routes.auth import router as auth_router

app = FastAPI(title="Clinica Dental Web API")
app.include_router(auth_router)
```

- [ ] **Step 7: Ejecutar los tests y verificar que pasan**

Run: `cd backend && pytest tests/test_auth_routes.py -v`
Expected: `5 passed`

- [ ] **Step 8: Ejecutar toda la suite del módulo**

Run: `cd backend && pytest -v`
Expected: todos los tests de `test_config.py`, `test_db.py`, `test_models.py`,
`test_passwords.py`, `test_jwt.py`, `test_base_repository.py`, `test_usuario_repository.py`,
`test_auth_service.py`, `test_api_deps.py` y `test_auth_routes.py` pasan (`30 passed`
aproximadamente).

- [ ] **Step 9: Commit**

```bash
git add backend/app/schemas/auth.py backend/app/api/routes/auth.py backend/app/main.py backend/tests/conftest.py backend/tests/test_auth_routes.py
git commit -m "feat(backend): endpoints de auth (login, me, logout) y app FastAPI"
```

---

## Self-Review

**Cobertura del spec:**
- Contraseñas hasheadas (bcrypt) → Task 3. ✅
- JWT para sesiones → Task 4, Task 6, Task 8. ✅
- `.env` para configuración → Task 1. ✅
- `Clinica` con estado y bloqueo de login al suspender → Task 2 (modelo), Task 6/8 (lógica y
  endpoint). ✅
- `Usuario` unificado con `id_clinica` nullable (superadmin) → Task 2, Task 6, Task 7. ✅
- `ClinicaModulo` (feature flags) → Task 2 (modelo creado; el endpoint para administrarlos es
  Módulo 2, fuera de alcance aquí, según el spec). ✅ (solo el modelo, correctamente acotado)
- PKs `INT AUTO_INCREMENT`, `Correo VARCHAR(100)` → Task 2 (modelos y migración). ✅
- Regla dura "todo repositorio exige `id_clinica`" → Task 5 (`BaseRepository` abstracto). ✅
- Endpoints `POST /auth/login`, `GET /auth/me`, `POST /auth/logout` → Task 8. ✅

**Placeholders:** revisado, no hay "TBD" ni pasos sin código real.

**Consistencia de tipos:** `AuthService.login` devuelve `dict` con `access_token`/`token_type`/
`usuario` en Task 6 y Task 8 usa exactamente esas claves. `UsuarioRepository.obtener_por_id` /
`obtener_por_username` se usan con la misma firma en Task 6, 7 y 8. `resolve_clinica_id` y
`require_roles` de Task 7 no se conectan todavía a ninguna ruta protegida por clínica (no hay
recursos tenant-scoped en este módulo) — quedan listos como dependencias para que el Módulo 2 en
adelante los use directamente, sin que este plan necesite un endpoint ficticio para "usarlos".
