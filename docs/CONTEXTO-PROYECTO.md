# Contexto del Proyecto — ClinicaDentalWeb

**Para:** Meli (y su asistente de IA), para continuar con los Módulos 4 y 5.
**Última actualización:** 2026-07-31 — Módulos 1, 2 y 3 completos.

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
- `docs/superpowers/specs/2026-07-31-modulo-3-parametros-clinica-design.md` — spec del Módulo 3,
  incluye la tabla de decisiones de modelado con su justificación.
- `docs/superpowers/plans/2026-07-31-modulo-3-parametros-clinica-plan.md` — plan TDD del Módulo 3.
- `docs/superpowers/specs/2026-08-02-modulo-4-operacion-clinica-design.md` — spec del Módulo 4,
  incluye la máquina de estados de la cita y la justificación del diseño de validadores.
- `docs/superpowers/plans/2026-08-02-modulo-4-operacion-clinica-plan.md` — plan TDD del Módulo 4.
  **Leé el apéndice del final:** registra los cinco defectos críticos que encontraron las revisiones
  de código, todos fallas del plan y no de la implementación. Es la parte más instructiva del
  documento.

Cuando armes el spec/plan de tu módulo, seguí el mismo formato y ubicación
(`docs/superpowers/specs/YYYY-MM-DD-modulo-N-<nombre>-design.md` y el equivalente en `plans/`).

- `docs/superpowers/specs/2026-08-05-modulo-5-expediente-clinico-design.md` — spec del Módulo 5,
  incluye la política de bajas que quedó pendiente del Módulo 4 (sección 1) y las ocho decisiones
  de modelado (sección 2).
- `docs/superpowers/plans/2026-08-05-modulo-5-expediente-clinico-plan.md` — plan TDD del Módulo 5.

---

## 2. Roadmap completo (8 módulos)

| # | Módulo | Asignado | Estado |
|---|---|---|---|
| 1 | Tenancy + Auth core (`Clinica`, `Usuario`, JWT, bcrypt, aislamiento por clínica) | Christian | ✅ Completo |
| 2 | Panel superadministrador (CRUD clínicas, admin principal, feature flags) | Christian | ✅ Completo |
| 3 | Parámetros por clínica (`Especialidad`, `Consultorio`, `MetodoPago`, horario de atención, configuración) | **Meli** | ✅ Completo |
| 4 | Operación clínica básica (Pacientes, Odontólogos, Asistentes, Citas) | **Meli** | ✅ Completo |
| 5 | Expediente clínico avanzado (diagnósticos, odontogramas, planes de tratamiento, presupuestos, recetas) | **Meli** | ✅ Completo, verificado contra MySQL real |
| 6 | Facturación extendida | Christian | ⬜ Pendiente |
| 7 | Dashboards y métricas | Christian | ⬜ Pendiente |
| 8 | Notificaciones y recordatorios | Sin asignar | ⬜ Pendiente |

**Tu bloque (Meli) está completo hasta el Módulo 5.** El Módulo 6 (Christian) ahora puede apoyarse en
`PlanTratamiento` y `Presupuesto` de este módulo para "presupuesto → factura", además de en `Paciente`
y `Cita` del Módulo 4.

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
    postman/                     (una coleccion por modulo, ver seccion 9)
    CONTEXTO-PROYECTO.md          (este archivo)
  backend/
    .venv/                       (entorno virtual, no se commitea)
    requirements.txt
    .env.example                 (variables para desarrollo local sin Docker)
    pytest.ini
    alembic.ini
    scripts/
      seed_superadmin_dev.sql     (siembra el superadmin, SOLO desarrollo -- ver seccion 9)
    alembic/
      env.py
      versions/                  (0001_... a 0004_..., -- nunca edites una ya aplicada)
    app/
      config.py                  (Settings, lee de .env)
      db.py                      (engine, SessionLocal, get_db)
      exceptions.py               (TODAS las excepciones de dominio del proyecto viven aca)
      main.py                     (arma el FastAPI() e incluye los routers)
      models/                     (un archivo por entidad o grupo de entidades relacionadas)
                                   parametros.py = catalogos + horario + config (Modulo 3)
                                   personas.py   = Paciente, Doctor, Asistente, HorarioDoctor
                                   cita.py       = Cita, EstadoCita, TRANSICIONES_PERMITIDAS
      security/
        passwords.py               (hash_password, verify_password, generar_password_temporal)
        jwt.py                      (create_access_token, decode_access_token, TokenError)
      repositories/                (acceso a datos, ver seccion de convenciones)
                                   catalogo_repository.py = CRUD compartido de catalogos (Modulo 3)
      services/                    (logica de negocio que orquesta repositorios)
                                   validadores_cita.py = una clase por regla de agendamiento;
                                     el patron a copiar si tu operacion tiene varias reglas
      schemas/                     (Pydantic: un archivo por dominio, ej. auth.py, clinica.py)
      api/
        deps.py                     (get_current_user, require_roles, resolve_clinica_id,
                                     get_doctor_actual)
        routes/                     (un archivo por dominio, ej. auth.py, clinicas.py)
    tests/
      conftest.py                  (fixtures compartidas: db_session, client)
      factories.py                 (helpers compartidos: crear_clinica, crear_paciente,
                                    crear_doctor, crear_cita, token_de, auth... USALOS,
                                    no vuelvas a copiar el bloque en cada archivo)
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

## 6bis. Qué existe ya — Módulo 3 (Parámetros por Clínica)

**Modelos** (`app/models/parametros.py`, migración `0003`):
- `Especialidad`, `Consultorio`, `MetodoPago` — los tres catálogos comparten exactamente la misma
  forma: `id` propia, `id_clinica` (FK), `nombre` (`VARCHAR(50)`), `activo` (bool). Unicidad
  `(id_clinica, nombre)`: dos clínicas pueden tener ambas "Ortodoncia", la misma clínica no.
- `HorarioClinica` — horario de atención, **una fila por día**. Llave compuesta
  `(id_clinica, dia_semana)`. `hora_apertura`/`hora_cierre` son nullable (para los días cerrados)
  y `cerrado: bool` es explícito.
- `ConfiguracionClinica` — 1:1 con `Clinica` (`id_clinica` es PK **y** FK, así el esquema mismo
  impide dos configuraciones). Campos: `duracion_cita_minutos` (30), `porcentaje_impuesto`
  (`13.00`, IVA de El Salvador), `prefijo_factura` (`"F"`), `proximo_numero_factura` (1),
  `horas_minimas_cambio_cita` (24), `dias_minimos_reagendamiento` (3).
- `DiaSemana` — enum nuevo con `values_callable` (bug #2). Valores sin tilde: `miercoles`,
  `sabado`.
- `HORARIO_POR_DEFECTO` — constante con los 7 días: L-V abierto 08:00–17:00, sábado y domingo
  cerrados. **Única fuente de verdad** de esos defaults; la usan la ruta y los tests.

**`CatalogoRepository[T]` (`app/repositories/catalogo_repository.py`) — leelo antes de agregar
cualquier catálogo nuevo.** Hereda de `BaseRepository` e implementa **una sola vez** el CRUD de
los catálogos por clínica: filtro por `id_clinica`, nombre único (case-insensitive con
`func.lower()` explícito, contando los inactivos), borrado lógico y `listar(..., incluir_inactivos)`.
Los tres repos concretos son de dos líneas:

```python
class EspecialidadRepository(CatalogoRepository[Especialidad]):
    model = Especialidad
```

Si en tu módulo aparece otro catálogo por clínica (`TipoTratamiento`, etc.), heredá de acá en vez
de escribir el CRUD de nuevo.

**Dos repositorios más que NO heredan de `BaseRepository`** (misma lógica que las excepciones ya
documentadas): `HorarioClinicaRepository` (llave compuesta con un enum) y
`ConfiguracionClinicaRepository` (relación 1:1, la PK *es* `id_clinica`). Ambos igual exigen
`id_clinica` como primer parámetro.

**Endpoints** — `/especialidades`, `/consultorios`, `/metodos-pago` (CRUD completo, `DELETE`
desactiva y devuelve `204`), `GET`/`PUT /horarios`, `GET`/`PUT /configuracion`.

**Permisos del módulo, una sola regla sin excepciones: los 4 roles leen, solo `admin` y
`superadmin` escriben.** Cada router declara dos constantes (`LECTURA` y `ESCRITURA`) y las aplica
por endpoint, no a nivel de router.

**Este módulo es el primer consumidor de `resolve_clinica_id`.** Ningún endpoint recibe
`id_clinica` por URL ni por body: sale del JWT, o del header `X-Clinica-Id` si es superadmin.
Copiá ese patrón en los Módulos 4 en adelante.

**Dos comportamientos que sorprenden si no los sabés:**
- `GET /configuracion` **escribe**: si la clínica no tiene configuración, la crea con los defaults.
  Se decidió así para no tocar `ClinicaService` (Módulo 2) ni migrar las clínicas preexistentes.
- `GET /horarios` **no** escribe: devuelve siempre los 7 días, rellenando con
  `HORARIO_POR_DEFECTO` los que no tengan fila. `PUT /horarios` reemplaza la semana completa
  (los 7 días en un solo request) y valida todos los días antes de escribir ninguno.

**Excepciones nuevas** en `app/exceptions.py`: `NombreDuplicadoEnClinicaError` (→ `409`) y
`HorarioInvalidoError` (→ `422`).

**Lo que este módulo habilita:** en el Módulo 4, `Doctor.id_especialidad` y `Cita.id_consultorio`
como FK, la validación de que una cita caiga dentro del horario de atención, y las reglas de
cambio de cita. En el Módulo 6, `Factura.id_metodo_pago`, el impuesto y la numeración.

**Hueco conocido y decidido a conciencia:** un paciente puede cancelar con 24 h de anticipación y
reservar una cita nueva para mañana, esquivando la regla de los 3 días de reagendamiento.
Cerrarlo exigiría una anticipación mínima también para las reservas nuevas — queda como decisión
del Módulo 4.

---

## 6ter. Qué existe ya — Módulo 4 (Operación Clínica Básica)

**Modelos** (`app/models/personas.py` y `app/models/cita.py`, migración `0004`):

- `Paciente` — `id_paciente`, `id_clinica`, `nombre`, `apellido`, `fecha_nacimiento` (nullable),
  `telefono` (`varchar15`), `correo` (`varchar100`, nullable), `direccion`, `activo`, `created_at`.
  **Sin `id_usuario`:** el paciente no se loguea, es una ficha que la clínica opera en su nombre.
  **La edad no se almacena**, se calcula desde `fecha_nacimiento` y se expone en el schema de
  respuesta — guardarla la volvería mentira al día siguiente del cumpleaños.
- `Doctor` y `Asistente` — 1:1 con `Usuario` (`id_usuario` FK **única y no nula**, como manda el ERD
  to-be). `Doctor` agrega `id_especialidad` (FK a `Especialidad` del Módulo 3, **nullable**: una
  clínica recién creada no tiene el catálogo cargado y exigirla bloquearía el alta del primer doctor).
- `HorarioDoctor` — bloques de disponibilidad semanal. **PK propia, no compuesta** como
  `HorarioClinica`: un doctor atiende de 08:00 a 12:00, almuerza, y vuelve de 14:00 a 18:00. Unicidad
  `(id_doctor, dia_semana, hora_inicio)`. Reutiliza el enum `DiaSemana` del Módulo 3. No lleva
  `id_clinica`: se deduce del doctor, y el aislamiento lo garantiza el repositorio con un join.
- `Cita` — `id_paciente`, `id_doctor`, `id_consultorio` (nullable), `id_asistente` (nullable, quién
  la agendó), `fecha_hora`, `duracion_minutos`, `estado`, `motivo`, `veces_reagendada`. Sin
  `id_tratamiento`: eso es Módulo 5/6.
- `EstadoCita` — `programada`, `confirmada`, `completada`, `cancelada`, `no_asistio`. Con
  `values_callable`, como todos los enums del proyecto.
- `ConfiguracionClinica` gana `anticipacion_minima_reserva_horas` (default 24, rango 1–720).

**Dos decisiones de modelado que conviene no revertir:**

- **`Cita.duracion_minutos` se guarda, no se deriva de la configuración.** Es una foto del momento en
  que se agendó. Si se leyera de `ConfiguracionClinica` al mostrar la cita, cambiar la duración por
  defecto movería retroactivamente todas las citas ya agendadas y podría hacerlas chocar entre sí.
- **`veces_reagendada` en vez de un estado `reagendada`.** Reagendar es una transición, no una
  situación: un estado `reagendada` no responde "¿está confirmada o no?" y habría que acordarse de
  incluirlo en cada filtro de agenda activa.

**Alta y baja del personal — `PersonalService`.** Un solo `POST` crea el `Usuario` y el perfil en una
transacción, con `try` / `except` y `db.rollback()` explícito, copiando
`ClinicaService.crear_clinica_con_admin`. Devuelve la password temporal **una sola vez**; ningún
`GET` la expone. Es el **único** servicio del módulo que hace `commit()`.

`_cambiar_actividad` mueve la actividad del perfil **y la del `Usuario` juntas, en los dos
sentidos**: un profesional dado de baja no debe poder entrar al sistema, y uno reactivado tiene que
poder. Si se movieran por separado quedaría un doctor que aparece en los listados y al que se le
pueden agendar citas, pero que no puede loguearse.

Por eso el `PUT /doctores/{id}` y el `PUT /asistentes/{id}` **no** aplican `activo` con `setattr`:
lo sacan del body y lo delegan en el servicio. Y lo hacen **al final**, después de que el resto de la
actualización funcionó, porque el servicio commitea adentro: si se resolviera primero y después
fallara algo, la baja quedaría aplicada y el cliente recibiría un error creyendo que no se aplicó
nada. Un solo commit por request.

`PUT /pacientes/{id}` es distinto y conviene no confundirlos: ahí `activo` **sí** se aplica con
`setattr`, porque `Paciente` no tiene `Usuario` asociado y no hay nada que mantener sincronizado. Lo
que ese endpoint sí chequea a mano es el **permiso**: `activo` en el body exige un rol con permiso de
baja (`ROLES_BAJA`), porque los roles que pueden editar un paciente son más que los que pueden darlo
de baja.

**El diseño de validadores — leelo antes de tocar el agendamiento.** Agendar una cita tiene siete
reglas. En vez de siete `if` dentro de `CitaService`, **cada regla es un objeto independiente** en
`app/services/validadores_cita.py` con la interfaz `validar(ctx: ContextoCita) -> None` que lanza su
excepción de dominio. `CitaService` recorre la lista y **corta en el primero que falla**.

Los siete, en orden: referencias de la misma clínica, no en el pasado, anticipación mínima, dentro
del horario de la clínica, dentro del horario del doctor, sin choque de doctor, sin choque de
consultorio.

Tres consecuencias que valen para el Módulo 5:

- Cada regla se testea **sin base de datos y sin servicio**: se arma un `ContextoCita` a mano y se le
  pasan dobles a los validadores que consultan.
- Agregar una regla es un archivo nuevo más un renglón en `validadores_por_defecto`, **no** editar
  `CitaService`. Mismo criterio con el que el Módulo 3 justificó `MetodoPago` como tabla en vez de
  columnas booleanas: extender es dato o composición, no modificación.
- `ContextoCita.excluir_id_cita` hace que los mismos siete sirvan para crear y para reagendar: al
  reagendar se excluye la propia cita del chequeo de choques, si no chocaría contra sí misma.

**Máquina de estados.** `TRANSICIONES_PERMITIDAS` (en `app/models/cita.py`) es la **única** fuente de
verdad, y expresa "terminal" como conjunto vacío. `programada → confirmada | cancelada`;
`confirmada → completada | no_asistio | cancelada`; las otras tres son terminales. Solo se completa o
se marca ausente desde `confirmada`.

**Reagendar queda deliberadamente fuera de esa tabla:** no es una transición de estado sino un
movimiento de datos. Mueve la fila (misma `id_cita`), incrementa `veces_reagendada` y **resetea** el
estado a `programada`, porque la confirmación era para la hora vieja.

**`cambiar_estado` delega en `cancelar()` cuando el estado pedido es `cancelada`.** No es un detalle
de estilo: la tabla permite `programada → cancelada`, así que sin la delegación cualquiera podría
cancelar sobre la hora por esa vía y `horas_minimas_cambio_cita` quedaría decorativa.

**Endpoints.** `/pacientes`, `/doctores`, `/asistentes` (CRUD, `DELETE` da de baja lógica),
`GET`/`PUT /doctores/{id}/horarios` (reemplaza la semana completa), y `/citas` con `GET`, `POST`,
`GET /{id}`, `PATCH /{id}/estado`, `PATCH /{id}/cancelar` y `PATCH /{id}/reagendar`. **No hay
`DELETE /citas`**: una cita no se borra, se cancela — borrarla perdería el registro que el historial
del paciente y las métricas del Módulo 7 necesitan.

**Permisos — este módulo rompe a propósito la regla única del Módulo 3.** Aquel era configuración de
la clínica; esto es la operación diaria, y una asistente que no puede registrar un paciente ni
agendar una cita no puede hacer su trabajo. La regla que la reemplaza es igual de enunciable: **quien
ejecuta la operación en el mundo real puede registrarla en el sistema; quien administra la clínica
define quién trabaja en ella.**

| Recurso | Leer | Crear / editar | Dar de baja |
|---|---|---|---|
| Pacientes | los 4 roles | superadmin, admin, asistente, doctor | superadmin, admin |
| Doctores, asistentes | los 4 roles | superadmin, admin | superadmin, admin |
| Horario de un doctor | los 4 roles | superadmin, admin, y el propio doctor sobre el suyo | — |
| Citas | admin y asistente: todas. **Doctor: solo las suyas** | superadmin, admin, asistente | — (se cancela) |
| Estado de una cita | — | superadmin, admin, asistente, y el doctor de esa cita | — |

**El filtro del doctor sobre las citas es un `WHERE`, no un `403`.** `GET /citas` le inyecta
`id_doctor = <el suyo>` ignorando el que venga por query string, y una cita ajena por id devuelve
**404** — un 403 le confirmaría que existe, y eso ya es información sobre un paciente que no atiende.

**Y el chequeo se hace por rol, no por "tiene perfil".** `get_doctor_actual` devuelve `None` tanto
para "no es doctor" como para "es doctor sin fila `Doctor`", así que decidir por `is not None` hacía
que un doctor sin perfil viera **todas** las citas de la clínica. La falla tiene que cerrar, no
abrir. Si en el Módulo 5 agregás una vista filtrada por doctor, copiá este patrón, no el ingenuo.

**Excepciones nuevas** en `app/exceptions.py`: `ReferenciaInvalidaError`, `CitaEnElPasadoError`,
`AnticipacionInsuficienteError`, `FueraDeHorarioClinicaError`, `DoctorNoDisponibleError`,
`ChoqueDeCitaError` y `TransicionInvalidaError`. Traducción: los conflictos con el estado del sistema
van a **409** (`ChoqueDeCitaError`, `TransicionInvalidaError`), las violaciones de una regla sobre los
datos enviados a **422**.

**Qué se tocó de los Módulos 1 a 3**, y nada más: `app/api/deps.py` (se agregó `get_doctor_actual`),
y `app/models/parametros.py` más `app/schemas/parametros.py` (la columna nueva
`anticipacion_minima_reserva_horas`). No se tocó `ClinicaService`, `AuthService`,
`MODULOS_DISPONIBLES` ni ninguna migración ya aplicada.

**Helpers de test compartidos.** `tests/factories.py` (nuevo) trae `crear_clinica`, `crear_usuario`,
`token_de`, `auth`, `crear_paciente`, `crear_doctor`, `crear_asistente` y `crear_cita`. Usalos en el
Módulo 5 en vez de volver a copiar el bloque en cada archivo de test.

**Verificación contra el backend real:** `docs/postman/ClinicaDentalWeb-Modulo4.postman_collection.json`,
7 carpetas y 48 requests, ejecutable de punta a punta con Run Collection.

**Lo que este módulo habilita:** en el Módulo 5, `HistorialMedico.id_paciente`, los odontogramas y
planes de tratamiento colgando de `Paciente`, y `Tratamiento.id_doctor` (la FK `Cita.id_tratamiento`
se agrega ahí con una migración de una columna). En el 6, `Factura.id_paciente` y
`Factura.id_asistente`. En el 7, las métricas de citas por estado, doctor y rango — `CitaRepository.listar`
ya devuelve todo lo que necesitan. En el 8, los recordatorios sobre `Cita.fecha_hora`.

**Deuda conocida y decidida a conciencia:** el hueco de reagendamiento del Módulo 3 sigue abierto (ver
sección 11 del spec del Módulo 4), y no hay forma de regenerar una password temporal perdida — eso es
[BE-09 en Notion](https://app.notion.com/p/3b0a9ad7882681f7a53ec475508452ff), ticket aparte porque el
arreglo correcto cubre a los cuatro roles y es territorio de auth.

---

## 6quater. Qué existe ya — Módulo 5 (Expediente Clínico Avanzado)

**Resuelve primero la deuda de bajas del Módulo 4** (sección 11 de su spec): se adoptó la opción
recomendada, bloquear la baja si hay referencias activas. `PacienteRepository.eliminar` y
`PersonalService.dar_de_baja_doctor` ahora lanzan `ReferenciaEnUsoError` (→ `409`) si el paciente o
el doctor tiene un `PlanTratamiento` en `borrador`/`aprobado`/`en_progreso`. La deuda que **no**
resuelve (citas, consultorios y especialidades inactivos) sigue abierta a propósito — ver sección 7
del spec del Módulo 5.

**Modelos nuevos** (migración `0005`):
- `app/models/expediente.py` — `Tratamiento` (catálogo con precio, hereda `CatalogoRepository`),
  `Consulta`, `Diagnostico`, `Odontograma`, `PiezaDental`, `EstadoPiezaDental`.
- `app/models/plan_tratamiento.py` — `PlanTratamiento`, `PlanTratamientoDetalle`, sus dos enums y
  sus dos tablas de transiciones (`TRANSICIONES_PLAN_PERMITIDAS`,
  `TRANSICIONES_DETALLE_PERMITIDAS`), y `ESTADOS_PLAN_ACTIVOS` (la que usa la política de bajas).
- `app/models/presupuesto.py` — `Presupuesto`, 1:1 con `PlanTratamiento`, se **regenera** en vez de
  versionarse.
- `app/models/receta.py` — `Receta` + `RecetaDetalle` (una tabla de medicamentos, no texto libre).
- `Cita.id_tratamiento` (nullable): qué procedimiento se realizó en una cita puntual, sin exigirlo
  al agendar.

**Decisión de modelado que conviene no revertir:** `PlanTratamientoDetalle.precio_unitario` se copia
de `Tratamiento.precio` al agregar el detalle, no se lee en vivo — misma foto-del-momento que
`Cita.duracion_minutos` del Módulo 4. Si el catálogo sube de precio después, los detalles ya
agregados no se mueven.

**Repositorios y servicios**, ver la sección 3 y 4 del spec para el detalle completo. Los puntos que
no son obvios desde el nombre:
- `OdontogramaRepository` no hereda `BaseRepository` ni valida que el paciente sea de la clínica —
  esa validación es responsabilidad de la ruta (mismo criterio que `HorarioDoctorRepository`).
- El `PUT` del odontograma es un upsert **parcial** de piezas, a diferencia del `PUT /horarios` del
  Módulo 3/4 que reemplaza la semana completa.
- `PresupuestoService.generar_o_regenerar` hace upsert sobre el `Presupuesto` del plan; llamarlo dos
  veces no crea dos presupuestos.

**Endpoints nuevos:** `/tratamientos`, `/consultas` (+ `/consultas/{id}/diagnosticos`),
`/pacientes/{id}/odontograma`, `/planes-tratamiento` (+ `/detalles` y `/presupuesto` anidados),
`/presupuestos`, `/recetas`. La tabla de permisos completa, entidad por entidad, está en la sección 5
del spec — no es una regla única como el Módulo 3 ni como el Módulo 4, cada entidad cae en un lado
distinto de la tensión configuración/operación según quién la toca en la realidad.

**Defecto encontrado y corregido después del cierre inicial:** ni `DELETE /pacientes/{id}` ni
`DELETE`/`PUT /doctores/{id}` capturaban `ReferenciaEnUsoError` — un intento de baja con un plan de
tratamiento activo devolvía `500` en vez de `409`. Peor todavía, `PUT /pacientes/{id}` con
`{"activo": false}` ni siquiera llegaba a evaluar la política: pasaba por
`PacienteRepository.actualizar()` (un `setattr` genérico), no por `eliminar()`, así que la baja se
aplicaba igual sin chequear nada. La corrección separa `activo` del resto de los campos en el `PUT`
de pacientes (mismo patrón que ya usaba `actualizar_doctor` en el Módulo 4) y agrega el `except
ReferenciaEnUsoError` que faltaba en ambos routers. Regresión a nivel de ruta en
`tests/test_baja_bloqueada_routes_modulo5.py` — los tests de repositorio/servicio que ya existían
(`test_paciente_repository_baja_modulo5.py`, `test_personal_service_baja_modulo5.py`) nunca pasaban
por las rutas reales, por eso no lo detectaron.

**Verificación contra MySQL real: hecha (2026-08-06).** `alembic upgrade head` corrió limpio
(`0002 → 0003 → 0004 → 0005`) y los cuatro enums nuevos quedaron en minúscula
(`estado_pieza_dental`, `estado_plan_tratamiento`, `estado_detalle_plan_tratamiento`,
`estado_presupuesto`) — sin el bug de `values_callable`. Smoke test end-to-end vía HTTP: crear
clínica+admin → doctor → paciente → tratamiento → plan de tratamiento → detalle (el precio se
copia del catálogo, `25.00 x2` quedó congelado en el detalle) → generar presupuesto
(`monto_total: 50.00`, calculado bien) → odontograma con las 32 piezas por defecto. También se
confirmó el fix de bajas bloqueadas: `DELETE /pacientes/{id}` y
`PUT /pacientes/{id}` con `{"activo": false}` devuelven ambos `409` cuando el paciente tiene un
plan de tratamiento activo. Falta correr la colección de Postman completa
(`docs/postman/ClinicaDentalWeb-Modulo5.postman_collection.json`) para cobertura exhaustiva, pero
la verificación funcional ya no es una duda abierta.

**Lo que este módulo habilita:** en el Módulo 6, `PlanTratamiento` y `Presupuesto` son la base directa
de "presupuesto → factura" — `Presupuesto.monto_total` ya está calculado, solo falta convertirlo en
`Factura` con impuesto y numeración. En el Módulo 7, `Consulta` y `PlanTratamientoDetalle.estado` dan
métricas de qué se atendió y qué se completó, además de las que ya daba `Cita`.

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
3. **Un índice que está en la migración y no en el modelo es una divergencia silenciosa.** Los tests
   corren sobre `Base.metadata.create_all()`, así que validan el esquema del **modelo**; producción
   corre el de la **migración**. Si los dos no coinciden, los tests pasan sobre un esquema que no
   existe. Apareció con `ix_cita_doctor_fecha` en el Módulo 4. Mismo criterio para el nombre de los
   constraints: si la migración le pone nombre a un `UniqueConstraint`, el modelo también, o
   `alembic --autogenerate` va a marcar una diferencia falsa.
4. **Un campo que viaja en el body de un `PUT` esquiva la matriz de permisos.** Los repositorios
   aplican `data` con `setattr`, así que cualquier campo del schema `Update` es escribible por quien
   tenga permiso de edición — aunque ese campo represente una acción que su rol no tiene. Pasó dos
   veces en el Módulo 4: `{"activo": false}` en `PUT /pacientes` era una puerta trasera al `DELETE`,
   y `{"id_especialidad": <de otra clínica>}` en `PUT /doctores` esquivaba la validación que sí hace
   el `POST`. **Si un campo de un `Update` tiene una regla de negocio o un permiso propio, chequealo
   en la ruta o delegalo al servicio; no alcanza con que el schema lo acepte.**
5. **Una dependencia que devuelve `None` por dos motivos distintos hace fallar el sistema abierto.**
   `get_doctor_actual` devuelve `None` tanto para "no es doctor" como para "es doctor sin fila
   `Doctor`", y el filtro de citas decidía con `is not None` — así que un doctor sin perfil pasaba a
   ver **todas** las citas de la clínica en vez de ninguna. Cuando un chequeo de permisos dependa de
   que algo exista, decidí por el **rol** y hacé que la ausencia cierre, no que abra.

---

## 9. Cómo correr todo

**Entorno local (sin Docker), desde `backend/`:**
```bash
.venv/Scripts/python.exe -m pytest -v          # toda la suite
.venv/Scripts/python.exe -m pytest tests/test_algo.py -v   # un archivo puntual
```

**Docker (para probar contra MySQL real antes de dar un módulo por terminado):**
```bash
docker compose build backend      # OJO: hay que reconstruir cada vez que cambia el codigo
docker compose up -d
docker compose exec backend alembic upgrade head
```

El backend queda en `http://localhost:8000`.

**Tres cosas que muerden acá y que ya nos pasaron. Leelas antes de pelearte con Docker:**

1. **`docker compose build backend` no es opcional.** Si cambiaste código y solo hacés `up -d`,
   corre la imagen vieja. El síntoma es confuso: los endpoints nuevos dan `404`, o peor, dan `500`
   porque el código está pero la migración no corrió.
2. **El primer `alembic upgrade head` puede fallar con error 2003 (`Can't connect to MySQL server`).**
   No es tu culpa: el healthcheck de `db` en `docker-compose.yml` usa `mysqladmin ping -h localhost`,
   que devuelve `Healthy` mientras MySQL todavía está en su servidor temporal de inicialización. Con
   reintentar el comando a los pocos segundos alcanza. El arreglo de fondo (apuntar el healthcheck a
   `127.0.0.1` con usuario y password) es un pendiente del Módulo 1.
3. **Si recreás el volumen (`docker compose down -v`), desaparece el superadmin** y ninguna colección
   de Postman puede arrancar, porque todas empiezan logueándose con él. No hay script de seed todavía
   (pendiente del Módulo 1), así que hay que insertarlo a mano:
   ```powershell
   Get-Content backend/scripts/seed_superadmin_dev.sql | docker compose exec -T db mysql -u root -p<TU_DB_PASSWORD> clinica_dental_web
   ```
   La password de root es la que tenés en `DB_PASSWORD` de tu `.env`, y va **pegada** al `-p`, sin
   espacio. Crea `superadmin` / `Superadmin123`, que son las credenciales que las colecciones traen
   por defecto. El archivo es idempotente y está marcado como solo-desarrollo.

**Colecciones de Postman.** Una por módulo, en `docs/postman/`, versionadas en el repo:

- `ClinicaDentalWeb-Modulo3.postman_collection.json`
- `ClinicaDentalWeb-Modulo4.postman_collection.json` — 7 carpetas, 48 requests

Un archivo por módulo y no una colección que crece: así se puede verificar un módulo sin arrastrar
los demás, y el historial de cada uno queda claro. Todas arrancan con una carpeta `0. Setup` que
encadena los tokens y el `id_clinica` en variables de colección, así que son ejecutables de punta a
punta con **Run Collection** sin intervención manual. Cuando armes la del Módulo 5, copiá esa
estructura.

**Y no reemplazan a `pytest`.** Los tests corren contra SQLite y no ven la serialización real de
`datetime` ni de los enums; las colecciones corren contra MySQL sobre HTTP de verdad. Los dos bugs
conocidos de la sección 8 que "solo revientan en MySQL" se detectan acá, no en la suite.

**Variables de entorno:** copiá `backend/.env.example` a `backend/.env` para desarrollo local, o
`.env.example` (raíz) a `.env` para Docker Compose.
