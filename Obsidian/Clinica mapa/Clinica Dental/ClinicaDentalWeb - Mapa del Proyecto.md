#proyecto #clinicadentalweb #mapa

# ClinicaDentalWeb — Mapa del Proyecto

Nodo central. Desde acá se llega a todo. La fuente de verdad técnica detallada sigue siendo
`docs/CONTEXTO-PROYECTO.md` en el repo — este vault es el mapa rápido y conectado, no un
duplicado.

## Qué es

Reescritura completa del sistema legacy de escritorio `ClinicaDental` (PyQt6 + MySQL, una sola
clínica — queda intacto como referencia, nunca se toca) hacia una plataforma web
**multi-clínica**: varias clínicas dentales se registran y operan independientes bajo un
superadministrador.

- Repo: `C:\Christian\Personal\ClinicaDentalWeb`
- GitHub: https://github.com/ChristianRende22/ClinicaDentalWeb (rama `main`, push directo)

Ver [[Equipo]] y [[Referencias Externas]].

## Roadmap

Ver [[Roadmap]] para la tabla completa con estado y dependencias entre módulos.

## Módulos (Backend)

- [[Modulo 1 - Tenancy y Auth]] ✅
- [[Modulo 2 - Panel Superadmin]] ✅
- [[Modulo 3 - Parametros por Clinica]] ✅
- [[Modulo 4 - Operacion Clinica Basica]] ✅
- [[Modulo 5 - Expediente Clinico Avanzado]] ✅
- [[Modulo 6 - Facturacion Extendida]] ✅
- [[Modulo 7 - Dashboards]] ⬜ siguiente
- [[Modulo 8 - Notificaciones]] ⬜

## Conceptos transversales

- [[Convenciones de Arquitectura]] — patrones que TODO módulo nuevo debe seguir
- [[Bugs Conocidos]] — errores reales ya encontrados, para no repetirlos
- [[Flujo de Trabajo con Claude]] — cómo se construye cada módulo, reglas de commit

## Cómo arrancar la próxima sesión de Claude Code

Abrí Claude Code en `C:\Christian\Personal\ClinicaDentalWeb` y decile:

> "Leé el vault de Obsidian en `Obsidian/Clinica mapa/Clinica Dental`, empezando por
> `ClinicaDentalWeb - Mapa del Proyecto.md`, y `docs/CONTEXTO-PROYECTO.md`. Vamos a seguir con el
> Módulo 7 (Dashboards)."

**Regla permanente: cada vez que se termina un módulo nuevo, se crea/actualiza su nota acá
mismo, enlazada a este mapa y a los módulos de los que depende — no queda como nota suelta.**
