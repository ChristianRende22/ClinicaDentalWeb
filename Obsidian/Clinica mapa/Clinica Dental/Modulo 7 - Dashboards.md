#modulo7 #backend #pendiente

# Módulo 7 — Dashboards

**Estado:** ⬜ Siguiente · **Quién:** Christian
Enlaza a [[Roadmap]] · Depende de: [[Modulo 4 - Operacion Clinica Basica]],
[[Modulo 6 - Facturacion Extendida]]

## Qué debería construir (sin diseñar todavía)

Métricas y dashboards: citas por estado/doctor/rango, ingresos por período/método de pago,
facturas pendientes de cobro.

## Lo que ya está listo para apoyarse

- `CitaRepository.listar` ([[Modulo 4 - Operacion Clinica Basica]]) ya trae lo necesario para
  métricas de citas.
- `FacturaRepository`/`PagoRepository` ([[Modulo 6 - Facturacion Extendida]]) para ingresos.
- `Consulta`/`PlanTratamientoDetalle.estado` ([[Modulo 5 - Expediente Clinico Avanzado]]) para
  qué se atendió y qué se completó.

## Antes de empezar

Pasar por el flujo completo: brainstorming → spec → plan TDD → ejecución inline → verificación
Docker/MySQL → actualizar `docs/CONTEXTO-PROYECTO.md` → actualizar esta nota. Ver
[[Flujo de Trabajo con Claude]] y [[Convenciones de Arquitectura]].
