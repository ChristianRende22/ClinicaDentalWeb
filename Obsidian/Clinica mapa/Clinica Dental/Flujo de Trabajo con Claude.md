#flujo-de-trabajo

# Flujo de Trabajo con Claude

Cómo se construye cada módulo. Ver [[Equipo]] — ambos (Christian y Meli) siguen esto.

## Proceso por módulo

1. **Brainstorming** — una pregunta a la vez, propone 2-3 opciones, presenta el diseño en
   secciones.
2. **Spec** — se escribe a `docs/superpowers/specs/YYYY-MM-DD-modulo-N-<nombre>-design.md` y se
   commitea.
3. **Plan TDD** — a `docs/superpowers/plans/YYYY-MM-DD-modulo-N-<nombre>-plan.md`, bite-sized,
   cada paso con código real, y se commitea.
4. **Ejecución** — desde el Módulo 7 en adelante, **subagent-driven** (subagente implementador +
   revisor por tarea, revisión final de branch): cambio explícito confirmado al arrancar el
   Módulo 7 (2026-08-08), reemplaza la ejecución inline que se usó en los Módulos 1-6.
5. **Verificación contra Docker/MySQL real** — obligatoria antes de dar el módulo por cerrado
   (ver [[Bugs Conocidos]]).
6. **Actualizar `docs/CONTEXTO-PROYECTO.md`** con una sección nueva del módulo.
7. **Actualizar este vault de Obsidian** — nota nueva del módulo, enlazada acá y a los módulos
   de los que depende. Este paso es tan obligatorio como el resto, no opcional.

## Reglas de commit (corregidas varias veces, no improvisar)

- **Bajo ejecución inline (Módulos 1-6):** no se commitea nada durante la ejecución. Se escribe y
  testea todo, pero queda sin commitear. Solo se commitea (y recién ahí se pushea) cuando
  Christian lo dice explícitamente ("commiteá y pusheá el módulo N").
- **Bajo subagent-driven (Módulo 7 en adelante):** cada subagente de tarea commitea su propia
  tarea como parte del flujo normal del skill — no se espera un ok aparte para esos commits.
  El `git push` sigue necesitando el ok explícito de Christian en cualquier modo.
- Cuando se commitea: **un commit por tarea del plan**, no uno gigante.
- **Nunca poner `Co-Authored-By: Claude` ni ninguna atribución de Claude/Anthropic** en los
  mensajes de commit. Regla permanente, no solo para el commit del momento.
- Antes de responder si algo está commiteado, **verificar con `git status`/`git log`**, no
  asumir de memoria.

## Antes de escribir un plan nuevo

Leer el código real del módulo más reciente (modelos, repositorios, servicios, rutas) en vez de
inventar el patrón — ver [[Convenciones de Arquitectura]] para lo que ya está establecido y hay
que igualar, no aproximar.
