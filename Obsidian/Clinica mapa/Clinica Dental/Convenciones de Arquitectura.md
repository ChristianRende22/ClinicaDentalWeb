#convenciones #arquitectura

# Convenciones de Arquitectura

Todo módulo nuevo ([[Modulo 7 - Dashboards]], [[Modulo 8 - Notificaciones]], y lo que venga
después) tiene que respetar esto. El detalle completo con ejemplos de código está en
`docs/CONTEXTO-PROYECTO.md` sección 7 del repo — acá el resumen conectado.

## TDD siempre
Test falla por la razón correcta (RED) → implementación mínima (GREEN) → commit. Nunca
implementación antes que el test.

## `BaseRepository` — la regla dura
Todo repositorio de un recurso que vive **dentro** de una clínica (`Paciente`, `Doctor`, `Cita`,
`Factura`...) hereda de `BaseRepository`. Sus métodos exigen `id_clinica` como primer parámetro
**obligatorio, sin default**. El aislamiento entre clínicas se fuerza por la firma del método,
no por disciplina del programador.

Se introdujo en [[Modulo 1 - Tenancy y Auth]]. Excepciones documentadas: `UsuarioRepository`,
`ClinicaRepository`, `ClinicaModuloRepository` (de [[Modulo 1 - Tenancy y Auth]] /
[[Modulo 2 - Panel Superadmin]]) — son repositorios de plataforma, no de un recurso
tenant-scoped.

## Repositorios de entidades hijas — NO heredan `BaseRepository`
`FacturaDetalle`, `Pago` ([[Modulo 6 - Facturacion Extendida]]), `PlanTratamientoDetalle`
([[Modulo 5 - Expediente Clinico Avanzado]]), `HorarioDoctor`
([[Modulo 4 - Operacion Clinica Basica]]) — todos se aíslan con un `JOIN` contra su entidad
padre en vez de llevar `id_clinica` propio. Mismo criterio en los cuatro casos.

## `CatalogoRepository[T]`
Introducido en [[Modulo 3 - Parametros por Clinica]]: CRUD compartido para catálogos por
clínica (nombre único, borrado lógico). `Especialidad`, `Consultorio`, `MetodoPago`, y
`Tratamiento` ([[Modulo 5 - Expediente Clinico Avanzado]]) heredan de acá en vez de repetir el
CRUD.

## Servicios con transacción explícita
Cuando una operación toca varias tablas relacionadas, el servicio hace
`try` / `except` + `db.rollback()` explícito y **commitea él mismo** (no la ruta). Ejemplos:
`ClinicaService.crear_clinica_con_admin` ([[Modulo 2 - Panel Superadmin]]),
`PersonalService` ([[Modulo 4 - Operacion Clinica Basica]]),
`FacturaService._emitir` ([[Modulo 6 - Facturacion Extendida]]).

## Enums — `values_callable` siempre
Todo enum nuevo lleva `values_callable=lambda enum_cls: [e.value for e in enum_cls]`. Ver
[[Bugs Conocidos]] — sin esto, el bug solo aparece contra MySQL real, nunca en los tests.

## Reglas de negocio como objetos independientes
Patrón de `validadores_cita.py` ([[Modulo 4 - Operacion Clinica Basica]]): cada regla es una
clase con `validar(ctx) -> None` en vez de un bloque de `if` gigante en el servicio. Agregar una
regla es un archivo nuevo, no editar el servicio.

## Verificación contra Docker/MySQL real
Obligatoria para cerrar cualquier módulo, no opcional. Ver [[Bugs Conocidos]] — varios bugs
reales solo se manifestaron ahí.

## Excepciones de dominio → HTTP
Todas viven en `app/exceptions.py`. Repositorios y servicios lanzan la excepción; la ruta la
atrapa y la traduce a `HTTPException` con el status code correcto. Nunca `HTTPException` dentro
de un repositorio o servicio.

## Filtro por rol es un `WHERE`, no un `403`
Cuando un doctor solo puede ver sus propios recursos (citas, facturas), el filtro se aplica en
la query (`WHERE id_doctor = <el suyo>`), y un recurso ajeno por id devuelve **404**, no 403 —
un 403 confirmaría que el recurso existe. Ver [[Bugs Conocidos]] para el error de implementarlo
al revés.
