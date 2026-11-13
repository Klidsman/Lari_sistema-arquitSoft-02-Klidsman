# Plan técnico: 013 Registro de Materiales

**Branch**: `013-registro-materiales` | **Date**: 2026-11-12 | **Spec**:
`05-especificaciones/013-registro-materiales/spec.md`

**Input**: Spec en `05-especificaciones/013-registro-materiales/spec.md`

## Summary

Implementar el registro de materiales usados por los técnicos y el saldo mensual del tenant. El
tenant habilita un catálogo de materiales, carga saldos iniciales, registra despachos del almacén
vinculados a un recojo y captura el uso por orden de liquidación y técnico. El reporte mensual calcula
`saldo final = saldo inicial + despachos - uso`, con herencia del saldo final del mes anterior y
alerta cuando el resultado es negativo. Todo cambio de orden, saldo o despacho queda auditado; no se
borra nada; el módulo no modifica stock, conciliaciones ni recojos.

La spec y el plan anterior tienen tres puntos que este plan corrige:
1. El catálogo es `materiales.Material`, no `catalogo.Material`; las líneas de recojo son
   `recojos.LineaRecojo`, no `RecojoLinea`.
2. La unicidad de la orden es `(tenant, técnico, periodo, número de orden)`: el mismo técnico puede
   tener varias órdenes en el mes con números distintos, como exige el flujo de registro.
3. Se reutiliza `auditoria.RegistroCambio` y los roles del dominio; no se crean permisos Django ni una
   tabla de auditoría paralela.

## Technical Context

| Aspecto | Decisión |
|---|---|
| Lenguaje | Python 3.12+ |
| Framework | Django LTS 5.x |
| Base de datos | PostgreSQL 16+; sin SQLite, tampoco en pruebas |
| Interfaz | Django + HTMX; registro por orden, entradas, catálogo y reporte |
| App nueva | `registro_materiales` |
| Catálogo | `materiales.Material` compartido; habilitación por tenant |
| Recojos | `recojos.Recojo` y `recojos.LineaRecojo` de 004, solo lectura |
| Stock | **No se lee ni se modifica** |
| Conciliación | **No se lee, genera ni modifica** |
| Periodo | `YYYY-MM`, derivado solo de la fecha de la orden |
| Saldo | Inicial manual o heredado del final anterior; final puede ser negativo con alerta |
| Auditoría | `auditoria.RegistroCambio` con `tenant` |
| Transacciones | Orden, saldo y despacho atómicos |
| Bloqueos | `select_for_update` para despachos y ediciones |
| Exportación | No hay Excel/PDF en 013 |
| Dependencias nuevas | Ninguna |
| Pruebas | `pytest` + `pytest-django` sobre PostgreSQL |

### Prerrequisitos bloqueantes

- **001**: `AUTH_USER_MODEL`, `ContextoUsuarioMiddleware`, `Tenant`, `Region`, roles y
  `auditoria.RegistroCambio` con `tenant`.
- **002**: `materiales.Material` con `codigo`, `descripcion`, `lote` y `es_seriado`.
- **003**: `tecnicos.Tecnico` con `tenant`, `nif` y `activo`.
- **004**: `recojos.Recojo` y `recojos.LineaRecojo` con `tenant`, `material`, `cantidad`,
  `recojo` y `serie`.
- **Infraestructura**: PostgreSQL con rol sin `SUPERUSER` ni `BYPASSRLS`.

Si falta cualquiera, la implementación se detiene y se reporta.

### Orden de implementación

1. Correcciones documentales de 013 y del catálogo.
2. App `registro_materiales`: modelos, migraciones, servicios de cantidades y periodos.
3. Registro por orden y catálogo habilitado.
4. Saldos iniciales, despachos y reporte mensual.
5. 012 no depende de 013; 013 es el último módulo del orden global.

## Constitution Check

*GATE: verificado antes de la Fase 0 y re-evaluado después de la Fase 1.*

| Principio | Resultado | Evidencia / decisión |
|---|---|---|
| I. Aislamiento multitenant (NO NEGOCIABLE) | PASA | Todas las tablas llevan `tenant`; las consultas filtran por la sesión; un dato ajeno se trata como inexistente. RLS como respaldo. |
| II. Jerarquía Región → Tenant → Técnico | PASA | Solo la cuenta `USUARIO_TENANT` opera el módulo; técnicos y materiales se validan contra el tenant. Admin y almacén no operan salvo decisión de 001. |
| III. Invariantes de stock | PASA | 013 **no lee ni modifica** `StockGeneral`/`StockTecnico`; el saldo es un registro paralelo y no altera el inventario. |
| IV. Identidad y unicidad de series | PASA | 013 no crea ni modifica series; solo referencia renglones de recojo. |
| V. Integridad transaccional | PASA | Guardar orden, saldo o despacho es atómico; un fallo revierte datos y auditoría. |
| VI. Auditoría inmutable y trazabilidad | PASA | `OrdenLiquidacion`, `UsoMaterialOrden`, `SaldoInicialPeriodo`, `DespachoAlmacen` y `MaterialHabilitado` se auditan con valor anterior/nuevo; no se borra nada. |
| VII. Autoridad del reporte de Lari | PASA | 013 no procesa reportes Lari ni conciliaciones; es independiente de 010. |
| VIII. Spec-driven, pruebas y simplicidad | PASA | Cada criterio de aceptación tiene prueba. Sin dependencias nuevas; lógica en `services.py`; no hay Excel en 013. |

**Post-design re-check**: PASA. Se corrigió el nombre del catálogo y de las líneas de recojo, se
reutiliza la auditoría compartida, no se crean permisos Django y no se toca stock ni conciliación.

## Project Structure

```text
registro_materiales/
├── __init__.py
├── apps.py
├── models.py
├── services.py
├── forms.py
├── views.py
├── urls.py
└── migrations/
    ├── 0001_initial.py
    └── 0002_rls.py

templates/
└── registro_materiales/
    ├── registro_orden.html
    ├── _catalogo_orden.html
    ├── entradas.html
    ├── catalogo.html
    ├── reporte.html
    └── historial.html

tests/
├── unit/
│   ├── test_registro_servicios.py
│   ├── test_registro_saldos.py
│   └── test_registro_validaciones.py
├── integration/
│   ├── test_registro_ordenes.py
│   ├── test_registro_catalogo.py
│   ├── test_registro_despachos.py
│   ├── test_registro_saldos.py
│   ├── test_registro_reporte.py
│   ├── test_registro_auditoria.py
│   └── test_registro_aislamiento.py
└── contract/
    └── test_registro_http.py
```

También se modifican:

- `config/settings/base.py`: registrar `registro_materiales` y `REGISTRO_MATERIALES_PERIODOS_MAX`.
- `config/urls.py`: incluir `registro_materiales.urls`.
- `templates/base.html`: enlace “Registrar materiales” solo para `USUARIO_TENANT`.
- No se modifican modelos, migraciones ni servicios de 001/002/003/004/005/008/009/010/011/012.

## Modelo de datos

### `registro_materiales.MaterialHabilitado`

| Campo | Tipo | Nulo | Regla |
|---|---|---|---|
| `id` | `BigAutoField` | No | Clave primaria |
| `tenant` | FK `tenants.Tenant` | No | `PROTECT`, `related_name="materiales_habilitados"` |
| `material` | FK `materiales.Material` | No | `PROTECT`, `related_name="habilitaciones"` |
| `activo` | `BooleanField` | No | `default=True`; deshabilitar conserva historial |
| `orden` | `PositiveIntegerField` | No | `default=0`; orden de presentación |
| `creado_por` | FK `acceso.Usuario` | No | `PROTECT`, `related_name="+"` |
| `creado_en` | `DateTimeField` | No | `auto_now_add` |
| `actualizado_por` | FK `acceso.Usuario` | Sí | `PROTECT`, `related_name="+"` |
| `actualizado_en` | `DateTimeField` | No | `auto_now` |

- `UniqueConstraint(tenant, material, name="material_habilitado_unico")`.
- Índices `(tenant, activo, orden)` y `(material)`.
- Un material deshabilitado no se puede usar en nuevas órdenes; su historial se conserva.

### `registro_materiales.SaldoInicialPeriodo`

| Campo | Tipo | Nulo | Regla |
|---|---|---|---|
| `tenant` | FK `Tenant` | No | `PROTECT` |
| `material` | FK `Material` | No | `PROTECT` |
| `periodo` | `CharField(7)` | No | `YYYY-MM`; regex `^[0-9]{4}-(0[1-9]|1[0-2])$` |
| `cantidad` | `PositiveIntegerField` | No | `>=0` |
| `creado_por` | FK `Usuario` | No | `PROTECT` |
| `creado_en` | `DateTimeField` | No | `auto_now_add` |
| `actualizado_por` | FK `Usuario` | Sí | `PROTECT` |
| `actualizado_en` | `DateTimeField` | No | `auto_now` |

- `UniqueConstraint(tenant, material, periodo, name="saldo_inicial_unico")`.
- `CheckConstraint(cantidad >= 0)`.
- Solo un saldo manual por mes/material; si el periodo no tiene manual, se hereda.

### `registro_materiales.DespachoAlmacen`

| Campo | Tipo | Nulo | Regla |
|---|---|---|---|
| `tenant` | FK `Tenant` | No | `PROTECT` |
| `material` | FK `Material` | No | `PROTECT` |
| `recojo` | FK `recojos.Recojo` | No | `PROTECT`; del tenant |
| `recojo_linea` | FK `recojos.LineaRecojo` | No | `PROTECT`; del recojo |
| `fecha` | `DateField` | No | Define el periodo del despacho |
| `cantidad` | `PositiveIntegerField` | No | `>=0`; 0 se registra pero no suma |
| `creado_por` | FK `Usuario` | No | `PROTECT` |
| `creado_en` | `DateTimeField` | No | `auto_now_add` |
| `actualizado_por` | FK `Usuario` | Sí | `PROTECT` |
| `actualizado_en` | `DateTimeField` | No | `auto_now` |

- `CheckConstraint(cantidad >= 0)`.
- Índices `(tenant, fecha)`, `(tenant, material, fecha)` y `(recojo_linea)`.
- La suma de despachos de una línea no supera `recojo_linea.cantidad`; se valida bajo bloqueo.

### `registro_materiales.OrdenLiquidacion`

| Campo | Tipo | Nulo | Regla |
|---|---|---|---|
| `tenant` | FK `Tenant` | No | `PROTECT` |
| `tecnico` | FK `Tecnico` | No | `PROTECT`; del tenant |
| `numero_orden` | `CharField(30)` | No | 1–30 alfanuméricos, sin espacios internos; normalizado a mayúsculas |
| `fecha_liquidacion` | `DateField` | No | Fecha de la orden |
| `periodo` | `CharField(7)` | No | Derivado de la fecha; `YYYY-MM` |
| `creado_por` | FK `Usuario` | No | `PROTECT` |
| `actualizado_por` | FK `Usuario` | Sí | `PROTECT` |
| `creado_en` | `DateTimeField` | No | `auto_now_add` |
| `actualizado_en` | `DateTimeField` | No | `auto_now` |

- `UniqueConstraint(tenant, tecnico, periodo, numero_orden, name="orden_unica_por_tecnico_mes_numero")`.
- `CheckConstraint(numero_orden regex ^[A-Z0-9]{1,30}$)`.
- `CheckConstraint(periodo regex)`.
- Índices `(tenant, periodo)`, `(tenant, tecnico, periodo)` y `(numero_orden)`.
- La misma orden puede existir para otro técnico o en otro mes.
- Si la orden ya existe para la clave, se abre para editar; no se duplica.

### `registro_materiales.UsoMaterialOrden`

| Campo | Tipo | Nulo | Regla |
|---|---|---|---|
| `tenant` | FK `Tenant` | No | `PROTECT` |
| `orden` | FK `OrdenLiquidacion` | No | `CASCADE` |
| `tecnico` | FK `Tecnico` | No | `PROTECT`; debe coincidir con `orden.tecnico` |
| `material` | FK `Material` | No | `PROTECT`; habilitado para el tenant |
| `cantidad` | `PositiveIntegerField` | No | `default=0`; `>=0` |
| `creado_por` | FK `Usuario` | No | `PROTECT` |
| `creado_en` | `DateTimeField` | No | `auto_now_add` |
| `actualizado_por` | FK `Usuario` | Sí | `PROTECT` |
| `actualizado_en` | `DateTimeField` | No | `auto_now` |

- `UniqueConstraint(orden, material, name="uso_unico_por_orden_material")`.
- `CheckConstraint(cantidad >= 0)`.
- Índices `(tenant, tecnico, material)`, `(tenant, material)` y `(orden)`.
- Una línea con cantidad 0 se conserva si existió; no se borra.
- La cantidad se normaliza y valida como entero `>=0`.

### Entidades externas consumidas

| Entidad | Dueña | Uso en 013 |
|---|---|---|
| `materiales.Material` | 002 | Catálogo compartido; no se duplica. |
| `recojos.Recojo` / `LineaRecojo` | 004 | Respaldo del despacho; solo lectura. |
| `tecnicos.Tecnico` | 003 | Técnico de la orden y del uso. |
| `tenants.Tenant` | 001 | Alcance y RLS. |
| `auditoria.RegistroCambio` | 001 | Auditoría compartida. |

## Migraciones

1. `registro_materiales/migrations/0001_initial.py`: `MaterialHabilitado`, `SaldoInicialPeriodo`,
   `DespachoAlmacen`, `OrdenLiquidacion` y `UsoMaterialOrden` con restricciones e índices.
2. `registro_materiales/migrations/0002_rls.py`: RLS por `tenant_id` en todas las tablas.
3. No se modifican migraciones de apps existentes.
4. No se cargan datos iniciales por migración; el catálogo habilitado se carga por la interfaz del
   tenant o por un comando de administración.

## Servicios (lógica de negocio)

Viven en `registro_materiales/services.py`; las vistas solo orquestan.

### Excepciones

- `PermisoDenegado`: “No tienes permiso para registrar materiales”.
- `TecnicoNoExiste`: “El técnico no pertenece a tu tenant”.
- `MaterialNoHabilitado`: “El material no está habilitado para tu tenant”.
- `MaterialInactivo`: “El material está deshabilitado”.
- `CantidadInvalida`: “La cantidad debe ser un número entero mayor o igual a 0”.
- `NumeroOrdenInvalido`: “El número de orden es obligatorio y debe tener entre 1 y 30 caracteres
  alfanuméricos”.
- `PeriodoInvalido`: “El periodo debe tener el formato AAAA-MM”.
- `RecojoNoExiste`: “El recojo no pertenece a tu tenant”.
- `LineaRecojoNoExiste`: “La línea de recojo no pertenece al recojo”.
- `MaterialNoCoincide`: “El material no coincide con la línea de recojo”.
- `DespachoExcedeRecojo`: “La cantidad despachada supera la cantidad del recojo”.
- `TecnicoNoCoincide`: “El técnico de la línea no coincide con el técnico de la orden”.
- `NoEncontrado`: “El registro no existe”.

### Periodos y cantidades

- `periodo_de_fecha(fecha) -> str`: `YYYY-MM`.
- `validar_periodo(periodo)`: regex y fecha real.
- `normalizar_numero_orden(valor) -> str`: `strip`, mayúsculas, sin espacios internos; 1–30
  alfanuméricos.
- `validar_cantidad(valor, permitir_vacio=False) -> int`: normaliza espacios; vacío → 0 si se permite;
  rechaza negativos, decimales y texto; devuelve entero `>=0`.

### Catálogo habilitado

- `materiales_habilitados(tenant, incluir_inactivos=False)`.
- `habilitar_material(tenant, material, actor)`: crea o reactiva; audita `MaterialHabilitado/alta` o
  `activo`.
- `deshabilitar_material(tenant, material, actor)`: marca inactivo; audita; conserva historial.

### Órdenes y usos

- `obtener_orden(tenant, tecnico, numero_orden, fecha)`:
  - Normaliza número y calcula periodo.
  - Busca por `(tenant, tecnico, periodo, numero_orden)`.
  - Devuelve la orden existente o una instancia nueva sin guardar.
- `guardar_orden(tenant, tecnico, numero_orden, fecha, cantidades, actor)`:
  1. Valida cuenta, técnico, número, fecha y cantidades.
  2. Solo acepta materiales habilitados y activos para líneas nuevas; permite editar líneas existentes
     aunque el material se haya deshabilitado después.
  3. En `transaction.atomic`:
     - Bloquear `Tenant` y, si existe, la orden con `select_for_update`.
     - Calcular el periodo desde la fecha.
     - Crear o actualizar la orden y revalidar la unicidad de la nueva clave.
     - Comparar las cantidades anteriores con las nuevas; crear/actualizar `UsoMaterialOrden` y poner
       a 0 las que dejaron de usarse; no borrar.
     - Auditar `OrdenLiquidacion/alta`, `OrdenLiquidacion/periodo`, `OrdenLiquidacion/numero_orden`,
       `OrdenLiquidacion/fecha_liquidacion`, `UsoMaterialOrden/alta` y `UsoMaterialOrden/cantidad`.
  4. Si dos guardados crean la misma clave, la restricción única decide; el segundo recarga la orden
     existente y la actualiza con auditoría, sin duplicar.
  5. Devuelve la orden.
- `historial_orden(tenant, orden_id)`: devuelve los `RegistroCambio` de la orden y sus usos.

### Saldos iniciales

- `registrar_saldo_inicial(tenant, material, periodo, cantidad, actor)`:
  - Valida material habilitado/activo, periodo y cantidad.
  - `transaction.atomic`: crea o actualiza el saldo manual; audita `SaldoInicialPeriodo/alta` y
    `/cantidad` con valor anterior/nuevo.
- `saldo_inicial_efectivo(tenant, material, periodo)`:
  - Si existe saldo manual, lo devuelve.
  - Si no, busca el periodo anterior con datos (manual, despacho o uso) y calcula su saldo final;
    si no hay datos anteriores, devuelve 0.
  - Itera desde el periodo más antiguo con datos hasta el anterior, sin recursión infinita.
- `saldo_final(tenant, material, periodo)`:
  - `inicial + despachos - usado`; puede ser negativo (alerta, no bloqueo).

### Despachos

- `registrar_despacho(tenant, recojo, recojo_linea, material, fecha, cantidad, actor)`:
  - Valida cuenta, recojo/línea del tenant, material de la línea, fecha y cantidad.
  - `transaction.atomic`: bloquea `Tenant`, `LineaRecojo` y despachos de la línea; suma los existentes
    (excluyendo el que se edita) y verifica que no superen `recojo_linea.cantidad`.
  - Crea el despacho; audita `DespachoAlmacen/alta`.
- `actualizar_despacho(despacho, fecha, cantidad, actor)`:
  - Valida pertenencia y cantidad; recalcula la suma de la línea excluyendo el despacho.
  - Actualiza fecha/cantidad; audita valores anterior/nuevo.
- `despachos_del_periodo(tenant, periodo)` y `recojos_del_tenant(tenant, q="")` para selectores.

### Reporte mensual

- `reporte_mensual(tenant, periodo)`:
  - Materiales: todos los habilitados activos más los que tengan saldo, despacho o uso en el periodo.
  - Por material: `saldo_inicial`, `despachos`, `usado`, `saldo_final`.
  - Detalle por técnico: NIF y cantidad usada por material.
  - `saldo_final < 0` marca alerta.
  - Usa agregaciones y `select_related`; sin N+1.
- `resumen_materiales` y `detalle_tecnicos` para la plantilla.

## Interfaz y endpoints

| Ruta | Método | Función |
|---|---|---|
| `/registro-materiales/` | GET | Pantalla de registro por orden |
| `/registro-materiales/orden/contexto/` | GET | Fragmento HTMX con orden existente o catálogo |
| `/registro-materiales/orden/guardar/` | POST | Guardar orden y usos |
| `/registro-materiales/ordenes/<id>/historial/` | GET | Historial de la orden y sus usos |
| `/registro-materiales/materiales/` | GET/POST | Catálogo habilitado; habilitar/deshabilitar |
| `/registro-materiales/entradas/` | GET | Saldos y despachos del periodo |
| `/registro-materiales/saldo-inicial/guardar/` | POST | Guardar saldo inicial |
| `/registro-materiales/despachos/guardar/` | POST | Registrar despacho |
| `/registro-materiales/despachos/<id>/editar/` | POST | Editar despacho |
| `/registro-materiales/recojos/buscar/` | GET | Buscar recojos y líneas del tenant |
| `/registro-materiales/reporte/` | GET | Reporte mensual |

### Pantalla de registro por orden

- Selector de técnico del tenant.
- Número de orden y fecha de liquidación.
- Al enviar el contexto, el sistema devuelve la orden existente o el catálogo habilitado con 0.
- Tabla: código, descripción, lote, cantidad usada.
- Guardar conserva técnico y fecha, limpia número y devuelve el foco.
- Cambiar de técnico reinicia el formulario.
- Un material deshabilitado no aparece para nuevas órdenes, pero sus líneas históricas se muestran.

### Pantallas de entradas y catálogo

- Entradas: periodo, saldo inicial editable por material y despachos del periodo con recojo/línea.
- Catálogo: materiales del catálogo compartido con estado habilitado/inactivo; activar/desactivar.
- Reporte: tabla por material y detalle expandible por técnico; alerta si el saldo final es negativo.

## Validaciones (dónde vive cada una)

| Regla | Dónde se valida | Mensaje |
|---|---|---|
| Cantidad entera ≥ 0 | Formulario, servicio y `CheckConstraint` | “La cantidad debe ser un número entero mayor o igual a 0” |
| Número de orden obligatorio/1–30 alfanumérico | Formulario, servicio y `CheckConstraint` | “El número de orden es obligatorio y debe tener entre 1 y 30 caracteres alfanuméricos” |
| Periodo `YYYY-MM` | Servicio y `CheckConstraint` | “El periodo debe tener el formato AAAA-MM” |
| Orden única por tenant/técnico/periodo/número | Servicio y restricción única | Si existe, se abre para editar |
| Técnico del tenant | Servicio | “El técnico no pertenece a tu tenant” |
| Material habilitado/activo | Servicio | “El material no está habilitado para tu tenant” / “El material está deshabilitado” |
| Técnico de línea = técnico de orden | Servicio | “El técnico de la línea no coincide con el técnico de la orden” |
| Recojo/línea del tenant | Servicio | “El recojo no pertenece a tu tenant” / “La línea de recojo no pertenece al recojo” |
| Material de la línea | Servicio | “El material no coincide con la línea de recojo” |
| Despacho ≤ línea de recojo | Servicio y bloqueo | “La cantidad despachada supera la cantidad del recojo” |
| Permiso del módulo | Servicio y vista | “No tienes permiso para registrar materiales” |

## Transacciones y concurrencia

- Cada guardado de orden, saldo o despacho es una transacción.
- La restricción única de la orden y el bloqueo de la línea de recojo son la fuente de verdad ante
  doble clic o sesiones simultáneas.
- Dos despachos simultáneos de la misma línea se serializan y no superan la cantidad del recojo.
- La auditoría se inserta en la misma transacción; si falla, se revierte el cambio.
- No se usan `F()` ciegos ni borrados.

## Auditoría y RLS

- Eventos:
  - `MaterialHabilitado/alta` y `/activo`.
  - `SaldoInicialPeriodo/alta` y `/cantidad`.
  - `DespachoAlmacen/alta`, `/fecha` y `/cantidad`.
  - `OrdenLiquidacion/alta`, `/numero_orden`, `/fecha_liquidacion` y `/periodo`.
  - `UsoMaterialOrden/alta` y `/cantidad`.
- El actor es el usuario de la sesión; `tenant` se toma del actor/entidad.
- No se auditan secretos ni datos de otro tenant.
- RLS:
  - `registro_materiales_materialhabilitado`, `saldos`, `despachos`, `ordenes` y `usos` por
    `tenant_id`.
  - Si 001 no está disponible, deuda y filtrado ORM.
- El rol de aplicación no es superusuario ni `BYPASSRLS`.

## Pruebas

Un caso por criterio de aceptación, más restricciones, cálculo, concurrencia y aislamiento.

| Criterio | Prueba principal |
|---|---|
| Menú solo tenant | `test_menu_registrar_materiales_solo_para_tenant` |
| Catálogo en orden nueva | `test_orden_nueva_muestra_catalogo_habilitado` |
| Orden existente se abre | `test_orden_duplicada_mismo_tecnico_y_mes_abre_existente` |
| Misma orden otro técnico/mes | `test_misma_orden_en_otro_tecnico_o_mes_se_permite` |
| Cantidad 0 no suma | `test_cantidad_vacia_o_cero_no_suma_uso` |
| Cantidad inválida | `test_cantidad_negativa_decimal_o_texto_se_rechaza` |
| Saldo final | `test_saldo_final_es_inicial_mas_despachos_menos_usado` |
| Herencia de saldo | `test_mes_sin_saldo_inicial_hereda_final_anterior` |
| Saldo manual prevalece | `test_saldo_inicial_manual_prevalece_y_se_audita` |
| Despacho del tenant | `test_despacho_vinculado_a_recojo_del_tenant` |
| Despacho ajeno | `test_despacho_con_recojo_de_otro_tenant_se_rechaza` |
| Despacho excede línea | `test_despacho_mayor_a_linea_de_recojo_se_rechaza` |
| Técnico de línea | `test_uso_con_tecnico_distinto_al_de_la_orden_se_rechaza` |
| Historial | `test_editar_orden_registra_historial` |
| Aislamiento | `test_aislamiento_entre_tenants_en_ordenes_y_reporte` |
| Reporte detalle | `test_reporte_mensual_incluye_detalle_por_tecnico` |
| Doble clic | `test_doble_clic_no_crea_orden_duplicada` |
| Cambio de fecha/mes | `test_cambio_de_fecha_a_otro_mes_revalida_unicidad` |
| Saldo negativo | `test_saldo_final_negativo_se_muestra_con_alerta` |

Además:

- **Catálogo**: habilitar, deshabilitar, reactivar y material no habilitado.
- **Saldos**: manual prevalece, herencia encadenada, sin datos = 0, cantidades inválidas.
- **Despachos**: cantidad 0, suma acumulada, edición, línea inexistente, material distinto.
- **Órdenes**: número con espacios/guiones, fecha a otro mes, orden de otro tenant, doble clic.
- **Reporte**: totales por material, detalle por técnico, saldo negativo con alerta.
- **Auditoría**: un registro por cambio, valores anterior/nuevo, sin secretos.
- **Aislamiento**: dos tenants, datos ajenos como inexistentes; RLS si está disponible.
- **Rendimiento**: reporte de 100 materiales y 1 000 usos en tiempo razonable, sin N+1.

## Correcciones documentales necesarias

| Documento | Corrección |
|---|---|
| `013-registro-materiales/plan.md` | Este documento reemplaza el plan anterior. |
| `013-registro-materiales/spec.md` §5.4 y regla 4 | Aclarar que la unicidad es por tenant, técnico, periodo y número de orden; se permiten varias órdenes del mismo técnico en el mes con números distintos. |
| `013-registro-materiales/plan.md` anterior | `catalogo.Material` → `materiales.Material`; `recojos.RecojoLinea` → `recojos.LineaRecojo`; no duplicar `RegistroCambio`; no permisos Django; FK `PROTECT`. |
| `05-especificaciones/004-recojo-de-materiales/data-model.md` | Sin cambios; se referencia `Recojo`/`LineaRecojo`. |
| `03-reglas-de-dominio/catalogo-de-materiales.md` | Sigue vacío; se usa 002 como fuente vigente (deuda existente). |

## Decisiones y riesgos

- **Catálogo compartido habilitado por tenant**: no duplica códigos/descripciones; el tenant solo
  habilita lo que usa. Alternativa descartada: copiar materiales por tenant.
- **Unicidad de orden con número**: permite varias órdenes del mismo técnico en el mes, como exige el
  flujo. Alternativa descartada: una sola orden por técnico/mes.
- **Saldo inicial heredado**: se calcula desde el mes anterior con datos; no se persiste un saldo
  final mensual. Alternativa descartada: tabla de saldos calculados (deuda de rendimiento).
- **Despacho vinculado a recojo**: garantiza respaldo y no toca stock. Alternativa descartada:
  despacho libre sin recojo.
- **Sin borrado**: los usos a 0 se conservan y se auditan. Alternativa descartada: borrar líneas.
- **Sin Excel/PDF**: fuera de alcance de 013.
- **Riesgo de herencia larga**: se itera desde el periodo más antiguo con datos; se limita con
  `REGISTRO_MATERIALES_PERIODOS_MAX` y se documenta.
- **Riesgo de concurrencia en despachos**: bloqueo de la línea y suma bajo transacción.
- **Riesgo de datos históricos**: materiales deshabilitados se muestran en órdenes existentes, no en
  nuevas.

## Complexity Tracking

| Decisión | Por qué no viola la constitución |
|---|---|
| Módulo separado del stock | La spec lo declara independiente; no lee ni escribe stock. |
| Catálogo habilitado por tenant | No duplica el catálogo global; solo agrega una relación de disponibilidad. |
| Saldo calculado a demanda | No crea una fuente paralela persistida; usa saldos manuales y movimientos. |
| Sin permisos Django | Usa roles del dominio y alcance de sesión, como el resto del sistema. |
| Sin exportación | La spec la excluye expresamente. |

## Criterios de salida

- `research.md`, `data-model.md`, `contracts/` y `quickstart.md` creados y coherentes con este plan.
- Plan sin `catalogo.Material`, sin `RecojoLinea`, sin tabla de auditoría duplicada, sin permisos
  Django y sin escrituras a stock/conciliación.
- Correcciones de 013 registradas y aplicadas antes de implementar.
- `tasks.md` derivado de este plan cubre todos los criterios de aceptación con al menos una prueba.
- No se implementa código en esta fase.
