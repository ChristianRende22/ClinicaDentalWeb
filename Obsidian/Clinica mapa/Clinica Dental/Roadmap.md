#roadmap

# Roadmap

Enlaza a [[ClinicaDentalWeb - Mapa del Proyecto]].

| #   | Módulo                                     | Quién       | Estado      | Depende de                                                                        |
| --- | ------------------------------------------ | ----------- | ----------- | --------------------------------------------------------------------------------- |
| 1   | [[Modulo 1 - Tenancy y Auth]]              | Christian   | ✅           | —                                                                                 |
| 2   | [[Modulo 2 - Panel Superadmin]]            | Christian   | ✅           | [[Modulo 1 - Tenancy y Auth]]                                                     |
| 3   | [[Modulo 3 - Parametros por Clinica]]      | Meli        | ✅           | [[Modulo 1 - Tenancy y Auth]]                                                     |
| 4   | [[Modulo 4 - Operacion Clinica Basica]]    | Meli        | ✅           | [[Modulo 3 - Parametros por Clinica]]                                             |
| 5   | [[Modulo 5 - Expediente Clinico Avanzado]] | Meli        | ✅           | [[Modulo 4 - Operacion Clinica Basica]]                                           |
| 6   | [[Modulo 6 - Facturacion Extendida]]       | Christian   | ✅           | [[Modulo 3 - Parametros por Clinica]], [[Modulo 5 - Expediente Clinico Avanzado]] |
| 7   | [[Modulo 7 - Dashboards]]                  | Christian   | ✅           | [[Modulo 4 - Operacion Clinica Basica]], [[Modulo 6 - Facturacion Extendida]]     |
| 8   | [[Modulo 8 - Notificaciones]]              | Sin asignar | ⬜ siguiente | [[Modulo 3 - Parametros por Clinica]], [[Modulo 4 - Operacion Clinica Basica]]    |

**Meli terminó su bloque (3, 4, 5); Christian cerró el 6 y el 7.** El 8 estaba "sin asignar, el
que termine primero" — queda como el único módulo pendiente, para quien lo tome.

Ver [[Convenciones de Arquitectura]] para lo que hay que respetar en el 7 y el 8.
