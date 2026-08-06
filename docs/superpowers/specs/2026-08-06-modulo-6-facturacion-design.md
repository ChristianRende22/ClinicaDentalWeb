# Diseño: Facturación Extendida — Módulo 6

**Fecha:** 2026-08-06
**Estado:** Aprobado para pasar a plan de implementación
**Depende de:** Módulo 3 (`ConfiguracionClinica.porcentaje_impuesto`/`prefijo_factura`/
`proximo_numero_factura`, catálogo `MetodoPago`), Módulo 4 (`Paciente`, `Doctor`), Módulo 5
(`Tratamiento`, `PlanTratamiento`, `Presupuesto`).

## 1. Contexto

El Módulo 5 dejó `Presupuesto` (1:1 con `PlanTratamiento`, `monto_total` calculado, estados
`vigente`/`aceptado`/`rechazado`/`vencido`) pero ningún camino para convertirlo en un cobro real.
El Módulo 3 dejó en `ConfiguracionClinica` los campos `porcentaje_impuesto`, `prefijo_factura` y
`proximo_numero_factura`, pensados exactamente para este momento pero sin ningún consumidor
todavía. Este módulo cierra ese circuito: genera facturas (desde un presupuesto aceptado, o
sueltas), aplica impuesto y numeración, y registra pagos parciales hasta saldar el total.

## 2. Alcance

Dentro de este módulo:
- `Factura` con líneas estructuradas (`FacturaDetalle`, mismo patrón "foto del precio" que
  `PlanTratamientoDetalle` del Módulo 5).
- Generar una factura desde un `Presupuesto` **aceptado** (copia sus líneas), o crearla suelta
  (sin plan de tratamiento de por medio).
- Numeración automática (`prefijo_factura` + correlativo de `ConfiguracionClinica`, incrementado
  atómicamente en la misma transacción de creación).
- Impuesto aplicado y **congelado** al emitir (`monto_impuesto` se guarda, no se recalcula si
  `porcentaje_impuesto` cambia después — mismo criterio que `Cita.duracion_minutos` del Módulo 4
  y `PlanTratamientoDetalle.precio_unitario` del Módulo 5: es una foto del momento, no un valor
  derivado en vivo).
- Pagos parciales: tabla `Pago`, una factura puede tener varios; el estado de la factura se
  deriva de la suma pagada vs. el total.
- Anular una factura (solo si no tiene pagos registrados).

Fuera de alcance:
- **Facturación electrónica (DTE, obligatoria en El Salvador).** Se decide explícitamente no
  implementarla en este módulo. `Factura.numero_factura` es un correlativo **interno**, no un
  Documento Tributario Electrónico — no tiene código de generación, sello de recepción de
  Hacienda, ni firma digital. Un módulo futuro puede agregar esos campos
  (`codigo_generacion`, `sello_recibido`, `numero_control`, etc.) con una migración nueva que
  solo agrega columnas nullable a `Factura`; nada de lo diseñado acá le cierra esa puerta ni
  necesita reescribirse cuando llegue.
- Reembolsos (anular una factura con pagos ya registrados queda fuera — habría que devolver
  dinero primero, y eso es un proceso, no un campo).
- Reportes de ingresos/facturación — eso es Módulo 7 (Dashboards), que va a consumir
  `FacturaRepository`/`PagoRepository` tal como ya consume `CitaRepository` hoy.
- Descuentos o notas de crédito.

## 3. Modelos

### `Factura` (tenant-scoped, hereda `BaseRepository`)

```
id_factura        PK, int autoincrement
id_clinica        FK -> clinica.id_clinica
id_paciente       FK -> paciente.id_paciente, obligatorio
id_doctor         FK -> doctor.id_doctor, nullable (responsable del tratamiento; nulo en
                   cargos administrativos sueltos que no vienen de un tratamiento clinico)
id_asistente      FK -> asistente.id_asistente, nullable (quien la emitio)
id_plan           FK -> plan_tratamiento.id_plan, nullable, UNIQUE (1:1 opcional: solo si
                   nacio de un presupuesto aceptado)
numero_factura    varchar(20), UNIQUE por clinica (prefijo + correlativo, ej. "F000001")
monto_subtotal    Numeric(10,2)
monto_impuesto    Numeric(10,2)   -- congelado al emitir
monto_total       Numeric(10,2)
estado            EstadoFactura: pendiente | parcial | pagada | anulada
fecha_emision     DateTime, server_default now()
```

### `FacturaDetalle` (child de `Factura`, NO hereda `BaseRepository` — mismo criterio que
`PlanTratamientoDetalle`: el aislamiento por clínica se garantiza con un `JOIN` contra `Factura`,
no con una columna `id_clinica` propia)

```
id_detalle        PK
id_factura        FK -> factura.id_factura
id_tratamiento    FK -> tratamiento.id_tratamiento
cantidad          int, default 1
precio_unitario   Numeric(10,2)   -- copiado de Tratamiento.precio al agregar la linea
```

### `Pago` (child de `Factura`, mismo criterio: NO hereda `BaseRepository`, join contra `Factura`)

```
id_pago           PK
id_factura        FK -> factura.id_factura
id_metodo_pago    FK -> metodo_pago.id_metodo_pago (catalogo del Modulo 3)
id_asistente      FK -> asistente.id_asistente, nullable (quien cobro)
monto             Numeric(10,2)
fecha_pago        DateTime, server_default now()
```

### `EstadoFactura`

```python
class EstadoFactura(str, enum.Enum):
    PENDIENTE = "pendiente"
    PARCIAL = "parcial"
    PAGADA = "pagada"
    ANULADA = "anulada"
```

Con `values_callable=lambda enum_cls: [e.value for e in enum_cls]` desde el día uno (bug #2 de
la sección 8 del contexto del proyecto — no darle la oportunidad de aparecer).

`pendiente`/`parcial`/`pagada` se **derivan** de `suma(Pago.monto) vs. Factura.monto_total`
cada vez que se registra un pago; no son un valor que el cliente pueda setear directamente.
`anulada` es la única transición manual, y solo alcanzable si `suma(Pago.monto) == 0`.

## 4. Repositorios y servicios

```
FacturaRepository          -- hereda BaseRepository (PK simple, id_clinica directo)
FacturaDetalleRepository   -- NO hereda (child de Factura, filtra via JOIN)
PagoRepository             -- NO hereda (child de Factura, filtra via JOIN)
```

### `FacturaService`

- `generar_desde_presupuesto(id_clinica, id_plan) -> Factura`
  1. Obtiene el `PlanTratamiento` y su `Presupuesto` (404 si no existen o no son de esa clínica).
  2. Exige `Presupuesto.estado == ACEPTADO` — si no, `PresupuestoNoAceptadoError` (409).
  3. Copia a `FacturaDetalle` cada `PlanTratamientoDetalle` con `estado != CANCELADO`
     (`id_tratamiento`, `cantidad`, `precio_unitario` tal cual están, sin recalcular).
  4. `monto_subtotal = suma(cantidad * precio_unitario)`; `monto_impuesto = subtotal *
     ConfiguracionClinica.porcentaje_impuesto / 100`; `monto_total = subtotal + impuesto`.
  5. Toma `numero_factura` de `ConfiguracionClinica` (`prefijo_factura` +
     `proximo_numero_factura` con padding a 6 dígitos) e **incrementa
     `proximo_numero_factura` en la misma transacción**.
  6. `id_paciente`/`id_doctor` se copian del `PlanTratamiento`. `estado = PENDIENTE`.
  7. Todo en un único `try`/`except` con `db.rollback()` explícito si algo falla — mismo patrón
     que `ClinicaService.crear_clinica_con_admin` y `PersonalService` del Módulo 4: nada de esto
     queda a medias.

- `crear_suelta(id_clinica, id_paciente, id_doctor, lineas: list[dict]) -> Factura`
  Mismo cálculo de subtotal/impuesto/total y misma numeración atómica que arriba, sin plan de
  por medio; `id_plan = None`. `lineas` es `[{"id_tratamiento": int, "cantidad": int}]`, el
  precio se copia del catálogo `Tratamiento` en el momento.

- `anular(id_clinica, id_factura) -> Factura`
  Si `PagoRepository.listar_de_factura(...)` no está vacío: `FacturaConPagosError` (409). Si no,
  `estado = ANULADA`.

### `PagoService`

- `registrar_pago(id_clinica, id_factura, monto, id_metodo_pago, id_asistente=None) -> Pago`
  1. `Factura.estado == ANULADA` → `FacturaAnuladaError` (409).
  2. `saldo_pendiente = Factura.monto_total - suma(Pago.monto existentes)`; si
     `monto > saldo_pendiente` → `PagoExcedeSaldoError` (422).
  3. Inserta el `Pago`, recalcula y guarda el nuevo `Factura.estado`
     (`pagada` si el saldo llega a 0, `parcial` si queda un resto, nunca vuelve a `pendiente`
     una vez que hubo algún pago).

## 5. Endpoints

```
POST   /planes-tratamiento/{id_plan}/factura   -- genera desde presupuesto aceptado
POST   /facturas                                -- suelta, con lineas en el body
GET    /facturas                                -- lista (doctor: filtrada por su id, via WHERE)
GET    /facturas/{id_factura}
PATCH  /facturas/{id_factura}/anular
POST   /facturas/{id_factura}/pagos             -- registrar un pago
GET    /facturas/{id_factura}/pagos             -- historial de pagos de esa factura
```

Todos resuelven `id_clinica` vía `resolve_clinica_id` (Módulo 1) — ningún endpoint la recibe por
URL ni por body, mismo patrón desde el Módulo 3.

## 6. Permisos

| Recurso | Leer | Crear / anular / cobrar |
|---|---|---|
| Facturas | superadmin, admin, asistente: todas. **Doctor: solo las suyas** (`GET /facturas` filtra por `id_doctor` propio vía `WHERE`, igual que `GET /citas` del Módulo 4; una factura ajena por id da **404**, no 403 — mismo criterio de "la falla cierra, no confirma que el recurso existe") | superadmin, admin, asistente |
| Pagos | mismo criterio que la factura a la que pertenecen | superadmin, admin, asistente |

Doctor nunca crea, anula ni cobra — solo consulta. Es dinero, y quien cobra en la realidad de la
clínica es admin o asistente en recepción, no el doctor en el consultorio.

## 7. Excepciones nuevas

En `app/exceptions.py`: `PresupuestoNoAceptadoError` (→ 409), `FacturaConPagosError` (→ 409),
`FacturaAnuladaError` (→ 409), `PagoExcedeSaldoError` (→ 422).

## 8. Deuda conocida y decidida a conciencia

- **Numeración sin lock explícito.** `proximo_numero_factura` se lee e incrementa dentro de la
  misma transacción SQL, pero sin `SELECT ... FOR UPDATE`. Con el volumen de una sola
  recepcionista emitiendo facturas, el riesgo de dos requests concurrentes exactos es
  despreciable; si se vuelve un problema real (varias cajas cobrando a la vez), un lock a nivel
  de fila sobre `ConfiguracionClinica` es el arreglo, sin tocar el resto del diseño.
- **Facturación electrónica:** ver sección 2, fuera de alcance a propósito, sin bloquear el
  módulo futuro.
