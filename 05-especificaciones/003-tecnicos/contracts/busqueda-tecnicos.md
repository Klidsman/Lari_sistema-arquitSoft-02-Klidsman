# Contrato del fragmento de búsqueda de técnicos

**Fase**: 1 | **Fecha**: 2026-11-12 | **Spec**: `05-especificaciones/003-tecnicos/spec.md`

Contrato de `GET /tecnicos/buscar/` para los módulos que necesitan elegir un técnico del tenant y
completar su NIF en un formulario: specs 005 (stock inicial), 006 (asignación), 009 (traspaso) y
013 (registro de materiales). La spec 010 (conciliación) resuelve NIF del reporte dentro del
tenant, pero no usa el fragmento para operaciones nuevas.

## Petición

| Aspecto | Valor |
|---|---|
| Método | `GET` |
| Autenticación | Cookie de sesión; solo `USUARIO_TENANT` activo |
| Tenant | Se obtiene de la sesión; **no** se acepta `tenant_id` ni `region_id` |
| Parámetros | `q` (texto libre, opcional), `limit` (entero, opcional) |
| `limit` | Por defecto `20`; máximo `50`; valores no numéricos o fuera de rango se acotan |
| `q` vacío | Devuelve los primeros `limit` técnicos activos ordenados por nombre y NIF |
| `q` con texto | Filtra por `nif__icontains` **o** `nombre__icontains` dentro del tenant |
| Filtro de estado | **Siempre** `activo=True`; el fragmento no ofrece desactivados |
| Orden | `nombre` ascendente, `nif` como desempate |
| CSRF | No aplica (`GET`) |

## Respuesta

`200 OK` con `Content-Type: text/html; charset=utf-8` y un fragmento HTML (sin `<html>`,
`<head>` ni `<body>`) que HTMX inserta en el contenedor del consumidor.

Cada resultado es una fila con los tres atributos de datos obligatorios:

| Atributo | Contenido | Ejemplo |
|---|---|---|
| `data-nif` | NIF normalizado de 6 caracteres | `data-nif="LA1234"` |
| `data-nombre` | Nombre normalizado | `data-nombre="Juan Pérez"` |
| `data-activo` | Estado del técnico; el fragmento solo devuelve activos | `data-activo="true"` |

Forma esperada (ilustrativa, no normativa en clases CSS):

```html
<ul class="resultados-tecnicos">
  <li class="resultado-tecnico"
      role="option"
      data-nif="LA1234"
      data-nombre="Juan Pérez"
      data-activo="true">
    <span class="nif">LA1234</span>
    <span class="nombre">Juan Pérez</span>
    <span class="estado">Activo</span>
  </li>
</ul>
```

- Los atributos `data-*` son el contrato; el texto visible puede variar en formato.
- El NIF mostrado al usuario es el mismo que el formulario consumidor usa para autocompletar; no
  se recalcula ni se transforma en el cliente.
- El NIF es inmutable: sirve como clave estable de selección.
- No se devuelve el `id` interno como parte del contrato; si el consumidor necesita la FK, la
  resuelve en el servidor a partir del NIF y del tenant de la sesión.

## Estado vacío y errores

| Caso | Respuesta |
|---|---|
| Sin coincidencias | `200` con "No se encontraron técnicos" dentro del contenedor |
| Tenant sin técnicos activos y `q` vacío | `200` con el mismo estado vacío |
| Sesión ausente | `401` o redirección a `/login/` |
| Sesión `pendiente_2fa` | Redirección a `/login/2fa/`; no devuelve filas |
| Rol `ADMIN` o `ALMACEN` | `403` "No tienes permiso para gestionar técnicos" |
| Tenant suspendido | `403` "El tenant está suspendido" |
| Método distinto de `GET` | `405` |

## Garantías para los consumidores

1. El fragmento nunca devuelve técnicos de otro tenant.
2. El fragmento nunca devuelve `tenant_id`, `region_id`, stock, datos del creador ni documentos
   históricos.
3. Solo devuelve técnicos activos; un técnico desactivado no puede seleccionarse en una operación
   nueva.
4. El consumidor debe revalidar al guardar con `validar_tecnico_para_operacion(tenant, id)`: un
   formulario viejo puede contener un técnico que se desactivó después de abrir la pantalla.
5. El consumidor no debe consultar `Tecnico` directamente sin filtrar por el tenant de la sesión;
   debe usar `tecnicos_para_operacion` y los helpers de `tecnicos/services.py`.
6. El NIF se completa desde el técnico elegido y no se edita en el formulario consumidor.
7. Para documentos históricos que deban mostrar técnicos desactivados (conciliación, logística
   inversa, registro de materiales), el consumidor usa `tecnicos_para_reporte` o una consulta
   filtrada por tenant, **no** este fragmento activo.

## Consumidores y uso previsto

| Spec | Uso |
|---|---|
| 005 Stock inicial | Valida que el NIF exista dentro del tenant; puede usar el selector para cargar líneas |
| 006 Solicitud de asignación | Selector de técnico activo; copia el NIF al Excel y revalida al guardar |
| 009 Traspaso entre técnicos | Selector de origen y destino; ambos activos, del mismo tenant y distintos |
| 010 Conciliación | Resuelve el NIF del reporte dentro del tenant; no usa el fragmento activo para operaciones nuevas |
| 013 Registro de materiales | Órdenes con técnico activo del tenant; conserva la FK histórica aunque se desactive |

## Pruebas de contrato asociadas

- `GET /tecnicos/buscar/?q=LA12` devuelve los técnicos activos del tenant cuyo NIF contiene ese
  texto.
- `GET /tecnicos/buscar/?q=Juan` devuelve los técnicos activos cuyo nombre contiene ese texto.
- `GET /tecnicos/buscar/` con `q` vacío devuelve hasta `limit` técnicos activos ordenados por
  nombre y NIF.
- Un técnico desactivado no aparece aunque coincida con `q`.
- El fragmento no contiene `tenant_id`, `region_id`, stock ni datos del creador.
- La misma consulta desde dos tenants devuelve solo los técnicos de cada uno.
- `limit` se acota a 20 por defecto y 50 como máximo.
- `POST`, `DELETE` u otro método responde `405`.
- `ADMIN` y `ALMACEN` reciben `403`.
- Un formulario viejo con un técnico desactivado se rechaza al guardar en el módulo consumidor.
