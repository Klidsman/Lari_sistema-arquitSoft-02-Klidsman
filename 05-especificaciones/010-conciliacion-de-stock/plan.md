# Plan técnico: 010 Conciliación de Stock

## Referencias
- Spec: `05-especificaciones/010-conciliacion-de-stock/spec.md`
- Contrato: `04-contratos/excel-conciliacion.md`
- Reglas: `03-reglas-de-dominio/stock.md`, `series.md`, `auditoria.md`
- ADR: ADR-012 (conciliación), ADR-013 (Excel)
- Stack: Django LTS, PostgreSQL, HTMX, openpyxl y pytest, según la sección final de la constitución.

## Módulos afectados
- App Django nueva `conciliaciones`: modelo `Conciliacion`, `DiferenciaSerie`, `DiferenciaCantidad`, servicios, formularios y vistas.
- App `stock`: actualización de stock al aprobar (usando funciones de spec 008).
- App `series`: creación de series y cambio de estado (Instalado).
- App `materiales`: validación de existencia en catálogo.
- App `tecnicos`: validación de pertenencia al tenant.
- App `auditoria`: modelo `RegistroCambio`, compartido.
- Middleware de contexto de tenant de la spec 001.
- No se modifican recojos, asignaciones ni traspasos.

## Modelo de datos

```python
class Conciliacion(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="conciliaciones",
    )
    region = models.ForeignKey(
        "regiones.Region",
        on_delete=models.PROTECT,
        related_name="conciliaciones",
    )
    fecha_carga = models.DateTimeField(auto_now_add=True)
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(
        max_length=20,
        choices=[
            ("EN_REVISION", "En revisión"),
            ("APROBADA", "Aprobada"),
            ("RECHAZADA", "Rechazada"),
        ],
        default="EN_REVISION",
    )
    archivo = models.CharField(max_length=255)
    hash_sha256 = models.CharField(max_length=64, null=True, blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="conciliaciones_creadas",
    )
    aprobado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="conciliaciones_aprobadas",
    )

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "estado"], name="conciliacion_tenant_estado"),
            models.Index(fields=["region", "fecha_carga"], name="conciliacion_region_fecha"),
        ]

    def __str__(self):
        return f"Conciliacion {self.id} - {self.tenant} - {self.estado}"


class DiferenciaSerie(models.Model):
    conciliacion = models.ForeignKey(
        "Conciliacion",
        on_delete=models.CASCADE,
        related_name="diferencias_series",
    )
    tecnico = models.ForeignKey(
        "tecnicos.Tecnico",
        on_delete=models.PROTECT,
        related_name="diferencias_series",
    )
    material = models.ForeignKey(
        "materiales.Material",
        on_delete=models.PROTECT,
        related_name="diferencias_series",
    )
    serie = models.CharField(max_length=12)
    tipo = models.CharField(
        max_length=20,
        choices=[
            ("EN_REPORTE_NO_SISTEMA", "En reporte, no en sistema"),
            ("EN_SISTEMA_NO_REPORTE", "En sistema, no en reporte"),
        ],
    )

    class Meta:
        indexes = [
            models.Index(fields=["conciliacion", "tipo"], name="dif_serie_conciliacion_tipo"),
            models.Index(fields=["serie"], name="dif_serie_serie"),
        ]

    def __str__(self):
        return f"{self.serie} - {self.tipo}"


class DiferenciaCantidad(models.Model):
    conciliacion = models.ForeignKey(
        "Conciliacion",
        on_delete=models.CASCADE,
        related_name="diferencias_cantidades",
    )
    tecnico = models.ForeignKey(
        "tecnicos.Tecnico",
        on_delete=models.PROTECT,
        related_name="diferencias_cantidades",
    )
    material = models.ForeignKey(
        "materiales.Material",
        on_delete=models.PROTECT,
        related_name="diferencias_cantidades",
    )
    cantidad_sistema = models.IntegerField()
    cantidad_reporte = models.IntegerField()
    diferencia = models.IntegerField()

    class Meta:
        indexes = [
            models.Index(fields=["conciliacion", "tecnico"], name="dif_cantidad_conciliacion_tecnico"),
        ]

    def __str__(self):
        return f"{self.tecnico.nif} - {self.material.codigo} - {self.diferencia}"
```

- `Conciliacion` representa una conciliación con el reporte de Lari.
- `DiferenciaSerie` registra series que están en el reporte pero no en el sistema, o viceversa.
- `DiferenciaCantidad` registra diferencias de cantidad para materiales no seriados.
- Los índices optimizan las consultas por tenant, región y tipo de diferencia.

## Migraciones
- `conciliaciones/migrations/0001_initial.py`: modelos `Conciliacion`, `DiferenciaSerie`, `DiferenciaCantidad` con índices.
- No se crean conciliaciones por migración.
- No se modifican tablas de stock, series, asignaciones ni traspasos.

## Servicios (lógica de negocio)
Viven en `conciliaciones/services.py`, no en las vistas.

### Validación de alcance
- `validar_cuenta_tenant(actor, tenant)`:
  - Verifica que `actor.rol == "USUARIO_TENANT"`.
  - Verifica que `actor.tenant_id == tenant.id`.
  - Verifica que la cuenta esté activa y que el tenant esté activo.
  - Si no cumple, lanza `PermisoDenegado`.
- `validar_puede_cargar_reporte(tenant)`:
  - Verifica que no haya una conciliación en estado "EN_REVISION" para el tenant.
  - Si hay una, lanza `ConciliacionEnRevision`.

### Lectura y procesamiento del Excel
- `leer_excel_conciliacion(archivo)`:
  - Usa `openpyxl` para leer el archivo Excel.
  - Lee la hoja "GENERAL".
  - Extrae las columnas: Material, Lote, Libre utilización, Número de serie, Nº ident.fis.1, Texto breve material.
  - Devuelve una lista de diccionarios con los datos de cada fila.
  - Si el formato es inválido, lanza `FormatoExcelInvalido`.

### Validación del reporte
- `validar_reporte(tenant, filas)`:
  - Valida que todos los técnicos del reporte pertenezcan al tenant.
  - Valida que todos los técnicos pertenezcan a la región del tenant.
  - Si hay técnicos no pertenecientes, lanza `TecnicosNoPertenecen`.
  - Valida que todos los materiales existan en el catálogo.
  - Si hay materiales no existentes, lanza `MaterialesNoExistentes`.

### Filtrado por tenant
- `filtrar_filas_por_tenant(tenant, filas)`:
  - Filtra las filas donde el técnico (Nº ident.fis.1) pertenece al tenant.
  - Las filas con técnicos de otros tenants se ignoran silenciosamente.
  - Devuelve la lista filtrada.

### Comparación de series
- `comparar_series(tenant, filas_reporte)`:
  - Obtiene todas las series Asignadas del tenant.
  - Extrae las series del reporte.
  - Calcula:
    - `en_reporte_no_sistema`: series en reporte que no están en el sistema
    - `en_sistema_no_reporte`: series en sistema que no están en el reporte
  - Devuelve dos listas de series.

### Comparación de cantidades
- `comparar_cantidades(tenant, filas_reporte)`:
  - Agrupa por técnico y material en el reporte.
  - Obtiene el stock del sistema por técnico y material.
  - Calcula la diferencia: `reporte - sistema`.
  - Devuelve una lista de diferencias (técnico, material, sistema, reporte, diferencia).

### Creación de conciliación
- `crear_conciliacion(tenant, archivo, actor)`:
  - `validar_cuenta_tenant(actor, tenant)`.
  - `validar_puede_cargar_reporte(tenant)`.
  - Lee el Excel con `leer_excel_conciliacion`.
  - Valida el reporte con `validar_reporte`.
  - Filtra filas por tenant con `filtrar_filas_por_tenant`.
  - Compara series con `comparar_series`.
  - Compara cantidades con `comparar_cantidades`.
  - Calcula el hash SHA-256 del archivo.
  - En `transaction.atomic`:
    - Crea la `Conciliacion` en estado "EN_REVISION".
    - Crea cada `DiferenciaSerie`.
    - Crea cada `DiferenciaCantidad`.
    - Guarda el archivo en disco.
    - Registra auditoría de la carga.
  - Devuelve la `Conciliacion` creada.

### Recálculo de diferencias
- `recalcular_diferencias(conciliacion)`:
  - Verifica que `conciliacion.estado == "EN_REVISION"`.
  - Borra las diferencias existentes.
  - Vuelve a leer el archivo guardado.
  - Vuelve a filtrar, comparar series y comparar cantidades.
  - Crea las nuevas diferencias.
  - Registra auditoría del recálculo.
  - Devuelve la `Conciliacion` actualizada.

### Aprobación de conciliación
- `aprobar_conciliacion(conciliacion, actor)`:
  - `validar_cuenta_tenant(actor, conciliacion.tenant)`.
  - Verifica que `conciliacion.estado == "EN_REVISION"`.
  - Verifica que no haya materiales del reporte que no existen en el catálogo.
  - Recalcula diferencias con `recalcular_diferencias`.
  - Si hubo cambios, exige revisión de nuevo (lanza `HuboCambios`).
  - En `transaction.atomic`:
    - Cambia estado a "APROBADA".
    - Para diferencias de tipo "en_reporte_no_sistema":
      - Crea la serie con tenant y región.
      - Asigna la serie al técnico.
      - Incrementa stock del técnico.
    - Para diferencias de tipo "en_sistema_no_reporte":
      - Marca la serie como Instalada (o retira del técnico).
      - Decrementa stock del técnico.
    - Para diferencias de cantidad:
      - Actualiza stock del técnico a la cantidad reportada (usando `actualizar_stock_tecnico` de spec 008).
    - Registra auditoría de cada ajuste (valor anterior, valor nuevo).
    - Registra auditoría de la aprobación.
  - Devuelve la `Conciliacion` actualizada.

### Rechazo de conciliación
- `rechazar_conciliacion(conciliacion, actor)`:
  - `validar_cuenta_tenant(actor, conciliacion.tenant)`.
  - Verifica que `conciliacion.estado == "EN_REVISION"`.
  - En `transaction.atomic`:
    - Cambia estado a "RECHAZADA".
    - No se modifican series ni stock.
    - Registra auditoría del rechazo.
  - Devuelve la `Conciliacion` actualizada.

### Consultas
- `obtener_conciliacion_en_revision(tenant)`:
  - Devuelve la conciliación en estado "EN_REVISION" del tenant.
  - Si no existe, lanza `NoEncontrado`.
- `listar_conciliaciones(tenant, estado=None)`:
  - Filtra siempre por `tenant`.
  - Opcionalmente filtra por estado.
  - Ordena por `fecha_carga` descendente.
  - Devuelve un queryset paginado.

## Permisos
- Cargar: `conciliaciones.add_conciliacion`.
- Ver: `conciliaciones.view_conciliacion`.
- Aprobar: `conciliaciones.aprobar_conciliacion`.
- Rechazar: `conciliaciones.rechazar_conciliacion`.
- Todos se asignan al rol `USUARIO_TENANT`.
- Los servicios vuelven a validar rol, tenant y estado; nunca se confía solo en la vista.
- No se acepta `tenant_id` desde formularios, URLs o archivos.
- Se recomienda RLS en PostgreSQL como respaldo del filtrado por tenant.

## Interfaz y endpoints

| Ruta | Método | Función |
|---|---|---|
| `/conciliaciones/` | GET | Listado paginado con filtro por estado |
| `/conciliaciones/cargar/` | POST | Carga del reporte de Lari |
| `/conciliaciones/<id>/` | GET | Detalle de la conciliación |
| `/conciliaciones/<id>/aprobar/` | POST | Aprobar conciliación |
| `/conciliaciones/<id>/rechazar/` | POST | Rechazar conciliación |
| `/conciliaciones/<id>/recalcular/` | POST | Recalcular diferencias |

### Pantallas
- **Listado:** Fecha, estado, archivo, total diferencias series, total diferencias cantidades. Filtro por estado.
- **Carga:**
  - Formulario para subir archivo Excel.
  - Validación del formato.
  - Vista previa de errores si los hay.
  - Botón "Cargar" que crea la conciliación.
- **Detalle:**
  - Datos de la conciliación (fecha, estado, archivo).
  - Sección de diferencias de series:
    - Grupo "En reporte, no en sistema" (material ajeno).
    - Grupo "En sistema, no en reporte" (series faltantes).
  - Sección de diferencias de cantidades.
  - Alertas categorizadas de discrepancias.
  - Aviso si hubo cambios desde la carga.
  - Acciones: Aprobar, Rechazar, Recalcular.
- **Aprobación:**
  - Resumen de ajustes que se aplicarán.
  - Confirmación del usuario.
  - Si hubo cambios, se exige revisar de nuevo.

## Integraciones
- **Stock (spec 008):** usa funciones de actualización de stock técnico.
- **Series (transversal):** crea series y cambia estado a Instalado.
- **Catálogo de materiales (spec 002):** valida existencia de materiales.
- **Técnicos (spec 003):** valida pertenencia al tenant.
- **Contrato:** usa el formato definido en `04-contratos/excel-conciliacion.md`.
- **Auditoría (transversal):** usa `RegistroCambio` compartido.

## Validaciones (dónde vive cada una)

| Regla | Dónde se valida | Mensaje |
|---|---|---|
| Tenant de la sesión | Servicio y decorador | "No tienes permiso para cargar conciliaciones" |
| Solo una en revisión | Servicio | "Ya hay una conciliación en revisión" |
| Técnicos pertenecen al tenant | Servicio | "El reporte contiene técnicos que no pertenecen al tenant" |
| Materiales existen en catálogo | Servicio | "El reporte contiene materiales que no existen en el catálogo" |
| Aprobación bloquea si material no existe | Servicio | "Aprobación bloqueada: materiales no existen en catálogo" |
| Aprobación es todo o nada | Servicio y transacción | Si falla, se revierte todo |
| Recálculo si hubo cambios | Servicio | "Hubo cambios, revise de nuevo" |

## Transacciones y concurrencia
- La creación de la conciliación y sus diferencias se ejecutan en una sola transacción.
- La aprobación de la conciliación, la creación de series, el cambio de estado y la actualización de stock se ejecutan en una sola transacción.
- La validación se ejecuta antes de la transacción para fallar rápido.
- Si dos sesiones intentan cargar reportes simultáneamente:
  - La primera en validar crea la conciliación.
  - La segunda detecta que ya hay una en revisión y falla.
- No se usan bloqueos de aplicación; el estado de conciliación es la fuente de verdad.

## Pruebas
Un caso por criterio de aceptación. Nombres propuestos:

- `test_cargar_reporte_crea_conciliacion_en_revision`
- `test_solo_una_conciliacion_en_revision`
- `test_tecnico_ausente_se_ignora`
- `test_material_ausente_se_asume_0`
- `test_diferencias_series_se_muestran_dos_grupos`
- `test_alertas_categorizadas`
- `test_aprobacion_bloquea_si_material_no_existe`
- `test_aprobacion_todo_o_nada`
- `test_ajustos_al_aprobar`
- `test_auditoria_ajustes`
- `test_recalculo_si_hubo_cambios`
- `test_tecnico_no_pertenece_rechaza_archivo`

Además, pruebas de lectura de Excel:
- Leer Excel con formato incorrecto debe fallar.
- Leer Excel sin hoja GENERAL debe fallar.

## Decisiones y riesgos
- **Solo una en revisión:** simplifica el flujo pero puede ser restrictivo. Si el negocio requiere múltiples conciliaciones simultáneas, se puede cambiar.
- **Recálculo obligatorio si hubo cambios:** protege contra aprobaciones con datos desactualizados. Puede ser frustrante si el usuario no hizo cambios, pero es más seguro.
- **Regla de ausencia de técnicos:** ignorar técnicos ausentes puede ocultar problemas. Se asume que es correcto según el negocio.
- **Creación de series al aprobar:** las series del reporte que no existen se crean. Esto es necesario pero requiere validar que las series sean válidas.
- **Estado Instalado para series faltantes:** alternativas: retirar del técnico o borrar. Marcar como Instalado parece más apropiado para trazabilidad.
- **Auditoría compartida:** se usa `RegistroCambio` para evitar un sistema de auditoría por módulo.
- **Riesgo de grandes volúmenes:** el reporte puede tener miles de filas. La comparación debe ser eficiente (índices, batch processing).
- **Riesgo de materiales no existentes:** bloquea la aprobación pero no la carga. Esto permite al usuario corregir el catálogo antes de aprobar.
