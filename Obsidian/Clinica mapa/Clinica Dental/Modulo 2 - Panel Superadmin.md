#modulo2 #backend

# Módulo 2 — Panel Superadmin

**Estado:** ✅ Completo · **Quién:** Christian
Enlaza a [[Roadmap]] · Depende de: [[Modulo 1 - Tenancy y Auth]] · Habilita:
[[Modulo 3 - Parametros por Clinica]] en adelante (todas las clínicas se crean desde acá)

## Qué construye

El CRUD de clínicas para el superadmin: crear, editar, activar/suspender, y controlar qué
módulos tiene habilitados cada una.

## Lo importante

- `ClinicaService.crear_clinica_con_admin` — crea la `Clinica` + siembra los 8
  `ClinicaModulo` + crea el `Usuario` admin con password temporal, todo en **una transacción**
  (`try`/`except`+`db.rollback()`, patrón de referencia para
  [[Convenciones de Arquitectura]]).
- `MODULOS_DISPONIBLES` — única fuente de verdad de qué módulos existen en el sistema
  (`pacientes`, `citas`, `odontogramas`, `presupuestos`, `recetas`, `facturacion`,
  `dashboards`, `notificaciones`).
- Flujo de password temporal: `Usuario.debe_cambiar_password` (default `True`), expuesto en
  `/auth/login` y `/auth/me`, se apaga vía `POST /auth/cambiar-password`. El backend no bloquea
  otros endpoints mientras esté en `True` — decisión de UX, no de seguridad de datos.

## Endpoints

`POST/GET /clinicas`, `GET/PUT /clinicas/{id}`, `PATCH /clinicas/{id}/estado`,
`PATCH /clinicas/{id}/modulos/{modulo}`, `POST /auth/cambiar-password`.

## Ver también

[[Modulo 1 - Tenancy y Auth]] (de donde hereda `Usuario`/`Clinica`).
