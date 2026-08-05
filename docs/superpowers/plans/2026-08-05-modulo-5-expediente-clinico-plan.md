# Plan TDD — Módulo 5 (BE-05, Expediente clínico avanzado)

Sigue el spec `docs/superpowers/specs/2026-08-05-modulo-5-expediente-clinico-design.md`. Cada task:
test primero (RED, por la razón correcta), después la implementación mínima (GREEN). El orden
respeta las dependencias: no se puede probar `PlanTratamientoService` sin `Tratamiento`, ni la
política de bajas sin `PlanTratamiento`.

## Task 1 — Modelos y migración `0005`

**Archivos:** `app/models/expediente.py`, `app/models/plan_tratamiento.py`,
`app/models/presupuesto.py`, `app/models/receta.py`, `app/models/cita.py` (agrega
`id_tratamiento`), `app/models/__init__.py` (exporta todo lo nuevo),
`alembic/versions/0005_expediente_clinico.py`.

**Tests primero** (`tests/test_expediente_models.py`, `tests/test_plan_tratamiento_models.py`,
`tests/test_presupuesto_models.py`, `tests/test_receta_models.py`):
- Cada modelo tiene sus columnas, sus defaults (`activo=True`, `estado` por defecto de cada enum,
  `cantidad=1`, `orden=0`) y sus `UniqueConstraint`.
- Los cuatro enums nuevos (`EstadoPiezaDental`, `EstadoPlanTratamiento`,
  `EstadoDetallePlanTratamiento`, `EstadoPresupuesto`) usan `.value` en minúscula al guardarse y
  leerse (mismo test que `test_parametros_models.py` le hace a `DiaSemana`) — este es el que solo
  falla contra MySQL si se olvida `values_callable`, así que se prueba aunque SQLite no lo detecte:
  documenta la intención para quien corra la suite contra MySQL en la Task 9.
- `Cita.id_tratamiento` acepta `None` y acepta un id válido.
- **Divergencia modelo/migración** (defecto #1 del Módulo 4): un test que hace
  `Base.metadata.create_all()` en un engine y compara el nombre de cada índice/constraint contra lo
  que declara la migración no es viable en SQLite; en su lugar, la Task 9 (MySQL real) es la que
  cierra este chequeo. Documentarlo en el propio archivo de migración con un comentario, como ya
  hace `0004`.

**Implementación:** copiar la forma de `personas.py`/`cita.py`. Los `ForeignKeyConstraint` de la
migración en el mismo orden que las tablas se crean (una tabla no puede referenciar a otra que
todavía no existe): `tratamiento` → `consulta` → `diagnostico` → `odontograma` → `pieza_dental` →
`plan_tratamiento` → `plan_tratamiento_detalle` → `presupuesto` → `receta` → `receta_detalle`, y al
final el `add_column` de `Cita.id_tratamiento`.

## Task 2 — `TratamientoRepository`

**Archivo:** `app/repositories/tratamiento_repository.py`.

**Tests primero** (`tests/test_tratamiento_repository.py`):
- Smoke de herencia (apunta al modelo correcto), igual que `test_especialidad_repository.py`.
- `eliminar` desactiva un tratamiento sin uso (caso feliz, delega en `CatalogoRepository.eliminar`).
- `eliminar` lanza `ReferenciaEnUsoError` si existe un `PlanTratamientoDetalle` en estado
  `pendiente` o `en_progreso` que lo referencia — **este test se escribe antes de que exista
  `PlanTratamientoRepository`**, así que usa un `INSERT` manual a la tabla `plan_tratamiento_detalle`
  (o una factory mínima local) en vez de pasar por el repositorio del Task 5. Documentar la
  dependencia circular a propósito: `TratamientoRepository` necesita saber de
  `PlanTratamientoDetalleRepository`, pero ese vive en otro archivo que a su vez no depende de
  tratamientos — mismo patrón de import adentro del método que usa `validadores_por_defecto`.
- `eliminar` **no** bloquea si el único detalle que lo usa está `completado` o `cancelado`.
- Aislamiento entre clínicas (un tratamiento de la clínica A no aparece al listar/obtener con
  `id_clinica` de la B).

**Implementación:**
```python
class TratamientoRepository(CatalogoRepository[Tratamiento]):
    model = Tratamiento

    def eliminar(self, id_clinica: int, id_: int) -> bool:
        from app.repositories.plan_tratamiento_repository import (
            PlanTratamientoDetalleRepository,
        )

        if PlanTratamientoDetalleRepository(self.db).existe_activo_con_tratamiento(
            id_clinica, id_
        ):
            raise ReferenciaEnUsoError(
                "No se puede dar de baja: hay un plan de tratamiento activo que lo usa"
            )
        return super().eliminar(id_clinica, id_)
```

## Task 3 — `ConsultaRepository`, `DiagnosticoRepository` y `ConsultaService`

**Archivos:** `app/repositories/consulta_repository.py`, `app/repositories/diagnostico_repository.py`,
`app/services/consulta_service.py`.

**Tests primero:**
- `ConsultaRepository`: CRUD, aislamiento, `listar` filtra por `id_paciente`/`id_doctor`/rango de
  fechas y ordena por `fecha_hora` descendente (lo más reciente primero, es un historial). `eliminar`
  lanza `NotImplementedError` (mismo contrato que `CitaRepository`).
- `DiagnosticoRepository`: CRUD simple, `listar_de_consulta`. Sin test de borrado real, mismo
  criterio.
- `ConsultaService.crear`: lanza `ReferenciaInvalidaError` si el paciente no existe, está inactivo, o
  es de otra clínica; mismo chequeo para el doctor. Camino feliz crea la consulta. Si viene
  `id_cita`, no valida que la cita exista todavía (queda para una iteración futura si se necesita;
  documentarlo como decisión, no como olvido).

**Implementación:** `ConsultaService` es dos `if` con `PacienteRepository`/`DoctorRepository`
inyectados, no un array de validadores — no amerita el patrón del Módulo 4 con solo dos reglas.

## Task 4 — `OdontogramaRepository`

**Archivo:** `app/repositories/odontograma_repository.py`.

**Tests primero** (`tests/test_odontograma_repository.py`):
- `obtener_o_crear` crea el odontograma la primera vez y es idempotente (segunda llamada devuelve
  el mismo `id_odontograma`), mismo test que `test_configuracion_repository.py` le hace a
  `obtener_o_crear`.
- `listar_piezas` sobre un odontograma sin ninguna pieza tocada devuelve las 32, todas `sano`.
- `actualizar_pieza` crea la fila si no existe (upsert) y la actualiza si ya existe, sin duplicar
  (respeta el `UniqueConstraint`).
- `numero_pieza` fuera de 1–32 lanza `ValueError` (validación de rango, no de FK — se prueba en el
  repositorio porque no depende de la base).
- Aislamiento: el odontograma de un paciente de la clínica A no se puede tocar con `id_clinica` de
  la B, aunque se adivine el `id_paciente`.

## Task 5 — `PlanTratamientoRepository`, `PlanTratamientoDetalleRepository` y
`PlanTratamientoService`

**Archivos:** `app/repositories/plan_tratamiento_repository.py`,
`app/services/plan_tratamiento_service.py`, `app/models/plan_tratamiento.py`
(`TRANSICIONES_PLAN_PERMITIDAS`).

**Tests primero:**
- Repositorio: CRUD de `PlanTratamiento`, aislamiento. `existe_plan_activo_de_paciente` y
  `existe_plan_activo_de_doctor` — verdadero solo con `borrador`/`aprobado`/`en_progreso`, falso con
  `completado`/`cancelado` y falso si no hay ningún plan.
- `PlanTratamientoDetalleRepository.existe_activo_con_tratamiento` — verdadero solo con
  `pendiente`/`en_progreso`.
- `PlanTratamientoService.agregar_detalle`: copia `Tratamiento.precio` a `precio_unitario` en el
  momento de agregar; si después cambia el precio del catálogo, el detalle ya creado no se mueve
  (test que cambia el precio del tratamiento después de agregar el detalle y verifica que el
  detalle conserva el precio viejo). Lanza `ReferenciaInvalidaError` si el tratamiento no existe,
  está inactivo, o es de otra clínica.
- `PlanTratamientoService.cambiar_estado_detalle` respeta una tabla de transiciones propia del
  detalle (`pendiente → en_progreso → completado`, y `cancelada` alcanzable desde `pendiente` o
  `en_progreso`, terminal desde ahí). Transición inválida lanza `TransicionInvalidaError`.
- `PlanTratamientoService.cambiar_estado` (del plan): `borrador → aprobado → en_progreso →
  completado`, y `cancelado` alcanzable desde `borrador` o `aprobado` (no desde `en_progreso`: un
  plan que ya empezó a ejecutarse no se cancela entero, se cancelan los detalles que falten uno por
  uno — decisión de diseño a documentar en el spec si no quedó ya, y en el docstring del código).
- `existe_plan_activo_de_paciente`/`_de_doctor` se prueban también **desde el lado de quien las
  consume**: un test de integración en la Task 7 (repositorios de `Paciente`/`PersonalService`) que
  verifica que la baja se bloquea de punta a punta.

**Implementación:** `TRANSICIONES_PLAN_PERMITIDAS` como diccionario, mismo formato que
`TRANSICIONES_PERMITIDAS` de `Cita` (conjunto vacío = terminal). `PlanTratamientoDetalle` tiene la
suya propia, separada, porque son dos máquinas de estado distintas sobre dos entidades distintas.

## Task 6 — `PresupuestoRepository` y `PresupuestoService`

**Archivos:** `app/repositories/presupuesto_repository.py`, `app/services/presupuesto_service.py`.

**Tests primero:**
- `generar_o_regenerar` suma `precio_unitario * cantidad` de los detalles **no cancelados** del
  plan y crea el `Presupuesto` si no existía.
- Llamado una segunda vez sobre el mismo plan **actualiza** el existente (mismo `id_presupuesto`),
  no crea uno nuevo — prueba directa de la decisión 2 del spec (regenerar, no versionar).
- Si se cancela un detalle entre la primera y la segunda generación, el total baja.
- `cambiar_estado`: `vigente → aceptado | rechazado`, terminales los dos. Transición inválida
  (`aceptado → rechazado`) lanza `TransicionInvalidaError`.
- Generar el presupuesto de un plan sin ningún detalle da `monto_total = 0`, no un error — un plan
  recién creado es un caso válido, no uno excepcional.

## Task 7 — Extender la política de bajas a `Paciente` y `Doctor`

**Archivos editados:** `app/repositories/paciente_repository.py` (`eliminar`),
`app/services/personal_service.py` (`dar_de_baja_doctor`).

**Tests primero** (agregados a `tests/test_paciente_repository.py` y
`tests/test_personal_service.py`, no archivos nuevos — son casos nuevos de comportamiento existente):
- `PacienteRepository.eliminar` da de baja normalmente a un paciente sin planes (no rompe nada de
  lo que ya pasaba).
- `PacienteRepository.eliminar` lanza `ReferenciaEnUsoError` si el paciente tiene un
  `PlanTratamiento` en `borrador`/`aprobado`/`en_progreso`.
- `PacienteRepository.eliminar` **no** bloquea si todos los planes del paciente están
  `completado`/`cancelado`.
- Mismos tres casos para `PersonalService.dar_de_baja_doctor`, con el doctor como responsable del
  plan.
- El endpoint (`DELETE /pacientes/{id}`, `DELETE /doctores/{id}`) traduce `ReferenciaEnUsoError` a
  `409`, no a `422` — es un conflicto con el estado del sistema, no una regla sobre datos enviados,
  mismo criterio que `ChoqueDeCitaError` en el Módulo 4.

**Implementación:** ver el bloque de código en la sección 4 del spec.

## Task 8 — `RecetaRepository`, `RecetaDetalleRepository` y `RecetaService`

**Archivos:** `app/repositories/receta_repository.py`, `app/services/receta_service.py`.

**Tests primero:**
- `RecetaService.crear` con al menos un medicamento: crea `Receta` + sus `RecetaDetalle` en una sola
  transacción.
- `RecetaService.crear` con una lista de medicamentos vacía lanza `ValueError` (o una excepción de
  dominio nueva si se prefiere consistencia — decidir en la implementación y documentarlo) **antes**
  de tocar la base: una receta sin medicamentos no es un estado intermedio válido.
- Si falla la creación de un `RecetaDetalle` (por ejemplo, una violación de constraint fabricada en
  el test), no queda una `Receta` huérfana sin detalles — mismo test que el Módulo 4 le hizo a
  `PersonalService` con el usuario huérfano.
- Valida paciente y doctor igual que `ConsultaService` (reutilizar, no copiar, si el chequeo es
  idéntico — evaluar extraer un helper compartido en la implementación).

## Task 9 — Schemas

**Archivos:** `app/schemas/tratamiento.py`, `app/schemas/consulta.py` (+ diagnóstico),
`app/schemas/odontograma.py`, `app/schemas/plan_tratamiento.py`, `app/schemas/presupuesto.py`,
`app/schemas/receta.py`.

**Tests primero** (`tests/test_schemas_modulo5.py`, mismo criterio que
`tests/test_schemas_modulo4.py`):
- `TratamientoCreate` rechaza `precio <= 0` y `nombre` vacío.
- Los `Update` de cada entidad no admiten `null` explícito en un campo no nullable de la columna
  (mismo patrón `_no_nulo` que `PacienteUpdate` — reusar la función existente de
  `app/schemas/personas.py` en vez de copiarla, moviéndola a un módulo compartido si hace falta).
- `PlanTratamientoDetalleCreate` exige `cantidad >= 1`.
- `RecetaCreate.medicamentos` exige al menos un elemento (`min_length=1`), espejo del chequeo del
  servicio (dos capas, cinturón y tirantes: rechazar en el borde donde el error se puede reportar
  bien, mismo criterio que `_sin_zona_horaria` del Módulo 4).
- `PiezaDentalUpdate.numero_pieza` acotado 1–32 con `Field(ge=1, le=32)`.

## Task 10 — Routers

**Archivos:** `app/api/routes/tratamientos.py`, `consultas.py`, `odontogramas.py`,
`planes_tratamiento.py`, `presupuestos.py`, `recetas.py`, y `app/main.py` (registra los seis).

**Tests primero** (un archivo de test por router, mismo patrón que
`tests/test_citas_routes.py`):
- Matriz de permisos de la tabla de la sección 5 del spec, entidad por entidad: cada rol contra
  cada endpoint de lectura/escritura.
- Aislamiento entre clínicas en cada `GET .../{id}` y en el `X-Clinica-Id` de un superadmin.
- Traducción de excepciones: `ReferenciaInvalidaError` → `422`, `ReferenciaEnUsoError` y
  `TransicionInvalidaError` → `409` — mismo criterio de traducción que `citas.py`, reutilizar la
  idea de `_A_409`/`_A_422` en cada router nuevo que la necesite.
- `DELETE /tratamientos/{id}` en uso → `409` con el mensaje de `ReferenciaEnUsoError`.
- `PUT /pacientes/{id}/odontograma` con una sola pieza en el body no toca las demás (prueba directa
  de la decisión 4 del spec: el upsert es parcial).
- `POST /planes-tratamiento/{id}/presupuesto` llamado dos veces devuelve el mismo `id_presupuesto`
  con el total actualizado.

**Implementación:** copiar el esqueleto de `citas.py` (constantes `LECTURA`/`ESCRITURA` por
router, diccionario de traducción de excepciones, `try/except` en la ruta, servicio hace el
`flush`, la ruta hace el `commit`).

## Task 11 — Colección de Postman y verificación contra MySQL real

- `docs/postman/ClinicaDentalWeb-Modulo5.postman_collection.json`, mismo formato que la del Módulo
  4 (carpeta `0. Setup` que encadena token e `id_clinica`, ejecutable de punta a punta con Run
  Collection). Cubrir: alta de tratamiento, consulta con diagnóstico, odontograma con upsert
  parcial, plan con detalle y presupuesto regenerado, receta con dos medicamentos, y los tres casos
  de `409` de la política de bajas (paciente, doctor, tratamiento en uso).
- `alembic upgrade head` en Docker contra MySQL real, y confirmar en minúscula los cuatro enums
  nuevos (`SHOW COLUMNS`), igual que se hizo en los Módulos 3 y 4 — es el único chequeo que puede
  detectar si algún `values_callable` se olvidó.
- Actualizar `docs/CONTEXTO-PROYECTO.md`: nueva sección "6quater — Qué existe ya (Módulo 5)", el
  roadmap de la sección 2, y la fila del Módulo 6 en "lo que este módulo habilita".

## Nota sobre alcance de tests

Este plan no fija un número de tests como objetivo (el Módulo 4 llegó a 376 por acumulación, no
porque alguien lo pidiera). El criterio es cobertura por comportamiento documentado en el spec: cada
decisión de la sección 2, cada regla de la sección 1 (política de bajas) y cada fila de la tabla de
permisos de la sección 5 tiene que tener al menos un test que falle si se rompe. Task 12, al cierre,
es correr la suite completa y confirmar que no quedó ninguna fila de esas tablas sin un test propio.

## Task 12 — Cierre

- Suite completa en verde contra SQLite.
- Revisión de código propia antes de dar el módulo por terminado, buscando específicamente el
  patrón que el apéndice del plan del Módulo 4 documentó: "un campo o una regla que viaja por un
  camino distinto al que el diseño previó". Puntos concretos a revisar con ese lente:
  - ¿Algún `Update` schema deja pasar un campo con regla propia (como `activo` en `Paciente`) sin
    que la ruta lo intercepte?
  - ¿`cambiar_estado` de `PlanTratamiento` puede llegar a `cancelado` por un camino que no pase por
    la validación de que el plan no esté `en_progreso`?
  - ¿Alguna dependencia de FastAPI nueva devuelve `None` por dos motivos distintos y decide por
    `is not None` en vez de por rol?
- `docs/CONTEXTO-PROYECTO.md` actualizado (ver Task 11).
