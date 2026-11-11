# Plan técnico: 011 Logística Inversa y Devoluciones

## Referencias
- Spec: `05-especificaciones/011-logistica-inversa-y-devoluciones/spec.md`
- Reglas: `03-reglas-de-dominio/stock.md`, `series.md`, `auditoria.md`
- ADR: ADR-012 (conciliación), ADR-013 (Excel)
- Stack: Django LTS, PostgreSQL, HTMX, openpyxl y pytest, según la sección final de la constitución.

## Módulos afectados
- App Django nueva `logistica_inversa`: modelo `Devolucion`, `BajaEquipo`, servicios, formularios y vistas.
- App `stock`: actualización de stock (usando funciones de spec 008).
- App `series`: cambio de estado de series (Asignada → Disponible para devolución, Asignada → Inactivo para baja).
- App `tecnicos`: selector de técnicos.
- App `auditoria`: modelo `RegistroCambio`, compartido.
- Middleware de contexto de tenant de la spec 001.
- No se modifican recojos, asignaciones, traspasos ni conciliaciones.

## Modelo de datos

```python
class Devolucion(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="devoluciones",
    )
    tecnico = models.ForeignKey(
        "tecnicos.Tecnico",
        on_delete=models.PROTECT,
        related_name="devoluciones",
    )
    fecha = models.DateField()
    observaciones = models.TextField(null=True, blank=True)
    acta_ruta = models.CharField(max_length=255, null=True, blank=True)
    acta_hash = models.CharField(max_length=64, null=True, blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="devoluciones_creadas",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "fecha"], name="devolucion_tenant_fecha"),
            models.Index(fields=["tecnico", "fecha"], name="devolucion_tecnico_fecha"),
        ]

    def __str__(self):
        return f"Devolucion {self.id} - {self.tecnico.nif} - {self.fecha}"


class LineaDevolucion(models.Model):
    devolucion = models.ForeignKey(
        "Devolucion",
        on_delete=models.CASCADE,
        related_name="lineas",
    )
    serie = models.CharField(max_length=12)
    material = models.ForeignKey(
        "materiales.Material",
        on_delete=models.PROTECT,
        related_name="lineas_devolucion",
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(serie__regex=r"^[A-Z0-9]{12}$"),
                name="linea_devolucion_serie_formato",
            ),
        ]
        indexes = [
            models.Index(fields=["devolucion", "serie"], name="linea_devolucion_devolucion_serie"),
            models.Index(fields=["serie"], name="linea_devolucion_serie"),
        ]

    def __str__(self):
        return f"{self.serie}"


class BajaEquipo(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="bajas_equipos",
    )
    serie = models.CharField(max_length=12, unique=True)
    causa = models.CharField(
        max_length=20,
        choices=[
            ("AVERIA", "Avería"),
            ("MIGRACION", "Migración"),
            ("OTRO", "Otro"),
        ],
    )
    observaciones = models.TextField(null=True, blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="bajas_equipos_creadas",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "causa"], name="baja_equipo_tenant_causa"),
            models.Index(fields=["serie"], name="baja_equipo_serie"),
        ]

    def __str__(self):
        return f"Baja {self.serie} - {self.causa}"
```

- `Devolucion` representa una devolución de equipos por un técnico.
- `LineaDevolucion` representa cada serie devuelta.
- `BajaEquipo` representa un equipo recuperado o dado de baja.
- La restricción única en `BajaEquipo.serie` asegura que una serie solo se da de baja una vez.

## Migraciones
- `logistica_inversa/migrations/0001_initial.py`: modelos `Devolucion`, `LineaDevolucion`, `BajaEquipo` con restricciones e índices.
- No se crean devoluciones o bajas por migración.
- No se modifican tablas de stock, series, asignaciones ni traspasos.

## Servicios (lógica de negocio)
Viven en `logistica_inversa/services.py`, no en las vistas.

### Validación de alcance
- `validar_cuenta_tenant(actor, tenant)`:
  - Verifica que `actor.rol == "USUARIO_TENANT"`.
  - Verifica que `actor.tenant_id == tenant.id`.
  - Verifica que la cuenta esté activa y que el tenant esté activo.
  - Si no cumple, lanza `PermisoDenegado`.

### Validación de series
- `validar_serie_en_tecnico(serie, tecnico)`:
  - Verifica que la serie esté asignada al técnico.
  - Si no, lanza `SerieNoEnTecnico`.
- `validar_serie_no_dada_de_baja(serie)`:
  - Verifica que la serie no esté dada de baja.
  - Si está dada de baja, lanza `SerieYaDadaDeBaja`.

### Registro de devolución
- `registrar_devolucion(tenant, tecnico, series, observaciones, actor)`:
  - `validar_cuenta_tenant(actor, tenant)`.
  - Para cada serie:
    - `validar_serie_en_tecnico(serie, tecnico)`.
    - `validar_serie_no_dada_de_baja(serie)`.
  - En `transaction.atomic`:
    - Crea la `Devolucion`.
    - Crea cada `LineaDevolucion`.
    - Para cada serie:
      - Cambia estado de serie a DISPONIBLE.
      - Decrementa stock del técnico (usando `decrementar_stock_tecnico` de spec 008).
      - Incrementa stock general (usando `incrementar_stock_general` de spec 008).
      - Registra auditoría del cambio de estado.
      - Registra auditoría del cambio de stock técnico.
      - Registra auditoría del cambio de stock general.
    - Registra auditoría de la devolución.
  - Devuelve la `Devolucion` creada.

### Registro de baja
- `registrar_baja_equipo(tenant, serie, causa, observaciones, actor)`:
  - `validar_cuenta_tenant(actor, tenant)`.
  - `validar_serie_no_dada_de_baja(serie)`.
  - En `transaction.atomic`:
    - Crea la `BajaEquipo`.
    - Cambia estado de serie a INACTIVO (o estado específico de baja).
    - Si la serie está en stock de un técnico:
      - Decrementa stock del técnico.
      - Decrementa stock general.
    - Registra auditoría del cambio de estado.
    - Registra auditoría de la baja.
  - Devuelve la `BajaEquipo` creada.

### Generación de acta
- `generar_acta_devolucion(devolucion)`:
  - Usa `openpyxl` para crear el Excel del acta.
  - Escribe metadatos: tenant, técnico, fecha de devolución.
  - Escribe tabla de series devueltas.
  - Guarda el archivo en disco con nombre único.
  - Calcula el hash SHA-256 del archivo.
  - Actualiza `devolucion.acta_ruta` y `devolucion.acta_hash`.
  - Devuelve ruta y hash.

### Consultas
- `listar_devoluciones(tenant, fecha_desde=None, fecha_hasta=None)`:
  - Filtra siempre por `tenant`.
  - Opcionalmente filtra por rango de fechas.
  - Ordena por `fecha` descendente.
  - Devuelve un queryset paginado.
- `listar_bajas(tenant, causa=None)`:
  - Filtra siempre por `tenant`.
  - Opcionalmente filtra por causa.
  - Ordena por `creado_en` descendente.
  - Devuelve un queryset paginado.

## Permisos
- Registrar devolución: `logistica_inversa.add_devolucion`.
- Registrar baja: `logistica_inversa.add_bajaequipo`.
- Ver: `logistica_inversa.view_devolucion`, `logistica_inversa.view_bajaequipo`.
- Generar acta: `logistica_inversa.generar_acta`.
- Todos se asignan al rol `USUARIO_TENANT`.
- Los servicios vuelven a validar rol y tenant; nunca se confía solo en la vista.
- No se acepta `tenant_id` o técnicos desde formularios, URLs o archivos.
- Se recomienda RLS en PostgreSQL como respaldo del filtrado por tenant.

## Interfaz y endpoints

| Ruta | Método | Función |
|---|---|---|
| `/logistica-inversa/devoluciones/` | GET | Listado de devoluciones |
| `/logistica-inversa/devoluciones/nueva/` | GET / POST | Registro de devolución |
| `/logistica-inversa/devoluciones/<id>/` | GET | Detalle de devolución |
| `/logistica-inversa/devoluciones/<id>/generar-acta/` | POST | Generar acta de entrega |
| `/logistica-inversa/bajas/` | GET | Listado de bajas |
| `/logistica-inversa/bajas/nueva/` | GET / POST | Registro de baja |

### Pantallas
- **Listado de devoluciones:** Fecha, técnico, total series, observaciones. Filtro por rango de fechas.
- **Registro de devolución:**
  - Selector de técnico.
  - Fecha (precompletada con hoy, editable).
  - Selector de series del técnico (multi-select).
  - Observaciones (opcional).
  - Botón "Registrar".
- **Detalle de devolución:**
  - Datos de la devolución.
  - Lista de series.
  - Descarga del acta (si generada).
  - Botón "Generar acta".
- **Listado de bajas:** Serie, causa, fecha, observaciones. Filtro por causa.
- **Registro de baja:**
  - Campo de serie.
  - Selector de causa (Avería, Migración, Otro).
  - Observaciones (opcional).
  - Botón "Registrar".

## Integraciones
- **Stock (spec 008):** usa `decrementar_stock_tecnico`, `incrementar_stock_general` para devoluciones; usa decremento de ambos para bajas.
- **Series (transversal):** cambia estado de serie (Asignada → Disponible, Asignada → Inactivo).
- **Técnicos (spec 003):** selector de técnicos.
- **Auditoría (transversal):** usa `RegistroCambio` compartido.

## Validaciones (dónde vive cada una)

| Regla | Dónde se valida | Mensaje |
|---|---|---|
| Tenant de la sesión | Servicio y decorador | "No tienes permiso para registrar devoluciones" |
| Serie en técnico | Servicio | "La serie no está asignada al técnico" |
| Serie no dada de baja | Servicio | "La serie ya fue dada de baja" |
| Causa obligatoria | Formulario y servicio | "Debe indicar la causa de la baja" |

## Transacciones y concurrencia
- La devolución, el cambio de estado de series y la actualización de stock se ejecutan en una sola transacción.
- La baja, el cambio de estado de serie y la actualización de stock se ejecutan en una sola transacción.
- La validación se ejecuta antes de la transacción para fallar rápido.
- Si dos sesiones intentan dar de baja la misma serie simultáneamente:
  - La primera en validar pasa.
  - La segunda detecta que la serie ya está dada de baja y falla.
- No se usan bloqueos de aplicación; la restricción única de serie en `BajaEquipo` resuelve conflictos.

## Pruebas
Un caso por criterio de aceptación. Nombres propuestos:

- `test_devolucion_libera_custodia`
- `test_series_devueltas_pueden_reasignarse`
- `test_recuperacion_con_causa`
- `test_baja_por_migracion`
- `test_generacion_acta`
- `test_auditoria_devoluciones`
- `test_serie_no_en_tecnico_se_rechaza`
- `test_serie_ya_dada_de_baja_se_rechaza`
- `test_devolucion_actualiza_stock_correctamente`
- `test_baja_elimina_stock_disponible`

Además, pruebas de base de datos:
- Insertar una serie con formato inválido directamente debe fallar.
- Insertar dos bajas con la misma serie debe fallar.

## Decisiones y riesgos
- **Estado INACTIVO para bajas:** las series dadas de baja se marcan como INACTIVO. Alternativa: eliminarlas, pero esto pierde trazabilidad.
- **Stock general en devolución:** la devolución incrementa el stock general. Esto es correcto porque el material vuelve a estar disponible.
- **Stock general en baja:** la baja decrementa el stock general. Esto es correcto porque el material ya no está disponible.
- **Causa obligatoria:** obliga al usuario a documentar por qué se da de baja. Esto mejora la trazabilidad.
- **Acta opcional:** la devolución puede existir sin acta. El acta se genera a demanda.
- **Auditoría compartida:** se usa `RegistroCambio` para evitar un sistema de auditoría por módulo.
- **Riesgo de series no en técnico:** si la serie no está asignada al técnico, no se puede devolver. La validación previa mitiga esto.
- **Riesgo de bajas masivas:** si se dan de baja muchas series, puede afectar el stock. Se debe monitorear el stock después de bajas masivas.
