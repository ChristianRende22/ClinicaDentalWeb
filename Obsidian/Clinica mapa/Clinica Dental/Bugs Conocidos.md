#bugs #convenciones

# Bugs Conocidos

Errores reales ya encontrados y corregidos. Revisar esto antes de escribir código nuevo para no
repetirlos. Ver [[Convenciones de Arquitectura]] para las reglas que nacieron de estos bugs.

## 1. SQLite + `TestClient` en hilos distintos
`TestClient` corre el endpoint en un hilo de threadpool distinto al del test. Sin
`poolclass=StaticPool` en el engine de SQLite en memoria, cada conexión nueva ve una base de
datos vacía y distinta — las tablas "desaparecen". Fix en `tests/conftest.py`, fixture
`db_session`. Encontrado en [[Modulo 1 - Tenancy y Auth]].

## 2. SQLAlchemy `Enum` usa `.name`, no `.value`, por defecto
Un enum de Python declarado como columna `Enum` se serializa por `.name` (`ACTIVA`) salvo que
se pase `values_callable=lambda enum_cls: [e.value for e in enum_cls]`. **Solo revienta contra
MySQL real** — SQLite no tiene ENUM nativo, así que los tests pasan igual con el bug presente.
Encontrado en [[Modulo 1 - Tenancy y Auth]] al verificar contra Docker, repetido con cuidado en
todos los módulos siguientes.

## 3. Un índice en la migración que no está en el modelo
Los tests corren sobre `Base.metadata.create_all()` (el esquema del **modelo**); producción
corre la migración de Alembic. Si un índice o el nombre de un constraint solo está en uno de los
dos, los tests pasan sobre un esquema que no existe en producción. Apareció con
`ix_cita_doctor_fecha` en [[Modulo 4 - Operacion Clinica Basica]].

## 4. Un campo del body de un `PUT` esquiva la matriz de permisos
Los repositorios aplican `data` con `setattr` genérico, así que cualquier campo del schema
`Update` es escribible por quien tenga permiso de editar — aunque ese campo represente una
acción con su propio permiso. Pasó dos veces en [[Modulo 4 - Operacion Clinica Basica]]:
`{"activo": false}` en `PUT /pacientes` era una puerta trasera al `DELETE`, y
`{"id_especialidad": <de otra clinica>}` en `PUT /doctores` esquivaba la validación del `POST`.
**Regla:** si un campo de un Update tiene una regla de negocio o un permiso propio, chequealo en
la ruta o delegalo a un servicio — no alcanza con que el schema lo acepte.

## 5. Una dependencia que devuelve `None` por dos motivos abre en vez de cerrar
`get_doctor_actual` devuelve `None` tanto para "no es doctor" como para "es doctor sin fila
`Doctor`". El filtro de citas decidía con `is not None`, así que un doctor sin perfil pasaba a
ver **todas** las citas de la clínica. Encontrado en [[Modulo 4 - Operacion Clinica Basica]].
**Regla:** cuando un chequeo de permisos depende de que algo exista, decidí por el rol y hacé
que la ausencia cierre, nunca que abra.

## 6. `ReferenciaEnUsoError` no capturada en las rutas de baja
Ni `DELETE /pacientes/{id}` ni `DELETE`/`PUT /doctores/{id}` capturaban la excepción — devolvía
`500` en vez de `409`. Peor: `PUT /pacientes/{id}` con `{"activo": false}` pasaba por
`actualizar()` (setattr genérico) en vez de por `eliminar()`, así que la baja se aplicaba sin
chequear nada (mismo patrón que el bug #4). Corregido en
[[Modulo 5 - Expediente Clinico Avanzado]]. Los tests de repositorio/servicio no lo detectaron
porque no pasan por las rutas reales — la regresión solo se ve con un test de ruta dedicado.
