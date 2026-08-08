#modulo7 #backend #completo

# Módulo 7 — Dashboards

**Estado:** ✅ Completo · **Quién:** Christian
Enlaza a [[Roadmap]] · Depende de: [[Modulo 4 - Operacion Clinica Basica]],
[[Modulo 6 - Facturacion Extendida]]

## Qué construye

Tres endpoints de solo lectura en `app/api/routes/dashboards.py`, sin modelos ni migraciones
nuevas — todo se agrega sobre `Cita`, `Factura` y `Pago` ya existentes:

- `GET /dashboard/citas/resumen` — conteo de citas por estado, rango de fechas y doctor. Los 4
  roles, con el doctor forzado a sus propias citas (mismo criterio de [[Convenciones de
  Arquitectura]]: filtro por WHERE, no 403).
- `GET /dashboard/ingresos` — dinero **cobrado** (no facturado) por período y método de pago, con
  serie temporal agrupable por día/semana/mes. Solo superadmin/admin.
- `GET /dashboard/facturas-pendientes` — facturas en estado pendiente/parcial con saldo pendiente
  calculado. Solo superadmin/admin, sin filtro de fecha por default.

## Decisión que vale la pena recordar

`PagoRepository._expr_periodo` agrupa fechas en SQL con una rama explícita por dialecto
(`sqlite`/`mysql`) — a diferencia de `CitaRepository._solapadas` (Módulo 4), que resuelve el mismo
tipo de riesgo calculando en Python. Se aceptó el riesgo por eficiencia, y se verificó
explícitamente contra MySQL real (los tres `agrupar_por` funcionaron sin error de SQL) antes de
cerrar el módulo. Ver [[Bugs Conocidos]] si esto vuelve a morder.

## Cambio de flujo en este módulo

Este fue el primer módulo ejecutado con **subagent-driven-development** en vez de ejecución
inline (Módulos 1-6) — ver [[Flujo de Trabajo con Claude]]. Cada tarea del plan se implementó y
revisó con subagentes frescos, con commit por tarea automático.

## Deuda conocida

No incluye métricas de tratamientos/consultas (`Consulta`, `PlanTratamientoDetalle.estado`) —
alcance recortado a propósito en el brainstorming. Los datos ya están listos si se pide después.

## Detalle completo

`docs/CONTEXTO-PROYECTO.md` sección 6sexies. Spec:
`docs/superpowers/specs/2026-08-08-modulo-7-dashboards-design.md`. Plan:
`docs/superpowers/plans/2026-08-08-modulo-7-dashboards-plan.md`.
