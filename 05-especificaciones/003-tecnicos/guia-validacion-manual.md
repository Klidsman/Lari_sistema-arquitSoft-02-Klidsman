# Guía de validación manual — 003 Técnicos

> **Estado**: ejecutada el 2026-11-16. Los 16 escenarios se completaron con los resultados
> esperados. El registro oficial está en `quickstart.md`, sección «Registro de validación
> manual». Esta guía queda como referencia para futuras revalidaciones.

**Propósito**: ejecutar los escenarios 1–16 de
`05-especificaciones/003-tecnicos/quickstart.md` (tarea **T054**) sobre PostgreSQL y navegador.

**Prerrequisito**: entorno de la spec 001 levantado (`runserver`, PostgreSQL y Redis) y, para
probar permisos, un Administrador y un Responsable de almacén.

> Todos los comandos se ejecutan desde la raíz del repositorio.

---

## 0. Preparación

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe -m pytest -q
```

Debe terminar en **349 passed**.

Datos mínimos:

1. Región con almacén.
2. Tenant A con su cuenta activa (`USUARIO_TENANT`).
3. Tenant B con su cuenta activa.
4. Administrador de plataforma con sesión iniciada.
5. Responsable de almacén con sesión iniciada.

---

## 1. Alta de técnico

1. Inicia sesión con la cuenta del tenant A.
2. Abre `http://localhost:8000/tecnicos/nuevo/`.
3. Registra NIF `LA1234` y nombre `Juan Pérez`.
4. **Esperado**: redirección al detalle; el técnico aparece como Activo en `/tecnicos/`.
5. Abre `/auditoria/acceso/?entidad=Tecnico` como Administrador.
6. **Esperado**: registro `alta` con NIF, nombre y `estado=ACTIVO`.

Verificación:

```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from tecnicos.models import Tecnico; t=Tecnico.objects.get(nif='LA1234'); print(t.tenant.codigo, t.nombre, t.activo, t.creado_por.email)"
```

**Resultado:** x OK  ☐ Falló  Observaciones: ______________________________

---

## 2. Formato y normalización del NIF

1. Intenta guardar: `LA123`, `LA12345`, `A1234`, `LA12A4`, `LA 1234` y `LA-1234`.
2. **Esperado**: `El NIF debe tener el formato LAXXXX` en todos.
3. Guarda `la1234` y luego ` LA1234 `.
4. **Esperado**: se normaliza a `LA1234` y se guarda.

**Resultado:** X OK  ☐ Falló  Observaciones: ______________________________

---

## 3. NIF único y doble envío

1. Vuelve a registrar `LA1234` en el tenant A.
2. **Esperado**: `409` `El NIF ya está registrado`.
3. Inicia sesión con el tenant B e intenta registrar `LA1234`.
4. **Esperado**: el mismo mensaje, sin revelar el tenant propietario.
5. Con un NIF nuevo, haz doble clic en Guardar.
6. **Esperado**: una sola fila; la segunda petición recibe `El NIF ya está registrado`.

**Resultado:** X OK  ☐ Falló  Observaciones: ______________________________

---

## 4. NIF de un técnico desactivado

1. Desactiva un técnico con NIF `LA5678` del tenant A.
2. Intenta crear otro con `LA5678` en el tenant A.
3. **Esperado**: `El NIF ya está registrado; reactiva el técnico existente`.
4. Desde el tenant B, intenta crear `LA5678`.
5. **Esperado**: `El NIF ya está registrado`, sin sugerencia de reactivación.

**Resultado:** X OK  ☐ Falló  Observaciones: ______________________________

---

## 5. Validación del nombre

1. Intenta con nombre vacío y solo espacios.
2. **Esperado**: `El nombre es obligatorio`.
3. Intenta con 101 caracteres.
4. **Esperado**: `El nombre no puede superar los 100 caracteres`.
5. Registra `  Juan   Pérez  `.
6. **Esperado**: se guarda `Juan Pérez`.
7. Registra dos técnicos distintos con el mismo nombre.
8. **Esperado**: se permite; el nombre no es único.

**Resultado:** X OK  ☐ Falló  Observaciones: ______________________________

---

## 6. Edición e inmutabilidad

1. Abre un técnico y cambia el nombre.
2. **Esperado**: se guarda y la auditoría muestra valor anterior y nuevo.
3. Comprueba que NIF y tenant son solo lectura.
4. Fuerza `POST` con `nif=LA9999`.
5. **Esperado**: `400` `El NIF no se puede cambiar`.
6. Fuerza `tenant_id` de otro tenant.
7. **Esperado**: `400` `El tenant del técnico no se puede cambiar`.
8. Guarda sin cambiar el nombre.
9. **Esperado**: no se crea auditoría nueva.

**Resultado:** X OK  ☐ Falló  Observaciones: ______________________________

---

## 7. Desactivación y conservación

1. Desactiva un técnico activo con el botón **Desactivar**.
2. **Esperado**: estado Desactivado y auditoría `ACTIVO → DESACTIVADO`.
3. Busca su NIF en `/tecnicos/buscar/`.
4. **Esperado**: no aparece en el selector de operaciones nuevas.
5. Abre su detalle.
6. **Esperado**: sus datos y auditoría siguen visibles.
7. Repite la desactivación.
8. **Esperado**: sin cambio ni auditoría duplicada.
9. Verifica que no se borró la fila.
10. **Esperado**: el registro persiste.

**Resultado:** X OK  ☐ Falló  Observaciones: ______________________________

---

## 8. Reactivación

1. Abre un técnico desactivado y pulsa **Reactivar**.
2. **Esperado**: vuelve a Activo y se audita `DESACTIVADO → ACTIVO`.
3. Búscalo en `/tecnicos/buscar/`.
4. **Esperado**: reaparece en el selector.
5. Repite la reactivación.
6. **Esperado**: sin cambio ni auditoría nueva.

**Resultado:** X OK  ☐ Falló  Observaciones: ______________________________

---

## 9. Búsqueda y listado por tenant

1. Con el tenant A, busca `LA1234` y `Juan`.
2. **Esperado**: aparecen solo técnicos del tenant A.
3. Con el tenant B, repite la búsqueda.
4. **Esperado**: no aparecen técnicos del tenant A.
5. Deja la búsqueda vacía.
6. **Esperado**: listado del tenant, paginado a 50 y ordenado por nombre/NIF.
7. Prueba el filtro Activos/Desactivados/Todos.
8. **Esperado**: cada filtro muestra el estado correspondiente.

**Resultado:** X OK  ☐ Falló  Observaciones: ______________________________

---

## 10. Aislamiento y accesos forzados

1. Con el tenant B, abre por URL directa el detalle, edición, desactivación y reactivación de un
   técnico del tenant A.
2. **Esperado**: `404` `El técnico no existe` en todas, sin revelar datos.
3. Envía `tenant_id` del tenant A al crear o editar.
4. **Esperado**: se ignora o se rechaza; el técnico queda en el tenant de la sesión.

**Resultado:** X OK  ☐ Falló  Observaciones: ______________________________

---

## 11. Permisos de Administrador y Responsable de almacén

1. Como Administrador, intenta crear, editar, desactivar y reactivar por URL directa.
2. **Esperado**: `403` `No tienes permiso para gestionar técnicos` en todas.
3. Repite con el Responsable de almacén.
4. **Esperado**: el mismo `403`; tampoco ve el listado completo.

**Resultado:** X OK  ☐ Falló  Observaciones: ______________________________

---

## 12. Tenant suspendido y cuenta inactiva

1. Suspende el tenant A desde la administración de la spec 001.
2. Intenta operar con su cuenta.
3. **Esperado**: se le impide la sesión o recibe `403` `El tenant está suspendido`.
4. Reactiva el tenant.
5. **Esperado**: los técnicos y su auditoría se conservan y la cuenta vuelve a operar.

**Resultado:** X OK  ☐ Falló  Observaciones: ______________________________

---

## 13. Formulario viejo con técnico desactivado

1. Este caso depende de un módulo consumidor (005/006/009/013), aún no implementado.
2. Puede validarse a nivel de servicio:

```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from tenants.models import Tenant; from tecnicos.models import Tecnico; from tecnicos.services import validar_tecnico_para_operacion, TecnicoNoDisponible; t=Tecnico.objects.get(nif='LA5678'); 
try:
    validar_tecnico_para_operacion(t.tenant, t.pk)
    print('ERROR: permitió operar')
except TecnicoNoDisponible as e:
    print('OK:', e)"
```

3. **Esperado**: `OK: El técnico está desactivado`.

**Resultado:** X OK  ☐ Falló  Observaciones: ______________________________

---

## 14. Sin eliminación e idempotencia

1. Con sesión de tenant, envía `DELETE` a `/tecnicos/<id>/` y `/tecnicos/<id>/editar/`.
2. **Esperado**: `405`.
3. Envía `GET` a `/tecnicos/<id>/desactivar/` y `/tecnicos/<id>/reactivar/`.
4. **Esperado**: `405`.

Puedes usar la cookie de sesión desde DevTools:

```powershell
curl.exe -i -X DELETE "http://localhost:8000/tecnicos/1/" `
  -H "Cookie: sessionid=<tu-sessionid>"
```

**Resultado:** X OK  ☐ Falló  Observaciones: ______________________________

---

## 15. Auditoría

1. Abre `/auditoria/acceso/?entidad=Tecnico` como Administrador.
2. **Esperado**: registros `alta`, `nombre` y `activo`.
3. Inspecciona que el alta incluya NIF, nombre y `estado=ACTIVO`.
4. Comprueba que no haya contraseñas, tokens ni secretos ni `tenant_id`:

```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from auditoria.models import RegistroCambio; prohibidos=('password','contraseña','token','secreto','tenant_id'); malos=[(r.pk,r.campo) for r in RegistroCambio.objects.filter(entidad='Tecnico') if any(p in (r.campo+' '+r.valor_anterior+' '+r.valor_nuevo).lower() for p in prohibidos)]; print('sospechosos=', malos)"
```

5. **Esperado**: `sospechosos= []`.
6. Repite desactivación y reactivación.
7. **Esperado**: no se agregan registros por las repeticiones.

**Resultado:** X OK  ☐ Falló  Observaciones: ______________________________

---

## 16. Concurrencia

1. En dos ventanas de incógnito, con la misma cuenta del tenant, prepara el alta del mismo NIF.
2. Envía ambas casi al mismo tiempo.
3. **Esperado**: una tiene éxito y la otra recibe `El NIF ya está registrado`.
4. Confirma una sola fila:

```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from tecnicos.models import Tecnico; print(Tecnico.objects.filter(nif='<nif-prueba>').count())"
```

**Resultado:** X OK  ☐ Falló  Observaciones: ______________________________

---

## 17. Cierre

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

| # | Escenario | Resultado | Evidencia |
|---|---|---|---|
| 1 | Alta de técnico | | |
| 2 | Formato y normalización del NIF | | |
| 3 | NIF único y doble envío | | |
| 4 | NIF de desactivado | | |
| 5 | Validación del nombre | | |
| 6 | Edición e inmutabilidad | | |
| 7 | Desactivación y conservación | | |
| 8 | Reactivación | | |
| 9 | Búsqueda y listado | | |
| 10 | Aislamiento | | |
| 11 | Permisos | | |
| 12 | Tenant suspendido | | |
| 13 | Formulario viejo | | |
| 14 | Sin eliminación | | |
| 15 | Auditoría | | |
| 16 | Concurrencia | | |

Cuando termines, registra el resultado en `quickstart.md` y marca **T054** en `tasks.md`.
