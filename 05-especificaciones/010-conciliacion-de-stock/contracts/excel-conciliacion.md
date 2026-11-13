# Contrato: lectura del Excel de conciliación

Este contrato concreta `04-contratos/excel-conciliacion.md` para 010. Corrige dos puntos del contrato
general:

1. Solo se acepta `.xlsx`; `openpyxl` no lee `.xls` y no se agrega otra dependencia.
2. Las filas de técnicos de otro tenant de la misma región se ignoran; las de técnicos desconocidos
   o de otra región rechazan el archivo.

## Archivo

- Extensión `.xlsx`; el nombre original se guarda con `Path(nombre).name`.
- Tamaño máximo configurable; un archivo vacío o corrupto es `FormatoInvalido`.
- Se calcula SHA-256 sobre los bytes originales antes de abrir el libro.
- Se guarda en `CONCILIACIONES_DIR`/`MEDIA_ROOT` con nombre relativo seguro; nunca se expone la ruta
  física.
- El binario no se guarda en la base ni se audita.

## Hoja y columnas

- Solo se lee la hoja `GENERAL`; las demás hojas se ignoran.
- Columnas requeridas:

| Columna | Uso |
|---|---|
| `Material` | Código del catálogo |
| `Lote` | Lote informativo |
| `Libre utilización` | Cantidad para no seriados |
| `Número de serie` | Serie para seriados |
| `Nº ident.fis.1` | NIF del técnico |
| `Texto breve material` | Descripción |

- Se normalizan encabezados (mayúsculas, espacios) y se aceptan columnas extra.
- Si falta la hoja o una columna requerida, se rechaza el archivo.

## Interpretación

### Seriados

- Tienen valor en `Número de serie`; cada fila es una unidad.
- `Libre utilización` se ignora.
- La serie debe cumplir `^[A-Z0-9]{12}$`, ser única en el reporte y no estar `INSTALADA`.
- El material debe ser `es_seriado=True`.

### No seriados

- No tienen `Número de serie`.
- `Libre utilización` es la cantidad reportada; debe ser entero `>= 0`.
- Varias filas del mismo técnico/material se suman.
- El material debe ser `es_seriado=False`.

### Técnicos

- NIF con formato `LAXXXX`.
- Técnico del tenant que carga: se procesa.
- Técnico de otro tenant de la misma región: se ignora silenciosamente; no se muestra ni se audita
  con datos de ese tenant.
- Técnico desconocido o de otra región: rechaza el archivo completo.
- Técnico ausente del reporte: no se compara ni se modifica; no se asume 0.
- Material ausente para un técnico presente: cantidad 0.

## Materiales

- Si el código no existe en el catálogo, se registra `MaterialNoCatalogado` y la carga continúa.
- La aprobación se bloquea hasta que el material exista y se recalcule.

## Validaciones

- `.xlsx` válido y hoja `GENERAL`.
- Columnas requeridas.
- NIF `LAXXXX`.
- Serie con formato, única y no instalada.
- Material seriado/no seriado coherente con la presencia de serie.
- Cantidad no seriada entera `>= 0`.
- Sin filas de técnicos desconocidos o de otra región.

## Proceso

1. Validar cuenta y que no exista otra conciliación `EN_REVISION`.
2. Leer y validar el archivo.
3. Clasificar técnicos y filas.
4. Comparar series y cantidades.
5. Calcular la huella de stock.
6. Guardar archivo y hash.
7. Crear la conciliación `EN_REVISION` y sus diferencias en una transacción.
8. No modificar stock.

## Pruebas de contrato

- Un `.xlsx` con `GENERAL` y columnas válidas se lee correctamente.
- `.xls`, CSV, texto, archivo vacío o corrupto se rechazan.
- Hoja `GENERAL` ausente o columnas faltantes se rechazan.
- NIF inválido o de otra región rechaza el archivo.
- NIF de otro tenant de la misma región se ignora y no aparece en diferencias.
- Serie con formato inválido, duplicada o `INSTALADA` se rechaza.
- Material no catalogado se registra y bloquea la aprobación, no la carga.
- Cantidad no seriada negativa o no entera se rechaza.
- El archivo no modifica stock al cargar.
