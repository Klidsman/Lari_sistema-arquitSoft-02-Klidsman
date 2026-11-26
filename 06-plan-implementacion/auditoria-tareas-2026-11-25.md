# Auditoría de tareas por spec — 2026-11-25

Este documento contrasta los `tasks.md` con el código y las pruebas reales del repositorio.

## Resumen

| Spec | Código | Pruebas | Estado real | Pendiente real |
|---|---|---|---|---|
| 001 Tenants y acceso | `tenants`, `acceso`, `auditoria` | `test_tenants`, `test_sesion`, `test_login`, `test_auth_2fa`, `test_cuentas*`, `test_auditoria*` | Completo | Nada funcional |
| 002 Materiales | `materiales` | `test_material_*`, `test_restricciones_material` | Completo | Nada funcional |
| 003 Técnicos | `tecnicos` | `test_tecnico_*`, `test_tecnico_stock_http` | Completo | Nada funcional |
| 004 Recojos | `recojos` | 7 contract + 9 integration + 1 unit `test_recojo_*` | Completo | T059: recorrido manual de quickstart |
| 005 Stock inicial | `stock_inicial` | `test_stock_inicial_*` | Completo, incluido reinicio | T080 rendimiento, T083 docs, T086 cobertura, T087 manual |
| 006 Asignaciones | `asignaciones` | `test_asignacion_*` | Completo | Pruebas con nombres históricos y quickstart/cobertura |
| 007 Almacén | `asignaciones` | `test_almacen_*`, `test_almacen_notificaciones`, `test_almacen_tiempo_real*` | Completo | T120, T123, T125, T126, T130 |
| 008 Stock | `stock` | `test_stock_*`, `test_traspaso_movimientos` | Completo con libro de movimientos | T003 fixtures, T062 rendimiento, T068 cobertura, T069 manual |
| 009 Traspasos | `traspasos` | `test_traspaso*` | Completo; T001–T082 son históricas y fueron sustituidas por la ampliación T083–T118 | T080 manual |
| 010 Conciliación | `conciliaciones` | 63 pruebas `test_conciliacion_*`, 90 % de cobertura | Completo | T003, T076 y T085 |
| 011 Logística inversa | `logistica_inversa` | `test_devolucion*`, `test_baja*`, `test_logistica_inversa*` | Completo, incluida selección por técnico | Cobertura fina y quickstart |
| 012 Reportes | `reportes` | `test_reportes*` | Completo | Cobertura fina y quickstart |
| 013 Registro de materiales | `registro_materiales` | 51 pruebas de registro, 77 % de cobertura | Completo | T004, T069 y T078 |

## Por qué hay tareas sin marcar

- Los `tasks.md` se escribieron antes de implementar y no se actualizaron tarea por tarea.
- Varias tareas exigen archivos de prueba con nombres concretos; la implementación agrupó esas
  pruebas en otros archivos.
- Algunas tareas son de cobertura, rendimiento o validación manual, no de funcionalidad.
- Las tareas de 009 anteriores a la ampliación describen el modelo de un solo origen/destino y fueron
  reemplazadas por las tareas T083–T118.

## Criterio de cierre

Para dar una spec por cerrada:

1. El flujo del `spec.md` está implementado.
2. Al menos una prueba cubre cada criterio de aceptación.
3. `python manage.py check`, `makemigrations --check` y la suite completa están en verde.
4. Se recorrió el `quickstart.md` o se documentó la deuda.

La suite actual tiene **827 pruebas en verde**.
