# Plan técnico: 003 Técnicos del tenant

## Referencias
- Spec: `05-especificaciones/003-tecnicos/spec.md`
- Reglas: `03-reglas-de-dominio/stock.md`, `series.md`, `registro-materiales.md`, `auditoria.md`
- ADR: ADR-003, ADR-007, ADR-019
- Stack: Django LTS, PostgreSQL, HTMX y pytest, según la sección final de la constitución.

## Módulos afectados
- App Django nueva `tecnicos`: modelo `Tecnico`, servicios, formularios, vistas y búsqueda.
- App `auditoria`: modelo `RegistroCambio`, compartido. Si no existe, se crea aquí.
- Middleware de contexto de tenant de la spec 001.
- No se modifican stock, series, asignaciones, traspasos, conciliaciones ni registro de materiales.

## Modelo de datos

```python
class Tecnico(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="tecnicos",
    )
    nif = models.CharField(max_length=10, unique=True)
    nombre = models.CharField(max_length=100)
    activo = models.BooleanField(default=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(nif__regex=r"^LA[0-9]{4}$"),
                name="tecnico_nif_formato",
            ),
            models.CheckConstraint(
                condition=~Q(nombre=""),
                name="tecnico_nombre_obligatorio",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "activo"], name="tecnico_tenant_activo"),
            models.Index(fields=["tenant", "nombre"], name="tecnico_tenant_nombre"),
        ]

    def __str__(self):
        return f"{self.nif} - {self.nombre}"
```

- `nif` es único global. Si el negocio confirma que el mismo NIF puede existir en dos tenants, se cambia a `UniqueConstraint(fields=["tenant", "nif"])`.
- `tenant` usa `PROTECT` porque un tenant no se elimina y el técnico conserva su historial.
- No se guarda `region`: se obtiene desde `tenant.region`.
- `activo` no borra datos; solo controla la disponibilidad para nuevas operaciones.
- Los índices cubren el listado y la búsqueda por tenant, estado y nombre.
- La restricción `tecnico_nif_formato` protege la base de datos aunque se salte la validación de la aplicación.
- La restricción `tecnico_nombre_obligatorio` impide nombres vacíos por inserción directa.

## Migraciones
- `tecnicos/migrations/0001_initial.py`: modelo `Tecnico` con restricciones e índices.
- No se crean técnicos por migración.
- No se modifican tablas de stock, series, asignaciones, traspasos ni conciliaciones.
- Si el proyecto ya tiene datos, la migración no transforma técnicos existentes.

## Servicios (lógica de negocio)
Viven en `tecnicos/services.py`, no en las vistas.

### Validación de alcance
- `validar_cuenta_tenant(actor, tenant)`:
  - Verifica que `actor.rol == "USUARIO_TENANT"`.
  - Verifica que `actor.tenant_id == tenant.id`.
  - Verifica que la cuenta esté activa y que el tenant esté activo.
  - Si no cumple, lanza `PermisoDenegado`.
- `obtener_tecnico(tenant, tecnico_id)`:
  - Busca el técnico filtrando por `tenant`.
  - Si no existe o pertenece a otro tenant, lanza `NoEncontrado` sin revelar su existencia.
- `validar_tecnico_para_operacion(tenant, tecnico_id)`:
  - Usa `obtener_tecnico`.
  - Exige que el tenant esté activo.
  - Exige `activo=True`.
  - Devuelve el técnico o lanza `TecnicoNoDisponible`.
  - La usan asignaciones, traspasos, conciliación y registro de materiales.

### Normalización y validación
- `normalizar_nif(nif)`:
  - Elimina espacios al inicio y al final.
  - Convierte a mayúsculas.
  - No elimina guiones ni espacios internos: el formato estricto los rechaza.
- `validar_nif(nif)`:
  - Debe cumplir `^LA[0-9]{4}$`.
  - Si no, lanza `NifInvalido` con “El NIF debe tener el formato LAXXXX”.
- `normalizar_nombre(nombre)`:
  - Elimina espacios al inicio y al final.
  - Colapsa espacios internos repetidos.
- `validar_nombre(nombre)`:
  - No vacío.
  - Máximo 100 caracteres.
  - Si no, lanza `NombreInvalido`.

### Alta
- `crear_tecnico(tenant, datos, actor)`:
  - `validar_cuenta_tenant(actor, tenant)`.
  - Normaliza y valida NIF y nombre.
  - Verifica que el NIF no exista en todo el sistema.
  - En `transaction.atomic`, crea el técnico activo y registra la auditoría de alta.
  - Si la base de datos rechaza el NIF duplicado (`IntegrityError`), devuelve “El NIF ya está registrado”.
  - No acepta `tenant_id` desde el formulario: el tenant viene del argumento y de la sesión.

### Edición
- `actualizar_tecnico(tecnico, cambios, actor)`:
  - `validar_cuenta_tenant(actor, tecnico.tenant)`.
  - Rechaza cualquier intento de cambiar `nif` o `tenant`.
  - Solo permite cambiar `nombre`.
  - Normaliza y valida el nombre.
  - En `transaction.atomic`, aplica el cambio y registra un `RegistroCambio` por campo modificado.
  - Si el nombre no cambió, no genera auditoría duplicada.

### Estado
- `desactivar_tecnico(tecnico, actor)`:
  - `validar_cuenta_tenant(actor, tecnico.tenant)`.
  - Si ya está desactivado, no hace cambios ni duplica auditoría.
  - Marca `activo=False` y audita el valor anterior y el nuevo.
  - No borra stock, series, asignaciones, traspasos, órdenes ni conciliaciones.
- `reactivar_tecnico(tecnico, actor)`:
  - `validar_cuenta_tenant(actor, tecnico.tenant)`.
  - Si ya está activo, no hace cambios ni duplica auditoría.
  - Marca `activo=True` y audita el valor anterior y el nuevo.

### Consultas
- `buscar_tecnicos(tenant, q="", solo_activos=False)`:
  - Filtra siempre por `tenant`.
  - Busca por `nif__icontains` o `nombre__icontains`.
  - Si `solo_activos=True`, filtra `activo=True`.
  - Ordena por `nombre` y `nif`.
  - Devuelve un queryset paginado.
- `tecnicos_para_operacion(tenant)`:
  - Devuelve solo técnicos activos del tenant.
  - Es la fuente de los selectores de asignación, traspaso, conciliación y registro de materiales.
- `tecnicos_para_reporte(tenant, incluir_inactivos=True)`:
  - Devuelve técnicos del tenant para reportes históricos.
  - Incluye inactivos cuando el reporte los necesite.

## Permisos
- Crear: `tecnicos.add_tecnico`.
- Ver: `tecnicos.view_tecnico`.
- Editar nombre: `tecnicos.change_tecnico`.
- Desactivar: `tecnicos.desactivar_tecnico`.
- Reactivar: `tecnicos.reactivar_tecnico`.
- Todos se asignan al rol `USUARIO_TENANT`.
- El Administrador de plataforma y el Responsable de almacén no reciben estos permisos por defecto.
- Los servicios vuelven a validar rol, tenant y estado; nunca se confía solo en la vista.
- No se acepta `tenant_id` desde formularios, URLs o archivos.
- Se recomienda RLS en PostgreSQL como respaldo del filtrado por tenant.

## Interfaz y endpoints

| Ruta | Método | Función |
|---|---|---|
| `/tecnicos/` | GET | Listado paginado con búsqueda y filtro por estado |
| `/tecnicos/buscar/?q=` | GET | Fragmento HTMX con técnicos activos para otros módulos |
| `/tecnicos/nuevo/` | GET / POST | Alta de técnico |
| `/tecnicos/<id>/` | GET | Detalle del técnico |
| `/tecnicos/<id>/editar/` | GET / POST | Edición del nombre; NIF y tenant solo lectura |
| `/tecnicos/<id>/desactivar/` | POST | Desactivar técnico |
| `/tecnicos/<id>/reactivar/` | POST | Reactivar técnico |

### Pantallas
- **Listado:** NIF, nombre, estado y acciones. Búsqueda por NIF o nombre. Filtro Activos/Desactivados/Todos.
- **Alta:** NIF y nombre. El tenant no se muestra como campo editable.
- **Edición:** NIF y tenant como solo lectura; nombre editable; estado se cambia con acciones separadas.
- **Detalle:** datos del técnico y acceso a su historial en los módulos que lo consumen.
- **Selectores de otros módulos:** solo técnicos activos; el NIF se completa solo y no es editable.

## Integraciones
- **Asignaciones (spec 006):** el selector usa `tecnicos_para_operacion` y copia el NIF al Excel.
- **Traspasos (spec 009):** origen y destino deben ser técnicos activos del mismo tenant y distintos entre sí.
- **Conciliación (spec 010):** el NIF del reporte se resuelve dentro del tenant de la sesión; un NIF desconocido se informa como advertencia, nunca se busca en otro tenant.
- **Registro de materiales (spec 013):** las órdenes usan un técnico activo del tenant en el momento del alta; las órdenes históricas conservan el técnico aunque luego se desactive.
- **Stock inicial (spec 005):** el stock inicial se asocia a un técnico existente del tenant.
- **Logística inversa (spec 011):** una devolución o baja puede referenciar un técnico desactivado para conservar la trazabilidad.
- Todas las integraciones usan la FK `Tecnico` y el tenant de la sesión. No se acepta un NIF suelto sin resolverlo contra el tenant.

## Validaciones (dónde vive cada una)

| Regla | Dónde se valida | Mensaje |
|---|---|---|
| NIF con formato `LAXXXX` | Formulario, servicio y `CheckConstraint` | “El NIF debe tener el formato LAXXXX” |
| NIF único global | Servicio y restricción única | “El NIF ya está registrado” |
| NIF inmutable | Formulario y servicio | “El NIF no se puede cambiar” |
| Nombre obligatorio | Formulario, servicio y `CheckConstraint` | “El nombre es obligatorio” |
| Nombre máximo 100 | Formulario y servicio | “El nombre no puede superar los 100 caracteres” |
| Tenant inmutable | Servicio | “El tenant del técnico no se puede cambiar” |
| Solo cuenta del tenant | Servicio y decorador | “No tienes permiso para gestionar técnicos” |
| Técnico de otro tenant | Servicio | “El técnico no existe” |
| Técnico activo para operar | Servicio de integración | “El técnico está desactivado” |
| NIF de técnico desactivado | Servicio | “El NIF ya está registrado; reactiva el técnico existente” |
| Tenant suspendido | Middleware y servicio | “El tenant está suspendido” |

## Transacciones y concurrencia
- El alta y su auditoría se ejecutan en una sola transacción.
- La edición del nombre y su auditoría se ejecutan en una sola transacción.
- La desactivación y la reactivación se ejecutan en una transacción y auditan el cambio.
- La restricción única de `nif` resuelve dos altas simultáneas con el mismo NIF.
- Si dos sesiones editan el mismo técnico, se aplica la última escritura y la auditoría conserva ambos cambios.
- No se usan bloqueos de aplicación para evitar duplicados; la base de datos es la fuente de verdad.

## Pruebas
Un caso por criterio de aceptación. Nombres propuestos:

- `test_crear_tecnico_valido_queda_activo_y_auditado`
- `test_nif_duplicado_en_el_mismo_tenant_se_rechaza`
- `test_nif_duplicado_en_otro_tenant_se_rechaza_sin_revelar_tenant`
- `test_nif_en_minusculas_o_con_espacios_externos_se_normaliza`
- `test_nif_con_formato_invalido_se_rechaza`
- `test_nombre_vacio_o_solo_espacios_se_rechaza`
- `test_nombre_de_mas_de_100_caracteres_se_rechaza`
- `test_editar_nombre_audita_valor_anterior_y_nuevo`
- `test_nif_no_se_puede_editar`
- `test_tenant_no_se_puede_cambiar`
- `test_desactivar_tecnico_lo_quita_de_selectores_activos`
- `test_tecnico_desactivado_con_historial_sigue_visible`
- `test_reactivar_tecnico_lo_habilita_y_audita`
- `test_no_se_crea_otro_tecnico_con_nif_desactivado`
- `test_busqueda_solo_devuelve_tecnicos_del_tenant`
- `test_tecnico_de_otro_tenant_se_rechaza_sin_revelar_datos`
- `test_admin_plataforma_y_almacen_no_gestionan_tecnicos`
- `test_tecnico_desactivado_en_formulario_viejo_se_rechaza`
- `test_desactivar_tecnico_con_stock_conserva_stock`
- `test_altas_simultaneas_con_mismo_nif_fallan_por_restriccion_unica`
- `test_no_se_puede_eliminar_un_tecnico`
- `test_nombre_duplicado_se_permite`

Además, pruebas de base de datos:
- Insertar un NIF con formato inválido directamente debe fallar.
- Insertar dos técnicos con el mismo NIF directamente debe fallar.
- Insertar un técnico con nombre vacío directamente debe fallar.

## Decisiones y riesgos
- **NIF único global:** se asume que Lari asigna un NIF único por técnico. Si el mismo NIF puede pertenecer a dos tenants, se cambia a único por tenant y se ajusta la spec.
- **NIF inmutable:** se protege la trazabilidad de los Excel y reportes. Una corrección de NIF se resuelve desactivando el técnico y creando uno nuevo.
- **Sin eliminación:** los técnicos no se borran; se desactivan. Esto conserva stock, asignaciones, traspasos, órdenes y conciliaciones.
- **Desactivación con stock:** se permite desactivar un técnico con stock pendiente, pero no recibe nuevas operaciones. El stock sigue visible para devolución o traspaso; las reglas concretas viven en las specs 009 y 011.
- **Cupo máximo fuera de alcance:** la alerta de cupo de equipos sin liquidar se definirá en la spec de asignación o como parámetro del tenant, no en el alta del técnico.
- **NIF de 4 dígitos:** si Lari usa otra longitud, se ajusta el regex y la restricción de base de datos.
- **Auditoría compartida:** se usa `RegistroCambio` para evitar un sistema de auditoría por módulo.
- **Búsqueda por nombre:** se indexa `tenant + nombre`; si el volumen crece, se evalúa un índice de texto completo.
- **Integraciones:** todos los módulos deben usar los servicios de este módulo para resolver el técnico; no deben consultar `Tecnico` sin filtrar por tenant.
- **Concurrencia:** la restricción única de NIF es la fuente de verdad ante dos altas simultáneas.
