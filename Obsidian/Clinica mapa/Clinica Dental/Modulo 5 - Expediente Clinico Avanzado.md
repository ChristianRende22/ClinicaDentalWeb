#modulo5 #backend

# Módulo 5 — Expediente Clínico Avanzado

**Estado:** ✅ Completo · **Quién:** Meli
Enlaza a [[Roadmap]] · Depende de: [[Modulo 4 - Operacion Clinica Basica]] · Habilita:
[[Modulo 6 - Facturacion Extendida]], [[Modulo 7 - Dashboards]]

## Qué construye

Diagnósticos, odontograma, planes de tratamiento, presupuestos y recetas.

## Modelos

- `Tratamiento` — catálogo con precio, hereda `CatalogoRepository` (ver
  [[Convenciones de Arquitectura]]).
- `Consulta`, `Diagnostico`, `Odontograma`/`PiezaDental`.
- `PlanTratamiento`/`PlanTratamientoDetalle` — máquina de estados propia para cada uno.
  `precio_unitario` se copia del catálogo al agregar (foto del momento, mismo criterio que
  `Cita.duracion_minutos` de [[Modulo 4 - Operacion Clinica Basica]]).
- `Presupuesto` — 1:1 con `PlanTratamiento`, se **regenera**, no se versiona.
  `Presupuesto.monto_total` es lo que [[Modulo 6 - Facturacion Extendida]] convierte en factura.
- `Receta`/`RecetaDetalle`.

## Lo importante

**Resuelve la deuda de bajas del Módulo 4**: `PacienteRepository.eliminar` y
`PersonalService.dar_de_baja_doctor` ahora lanzan `ReferenciaEnUsoError` (→ 409) si hay un
`PlanTratamiento` activo. Ver [[Bugs Conocidos]] #6 — el fix inicial no capturaba la excepción
en las rutas, corregido después con un test de ruta dedicado.

## Permisos

No es una regla única como el Módulo 3 ni el 4 — cada entidad cae en un lado distinto de la
tensión configuración/operación. Tabla completa en la spec del módulo.

## Ver también

`docs/postman/ClinicaDentalWeb-Modulo5.postman_collection.json`.
