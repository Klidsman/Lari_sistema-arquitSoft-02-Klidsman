---
name: Lari · Control de materiales
description: Sistema visual de la operación diaria de materiales, documentado desde el código existente.
colors:
  sello: "#1f5f8b"
  sello-hundido: "#18496b"
  grafito: "#1f2933"
  grafito-medio: "#3e4c59"
  grafito-tenue: "#52606d"
  tapa: "#0f1c26"
  papel: "#f6f7f9"
  hoja: "#ffffff"
  filete: "#d9dee5"
  filete-tenue: "#eef1f4"
  correccion: "#a4262c"
  correccion-palido: "#fdf3f3"
  correccion-filete: "#e3b6b9"
  conformidad: "#256b3b"
  nota: "#8a5a00"
  nota-palido: "#fdf8ec"
  nota-filete: "#e6d6a8"
  sobre-tapa: "#ffffff"
  sobre-tapa-tenue: "#aab7c4"
  sobre-tapa-apagado: "#7f93a5"
  sobre-tapa-filete: "#6f8ba3"
typography:
  headline:
    fontFamily: 'system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "1.75rem"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  title:
    fontFamily: 'system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "1.5rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "0.06em"
  body:
    fontFamily: 'system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "0em"
  label:
    fontFamily: 'system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "0.875rem"
    fontWeight: 600
    lineHeight: 1.4
  small:
    fontFamily: 'system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "0.85rem"
    fontWeight: 400
    lineHeight: 1.5
  mono:
    fontFamily: 'ui-monospace, "Cascadia Mono", Consolas, monospace'
    fontSize: "0.85rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "0.08em"
rounded:
  sm: "6px"
  md: "8px"
  lg: "12px"
  xl: "16px"
  full: "50%"
spacing:
  xs: "0.35rem"
  sm: "0.5rem"
  md: "0.75rem"
  lg: "1rem"
  xl: "1.5rem"
  xxl: "2rem"
components:
  button-primary:
    backgroundColor: "{colors.sello}"
    textColor: "{colors.hoja}"
    rounded: "{rounded.sm}"
    padding: "0.6rem 1.1rem"
  button-primary-hover:
    backgroundColor: "{colors.sello-hundido}"
    textColor: "{colors.hoja}"
    rounded: "{rounded.sm}"
    padding: "0.6rem 1.1rem"
  button-secundario:
    backgroundColor: "{colors.hoja}"
    textColor: "{colors.sello}"
    rounded: "{rounded.sm}"
    padding: "0.4rem 0.85rem"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.sello}"
    rounded: "{rounded.sm}"
    padding: "0"
  button-auth:
    backgroundColor: "{colors.sello}"
    textColor: "{colors.hoja}"
    rounded: "{rounded.md}"
    padding: "0.65rem 1rem"
  campo-texto:
    backgroundColor: "{colors.hoja}"
    textColor: "{colors.grafito}"
    rounded: "{rounded.md}"
    padding: "0.6rem 0.75rem"
  campo-codigo:
    backgroundColor: "{colors.hoja}"
    textColor: "{colors.grafito}"
    rounded: "{rounded.md}"
    padding: "0.55rem 0.7rem"
  panel:
    backgroundColor: "{colors.hoja}"
    textColor: "{colors.grafito}"
    rounded: "{rounded.md}"
    padding: "0.75rem"
  tabla:
    backgroundColor: "{colors.hoja}"
    textColor: "{colors.grafito}"
    padding: "0.55rem 0.65rem"
  marca:
    textColor: "{colors.sello}"
    padding: "0"
---

# Design System: Lari · Control de materiales

## Overview

**Creative North Star: "El libro de inventario"**

Lari se lee como un libro de inventario abierto sobre una mesa: una hoja blanca sobre papel gris, renglones finos en lugar de recuadros, series y códigos en monoespaciada como si estuvieran sellados, y una sola tinta azul reservada para lo que exige una acción o marca el foco. No hay ornamentación: la jerarquía la hacen el peso tipográfico, el filete de 1 px y el espacio en blanco. Esa austeridad no es frialdad, es la forma que toma la trazabilidad cuando la interfaz tiene que ser creíble ante una auditoría.

El sistema nace de una aplicación operativa real: sesión única por tenant, series que se rastrean una por una, conciliaciones que se aprueban o rechazan completas, y un registro inmutable detrás de cada movimiento. La pantalla no persuade a nadie; permite que una persona con prisa haga un trabajo exacto y a prueba de error. Por eso la densidad es media-alta, la tabla es el ciudadano de primera y cada estado (error, aviso, conformidad) tiene color propio en lugar de un icono decorativo.

**Estado de este documento.** PRODUCT.md es explícito: no hay logo, manual de marca ni paleta corporativa, y la apariencia actual de `templates/` y `static/css/` es un punto de partida, no una identidad confirmada. Este DESIGN.md fotografía lo que hoy existe para que las pantallas nuevas no diverjan mientras esa identidad se decide. Los tokens de aquí son **normativos**; el carácter y el mundo visual son **provisionales** y se reemplazan cuando exista una dirección de marca confirmada. La ausencia de un sistema de controles en el shell (ver *Components*) es una carencia documentada, no una decisión estética: no la conviertas en ley.

**Key Characteristics:**
- Hoja blanca sobre papel gris; el fondo nunca compite con el contenido.
- Separación por filete de 1 px (`--borde`), no por sombra ni por relleno de color.
- Un único acento, el Azul sello, usado solo en acción, enlace, foco y estado activo.
- Monoespaciada para todo lo que es un identificador: series, códigos de material, TOTP, URIs.
- Densidad de mesa de trabajo: filas de 0.55 rem de padding vertical, sin aire decorativo.
- Semántica de color explícita: corrección (rojo), conformidad (verde), nota (ámbar).

## Colors

Paleta de instrumento: un azul de sello sobre una escala de grafito y papel, más tres colores de estado que solo aparecen cuando hay algo que decir.

### Primary
- **Azul sello** (`#1f5f8b`): el acento único. Aparece en la marca «Lari», los enlaces, el botón primario, el anillo de foco y el borde del bloque activo. Nunca se usa como fondo de sección ni como adorno.
- **Azul sello hundido** (`#18496b`): estado hover del botón primario. Es el mismo sello, un paso más oscuro.

### Neutral
- **Grafito** (`#1f2933`): color de texto por defecto. Contraste 13,7:1 sobre hoja.
- **Grafito medio** (`#3e4c59`): prosa de introducción y texto secundario largo.
- **Grafito tenue** (`#52606d`): metadatos, cantidades, etiquetas de `dt`; el texto que se lee después del principal.
- **Tapa** (`#0f1c26`): el único color oscuro de superficie. Exclusivo del panel de marca de la pantalla de acceso, que se lee como la tapa dura del libro.
- **Papel** (`#f6f7f9`): fondo de la aplicación. Es la mesa, no la página.
- **Hoja** (`#ffffff`): toda superficie de contenido — cabecera, tablas, paneles, tarjetas.
- **Filete** (`#d9dee5`): borde y separador estándar, siempre 1 px.
- **Filete tenue** (`#eef1f4`): separador interno dentro de un panel, donde el filete estándar resultaría demasiado duro.

### Tertiary
- **Rojo corrección** (`#a4262c`): errores de validación, `aria-invalid`, `.errorlist`, banner de autenticación fallida.
- **Rojo pálido** (`#fdf3f3`) con **filete rojo** (`#e3b6b9`): fondo y borde del banner de error de acceso.
- **Verde conformidad** (`#256b3b`): éxito, confirmación de copia, mensajes `mensaje-success`.
- **Ámbar de nota** (`#8a5a00`): notas operativas y auroras de advertencia dentro de una línea.
- **Ámbar pálido** (`#fdf8ec`) con **filete ámbar** (`#e6d6a8`): bloque de aviso del flujo TOTP.

### On-dark (panel de marca)
- **Sobre tapa** (`#ffffff`): el logotipo y su título.
- **Sobre tapa tenue** (`#aab7c4`): la descripción bajo el logotipo.
- **Sobre tapa apagado** (`#7f93a5`): el pie del panel.
- **Sobre tapa filete** (`#6f8ba3`): el contorno de los puntos de la lista de hechos.

### Named Rules

**La regla del sello.** El Azul sello ocupa menos del 10 % de cualquier pantalla y solo en cuatro papeles: acción, enlace, foco y estado activo. Su escasez es lo que lo vuelve legible como orden. Si dudas, no lo pongas.

**La regla del filete.** La separación se hace con una línea de 1 px (`--borde`) o, dentro de un panel, con el filete tenue (`#eef1f4`). Nunca con una sombra, un fondo gris alterno ni un borde de 2 px.

**La regla del papel.** El gris (`--fondo`) es la mesa y nunca contiene texto de lectura; el blanco (`--hoja` en este documento; hoy `#ffffff` literal en CSS) es la página y todo contenido vive encima. No inviertas los papeles.

## Typography

**Display Font:** — (no hay fuente de display; el sistema no tiene jerarquía de marca que la justifique)
**Body Font:** Pila del sistema (`system-ui, -apple-system, "Segoe UI", sans-serif`)
**Label/Mono Font:** `ui-monospace, "Cascadia Mono", Consolas, monospace`

**Character:** Tipografía de instrumento, no de marca: la del sistema operativo, sin descargas, sin licencias y sin latencia. La única inflexión expresiva es el monoespaciado con interletraje amplio para identificadores y códigos de un solo uso, que se lee como un número sellado en el libro.

### Hierarchy
- **Headline** (600, `1.75rem`, 1.15, `-0.02em`): título de la tarjeta de acceso y de la tarjeta de configuración 2FA. Es el techo real del sistema; no hay escala de display.
- **Title** (700, `1.5rem`, 1.2, `0.06em`): solo la marca «Lari» en el panel de tapa. El enlace de cabecera usa el mismo peso con interletraje reducido (`0.04em`) porque compite con la navegación.
- **Body** (400, `1rem`, 1.5): todo el contenido. En prosa instructiva se limita a `62ch`.
- **Label** (600, `0.875rem`): etiquetas de formulario, `legend` de bloque, encabezados de columna.
- **Small** (400, `0.85rem`): metadatos, cantidades, notas y mensajes auxiliares.
- **Mono** (`0.85rem`, `0.08em`): series, códigos, URIs `otpauth://`. El campo de código TOTP sube a `1.15rem` con `0.3em` de interletraje y se centra.

### Named Rules

**La regla de la serie en mono.** Todo lo que un humano podría confundir al dictar —serie, código de material, secreto TOTP, URI— va en monoespaciada con interletraje y `overflow-wrap: anywhere`. No hay excepciones por estética.

**La regla de los 62ch.** La prosa instructiva no pasa de `62ch`. Es la razón por la que los pasos del flujo TOTP se leen sin perder el renglón; aplícala a cualquier ayuda o introducción nueva.

## Layout

Contenedor único de `min(1100px, calc(100% - 2rem))` centrado con `1.5rem` de margen vertical. La cabecera es una fila flexible que envuelve: marca a la izquierda, navegación en línea con `0.35rem 1rem` de separación; en móvil la navegación ocupa el ancho completo y envuelve sin menú hamburguesa. No hay barra lateral de aplicación ni breadcrumbs.

Las pantallas de trabajo usan dos columnas: contenido principal flexible (`minmax(0, 1fr)`) y un raíl de contexto fijo de `340px` (recojos) o `310px` (asignaciones), con `position: sticky; top: 1rem; max-height: 80vh` y scroll propio. El raíl es el sitio de la verdad inmediata —series del recojo, materiales disponibles— y por eso nunca se coloca debajo del contenido cuando hay ancho.

Densidad media-alta: `0.55rem 0.65rem` en celdas, `0.75rem` de padding en paneles, `1rem` entre bloques, `1.25rem` de separación entre columnas. El ritmo de espaciado observado (`0.35 / 0.5 / 0.75 / 1 / 1.5 / 2rem`) es una escala de facto, no tokens: no existe un token de espaciado en el código.

Puntos de quiebre reales: `900px` (la asignación deja de ser dos columnas y el acceso colapsa a una sola), `700px` (el recojo apila el raíl bajo el formulario), `480px` (ajustes de padding y de tamaño en acceso y TOTP).

## Elevation & Depth

El sistema es **plano por defecto**. La profundidad la da la superposición de papeles —hoja blanca sobre papel gris— y el filete, no la sombra. Existen exactamente tres sombras en todo el proyecto y cada una tiene un motivo:

- **Tarjeta de acceso** (`box-shadow: 0 1.5rem 3.5rem rgba(15, 28, 38, 0.10)`): elevar el objeto único de la pantalla de entrada por encima de la mesa.
- **Bloque activo** (`box-shadow: 0 0 0 2px rgba(31, 95, 139, 0.15)`): un halo, no una sombra, para señalar el bloque de técnico en edición.
- **Campo inválido** (`box-shadow: 0 0 0 1px var(--error)`): refuerzo del borde de error, no elevación.

### Named Rules

**La regla de la hoja apoyada.** Una superficie nueva no flota. Si necesita destacar, se apoya en el papel con un filete y, como mucho, con el halo de estado activo. Las sombras difusas están reservadas a la tarjeta de acceso, que es una pantalla completa y no un componente repetido.

## Shapes

Lenguaje de esquina suave y contenido: `6px` en controles del shell (botones, enlaces con borde), `8px` en todo lo que es una superficie —paneles, raíles, bloques de técnico, campos de acceso, banners—, `12px` en la tarjeta de configuración 2FA y `16px` en la tarjeta de acceso de escritorio. En móvil, la tarjeta de acceso pierde radio y borde y se convierte en pantalla completa.

Los bordes son siempre de `1px`; el grosor no se usa para jerarquía. El único círculo del sistema es el punto de `0.4rem` que precede a cada hecho en el panel de tapa del acceso, dibujado con borde `1px` y sin relleno. No hay recortes en diagonal, ni esquinas mixtas, ni pestañas.

## Components

El sistema cubre el armazón (cabecera, tabla, mensajes), dos pantallas compuestas (recojos y asignación) y la superficie de acceso. **No cubre el resto**: `.boton`, `.etiqueta`, `.estado`, `.paginacion`, `.buscador`, `.ayuda`, `.detalle` y `.codigo` existen en las plantillas sin una sola regla en CSS. Cualquier pantalla nueva que use esas clases hereda el control por defecto del navegador, no un componente Lari.

### Buttons
- **Shape:** `6px` en el shell, `8px` en acceso; borde `1px` del mismo color que el fondo en el primario.
- **Primary:** fondo Azul sello, texto blanco, `0.6rem 1.1rem`, peso 600. En la pantalla de acceso, ancho completo, altura mínima `2.75rem`.
- **Hover / Focus:** el hover oscurece a Azul sello hundido (`#18496b`); en acceso se añade `translateY(1px)` al pulsar. El foco es siempre `outline: 3px solid var(--acento)` con `outline-offset: 2px`.
- **Secondary:** blanco con filete, texto Azul sello, `0.4rem 0.85rem` (el botón «Copiar» de la clave TOTP). El hover solo cambia el borde a Azul sello.
- **Ghost / enlace:** `.boton-enlace`, sin fondo ni borde, Azul sello subrayado, `padding: 0`. Se usa para «Cancelar», que nunca debe parecer primario.

### Chips / Badges
No implementados. `.etiqueta`, `.estado` y `.etiqueta-anulado` se usan en las tablas sin estilo. Cuando se definan, deben ser texto con filete o color de estado, no pastillas rellenas: el sistema no tiene rellenos de color fuera de los estados.

### Cards / Containers
- **Corner Style:** `8px`; `12px` y `16px` solo en las dos tarjetas de acceso.
- **Background:** Hoja blanca siempre; nunca un gris de sección.
- **Shadow Strategy:** plana, ver *Elevation & Depth*.
- **Border:** `1px` de Filete, o Filete tenue para divisores internos.
- **Internal Padding:** `0.75rem` en raíles y bloques, `1rem` en banners, `clamp(1.5rem, 4vw, 2.5rem)` en la tarjeta de configuración.

### Inputs / Fields
- **Style:** filete de 1 px, fondo Hoja, radio `8px`. En acceso, altura mínima `2.75rem` y `0.6rem 0.75rem`; en el resto, `0.55rem 0.7rem`.
- **Focus:** el `outline` de 3 px del sistema, sin cambio de borde ni glow.
- **Error:** `.errorlist` en Rojo corrección, sin viñetas, peso 600; el campo lleva `aria-invalid="true"` y un anillo de 1 px del mismo rojo.
- **Disabled:** no hay tratamiento definido; usar `opacity: 0.55`, como ya hace `.material-opcion[aria-disabled="true"]`.

### Navigation
Enlaces de texto en Grafito, sin subrayado en reposo, con el acento del sistema al pasar. La marca «Lari» es el único elemento con interletraje (`0.04em`) y peso 700. La navegación se filtra por rol en el servidor; no hay menús desplegables ni estado activo persistente. «Cerrar sesión» es un `button` dentro de un formulario en línea y se lee como un enlace más, no como acción destructiva.

### Tables
El componente más usado y el más cuidado: fondo Hoja, `border-collapse`, filas separadas por filete de 1 px, celdas `0.55rem 0.65rem` alineadas a la izquierda. No hay cebra, ni cabecera oscura, ni bordes verticales. La densidad es deliberada: la tabla es donde se leen series y diferencias de conciliación.

### Signature: raíl de contexto
El patrón que define las pantallas de trabajo. Una columna fija a la derecha (`340px` / `310px`), pegajosa, con scroll propio y altura máxima `80vh`, que muestra el estado vivo de lo que se está capturando —series escaneadas y su estado, materiales disponibles con cantidades—. En escritorio nunca se apila; por debajo de `700px`/`900px` pasa a bloque estático sobre el formulario porque el formulario es lo primero.

### Signature: tarjeta de acceso partida
`62rem` de ancho, dos columnas `0.92fr / 1.08fr`, radio `16px`, sombra difusa. A la izquierda, el panel de tapa oscuro con la marca, tres hechos operativos y el pie «Uso interno · Operación diaria». A la derecha, la tarjeta blanca con un único título, un subtítulo de `36ch` y un formulario de una columna. En móvil se convierte en pantalla completa: el panel de tapa se reduce a una franja con el logotipo y los hechos desaparecen.

**Variante de alta del segundo factor.** Cuando el contenido es una guía de tres pasos, la misma tarjeta pasa a una sola columna: la tapa se reduce a franja superior y el cuerpo reparte la guía en dos columnas, pasos 1 y 3 a la izquierda y el bloque de clave del paso 2 a la derecha (`19rem`), con una sola columna por debajo de `900px`. El orden del DOM sigue siendo 1 → 2 → 3; la rejilla solo mueve el paso 2 a la derecha para que la clave y el formulario de confirmación quepan en el primer viewport.

## Do's and Don'ts

### Do:
- **Do** construir sobre la hoja blanca: cualquier contenido nuevo va en una superficie blanca con filete de `1px var(--borde)`, sobre el papel `var(--fondo)`.
- **Do** usar `--acento` solo en acción, enlace, foco y estado activo, y comprobar que no supera el 10 % de la pantalla.
- **Do** mantener el foco visible de `3px` con `offset 2px` en todo control interactivo; es la garantía de teclado del sistema y no se negocia por estética.
- **Do** poner en monoespaciada, con `overflow-wrap: anywhere`, toda serie, código, secreto TOTP y URI.
- **Do** limitar la prosa instructiva a `62ch` y apoyarla en el Grafito medio, no en el Grafito.
- **Do** usar los tres estados con su pareja pálido/filete ya existente (rojo, verde, ámbar) en lugar de introducir un cuarto color.
- **Do** conservar la densidad de tabla (`0.55rem 0.65rem`); es lo que permite comparar series y discrepancias de un vistazo.
- **Do** tratar el raíl de contexto como parte del patrón de pantalla de trabajo: fijo, pegajoso, con scroll propio y apilado solo en móvil.

### Don't:
- **Don't** inventar un sistema de botones, campos, chips o paginación y presentarlo como existente: hoy `.boton`, `.etiqueta`, `.estado`, `.paginacion` y `.buscador` no tienen CSS. Si una pantalla nueva los necesita, se define el componente y se documenta aquí en el mismo cambio.
- **Don't** añadir sombras difusas a paneles, tarjetas repetidas o menús; la única sombra difusa del sistema es la tarjeta de acceso.
- **Don't** usar relleno de color de marca para separar secciones, ni cebra en tablas, ni cabeceras de columna oscuras.
- **Don't** introducir una segunda tipografía, una fuente de display descargada ni una escala tipográfica más allá de las seis roles documentados.
- **Don't** dar el mismo peso visual a una acción primaria y a «Cancelar»; la jerarquía primario / secundario / enlace es lo que evita el clic erróneo en el flujo 2FA.
- **Don't** repetir valores literales (`#fff`, `#eef1f4`, `rgba(...)`) en reglas nuevas: usa los tokens de `:root` y, si falta uno, añádelo al token set.
- **Don't** copiar los `style="..."` en línea de `templates/recojos/recojo_form.html`: duplican reglas que ya existen en `base.css` y se desincronizan en silencio.
- **Don't** tratar el carácter visual como identidad confirmada. PRODUCT.md dice que no hay marca: este documento es una foto del punto de partida y se reescribe cuando exista dirección de identidad.

### Drift conocido
- `auth.css` usa `#174a6d` como hover del botón, mientras `base.css` usa `#18496b`. El token canónico es **Azul sello hundido** (`#18496b`); al tocar `auth.css`, converge a `var(--acento-hundido)`.
- `--acento-hundido`, `--superficie` (la hoja blanca), `--hoja` y `--filete-tenue` no existen aún como custom properties en `:root`, aunque sus valores se repiten en duro por el código. Formalizarlos es el siguiente paso natural, no parte de este documento.
