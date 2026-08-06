#modulo1 #backend

# Módulo 1 — Tenancy y Auth

**Estado:** ✅ Completo · **Quién:** Christian
Enlaza a [[Roadmap]] · Depende de: — · Habilita: [[Modulo 2 - Panel Superadmin]] y todo lo demás

## Qué construye

Los cimientos multi-clínica: `Clinica`, `Usuario`, login con JWT, passwords con bcrypt, y el
mecanismo que fuerza el aislamiento por clínica en todo el backend.

## Modelos

- `Clinica` — `id_clinica`, `nombre`, `direccion`, `telefono`, `correo`, `estado`
  (`activa`/`suspendida`/`inactiva`).
- `ClinicaModulo` — llave compuesta `(id_clinica, modulo)`, feature flags por clínica (los usa
  [[Modulo 2 - Panel Superadmin]]).
- `Usuario` — `id_clinica` **nullable** (`NULL` = superadmin, no pertenece a ninguna clínica),
  `username` único, `password_hash`, `rol` (`superadmin`/`admin`/`doctor`/`asistente`).

## Lo importante: `BaseRepository`

Este módulo introduce la regla dura de todo el proyecto — ver [[Convenciones de Arquitectura]].
Todo repositorio de un recurso *dentro* de una clínica hereda de acá y exige `id_clinica` como
primer parámetro obligatorio.

## Auth

- `AuthService.login()` → JWT con `sub`, `id_clinica`, `rol`. Bloquea si
  `Clinica.estado != activa` (salvo superadmin).
- `app/api/deps.py`: `get_current_user`, `require_roles(*roles)`, `resolve_clinica_id` (la
  clínica del propio usuario, o la del header `X-Clinica-Id` si es superadmin).

## Endpoints

`POST /auth/login`, `GET /auth/me`, `POST /auth/logout`.

## Bugs encontrados acá

[[Bugs Conocidos]] #1 (SQLite StaticPool) y #2 (enum `.name` vs `.value`) — ambos aparecieron
primero en este módulo.

## Deuda pendiente

No hay forma de regenerar una password temporal perdida — ticket `BE-09` en
[[Referencias Externas]].
