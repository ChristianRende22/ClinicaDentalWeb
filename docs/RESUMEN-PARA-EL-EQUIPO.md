# Resumen del proyecto — Modernización Clínica Dental

**Fecha de esta sesión:** 2026-07-30
**Para:** el equipo / partner del proyecto

Este documento resume, en lenguaje simple, qué se decidió y por qué, para que cualquiera del
equipo pueda ponerse al día sin leer todo el detalle técnico.

## ¿De dónde partimos?

El sistema actual (`ClinicaDental`) es una app de escritorio en Python + PyQt6 + MySQL para
**una sola clínica** ("Dental Smiling"). Funciona, pero tiene varios problemas de fondo:

- Las contraseñas se guardan **en texto plano** (sin encriptar).
- El "usuario" de login es en realidad el nombre de pila del asistente — no hay un username real.
- Los IDs de doctor a veces son texto (`"1234"`) y a veces se tratan como número en el código,
  lo cual genera bugs.
- Los correos electrónicos se cortan si son muy largos (el campo es demasiado pequeño).
- Hay pedazos grandes de código muerto (datos de ejemplo comentados) y `print()` en vez de logs
  reales.
- El código mezcla "datos" con "acceso a la base de datos" en las mismas clases, lo cual hace
  difícil testear o cambiar cosas sin romper otras.

Estos puntos ya estaban en la lista original de mejoras y quedaron documentados formalmente en
el spec técnico (ver abajo).

## ¿Qué se decidió hacer?

Se decidió **reescribir el sistema** en un proyecto nuevo (`ClinicaDentalWeb`), en vez de
parchar el legacy. El legacy se queda como está, de solo lectura, como referencia.

El plan general tiene 3 grandes bloques:

1. **Diagramas** (lo que hicimos hoy) — mapear cómo está la base de datos y el código hoy,
   y diseñar cómo debería quedar.
2. **Backend** — la parte de servidor: seguridad, base de datos nueva, API (FastAPI), tests,
   Docker.
3. **Frontend** — la parte visual, al final, una vez el backend esté sólido.

## Cambio de rumbo grande: el sistema ahora es multi-clínica

A mitad de sesión se agregó un requerimiento importante: el sistema **ya no es para una sola
clínica**, sino que va a ser una plataforma donde **varias clínicas dentales** se registran y
operan de forma independiente, con:

- Un **panel de superadministrador** que ve y controla todas las clínicas (crearlas, activarlas,
  suspenderlas, asignarles un administrador).
- Un **panel propio por cada clínica**, donde solo ven y manejan su propia información
  (pacientes, odontólogos, citas, tratamientos, facturas, etc.) — **una clínica nunca puede ver
  los datos de otra**.
- Dos dashboards distintos: uno global (para el superadmin) y uno por clínica.
- Configuración por clínica (horarios, especialidades, precios, métodos de pago, etc.).
- Módulos clínicos nuevos que el sistema viejo no tenía: expedientes, diagnósticos,
  odontogramas, presupuestos, planes de tratamiento y recetas.

Esto es mucho trabajo, así que se dividió en **8 módulos** que se van a construir uno por uno
(no todo junto):

1. **Base de autenticación y aislamiento por clínica** ← *estamos acá ahora*
2. Panel de superadministrador (crear/administrar clínicas)
3. Configuración por clínica (horarios, especialidades, consultorios, precios)
4. Operación básica (pacientes, odontólogos, asistentes, citas) ya aislada por clínica
5. Expediente clínico avanzado (diagnósticos, odontogramas, planes de tratamiento, recetas)
6. Facturación extendida (presupuestos, impuestos, numeración de facturas)
7. Dashboards y métricas (global y por clínica)
8. Notificaciones y recordatorios

## Dónde estamos hoy

Terminamos de diseñar el **Módulo 1**: la base de todo el sistema multi-clínica. En corto:

- Cada clínica es una fila en una tabla `Clinica`, con un estado (activa / suspendida /
  inactiva). Si el superadmin la suspende, nadie de esa clínica puede volver a entrar hasta que
  se reactive.
- Los usuarios (doctores, asistentes, administradores, superadmin) se manejan todos desde una
  sola tabla `Usuario`, con su rol y su contraseña **encriptada** (no más texto plano).
- El superadmin es el único tipo de usuario que no pertenece a ninguna clínica en particular —
  puede ver todas.
- **Regla de seguridad clave:** el sistema nunca confía en el frontend para separar los datos
  de cada clínica. Cada consulta a la base de datos, desde el backend, está obligada a filtrar
  por la clínica del usuario que hizo login. No es opcional ni depende de que alguien se
  acuerde de ponerlo — está forzado por diseño.

El detalle técnico completo (diagramas de base de datos, diagramas de clases, decisiones
punto por punto) está en:
`docs/superpowers/specs/2026-07-30-modulo-tenancy-auth-clinicas-design.md`

## Qué sigue

Ahora se va a desglosar el Módulo 1 en tareas chicas y concretas (plan de implementación),
para empezar a programarlo. Los módulos 2 al 8 se van a diseñar y planear de la misma forma,
uno a la vez, según ese orden.
