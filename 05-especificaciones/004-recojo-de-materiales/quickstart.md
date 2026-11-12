# Quickstart y validación: 004 Recojo de materiales

**Fase**: 1 | **Fecha**: 2026-11-12 | **Spec**: `05-especificaciones/004-recojo-de-materiales/spec.md`

Guía para levantar el proyecto y validar de extremo a extremo el recojo de materiales: formulario
con varias líneas, materiales seriados y no seriados, normalización y vista previa de series,
rechazo de series inválidas/duplicadas/existentes, regla todo o nada, incremento del stock general,
aislamiento por tenant y auditoría. Los detalles de datos están en `data-model.md` y los contratos
en `contracts/`. Esta guía no contiene código de implementación.

## Prerrequisitos

- Python 3.12 o superior.
- PostgreSQL 16 o superior.
- Redis 7 o superior (broker de Celery de la spec 001).
- Spec 001 implementada: `acceso.Usuario`, `ContextoUsuarioMiddleware`, `tenants.Tenant`,
  `tenants.Region`, `tenants.Almacen` y `auditoria.RegistroCambio` con `registrar_cambio`.
- Spec 002 implementada: `materiales.Material` con búsqueda y tipos seriado/no seriado.
- Parte fundacional de la spec 008 implementada: `stock.StockGeneral` y
  `stock.services.incrementar_stock_general`. Sin esta parte, 004 no puede guardar stock.
- Git y acceso al repositorio.
- En Windows, PowerShell 7 o superior; en Linux/macOS, bash.

> La spec 003 (técnicos) **no** es un prerrequisito de 004: el recojo es del tenant y no referencia
> técnicos. Si se implementa 004 antes de 003, no hay dependencia pendiente.

## Configuración inicial

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

En Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

Variables de entorno y base de datos: las mismas de
`05-especificaciones/001-tenants-y-acceso/quickstart.md`. No se agregan variables nuevas para
esta spec, salvo las opcionales de formato de serie:

| Variable | Valor por defecto | Uso |
|---|---|---|
| `SERIE_LONGITUD` | `12` | Longitud esperada de la serie |
| `SERIE_PATRON` | `^[A-Z0-9]{12}$` | Patrón de validación |

## Puesta en marcha

```powershell
python manage.py migrate
python manage.py runserver
```

`migrate` aplica `series/migrations/0001_initial.py` y `recojos/migrations/0001_initial.py`. La app
`stock` y `materiales` deben haber migrado antes.

Datos mínimos para las pruebas manuales (crear desde la interfaz de las specs 001 y 002):

1. Una región `Ayacucho` con su almacén central.
2. Un tenant `AYA-01` de esa región y su cuenta activa.
3. Un segundo tenant `AYA-02` de la misma región y su cuenta activa.
4. Un tercer tenant de otra región, si se quiere probar un intento de cruce.
5. Un Administrador de plataforma con segundo factor.
6. Un Responsable de almacén de Ayacucho.
7. Material seriado `10402520279` (`ROSETA`, lote `FIBERHOME`).
8. Material no seriado `10402520323` (`CABLE`, lote `FIBERHOME`).
9. Una serie ya existente `XYZ987654321` en el tenant `AYA-02`, para probar `ya_existe`; se crea
   registrando previamente un recojo en `AYA-02` con esa serie.

## Pruebas automatizadas

```powershell
# Toda la suite
pytest

# Solo este módulo
pytest tests/unit tests/integration tests/contract -k "recojo or serie"

# Con cobertura de las apps nuevas
pytest --cov=recojos --cov=series
```

Las pruebas requieren PostgreSQL (no SQLite) porque validan `CheckConstraint` con expresión regular,
unicidad global, concurrencia real y transacciones anidadas con el servicio de stock.

## Escenarios de validación manual

### 1. Recojo seriado válido (CA-02)

1. Iniciar sesión con la cuenta del tenant `AYA-01`.
2. Ir a `/recojos/nuevo/`.
3. Elegir el material seriado `10402520279`; verificar que tipo `Seriado` y lote `FIBERHOME` se
   muestran como solo lectura.
4. Pegar tres series válidas, una por línea: `ABC123456789`, `DEF123456789`, `GHI123456789`.
5. **Esperado**: la vista previa muestra las tres como `Válida`; Guardar redirige al detalle.
6. **Esperado**: el detalle muestra fecha, tenant, región `Ayacucho`, total de series 3, total de
   cantidad 0 y las tres series.
7. Consultar el stock general del tenant para el material: aumentó en 3.
8. Consultar `series.Serie`: las tres están en estado `DISPONIBLE`, con el tenant y la región
   correctos.
9. Consultar la auditoría: hay un registro `Recojo/alta` y un registro `StockGeneral/cantidad` con
   valor anterior y nuevo.

### 2. Normalización de series (CA-03)

1. En una línea seriada, ingresar `abc123456789`.
2. **Esperado**: la vista previa muestra `ABC123456789` como `Válida`.
3. Ingresar `" abc 123456789 "`.
4. **Esperado**: también se normaliza a `ABC123456789`; la vista previa lo muestra así.
5. Guardar y verificar que la serie persistida es la normalizada.

### 3. Validación de formato (CA-04)

1. Ingresar `ABC123` (6 caracteres), `ABC12345678` (11), `ABC1234567890` (13) y `ABC-12345678`.
2. **Esperado**: todos se marcan como `Inválida` con "La serie debe tener 12 caracteres
   alfanuméricos".
3. Intentar guardar con una línea inválida.
4. **Esperado**: no se guarda ningún recojo; el formulario vuelve con el error.

### 4. Duplicados en el mismo recojo (CA-05)

1. Ingresar `ABC123456789` dos veces en la misma línea o en dos líneas del mismo recojo.
2. **Esperado**: la segunda ocurrencia se marca `Duplicada`; la primera sigue `Válida`.
3. Intentar guardar.
4. **Esperado**: no se guarda nada y se muestra "La serie está duplicada en el recojo".

### 5. Series existentes en el sistema (CA-06)

1. Con la cuenta del tenant `AYA-01`, ingresar `XYZ987654321` (serie del tenant `AYA-02`).
2. **Esperado**: la vista previa la marca `Ya existe` y muestra "La serie ya está registrada en el
   sistema", sin indicar el tenant, la región ni el recojo de origen.
3. Intentar guardar.
4. **Esperado**: no se guarda nada; el mensaje es uniforme.
5. Repetir desde la cuenta de `AYA-02` con la misma serie.
6. **Esperado**: el mismo estado y mensaje; no se revela el propietario.

### 6. Regla todo o nada (CA-07)

1. Preparar 10 series válidas y una inválida en el mismo recojo.
2. Intentar guardar.
3. **Esperado**: no se crea ningún `Recojo`, ninguna `LineaRecojo`, ninguna `Serie` y el stock no
   cambia; tampoco se escribe auditoría de recojo ni de stock.
4. Corregir la serie inválida y guardar.
5. **Esperado**: se guarda el recojo completo con las 10 series válidas.

### 7. Vista previa en tiempo real (CA-08)

1. Pegar un bloque de varias series en el campo de series.
2. **Esperado**: sin recargar la página, la vista previa muestra una fila por serie con su estado.
3. Escanear una serie con el lector de código de barras (el lector se comporta como teclado).
4. **Esperado**: la serie aparece en la vista previa con su estado.
5. Corregir una serie inválida y volver a validar.
6. **Esperado**: la vista previa se actualiza y la serie pasa a `Válida`.

### 8. Recojo de material no seriado (CA-09)

1. Elegir el material no seriado `10402520323`; verificar tipo `No seriado` y lote de solo lectura.
2. Ingresar cantidad `25`.
3. **Esperado**: el campo de series no se muestra; Guardar redirige al detalle.
4. **Esperado**: el detalle muestra total de cantidad 25 y total de series 0.
5. Verificar que el stock general del material aumentó en 25 y que no se creó ninguna `Serie`.

### 9. Restricción de región y aislamiento (CA-01)

1. Con la cuenta de `AYA-01`, registrar un recojo.
2. **Esperado**: el recojo y sus series tienen la región `Ayacucho`, derivada del tenant.
3. Forzar en la petición `region_id` de otra región y `tenant_id` de otro tenant.
4. **Esperado**: el recojo se guarda con el tenant y la región de la sesión; los valores forzados se
   ignoran.
5. Con la cuenta de `AYA-02`, intentar abrir el detalle del recojo de `AYA-01` por URL directa.
6. **Esperado**: `404` "El recojo no existe".
7. Iniciar sesión como Administrador de plataforma y como Responsable de almacén e intentar abrir
   `/recojos/` y `/recojos/nuevo/`.
8. **Esperado**: `403` "No tienes permiso para registrar recojos".

### 10. Varias líneas y varios materiales

1. Registrar un recojo con una línea del material seriado (2 series) y una línea del material no
   seriado (cantidad 10).
2. **Esperado**: el detalle muestra dos líneas, total de series 2 y total de cantidad 10.
3. Verificar que el stock general de cada material aumentó en su cantidad correspondiente.
4. Verificar que la auditoría de stock tiene un registro por material, no uno por serie.

### 11. Concurrencia de series

1. En dos sesiones del mismo tenant, preparar un recojo con la misma serie nueva.
2. Guardar ambas al mismo tiempo.
3. **Esperado**: una sesión guarda el recojo; la otra no guarda nada y recibe "La serie ya está
   registrada en el sistema".
4. Verificar que existe una sola `Serie` y un solo recojo con esa serie.

### 12. Inmutabilidad y ausencia de borrado

1. Abrir el detalle de un recojo.
2. **Esperado**: no hay botón ni enlace de edición o borrado.
3. Enviar `DELETE` a `/recojos/<id>/` y a `/recojos/nuevo/`.
4. **Esperado**: `405`.
5. Verificar que no existe una ruta de edición.

### 13. Auditoría

1. Abrir la consulta de auditoría administrativa de la spec 001 (o consultar
   `auditoria.RegistroCambio`).
2. **Esperado**: hay un registro `entidad="Recojo"`, `campo="alta"` con fecha, región, líneas,
   series y cantidad.
3. **Esperado**: hay registros `entidad="StockGeneral"`, `campo="cantidad"` con valor anterior y
   nuevo por cada material incrementado.
4. Inspeccionar los registros.
5. **Esperado**: no contienen contraseñas, tokens ni secretos; no incluyen `tenant_id` separado ni
   la lista completa de series.
6. Intentar un recojo con una serie inválida y verificar que no se agregó auditoría.

### 14. Tipo de material inmutable con movimientos

1. Después de un recojo del material seriado, intentar cambiar su tipo a no seriado desde la
   pantalla de edición de la spec 002.
2. **Esperado**: `"El tipo no se puede cambiar: el material tiene movimientos"`.
3. Repetir con un material sin recojos ni stock.
4. **Esperado**: el cambio de tipo se permite (regla de 002).

### 15. Rendimiento y ausencia de N+1

1. Preparar un recojo con 200 series y abrir su detalle.
2. **Esperado**: el detalle responde en menos de un segundo y no ejecuta una consulta por serie.
3. Abrir el listado con 50 recojos.
4. **Esperado**: los totales se muestran sin una consulta por recojo.
5. En la vista previa, pegar 200 series.
6. **Esperado**: la respuesta llega en menos de un segundo y usa una sola consulta de existencia.

## Criterios de salida

La funcionalidad se considera validada cuando:

- [ ] `pytest` pasa completo sobre PostgreSQL.
- [ ] Cada criterio de aceptación CA-01…CA-09 tiene al menos una prueba automatizada.
- [ ] Los escenarios manuales 1–15 se completan con los resultados esperados.
- [ ] Un recojo se guarda completo o no se guarda; no hay estados parciales.
- [ ] Las series se normalizan y validan antes de escribir; la unicidad global se impone en la
      base.
- [ ] El stock general sube con cada recojo y no se modifica por otra vía en esta spec.
- [ ] Las series creadas quedan `DISPONIBLE`, con el tenant y la región de la sesión.
- [ ] Un recojo de otro tenant se trata como inexistente y no se revela información ajena.
- [ ] Solo la cuenta del tenant registra y consulta recojos.
- [ ] No existe edición ni borrado de recojos; `DELETE` responde `405`.
- [ ] La auditoría de recojo y stock se escribe en la misma transacción, sin secretos.
- [ ] El tipo de un material con recojos o stock no se puede cambiar.
- [ ] La vista previa no escribe en la base y no revela datos de otros tenants.
