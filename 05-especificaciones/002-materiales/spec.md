# Spec: Módulo de materiales (catálogo compartido)

## Trazabilidad
- Historias: HU-xx (completar con los IDs de `02-historias-del-usuario.md`)
- Requisitos: RF-xx (completar con los IDs de `03-requisitos-funcionales.md`)
- Atributos de calidad: integridad de datos, auditabilidad.
  Excepción documentada al aislamiento multitenant (catálogo compartido).

## Dependencias
- Spec 001: cuentas de acceso y región del usuario.
- Reglas: `03-reglas-de-dominio/catalogo-de-materiales.md` y `auditoria.md`.

## Objetivo
Permitir que los usuarios autorizados registren los materiales que Lari
introduce en su almacén central, para que estén disponibles en recojos,
asignaciones y traspasos de todos los tenants.

## Datos del material
| Campo | Obligatorio | Regla |
|---|---|---|
| Código | Sí | Exactamente 11 dígitos. Único en todo el sistema. No editable. |
| Descripción | Sí | Entre 1 y 100 caracteres, sin espacios al inicio o final. |
| Lote | No | Hasta 50 caracteres. Atributo fijo del material; puede quedar vacío. |
| Tipo | Sí | Seriado o No seriado. |
| Estado | Sí | Activo o dado de baja. La baja es lógica: no borra la fila. |

## Reglas de negocio
- El catálogo es compartido: todos los tenants ven los mismos materiales.
  Es la única excepción al aislamiento multitenant.
- Cada material tiene un solo lote. Al elegir un material en cualquier
  formulario, descripción y lote se completan solos y no son editables ahí.
- El lote es informativo: no separa el stock.
- El código no se edita después de creado.
- El sistema registra quién creó el material y cuándo.
- Solo el Responsable de almacén registra materiales.
- Cualquier Responsable de almacén puede dar de baja cualquier material del
  catálogo, aunque lo haya creado otra cuenta.
- Cualquier Responsable de almacén o un administrador de plataforma puede
  editar descripción y lote de cualquier material activo, aunque lo haya creado
  otra cuenta. La cuenta de tenant no edita materiales.
- El tipo no se puede cambiar si el material ya tiene stock o movimientos
  en cualquier tenant.
- Cada alta, cambio y baja queda auditado: usuario, fecha, campo, valor
  anterior y valor nuevo.
- No se borran materiales: se dan de baja lógicamente. La fila, su creador y
  su auditoría se conservan; el material deja de aparecer en listados y búsquedas.
- Si se registra de nuevo un código que pertenece a un material dado de baja, el material
  se reactiva (`activo=True`) y se actualizan descripción, lote y tipo, conservando la misma
  fila y su historial. Se audita la reactivación.
- La búsqueda por código o por descripción devuelve materiales activos de todo el catálogo.

## Criterios de aceptación
- Dado un código nuevo de 11 dígitos con descripción y tipo,
  cuando el usuario guarda el formulario,
  entonces el material aparece en el catálogo con su usuario creador y su fecha.
- Dado el código 10402520279 ya registrado,
  cuando cualquier tenant intenta registrarlo de nuevo,
  entonces se rechaza con "El material ya existe", sin indicar qué tenant lo creó.
- Dado un código de 10 dígitos, de 12 dígitos o con letras,
  cuando se intenta guardar,
  entonces se rechaza con "El código debe tener 11 dígitos".
- Dado el material 10402520323 con lote FIBERHOME,
  cuando un usuario de otro tenant lo busca,
  entonces lo encuentra con su descripción y su lote.
- Dado un material registrado sin lote,
  cuando se guarda,
  entonces el lote queda vacío.
- Dado un material existente,
  cuando un Responsable de almacén cambia la descripción,
  entonces el cambio se guarda y queda registrado el valor anterior y el nuevo.
- Dada una cuenta de tenant,
  cuando intenta editar la descripción o el lote,
  entonces la acción no está disponible y el servidor la rechaza si se fuerza.
- Dado un material existente,
  cuando el usuario intenta cambiar el código,
  entonces el campo no es editable.
- Dado un material con stock o movimientos,
  cuando se intenta cambiar de seriado a no seriado o al revés,
  entonces el cambio se rechaza con "El tipo no se puede cambiar: el material tiene movimientos".
- Dado una descripción formada solo por espacios,
  cuando se guarda,
  entonces se rechaza con "La descripción es obligatoria".
- Dado un doble clic en Guardar,
  cuando la primera petición ya creó el material,
  entonces la segunda se rechaza con "El material ya existe" y no se crea un duplicado.
- Dado el texto "ROSETA" en la búsqueda,
  entonces aparece el material 10402520279 con su descripción y su lote.
- Dada una cuenta de tenant o un Administrador de plataforma,
  cuando intenta registrar un material,
  entonces el servidor rechaza la operación porque solo el Responsable de almacén crea materiales.
- Dado un material activo y un Responsable de almacén,
  cuando lo da de baja,
  entonces el material deja de aparecer en el catálogo y la búsqueda, la fila se conserva
  y la baja queda auditada con valor anterior y nuevo.
- Dado un material ya dado de baja,
  cuando se intenta dar de baja de nuevo,
  entonces no se modifica ni se audita otra vez.
- Dado un material dado de baja, cuando el Responsable de almacén registra un material con
  ese mismo código, entonces el material se reactiva con los nuevos datos y la reactivación
  queda auditada, sin crear una fila duplicada.

## Casos borde
- Espacios al inicio, al final o repetidos dentro de descripción y lote.
- Lote en minúsculas: se guarda normalizado (ver supuestos).
- Código con espacios o guiones dentro de los 11 dígitos.
- Búsqueda con texto vacío: devuelve el listado sin filtrar, paginado.
- Material creado por un usuario que luego se desactiva: el material se conserva.

## Supuestos a confirmar
1. El lote se guarda en mayúsculas, porque así llega desde Lari.
2. Límites: descripción de 100 caracteres y lote de 50. Ajustar si Lari usa más.
3. "Administrador de plataforma" es el rol definido en la spec 001.

## Fuera de alcance
- Carga masiva de materiales por Excel.
- Borrado físico de materiales (solo existe baja lógica).
- Cambio de código.
- Varios lotes por material.
- Detección de descripciones parecidas con códigos distintos (mejora posterior).
- Aprobación de materiales nuevos por un administrador antes de visibilidad.