---
description: "Lista de tareas para la implementación de 009 Traspaso entre Técnicos"
---

# Tareas: 009 Traspaso entre Técnicos

**Entrada**: Documentos de diseño en `05-especificaciones/009-traspaso-entre-tecnicos/`

**Prerrequisitos**: `plan.md` (obligatorio), `spec.md` (obligatorio), `research.md`, `data-model.md`,
`contracts/` y `quickstart.md`; **spec 001 implementada** (`acceso.Usuario`,
`ContextoUsuarioMiddleware`, `tenants.Tenant`, `tenants.Region` y `auditoria.RegistroCambio`),
**spec 002 implementada** (`materiales.Material`), **spec 003 implementada**
(`tecnicos.Tecnico`), **spec 004 implementada** (`series.Serie` con `numero`, estado, tenant,
material y lote), **spec 005 implementada** (series `ASIGNADA` con custodia), **spec 006/007
implementadas** (solicitudes, confirmación y `validar_cuenta_almacen`) y **spec 008 implementada**
(`StockTecnico`, `incrementar_stock_tecnico`, `decrementar_stock_tecnico` y auditoría de stock).
También deben estar aplicadas las correcciones documentales de `plan.md` §Correcciones: campos
`Serie.tecnico`/`Serie.asignada_en` en 004/005/006/007/008/011 y generación del Excel al enviar.
La app `traspasos` se crea aquí; no se duplican tablas de series, stock, asignaciones ni recojos.

**Pruebas**: **INCLUIDAS y obligatorias**. La constitución (principio VIII y puerta de pruebas) exige
al menos una prueba por criterio de aceptación CA-01…CA-09. Cada historia escribe primero sus pruebas,
las ve fallar y luego implementa. Todas las pruebas usan PostgreSQL, nunca SQLite.

**Organización**: `spec.md` no declara historias de usuario ni prioridades explícitas; define los
actores, RF-33…RF-38 y CA-01…CA-09. Se derivan cuatro historias para permitir entregas incrementales,
sin agregar funcionalidad fuera de la spec.

## Formato: `[ID] [P?] [Story] Descripción`

- **[P]**: puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia asociada (`US1`…`US4`)
- Todas las rutas son relativas a la raíz del repositorio

## Origen de las historias de usuario

| Historia | Prioridad | Origen en `spec.md` |
|---|---|---|
| US1 — Crear y enviar el traspaso con Excel y validaciones | P1 | RF-33, RF-34, RF-35, RF-36; CA-01…CA-05; §5.1–§5.4 |
| US2 — Confirmar y mover custodia y stock | P2 | RF-37, RF-38; CA-06, CA-08, CA-09; §5.5–§5.6 |
| US3 — Rechazar sin cambios y cancelar | P3 | RF-37; CA-07; §5.5 |
| US4 — Auditar y proteger la integridad | P4 | RF-37; §6.1, §6.3; CA-04…CA-06 |

## Convenciones de rutas

Proyecto Django único en la raíz: app nueva `traspasos/`, plantillas en `templates/traspasos/` y
`templates/almacen/traspasos/`, pruebas en `tests/{unit,integration,contract}/` y migración
transversal en `series/migrations/`. Las apps `acceso`, `tenants`, `auditoria`, `materiales`,
`tecnicos`, `series`, `asignaciones` y `stock` son propiedad de sus specs y no se duplican. 009 **no**
crea tablas de series, stock ni asignaciones, **no** toca `StockGeneral`, **no** envía correo ni usa
Celery y **no** usa permisos Django por cadena.

---

## Fase 1: Setup (infraestructura compartida)

**Propósito**: verificar prerrequisitos y correcciones documentales, crear la app, registrar rutas,
preparar fixtures y comprobar RLS.

- [ ] T001 Verificar los prerrequisitos en `config/settings/base.py`, `acceso/models.py`, `tenants/models.py`, `materiales/models.py`, `tecnicos/models.py`, `series/models.py`, `series/services.py`, `stock/models.py`, `stock/services.py`, `asignaciones/services.py` y `auditoria/services.py`: `AUTH_USER_MODEL="acceso.Usuario"`, `ContextoUsuarioMiddleware`, roles `ADMIN_PLATAFORMA`/`USUARIO_TENANT`/`RESPONSABLE_ALMACEN`, `Material.es_seriado`/`lote`, `Tecnico.tenant`/`nif`/`activo`, `Serie.estado` y `Serie.tecnico`/`asignada_en`, `StockTecnico` y servicios `incrementar_stock_tecnico`/`decrementar_stock_tecnico`, `validar_cuenta_almacen` y `registrar_cambio`; detenerse y reportar si falta alguno
- [ ] T002 Crear el esqueleto de la app `traspasos` en `traspasos/__init__.py`, `traspasos/apps.py`, `traspasos/models.py`, `traspasos/services.py`, `traspasos/excel.py`, `traspasos/forms.py`, `traspasos/views.py`, `traspasos/urls.py` y `traspasos/migrations/__init__.py`; registrar `"traspasos"` en `INSTALLED_APPS` y `TRASPASOS_EXCEL_DIR` en `config/settings/base.py`, e incluir `traspasos.urls` desde `config/urls.py`
- [ ] T003 [P] Extender `conftest.py` con fixtures sobre PostgreSQL: `region_traspaso`, `tenant_traspaso`, `tenant_traspaso_otro`, `usuario_tenant_traspaso`, `usuario_almacen_traspaso`, `usuario_almacen_otra_region`, `tecnico_origen`, `tecnico_destino`, `tecnico_otro_tenant`, `material_seriado_traspaso`, `material_no_seriado_traspaso`, `serie_asignada_origen`, `stock_tecnico_origen`, `stock_tecnico_destino`, `traspaso_borrador`, `traspaso_enviado` y `registro_cambios_traspaso`
- [ ] T004 [P] Comprobar si la infraestructura RLS de 001 está disponible en `config/settings/base.py` y en las migraciones de `tenants`; si no lo está, registrar la deuda en `05-especificaciones/009-traspaso-entre-tecnicos/research.md` y no crear una infraestructura paralela
- [ ] T005 [P] Verificar que las correcciones documentales de `05-especificaciones/004-recojo-de-materiales/`, `005-stock-inicial-de-tecnicos/`, `006-solicitud-de-asignacion/`, `007-envio-y-revision-del-almacen/`, `008-confirmacion-y-actualizacion-de-stock/`, `011-logistica-inversa-y-devoluciones/` y `04-contratos/excel-traspaso.md` estén aplicadas: `Serie.tecnico`/`Serie.asignada_en`, `crear_serie(..., tecnico, asignada_en)`, días en mano desde `Serie.asignada_en` y Excel generado al enviar; corregir antes de implementar si algo no coincide

---

## Fase 2: Fundacional (prerrequisitos bloqueantes)

**Propósito**: migración de custodia de series, modelos del traspaso, RLS, excepciones, reservas,
disponibilidad y cuadre que todas las historias necesitan.

**⚠️ CRÍTICO**: ninguna historia puede comenzar hasta completar esta fase.

### Pruebas fundacionales (escribir primero, deben fallar)

- [ ] T006 [P] Escribir en `tests/unit/test_traspaso_servicios.py` las pruebas de restricciones de `SolicitudTraspaso` y `LineaTraspaso`: `CheckConstraint` origen ≠ destino, estado válido, `LineaTraspaso` con serie o cantidad positiva, serie con cantidad 1, cantidad no negativa, `unique(solicitud, serie)` y `unique(solicitud, material)` para no seriados, `PROTECT` en tenant/región/material/serie/técnicos y `tenant` obligatorio en la línea
- [ ] T007 [P] Escribir en `tests/integration/test_traspaso_creacion.py` las pruebas de custodia de `series.Serie`: `ASIGNADA` exige `tecnico` y `asignada_en`; `DISPONIBLE`/`RESERVADA` exigen ambos nulos; el técnico debe ser del mismo tenant; la migración rellena datos históricos o se detiene; los índices `(tecnico, estado)` y `(tecnico, material)` existen
- [ ] T008 Escribir en `tests/unit/test_traspaso_servicios.py` las pruebas de `calcular_reservado_tecnico`, `calcular_disponible_tecnico` y `series_disponibles_para_traspaso`: solo cuentan solicitudes `ENVIADA`, las series reservadas se excluyen, material sin stock devuelve `0`, y una serie de otro técnico/tenant no aparece
- [ ] T009 [P] Escribir en `tests/unit/test_traspaso_cuadre.py` las pruebas de `construir_movimientos` y `validar_cuadre_traspaso`: cuadre correcto por series y cantidades; serie que sale y no entra; serie duplicada; serie con material o lote distinto; cantidad no seriada distinta; movimiento extra y faltante; todos producen `CuadreIncorrecto` con “Lo que sale debe cuadrar con lo que entra”
- [ ] T010 [P] Escribir en `tests/contract/test_traspaso_servicios_contrato.py` las pruebas de contrato de las firmas y excepciones de `traspasos/services.py` según `contracts/servicios-traspaso.md`: `crear_solicitud_traspaso`, `actualizar_lineas_borrador`, `enviar_solicitud_traspaso`, `confirmar_traspaso`, `rechazar_traspaso`, `cancelar_traspaso`, `revalidar_traspaso`, `generar_excel_traspaso` y `verificar_hash_excel`

### Implementación fundacional

- [ ] T011 Añadir a `series.Serie` los campos `tecnico` (FK `tecnicos.Tecnico`, `PROTECT`, `null=True`, `related_name="series"`) y `asignada_en` (`DateTimeField`, `null=True`), la `CheckConstraint` de coherencia con el estado y los índices `serie_tecnico_estado`/`serie_tecnico_material` en `series/models.py`
- [ ] T012 Crear `series/migrations/0003_serie_tecnico_asignada_en.py`: añadir los campos y rellenar datos históricos desde stock inicial y asignaciones confirmadas; activar la restricción solo si el relleno es consistente; si no es fiable, detener la migración y documentar la deuda
- [ ] T013 Implementar `SolicitudTraspaso` y `LineaTraspaso` en `traspasos/models.py` con los campos, restricciones e índices de `data-model.md`: `tenant`, `region`, técnicos, `fecha`, `estado`, `motivo_rechazo`, `excel_ruta`, `excel_hash`, marcas de tiempo, `creado_por`/`actualizado_por`; línea con `tenant`, `solicitud`, `material`, `lote`, `serie` FK y `cantidad`
- [ ] T014 Crear `traspasos/migrations/0001_initial.py` con T013, revisar que no cree traspasos, líneas, series ni stock por migración y aplicar con `python manage.py migrate`
- [ ] T015 Crear `traspasos/migrations/0002_rls.py` con RLS de solicitud por `tenant_id`/`region_id` y de línea por `tenant_id`; si T004 determinó que la infraestructura de 001 no está disponible, dejar la migración inactiva y registrar la deuda
- [ ] T016 Implementar en `traspasos/services.py` las excepciones y mensajes exactos de `contracts/servicios-traspaso.md`: `PermisoDenegado`, `TecnicosDistintoTenant`, `OrigenDestinoIguales`, `TecnicoNoExiste`, `MaterialNoExiste`, `SerieNoEnTecnico`, `SerieReservada`, `StockTecnicoInsuficiente`, `CuadreIncorrecto`, `EstadoTraspasoInvalido`, `MotivoRechazoRequerido`, `NoEncontrado`, `ArchivoNoDisponible` y `HashNoCoincide`
- [ ] T017 Implementar en `traspasos/services.py` `validar_cuenta_tenant`, `validar_tecnicos`, `calcular_reservado_tecnico`, `calcular_disponible_tecnico`, `series_disponibles_para_traspaso` y `validar_disponibilidad_lineas`, con `select_related`/`prefetch_related` y sin N+1
- [ ] T018 Implementar en `traspasos/services.py` los `dataclass` `LineaEntrada`, `MovimientoTraspaso`, `CuadreTraspaso`, `CambioMaterialTraspaso` y `ResultadoTraspaso`; `construir_movimientos`, `validar_cuadre_traspaso` y `resumen_cuadre`
- [ ] T019 Implementar en `traspasos/services.py` el helper de auditoría para `SolicitudTraspaso/alta`, `SolicitudTraspaso/estado`, `SolicitudTraspaso/excel`, `SolicitudTraspaso/motivo_rechazo`, `LineaTraspaso/alta`, `LineaTraspaso/baja`, `Serie/tecnico` y `Serie/asignada_en`, usando `auditoria.services.registrar_cambio`, sin secretos ni binarios
- [ ] T020 Ejecutar `pytest tests/unit/test_traspaso_servicios.py tests/unit/test_traspaso_cuadre.py tests/integration/test_traspaso_creacion.py tests/contract/test_traspaso_servicios_contrato.py`; corregir hasta que la fase fundacional esté en verde

**Checkpoint**: series con custodia, modelos de traspaso, RLS, excepciones, reservas y cuadre listos;
las historias pueden comenzar.

---

## Fase 3: US1 — Crear y enviar el traspaso con Excel y validaciones (P1) 🎯 MVP

**Objetivo**: el tenant crea un traspaso entre dos técnicos de su tenant, selecciona series o
cantidades del origen, el sistema valida disponibilidad y cuadre, y al enviar genera el Excel de dos
hojas (Z32/Z31) con hash. El borrador no reserva ni genera Excel.

**Prueba independiente**: crear un traspaso con 2 series y 10 unidades no seriadas, enviarlo y
descargar el Excel; verificar dos hojas, NIF correcto, mismas líneas, estado `ENVIADA` y que el stock
y la custodia no cambiaron. Intentar traspasar 15 sobre 10 o un cuadre con 50/40 y recibir rechazo.

### Pruebas de US1 (escribir primero, deben fallar)

- [ ] T021 [US1] Prueba de integración de **CA-02** en `tests/integration/test_traspaso_creacion.py`: `test_origen_destino_iguales_se_rechaza`; el servicio y el `CheckConstraint` rechazan el mismo técnico; no se crea la solicitud
- [ ] T022 [US1] Prueba de integración de **CA-03** en `tests/integration/test_traspaso_creacion.py`: `test_solo_cede_lo_que_tiene_asignado`; 15 sobre 10 devuelve “La cantidad supera el stock del técnico”; con 4 reservadas en `ENVIADA`, 7 sobre 6 también se rechaza
- [ ] T023 [US1] Prueba de integración de **CA-04** en `tests/integration/test_traspaso_creacion.py`: `test_cuadre_series_incorrecto_rechaza`; una serie que sale y no entra, una duplicada o con material/lote distinto aborta la creación y no guarda nada
- [ ] T024 [US1] Prueba de integración de **CA-05** en `tests/integration/test_traspaso_creacion.py`: `test_cuadre_cantidades_incorrecto_rechaza`; 50 que salen y 40 que entran aborta la creación; se prueba también una línea extra y una faltante
- [ ] T025 [US1] Prueba de integración de **CA-01** en `tests/integration/test_traspaso_envio.py`: `test_traspaso_mismo_tenant_genera_excel_dos_hojas`; al enviar se generan `Desasignación` (Z32, NIF origen) y `Asignación` (Z31, NIF destino), con las mismas líneas y hash SHA-256
- [ ] T026 [US1] Prueba de envío en `tests/integration/test_traspaso_envio.py`: `test_borrador_no_reserva_ni_genera_excel`; el borrador no tiene `excel_ruta`, no cambia `StockTecnico` ni `Serie.asignada_en`; al enviar, la solicitud queda `ENVIADA`, con `enviada_en`, y la reserva se deriva del estado
- [ ] T027 [US1] Prueba de revalidación al enviar en `tests/integration/test_traspaso_envio.py`: si una serie dejó de estar en el origen o apareció reservada por otro traspaso, el envío falla con `SerieNoEnTecnico`/`SerieReservada` y no genera Excel ni cambia el estado
- [ ] T028 [P] [US1] Prueba de edición de borrador en `tests/integration/test_traspaso_creacion.py`: editar líneas revalida disponibilidad y cuadre, audita bajas/altas y no toca stock, series ni Excel; editar una solicitud no `BORRADOR` devuelve `409`
- [ ] T029 [P] [US1] Prueba de contrato HTTP en `tests/contract/test_traspaso_http.py`: `GET/POST /traspasos/`, `/traspasos/nuevo/`, `/traspasos/<id>/`, `/traspasos/<id>/editar/`, `/traspasos/<id>/enviar/`, `/traspasos/<id>/cancelar/`, `/traspasos/series-tecnico/` y `/traspasos/validar-disponibilidad/` con códigos `200/302/400/403/404/405/409`
- [ ] T030 [P] [US1] Pruebas unitarias del Excel en `tests/unit/test_traspaso_excel.py`: dos hojas, metadatos Z32/Z31, Centro/Almacén de la región, NIF correcto, tablas de seriales y material menor, misma lista canónica, nombre relativo seguro y hash estable
- [ ] T031 [US1] Pruebas de descarga y hash en `tests/integration/test_traspaso_envio.py`: descarga `200` con `.xlsx`; archivo ausente `404`; hash alterado `409` con “El archivo fue modificado, descarga bloqueada”; no se expone la ruta física

### Implementación de US1

- [ ] T032 [US1] Implementar en `traspasos/services.py` `crear_solicitud_traspaso` y `actualizar_lineas_borrador`: validar cuenta, técnicos, materiales, disponibilidad y cuadre; crear/actualizar en `transaction.atomic`; copiar `region=tenant.region`, `tenant` y `lote`; auditar altas/bajas; no reservar ni generar Excel
- [ ] T033 [US1] Implementar en `traspasos/services.py` `enviar_solicitud_traspaso`: exigir `BORRADOR`, bloquear solicitud, `Tenant`, `StockTecnico` por `(material_id, tecnico_id)` y series por `id`, revalidar disponibilidad/reservas/cuadre, pasar a `ENVIADA`, fijar `enviada_en` y auditar
- [ ] T034 [US1] Implementar en `traspasos/excel.py` `generar_excel_traspaso`: hojas `Desasignación`/`Asignación`, metadatos Z32/Z31, Centro/Almacén, NIF, fecha, tenant, región e ID; tablas de seriales y material menor; guardar en `TRASPASOS_EXCEL_DIR` con nombre relativo seguro y hash SHA-256; limpiar el archivo si falla la transacción
- [ ] T035 [US1] Implementar en `traspasos/services.py` `verificar_hash_excel` con `hmac.compare_digest` y la resolución segura de ruta; rechazar `..`, rutas absolutas y salidas de `MEDIA_ROOT`/`TRASPASOS_EXCEL_DIR`
- [ ] T036 [US1] Implementar en `traspasos/forms.py` el formulario y formset de traspaso: técnicos del tenant, fecha por defecto hoy, líneas con material, series o cantidad, tipo/lote de solo lectura; validar origen ≠ destino, destino activo, cantidad `>0` y al menos una línea; no aceptar `tenant`/`region`/`estado`/NIF/tipo/lote del cliente
- [ ] T037 [US1] Implementar en `traspasos/views.py` y `traspasos/urls.py` las rutas de tenant de `contracts/http-endpoints.md`: listado, creación, detalle, edición, envío, cancelación, selector HTMX de series, validación de disponibilidad y descarga del Excel; aplicar login, CSRF y mapeo de errores `400/403/404/405/409`
- [ ] T038 [US1] Crear `templates/traspasos/listado.html`, `formulario.html`, `detalle.html` y `_series_tecnico.html`: estado, técnicos, fecha, líneas, cuadre, Excel y acciones según estado; sin datos de otro tenant ni series de otro técnico
- [ ] T039 [US1] Asegurar en `traspasos/services.py` que el envío no toca `StockGeneral`, no cambia `Serie.tecnico`/`Serie.asignada_en` y no envía correo ni encola tareas; solo reserva por estado y genera el Excel
- [ ] T040 [US1] Ejecutar `pytest tests/unit/test_traspaso_cuadre.py tests/unit/test_traspaso_excel.py tests/integration/test_traspaso_creacion.py tests/integration/test_traspaso_envio.py tests/contract/test_traspaso_http.py` y corregir hasta que CA-01…CA-05 estén en verde

**Checkpoint**: US1 funcional; el tenant crea y envía traspasos válidos, con Excel de dos hojas y sin
mover stock ni custodia.

---

## Fase 4: US2 — Confirmar y mover custodia y stock (P2)

**Objetivo**: el Responsable de almacén confirma un traspaso `ENVIADA`; las series cambian al técnico
destino, el stock del origen baja y el del destino sube, los días en mano se reinician y el stock
general no cambia.

**Prueba independiente**: confirmar un traspaso con 3 series y 20 unidades; verificar series
`ASIGNADA` al destino, stock origen −3/−20, destino +3/+20, `Serie.asignada_en` reiniciado y
`StockGeneral` idéntico. Repetir la confirmación y recibir `409`.

### Pruebas de US2 (escribir primero, deben fallar)

- [ ] T041 [US2] Prueba de integración de **CA-06** en `tests/integration/test_traspaso_confirmacion.py`: `test_confirmar_cambia_tecnico_de_series`; cada serie queda `ASIGNADA` al destino y conserva material/lote; el origen ya no la tiene
- [ ] T042 [US2] Prueba de stock en `tests/integration/test_traspaso_confirmacion.py`: el stock del origen baja y el del destino sube por el total agregado por material, usando los servicios de 008; se audita `StockTecnico/cantidad` en ambos
- [ ] T043 [US2] Prueba de **CA-08** en `tests/integration/test_traspaso_confirmacion.py`: `test_stock_general_invariable`; `StockGeneral` antes y después de crear, enviar y confirmar es idéntico; el rechazo y la cancelación se cubren en T055/T058
- [ ] T044 [US2] Prueba de **CA-09** en `tests/integration/test_traspaso_confirmacion.py`: `test_dias_en_mano_reinician_al_traspasar`; una serie con `asignada_en` hace 10 días queda con la fecha de confirmación y 0 días en el destino; la anterior queda auditada
- [ ] T045 [US2] Prueba de revalidación/rollback en `tests/integration/test_traspaso_confirmacion.py`: si una serie ya no está en el origen, el stock no alcanza o el cuadre falla, se revierte todo y la solicitud sigue `ENVIADA`
- [ ] T046 [US2] Prueba de estado en `tests/integration/test_traspaso_confirmacion.py`: confirmar una solicitud que no está `ENVIADA` devuelve `409`; una segunda confirmación no mueve stock ni custodia
- [ ] T047 [P] [US2] Prueba de concurrencia en `tests/integration/test_traspaso_concurrencia.py`: dos confirmaciones simultáneas de la misma solicitud dejan una sola `CONFIRMADA` y un solo movimiento; dos traspasos que compiten por el mismo stock dejan solo uno válido
- [ ] T048 [P] [US2] Prueba de contrato HTTP en `tests/contract/test_traspaso_http.py`: `GET /almacen/traspasos/`, detalle, descarga y `POST confirmar`; `302` al confirmar, `409` por estado/serie/stock, `404` por región ajena, `403` por rol y `405` para `GET`
- [ ] T049 [P] [US2] Prueba de auditoría de confirmación en `tests/integration/test_traspaso_auditoria.py`: `ENVIADA→CONFIRMADA`, `Serie/tecnico` y `Serie/asignada_en` por serie, y `StockTecnico/cantidad` de 008 sin duplicar

### Implementación de US2

- [ ] T050 [US2] Implementar en `traspasos/services.py` `revalidar_traspaso` y `confirmar_traspaso`: validar cuenta de almacén y `ENVIADA`; bloquear solicitud, `Tenant`, `StockTecnico` por `(material_id, tecnico_id)` y series por `id`; revalidar series, stock y cuadre; cambiar `Serie.tecnico` y `Serie.asignada_en`; decrementar/incrementar stock con 008; pasar a `CONFIRMADA`, fijar `confirmada_en` y auditar
- [ ] T051 [US2] Implementar en `traspasos/views.py` y `traspasos/urls.py` las rutas de almacén: bandeja de la región, detalle, descarga y confirmación; validar rol/región, mapear `409/404/403/405` y no exponer datos de otra región
- [ ] T052 [US2] Crear `templates/almacen/traspasos/listado.html` y `detalle.html`: técnicos, fecha, estado, líneas, cuadre, Excel y botón “Confirmar” solo para `ENVIADA`; sin acciones para estados terminales
- [ ] T053 [US2] Asegurar en `traspasos/services.py` que la confirmación no lee ni escribe `StockGeneral`, no crea series y no cambia el estado de la serie; devolver `ResultadoTraspaso` con series movidas, totales y `confirmada_en`
- [ ] T054 [US2] Ejecutar `pytest tests/integration/test_traspaso_confirmacion.py tests/integration/test_traspaso_concurrencia.py tests/integration/test_traspaso_auditoria.py tests/contract/test_traspaso_http.py` y corregir hasta que CA-06, CA-08 y CA-09 estén en verde

**Checkpoint**: US2 funcional; la confirmación mueve custodia y stock técnico, reinicia días en mano y
deja intacto el stock general.

---

## Fase 5: US3 — Rechazar sin cambios y cancelar (P3)

**Objetivo**: el almacén rechaza un traspaso `ENVIADA` con motivo obligatorio y no cambia series,
stock ni Excel; el tenant cancela un borrador sin reservas.

**Prueba independiente**: rechazar un traspaso con series y cantidades y comprobar que las series
siguen en el origen, el stock no cambió, el motivo quedó auditado y la reserva se liberó. Intentar
rechazar sin motivo y recibir `400`. Cancelar un borrador y comprobar que no hay cambios.

### Pruebas de US3 (escribir primero, deben fallar)

- [ ] T055 [US3] Prueba de **CA-07** en `tests/integration/test_traspaso_rechazo.py`: `test_rechazar_no_cambia_nada`; series, stock, `Serie.asignada_en` y `StockGeneral` quedan iguales; la solicitud queda `RECHAZADA` con `rechazada_en` y motivo
- [ ] T056 [US3] Prueba de motivo en `tests/integration/test_traspaso_rechazo.py`: motivo vacío, solo espacios o mayor a 1000 devuelve “El motivo de rechazo es obligatorio”; un rechazo válido audita estado y motivo
- [ ] T057 [US3] Prueba de liberación de reserva en `tests/integration/test_traspaso_rechazo.py`: tras rechazar, la serie y la cantidad vuelven a estar disponibles; otro traspaso puede reservarlas
- [ ] T058 [US3] Prueba de cancelación en `tests/integration/test_traspaso_rechazo.py`: cancelar un `BORRADOR` deja `CANCELADA` sin reservas ni cambios; cancelar `ENVIADA` devuelve `409`
- [ ] T059 [P] [US3] Prueba de contrato HTTP en `tests/contract/test_traspaso_http.py`: `POST rechazar` con `302/400/403/404/405/409`; `POST /traspasos/<id>/cancelar/` con `302/409`; sin `GET` para las acciones

### Implementación de US3

- [ ] T060 [US3] Implementar en `traspasos/services.py` `rechazar_traspaso`: validar cuenta de almacén, `ENVIADA`, motivo no vacío/máximo 1000; en `transaction.atomic` pasar a `RECHAZADA`, fijar `rechazada_en`/`motivo_rechazo` y auditar; no tocar series, stock ni Excel
- [ ] T061 [US3] Implementar en `traspasos/services.py` `cancelar_traspaso`: validar cuenta de tenant y `BORRADOR`; pasar a `CANCELADA`, fijar `cancelada_en` y auditar; no tocar series, stock ni Excel
- [ ] T062 [US3] Implementar en `traspasos/views.py`, `traspasos/urls.py` y `templates/almacen/traspasos/detalle.html` la acción de rechazo con motivo; completar la acción de cancelación en las plantillas del tenant; mapear errores y no permitir `GET`
- [ ] T063 [US3] Ejecutar `pytest tests/integration/test_traspaso_rechazo.py tests/contract/test_traspaso_http.py` y corregir hasta que CA-07 esté en verde

**Checkpoint**: US3 funcional; rechazar y cancelar no mueven stock ni custodia y liberan reservas.

---

## Fase 6: US4 — Auditar y proteger la integridad (P4)

**Objetivo**: todas las operaciones dejan auditoría completa y transaccional, y el traspaso resiste
concurrencia, fallos de Excel/auditoría y aislamiento entre tenants.

**Prueba independiente**: crear, enviar, confirmar y rechazar traspasos; verificar un registro por
evento, actor correcto, sin secretos ni duplicados de 008; forzar un fallo de auditoría y comprobar la
reversión total; ejecutar dos operaciones concurrentes sin interbloqueo.

### Pruebas de US4 (escribir primero, deben fallar)

- [ ] T064 [US4] Prueba de auditoría completa en `tests/integration/test_traspaso_auditoria.py`: alta de solicitud, altas/bajas de líneas, `BORRADOR→ENVIADA`, `SolicitudTraspaso/excel`, `ENVIADA→CONFIRMADA`, `Serie/tecnico`, `Serie/asignada_en`, rechazo con motivo y cancelación
- [ ] T065 [US4] Prueba de prohibiciones en `tests/integration/test_traspaso_auditoria.py`: el actor es el usuario de la sesión y nunca `None`; no hay contraseñas, tokens, secretos, binarios, rutas absolutas ni datos de otro tenant; la auditoría de stock es la de 008 y aparece una sola vez
- [ ] T066 [US4] Prueba de rollback en `tests/integration/test_traspaso_auditoria.py`: un fallo de auditoría o de generación del Excel revierte estado, líneas, series, stock y archivo parcial; no queda una solicitud `ENVIADA` sin Excel ni un Excel huérfano
- [ ] T067 [US4] Prueba de concurrencia de envío en `tests/integration/test_traspaso_concurrencia.py`: dos envíos que compiten por la misma serie dejan una sola reserva; el segundo recibe `SerieReservada`; dos operaciones con materiales invertidos no producen interbloqueo
- [ ] T068 [US4] Prueba de aislamiento en `tests/integration/test_traspaso_concurrencia.py`: tenant A no ve ni opera traspasos de B; almacén de otra región recibe `404`; series/stock de otro tenant no se consultan; `LineaTraspaso.tenant` coincide con la solicitud; RLS activa si está disponible
- [ ] T069 [US4] Prueba de rendimiento en `tests/integration/test_traspaso_concurrencia.py`: un traspaso de 100 series se valida y confirma en menos de 2 segundos, sin una consulta por serie

### Implementación de US4

- [ ] T070 [US4] Completar en `traspasos/services.py` las guardas de atomicidad y bloqueo: una sola transacción externa, sin commit propio, revalidación dentro del bloqueo, orden `SolicitudTraspaso → Tenant → StockTecnico (material, técnico) → Serie` y limpieza del archivo si falla el envío
- [ ] T071 [US4] Revisar `traspasos/services.py`, `traspasos/excel.py`, `traspasos/models.py` y `traspasos/views.py`: sin `F()` ciego, sin escrituras a `StockGeneral`, sin permisos Django por cadena, sin correo/Celery, sin `tenant_id`/`region_id` del cliente y con mensajes en español
- [ ] T072 [US4] Ejecutar `pytest tests/integration/test_traspaso_auditoria.py tests/integration/test_traspaso_concurrencia.py` y corregir hasta que la auditoría, el aislamiento y la concurrencia estén en verde

**Checkpoint**: US4 funcional; el traspaso es atómico, auditable, aislado y concurrente.

---

## Fase 7: Polish y preocupaciones transversales

- [ ] T073 [P] Ejecutar `pytest -k "traspaso"` sobre `tests/unit`, `tests/integration` y `tests/contract` con PostgreSQL y corregir cualquier fallo
- [ ] T074 [P] Ejecutar `pytest --cov=traspasos tests/unit tests/integration tests/contract` y revisar que cada validación, excepción y transición de `traspasos/services.py` tenga al menos una prueba
- [ ] T075 [P] Revisar `traspasos/excel.py` y `traspasos/services.py`: hash estable, ruta segura, dos hojas, cuadre, sin binarios en base/auditoría y sin correo
- [ ] T076 [P] Revisar `traspasos/models.py` y las migraciones: `tenant`/`region` obligatorios, RLS, restricciones únicas, `CheckConstraint` de custodia de series y ningún cambio a tablas de stock
- [ ] T077 [P] Revisar `traspasos/views.py`, `traspasos/urls.py` y `templates/traspasos/`: sin lógica de negocio, sin datos de otro tenant, sin `GET` en acciones y con CSRF
- [ ] T078 [P] Actualizar `05-especificaciones/009-traspaso-entre-tecnicos/quickstart.md` con los comandos y resultados reales de la suite, sin duplicar contratos ni modelos
- [ ] T079 [P] Verificar que las correcciones de 004/005/006/007/008/011 y `04-contratos/excel-traspaso.md` siguen aplicadas y que `Serie.tecnico`/`Serie.asignada_en` se fijan y limpian en todos los flujos
- [ ] T080 Recorrer los escenarios de `quickstart.md` para CA-01…CA-09 y registrar el resultado; si algo falla, corregir la implementación o el documento antes de cerrar
- [ ] T081 Ejecutar `python manage.py check` y `python manage.py migrate --check`; confirmar que no hay migraciones pendientes ni errores de configuración
- [ ] T082 Revisar `traspasos/services.py`, `traspasos/views.py`, `config/settings/base.py` y `requirements-dev.txt`: 009 no agrega dependencias, correo, Celery, SSE ni permisos Django, y `StockGeneral` es idéntico antes y después de todo el ciclo

---

## Dependencias y orden de ejecución

### Dependencias entre fases

- **Setup (Fase 1)**: depende de 001–008 implementadas y de las correcciones documentales.
- **Fundacional (Fase 2)**: depende de Setup; **bloquea** las historias.
- **US1 (Fase 3)**: depende de Fundacional; entrega creación, envío y Excel.
- **US2 (Fase 4)**: depende de US1 y de los servicios de stock de 008.
- **US3 (Fase 5)**: depende de US1; puede ejecutarse en paralelo con US2 si se coordinan archivos.
- **US4 (Fase 6)**: depende de US1–US3.
- **Polish (Fase 7)**: depende de todas las historias.

### Dependencias entre historias

- **US1** es el MVP: sin crear y enviar no hay traspaso que confirmar ni rechazar.
- **US2** y **US3** son independientes entre sí una vez que US1 existe; ambas cierran el ciclo del
  almacén.
- **US4** verifica propiedades de las tres anteriores.

### Dentro de cada historia

- Las pruebas se escriben primero y deben fallar.
- Modelos y migraciones antes de servicios.
- Servicios antes de vistas y plantillas.
- La creación antes del envío; el envío antes de la confirmación/rechazo.
- No se avanza con pruebas en rojo.

### Oportunidades de paralelización

- T003–T005 en Setup.
- T006–T010 en Fundacional (archivos de prueba distintos).
- T021–T024 en `test_traspaso_creacion.py` van en secuencia; T025–T027, T031 en `test_traspaso_envio.py` van en secuencia; T029, T030 usan archivos distintos.
- T041–T046 y T049 en `test_traspaso_confirmacion.py`/`test_traspaso_auditoria.py` se coordinan; T047 y T048 usan archivos distintos.
- T055–T058 en `test_traspaso_rechazo.py` van en secuencia; T059 usa otro archivo.
- T064–T066 en `test_traspaso_auditoria.py` van en secuencia; T067–T069 en `test_traspaso_concurrencia.py` van en secuencia.
- T073–T079 en Polish usan archivos distintos.

**Nota**: `traspasos/services.py` es el archivo de mayor contención; T032–T035, T050, T060–T061 y
T070 deben secuenciarse. `traspasos/excel.py` lo usa T034/T075.

---

## Ejemplo de paralelización: US1

```text
# Pruebas en archivos distintos
Tarea: "Contrato HTTP de traspasos en tests/contract/test_traspaso_http.py"       # T029
Tarea: "Excel en tests/unit/test_traspaso_excel.py"                                # T030

# Implementación secuencial en traspasos/services.py
T032 → T033 → T034 → T035 → T039 → T040

# Vistas y plantillas dependen de los servicios
T036 → T037 → T038
```

## Ejemplo de paralelización: US2 y US3

```text
# US2: pruebas en archivos distintos
T047 (concurrencia) y T048 (contrato HTTP) pueden ir en paralelo.
# US3: pruebas
T059 (contrato HTTP) puede ir en paralelo con T055–T058.
# Implementación
T050 (confirmar) y T060–T061 (rechazar/cancelar) comparten services.py: secuenciar.
```

## Estrategia de implementación

### MVP (Fundacional + US1)

1. Completar Setup.
2. Completar Fundacional; validar custodia de series, modelos y cuadre.
3. Completar US1.
4. **DETENERSE y VALIDAR**: CA-01…CA-05 en verde.
5. Demostrar creación, envío y descarga del Excel.

### Entrega incremental

1. Fundacional → modelos y disponibilidad listos.
2. US1 → crear y enviar traspasos con Excel.
3. US2 → confirmar y mover custodia/stock.
4. US3 → rechazar y cancelar.
5. US4 → auditoría, concurrencia y aislamiento.
6. Polish → cobertura, rendimiento y documentación.

---

## Trazabilidad de criterios de aceptación

| CA | Historia | Pruebas principales |
|---|---|---|
| CA-01 | US1 | T025, T040 |
| CA-02 | US1 | T021, T040 |
| CA-03 | US1 | T022, T040 |
| CA-04 | US1 | T023, T040 |
| CA-05 | US1 | T024, T040 |
| CA-06 | US2 | T041, T054 |
| CA-07 | US3 | T055, T063 |
| CA-08 | US2 | T043, T054 |
| CA-09 | US2 | T044, T054 |

## Notas

- [P] significa archivos distintos y sin dependencia de una tarea incompleta.
- [Story] solo aparece en las fases de historia; Setup, Fundacional y Polish no llevan etiqueta.
- Toda prueba se escribe antes de la implementación y debe fallar primero.
- No se acepta `tenant_id`, `region_id`, NIF, tipo de material, lote ni estado del cliente.
- 009 no toca `StockGeneral`, no crea series, no envía correo, no usa Celery y no crea permisos Django.
- `Serie.tecnico`/`Serie.asignada_en` son la fuente de custodia y días en mano; 009 los actualiza solo
  al confirmar un traspaso.
- Las reservas se derivan de `SolicitudTraspaso.estado=ENVIADA`; no hay tabla de reservas.
- Evitar tareas vagas y conflictos de archivo; `traspasos/services.py` debe secuenciarse.
