# Diseño: Núcleo Multi-Tenant (Clínica + Usuario + Auth) — Módulo 1

**Fecha:** 2026-07-30
**Estado:** Aprobado para pasar a plan de implementación
**Repo destino:** ClinicaDentalWeb (proyecto nuevo/modernizado)
**Repo legacy de referencia:** ClinicaDental (MVC + PyQt6 + MySQL, sin cambios directos)

## 1. Contexto

El proyecto legacy `ClinicaDental` es un sistema de escritorio (PyQt6 + MySQL) para una única
clínica dental ("Dental Smiling"). Se decidió modernizarlo reescribiéndolo como una plataforma
web multi-clínica (multi-tenant), con backend FastAPI y frontend a definir, manteniendo
`ClinicaDental` intacto como referencia de solo lectura.

### Problemas identificados en el legacy (auditoría as-is)

- Contraseñas en texto plano (`Doctor.Contrasena`, `Asistente.Contrasena`).
- Login usa `Asistente.Nombre` como si fuera username — no existe un campo de username real.
- `ID_Doctor` es `VARCHAR(10)` en la BD pero se castea a `int` en varios puntos del código
  (`Modelos/DoctorModelo.py`, `Modelos/TratamientoModelo.py`).
- `Correo VARCHAR(25)` trunca correos electrónicos normales.
- Contadores de ID manuales en memoria (`Paciente._contador_id`, `Cita._contador_id`) en vez de
  depender de `AUTO_INCREMENT`.
- `validar_telefono` en `PacienteModelo.py` se usa como `@staticmethod` pero no tiene el decorador.
- Bloques completos de datos hardcodeados comentados como "respaldo" (dead code) en
  `DoctorModelo.py`.
- `sys.path.append` repetido en cada archivo en vez de paquetes Python reales.
- `print()` en vez de `logging` en toda la capa de modelo.
- Los "modelos" mezclan datos, validación y acceso a BD (SQL embebido) en la misma clase
  (god classes) — no hay separación Modelo/Repositorio.
- Tablas `Asistente_Paciente`, `Asistente_Cita`, `Asistente_Factura` (M:N) sin que quede claro
  que aportan valor de negocio real sobre una simple auditoría 1:N.

### Diagrama ER as-is

```mermaid
erDiagram
    PACIENTE ||--o{ CITA : tiene
    PACIENTE ||--o{ HISTORIAL_MEDICO : tiene
    PACIENTE ||--o{ FACTURA : recibe
    DOCTOR ||--o{ CITA : atiende
    DOCTOR ||--o{ HORARIO : define
    DOCTOR ||--o{ TRATAMIENTO : realiza
    TRATAMIENTO ||--o{ CITA : "usado en"
    TRATAMIENTO }o--o{ FACTURA : "vía Tratamiento_Factura"
    ASISTENTE }o--o{ PACIENTE : "vía Asistente_Paciente"
    ASISTENTE }o--o{ CITA : "vía Asistente_Cita"
    ASISTENTE }o--o{ FACTURA : "vía Asistente_Factura"

    PACIENTE {
        int ID_Paciente PK
        varchar50 Nombre
        varchar50 Apellido
        date Fecha_Nacimiento
        varchar10 DUI
        char8 Telefono
        varchar25 Correo "trunca correos largos"
    }
    DOCTOR {
        varchar10 ID_Doctor PK "string, se castea a int en código"
        varchar50 Nombre
        varchar50 Apellido
        varchar50 Especialidad
        char8 Telefono
        varchar25 Correo
        varchar255 Contrasena "texto plano"
    }
    HORARIO {
        varchar10 ID_Horario PK
        varchar10 ID_Doctor FK
        time Hora_Inicio
        time Hora_Fin
        bool Disponible
    }
    HISTORIAL_MEDICO {
        int ID_Historial PK
        int ID_Paciente FK
        date Fecha_Creacion
        varchar100 Notas_Generales
        enum Estado
    }
    TRATAMIENTO {
        int ID_Tratamiento PK
        varchar10 ID_Doctor FK
        text Descripcion
        decimal Costo
        datetime Fecha
    }
    CITA {
        int ID_Cita PK
        int ID_Paciente FK
        varchar10 ID_Doctor FK
        int ID_Tratamiento FK
        datetime Fecha
        time Hora_Inicio
        time Hora_Fin
        enum Estado
        decimal Costo
    }
    FACTURA {
        varchar50 ID_Factura PK
        int ID_Paciente FK
        datetime Fecha_Emision
        text Descripcion_Servicio
        decimal Monto_Servicio
        decimal Monto_Total
        varchar20 Estado_Pago
    }
    ASISTENTE {
        int ID_Asistente PK
        varchar50 Nombre "se usa como username en login"
        varchar50 Apellido
        varchar15 Telefono
        varchar100 Correo
        varchar255 Contrasena "texto plano"
    }
```

### Diagrama de clases as-is (capa `Modelos/`)

```mermaid
classDiagram
    class Paciente {
        -_contador_id: int $
        -_pacientes_existentes: list $
        +id_paciente: int
        +nombre: str
        +telefono: int
        +correo: str
        +calcular_edad() int
        +get_balance_total() float
        +validar_telefono(telefono)$ bool
        +insertar_en_bd(paciente)$ bool
        +obtener_todos_los_pacientes()$ list
    }
    note for Paciente "God class: datos + validación + SQL.\nContador de ID en memoria.\nvalidar_telefono sin @staticmethod pero usado como tal."

    class Doctor {
        +num_junta_medica
        +nombre: str
        +citas: list
        +horario: list
        +obtener_doctores_desde_db()$ list
        +insert_doc_db(doctor)$ bool
    }
    note for Doctor "~150 líneas de datos hardcodeados comentados\ncomo 'respaldo' (dead code).\nnum_junta_medica vs id_doctor inconsistente."

    class Cita {
        -_contador_id: int $
        +id_cita: int
        +paciente: Paciente
        +doctor: Doctor
        +estado: str
    }
    note for Cita "Otro contador de ID en memoria, mismo patrón que Paciente."

    class Tratamiento {
        +id_doctor
        +descripcion: str
        +costo: float
    }
    note for Tratamiento "Depende de PyQt6.QtCore.QDate en la capa de 'modelo'."

    class Horario {
        +id_horario: str
        +doctor: Doctor
        +horario_ocupado(otro) bool
    }

    class Factura {
        +id_factura: str
        +paciente: Paciente
    }
    class FacturacionModel {
        +generar_id_factura_automatico()$ str
    }
    note for FacturacionModel "Genera 'F001','F002'... con SELECT + parseo de string\nen vez de PK autoincrement."

    class LoginModelo {
        +validar_usuario(usuario, password) bool
        +obtener_tipo_usuario(usuario) str
    }
    note for LoginModelo "Compara Contrasena en texto plano.\n'usuario' = Asistente.Nombre.\nNo existe clase Asistente propia."

    Cita --> Paciente
    Cita --> Doctor
    Horario --> Doctor
    Factura --> Paciente
    Tratamiento --> Doctor
```

## 2. Roadmap general (decisión de alcance)

El trabajo se organiza en fases; este documento cubre el detalle del primer módulo del bloque
de administración de clínicas.

- **Fase 0 — Diagramas** (este documento: as-is + to-be).
- **Fase 1 — Backend / Núcleo**: seguridad (bcrypt, JWT, `.env`), arquitectura (Repositorio,
  paquetes reales, logging), FastAPI, tests, Docker.
- **Fase 2 — Frontend**: reescritura de vistas.
- **Módulo de administración de clínicas** (priorizado dentro de Fase 1, antes de continuar con
  el resto del backend), dividido en:
  1. **Tenancy + Auth core** — `Clinica`, `Usuario`, aislamiento por `id_clinica` (este doc).
  2. Panel superadministrador (CRUD de clínicas, asignar admin, activar/suspender).
  3. Parámetros por clínica (`ConfiguracionClinica`, `Especialidad`, `Consultorio`).
  4. Operación clínica básica (Pacientes, Odontólogos, Asistentes, Citas, Horarios) con
     aislamiento por clínica.
  5. Expediente clínico avanzado (Diagnósticos, Odontogramas, Planes de tratamiento,
     Presupuestos, Recetas, historial de consultas).
  6. Facturación extendida (Presupuesto → Plan de tratamiento → Factura, impuestos,
     numeración configurable).
  7. Dashboards y métricas (superadmin + por clínica).
  8. Notificaciones y recordatorios.

## 3. Diagrama ER to-be (núcleo multi-tenant)

```mermaid
erDiagram
    CLINICA ||--o{ CLINICA_MODULO : configura
    CLINICA ||--o{ USUARIO : emplea
    CLINICA ||--o{ DOCTOR : tiene
    CLINICA ||--o{ ASISTENTE : tiene
    CLINICA ||--o{ PACIENTE : atiende
    USUARIO ||--o| DOCTOR : "es"
    USUARIO ||--o| ASISTENTE : "es"
    DOCTOR ||--o{ CITA : atiende
    DOCTOR ||--o{ HORARIO : define
    DOCTOR ||--o{ TRATAMIENTO : realiza
    PACIENTE ||--o{ CITA : tiene
    PACIENTE ||--o{ HISTORIAL_MEDICO : tiene
    PACIENTE ||--o{ FACTURA : recibe
    TRATAMIENTO ||--o{ CITA : "usado en"
    TRATAMIENTO }o--o{ FACTURA : "vía Tratamiento_Factura"
    ASISTENTE ||--o{ CITA : "agendó (opcional)"
    ASISTENTE ||--o{ FACTURA : "emitió (opcional)"

    CLINICA {
        int id_clinica PK
        varchar100 nombre
        varchar150 direccion
        varchar8 telefono
        varchar100 correo
        enum estado "activa | suspendida | inactiva, default activa"
        datetime created_at
    }
    CLINICA_MODULO {
        int id_clinica FK
        varchar50 modulo "pacientes | citas | odontogramas | presupuestos | recetas | facturacion | dashboards | notificaciones"
        bool habilitado "default true"
    }
    USUARIO {
        int id_usuario PK
        int id_clinica FK "nullable: NULL = superadmin"
        varchar30 username UK
        varchar255 password_hash "bcrypt"
        enum rol "superadmin | admin | doctor | asistente"
        bool activo
        datetime created_at
    }
    DOCTOR {
        int id_doctor PK
        int id_clinica FK
        int id_usuario FK,UK
        varchar50 nombre
        varchar50 apellido
        varchar50 especialidad
        varchar8 telefono
        varchar100 correo
    }
    ASISTENTE {
        int id_asistente PK
        int id_clinica FK
        int id_usuario FK,UK
        varchar50 nombre
        varchar50 apellido
        varchar15 telefono
        varchar100 correo
    }
    PACIENTE {
        int id_paciente PK
        int id_clinica FK
        varchar50 nombre
        varchar50 apellido
        date fecha_nacimiento
        varchar10 dui
        varchar8 telefono
        varchar100 correo
    }
    HORARIO {
        int id_horario PK
        int id_doctor FK
        time hora_inicio
        time hora_fin
        bool disponible
    }
    HISTORIAL_MEDICO {
        int id_historial PK
        int id_paciente FK
        date fecha_creacion
        varchar100 notas_generales
        enum estado
    }
    TRATAMIENTO {
        int id_tratamiento PK
        int id_doctor FK
        text descripcion
        decimal costo
        datetime fecha
    }
    CITA {
        int id_cita PK
        int id_paciente FK
        int id_doctor FK
        int id_tratamiento FK
        int id_asistente FK "nullable, quién la agendó"
        datetime fecha
        time hora_inicio
        time hora_fin
        enum estado
        decimal costo
    }
    FACTURA {
        int id_factura PK
        int id_paciente FK
        int id_asistente FK "nullable, quién la emitió"
        datetime fecha_emision
        text descripcion_servicio
        decimal monto_servicio
        decimal monto_total
        varchar20 estado_pago
    }
```

### Decisiones de diseño y justificación

| Decisión | Justificación |
|---|---|
| Multi-tenant desde ya (`Clinica` como raíz) | Habilita directamente el módulo de administración de clínicas sin rediseñar el esquema después. |
| `Usuario` unificado (no username/password duplicado en Doctor y Asistente) | Login, JWT y roles en un solo lugar; agregar roles nuevos (superadmin) no implica duplicar lógica de auth. |
| `Usuario.id_clinica` **nullable**, `NULL` = superadmin | Un superadmin no pertenece a una clínica; se evita una tabla de auth paralela. |
| PKs `INT AUTO_INCREMENT` en todo (elimina `"1234"`, `"H001"`, `"F001"`) | Elimina contadores manuales en memoria y parsing de strings tipo `F001`; simplifica tipos consistentes. |
| `Asistente_Paciente`, `Asistente_Cita`, `Asistente_Factura` (3 tablas M:N) → eliminadas | Se confirmó que la relación real es auditoría 1:N ("quién agendó/emitió"), no colaboración M:N. Se reemplaza por `id_asistente` nullable directo en `Cita` y `Factura`; `Asistente_Paciente` se elimina del todo (con auth por rol, cualquier asistente autenticado ve cualquier paciente de su clínica). |
| `Correo VARCHAR(100)` en todas las tablas | `VARCHAR(25)` truncaba correos reales. |
| `ClinicaModulo` (feature flags por módulo) en vez de un campo `plan` simple | El superadmin necesita habilitar/deshabilitar módulos individuales (ej. una clínica sin Recetas) desde el día uno. |
| Entidad `Doctor` se mantiene con ese nombre (no se renombra a `Odontologo`) | Evita romper continuidad con el legacy; "odontólogo" queda como término de UI/negocio. Reversible si el equipo prefiere renombrar. |
| Suspender/desactivar una clínica bloquea login inmediatamente para todos sus usuarios | Es el comportamiento esperado de un `estado != 'activa'`; los datos no se tocan, solo el acceso. |

## 4. Arquitectura de aislamiento multi-tenant (backend)

Requisito explícito del negocio: **la separación de datos se valida obligatoriamente en el
backend usando el `id_clinica` del usuario autenticado — nunca solo con filtros de frontend.**

```mermaid
classDiagram
    class AuthService {
        +login(username, password) TokenResponse
        +hash_password(plain) str
        +verify_password(plain, hash) bool
    }
    class JWTClaims {
        +sub: int  "id_usuario"
        +id_clinica: int|None
        +rol: str
        +exp: datetime
    }
    class TenantContext {
        +get_current_user(token) Usuario
        +require_clinica_activa(usuario) void
        +require_roles(*roles) callable
        +resolve_clinica_id(usuario, header_override) int
    }
    note for TenantContext "resolve_clinica_id():\n- rol normal -> usa id_clinica del JWT, ignora cualquier header\n- rol=superadmin -> puede pasar X-Clinica-Id explícito para inspeccionar una clínica"

    class BaseRepository~T~ {
        <<abstract>>
        +listar(id_clinica: int) list~T~
        +obtener(id_clinica: int, id: int) T
        +crear(id_clinica: int, data) T
        +actualizar(id_clinica: int, id: int, data) T
        +eliminar(id_clinica: int, id: int) bool
    }
    note for BaseRepository "Todo método EXIGE id_clinica como primer parámetro.\nNinguna query a tablas con id_clinica puede ejecutarse sin él."

    AuthService --> JWTClaims : emite
    TenantContext --> JWTClaims : valida
    TenantContext --> BaseRepository : inyecta id_clinica
```

Regla dura de diseño: **ningún repositorio expone un método que no reciba `id_clinica`**. El
aislamiento no depende de que cada desarrollador recuerde agregar `WHERE id_clinica = ...` —
la firma del método lo obliga.

## 5. Endpoints de este módulo

Este módulo cubre solo auth/tenancy. El CRUD completo de clínicas es el Módulo 2 (panel
superadministrador), fuera de alcance aquí.

- `POST /auth/login` — valida `Usuario` + `Clinica.estado == 'activa'` (salvo rol `superadmin`,
  que no tiene clínica asociada) → devuelve JWT con claims `sub`, `id_clinica`, `rol`.
- `GET /auth/me` — devuelve usuario, rol y clínica actual.
- `POST /auth/logout` — invalidación del lado cliente (blacklist de tokens queda fuera de
  alcance de este módulo; se puede agregar después si se requiere revocación inmediata).

## 6. Fuera de alcance de este módulo

- CRUD de clínicas (Módulo 2).
- `ConfiguracionClinica`, `Especialidad`, `Consultorio` (Módulo 3).
- Migración de datos reales del legacy (`ClinicaDental`) hacia el nuevo esquema — se abordará
  como tarea explícita dentro de Fase 1 cuando el esquema esté estable.
- Blacklist/revocación de JWT antes de expiración.
