#modulo6 #backend

# Módulo 6 — Facturación Extendida

**Estado:** ✅ Completo, verificado contra MySQL real · **Quién:** Christian
Enlaza a [[Roadmap]] · Depende de: [[Modulo 3 - Parametros por Clinica]],
[[Modulo 5 - Expediente Clinico Avanzado]] · Habilita: [[Modulo 7 - Dashboards]]

## Qué construye

Convierte un `Presupuesto` aceptado en una `Factura` real, o factura suelto sin plan; aplica
impuesto y numeración de `ConfiguracionClinica`; registra pagos parciales.

## Modelos

- `Factura` — `id_plan` nullable único (1:1 opcional con `PlanTratamiento`), `id_doctor`
  nullable, `numero_factura` único por clínica, `monto_subtotal`/`monto_impuesto`/`monto_total`
  congelados al emitir. `EstadoFactura`: `pendiente|parcial|pagada|anulada`.
- `FacturaDetalle`, `Pago` — child de `Factura`, sin `id_clinica` propio, join contra `Factura`
  (mismo criterio que `PlanTratamientoDetalle` del [[Modulo 5 - Expediente Clinico Avanzado]]).

**`numero_factura` es un correlativo interno, NO un DTE** (facturación electrónica, obligatoria
en El Salvador). Decisión explícita: no se implementa en este módulo. Un módulo futuro puede
agregar `codigo_generacion`/`sello_recibido` con una migración de columnas nullable, sin romper
nada de esto.

## Lo importante

- `FacturaService._emitir` — punto único de cálculo, usado por `generar_desde_presupuesto`
  (copia líneas de un Presupuesto `ACEPTADO`) y `crear_suelta` (líneas ad-hoc). Calcula
  impuesto desde `ConfiguracionClinica.porcentaje_impuesto` ([[Modulo 3 - Parametros por Clinica]]),
  arma `numero_factura`, **incrementa el correlativo en la misma transacción**.
- `PagoService.registrar_pago` — rechaza sobre factura anulada o pago que excede el saldo;
  recalcula el estado de la factura.
- Anular solo si la factura no tiene pagos registrados.

## Permisos

Superadmin/admin/asistente escriben; **doctor solo lee, y solo las suyas** — mismo patrón
`WHERE` no `403` que [[Modulo 4 - Operacion Clinica Basica]].

## Endpoints

`POST /planes-tratamiento/{id_plan}/factura` (anidado, no en `/facturas`),
`POST/GET /facturas`, `GET /facturas/{id}`, `PATCH /facturas/{id}/anular`,
`POST/GET /facturas/{id}/pagos`.

## Verificado contra MySQL real (2026-08-06)

Flujo completo probado por HTTP: plan→presupuesto aceptado→factura (impuesto 13% correcto,
numeración correlativa)→pago parcial→pago que completa→anular bloqueado con pagos→sobrepago
bloqueado→factura suelta y anulación sin pagos.
