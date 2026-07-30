# Contexto del Proyecto — ClinicaDentalWeb

**Para:** Meli (y su asistente de IA), para continuar con los Módulos 3, 4 y 5.
**Última actualización:** 2026-07-30 — Módulos 1 y 2 completos y en `main`.

Este documento resume todo lo que existe hasta ahora: qué se decidió, por qué, cómo está
armado el código, y qué convenciones hay que seguir para que los módulos nuevos encajen sin
fricción con lo ya construido.

---

## 1. Qué es este proyecto

Reescritura del sistema legacy `ClinicaDental` (escritorio, PyQt6, MySQL, una sola clínica) como
una plataforma web **multi-clínica**: varias clínicas dentales se registran y operan de forma
independiente, con un superadministrador que las gestiona a todas.

- **Repo legacy** (`ClinicaDental`, carpeta hermana): NO se toca. Es solo referencia de lo que
  había antes.
- **Repo nuevo** (`ClinicaDentalWeb`, este repo): todo el desarrollo pasa acá.

### Documentación de diseño (léela si necesitás el detalle completo de una decisión)

- `docs/superpowers/specs/2026-07-30-modulo-tenancy-auth-clinicas-design.md` — spec del Módulo 1,
  incluye el ERD as-is/to-be completo y el diagrama de clases del legacy.
- `docs/superpowers/plans/2026-07-30-modulo-tenancy-auth-clinicas-plan.md` — plan TDD tarea por
  tarea del Módulo 1.
- `docs/superpowers/specs/2026-07-30-modulo-2-panel-superadmin-design.md` — spec del Módulo 2.
- `docs/superpowers/plans/2026-07-30-modulo-2-panel-superadmin-plan.md` — plan TDD del Módulo 2.

Cuando armes el spec/plan de tu módulo, seguí el mismo formato y ubicación
(`docs/superpowers/specs/YYYY-MM-DD-modulo-N-<nombre>-design.md` y el equivalente en `plans/`).

---

## 2. Roadmap completo (8 módulos)

| # | Módulo | Asignado | Estado |
|---|---|---|---|
| 1 | Tenancy + Auth core (`Clinica`, `Usuario`, JWT, bcrypt, aislamiento por clínica) | Christian | ✅ Completo |
| 2 | Panel superadministrador (CRUD clínicas, admin principal, feature flags) | Christian | ✅ Completo |
| 3 | Parámetros por clínica (`Especialidad`, `Consultorio`, horarios, precios) | **Meli** | ⬜ Siguiente |
| 4 | Operación clínica básica (Pacientes, Odontólogos, Asistentes, Citas) | **Meli** | ⬜ Pendiente |
| 5 | Expediente clínico avanzado (diagnósticos, odontogramas, planes de tratamiento, recetas) | **Meli** | ⬜ Pendiente |
| 6 | Facturación extendida | Christian | ⬜ Pendiente |
| 7 | Dashboards y métricas | Christian | ⬜ Pendiente |
| 8 | Notificaciones y recordatorios | Sin asignar | ⬜ Pendiente |

**Tu bloque (Meli) es secuencial**: Módulo 3 → 4 → 5. El Módulo 4 usa `Especialidad`/`Consultorio`
del Módulo 3 (un `Doctor` va a referenciar una `Especialidad` por FK en vez de texto libre), y el
Módulo 5 usa `Paciente`/`Doctor` del Módulo 4. No hace falta esperarme a mí — mis módulos (6, 7)
dependen de los tuyos, no al revés.

---

## 3. Stack técnico

- **Python 3.12**, **FastAPI**, **SQLAlchemy 2.0** (ORM, estilo `Mapped`/`mapped_column`),
  **Alembic** (migraciones), **MySQL 8** (`mysql-connector-python` como driver).
- **Auth:** JWT (`PyJWT`), passwords con `passlib[bcrypt]` (¡ojo! fijamos `bcrypt<4.1` en
  `requirements.txt` por un bug de compatibilidad con `passlib` — no lo subas de versión sin
  revisar eso).
- **Validación:** `pydantic` v2 (`pydantic-settings` para config, `EmailStr` con
  `email-validator` para correos — no reinventes regex de validación de email).
- **Tests:** `pytest`, `httpx`/`TestClient` de FastAPI. Los tests usan **SQLite en memoria**, no
  MySQL — mucho más rápido, y es intencional (ver sección de gotchas más abajo).
- **Docker:** `docker-compose.yml` en la raíz levanta `backend` (FastAPI) + `db` (MySQL 8). Hay
  que reconstruir la imagen (`docker compose build backend`) cada vez que cambia el código o
  `requirements.txt`.

---

## 4. Estructura del repo

```
ClinicaDentalWeb/
  docker-compose.yml
  .env.example                  (variables para docker-compose)
  docs/
    superpowers/specs/           (un archivo de diseño por modulo)
    superpowers/plans/           (un plan TDD por modulo)
    CONTEXTO-PROYECTO.md          (este archivo)
  backend/
    .venv/                       (entorno virtual, no se commitea)
    requirements.txt
    .env.example                 (variables para desarrollo local sin Docker)
    pytest.ini
    alembic.ini
    alembic/
      env.py
      versions/                  (0001_..., 0002_..., etc. -- nunca edites una ya aplicada)
    app/
      config.py                  (Settings, lee de .env)
      db.py                      (engine, SessionLocal, get_db)
      exceptions.py               (TODAS las excepciones de dominio del proyecto viven aca)
      main.py                     (arma el FastAPI() e incluye los routers)
      models/                     (un archivo por entidad o grupo de entidades relacionadas)
      security/
        passwords.py               (hash_password, verify_password, generar_password_temporal)
        jwt.py                      (create_access_token, decode_access_token, TokenError)
      repositories/                (acceso a datos, ver seccion de convenciones)
      services/                    (logica de negocio que orquesta repositorios)
      schemas/                     (Pydantic: un archivo por dominio, ej. auth.py, clinica.py)
      api/
        deps.py                     (get_current_user, require_roles, resolve_clinica_id)
        routes/                     (un archivo por dominio, ej. auth.py, clinicas.py)
    tests/
      conftest.py                  (fixtures compartidas: db_session, client)
      test_<algo>.py               (un archivo de test por modulo de app/, mismo nombre)
```

---

## 5. Qué existe ya — Módulo 1 (Tenancy + Auth)

**Modelos** (`app/models/`):
- `Clinica` — `id_clinica`, `nombre`, `direccion`, `telefono`, `correo`, `estado`
  (`EstadoClinica`: `activa`/`suspendida`/`inactiva`, default `activa`), `created_at`.
- `ClinicaModulo` — llave compuesta `(id_clinica, modulo)`, `habilitado: bool`. Feature flags por
  clínica (ver Módulo 2).
- `Usuario` — `id_usuario`, `id_clinica` (**nullable**: `NULL` = superadmin, no pertenece a
  ninguna clínica), `username` (único), `password_hash`, `rol` (`RolUsuario`: `superadmin` /
  `admin` / `doctor` / `asistente`), `activo`, `debe_cambiar_password` (agregado en Módulo 2),
  `created_at`.

**Seguridad y auth:**
- `AuthService.login(username, password) -> dict` con `access_token`, `token_type`, `usuario`.
  Lanza `InvalidCredentialsError` (usuario/password malos) o `ClinicaInactivaError` (si
  `usuario.clinica.estado != ACTIVA`, salvo rol `superadmin` que no tiene clínica).
- `AuthService.cambiar_password(usuario, actual, nueva)` (agregado en Módulo 2).
- Dependencias FastAPI en `app/api/deps.py`:
  - `get_current_user` — valida el JWT, devuelve el `Usuario`.
  - `require_roles(*roles)` — factory de dependencia, `403` si el rol no matchea.
  - `resolve_clinica_id` — devuelve el `id_clinica` a usar: la del propio usuario, o (si es
    superadmin) la que venga en el header `X-Clinica-Id`.

**Endpoints:** `POST /auth/login`, `GET /auth/me`, `POST /auth/logout`,
`POST /auth/cambiar-password` (Módulo 2).

**Regla dura de arquitectura (esto es lo más importante para vos):**

`BaseRepository` (`app/repositories/base.py`) es una clase abstracta que **todo repositorio de
un recurso que vive dentro de una clínica** (`Paciente`, `Doctor`, `Cita`, `Especialidad`,
`Consultorio`, etc. — o sea, tus módulos) debe heredar. Sus métodos (`listar`, `obtener`, `crear`,
`actualizar`, `eliminar`) reciben `id_clinica: int` como **primer parámetro obligatorio, sin
default**. La razón: el aislamiento entre clínicas se fuerza por la firma del método, no por
disciplina del programador — nadie puede "olvidarse" del filtro porque el código ni compila sin
pasarlo.

```python
class BaseRepository(ABC, Generic[T]):
    def __init__(self, db: Session): ...
    @abstractmethod
    def listar(self, id_clinica: int) -> list[T]: ...
    @abstractmethod
    def obtener(self, id_clinica: int, id_: int) -> T | None: ...
    @abstractmethod
    def crear(self, id_clinica: int, data: dict) -> T: ...
    @abstractmethod
    def actualizar(self, id_clinica: int, id_: int, data: dict) -> T | None: ...
    @abstractmethod
    def eliminar(self, id_clinica: int, id_: int) -> bool: ...
```

**Excepciones a esta regla** (y por qué): `UsuarioRepository` y `ClinicaRepository` /
`ClinicaModuloRepository` NO heredan de `BaseRepository`:
- `UsuarioRepository` busca por `username`/`id_usuario` — es el punto de entrada del login,
  ocurre *antes* de saber a qué clínica pertenece la sesión.
- `ClinicaRepository` gestiona clínicas en sí mismas — no tiene sentido filtrar `Clinica` por
  `id_clinica`.
- `ClinicaModuloRepository` sí exige `id_clinica` en todos sus métodos (mismo espíritu), pero no
  hereda porque su llave es compuesta (`id_clinica` + `modulo`, un string), no un `int` simple
  como asume la firma de `BaseRepository`.

**Para tus módulos:** `PacienteRepository`, `DoctorRepository`, `CitaRepository`,
`EspecialidadRepository`, `ConsultorioRepository`, etc. **sí deben heredar `BaseRepository`** —
son exactamente el caso para el que se diseñó.

---

## 6. Qué existe ya — Módulo 2 (Panel Superadministrador)

- `ClinicaService.crear_clinica_con_admin(nombre, admin_username, direccion=None, telefono=None, correo=None) -> dict`
  crea la `Clinica` + siembra los 8 `ClinicaModulo` (todos `habilitado=True`) + crea el `Usuario`
  admin con una password temporal generada (`generar_password_temporal()`), todo en **una
  transacción** (`try/except` con `db.rollback()` explícito si algo falla — mirá el archivo, es
  un buen ejemplo a copiar si tus módulos necesitan crear varias entidades relacionadas de una).
- `MODULOS_DISPONIBLES` (en `app/repositories/clinica_modulo_repository.py`) es la única fuente
  de verdad de qué módulos existen: `pacientes`, `citas`, `odontogramas`, `presupuestos`,
  `recetas`, `facturacion`, `dashboards`, `notificaciones`. Si tu módulo agrega una entidad que
  debería ser toggleable por clínica, este es el lugar a tocar (con cuidado, es compartido).
- Endpoints `/clinicas` (todos con `require_roles(RolUsuario.SUPERADMIN)`): CRUD completo +
  `PATCH /clinicas/{id}/estado` + `PATCH /clinicas/{id}/modulos/{modulo}`.
- Flujo de password temporal: `Usuario.debe_cambiar_password` (default `True`), se expone en la
  respuesta de `/auth/login` y `/auth/me`, se pone en `False` vía
  `POST /auth/cambiar-password`. El backend **no** bloquea otros endpoints mientras el flag esté
  en `True` — es responsabilidad del frontend redirigir a la pantalla de cambio de password.

---

## 7. Convenciones a seguir (importante para que tu código encaje)

1. **TDD siempre:** test primero (RED, falla por la razón correcta), después la implementación
   mínima (GREEN). No escribas implementación antes que el test.
2. **Excepciones de dominio** viven todas en `app/exceptions.py` (una clase por error de negocio,
   ej. `InvalidCredentialsError`, `UsernameYaExisteError`). Los repositorios y servicios lanzan
   estas excepciones; las rutas (`app/api/routes/*.py`) las atrapan con `try/except` y las
   traducen a `HTTPException` con el status code correcto. Nunca metas un `HTTPException`
   directamente en un repositorio o servicio — esas capas no saben de HTTP.
3. **Repositorios** (`app/repositories/`): un archivo por entidad (o par de entidades muy
   relacionadas, como `Clinica`+`ClinicaModulo`... aunque ahí en realidad son dos archivos
   separados, revisalo). Reciben `db: Session` en el constructor. Métodos hacen `.flush()`, no
   `.commit()` — el `.commit()` final lo hace quien orquesta (la ruta, o un servicio si coordina
   varias escrituras relacionadas, como `ClinicaService`).
4. **Servicios** (`app/services/`) son para lógica que involucra más de un repositorio o
   coordina una transacción (ver `ClinicaService`, `AuthService`). Si un endpoint solo hace CRUD
   simple de una entidad, no hace falta un service — la ruta puede llamar al repositorio
   directamente (ver `app/api/routes/clinicas.py`, la mayoría de sus endpoints no pasan por un
   service).
5. **Migraciones:** un archivo por cambio de esquema, revision ID secuencial (`0001`, `0002`,
   `0003`...), `down_revision` apuntando al anterior. Nunca edites una migración ya committeada —
   si necesitás cambiar algo, agregá una migración nueva.
6. **Tests:** todo corre contra SQLite en memoria vía la fixture `db_session` (o `client` para
   endpoints, que ya trae `db_session` inyectada). Al terminar tu módulo, además corré todo
   contra MySQL real en Docker (`docker compose build backend && docker compose up -d --force-recreate backend && docker compose exec backend alembic upgrade head`) antes de darlo por
   terminado — ver la sección de gotchas, encontramos bugs reales que SOLO aparecen en MySQL.
7. **Nombres en español** para todo lo de negocio (modelos, campos, métodos de servicio/
   repositorio, mensajes de error) — el código en inglés es solo para nombres de clases/patrones
   técnicos genéricos (`BaseRepository`, `TokenError`). Seguí lo que ya hay, no mezcles.

---

## 8. Bugs reales que ya encontramos (para no repetirlos)

1. **SQLite + `TestClient` en threads distintos:** el fixture `db_session` en
   `tests/conftest.py` usa `poolclass=StaticPool` al crear el engine de SQLite en memoria. Sin
   esto, cada conexión nueva (y `TestClient` corre el endpoint en un hilo de threadpool distinto
   al del test) ve una base de datos en memoria *vacía y distinta*, y las tablas "desaparecen".
   Si creás una fixture de test nueva que abra su propio engine SQLite, copiá ese patrón.
2. **SQLAlchemy `Enum` + Python `enum.Enum` usa `.name` por defecto, no `.value`:** si declarás
   una columna `Enum` a partir de un `enum.Enum` de Python (como `EstadoClinica`, `RolUsuario`),
   SQLAlchemy por defecto serializa/lee usando el **nombre** del miembro (`ACTIVA`), no su
   **valor** (`activa`). Como la spec pide los valores en minúscula, hay que pasar
   `values_callable=lambda enum_cls: [e.value for e in enum_cls]` (mirá `models/clinica.py` y
   `models/usuario.py`). Esto NO se detecta en tests con SQLite (que no tiene ENUM nativo) —
   **solo revienta contra MySQL real**. Si agregás un enum nuevo en tu módulo, aplicá el mismo
   patrón desde el principio.

---

## 9. Cómo correr todo

**Entorno local (sin Docker), desde `backend/`:**
```bash
.venv/Scripts/python.exe -m pytest -v          # toda la suite
.venv/Scripts/python.exe -m pytest tests/test_algo.py -v   # un archivo puntual
```

**Docker (para probar contra MySQL real antes de dar un módulo por terminado):**
```bash
docker compose build backend
docker compose up -d
docker compose exec backend alembic upgrade head
```
El backend queda en `http://localhost:8000`. Hay una colección de Postman (`ClinicaWeb` en tu
workspace) con los endpoints de Módulo 1 y 2 ya armados, con scripts que encadenan tokens
automáticamente — puede servirte de referencia para armar las requests de tus módulos ahí mismo.

**Variables de entorno:** copiá `backend/.env.example` a `backend/.env` para desarrollo local, o
`.env.example` (raíz) a `.env` para Docker Compose.
