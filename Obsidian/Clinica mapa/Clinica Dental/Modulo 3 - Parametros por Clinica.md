#modulo3 #backend

# Módulo 3 — Parámetros por Clínica

**Estado:** ✅ Completo · **Quién:** Meli
Enlaza a [[Roadmap]] · Depende de: [[Modulo 1 - Tenancy y Auth]] · Habilita:
[[Modulo 4 - Operacion Clinica Basica]], [[Modulo 6 - Facturacion Extendida]]

## Qué construye

La configuración operativa de cada clínica: catálogos, horario de atención, parámetros
escalares (impuesto, numeración de facturas, duración de citas).

## Modelos

- `Especialidad`, `Consultorio`, `MetodoPago` — mismo shape (`id`, `id_clinica`, `nombre`,
  `activo`), CRUD compartido vía `CatalogoRepository[T]` (ver
  [[Convenciones de Arquitectura]]).
- `HorarioClinica` — una fila por día de la semana, llave compuesta.
- `ConfiguracionClinica` — 1:1 con `Clinica` (la PK es `id_clinica`). Campos clave que usan
  módulos futuros: `porcentaje_impuesto`, `prefijo_factura`, `proximo_numero_factura` (los
  consume [[Modulo 6 - Facturacion Extendida]]); `duracion_cita_minutos`,
  `anticipacion_minima_reserva_horas` (los consume
  [[Modulo 4 - Operacion Clinica Basica]]).

## Lo importante

Este es el **primer consumidor de `resolve_clinica_id`** ([[Modulo 1 - Tenancy y Auth]]) —
ningún endpoint recibe `id_clinica` por URL ni body, siempre sale del JWT o del header. Todos
los módulos siguientes copian este patrón.

`GET /configuracion` **escribe** (crea la config con defaults si no existe) —
`GET /horarios` **no** escribe (rellena con defaults en memoria sin persistir).

## Permisos

Regla única sin excepciones: los 4 roles leen, solo `admin`/`superadmin` escriben.
[[Modulo 4 - Operacion Clinica Basica]] rompe esta regla a propósito — ver esa nota.

## Deuda conocida

Un paciente puede esquivar `dias_minimos_reagendamiento` cancelando y reservando de nuevo.
Decisión consciente, queda para cuando alguien lo priorice.
