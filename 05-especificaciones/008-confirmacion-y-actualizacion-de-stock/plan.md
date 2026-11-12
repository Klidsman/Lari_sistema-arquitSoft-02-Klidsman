# Plan técnico: 008 Confirmación y Actualización de Stock

## Referencias
- Spec: `05-especificaciones/008-confirmacion-y-actualizacion-de-stock/spec.md`
- Reglas: `03-reglas-de-dominio/stock.md`, `series.md`, `auditoria.md`
- ADR: ADR-012 (conciliación)
- Stack: Django LTS, PostgreSQL y pytest, según la sección final de la constitución.

## Módulos afectados
- App Django `stock`: modelo `StockGeneral`, `StockTecnico` y servicios de actualización.
- App `series`: cambio de estado de series (Reservada → Asignada).
- App `auditoria`: modelo `RegistroCambio`, compartido.
- Integración con `asignaciones` (spec 007) para la confirmación.
- No se modifican recojos, traspasos ni conciliaciones.

> **Dependencia de las specs 004 y 005:** la parte fundacional de esta spec
> (`StockGeneral`, `incrementar_stock_general`, `StockTecnico`, `incrementar_stock_tecnico` y
> `decrementar_stock_tecnico`) debe existir antes de implementar el recojo (004) y el stock inicial
> de técnicos (005). 004 consume `StockGeneral` e `incrementar_stock_general`; 005 consume
> `StockTecnico` y los servicios de incremento/decremento, y nunca toca `StockGeneral`. La
> confirmación de asignaciones de esta spec puede completarse después de 007.

## Modelo de datos

```python
class StockGeneral(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="stock_general",
    )
    material = models.ForeignKey(
        "materiales.Material",
        on_delete=models.PROTECT,
        related_name="stock_general",
    )
    cantidad = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "material"],
                name="stock_general_tenant_material_unico",
            ),
            models.CheckConstraint(
                condition=Q(cantidad__gte=0),
                name="stock_general_cantidad_no_negativa",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "material"], name="stock_general_tenant_material"),
        ]

    def __str__(self):
        return f"{self.tenant} - {self.material.codigo} - {self.cantidad}"


class StockTecnico(models.Model):
    tecnico = models.ForeignKey(
        "tecnicos.Tecnico",
        on_delete=models.PROTECT,
        related_name="stock_tecnico",
    )
    material = models.ForeignKey(
        "materiales.Material",
        on_delete=models.PROTECT,
        related_name="stock_tecnico",
    )
    cantidad = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tecnico", "material"],
                name="stock_tecnico_tecnico_material_unico",
            ),
            models.CheckConstraint(
                condition=Q(cantidad__gte=0),
                name="stock_tecnico_cantidad_no_negativa",
            ),
        ]
        indexes = [
            models.Index(fields=["tecnico", "material"], name="stock_tecnico_tecnico_material"),
        ]

    def __str__(self):
        return f"{self.tecnico.nif} - {self.material.codigo} - {self.cantidad}"
```

- `StockGeneral` representa el stock general del tenant por material.
- `StockTecnico` representa el stock de un técnico por material.
- Ambos tienen restricción única para evitar duplicados.
- Ambos tienen restricción de cantidad no negativa.
- Los índices optimizan las consultas por tenant/tecnico y material.

## Migraciones
- `stock/migrations/0001_initial.py`: modelos `StockGeneral` y `StockTecnico` con restricciones e índices.
- No se crea stock por migración.
- No se modifican tablas de series, asignaciones, traspasos ni conciliaciones.

## Servicios (lógica de negocio)
Viven en `stock/services.py`, no en las vistas.

### Actualización de stock al confirmar asignación
- `actualizar_stock_confirmacion_asignacion(solicitud, actor)`:
  - Esta función es llamada por `confirmar_solicitud` en spec 007.
  - En `transaction.atomic`:
    - Para cada línea seriada:
      - Cambia estado de serie a ASIGNADA.
      - Actualiza `StockTecnico`: si no existe, crea con cantidad=1; si existe, incrementa en 1.
      - Actualiza `StockGeneral`: si no existe, crea con cantidad=-1; si existe, decrementa en 1.
      - Registra auditoría del cambio de estado de serie.
      - Registra auditoría del cambio de stock técnico.
      - Registra auditoría del cambio de stock general.
    - Para cada línea no seriada:
      - Confirma la reserva (la cantidad ya está reservada, solo se actualiza).
      - Actualiza `StockTecnico`: si no existe, crea con cantidad=cantidad; si existe, incrementa en cantidad.
      - Actualiza `StockGeneral`: si no existe, crea con cantidad=-cantidad; si existe, decrementa en cantidad.
      - Registra auditoría del cambio de stock técnico.
      - Registra auditoría del cambio de stock general.
    - Inicia el conteo de días en mano para seriados (RF-61).
  - Si falla alguna actualización, toda la transacción se revierte.
  - Devuelve True si la actualización fue exitosa.

### Actualización de stock (genérico)
- `incrementar_stock_tecnico(tecnico, material, cantidad, actor)`:
  - Valida que `cantidad > 0`.
  - En `transaction.atomic`:
    - Obtiene o crea `StockTecnico`.
    - `stock_tecnico.cantidad += cantidad`.
    - Registra auditoría (valor anterior, valor nuevo).
  - Devuelve el `StockTecnico` actualizado.

- `decrementar_stock_tecnico(tecnico, material, cantidad, actor)`:
  - Valida que `cantidad > 0`.
  - Valida que el técnico tenga suficiente stock.
  - En `transaction.atomic`:
    - Obtiene `StockTecnico`.
    - `stock_tecnico.cantidad -= cantidad`.
    - Registra auditoría (valor anterior, valor nuevo).
  - Devuelve el `StockTecnico` actualizado.

- `incrementar_stock_general(tenant, material, cantidad, actor)`:
  - Valida que `cantidad > 0`.
  - En `transaction.atomic`:
    - Obtiene o crea `StockGeneral`.
    - `stock_general.cantidad += cantidad`.
    - Registra auditoría (valor anterior, valor nuevo).
  - Devuelve el `StockGeneral` actualizado.

- `decrementar_stock_general(tenant, material, cantidad, actor)`:
  - Valida que `cantidad > 0`.
  - Valida que el tenant tenga suficiente stock.
  - En `transaction.atomic`:
    - Obtiene `StockGeneral`.
    - `stock_general.cantidad -= cantidad`.
    - Registra auditoría (valor anterior, valor nuevo).
  - Devuelve el `StockGeneral` actualizado.

### Consultas de stock
- `obtener_stock_general(tenant, material)`:
  - Obtiene `StockGeneral` filtrando por tenant y material.
  - Si no existe, devuelve 0.

- `obtener_stock_tecnico(tecnico, material)`:
  - Obtiene `StockTecnico` filtrando por técnico y material.
  - Si no existe, devuelve 0.

- `calcular_disponible(tenant, material)`:
  - Obtiene el stock general.
  - Obtiene la cantidad reservada en asignaciones ENVIADA.
  - Devuelve: `Stock General - Reservado`.

### Auditoría de stock
- `registrar_cambio_stock_tecnico(tecnico, material, valor_anterior, valor_nuevo, actor)`:
  - Crea `RegistroCambio` con:
    - Entidad: "StockTecnico"
    - ID entidad: ID del registro de stock
    - Campo: "cantidad"
    - Valor anterior
    - Valor nuevo
    - Usuario: actor
    - Fecha: ahora

- `registrar_cambio_stock_general(tenant, material, valor_anterior, valor_nuevo, actor)`:
  - Crea `RegistroCambio` con:
    - Entidad: "StockGeneral"
    - ID entidad: ID del registro de stock
    - Campo: "cantidad"
    - Valor anterior
    - Valor nuevo
    - Usuario: actor
    - Fecha: ahora

## Permisos
- Las funciones de actualización de stock son internas, no tienen permisos directos.
- Se llaman desde otros módulos (asignaciones, traspasos, conciliación).
- Los módulos que llaman validan permisos y contexto.

## Interfaz y endpoints
- Esta spec no tiene endpoints directos.
- La actualización de stock se hace a través de la confirmación de asignación (spec 007).
- Los datos de stock se exponen a través de endpoints de otros módulos.

## Integraciones
- **Asignaciones (spec 007):** la confirmación llama a `actualizar_stock_confirmacion_asignacion`.
- **Traspasos (spec 009):** usa `incrementar_stock_tecnico` y `decrementar_stock_tecnico`.
- **Conciliación (spec 010):** usa `calcular_disponible` y actualiza stock al aprobar.
- **Series (transversal):** el cambio de estado de series se coordina con la actualización de stock.
- **Auditoría (transversal):** usa `RegistroCambio` compartido.

## Validaciones (dónde vive cada una)

| Regla | Dónde se valida | Mensaje |
|---|---|---|
| Cantidad > 0 | Servicio | "La cantidad debe ser mayor a 0" |
| Stock técnico suficiente | Servicio | "El técnico no tiene suficiente stock" |
| Stock general suficiente | Servicio | "El tenant no tiene suficiente stock general" |
| Cantidad no negativa | `CheckConstraint` | Violación de restricción de base de datos |
| Transaccionalidad | Servicio y transacción | Si falla, se revierte todo |

## Transacciones y concurrencia
- Cada actualización de stock se ejecuta en una transacción.
- La actualización completa de confirmación de asignación se ejecuta en una sola transacción.
- Si dos sesiones intentan actualizar el mismo stock simultáneamente:
  - La primera en escribir gana.
  - La segunda puede fallar si no hay suficiente stock.
- No se usan bloqueos de aplicación; las restricciones de base de datos resuelven conflictos.

## Pruebas
Un caso por criterio de aceptación. Nombres propuestos:

- `test_series_pasan_a_asignada_al_confirmar`
- `test_stock_tecnico_sube_al_confirmar`
- `test_stock_general_baja_al_confirmar`
- `test_actualizacion_transaccional_falla_revierte_todo`
- `test_dias_en_mano_inician_al_confirmar`
- `test_auditoria_completa_registra_todos_los_cambios`
- `test_no_seriados_actualizan_cantidad_correctamente`
- `test_incrementar_stock_tecnico_crea_si_no_existe`
- `test_decrementar_stock_tecnico_valida_suficiente`
- `test_incrementar_stock_general_crea_si_no_existe`
- `test_decrementar_stock_general_valida_suficiente`
- `test_calcular_disponible_descontando_reservado`

Además, pruebas de base de datos:
- Insertar stock con cantidad negativa directamente debe fallar.
- Insertar dos registros de stock general para el mismo tenant y material debe fallar.
- Insertar dos registros de stock técnico para el mismo técnico y material debe fallar.

## Decisiones y riesgos
- **Modelos separados de stock:** `StockGeneral` y `StockTecnico` son tablas separadas para consultas eficientes. Alternativa: campos en `Tenant` y `Tecnico`, pero sería menos escalable.
- **Stock por material:** el stock se rastrea por material, no por serie. Las series se rastrean en el módulo de series. Esto mantiene separación de responsabilidades.
- **Creación si no existe:** las funciones de actualización crean el registro si no existe. Esto simplifica el código pero requiere validar restricciones.
- **Transaccionalidad es crítica:** si falla una actualización, toda la operación se revierte. Esto requiere que todas las actualizaciones estén en la misma transacción.
- **Auditoría compartida:** se usa `RegistroCambio` para evitar un sistema de auditoría por módulo.
- **Riesgo de inconsistencia:** si una actualización de stock falla después de cambiar el estado de series, la transacción revierte todo. Esto es correcto pero requiere manejo de errores cuidadoso.
- **Riesgo de concurrencia:** dos operaciones pueden intentar actualizar el mismo stock simultáneamente. Las restricciones de cantidad no negativa y la validación de suficiente stock manejan esto.
- **Cálculo de días en mano:** se puede calcular a demanda (al consultar) o en background. A demanda es más simple pero puede ser lento con muchos registros. Background es más complejo pero más eficiente.
