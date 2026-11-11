# Plan técnico: 013 Registro de materiales

## Referencias
- Spec: `05-especificaciones/013-registro-materiales/spec.md`
- Reglas: `03-reglas-de-dominio/registro-materiales.md`, `auditoria.md`
- Arquitectura: `docs/02-arquitectura-software/arquitectura.md`
- Stack: Django LTS, PostgreSQL, HTMX y pytest, según la sección final de la constitución.

## Módulos afectados
- App Django nueva `registro_materiales`: modelos, servicios, formularios, vistas y plantillas.
- App `auditoria`: modelo `RegistroCambio`, compartido. Si no existe, se crea en este módulo.
- Integración de solo lectura con:
  - `tenants.Tenant`
  - `tecnicos.Tecnico`
  - `catalogo.Material`
  - `recojos.Recojo` y `recojos.RecojoLinea`

No se modifican modelos, servicios, rutas ni migraciones de los módulos existentes.

## Modelo de datos

```python
class MaterialHabilitado(models.Model):
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="materiales_habilitados")
    material = models.ForeignKey("catalogo.Material", on_delete=models.PROTECT, related_name="+")
    activo = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)
    creado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+")
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "material"],
                name="material_habilitado_unico_por_tenant",
            ),
        ]
```

```python
class SaldoInicialPeriodo(models.Model):
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="+")
    material = models.ForeignKey("catalogo.Material", on_delete=models.PROTECT, related_name="+")
    periodo = models.CharField(max_length=7)  # YYYY-MM
    cantidad = models.PositiveIntegerField()
    usuario = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "material", "periodo"],
                name="saldo_inicial_unico_por_mes",
            ),
            models.CheckConstraint(
                condition=Q(periodo__regex=r"^[0-9]{4}-(0[1-9]|1[0-2])$"),
                name="saldo_inicial_periodo_valido",
            ),
            models.CheckConstraint(
                condition=Q(cantidad__gte=0),
                name="saldo_inicial_cantidad_no_negativa",
            ),
        ]
```

```python
class DespachoAlmacen(models.Model):
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="+")
    material = models.ForeignKey("catalogo.Material", on_delete=models.PROTECT, related_name="+")
    recojo = models.ForeignKey("recojos.Recojo", on_delete=models.PROTECT, related_name="+")
    recojo_linea = models.ForeignKey("recojos.RecojoLinea", on_delete=models.PROTECT, related_name="+")
    fecha = models.DateField()
    cantidad = models.PositiveIntegerField()
    usuario = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "fecha"], name="despacho_tenant_fecha"),
            models.Index(fields=["tenant", "material", "fecha"], name="despacho_tenant_material_fecha"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(cantidad__gte=0),
                name="despacho_cantidad_no_negativa",
            ),
        ]
```

```python
class OrdenLiquidacion(models.Model):
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="+")
    tecnico = models.ForeignKey("tecnicos.Tecnico", on_delete=models.PROTECT, related_name="+")
    numero_orden = models.CharField(max_length=30)
    fecha_liquidacion = models.DateField()
    periodo = models.CharField(max_length=7)  # YYYY-MM, derivado de la fecha
    creado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+")
    actualizado_por = models.ForeignKey(User, null=True, on_delete=models.PROTECT, related_name="+")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "tecnico", "periodo", "numero_orden"],
                name="orden_unica_por_tecnico_y_mes",
            ),
            models.CheckConstraint(
                condition=~Q(numero_orden=""),
                name="orden_numero_obligatorio",
            ),
            models.CheckConstraint(
                condition=Q(periodo__regex=r"^[0-9]{4}-(0[1-9]|1[0-2])$"),
                name="orden_periodo_valido",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "periodo"], name="orden_tenant_periodo"),
        ]
```

```python
class UsoMaterialOrden(models.Model):
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="+")
    orden = models.ForeignKey(OrdenLiquidacion, on_delete=models.CASCADE, related_name="usos")
    tecnico = models.ForeignKey("tecnicos.Tecnico", on_delete=models.PROTECT, related_name="+")
    material = models.ForeignKey("catalogo.Material", on_delete=models.PROTECT, related_name="+")
    cantidad = models.PositiveIntegerField()
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["orden", "material"],
                name="uso_unico_por_orden_y_material",
            ),
            models.CheckConstraint(
                condition=Q(cantidad__gte=0),
                name="uso_cantidad_no_negativa",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "tecnico", "material"], name="uso_tenant_tecnico_material"),
            models.Index(fields=["tenant", "material"], name="uso_tenant_material"),
        ]
```

```python
class RegistroCambio(models.Model):
    # Tabla de auditoría compartida (ver auditoria.md)
    entidad = models.CharField(max_length=50)
    entidad_id = models.BigIntegerField()
    campo = models.CharField(max_length=50)
    valor_anterior = models.TextField(blank=True)
    valor_nuevo = models.TextField(blank=True)
    usuario = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+")
    fecha = models.DateTimeField(auto_now_add=True)
```

- Solo inserción: el servicio nunca actualiza ni borra filas de auditoría.
- `RegistroCambio` se usa para orden, saldo inicial, despacho y uso.
- Si la app `auditoria` ya existe, se reutiliza; no se modifica su estructura.

## Migraciones
- `registro_materiales/migrations/0001_initial.py`: crea `MaterialHabilitado`, `SaldoInicialPeriodo`, `DespachoAlmacen`, `OrdenLiquidacion` y `UsoMaterialOrden`, con sus índices y restricciones.
- Si `auditoria` no existe, `auditoria/migrations/0001_initial.py` crea `RegistroCambio`.
- No se modifican migraciones de apps existentes.
- No se agregan datos iniciales por migración. El catálogo habilitado se carga por tenant desde la interfaz o por un comando de administración posterior.

## Servicios (lógica de negocio)
Viven en `registro_materiales/services.py`, no en las vistas.

- `periodo_de_fecha(fecha)` → `YYYY-MM`.
- `validar_cantidad(valor)`:
  - Normaliza espacios.
  - Rechaza vacío cuando es obligatorio.
  - Rechaza negativos, decimales y texto.
  - Devuelve un entero ≥ 0.
- `obtener_orden(tenant, tecnico, numero_orden, fecha)`:
  - Busca por `(tenant, tecnico, periodo, numero_orden)`.
  - Devuelve la orden existente o una orden nueva sin guardar.
- `guardar_orden(tenant, tecnico, numero_orden, fecha, lineas, usuario)`:
  - Valida técnico del tenant y fecha.
  - Calcula el periodo desde la fecha.
  - En `transaction.atomic`:
    - Crea o actualiza la orden.
    - Compara las cantidades anteriores con las nuevas.
    - Crea, actualiza o deja en 0 las líneas de uso.
    - Registra un `RegistroCambio` por cada campo modificado y por cada línea.
  - Si la clave única ya existe, devuelve la orden existente en lugar de fallar.
- `registrar_saldo_inicial(tenant, material, periodo, cantidad, usuario)`:
  - Valida material habilitado y cantidad.
  - En `transaction.atomic`, crea o actualiza el saldo del periodo.
  - Audita el valor anterior y el nuevo.
- `registrar_despacho(tenant, recojo, recojo_linea, material, fecha, cantidad, usuario)`:
  - Valida que recojo y línea pertenezcan al tenant.
  - Valida que el material corresponda a la línea.
  - Suma los despachos existentes de la línea y verifica que no superen la cantidad del recojo.
  - En `transaction.atomic`, crea el despacho y audita.
- `saldo_inicial_efectivo(tenant, material, periodo)`:
  - Si existe `SaldoInicialPeriodo`, lo devuelve.
  - Si no, calcula el saldo final del periodo anterior.
  - Si no hay periodo anterior, devuelve 0.
- `saldo_final(tenant, material, periodo)`:
  - `inicial + despachos - usado`.
- `reporte_mensual(tenant, periodo)`:
  - Agrupa por material: saldo inicial, despachos, usado, saldo final.
  - Agrupa el detalle por técnico `LAXXXX`.
  - Devuelve una estructura lista para la plantilla.

## Permisos
- `registro_materiales.registrar`: registrar órdenes, saldos y despachos.
- `registro_materiales.ver_reporte`: consultar el reporte mensual.
- Ambos permisos se asignan a la cuenta única del tenant definida en la spec 001.
- El Administrador de plataforma y el Responsable de almacén no los reciben por defecto.

## Interfaz y endpoints

| Ruta | Método | Función |
|---|---|---|
| `/registro-materiales/` | GET | Pantalla de registro por orden |
| `/registro-materiales/orden/contexto/` | GET | Fragmento HTMX con la orden existente o el catálogo |
| `/registro-materiales/orden/guardar/` | POST | Guardar la orden y sus usos |
| `/registro-materiales/ordenes/<id>/historial/` | GET | Historial de cambios |
| `/registro-materiales/entradas/` | GET | Saldos iniciales y despachos del periodo |
| `/registro-materiales/saldo-inicial/guardar/` | POST | Guardar un saldo inicial |
| `/registro-materiales/despachos/guardar/` | POST | Registrar un despacho |
| `/registro-materiales/recojos/buscar/` | GET | Buscar recojos y líneas del tenant |
| `/registro-materiales/reporte/` | GET | Reporte mensual por material y técnico |

### Pantalla de registro por orden
- Selector de técnico del tenant.
- Campo número de orden.
- Campo fecha de liquidación.
- Al presionar Enter en el número de orden, se dispara una petición HTMX que devuelve:
  - La orden existente con sus cantidades, si ya existe.
  - El catálogo habilitado con cantidades en 0, si es nueva.
- Tabla de materiales con columnas código, descripción, lote y cantidad usada.
- Guardar conserva técnico y fecha, limpia el número de orden y devuelve el foco al campo.
- Cambiar de técnico reinicia el formulario.

### Pantalla de entradas manuales
- Selector de periodo.
- Tabla de materiales con saldo inicial editable y guardado individual.
- Formulario de despacho: recojo, línea de recojo, material, fecha y cantidad.
- Listado de despachos del periodo con su recojo asociado.

### Pantalla de reporte
- Selector de periodo.
- Tabla por material: saldo inicial, despachos, usado, saldo final.
- Detalle expandible por técnico: material y cantidad usada.
- Alerta visual si el saldo final es negativo.

## Validaciones (dónde vive cada una)

| Regla | Dónde se valida | Mensaje |
|---|---|---|
| Cantidad entera ≥ 0 | Formulario, servicio y `CheckConstraint` | “La cantidad debe ser un número entero mayor o igual a 0” |
| Número de orden obligatorio | Formulario y `CheckConstraint` | “El número de orden es obligatorio” |
| Periodo válido | Servicio y `CheckConstraint` | “El periodo debe tener el formato AAAA-MM” |
| Orden única por técnico y mes | Servicio y restricción única | Si existe, se abre para editar |
| Técnico del tenant | Servicio | “El técnico no pertenece a tu tenant” |
| Material habilitado | Servicio | “El material no está habilitado para tu tenant” |
| Técnico de la línea igual al de la orden | Servicio | “El técnico de la línea no coincide con el técnico de la orden” |
| Recojo del tenant | Servicio | “El recojo no pertenece a tu tenant” |
| Cantidad dentro del recojo | Servicio | “La cantidad despachada supera la cantidad del recojo” |
| Permiso de operación | Servicio y vista | “No tienes permiso para registrar materiales” |

## Transacciones y concurrencia
- Cada guardado de orden, saldo o despacho se ejecuta en `transaction.atomic`.
- La restricción única de la base de datos es la fuente de verdad ante doble clic o dos sesiones simultáneas.
- Si dos sesiones crean la misma orden, la segunda recibe la orden existente y la abre para editar.
- La auditoría se inserta en la misma transacción que el cambio.
- No se usan bloqueos de aplicación para reemplazar las restricciones de base de datos.

## Aislamiento multitenant
- El tenant se obtiene de la cuenta autenticada, nunca de un campo del formulario.
- Todas las consultas usan `tenant` como primer filtro.
- Las claves únicas incluyen `tenant`.
- Los objetos de otro tenant responden como inexistentes.
- Se recomienda RLS en PostgreSQL como respaldo.
- Las pruebas crean dos tenants y verifican que no hay filtración en órdenes, saldos, despachos, usos ni reportes.

## Pruebas
Un caso por criterio de aceptación. Nombres propuestos:

- `test_menu_registrar_materiales_solo_para_tenant`
- `test_orden_nueva_muestra_catalogo_habilitado`
- `test_orden_duplicada_mismo_tecnico_y_mes_abre_existente`
- `test_misma_orden_en_otro_tecnico_o_mes_se_permite`
- `test_cantidad_vacia_o_cero_no_suma_uso`
- `test_cantidad_negativa_decimal_o_texto_se_rechaza`
- `test_saldo_final_es_inicial_mas_despachos_menos_usado`
- `test_mes_sin_saldo_inicial_hereda_final_anterior`
- `test_saldo_inicial_manual_prevalece_y_se_audita`
- `test_despacho_vinculado_a_recojo_del_tenant`
- `test_despacho_con_recojo_de_otro_tenant_se_rechaza`
- `test_despacho_mayor_a_linea_de_recojo_se_rechaza`
- `test_uso_con_tecnico_distinto_al_de_la_orden_se_rechaza`
- `test_editar_orden_registra_historial`
- `test_aislamiento_entre_tenants_en_ordenes_y_reporte`
- `test_reporte_mensual_incluye_detalle_por_tecnico`
- `test_doble_clic_no_crea_orden_duplicada`
- `test_cambio_de_fecha_a_otro_mes_revalida_unicidad`
- `test_saldo_final_negativo_se_muestra_con_alerta`

Además, pruebas de restricciones de base de datos:
- Insertar una cantidad negativa directamente debe fallar.
- Insertar dos saldos iniciales para el mismo tenant, material y periodo debe fallar.
- Insertar dos órdenes con la misma clave debe fallar.

## Decisiones confirmadas y riesgos
- **Catálogo habilitado sobre catálogo compartido:** confirmado. Se evita duplicar códigos y descripciones.
- **Dependencia de la spec 004:** confirmada. El módulo referencia `Recojo` y `RecojoLinea`; no los modifica.
- **Frecuencia diaria, semanal o mensual:** confirmada como forma de consulta. El reporte siempre es mensual y no se guarda como atributo obligatorio.
- **Saldo inicial manual:** confirmado. Prevalece sobre la herencia automática y queda auditado.
- **Saldo final negativo:** confirmado. Se muestra con alerta y no bloquea el registro.
- **Número de orden:** confirmado de 1 a 30 caracteres alfanuméricos, sin espacios internos.
- **Rendimiento:** el cálculo del saldo inicial puede requerir recorrer meses anteriores. Para el volumen previsto, se resuelve con consultas agregadas e índices por tenant, material y periodo. Si crece, se puede agregar una tabla de saldos mensuales calculados.
