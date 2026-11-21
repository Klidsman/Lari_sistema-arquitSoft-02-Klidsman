---
name: Lari · Control de materiales
description: Sistema visual de la operación diaria de materiales, documentado desde el código existente: shell, acceso y componentes de contenido.
colors:
  sello: "#1f5f8b"
  sello-hundido: "#18496b"
  grafito: "#1f2933"
  grafito-medio: "#3e4c59"
  grafito-tenue: "#52606d"
+  grafito-suave: "#5b6875"
  tapa: "#0f1c26"
  papel: "#f6f7f9"
  hoja: "#ffffff"
  superficie-alt: "#f0f2f5"
  tapa-activa: "#172a38"
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
  sobre-tapa-enlace: "#c9d4de"
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
  content-heading:
    fontFamily: 'system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "1.6rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.02em"
  table-head:
    fontFamily: 'system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "0.75rem"
    fontWeight: 700
    lineHeight: 1.4
    letterSpacing: "0.05em"
rounded:
  sm: "0.4rem"
  md: "0.5rem"
  lg: "0.75rem"
  xl: "1rem"
  pill: "999px"
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
    padding: "0.65rem 0.75rem"
  tabla-cabecera:
    backgroundColor: "{colors.superficie-alt}"
    textColor: "{colors.grafito-tenue}"
    padding: "0.65rem 0.75rem"
  buscador:
    backgroundColor: "{colors.hoja}"
    textColor: "{colors.grafito}"
    rounded: "{rounded.md}"
    padding: "0.85rem 1rem"
  paginacion:
    backgroundColor: "{colors.hoja}"
    textColor: "{colors.sello}"
    rounded: "{rounded.sm}"
    padding: "0.35rem 0.7rem"
  etiqueta:
    backgroundColor: "{colors.superficie-alt}"
    textColor: "{colors.grafito-tenue}"
    rounded: "{rounded.pill}"
    padding: "0.15rem 0.5rem"
  detalle:
    backgroundColor: "{colors.hoja}"
    textColor: "{colors.grafito}"
    rounded: "{rounded.md}"
    padding: "1rem 1.25rem"
  boton-contenido:
    backgroundColor: "{colors.hoja}"
    textColor: "{colors.grafito}"
    rounded: "{rounded.sm}"
    padding: "0.45rem 0.8rem"
  boton-contenido-primario:
    backgroundColor: "{colors.sello}"
    textColor: "{colors.hoja}"
    rounded: "{rounded.sm}"
    padding: "0.45rem 0.8rem"
  sidebar:
    backgroundColor: "{colors.tapa}"
    textColor: "{colors.sobre-tapa}"
    padding: "0.5rem 0.75rem"
  sidebar-activo:
    backgroundColor: "{colors.tapa-activa}"
    textColor: "{colors.sobre-tapa}"
    rounded: "{rounded.sm}"
    padding: "0.5rem 0.75rem"
  marca:
    textColor: "{colors.sello}"
    padding: "0"
---

# Design System: Lari · Control de materiales

## Overview

**Creative North Star: "El libro de inventario"**

Lari se lee como un libro de inventario abierto sobre una mesa: una hoja blanca sobre papel gris, renglones finos en lugar de recuadros, series y códigos en monoespaciada como si estuvieran sellados, y una sola tinta azul reservada para lo que exige una acción o marca el foco. No hay ornamentación: la jerarquía la hacen el peso tipográfico, el filete de 1 px y el espacio en blanco. Esa austeridad no es frialdad, es la forma que toma la trazabilidad cuando la interfaz tiene que ser creíble ante una auditoría.

El sistema nace de una aplicación operativa real: sesión única por tenant, series que se rastrean una por una, conciliaciones que se aprueban o rechazan completas, y un registro inmutable detrás de cada movimiento. La pantalla no persuade a nadie; permite que una persona con prisa haga un trabajo exacto y a prueba de error. Por eso la densidad es media-alta, la tabla es el ciudadano de primera y cada estado (error, aviso, conformidad) tiene color propio en lugar de un icono decorativo.

**Estado de este documento.** PRODUCT.md es explícito: no hay logo, manual de marca ni paleta corporativa, y la apariencia actual de `templates/` y `static/css/` es un punto de partida, no una identidad confirmada. Este DESIGN.md fotografía lo que hoy existe para que las pantallas nuevas no diverjan mientras esa identidad se decide. Los tokens de aquí son **normativos**; el carácter y el mundo visual son **provisionales** y se reemplazan cuando exista una dirección de marca confirmada. Desde la última revisión, el sistema ya cubre el shell autenticado, los formularios, las tablas, los botones, los buscadores, la paginación y los estados; lo que sigue sin regla propia se enumera en *Drift conocido*, no se presenta como inexistente.

**Key Characteristics:**
- Hoja blanca sobre papel gris; el fondo nunca compite con el contenido.
- Shell autenticado con barra lateral en Tapa, topbar blanca y contenido sobre Papel.
- Separación por filete de 1 px (`--borde`), no por sombra ni por relleno de color.
- Un único acento, el Azul sello, usado solo en acción, enlace, foco y estado activo.
- Monoespaciada para todo lo que es un identificador: series, códigos de material, TOTP, URIs.
- Densidad de mesa de trabajo: celdas de `0.65rem 0.75rem`, sin aire decorativo.
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
- **Grafito suave** (`#5b6875`): subtítulos de acceso y rol en la topbar; un paso más claro que el tenue.
- **Tapa** (`#0f1c26`): el único color oscuro de superficie. Es el panel de marca de la pantalla de acceso y la barra lateral del shell autenticado; se lee como la tapa dura del libro.
- **Papel** (`#f6f7f9`): fondo de la aplicación. Es la mesa, no la página.
- **Hoja** (`#ffffff`): toda superficie de contenido — topbar, tablas, paneles, tarjetas.
- **Superficie alterna** (`#f0f2f5`): cabecera de tabla, etiquetas y fondos de estado neutro. No es un gris de sección: nunca ocupa una franja completa de la pantalla.
- **Filete** (`#d9dee5`): borde y separador estándar, siempre 1 px.
- **Filete tenue** (`#eef1f4`): separador interno dentro de un panel, donde el filete estándar resultaría demasiado duro.

### Tertiary
- **Rojo corrección** (`#a4262c`): errores de validación, `aria-invalid`, `.errorlist`, banner de autenticación fallida.
- **Rojo pálido** (`#fdf3f3`) con **filete rojo** (`#e3b6b9`): fondo y borde del banner de error de acceso.
- **Verde conformidad** (`#256b3b`): éxito, confirmación de copia, mensajes `mensaje-success`.
- **Ámbar de nota** (`#8a5a00`): notas operativas y auroras de advertencia dentro de una línea.
- **Ámbar pálido** (`#fdf8ec`) con **filete ámbar** (`#e6d6a8`): bloque de aviso del flujo TOTP.

### On-dark (Tapa: acceso y barra lateral)
- **Sobre tapa** (`#ffffff`): el logotipo, el título y el enlace activo de la sidebar.
- **Sobre tapa enlace** (`#c9d4de`): enlaces de la sidebar en reposo.
- **Sobre tapa tenue** (`#aab7c4`): la descripción bajo el logotipo y los metadatos.
- **Sobre tapa apagado** (`#7f93a5`): el pie del panel y las etiquetas de grupo de la sidebar.
- **Sobre tapa filete** (`#6f8ba3`): el contorno de los puntos de la lista de hechos.
- **Tapa activa** (`#172a38`): fondo del enlace activo de la sidebar; sin franja lateral ni borde de 2 px.

### Named Rules

**La regla del sello.** El Azul sello ocupa menos del 10 % de cualquier pantalla y solo en cuatro papeles: acción, enlace, foco y estado activo. Su escasez es lo que lo vuelve legible como orden. Si dudas, no lo pongas.

**La regla del filete.** La separación se hace con una línea de 1 px (`--borde`) o, dentro de un panel, con el filete tenue (`#eef1f4`). Nunca con una sombra, una cebra de filas ni un borde de 2 px.

**La regla del papel.** El gris (`--fondo`) es la mesa y nunca contiene texto de lectura; el blanco (`--superficie`) es la página y todo contenido vive encima. No inviertas los papeles.

## Typography

**Display Font:** — (no hay fuente de display; el sistema no tiene jerarquía de marca que la justifique)
**Body Font:** Pila del sistema (`system-ui, -apple-system, "Segoe UI", sans-serif`)
**Label/Mono Font:** `ui-monospace, "Cascadia Mono", Consolas, monospace`

**Character:** Tipografía de instrumento, no de marca: la del sistema operativo, sin descargas, sin licencias y sin latencia. La única inflexión expresiva es el monoespaciado con interletraje amplio para identificadores y códigos de un solo uso, que se lee como un número sellado en el libro.

### Hierarchy
- **Headline** (600, `1.75rem`, 1.15, `-0.02em`): título de la tarjeta de acceso y de la tarjeta de configuración 2FA. Es el techo real del sistema; no hay escala de display.
- **Content heading** (600, `1.6rem`, 1.2, `-0.02em`): `h1` de las pantallas de trabajo. No compite con el headline de acceso.
- **Title** (700, `1.5rem`, 1.2, `0.06em`): solo la marca «Lari» en la tapa de acceso y en la sidebar. El enlace de cabecera usa el mismo peso con interletraje reducido.
- **Body** (400, `1rem`, 1.5): todo el contenido. En prosa instructiva se limita a `62ch`.
- **Label** (600, `0.875rem`): etiquetas de formulario, `legend` de bloque, encabezados de columna.
- **Table head** (700, `0.75rem`, mayúsculas, `0.05em`): cabecera de tabla; se lee como el encabezado impreso de una columna de inventario.
- **Small** (400, `0.85rem`): metadatos, cantidades, notas y mensajes auxiliares.
- **Mono** (`0.85rem`, `0.08em`): series, códigos, URIs `otpauth://`. El campo de código TOTP sube a `1.15rem` con `0.3em` de interletraje y se centra.

### Named Rules

**La regla de la serie en mono.** Todo lo que un humano podría confundir al dictar —serie, código de material, secreto TOTP, URI— va en monoespaciada con interletraje y `overflow-wrap: anywhere`. No hay excepciones por estética.

**La regla de los 62ch.** La prosa instructiva no pasa de `62ch`. Es la razón por la que los pasos del flujo TOTP se leen sin perder el renglón; aplícala a cualquier ayuda o introducción nueva.

## Layout

**Shell autenticado.** Barra lateral fija de `15rem` en Tapa, topbar blanca de `3.5rem` y contenido sobre Papel con ancho máximo `1100px`. La sidebar agrupa la navegación por rol (Operación, Almacén, Catálogo, Administración) y reserva el pie para «Mi perfil». El enlace activo se marca con fondo Tapa activa y peso 600, más `aria-current="page"`; no usa franja lateral ni borde de 2 px. La topbar muestra correo, rol y «Cerrar sesión». En móvil (`< 900px`) la sidebar se convierte en drawer con overlay, cierre con Esc, foco atrapado e `inert`; el botón «Menú» queda en la topbar. Las pantallas de acceso ocultan el shell por completo.

Las pantallas de trabajo usan dos columnas: contenido principal flexible (`minmax(0, 1fr)`) y un raíl de contexto fijo de `340px` (recojos) o `310px` (asignaciones), con `position: sticky; top: 1rem; max-height: 80vh` y scroll propio. El raíl es el sitio de la verdad inmediata —series del recojo, materiales disponibles— y por eso nunca se coloca debajo del contenido cuando hay ancho.

Densidad media-alta: `0.65rem 0.75rem` en celdas, `0.85rem 1rem` en buscadores, `0.75rem` de padding en paneles, `1rem` entre bloques, `1.25rem` de separación entre columnas. La escala de espaciado (`0.35 / 0.5 / 0.75 / 1 / 1.5 / 2rem`) sigue siendo una escala de facto; los tokens viven en `:root` para color y radio, no para espaciado.

Puntos de quiebre reales: `900px` (la sidebar pasa a drawer y la asignación deja de ser dos columnas), `700px` (el recojo apila el raíl bajo el formulario), `480px` (ajustes de padding y de tamaño en acceso y TOTP).

## Elevation & Depth

El sistema es **plano por defecto**. La profundidad la da la superposición de papeles —hoja blanca sobre papel gris— y el filete, no la sombra. Existen exactamente tres sombras en todo el proyecto y cada una tiene un motivo:

- **Tarjeta de acceso** (`box-shadow: 0 1.5rem 3.5rem rgba(15, 28, 38, 0.10)`): elevar el objeto único de la pantalla de entrada por encima de la mesa.
- **Bloque activo** (`box-shadow: 0 0 0 2px rgba(31, 95, 139, 0.15)`): un halo, no una sombra, para señalar el bloque de técnico en edición.
- **Campo inválido** (`box-shadow: 0 0 0 1px var(--error)`): refuerzo del borde de error, no elevación.

El drawer móvil no añade sombra: se separa con el overlay `rgba(15, 28, 38, 0.55)`, que oscurece el contenido sin sugerir una tarjeta flotante.

### Named Rules

**La regla de la hoja apoyada.** Una superficie nueva no flota. Si necesita destacar, se apoya en el papel con un filete y, como mucho, con el halo de estado activo. Las sombras difusas están reservadas a la tarjeta de acceso, que es una pantalla completa y no un componente repetido.

## Shapes

Lenguaje de esquina suave y contenido: `0.4rem` en controles (botones, buscadores, enlaces con borde, campos), `0.5rem` en superficies —paneles, raíles, bloques de técnico, `dl.detalle`, banners—, `0.75rem` en la tarjeta de configuración 2FA y `1rem` en la tarjeta de acceso de escritorio. Las etiquetas de estado usan `999px` y son la única forma completamente redondeada del sistema. En móvil, la tarjeta de acceso pierde radio y borde y se convierte en pantalla completa.

Los bordes son siempre de `1px`; el grosor no se usa para jerarquía. El único círculo del sistema es el punto de `0.4rem` que precede a cada hecho en el panel de tapa del acceso, dibujado con borde `1px` y sin relleno. No hay recortes en diagonal, ni esquinas mixtas, ni pestañas.

## Components

El sistema cubre el shell autenticado (sidebar, topbar, drawer móvil), los componentes de contenido (tabla, buscador, paginación, botones, formularios, etiquetas, detalle, mensajes y estados vacíos), las dos pantallas compuestas (recojos y asignación) y la superficie de acceso. Lo que aún no tiene regla propia —fragmentos de búsqueda y bloques internos de asignación— se enumera en *Drift conocido*.

### Buttons
- **Shape:** `0.4rem` de radio y borde de 1 px.
- **Neutral:** fondo Hoja, texto Grafito, `0.45rem 0.8rem`, altura mínima `2.25rem`. Es el botón por defecto de filtros y acciones secundarias.
- **Primary:** fondo Azul sello, texto blanco, `0.45rem 0.8rem`, peso 600. Se usa en `.boton` para crear, descargar o entrar. En acceso, ancho completo y altura mínima `2.75rem`.
- **Hover / Focus:** el hover del primario oscurece a Azul sello hundido (`#18496b`); el neutro cambia borde y texto a Azul sello. En acceso se añade `translateY(1px)` al pulsar. El foco es siempre `outline: 3px solid var(--acento)` con `outline-offset: 2px`.
- **Secondary:** blanco con filete, texto Grafito, hover Azul sello.
- **Ghost / enlace:** `.boton-enlace`, sin fondo ni borde, Azul sello subrayado, `padding: 0`. Se usa para «Cancelar», que nunca debe parecer primario.
- **En tabla:** las acciones son enlaces de texto en Azul sello; los formularios de baja se leen como enlace, no como botón relleno.

### Chips / Badges
Implementados como etiquetas de estado. `.etiqueta` y `.estado` usan fondo Superficie alterna, texto Grafito tenue, radio `999px` y `0.15rem 0.5rem`; `.etiqueta-anulado` cambia a fondo Rojo pálido, filete rojo y texto Rojo corrección. Son la única forma completamente redondeada y el único relleno de color fuera de los banners; no se usan para decorar encabezados ni para sustituir texto.

### Cards / Containers
- **Corner Style:** `0.5rem`; `0.75rem` y `1rem` solo en las dos tarjetas de acceso.
- **Background:** Hoja blanca siempre; nunca un gris de sección.
- **Shadow Strategy:** plana, ver *Elevation & Depth*.
- **Border:** `1px` de Filete, o Filete tenue para divisores internos.
- **Internal Padding:** `0.75rem` en raíles y bloques, `1rem 1.25rem` en `dl.detalle`, `0.85rem 1rem` en buscadores, `1rem` en banners, `clamp(1.5rem, 4vw, 2.5rem)` en la tarjeta de configuración.

### Inputs / Fields
- **Style:** filete de 1 px, fondo Hoja, radio `0.4rem`, altura mínima `2.25rem` y `0.5rem 0.65rem`; en acceso, altura mínima `2.75rem` y `0.6rem 0.75rem`.
- **Layout:** en formularios de contenido las etiquetas van encima del campo y el campo no supera `32rem`; en `.linea-recojo` ocupa el ancho completo del fieldset.
- **Focus:** el `outline` de 3 px del sistema, sin cambio de borde ni glow.
- **Error:** `.errorlist` en Rojo corrección, sin viñetas, peso 600; el campo lleva `aria-invalid="true"` y un anillo de 1 px del mismo rojo.
- **Disabled:** fondo Superficie alterna y texto Grafito tenue; no se usa `opacity` como único indicador.
- **File input:** borde discontinuo, padding `0.45rem`; el botón nativo del navegador se conserva.

### Navigation
El shell autenticado es la navegación principal: sidebar en Tapa, grupos por rol y enlace activo con fondo Tapa activa, peso 600 y `aria-current="page"`. La topbar muestra correo, rol y «Cerrar sesión». La navegación se filtra por rol en el servidor; no hay menús desplegables. En móvil la sidebar es un drawer con overlay, `aria-expanded`, `inert`, foco atrapado y cierre con Esc. El enlace «Saltar al contenido» es el primer foco de la página.

### Search / Filters
`.buscador` es una barra de Hoja con filete, radio `0.4rem`, padding `0.85rem 1rem` y separación `0.75rem`. Las etiquetas van encima del control, en Grafito tenue y `0.8125rem`; el botón se alinea al pie. Se usa en listas y bandejas; no se usa en formularios de edición.

### Pagination
`nav.paginacion` centrada, con enlaces de `0.35rem 0.7rem`, filete de 1 px, radio `0.4rem` y texto Azul sello. El contador va en Grafito tenue. Aparece solo cuando hay más de una página.

### Tables
El componente más usado: fondo Hoja, borde de 1 px, `border-collapse: separate`, filas separadas por Filete tenue y celdas `0.65rem 0.75rem` alineadas a la izquierda. La cabecera usa Superficie alterna, texto Grafito tenue, mayúsculas y `0.75rem`. No hay cebra ni bordes verticales; el hover de fila es `#fafbfc`. Las celdas numéricas usan `font-variant-numeric: tabular-nums`. El estado vacío ocupa la fila con `colspan` y se centra en Grafito tenue. En móvil, un contenedor `.tabla-scroll` permite scroll horizontal; la tabla no se corta.

### Detail list
`dl.detalle` en rejilla de dos columnas (`minmax(7rem, max-content)` y `minmax(0, 1fr)`), fondo Hoja, filete y padding `1rem 1.25rem`. Los `dt` van en versalitas de `0.75rem` y Grafito tenue; los `dd` en `0.9375rem` con `overflow-wrap: anywhere` para hashes y códigos largos.

### Messages and empty states
`.mensaje` usa borde completo, fondo tenue y color de estado; no hay franja lateral. `.mensaje-error` rojo, `.mensaje-success` verde y `.mensaje-aviso` ámbar. `.ayuda` es texto Grafito tenue; `.sin-resultados` es un bloque de borde discontinuo, fondo Hoja y texto centrado.

### Menu and summaries
`.menu-modulo` es una rejilla de enlaces/tarjetas para el módulo de registro de materiales; `.resumen-carga` es una rejilla de totales en Hoja con filete. `.fila-alerta` tiñe la fila de Rojo pálido para negativos del dashboard.

### Signature: shell autenticado
La estructura de todas las pantallas privadas. Sidebar de `15rem` en Tapa con marca, grupos por rol y «Mi perfil» al pie; topbar blanca de `3.5rem` con correo, rol y «Cerrar sesión»; contenido sobre Papel con máximo `1100px`. No hay sombras: sidebar y topbar se separan del contenido por el cambio de superficie y el filete. En móvil la sidebar se convierte en drawer con overlay y el botón «Menú» queda en la topbar.

### Signature: raíl de contexto
El patrón que define las pantallas de trabajo. Una columna fija a la derecha (`340px` / `310px`), pegajosa, con scroll propio y altura máxima `80vh`, que muestra el estado vivo de lo que se está capturando —series escaneadas y su estado, materiales disponibles con cantidades—. En escritorio nunca se apila; por debajo de `700px`/`900px` pasa a bloque estático sobre el formulario porque el formulario es lo primero.

### Signature: tarjeta de acceso partida
`62rem` de ancho, dos columnas `0.92fr / 1.08fr`, radio `1rem`, sombra difusa. A la izquierda, el panel de tapa oscuro con la marca, tres hechos operativos y el pie «Uso interno · Operación diaria». A la derecha, la tarjeta blanca con un único título, un subtítulo de `36ch` y un formulario de una columna. En móvil se convierte en pantalla completa: el panel de tapa se reduce a una franja con el logotipo y los hechos desaparecen.

**Variante de alta del segundo factor.** Cuando el contenido es una guía de tres pasos, la misma tarjeta pasa a una sola columna: la tapa se reduce a franja superior y el cuerpo reparte la guía en dos columnas, pasos 1 y 3 a la izquierda y el bloque de clave del paso 2 a la derecha (`19rem`), con una sola columna por debajo de `900px`. El orden del DOM sigue siendo 1 → 2 → 3; la rejilla solo mueve el paso 2 a la derecha para que la clave y el formulario de confirmación quepan en el primer viewport.

## Flujo de traspaso en tres columnas

La pantalla `templates/traspasos/formulario.html` usa `.traspaso-flujo`, una rejilla de tres columnas
(`12rem / 1.5fr / 15rem`) sobre hojas blancas con filete. Cada columna es un `.traspaso-columna`:
técnico que entrega (`.tecnico-opcion`), materiales en mano (`.material-traspaso`,
`.material-traspaso__accion`, `.series-lista`, `.serie-opcion`) y técnicos que reciben
(`.tecnico-recibe`). El resumen usa `.resumen-recibiran` y `.lista-resumen`; el estado activo del
técnico usa filete de acento y el halo documentado como «Bloque activo». Por debajo de `1000px` la
rejilla pasa a una columna y el panel de materiales pierde su scroll propio.

## Do's and Don'ts

### Do:
- **Do** construir sobre la hoja blanca: cualquier contenido nuevo va en una superficie blanca con filete de `1px var(--borde)`, sobre el papel `var(--fondo)`.
- **Do** usar `--acento` solo en acción, enlace, foco y estado activo, y comprobar que no supera el 10 % de la pantalla.
- **Do** mantener el foco visible de `3px` con `offset 2px` en todo control interactivo; es la garantía de teclado del sistema y no se negocia por estética.
- **Do** poner en monoespaciada, con `overflow-wrap: anywhere`, toda serie, código, secreto TOTP y URI.
- **Do** limitar la prosa instructiva a `62ch` y apoyarla en el Grafito medio, no en el Grafito.
- **Do** usar los tres estados con su pareja pálido/filete ya existente (rojo, verde, ámbar) en lugar de introducir un cuarto color.
- **Do** conservar la densidad de tabla (`0.65rem 0.75rem`) y la cabecera de Superficie alterna; es lo que permite comparar series y discrepancias de un vistazo.
- **Do** usar el botón primario (`.boton`) para la acción principal y el neutro para filtros y acciones secundarias.
- **Do** usar `.buscador`, `.paginacion`, `.tabla`, `.detalle` y `.etiqueta` antes de inventar una variante local.
- **Do** tratar el raíl de contexto como parte del patrón de pantalla de trabajo: fijo, pegajoso, con scroll propio y apilado solo en móvil.
- **Do** envolver las tablas nuevas en `.tabla-scroll` o confiar en la envoltura automática del shell para que el móvil no las corte.

### Don't:
- **Don't** crear un botón, campo, chip o paginación nuevos sin CSS y sin documentarlos aquí en el mismo cambio. El sistema ya existe; extiéndelo, no lo reinventes.
- **Don't** añadir sombras difusas a paneles, tarjetas repetidas o menús; la única sombra difusa del sistema es la tarjeta de acceso.
- **Don't** usar franjas laterales de color como estado activo; usa fondo Tapa activa y peso 600, como la sidebar.
- **Don't** usar relleno de color de marca para separar secciones, ni cebra en tablas, ni cabeceras de columna oscuras.
- **Don't** usar las etiquetas de estado como decoración: solo describen un estado real.
- **Don't** introducir una segunda tipografía, una fuente de display descargada ni una escala tipográfica más allá de los roles documentados.
- **Don't** dar el mismo peso visual a una acción primaria y a «Cancelar»; la jerarquía primario / secundario / enlace es lo que evita el clic erróneo en el flujo 2FA.
- **Don't** repetir valores literales (`#fff`, `#eef1f4`, `rgba(...)`) en reglas nuevas: usa los tokens de `:root` y, si falta uno, añádelo al token set.
- **Don't** volver a introducir `style="..."` en plantillas; si una pantalla necesita una excepción, se resuelve con una clase.
- **Don't** tratar el carácter visual como identidad confirmada. PRODUCT.md dice que no hay marca: este documento es una foto del punto de partida y se reescribe cuando exista dirección de identidad.

### Drift conocido
- Los fragmentos de búsqueda `.resultado-material` y `.resultado-tecnico` aún no tienen regla propia; heredan el estilo básico de lista. Es la siguiente pieza de UI pendiente.
- Los bloques internos del constructor de asignaciones y del recojo (`.constructor-bloque`, `.filas-bloque`, `.serie-opcion`, `.series-seleccionadas`, `.material-seleccionado`, `.resumen-series`, `.titulo-bloque`, `.material-fila`, `.agregar-fila`, `.quitar-fila`, `.quitar-bloque`) usan controles globales pero no un componente documentado. Funcionan; no están pulidos.
- `templates/inicio.html` sigue siendo una pantalla de bienvenida, no un dashboard. Un panel de accesos rápidos por rol es el siguiente paso.
- La configuración 2FA no tiene QR; usa clave manual copiable. Añadirlo requiere una dependencia de generación de QR.
- `.impeccable/design.json` se generó antes del shell y de `componentes.css`; hay que regenerarlo cuando se cierre esta fase.
- Quedan literales por tokenizar: `#fafbfc` (hover de fila), `#f2f8f4` (fondo de éxito) y `#6b4e00` (texto de aviso). No introduzcas nuevos: formalízalos en `:root` cuando toques esas reglas.
- No hay tema oscuro. El sistema es claro por decisión; `color-scheme: light` es explícito.
- La única transición del sistema es el drawer móvil (`180ms`, desactivada con `prefers-reduced-motion`). No hay animaciones decorativas.
