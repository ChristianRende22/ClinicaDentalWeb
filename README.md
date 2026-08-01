# ClinicaDentalWeb

Plataforma web multi-clínica para gestión odontológica. Reescritura del sistema legacy
`ClinicaDental` (escritorio, PyQt6, una sola clínica) como backend FastAPI multi-tenant.

**Stack:** Python 3.12 · FastAPI · SQLAlchemy 2.0 · Alembic · MySQL 8 · JWT · bcrypt · pytest · Docker

Documentación del proyecto: [`docs/CONTEXTO-PROYECTO.md`](docs/CONTEXTO-PROYECTO.md) — qué existe,
qué convenciones seguir y qué bugs ya encontramos.

---

## Requisitos

- **Python 3.12** (no 3.13 ni 3.14: `passlib` depende del módulo `crypt`, eliminado en 3.13)
- **Docker Desktop** (solo para correr contra MySQL real)

Verificá qué versiones de Python tenés:

```powershell
py --list
```

Si no aparece la 3.12:

```powershell
py install 3.12
```

---

## Puesta en marcha local (sin Docker)

Todo desde la carpeta `backend/`.

### 1. Crear el entorno virtual e instalar dependencias

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

> En PowerShell las rutas relativas necesitan el prefijo `.\`. Sin él vas a ver
> `The term '.venv\Scripts\python.exe' is not recognized`.

### 2. Crear el archivo de configuración

```powershell
Copy-Item .env.example .env
```

Abrí `backend\.env` y poné una `JWT_SECRET_KEY` real (mínimo 32 caracteres, si no vas a ver
warnings de HMAC). Generala así:

```powershell
.\backend\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

### 3. Correr los tests

**No necesitás `.env` ni MySQL para esto:** `tests/conftest.py` setea las variables que hacen
falta y los tests corren contra SQLite en memoria.

```powershell
.\.venv\Scripts\python.exe -m pytest -q                       # toda la suite
.\.venv\Scripts\python.exe -m pytest tests/test_algo.py -v     # un archivo puntual
.\.venv\Scripts\python.exe -m pytest -k "especialidad" -v      # por nombre de test
```

### 4. Levantar la API

Necesita MySQL corriendo y `backend\.env` configurado apuntando a esa base.

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

- API: <http://localhost:8000>
- Documentación interactiva (Swagger): <http://localhost:8000/docs>

---

## Puesta en marcha con Docker (MySQL real)

Todo desde la **raíz del repo**.

### 1. Crear el archivo de configuración de compose

```powershell
Copy-Item .env.example .env
```

`JWT_SECRET_KEY` es **obligatoria**: si falta, `docker compose` ni siquiera arranca y tira
`required variable JWT_SECRET_KEY is missing a value`.

```
DB_PASSWORD=una-clave-cualquiera
DB_NAME=clinica_dental_web
JWT_SECRET_KEY=<generala con el comando de arriba>
```

### 2. Levantar los contenedores

```powershell
docker compose build backend
docker compose up -d
```

Levanta dos servicios: `db` (MySQL 8, puerto 3306) y `backend` (FastAPI, puerto 8000).

### 3. Aplicar las migraciones

```powershell
docker compose exec backend alembic upgrade head
```

> **En el primer arranque esto puede fallar con `2003 (HY000): Can't connect to MySQL server on
> 'db:3306' (111)`.** No es un error de tu código: con el volumen recién creado, MySQL inicializa
> la base con un servidor temporal, y el healthcheck del compose lo da por sano antes de tiempo.
> Esperá ~30 segundos, confirmá con `docker compose logs db --tail 5` que aparezca
> `ready for connections ... port: 3306` (la del servidor temporal dice `port: 0`) y reintentá.

### 4. Usar la API

<http://localhost:8000/docs>

### Comandos útiles de Docker

```powershell
docker compose ps                        # estado de los contenedores
docker compose logs backend --tail 50    # logs de la API
docker compose logs db --tail 50         # logs de MySQL
docker compose restart backend           # reiniciar solo el backend
docker compose down                      # bajar todo (conserva los datos)
docker compose down -v                   # bajar y BORRAR la base entera
```

**Importante:** cada vez que cambia el código o `requirements.txt` hay que reconstruir la imagen:

```powershell
docker compose build backend
docker compose up -d --force-recreate backend
```

---

## Migraciones (Alembic)

```powershell
# aplicar todas las pendientes
docker compose exec backend alembic upgrade head

# ver el historial y cuál es la head
docker compose exec backend alembic history

# ver en qué revisión está la base
docker compose exec backend alembic current

# retroceder una migración
docker compose exec backend alembic downgrade -1
```

Sin Docker, desde `backend/` y con MySQL accesible:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

**Regla:** nunca edites una migración ya aplicada o commiteada. Si hace falta cambiar algo, agregá
una nueva. Los archivos van en `backend/alembic/versions/` con ID secuencial (`0001`, `0002`, ...).

---

## Consultar la base directamente

```powershell
docker compose exec db mysql -uroot -p clinica_dental_web
```

Ejemplos de verificación:

```powershell
# ver la definición de una columna ENUM (deben estar en minúscula)
docker compose exec db mysql -uroot -p -e "SHOW COLUMNS FROM horario_clinica FROM clinica_dental_web LIKE 'dia_semana';"

# listar las tablas
docker compose exec db mysql -uroot -p -e "SHOW TABLES FROM clinica_dental_web;"
```

---

## Postman

En `docs/postman/` hay colecciones listas para importar (Postman → Import → File).

- `ClinicaDentalWeb-Modulo3.postman_collection.json` — 32 requests del Módulo 3, con asserts.

Uso: levantá el backend, asegurate de que exista un superadmin en la base, y corré primero la
carpeta **0. Setup** (hace login, crea una clínica de prueba y guarda los tokens en variables de
colección). Después podés usar **Run Collection** y ver todo en verde de una.

Si tu superadmin no es `superadmin` / `Superadmin123`, ajustá las variables de la colección.

---

## Verificación antes de cerrar un módulo

1. La suite completa en verde contra SQLite:
   `.\.venv\Scripts\python.exe -m pytest -q`
2. `alembic upgrade head` sin errores contra MySQL en Docker.
3. Los `ENUM` nuevos con sus valores en minúscula en MySQL (ver comando de arriba).
4. Un recorrido manual por `/docs` de los endpoints nuevos.

El punto 2 y 3 no son opcionales: los tests usan SQLite, que no tiene `ENUM` nativo, así que hay
bugs que **solo aparecen contra MySQL**. Está documentado en
[`docs/CONTEXTO-PROYECTO.md`](docs/CONTEXTO-PROYECTO.md), sección 8.

---

## Estructura

```
ClinicaDentalWeb/
  docker-compose.yml
  .env.example                 variables para docker compose (raíz)
  docs/
    CONTEXTO-PROYECTO.md       qué existe, convenciones, bugs conocidos
    superpowers/specs/         un documento de diseño por módulo
    superpowers/plans/         un plan TDD por módulo
  backend/
    .env.example               variables para desarrollo local
    requirements.txt
    alembic/versions/          migraciones
    app/
      config.py                Settings (lee de .env)
      db.py                    engine, SessionLocal, get_db
      exceptions.py            todas las excepciones de dominio
      main.py                  arma el FastAPI e incluye los routers
      models/                  entidades SQLAlchemy
      security/                hash de passwords y JWT
      repositories/            acceso a datos
      services/                lógica que coordina varios repositorios
      schemas/                 modelos Pydantic (entrada/salida)
      api/deps.py              get_current_user, require_roles, resolve_clinica_id
      api/routes/              un archivo por dominio
    tests/                     un archivo de test por módulo de app/
```

---

## Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| `The term '.venv\Scripts\python.exe' is not recognized` | Falta el `.\` de PowerShell. Usá `.\.venv\Scripts\python.exe` |
| `Python was not found; run without arguments to install from the Microsoft Store` | `python` no está en el PATH. Usá `py` o la ruta del venv |
| `No runtime installed that matches 3.12` | `py install 3.12` |
| Falla al instalar `bcrypt` | Estás usando Python 3.13+. El proyecto necesita 3.12 |
| `required variable JWT_SECRET_KEY is missing a value` | Falta el `.env` en la raíz (para Docker) |
| `2003 (HY000): Can't connect to MySQL server on 'db:3306' (111)` | MySQL todavía está inicializando. Esperá 30s y reintentá |
| Los cambios de código no se ven en Docker | Reconstruí: `docker compose build backend && docker compose up -d --force-recreate backend` |
| `InsecureKeyLengthWarning: The HMAC key is 15 bytes long` | La `JWT_SECRET_KEY` es corta. Usá una de 32+ caracteres |
