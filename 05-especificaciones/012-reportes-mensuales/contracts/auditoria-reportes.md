# Contrato: auditoría de 012

012 solo escribe `CorteMensual`; audita su creación y regeneración. No audita el contenido de los
Excel ni cada descarga.

## Alta de corte

| Campo | Valor |
|---|---|
| Entidad | `CorteMensual` |
| ID entidad | `corte.id` |
| Campo | `alta` |
| Valor anterior | vacío |
| Valor nuevo | alcance (tenant/global), mes, año, totales |
| Actor | Admin o tenant de la sesión |
| Extra | `version=1` |

## Regeneración

| Campo | Valor |
|---|---|
| Entidad | `CorteMensual` |
| ID entidad | `corte.id` |
| Campo | `regenerado` |
| Valor anterior | totales y versión anteriores |
| Valor nuevo | totales y versión nuevos |
| Actor | Admin o tenant de la sesión |
| Extra | `regenerado_en` |

## Reglas

- La auditoría es síncrona y transaccional: si falla, se revierte la generación/regeneración.
- El actor es el usuario de la sesión; nunca `None`.
- No se auditan los archivos exportados, su contenido ni cada descarga: son vistas de solo lectura.
- No se auditan secretos, binarios ni rutas.
- La auditoría de los datos de origen (stock, series, conciliaciones) pertenece a sus specs; 012 no la
  duplica.

## Consulta

- La auditoría se consulta con las vistas de 001 según el rol.
- La exportación de auditoría es un reporte del mes, no una pantalla de auditoría propia.

## Pruebas de contrato

- Generar produce `CorteMensual/alta` con alcance, mes, año, totales y actor.
- Regenerar produce `CorteMensual/regenerado` con valores anteriores/nuevos y `version`.
- Un fallo de auditoría revierte el corte completo.
- Exportar no crea registros de auditoría de archivo.
- Ningún registro contiene secretos, binarios ni rutas.
