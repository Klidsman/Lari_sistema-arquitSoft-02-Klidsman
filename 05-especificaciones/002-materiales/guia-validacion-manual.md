# Guía de validación manual — 002 Materiales

> **Estado**: ejecutada el 2026-11-14. Los 11 escenarios se completaron con los resultados
> esperados. El registro oficial está en `quickstart.md`, sección «Registro de validación
> manual». Esta guía queda como referencia para futuras revalidaciones.

**Propósito**: ejecutar los escenarios 1–11 de
`05-especificaciones/002-materiales/quickstart.md` (tarea **T047**) sobre PostgreSQL y navegador.

**Prerrequisito**: entorno de la spec 001 ya levantado (`runserver`, PostgreSQL y Redis). Si no,
sigue primero `05-especificaciones/001-tenants-y-acceso/guia-validacion-manual.md`.

> Todos los comandos se ejecutan desde la raíz del repositorio.

---

## 0. Preparación

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe -m pytest -q
```

Debe terminar en **214 passed**.

Necesitas:

1. Un Administrador de plataforma con TOTP (spec 001).
2. La cuenta activa de un tenant A (solo consulta).
3. La cuenta activa de un tenant B (otro tenant, solo consulta).
4. Una cuenta activa de **Responsable de almacén** (crea y da de baja materiales).
5. Opcionalmente, una segunda cuenta de Responsable de almacén en otra región para validar la
   baja de materiales ajenos.
6. Al menos una región, un almacén y los dos tenants creados desde la interfaz de la spec 001.

Arranca el servidor:

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

---

## 1. Alta de material

1. Inicia sesión con la cuenta del **Responsable de almacén**.
2. Abre `http://localhost:8000/materiales/nuevo/`.
3. Registra: código `10402520279`, descripción `ROSETA`, lote `FIBERHOME`, tipo `Seriado`.
4. **Esperado**: `302` al listado; el material aparece con creador y fecha.
5. Abre `/auditoria/acceso/?entidad=Material` como Administrador.
6. **Esperado**: registro `alta` con `codigo`, `descripcion`, `lote` y `tipo`.

Verificación rápida:

```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from materiales.models import Material; m=Material.objects.get(codigo='10402520279'); print(m.codigo, m.descripcion, m.lote, m.tipo, m.creado_por.email, m.creado_en)"
```

**Resultado:** x OK  ☐ Falló  Observaciones: ______________________________

---

## 2. Código de 11 dígitos obligatorio

En `/materiales/nuevo/` intenta guardar, uno por uno:

| Código | Esperado |
|---|---|
| `1040252027` | `El código debe tener 11 dígitos` |
| `104025202799` | `El código debe tener 11 dígitos` |
| `10402520A79` | `El código debe tener 11 dígitos` |
| `1040 2520279` | `El código debe tener 11 dígitos` |
| `1040-2520279` | `El código debe tener 11 dígitos` |

**Resultado:** x OK  ☐ Falló  Observaciones: ______________________________

---

## 3. Código único y doble clic

1. Como almacén, vuelve a registrar `10402520279`.
2. **Esperado**: `409` con `El material ya existe`, sin mencionar cuenta ni tenant.
3. Con una segunda cuenta de Responsable de almacén (otra región), intenta registrar el mismo
   código.
4. **Esperado**: el mismo mensaje uniforme; el catálogo es global.
5. Cierra sesión e inicia con la cuenta del tenant A o con el Administrador.
6. Abre `/materiales/nuevo/`.
7. **Esperado**: `403`; solo el Responsable de almacén crea materiales.
8. Vuelve a la cuenta de almacén y, con un código nuevo, haz doble clic rápido en **Guardar**.
9. **Esperado**: se crea una sola fila; la segunda petición recibe `El material ya existe`.

Verificación:

```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from materiales.models import Material; print('cantidad=', Material.objects.filter(codigo='10402520279').count())"
```

**Resultado:** x OK  ☐ Falló  Observaciones: ______________________________

---

## 4. Normalización de descripción y lote

1. Registra un material con descripción `  ROSETA   ÓPTICA  ` y lote ` fiberhome `.
2. **Esperado**: se guarda `ROSETA ÓPTICA` y `FIBERHOME`.
3. Intenta una descripción formada solo por espacios.
4. **Esperado**: `La descripción es obligatoria`.
5. Registra un material sin lote.
6. **Esperado**: lote vacío y el material aparece igualmente en el listado y la búsqueda.

**Resultado:** x OK  ☐ Falló  Observaciones: ______________________________

---

## 5. Catálogo compartido

1. Con el tenant A, busca `10402520279` en `/materiales/`.
2. **Esperado**: aparece con descripción y lote.
3. Cierra sesión e inicia con el tenant B.
4. Repite la búsqueda.
5. **Esperado**: exactamente el mismo material y datos; no se filtra por tenant.

**Resultado:** ☐ OK  ☐ Falló  Observaciones: ______________________________

---

## 6. Búsqueda

1. Busca `ROSETA` en `/materiales/`.
2. **Esperado**: aparece `10402520279` con su descripción y lote.
3. Abre `http://localhost:8000/materiales/buscar/?q=ROSETA`.
4. **Esperado**: fragmento HTML con `data-codigo`, `data-descripcion`, `data-lote` y `data-tipo`.
5. Busca `1040252` (código parcial).
6. **Esperado**: aparecen los materiales cuyo código contiene ese texto.
7. Deja la búsqueda vacía.
8. **Esperado**: listado completo, paginado a 50 filas.
9. Prueba `?limit=999` en el fragmento.
10. **Esperado**: como máximo 50 filas.

**Resultado:** x OK  ☐ Falló  Observaciones: ______________________________

---

## 7. Edición y permisos

1. Como Responsable de almacén (aunque el material lo haya creado otra cuenta), abre
   `/materiales/<id>/editar/` y cambia la descripción.
2. **Esperado**: se guarda; la auditoría muestra valor anterior y nuevo.
3. Inicia sesión con una cuenta de tenant (nunca puede editar materiales).
4. Fuerza la URL `/materiales/<id>/editar/`.
5. **Esperado**: `403` `No tienes permiso para editar este material`.
6. Como Administrador de plataforma, edita la descripción.
7. **Esperado**: se permite y se audita.
8. Comprueba que el formulario no muestra el campo código.
9. Fuerza un `POST` con `codigo=99999999999`.
10. **Esperado**: `400` `El código no se puede cambiar`; el material conserva su código.

Verificación de auditoría:

```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from auditoria.models import RegistroCambio; print(list(RegistroCambio.objects.filter(entidad='Material').values_list('campo','valor_anterior','valor_nuevo')))"
```

**Resultado:** ☐ OK  ☐ Falló  Observaciones: ______________________________

---

## 8. Tipo inmutable con movimientos

1. Con un material sin movimientos, cambia de `Seriado` a `No seriado`.
2. **Esperado**: se permite y se audita `tipo` con valor anterior y nuevo.
3. Como aún no existen tablas de stock (specs 004+), simula una verificación de movimientos en
   consola:

```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from materiales import services; from materiales.models import Material; from acceso.models import Usuario; m=Material.objects.get(codigo='10402520279'); a=Usuario.objects.get(email='admin@lari.local'); baja=services.registrar_verificacion_movimientos(lambda material: True); 
try:
    services.actualizar_material(m, {'tipo': 'SERIADO' if m.tipo == 'NO_SERIADO' else 'NO_SERIADO'}, a)
    print('ERROR: permitió el cambio')
except services.ValidacionMaterial as e:
    print('OK:', e)
finally:
    baja()"
```

4. **Esperado**: `OK: El tipo no se puede cambiar: el material tiene movimientos`.
5. Confirma que el tipo no cambió y que no hay auditoría nueva de `tipo`.

> Este caso también está cubierto por `tests/integration/test_material_tipo.py`, porque la
> verificación debe vivir en el mismo proceso que la petición.

**Resultado:** X OK  ☐ Falló  Observaciones: ______________________________

---

## 9. Baja lógica, sin eliminación y conservación

1. Como Responsable de almacén, abre `/materiales/` y pulsa **Dar de baja** sobre un material.
2. **Esperado**: `302`; el material desaparece del listado y de la búsqueda; en base de datos
   queda `activo=False`; la auditoría registra `activo` de `True` a `False`.
3. Repite la baja del mismo material (por URL o consola).
4. **Esperado**: `200`, sin cambios ni auditoría nueva (idempotente).
5. Con una segunda cuenta de almacén, da de baja un material creado por la primera.
6. **Esperado**: se permite; cualquier almacén puede dar de baja cualquier material.
7. Como tenant o Administrador, intenta dar de baja.
8. **Esperado**: `403`.
9. Prueba `DELETE` (copia tu cookie `sessionid` desde DevTools):

```powershell
curl.exe -i -X DELETE "http://localhost:8000/materiales/1/editar/" `
  -H "Cookie: sessionid=<tu-sessionid>"
```

10. **Esperado**: `405`; no existe borrado físico.
11. Vuelve a registrar el mismo código desde `/materiales/nuevo/` con datos nuevos.
12. **Esperado**: no se crea otra fila; el material se reactiva (`activo=True`) con los nuevos
    datos y la reactivación queda auditada.
13. Desactiva la cuenta creadora desde `/plataforma/cuentas/`.
14. **Esperado**: el material y su auditoría permanecen en la base.

Verificación:

```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from materiales.models import Material; m=Material.objects.get(codigo='10402520279'); print('activo=', m.activo, 'existe=', True)"
```

**Resultado:** X OK  ☐ Falló  Observaciones: ______________________________

---

## 10. Auditoría

1. Abre `/auditoria/acceso/?entidad=Material` como Administrador.
2. **Esperado**: altas, un registro por cada campo modificado (`descripcion`, `lote`, `tipo`) y
   un registro `activo` por cada baja.
3. Inspecciona que el alta incluya código, descripción, lote y tipo, y no incluya `tenant_id`.
4. Comprueba que no haya contraseñas, tokens ni secretos:

```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from auditoria.models import RegistroCambio; prohibidos=('password','contraseña','token','secreto'); malos=[(r.pk,r.campo) for r in RegistroCambio.objects.filter(entidad='Material') if any(p in (r.campo+' '+r.valor_anterior+' '+r.valor_nuevo).lower() for p in prohibidos)]; print('sospechosos=', malos)"
```

5. **Esperado**: `sospechosos= []`.

**Resultado:** X OK  ☐ Falló  Observaciones: ______________________________

---

## 11. Concurrencia

1. Abre dos ventanas de incógnito, ambas con la misma cuenta de Responsable de almacén.
2. Prepara el alta del mismo código nuevo en ambas.
3. Envía las dos casi al mismo tiempo.
4. **Esperado**: una alta tiene éxito y la otra recibe `El material ya existe`.
5. Confirma que existe una sola fila:

```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from materiales.models import Material; print(Material.objects.filter(codigo='<codigo-prueba>').count())"
```

**Resultado:** X OK  ☐ Falló  Observaciones: ______________________________

---

## 12. Cierre

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

| # | Escenario | Resultado | Evidencia |
|---|---|---|---|
| 1 | Alta de material | | |
| 2 | Código de 11 dígitos | | |
| 3 | Código único y doble clic | | |
| 4 | Normalización | | |
| 5 | Catálogo compartido | | |
| 6 | Búsqueda | | |
| 7 | Edición y permisos | | |
| 8 | Tipo inmutable | | |
| 9 | Baja lógica y conservación | | |
| 10 | Auditoría | | |
| 11 | Concurrencia | | |

Cuando termines, registra el resultado en `quickstart.md` (sección **Criterios de salida**) y
marca **T047** en `tasks.md`.
