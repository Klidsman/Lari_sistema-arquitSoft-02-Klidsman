# Plan técnico: 012 Reportes Mensuales

## Referencias
- Spec: `05-especificaciones/012-reportes-mensuales/spec.md`
- Reglas: `03-reglas-de-dominio/auditoria.md`
- ADR: ADR-013 (Excel)
- Stack: Django LTS, PostgreSQL, openpyxl y pytest, según la sección final de la constitución.

## Módulos afectados
- App Django nueva `reportes`: modelo `CorteMensual`, servicios, formularios y vistas.
- App `auditoria`: consulta de `RegistroCambio` para reportes de auditoría.
- App `conciliaciones`: consulta de `Conciliacion` para reportes de conciliación.
- App `stock`: consulta de `StockTecnico` y `StockGeneral` para cálculos de totales.
- Middleware de contexto de tenant de la spec 001.
- No se modifican recojos, asignaciones, traspasos ni conciliaciones.

## Modelo de datos

```python
class CorteMensual(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="cortes_mensuales",
        null=True,
        blank=True,
    )
    mes = models.IntegerField()
    anio = models.IntegerField()
    solicitados = models.IntegerField(default=0)
    asignados = models.IntegerField(default=0)
    liquidados_instalados = models.IntegerField(default=0)
    devueltos = models.IntegerField(default=0)
    no_justificado = models.IntegerField(default=0)
    porcentaje_merma = models.DecimalField(max_digits=5, decimal_places=2)
    generado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cortes_mensuales_generados",
    )
    generado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "mes", "anio"],
                name="corte_mensual_tenant_mes_anio_unico",
            ),
            models.CheckConstraint(
                condition=Q(mes__gte=1) & Q(mes__lte=12),
                name="corte_mensual_mes_valido",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "anio", "mes"], name="corte_mensual_tenant_anio_mes"),
            models.Index(fields=["anio", "mes"], name="corte_mensual_anio_mes"),
        ]

    def __str__(self):
        if self.tenant:
            return f"Corte {self.tenant} - {self.mes}/{self.anio}"
        return f"Corte Global - {self.mes}/{self.anio}"
```

- `CorteMensual` representa un corte mensual de totales.
- `tenant` puede ser NULL para cortes globales (todos los tenants).
- `solicitados`, `asignados`, `liquidados_instalados`, `devueltos` son totales calculados.
- `no_justificado` se calcula como: `asignados - (liquidados_instalados + devueltos)`.
- `porcentaje_merma` se calcula como: `(no_justificado / asignados) * 100`.
- La restricción única asegura un corte por tenant/mes/año.

## Migraciones
- `reportes/migrations/0001_initial.py`: modelo `CorteMensual` con restricciones e índices.
- No se crean cortes por migración.
- No se modifican tablas de stock, series, asignaciones ni traspasos.

## Servicios (lógica de negocio)
Viven en `reports/services.py`, no en las vistas.

### Validación de alcance
- `validar_cuenta_admin(actor)`:
  - Verifica que `actor.rol == "ADMIN_PLATAFORMA"`.
  - Si no, lanza `PermisoDenegado`.
- `validar_cuenta_tenant_o_admin(actor, tenant)`:
  - Verifica que `actor.rol == "ADMIN_PLATAFORMA"` o (`actor.rol == "USUARIO_TENANT"` y `actor.tenant == tenant`).
  - Si no, lanza `PermisoDenegado`.

### Cálculo de totales mensuales
- `calcular_totales_mensuales(tenant, mes, anio)`:
  - Calcula el rango de fechas del mes (primer y último día).
  - Obtiene el total de materiales solicitados en el mes (de `SolicitudAsignacion` con estado CONFIRMADA).
  - Obtiene el total de materiales asignados en el mes (suma de líneas de asignaciones confirmadas).
  - Obtiene el total de materiales liquidados/instalados en el mes (series cambiadas a estado INSTALADO).
  - Obtiene el total de materiales devueltos en el mes (de `Devolucion`).
  - Calcula `no_justificado = asignados - (liquidados_instalados + devueltos)`.
  - Calcula `porcentaje_merma = (no_justificado / asignados) * 100` (si asignados > 0).
  - Devuelve diccionario con todos los totales.

### Generación de corte mensual
- `generar_corte_mensual(tenant, mes, anio, actor)`:
  - `validar_cuenta_tenant_o_admin(actor, tenant)`.
  - Verifica que no exista ya un corte para el mismo tenant/mes/año.
  - Calcula totales con `calcular_totales_mensuales`.
  - En `transaction.atomic`:
    - Crea el `CorteMensual` con los totales calculados.
    - Registra auditoría de la generación.
  - Devuelve el `CorteMensual` creado.

### Regeneración de corte mensual
- `regenerar_corte_mensual(corte, actor)`:
  - `validar_cuenta_tenant_o_admin(actor, corte.tenant)`.
  - Recalcula totales con `calcular_totales_mensuales`.
  - En `transaction.atomic`:
    - Actualiza los campos del `CorteMensual`.
    - Registra auditoría de la regeneración.
  - Devuelve el `CorteMensual` actualizado.

### Exportación de auditoría mensual
- `exportar_auditoria_mensual(tenant, mes, anio)`:
  - Calcula el rango de fechas del mes.
  - Consulta `RegistroCambio` filtrando por fecha en el rango.
  - Si `tenant` es NULL, filtra por todos los tenants.
  - Si `tenant` no es NULL, filtra solo por ese tenant.
  - Usa `openpyxl` para crear el Excel.
  - Escribe filas con: fecha, usuario, entidad, acción, valor anterior, valor nuevo.
  - Guarda el archivo en disco con nombre único.
  - Devuelve ruta del archivo.

### Exportación de conciliación mensual
- `exportar_conciliacion_mensual(tenant, mes, anio)`:
  - Calcula el rango de fechas del mes.
  - Consulta `Conciliacion` filtrando por fecha en el rango.
  - Si `tenant` es NULL, filtra por todos los tenants.
  - Si `tenant` no es NULL, filtra solo por ese tenant.
  - Usa `openpyxl` para crear el Excel.
  - Escribe filas con: fecha, estado, diferencias series, diferencias cantidades, ajustes aplicados.
  - Guarda el archivo en disco con nombre único.
  - Devuelve ruta del archivo.

### Consultas
- `listar_cortes_mensuales(tenant=None, anio=None)`:
  - Si `tenant` es NULL, muestra cortes globales.
  - Si `tenant` no es NULL, filtra por tenant.
  - Opcionalmente filtra por año.
  - Ordena por `anio`, `mes` descendente.
  - Devuelve un queryset paginado.
- `obtener_corte_mensual(tenant, mes, anio)`:
  - Busca el corte filtrando por tenant, mes y año.
  - Si no existe, lanza `NoEncontrado`.

## Permisos
- Generar corte: `reports.add_cortemensual`.
- Ver corte: `reports.view_cortemensual`.
- Regenerar corte: `reports.regenerar_cortemensual`.
- Exportar auditoría: `reports.exportar_auditoria`.
- Exportar conciliación: `reports.exportar_conciliacion`.
- Generar, regenerar y exportar globales se asignan solo a `ADMIN_PLATAFORMA`.
- Generar, regenerar y exportar por tenant se asignan a `ADMIN_PLATAFORMA` y `USUARIO_TENANT`.
- Los servicios vuelven a validar rol y tenant; nunca se confía solo en la vista.
- No se acepta `tenant_id` desde formularios, URLs o archivos.
- Se recomienda RLS en PostgreSQL como respaldo del filtrado por tenant.

## Interfaz y endpoints

| Ruta | Método | Función |
|---|---|---|
| `/reportes/cortes-mensuales/` | GET | Listado de cortes mensuales |
| `/reportes/cortes-mensuales/generar/` | POST | Generar corte mensual |
| `/reportes/cortes-mensuales/<id>/` | GET | Detalle del corte |
| `/reportes/cortes-mensuales/<id>/regenerar/` | POST | Regenerar corte mensual |
| `/reportes/cortes-mensuales/<id>/exportar-auditoria/` | POST | Exportar auditoría mensual a Excel |
| `/reportes/cortes-mensuales/<id>/exportar-conciliacion/` | POST | Exportar conciliación mensual a Excel |

### Pantallas
- **Listado de cortes:**
  - Filtro por tenant (solo para admin).
  - Filtro por año.
  - Tabla con: mes/año, tenant (si aplica), solicitados, asignados, liquidados/instalados, % merma.
  - Acciones: Ver detalle, Generar nuevo, Regenerar, Exportar.
- **Generar corte:**
  - Selector de tenant (solo para admin; tenants ven el suyo fijo).
  - Selector de mes y año.
  - Botón "Generar".
- **Detalle de corte:**
  - Datos del corte (totales, % merma).
  - Acciones: Regenerar, Exportar auditoría, Exportar conciliación.
- **Exportación:**
  - Selección de tipo de reporte (auditoría o conciliación).
  - Botón "Exportar a Excel".
  - Descarga del archivo generado.

## Integraciones
- **Auditoría (transversal):** consulta `RegistroCambio` para exportar auditoría.
- **Conciliaciones (spec 010):** consulta `Conciliacion` para exportar conciliación.
- **Stock (spec 008):** consulta `StockTecnico` y `StockGeneral` para cálculos de totales.
- **Asignaciones (spec 006):** consulta `SolicitudAsignacion` para cálculo de solicitados.
- **Series (transversal):** consulta estado INSTALADO para cálculo de liquidados/instalados.
- **Logística inversa (spec 011):** consulta `Devolucion` para cálculo de devueltos.

## Validaciones (dónde vive cada una)

| Regla | Dónde se valida | Mensaje |
|---|---|---|
| Admin para cortes globales | Servicio y decorador | "Solo el administrador puede generar cortes globales" |
| Tenant o admin para cortes por tenant | Servicio y decorador | "No tienes permiso para este corte" |
| Corte único por mes/año | Servicio y `UniqueConstraint` | "Ya existe un corte para este mes/año" |
| Mes válido (1-12) | `CheckConstraint` | Violación de restricción de base de datos |

## Transacciones y concurrencia
- La generación del corte se ejecuta en una sola transacción.
- La regeneración del corte se ejecuta en una sola transacción.
- La exportación a Excel no es transaccional (solo lectura).
- Si dos usuarios intentan generar el mismo corte simultáneamente:
  - La primera en validar pasa.
  - La segunda detecta que ya existe y falla.
- No se usan bloqueos de aplicación; la restricción única resuelve conflictos.

## Pruebas
Un caso por criterio de aceptación. Nombres propuestos:

- `test_corte_mensual_con_totales`
- `test_calculo_merma_correcto`
- `test_exportar_auditoria_excel`
- `test_exportar_conciliacion_excel`
- `test_corte_unico_por_mes_anio`
- `test_regenerar_corte_actualiza_totales`
- `test_corte_global_sin_tenant`
- `test_admin_puede_generar_cortes_globales`
- `test_tenant_puede_generar_corte_propio`

Además, pruebas de cálculo:
- Dado 100 asignados, 80 liquidados, 5 devueltos, merma = 15%.
- Dado 0 asignados, merma = 0% (no división por cero).

## Decisiones y riesgos
- **Corte puede ser global o por tenant:** permite al admin ver totales globales y al tenant ver sus propios totales. El campo `tenant` nullable permite esto.
- **Cálculo de merma:** la fórmula asume que todo lo no justificado es merma. Si el negocio requiere otra fórmula, se puede ajustar.
- **Regeneración de corte:** permite recalcular si hubo errores o cambios posteriores. Esto es útil pero requiere cuidado para no perder datos históricos.
- **Exportación a demanda:** los reportes se generan a demanda, no se almacenan. Esto simplifica el sistema pero puede ser lento si se exportan muchos reportes.
- **Optimización de cálculos:** los cálculos de totales pueden ser lentos con muchos datos. Se recomienda usar agregaciones de base de datos para rendimiento.
- **Auditoría compartida:** se usa `RegistroCambio` para evitar un sistema de auditoría por módulo.
- **Riesgo de corte incorrecto:** si el cálculo tiene errores, la merma será incorrecta. Las pruebas deben validar los cálculos exhaustivamente.
