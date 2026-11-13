# Quickstart y validación: 013 Registro de Materiales

**Fase**: 1 | **Fecha**: 2026-11-12 | **Spec**:
`05-especificaciones/013-registro-materiales/spec.md`

Guía para validar el catálogo habilitado, el registro por orden, los saldos, los despachos y el
reporte mensual. Los detalles de datos están en `data-model.md` y los contratos en `contracts/`.

## Prerrequisitos

- Python 3.12+.
- PostgreSQL 16+ con rol sin `SUPERUSER` ni `BYPASSRLS`.
- Specs 001, 002, 003 y 004 implementadas.
- `materiales.Material`, `tecnicos.Tecnico`, `recojos.Recojo`/`LineaRecojo` y
  `auditoria.RegistroCambio` con `tenant`.
- App `registro_materiales` registrada en `config/settings/base.py` y migraciones aplicadas.

Si falta cualquiera, la validación se detiene y se reporta.

## Configuración inicial

Seguir la configuración de `05-especificaciones/001-tenants-y-acceso/quickstart.md` (venv,
dependencias, PostgreSQL y `.env`). Después:

```powershell
python manage.py migrate
python manage.py check
```

Comprobar las tablas:

```powershell
python manage.py shell -c "from registro_materiales.models import MaterialHabilitado, SaldoInicialPeriodo, DespachoAlmacen, OrdenLiquidacion, UsoMaterialOrden; print(MaterialHabilitado._meta.db_table, OrdenLiquidacion._meta.db_table)"
```

**Esperado**: `registro_materiales_materialhabilitado` y `registro_materiales_ordenliquidacion`, sin
errores.

No se cargan datos por migración. El catálogo habilitado se carga desde la pantalla del tenant o por
un comando de administración.

## Pruebas automatizadas

```powershell
# Servicios y validaciones
pytest tests/unit/test_registro_servicios.py tests/unit/test_registro_saldos.py
pytest tests/unit/test_registro_validaciones.py

# Integración
pytest tests/integration/test_registro_ordenes.py tests/integration/test_registro_catalogo.py
pytest tests/integration/test_registro_despachos.py tests/integration/test_registro_saldos.py
pytest tests/integration/test_registro_reporte.py tests/integration/test_registro_auditoria.py
pytest tests/integration/test_registro_aislamiento.py

# Contrato HTTP
pytest tests/contract/test_registro_http.py

# Todo 013
pytest -k "registro"

# Cobertura
pytest --cov=registro_materiales
```

Las pruebas requieren PostgreSQL real; validan restricciones, bloqueos, RLS y concurrencia.

## Escenarios de validación

### Catálogo y menú

1. Iniciar sesión como cuenta del tenant.
2. Abrir “Registrar materiales”.
3. Habilitar y deshabilitar un material.

**Esperado**: solo aparecen técnicos y materiales del tenant; el material deshabilitado no se ofrece
en nuevas órdenes, pero conserva historial. La cuenta de otro tenant no ve la opción.

Pruebas: `test_menu_registrar_materiales_solo_para_tenant`,
`test_orden_nueva_muestra_catalogo_habilitado`.

### Orden nueva y existente

1. Elegir técnico, número de orden y fecha.
2. Enviar el contexto: debe aparecer el catálogo con cantidades 0.
3. Guardar una orden con cantidades.
4. Volver a ingresar el mismo número para el mismo técnico y mes.

**Esperado**: la orden existente se abre para editar, sin duplicado. El mismo número para otro
técnico o mes se permite. Un doble clic no crea duplicados.

Pruebas: `test_orden_duplicada_mismo_tecnico_y_mes_abre_existente`,
`test_misma_orden_en_otro_tecnico_o_mes_se_permite`, `test_doble_clic_no_crea_orden_duplicada`.

### Cantidades

- Vacío o 0 no suma uso.
- Negativo, decimal o texto devuelve “La cantidad debe ser un número entero mayor o igual a 0”.
- Un uso con técnico distinto al de la orden se rechaza.

Pruebas: `test_cantidad_vacia_o_cero_no_suma_uso`,
`test_cantidad_negativa_decimal_o_texto_se_rechaza`,
`test_uso_con_tecnico_distinto_al_de_la_orden_se_rechaza`.

### Saldos

1. Cargar saldo inicial 100 para un material/periodo.
2. Registrar despachos 20 y usos 30.
3. Consultar el reporte.

**Esperado**: saldo final 90. Un mes sin saldo manual hereda 90 del anterior. Un saldo manual prevalece
y se audita. Un saldo final negativo se muestra con alerta.

Pruebas: `test_saldo_final_es_inicial_mas_despachos_menos_usado`,
`test_mes_sin_saldo_inicial_hereda_final_anterior`,
`test_saldo_inicial_manual_prevalece_y_se_audita`,
`test_saldo_final_negativo_se_muestra_con_alerta`.

### Despachos

1. Registrar un despacho con recojo y línea del tenant.
2. Intentar con recojo/línea de otro tenant.
3. Intentar superar la cantidad de la línea.

**Esperado**: el despacho válido se registra; el ajeno y el excedido se rechazan. La cantidad 0 se
registra pero no suma. La edición se audita.

Pruebas: `test_despacho_vinculado_a_recojo_del_tenant`,
`test_despacho_con_recojo_de_otro_tenant_se_rechaza`,
`test_despacho_mayor_a_linea_de_recojo_se_rechaza`.

### Reporte

1. Consultar el reporte del periodo.

**Esperado**: totales por material (inicial, despachos, usado, final) y detalle por técnico. El saldo
negativo se muestra con alerta.

Pruebas: `test_reporte_mensual_incluye_detalle_por_tecnico`.

### Historial y aislamiento

- Editar una orden, saldo o despacho genera un registro con usuario, fecha, valor anterior y nuevo.
- La cuenta de otro tenant no puede consultar ni modificar datos; no se revela su existencia.
- Cambiar la fecha de una orden a otro mes recalcula el periodo y revalida la unicidad.

Pruebas: `test_editar_orden_registra_historial`,
`test_aislamiento_entre_tenants_en_ordenes_y_reporte`,
`test_cambio_de_fecha_a_otro_mes_revalida_unicidad`.

## Escenarios complementarios

### Catálogo

- Habilitar, deshabilitar y reactivar; no se borra el historial.
- Material no habilitado no se puede usar en una orden nueva.
- Material deshabilitado con usos históricos se muestra en la orden existente.

### Saldos

- Sin datos anteriores: inicial 0.
- Herencia encadenada de varios meses.
- Periodo inválido (`2026-13`) se rechaza.
- Saldo manual duplicado se actualiza y audita.

### Despachos

- Varios despachos por línea no superan el total.
- Editar un despacho recalcula la suma excluyendo el propio.
- Material distinto al de la línea se rechaza.
- Recojo sin línea se rechaza.

### Órdenes

- Número con espacios se recorta y normaliza; número vacío o con guiones se rechaza.
- Cambio de fecha a otro mes revalida la clave.
- Orden de otro tenant se trata como inexistente.

### Rendimiento

- Reporte de 100 materiales y 1 000 usos en tiempo razonable, sin N+1.
- Herencia de saldo cacheada por request.

## Criterios de salida

La funcionalidad se considera validada cuando:

- [ ] `pytest -k "registro"` pasa completo sobre PostgreSQL.
- [ ] Todos los criterios de aceptación tienen al menos una prueba automatizada.
- [ ] La orden es única por tenant/técnico/periodo/número y se abre para editar.
- [ ] Las cantidades 0 no suman; las inválidas se rechazan.
- [ ] El saldo final es `inicial + despachos - uso` y la herencia funciona.
- [ ] Los despachos respetan el recojo y su línea.
- [ ] Toda edición queda auditada con valor anterior y nuevo.
- [ ] Ningún tenant ve datos de otro.
- [ ] 013 no modifica stock, conciliaciones ni recojos.
- [ ] No se agregaron dependencias, Excel/PDF ni permisos Django por cadena.
