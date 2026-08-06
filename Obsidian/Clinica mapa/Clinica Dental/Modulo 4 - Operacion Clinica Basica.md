#modulo4 #backend

# Módulo 4 — Operación Clínica Básica

**Estado:** ✅ Completo · **Quién:** Meli
Enlaza a [[Roadmap]] · Depende de: [[Modulo 3 - Parametros por Clinica]] · Habilita:
[[Modulo 5 - Expediente Clinico Avanzado]], [[Modulo 6 - Facturacion Extendida]],
[[Modulo 7 - Dashboards]]

## Qué construye

Pacientes, Doctores, Asistentes y Citas — el día a día de la clínica.

## Modelos

- `Paciente` — sin `Usuario` asociado (no se loguea). Edad se calcula, no se guarda.
- `Doctor`, `Asistente` — 1:1 con `Usuario`. `Doctor.id_especialidad` (nullable) referencia
  [[Modulo 3 - Parametros por Clinica]].
- `HorarioDoctor` — bloques semanales de disponibilidad, no hereda `BaseRepository` (ver
  [[Convenciones de Arquitectura]]).
- `Cita` — `duracion_minutos` se **guarda**, no se deriva de `ConfiguracionClinica` (foto del
  momento). `veces_reagendada` en vez de un estado `reagendada`.

## Lo importante

- **`PersonalService`** — alta/baja de Doctor/Asistente en una transacción, mismo patrón que
  `ClinicaService` ([[Modulo 2 - Panel Superadmin]]).
- **`validadores_cita.py`** — 7 reglas de agendamiento, cada una un objeto independiente (ver
  [[Convenciones de Arquitectura]]). Patrón de referencia para reglas de negocio complejas.
- **Máquina de estados de `Cita`** — `TRANSICIONES_PERMITIDAS`, única fuente de verdad.
  Reagendar NO es una transición: mueve la fila y resetea a `programada`.

## Permisos — rompe la regla única del Módulo 3 a propósito

Quien ejecuta la operación en el mundo real puede registrarla en el sistema. Doctor solo ve
**sus propias citas** — filtro `WHERE`, nunca `403` (ver [[Bugs Conocidos]] #5 y
[[Convenciones de Arquitectura]]).

## Bugs encontrados acá

[[Bugs Conocidos]] #3, #4, #5 — todos nacieron en este módulo.

## Ver también

`docs/postman/ClinicaDentalWeb-Modulo4.postman_collection.json` en el repo.
