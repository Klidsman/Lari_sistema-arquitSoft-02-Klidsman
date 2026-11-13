# Contrato: servicios de reportes

Los servicios viven en `reportes/services.py`; las vistas solo orquestan.

## Tipos

| Tipo | Definición |
|---|---|
| `tenant` | `tenants.Tenant` o `None` para global |
| `mes` / `anio` | Enteros; mes 1–12, año 2000–2100 |
| `actor` | `acceso.Usuario` de la sesión |
| `corte` | `reportes.CorteMensual` |

```python
@dataclass(frozen=True)
class TotalesCorte:
    solicitados: int
    asignados: int
    liquidados_instalados: int
    devueltos: int
    no_justificado: int
    porcentaje_merma: Decimal

@dataclass(frozen=True)
class ArchivoReporte:
    nombre: str
    contenido: bytes
    content_type: str
```

## Excepciones

| Excepción | Mensaje |
|---|---|
| `PermisoDenegado` | “No tienes permiso para generar este corte” / “Solo el administrador puede generar cortes globales” |
| `CorteExistente` | “Ya existe un corte para este mes/año” |
| `CorteNoExiste` | “El corte no existe” |
| `MesInvalido` | “El mes debe estar entre 1 y 12” |
| `AnioInvalido` | “El año no es válido” |

## Alcance

### `validar_cuenta_admin(actor) -> None`

- Exige `ADMIN_PLATAFORMA`; si no, `PermisoDenegado`.

### `validar_cuenta_tenant_o_admin(actor, tenant) -> None`

- Admin: cualquier tenant o global.
- `USUARIO_TENANT`: solo su tenant; global prohibido.

### `resolver_alcance(actor, tenant) -> Literal["TENANT","GLOBAL"]`

- `tenant=None`: exige Admin y devuelve `GLOBAL`.
- `tenant` concreto: exige Admin o cuenta de ese tenant y devuelve `TENANT`.

## Rango del mes

### `rango_mes(mes, anio) -> tuple[datetime, datetime]`

- Valida mes y año; lanza `MesInvalido`/`AnioInvalido`.
- Usa la zona horaria configurada.
- Devuelve `[inicio, fin)`, donde `fin` es el primer instante del mes siguiente.

## Cálculo

### `calcular_totales(tenant, mes, anio) -> TotalesCorte`

- `solicitados`: unidades de `LineaAsignacion` de solicitudes con `fecha` en el mes y estado
  `ENVIADA`, `CONFIRMADA` o `RECHAZADA`; serie = 1, no seriado = `cantidad`.
- `asignados`: unidades de `LineaAsignacion` de solicitudes `CONFIRMADA` con `confirmada_en` en el
  mes.
- `liquidados_instalados`: series distintas con `RegistroCambio` `entidad="Serie"`,
  `campo="estado"`, `valor_nuevo="INSTALADA"` y `fecha` en el mes; filtro por tenant si aplica.
- `devueltos`: filas de `LineaDevolucion` de devoluciones con `fecha` en el mes; filtro por tenant.
- `no_justificado = max(0, asignados - liquidados_instalados - devueltos)`.
- `porcentaje_merma = 0` si `asignados=0`; si no, `round(no_justificado/asignados*100, 2)`.
- No escribe en base ni bloquea.

## Generación y regeneración

### `generar_corte(tenant, mes, anio, actor) -> CorteMensual`

1. `resolver_alcance` y `rango_mes`.
2. Si ya existe el corte, `CorteExistente`.
3. `calcular_totales`.
4. `transaction.atomic`: crear `CorteMensual` (`version=1`, `generado_por=actor`) y auditar
   `CorteMensual/alta`.
5. Devolver el corte.

### `regenerar_corte(corte, actor) -> CorteMensual`

1. `resolver_alcance(actor, corte.tenant)`.
2. `transaction.atomic`: `select_for_update` del corte, recalcular, actualizar campos,
   `version += 1`, `regenerado_en=ahora`, `actualizado_por=actor`; auditar
   `CorteMensual/regenerado` con valores anterior y nuevo.
3. Devolver el corte.

## Exportaciones

### `exportar_auditoria(tenant, mes, anio, actor) -> ArchivoReporte`

- `resolver_alcance` y `rango_mes`.
- Filtrar `RegistroCambio` por `fecha` en `[inicio, fin)` y por `tenant` si no es global.
- Ordenar por `fecha`, `id`.
- Generar un `.xlsx` en memoria con columnas: Fecha, Usuario, Entidad, Acción, Valor anterior,
  Valor nuevo.
- El nombre es `auditoria-<tenant|global>-<anio>-<mes>.xlsx`.
- No persiste archivo ni audita el contenido.

### `exportar_conciliacion(tenant, mes, anio, actor) -> ArchivoReporte`

- `resolver_alcance` y `rango_mes`.
- Filtrar `Conciliacion` por `fecha_carga` en `[inicio, fin)` y por tenant si no es global.
- Columnas: Fecha, Estado, Tenant (solo global), Diferencias series, Diferencias cantidades, Ajustes
  aplicados.
- `diferencias_series`/`diferencias_cantidades` son conteos de las tablas relacionadas.
- `ajustes_aplicados` es el campo de 010; 0 si no está aprobada.
- Nombre `conciliacion-<tenant|global>-<anio>-<mes>.xlsx`.

## Consultas

- `listar_cortes(tenant, anio=None)`: tenant propio o global (admin).
- `obtener_corte(tenant, corte_id)`: filtra por alcance; `CorteNoExiste` si es ajeno.
- `detalle_corte(corte)`.

## Reglas transversales

- 012 no escribe stock, series, asignaciones, traspasos ni conciliaciones; solo `CorteMensual`.
- Nunca se acepta `tenant_id` del cliente para una cuenta de tenant.
- No se usan permisos Django por cadena.
- No se usa Celery ni correo.
- Las exportaciones son de solo lectura y no persisten archivos.

## Pruebas de contrato

- Cada firma, retorno y excepción coincide con este documento.
- Generar dos veces el mismo alcance/mes falla con `CorteExistente`.
- Regenerar incrementa `version` y audita valores anterior/nuevo.
- La exportación de tenant no incluye registros de otro tenant; la global incluye todo.
- Asignados 0 produce merma 0; no justificado negativo se acota a 0.
- Ningún servicio modifica stock, series ni conciliaciones.
