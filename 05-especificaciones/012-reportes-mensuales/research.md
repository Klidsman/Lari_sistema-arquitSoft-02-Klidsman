# Investigación y decisiones: 012 Reportes Mensuales

**Fase**: 0 | **Fecha**: 2026-11-12 | **Spec**:
`05-especificaciones/012-reportes-mensuales/spec.md`

Resuelve las incógnitas del plan y fija las definiciones que no deben quedar a criterio de la
implementación. No hay `NEEDS CLARIFICATION` pendientes; las correcciones y deudas se listan al final.

## Contexto de dependencias

| Dependencia | Estado esperado | Uso en 012 |
|---|---|---|
| 001 — acceso, tenants y auditoría | Implementada | Roles, alcance, `RegistroCambio` con `tenant` |
| 002/003 — materiales y técnicos | Implementadas | Catálogo y técnicos por tenant |
| 004/010/011 — series | Implementadas | `INSTALADA` (liquidados) e `INACTIVA` (bajas) |
| 006/007/008 — asignaciones | Implementadas | `SolicitudAsignacion`, `LineaAsignacion`, `confirmada_en` |
| 009 — traspasos | Implementada | Datos auditados; no se usa para el corte |
| 010 — conciliación | Implementada | `Conciliacion` y `ajustes_aplicados` |
| 011 — logística inversa | Implementada | `Devolucion`/`LineaDevolucion` |
| PostgreSQL 16+ | Infraestructura | Agregaciones, índices, restricciones y RLS |

## Decisiones

### D-01. Definición de solicitados y asignados

- **Decisión**:
  - **Solicitados**: unidades de `LineaAsignacion` de solicitudes con `fecha` en el mes y estado
    `ENVIADA`, `CONFIRMADA` o `RECHAZADA`. Cada serie suma 1; cada no seriado suma su `cantidad`.
  - **Asignados**: unidades de `LineaAsignacion` de solicitudes `CONFIRMADA` con `confirmada_en` en
    el mes, con la misma regla.
- **Justificación**: “solicitado” es lo que el tenant pidió (aunque se rechace); “asignado” es lo que
  el almacén confirmó en el mes. Si ambos usaran solo confirmadas, serían el mismo número. Se excluyen
  `BORRADOR` y `CANCELADA` porque no llegaron a pedirse al almacén.
- **Alternativas descartadas**: contar todas las solicitudes (incluye borradores no enviados); contar
  solo confirmadas para ambos (métrica duplicada).

### D-02. Merma y no justificado

- **Decisión**: `no_justificado = max(0, asignados - liquidados_instalados - devueltos)` y
  `porcentaje_merma = 0` si `asignados=0`; si no, `round(no_justificado / asignados * 100, 2)`.
- **Justificación**: la fórmula de la spec puede dar negativo cuando se instalan o devuelven equipos
  asignados en meses anteriores. Una merma negativa no tiene sentido operativo; se acota a 0 y se
  documenta.
- **Alternativas descartadas**: permitir merma negativa (confunde); recalcular asignados históricos
  (complejo y fuera de spec).

### D-03. Corte persistido, exportaciones a demanda

- **Decisión**: `CorteMensual` se guarda para consulta histórica y auditoría. Las exportaciones de
  auditoría y conciliación se generan en memoria y se descargan; no se persisten archivos.
- **Justificación**: el corte es un dato estable y consultable; los Excel son vistas del mes y
  persistirlos crearía archivos huérfanos y duplicaría datos.
- **Alternativas descartadas**: calcular todo al vuelo (no hay histórico); guardar cada Excel (más
  almacenamiento y limpieza).

### D-04. Global con `tenant=None` y restricciones parciales

- **Decisión**: dos `UniqueConstraint` parciales: `(tenant, anio, mes)` cuando `tenant` no es nulo y
  `(anio, mes)` cuando es nulo.
- **Justificación**: en PostgreSQL los NULL no colisionan en un `unique`; sin la restricción parcial
  se podrían crear varios cortes globales del mismo mes.
- **Alternativas descartadas**: un campo `alcance` con valor “GLOBAL” (más estado); validar solo en el
  servicio (dos generaciones simultáneas podrían pasar).

### D-05. `RegistroCambio.tenant`

- **Decisión**: añadir `tenant` nullable a `RegistroCambio`, poblado por `registrar_cambio` desde la
  entidad o el actor; `None` para acciones globales de plataforma.
- **Justificación**: sin ese campo, exportar la auditoría de un tenant requeriría deducirla del
  usuario, lo que falla para acciones del almacén (otro rol) o registros globales. Es la forma
  correcta de aislar.
- **Implementación**: `registrar_cambio` resuelve `tenant` desde el actor y, si no lo tiene, desde un
  registro de entidades auditables que conoce el modelo y su ruta de tenant; si no puede, deja `None`.
  Las specs que ya llaman a `registrar_cambio` no necesitan cambiar su firma.
- **Alternativas descartadas**: filtrar por `usuario.tenant` (incompleto); mapear entidad/ID a tenant
  en cada consulta (frágil y lento).

### D-06. `Conciliacion.ajustes_aplicados`

- **Decisión**: añadir `ajustes_aplicados` a `Conciliacion`, fijado al aprobar con el total de series
  creadas/reasignadas/instaladas y ajustes de cantidad. En estados no aprobados es 0.
- **Justificación**: 012 debe mostrar “Ajustes aplicados” y no puede reconstruirlo con fiabilidad solo
  desde diferencias.
- **Alternativas descartadas**: contar diferencias (no todas generan ajuste); contar registros de
  auditoría (no están correlacionados con la conciliación).

### D-07. Exportaciones en memoria

- **Decisión**: `openpyxl` genera un `BytesIO`; el servicio devuelve `ArchivoReporte(nombre, bytes,
  content_type)`. La vista responde con `HttpResponse` y `Content-Disposition`. No hay archivos
  persistidos ni hash.
- **Justificación**: la spec pide exportar/descargar, no almacenar. Evita limpieza y rutas.
- **Alternativas descartadas**: guardar en `MEDIA_ROOT` (huérfanos, permisos); generar un modelo de
  reporte (complejidad innecesaria).

### D-08. Rango mensual y zona horaria

- **Decisión**: calendario natural; `inicio` y `fin` en la zona configurada; filtros `[inicio, fin)`.
  Mes 1–12; año 2000–2100.
- **Justificación**: evita ambigüedad de límites y dobles conteos del primer día del mes siguiente.
- **Alternativas descartadas**: usar solo fechas `DateField` sin hora (mezcla); UTC fijo (desfase
  local).

### D-09. Permisos

- **Decisión**: global solo `ADMIN_PLATAFORMA`; tenant solo `USUARIO_TENANT` de ese tenant; el Admin
  puede generar/ver cualquier tenant. Sin permisos Django por cadena.
- **Justificación**: patrón de 001/006/007/009/010/011 y alcance por sesión.
- **Alternativas descartadas**: `reportes.add_cortemensual` (no refleja alcance); confiar solo en la
  vista.

### D-10. RLS

- **Decisión**: `CorteMensual` por `tenant_id`; las filas globales (`tenant_id IS NULL`) solo para
  Admin. Si 001 no está disponible, deuda y filtrado ORM.
- **Justificación**: principio I; el corte global no debe verse desde una cuenta de tenant.
- **Alternativas descartadas**: sin RLS; política que permita NULL a cualquier rol (fuga global).

### D-11. Sin escrituras de stock

- **Decisión**: 012 no escribe `StockTecnico`, `StockGeneral`, `Serie`, `SolicitudAsignacion` ni
  `Conciliacion`; solo lee y crea `CorteMensual`.
- **Justificación**: es un reporte; cualquier escritura alteraría la fuente que mide.
- **Alternativas descartadas**: “corregir” totales desde el reporte (fuera de spec).

### D-12. Rendimiento

- **Decisión**: agregaciones SQL, `distinct`, índices por tenant/fecha y exportación por lotes;
  objetivo de 10 000 líneas y 5 000 registros de auditoría en tiempo razonable, sin N+1.
- **Justificación**: requisito 6.1.
- **Alternativas descartadas**: recorrer objetos en Python (N+1 y memoria).

### D-13. Sin Celery ni correo

- **Decisión**: generación y exportación síncronas; sin tareas, sin correo.
- **Justificación**: la spec no lo pide y el tamaño esperado no lo exige.
- **Alternativas descartadas**: tarea asíncrona con sondeo (más infraestructura); envío por correo
  (fuera de spec).

### D-14. Auditoría de reportes

- **Decisión**: auditar `CorteMensual/alta` y `CorteMensual/regenerado`; no auditar el contenido de
  los Excel ni cada descarga.
- **Justificación**: lo relevante es el dato del corte; el archivo es una vista efímera.
- **Alternativas descartadas**: auditar cada exportación (ruido); no auditar regeneraciones (pierde
  trazabilidad).

### D-15. Alcance funcional

- **Decisión**: cortes por tenant y globales; no hay cortes por región. Las exportaciones son de
  auditoría y conciliación; no se agregan reportes de stock, traspasos o devoluciones.
- **Justificación**: la spec solo pide esos dos alcances y esas dos exportaciones.
- **Alternativas descartadas**: agregar región (sin requisito); exportar todas las entidades (fuera de
  alcance).

## Correcciones documentales necesarias

1. `012-reportes-mensuales/spec.md` §5.1, §5.2 y §9: definir métricas, acotar no justificado a 0 y
   aclarar corte persistido/exportaciones a demanda.
2. `001-tenants-y-acceso/data-model.md` y contratos de auditoría: añadir `RegistroCambio.tenant`
   nullable e índice `(tenant, fecha)`; `registrar_cambio` lo puebla.
3. `010-conciliacion-de-stock/data-model.md` y `plan.md`: añadir `Conciliacion.ajustes_aplicados` y
   fijarlo al aprobar.
4. `004-recojo-de-materiales/data-model.md`: recordar que `INSTALADA` cuenta como liquidado/instalado
   e `INACTIVA` como baja, sin sumarlas.

## Deudas y riesgos abiertos

| Deuda / riesgo | Tratamiento |
|---|---|
| `RegistroCambio` histórico sin `tenant` | Rellenar desde entidad/actor cuando sea posible; si no, `None` y solo aparece en el global |
| Conciliaciones antiguas sin `ajustes_aplicados` | `0` por defecto; no se reconstruye |
| Merma acotada a 0 | Se documenta y se prueba; el no justificado exacto negativo no se muestra |
| RLS no disponible | Deuda; el ORM filtra por tenant/global |
| Reportes grandes | Agregaciones, índices y exportación por lotes |
| Cambios de datos posteriores | El corte guardado es una foto; regenerar actualiza con auditoría |

## Conclusión

No quedan incógnitas bloqueantes. El corte queda definido sin ambigüedad, el global se protege con
restricciones parciales, la auditoría se puede aislar por tenant y las exportaciones se generan sin
persistir archivos ni alterar stock.
