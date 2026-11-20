# Guía de validación manual — 004 Recojo de materiales

**Propósito**: ejecutar los escenarios 1–15 de
`05-especificaciones/004-recojo-de-materiales/quickstart.md` (tarea **T059**).

**Prerrequisito**: 001, 002 y la base de stock de 008 implementadas. Entorno con PostgreSQL,
Redis y `runserver` activo.

> Todos los comandos se ejecutan desde la raíz del repositorio.

---

## 0. Preparación

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe -m pytest -q
```

Debe terminar en **431 passed**.

Datos mínimos:

1. Región `Ayacucho` con almacén central.
2. Tenant `AYA-01` con cuenta activa.
3. Tenant `AYA-02` con cuenta activa (misma región).
4. Administrador de plataforma y Responsable de almacén.
5. Material seriado `10402520279` (`ROSETA`, lote `FIBERHOME`).
6. Material no seriado `10402520323` (`CABLE`, lote `FIBERHOME`).

---

## 1. Recojo seriado válido (CA-02)

1. Inicia sesión con `AYA-01`.
2. Abre `http://localhost:8000/recojos/nuevo/`.
3. Escribe un nombre para el recojo, por ejemplo `Recojo de rosetas`.
4. Elige el material en la lista desplegable; se muestran código, lote y tipo.
5. Antes de guardar, comprueba que puedes cambiar de material o pulsar **Quitar línea** para
   corregir un error; un recojo ya guardado no se edita.
6. Verifica que el estado de las series aparece en el panel derecho, no debajo del formulario.
7. Pega: `ABC123456789`, `DEF123456789`, `GHI123456789` (una por línea o separadas por ` - `).
8. **Esperado**: la vista previa muestra las tres como Válida en el panel derecho.
9. Guarda.
10. **Esperado**: detalle con nombre, fecha, tenant, región, total de series 3, cantidad 0 y las
    tres series.

Verificación:

```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from stock.models import StockGeneral; from series.models import Serie; from materiales.models import Material; m=Material.objects.get(codigo='10402520279'); print('stock=', StockGeneral.objects.get(material=m).cantidad); print(list(Serie.objects.values_list('numero','estado','tenant__codigo','region__codigo')))"
```

**Resultado:** ☐ OK  ☐ Falló  Observaciones: ______________________________

---

## 2. Normalización de series (CA-03)

1. Ingresa `abc123456789`.
2. **Esperado**: la vista previa muestra `ABC123456789` como Válida.
3. Ingresa `" abc 123456789 "`.
4. **Esperado**: se normaliza igual.
5. Pega en una sola fila:
   `7493DA33A8E0 - 2C9682081050 - 7493DA526E40 - 7493DA527310`.
6. **Esperado**: la vista previa muestra cuatro series válidas; los guiones y espacios se usan
   como separadores.
7. Guarda y verifica que las series persistidas son las normalizadas.

**Resultado:** x OK  ☐ Falló  Observaciones: ______________________________

---

## 3. Validación de formato (CA-04)

1. Prueba `ABC123`, `ABC12345678`, `ABC1234567890` y `ABC-12345678`.
2. **Esperado**: todos como Inválida con “La serie debe tener 12 caracteres alfanuméricos”.
3. Intenta guardar.
4. **Esperado**: no se guarda nada.

**Resultado:** x OK  ☐ Falló  Observaciones: ______________________________

---

## 4. Duplicados en el mismo recojo (CA-05)

1. Ingresa `ABC123456789` dos veces.
2. **Esperado**: la segunda se marca Duplicada.
3. Intenta guardar.
4. **Esperado**: “La serie está duplicada en el recojo” y no se guarda nada.

**Resultado:** x OK  ☐ Falló  Observaciones: ______________________________

---

## 5. Series existentes (CA-06)

1. Con `AYA-01`, ingresa una serie que ya exista en `AYA-02`.
2. **Esperado**: estado “Ya existe”, mensaje “La serie ya está registrada en el sistema”, sin datos del tenant.
3. Intenta guardar.
4. **Esperado**: no se guarda nada.

**Resultado:** x OK  ☐ Falló  Observaciones: ______________________________

---

## 6. Regla todo o nada (CA-07)

1. Prepara 10 series válidas y una inválida.
2. Guarda.
3. **Esperado**: no queda `Recojo`, ni líneas, ni series, ni cambios de stock, ni auditoría.
4. Corrige la serie y guarda.
5. **Esperado**: se guarda el recojo completo.

Verificación:

```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from recojos.models import Recojo, LineaRecojo; from series.models import Serie; from stock.models import StockGeneral; print('recojos=',Recojo.objects.count(),'lineas=',LineaRecojo.objects.count(),'series=',Serie.objects.count(),'stock=',StockGeneral.objects.count())"
```

**Resultado:** ☐ OK  ☐ Falló  Observaciones: ______________________________

---

## 7. Vista previa en tiempo real (CA-08)

1. Pega un bloque de series en el campo de series.
2. **Esperado**: sin recargar, aparece una fila por serie con su estado.
3. Corrige una inválida.
4. **Esperado**: la vista previa se actualiza a Válida.

**Resultado:** ☐ OK  ☐ Falló  Observaciones: ______________________________

---

## 8. Material no seriado (CA-09)

1. Elige el material no seriado e ingresa cantidad `25`.
2. **Esperado**: se guarda; detalle con total de series 0 y cantidad 25.
3. Verifica que el stock general subió en 25 y no se creó ninguna `Serie`.

**Resultado:** ☐ OK  ☐ Falló  Observaciones: ______________________________

---

## 9. Región y aislamiento (CA-01)

1. Con `AYA-01`, registra un recojo.
2. **Esperado**: recojo y series con región de `AYA-01`.
3. Fuerza `region_id`/`tenant_id` de otro tenant.
4. **Esperado**: se ignoran.
5. Con `AYA-02`, abre el detalle del recojo de `AYA-01`.
6. **Esperado**: `404` “El recojo no existe”.
7. Como Administrador y Responsable, abre `/recojos/`.
8. **Esperado**: `403` “No tienes permiso para registrar recojos”.

**Resultado:** ☐ OK  ☐ Falló  Observaciones: ______________________________

---

## 10. Varias líneas y materiales

1. Registra una línea seriada con 2 series y una no seriada con cantidad 10.
2. **Esperado**: dos líneas, total series 2, total cantidad 10.
3. **Esperado**: stock de cada material incrementado; un registro de stock por material.

**Resultado:** x OK  ☐ Falló  Observaciones: ______________________________

---

## 11. Concurrencia de series

1. En dos sesiones del mismo tenant, prepara la misma serie nueva.
2. Guarda ambas casi al mismo tiempo.
3. **Esperado**: una guarda; la otra recibe “La serie ya está registrada en el sistema”.
4. **Esperado**: una sola `Serie` y un solo recojo con esa serie.

**Resultado:** x OK  ☐ Falló  Observaciones: ______________________________

---

## 12. Inmutabilidad y ausencia de borrado

1. **Esperado**: el detalle no ofrece editar ni borrar.
2. Envía `DELETE` a `/recojos/<id>/` y `/recojos/nuevo/`.
3. **Esperado**: `405`.
4. No existe ruta de edición.

**Resultado:** ☐ OK  ☐ Falló  Observaciones: ______________________________

---

## 13. Auditoría

1. Abre `/auditoria/acceso/?entidad=Recojo` como Administrador.
2. **Esperado**: registro `alta` con fecha, región, líneas, series y cantidad.
3. Filtra `entidad=StockGeneral`, `campo=cantidad`.
4. **Esperado**: valor anterior y nuevo por material.
5. Comprueba que no hay secretos ni `tenant_id` separado:

```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from auditoria.models import RegistroCambio; prohibidos=('password','contraseña','token','secreto','tenant_id'); malos=[(r.pk,r.campo) for r in RegistroCambio.objects.filter(entidad__in=['Recojo','StockGeneral']) if any(p in (r.campo+' '+r.valor_anterior+' '+r.valor_nuevo).lower() for p in prohibidos)]; print('sospechosos=', malos)"
```

**Resultado:** x OK  ☐ Falló  Observaciones: ______________________________

---

## 14. Tipo de material inmutable con movimientos

1. Después de un recojo, intenta cambiar el tipo del material desde 002.
2. **Esperado**: “El tipo no se puede cambiar: el material tiene movimientos”.
3. Prueba con un material sin recojos ni stock.
4. **Esperado**: el cambio se permite.

**Resultado:** ☐ OK  ☐ Falló  Observaciones: ______________________________

---

## 15. Anulación lógica dentro de 24 horas

1. Abre un recojo registrado hace menos de 24 horas.
2. **Esperado**: el detalle muestra el aviso de 24 horas y el formulario de anulación.
3. Escribe un motivo y confirma.
4. **Esperado**: estado **Anulado**, stock revertido, series **Disponible** si no se usaron, auditoría de recojo/stock/series.
5. Intenta anular otra vez.
6. **Esperado**: no cambia nada ni duplica auditoría.
7. Fuerza `creado_en` a más de 24 horas y recarga.
8. **Esperado**: mensaje de plazo vencido y sin botón de anulación.

**Resultado:** ☐ OK  ☐ Falló  Observaciones: ______________________________

## 16. Rendimiento

1. Prepara un recojo con 200 series y abre el detalle.
2. **Esperado**: responde en menos de un segundo y sin una consulta por serie.
3. Abre el listado con 50 recojos.
4. **Esperado**: totales sin una consulta por recojo.
5. Pega 200 series en la vista previa.
6. **Esperado**: respuesta rápida y una sola consulta de existencia.

**Resultado:** x OK  ☐ Falló  Observaciones: ______________________________

---

## 16. Cierre

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

| # | Escenario | Resultado | Evidencia |
|---|---|---|---|
| 1 | Recojo seriado válido | | |
| 2 | Normalización | | |
| 3 | Validación de formato | | |
| 4 | Duplicados | | |
| 5 | Series existentes | | |
| 6 | Todo o nada | | |
| 7 | Vista previa | | |
| 8 | Material no seriado | | |
| 9 | Región y aislamiento | | |
| 10 | Varias líneas | | |
| 11 | Concurrencia | | |
| 12 | Sin borrado | | |
| 13 | Auditoría | | |
| 14 | Tipo inmutable | | |
| 15 | Anulación en 24 h | | |
| 16 | Rendimiento | | |

Cuando termines, registra el resultado en `quickstart.md` y marca **T059**.
