# Acta de Devolución

Formato y estructura del archivo Excel del acta de entrega de devoluciones a Lari.

## 1. Propósito

El acta de devolución es el documento estandarizado que el sistema genera automáticamente cuando un tenant registra una devolución de equipos. Este Excel contiene un cuadro simple con el técnico (LAXXXX), material, serie y fecha de devolución.

## 2. Generación

- El sistema genera el acta automáticamente al registrar una devolución
- No se puede editar manualmente el acta antes de generarlo
- El acta se guarda de forma inmutable con firma SHA-256 para garantizar su integridad
- El acta se puede descargar y enviar a Lari (contrata principal)

## 3. Estructura del Archivo

El acta de devolución contiene una hoja principal con una tabla simple:

### Metadatos del Acta

| Campo | Descripción | Valor |
|---|---|---|
| **Tenant** | Nombre/código del tenant | Completado automáticamente |
| **Región** | Región del tenant | Completado automáticamente |
| **Fecha de generación** | Fecha de generación del acta | Fecha actual |
| **ID de devolución** | Identificador único de la devolución | Generado por el sistema |

### Tabla de Devoluciones

| Columna | Descripción | Ejemplo |
|---|---|---|
| **NIF** | Identificador del técnico (LAXXXX) | LA1234 |
| **Material** | Código del material (11 dígitos) | 12345678901 |
| **Descripción** | Descripción del material | Router Huawei |
| **Serie** | Serie individual (12 caracteres) | ABC123456789 |
| **Fecha de devolución** | Fecha en que el técnico devolvió el equipo | 20-10-2026 |

## 4. Campos No Editables

Todos los campos se completan automáticamente y **no son editables** por el usuario:
- NIF (completado desde el técnico que devolvió)
- Material
- Descripción
- Serie
- Fecha de devolución

## 5. Validaciones del Acta

El sistema valida que:
- Cada serie tenga el formato correcto (12 caracteres alfanuméricos A-Z, 0-9)
- Las series sean únicas (no haya duplicados)
- La fecha de devolución sea válida
- Código y Descripción coincidan con el catálogo de materiales

## 6. Integridad del Archivo

- El acta se guarda con una firma SHA-256 para garantizar que no fue alterado
- El hash se registra en el sistema junto con la devolución
- Se puede verificar el hash del acta recibido contra el registrado

## 7. Descarga y Envío

- El acta se puede descargar desde el detalle de la devolución
- El tenant puede enviar el acta a Lari por correo u otro medio
- El sistema registra la fecha de generación del acta

## 8. Ejemplo de Formato

```
+----------+---------------+----------------+------------------+-------------------+
| NIF      | Material      | Descripción     | Serie            | Fecha devolución  |
+----------+---------------+----------------+------------------+-------------------+
| LA1234   | 12345678901   | Router Huawei   | ABC123456789     | 20-10-2026        |
| LA1234   | 12345678901   | Router Huawei   | DEF123456789     | 20-10-2026        |
| LA5678   | 98765432109   | Decodificador   | GHI123456789     | 20-10-2026        |
+----------+---------------+----------------+------------------+-------------------+
```

## 9. Regla de Simplicidad

- El acta es un cuadro simple sin múltiples hojas
- No incluye metadatos complejos de cuadrilla
- No incluye movimientos SAP (Z31, Z32)
- Solo contiene la información esencial para la devolución: técnico, material, serie y fecha
