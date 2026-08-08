# Módulo 7 — Dashboards y métricas — Spec de diseño

**Fecha:** 2026-08-08
**Depende de:** Módulo 4 (Operación Clínica Básica — `Cita`), Módulo 6 (Facturación Extendida —
`Factura`, `Pago`).
**No agrega modelos ni migraciones.** Todo se calcula sobre datos existentes.

---

## 1. Alcance

Tres métricas, sin más — decisión explícita durante el brainstorming: **no** se suma una cuarta
métrica de tratamientos/consultas (`Consulta`, `PlanTratamientoDetalle.estado`) aunque el mapa del
proyecto la mencionaba como dato disponible. Queda fuera de este módulo.

1. **Resumen de citas** por estado, rango de fechas y doctor.
2. **Ingresos** (dinero efectivamente cobrado) por período y método de pago, con serie temporal
   agrupable por día/semana/mes.
3. **Facturas pendientes de cobro** (estado `pendiente` o `parcial`), listado con saldo pendiente
   calculado + totales.

Todos son endpoints de **solo lectura**. No hay `Create`/`Update`/`Delete`.

---

## 2. Decisiones de diseño

### 2.1 Sin `DashboardService`

Las tres métricas son lecturas puras que no coordinan una transacción ni escriben en más de una
tabla — no encajan en el criterio que el proyecto usa para justificar un service (`ClinicaService`,
`PersonalService`, `FacturaService._emitir`, todos con `commit()` propio). Se agregan métodos de
agregación directamente a los repositorios existentes (`CitaRepository`, `FacturaRepository`,
`PagoRepository`), y la ruta nueva (`app/api/routes/dashboards.py`) los llama directo — mismo
patrón que ya usa `app/api/routes/clinicas.py` para CRUD simple.

### 2.2 Ingresos = cobrado, no facturado

`suma(Pago.monto)`, no `suma(Factura.monto_total)`. Una factura pendiente está facturada pero no
cobrada; el dashboard de ingresos tiene que reflejar caja real, no lo emitido.

### 2.3 Rangos de fecha: default mes actual, salvo facturas pendientes

`GET /dashboard/citas/resumen` y `GET /dashboard/ingresos` usan `desde`/`hasta` con default el
primer y último día del mes en curso si no se pasan — el caso más común es "el dashboard de ahora".

`GET /dashboard/facturas-pendientes` es distinto a propósito: una factura pendiente de hace tres
meses sigue siendo cobrable hoy, así que sus `desde`/`hasta` son opcionales **sin default** (sin
límite si no se pasan) — filtran por `fecha_emision` solo si el cliente los pide, para acotar un
listado que creció mucho.

### 2.4 Agregación de la serie temporal: en SQL, no en Python

`agrupar_por=semana|mes` en `/dashboard/ingresos` se resuelve con funciones de fecha en SQL
(`func.date`, y `func.strftime`/`func.date_format` según dialecto), no trayendo los `Pago` del
rango y agrupándolos en Python. Es la opción más eficiente, con un riesgo conocido y aceptado: la
misma familia de bugs que `values_callable` (sección 8 del `CONTEXTO-PROYECTO.md`) — algo que
funciona en SQLite (tests) y se comporta distinto en MySQL (producción). La mitigación es
puntual: el código de agrupación por período rama explícitamente por
`db.bind.dialect.name` (`sqlite` vs `mysql`) en vez de asumir una sintaxis portable inexistente, y
la verificación contra Docker/MySQL real (obligatoria para cerrar el módulo, sección 6) prueba
`agrupar_por=dia`, `semana` y `mes` explícitamente antes de dar el endpoint por cerrado.

### 2.5 Permisos — split por tipo de métrica, no una regla única

A diferencia del Módulo 3 (una sola regla) y como el Módulo 4/6 (matriz por recurso):

| Endpoint | Superadmin | Admin | Asistente | Doctor |
|---|---|---|---|---|
| `GET /dashboard/citas/resumen` | Sí, toda la clínica | Sí, toda la clínica | Sí, toda la clínica | Sí, **solo lo suyo** |
| `GET /dashboard/ingresos` | Sí | Sí | No | No |
| `GET /dashboard/facturas-pendientes` | Sí | Sí | No | No |

Justificación: citas es operación diaria (misma regla que Módulo 4: quien ejecuta la operación
puede consultar su propio panorama). Ingresos y facturas pendientes son información financiera de
la clínica completa — territorio gerencial, igual que el resto del Módulo 6 salvo el propio
listado de facturas por doctor.

El filtro del doctor en `/dashboard/citas/resumen` es un `WHERE id_doctor = <el suyo>` inyectado
en el repositorio, **no** un `403` — mismo criterio que `GET /citas` y `GET /facturas` (Módulo 4 y
6): decidido por rol vía `get_doctor_actual`, con la ausencia de perfil cerrando a "no ve nada", no
abriendo a "ve todo".

---

## 3. Endpoints

### 3.1 `GET /dashboard/citas/resumen`

**Query params:** `desde: date | None`, `hasta: date | None` (default: primer/último día del mes
actual), `id_doctor: int | None` (ignorado si el usuario es rol `doctor` — se fuerza al propio).

**Respuesta** (`ResumenCitasResponse`):
```json
{
  "desde": "2026-08-01",
  "hasta": "2026-08-31",
  "total": 87,
  "por_estado": {
    "programada": 12, "confirmada": 30, "completada": 40, "cancelada": 3, "no_asistio": 2
  },
  "por_doctor": [
    {"id_doctor": 3, "nombre": "Dra. Pérez", "total": 45, "por_estado": {"programada": 5, "...": 0}}
  ]
}
```

`por_doctor` es lista vacía cuando el usuario es rol `doctor` (ya filtrado a sí mismo por el
`WHERE`; repetir su propio desglose en una lista de un elemento no aporta).

**Implementación:** `CitaRepository.resumen_por_estado(id_clinica, desde=None, hasta=None,
id_doctor=None) -> dict` reutiliza los mismos filtros de `listar` (`id_clinica`, `fecha_hora`
entre `desde`/`hasta`, `id_doctor`) pero agrupa con `GROUP BY estado` (y `GROUP BY id_doctor,
estado` para el desglose) usando `func.count`, en vez de traer las filas a Python.

### 3.2 `GET /dashboard/ingresos`

**Query params:** `desde: date | None`, `hasta: date | None` (default: mes actual), `agrupar_por:
Literal["dia", "semana", "mes"] = "dia"`.

**Respuesta** (`ResumenIngresosResponse`):
```json
{
  "desde": "2026-08-01", "hasta": "2026-08-31", "agrupar_por": "dia",
  "total": 4250.00,
  "por_metodo_pago": [
    {"id_metodo_pago": 1, "nombre": "Efectivo", "monto": 3000.00},
    {"id_metodo_pago": 2, "nombre": "Tarjeta", "monto": 1250.00}
  ],
  "serie": [
    {"periodo": "2026-08-01", "monto": 120.00},
    {"periodo": "2026-08-02", "monto": 0.00}
  ]
}
```

**Implementación:** `PagoRepository.totales_por_periodo(id_clinica, desde=None, hasta=None,
agrupar_por="dia") -> dict`. `Pago` no tiene `id_clinica` propio — el aislamiento es un `JOIN`
contra `Factura` (mismo criterio que `FacturaDetalleRepository`). Tres queries agregadas: total
(`SUM(monto)`), por método de pago (`GROUP BY id_metodo_pago` + join contra `MetodoPago` para el
nombre), y la serie (`GROUP BY` la fecha truncada según `agrupar_por`, ver 2.4).

### 3.3 `GET /dashboard/facturas-pendientes`

**Query params:** `desde: date | None`, `hasta: date | None` (sin default, filtran
`fecha_emision` solo si se pasan).

**Respuesta** (`FacturasPendientesResponse`):
```json
{
  "resumen": {"cantidad": 5, "monto_pendiente_total": 850.00},
  "facturas": [
    {
      "id_factura": 12, "numero_factura": "F000012", "id_paciente": 3,
      "paciente": "Juan Pérez", "estado": "parcial",
      "monto_total": 200.00, "monto_pagado": 50.00, "saldo_pendiente": 150.00,
      "fecha_emision": "2026-08-05T10:00:00"
    }
  ]
}
```

**Implementación:** `FacturaRepository.listar_pendientes(id_clinica, desde=None, hasta=None) ->
list[dict]`. Filtra `estado IN (PENDIENTE, PARCIAL)`, `LEFT JOIN` contra una subconsulta
`SUM(Pago.monto) GROUP BY id_factura` con `COALESCE(..., 0)` para facturas sin pagos, y calcula
`saldo_pendiente = monto_total - monto_pagado`. También `JOIN` contra `Paciente` para el nombre
mostrado.

---

## 4. Nuevos archivos

- `app/api/routes/dashboards.py` — router nuevo, prefijo `/dashboard`, tres endpoints.
- `app/schemas/dashboard.py` — `ResumenCitasResponse`, `ResumenPorDoctor`, `ResumenIngresosResponse`,
  `TotalPorMetodoPago`, `PuntoSerie`, `FacturasPendientesResponse`, `FacturaPendienteItem`.
- Métodos nuevos (sin archivo nuevo) en `CitaRepository`, `FacturaRepository`, `PagoRepository`.
- `main.py`: registrar `dashboards_router`.

No hay excepciones de dominio nuevas — los tres endpoints no tienen casos de error de negocio más
allá de validación de query params (que Pydantic/FastAPI ya cubre) y los `403` de permisos
(cubiertos por `require_roles`, no por excepciones custom).

---

## 5. Testing

- **Repositorios:** un archivo de test por repositorio afectado, agregando casos a los existentes
  o uno nuevo `test_dashboard_repositorios.py` si se prefiere agrupar — a decidir en el plan.
  Casos clave: agrupación correcta por estado/doctor, filtrado por rango, ingresos con múltiples
  métodos de pago, serie con `agrupar_por` en los tres valores, facturas pendientes con pagos
  parciales y sin pagos.
- **Rutas:** `test_dashboards_routes.py` — permisos por rol (los tres endpoints, incluyendo que
  asistente/doctor reciban `403` en ingresos/facturas-pendientes), el filtro del doctor en
  citas/resumen, defaults de rango de fechas.
- **Aislamiento entre clínicas:** cada endpoint con datos de dos clínicas, verificar que los
  números de una no contaminen los de la otra.
- **Verificación Docker/MySQL real, obligatoria antes de cerrar el módulo** (sección 6 de
  `CONTEXTO-PROYECTO.md`): correr los tres endpoints contra MySQL, con foco explícito en
  `agrupar_por=semana` y `agrupar_por=mes` (sección 2.4) — es la parte del módulo con riesgo real
  de divergencia SQLite/MySQL.

---

## 6. Qué no cambia

No se toca ningún modelo, migración, servicio ni endpoint de los Módulos 1–6. `CitaRepository`,
`FacturaRepository` y `PagoRepository` ganan métodos nuevos, no se modifican los existentes.
