# Diseño: Panel Superadministrador — Módulo 2

**Fecha:** 2026-07-30
**Estado:** Aprobado para pasar a plan de implementación
**Depende de:** Módulo 1 (Tenancy + Auth core) — ya implementado y en `main`.

## 1. Contexto

El Módulo 1 dejó listas las tablas `Clinica`, `Usuario` y `ClinicaModulo`, el login con JWT y el
mecanismo de aislamiento por `id_clinica`, pero dejó **explícitamente fuera de alcance** el CRUD
de clínicas ("Módulo 2, fuera de alcance aquí" — spec de Módulo 1, sección 6). Este documento
cubre ese CRUD: el panel desde el cual el superadmin crea, edita, activa/suspende clínicas,
les asigna un administrador principal y controla qué módulos tiene habilitados cada una.

## 2. Alcance

Dentro de este módulo:
- CRUD de `Clinica` (crear, listar, ver detalle, editar datos generales)
- Cambiar `estado` de una clínica (activa/suspendida/inactiva)
- Crear el admin principal de una clínica **en el mismo request** que crea la clínica
- Prender/apagar módulos individuales por clínica (`ClinicaModulo`)
- Flujo de cambio de password obligatorio para el admin recién creado (login con password
  temporal → forzado a cambiarla)

Fuera de alcance (quedan para módulos posteriores):
- Parámetros operativos de la clínica (horarios, especialidades, consultorios, precios) → Módulo 3
- Dashboards/métricas → Módulo 7
- Bloqueo de otros endpoints mientras `debe_cambiar_password=True` (por ahora es responsabilidad
  del frontend redirigir a la pantalla de cambio de password; no se fuerza a nivel de cada
  endpoint del backend — evita sobre-ingeniería en esta etapa)
- Reenviar o recuperar la password temporal después de la creación (si se pierde, el superadmin
  tendría que resetearla — ese endpoint de reset no existe todavía y no es parte de este módulo)

## 3. Cambios al modelo de datos

### `Usuario` (modifica el modelo del Módulo 1)

Se agrega una columna nueva:

```
debe_cambiar_password: bool, default True, server_default '1'
```

Migración nueva `0002_usuario_debe_cambiar_password.py` (no se toca la `0001`, ya aplicada).
Los usuarios ya existentes (creados en Módulo 1 vía scripts de prueba) quedan con
`debe_cambiar_password=True` por el `server_default` — comportamiento aceptable, no hay usuarios
reales en producción todavía.

### `Clinica` y `ClinicaModulo`
Sin cambios de esquema — ya existían desde el Módulo 1.

## 4. Endpoints

Todos bajo el prefijo `/clinicas`, protegidos con `require_roles(RolUsuario.SUPERADMIN)`
(dependencia ya existente desde el Módulo 1, sin cambios).

| Método y ruta | Descripción |
|---|---|
| `POST /clinicas` | Crea la clínica **y** su admin principal en una sola transacción. Ver detalle abajo. |
| `GET /clinicas` | Lista todas las clínicas. Filtro opcional `?estado=activa\|suspendida\|inactiva`. |
| `GET /clinicas/{id_clinica}` | Detalle de una clínica. |
| `PUT /clinicas/{id_clinica}` | Edita `nombre`, `direccion`, `telefono`, `correo`. |
| `PATCH /clinicas/{id_clinica}/estado` | Cambia el `estado` (activa/suspendida/inactiva). |
| `PATCH /clinicas/{id_clinica}/modulos/{modulo}` | Body `{"habilitado": bool}` — prende/apaga un módulo puntual. |

### `POST /clinicas` en detalle

Request:
```json
{
  "nombre": "Dental Smiling",
  "direccion": "San Salvador",
  "telefono": "22334455",
  "correo": "contacto@dentalsmiling.com",
  "admin_username": "admin.dentalsmiling"
}
```

Proceso (una sola transacción de BD):
1. Crear la `Clinica` con `estado=ACTIVA`.
2. Insertar las 8 filas de `ClinicaModulo` (`pacientes`, `citas`, `odontogramas`,
   `presupuestos`, `recetas`, `facturacion`, `dashboards`, `notificaciones`), todas con
   `habilitado=True`.
3. Generar una password temporal aleatoria (`secrets.token_urlsafe`, 16 bytes → string legible).
4. Crear el `Usuario` admin: `username=admin_username`, `password_hash=hash(temporal)`,
   `rol=ADMIN`, `id_clinica=<la recién creada>`, `debe_cambiar_password=True`.
5. Devolver la clínica creada **y** la password temporal en texto plano (única vez que se
   expone). Si algo fallara en el paso 2-4, la transacción entera se revierte (no queda una
   clínica huérfana sin admin).

Response:
```json
{
  "clinica": { "id_clinica": 1, "nombre": "Dental Smiling", "estado": "activa", "...": "..." },
  "admin": { "id_usuario": 1, "username": "admin.dentalsmiling" },
  "password_temporal": "kX9f-3mQpR7vNc2Z"
}
```

## 5. Cambio de password obligatorio

- `POST /auth/cambiar-password` (nuevo, bajo el router de auth ya existente): requiere estar
  autenticado (`get_current_user`), recibe `{"password_actual": "...", "password_nueva": "..."}`.
  Verifica `password_actual` contra el hash guardado, hashea `password_nueva`, actualiza
  `password_hash` y pone `debe_cambiar_password=False`.
- `AuthService.login()` (Módulo 1) y `GET /auth/me` ahora exponen `debe_cambiar_password` en la
  respuesta, para que el frontend decida si redirige a la pantalla de cambio de password. El
  backend no bloquea otros endpoints mientras el flag esté en `True` — es una decisión de UX,
  no de seguridad de datos (a diferencia del aislamiento por clínica, que sí se fuerza siempre).

## 6. Repositorios

### `ClinicaRepository` (nuevo, NO hereda de `BaseRepository`)

`Clinica` es la unidad de tenancy en sí misma — a diferencia de un recurso *dentro* de una
clínica (como serán `Paciente`/`Doctor`/`Cita` en el Módulo 4), no tiene sentido filtrar
`Clinica` por `id_clinica`. Es un repositorio de alcance de plataforma, exclusivo del superadmin.

Métodos: `listar(estado: EstadoClinica | None) -> list[Clinica]`,
`obtener(id_clinica: int) -> Clinica | None`, `crear(data: dict) -> Clinica`,
`actualizar(id_clinica: int, data: dict) -> Clinica | None`,
`cambiar_estado(id_clinica: int, estado: EstadoClinica) -> Clinica | None`.

### `ClinicaModuloRepository` (nuevo, NO hereda de `BaseRepository`)

Su llave compuesta (`id_clinica` + `modulo`, un string) no encaja con la firma abstracta de
`BaseRepository` (que asume un id entero como segunda parte de la llave). Igual exige
`id_clinica` como primer parámetro en todos sus métodos, manteniendo el espíritu de la regla
del Módulo 1, solo que como repositorio independiente en vez de subclase.

Métodos: `sembrar_modulos_default(id_clinica: int) -> None` (crea las 8 filas al crear una
clínica), `listar(id_clinica: int) -> list[ClinicaModulo]`,
`actualizar_estado(id_clinica: int, modulo: str, habilitado: bool) -> ClinicaModulo | None`.

`MODULOS_DISPONIBLES` se define como constante (lista de los 8 strings) en el mismo archivo del
repositorio — es la única fuente de verdad de qué módulos existen en el sistema.

## 7. Validación

- `correo` en los schemas de request usa `pydantic.EmailStr` (requiere el extra
  `pydantic[email]`) en vez de reinventar una regex como hacía el modelo legacy
  (`Paciente.validar_formato_email`). Se agrega `email-validator` a `requirements.txt`.
- `nombre` de clínica: requerido, no vacío.
- `admin_username`: mismo constraint que `Usuario.username` del Módulo 1 (único, `VARCHAR(30)`).
  Si ya existe, `POST /clinicas` responde `409 Conflict` (nuevo caso de error, no existía en
  Módulo 1 porque ahí no había endpoint de registro de usuarios).

## 8. Fuera de alcance (recordatorio)

- Parámetros por clínica (Módulo 3)
- Dashboards (Módulo 7)
- Reset de password para un admin que perdió su password temporal
- Forzar `debe_cambiar_password` a nivel de middleware/dependencia global
