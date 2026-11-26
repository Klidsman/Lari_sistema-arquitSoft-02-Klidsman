---
name: Lari · Control de materiales
description: Sistema visual de la operación diaria de materiales, documentado desde el código existente: shell, acceso y componentes de contenido.
colors:
  sello: "#1f5f8b"
  sello-hundido: "#18496b"
  sello-tenue: "#e7eff6"
  grafito: "#1f2933"
  grafito-medio: "#3e4c59"
  grafito-tenue: "#52606d"
+  grafito-suave: "#5b6875"
  tapa: "#0f1c26"
  papel: "#f6f7f9"
  hoja: "#ffffff"
  superficie-alt: "#f0f2f5"
  hoja-hover: "#fafbfc"
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
  marca-lari:
    backgroundColor: "transparent"
    textColor: "{colors.sobre-tapa}"
    padding: "0"
  icono:
    backgroundColor: "transparent"
    textColor: "{colors.acento}"
    padding: "0"
  acceso:
    backgroundColor: "{colors.hoja}"
    textColor: "{colors.grafito}"
    rounded: "{rounded.md}"
    padding: "0.8rem 1.25rem"
---

# Design System: Lari · Control de materiales

## Overview

**Creative North Star: "El libro de inventario"**

Lari se lee como un libro de inventario abierto sobre una mesa: una hoja blanca sobre papel gris, renglones finos en lugar de recuadros, series y códigos en monoespaciada como si estuvieran sellados, y una sola tinta azul reservada para lo que exige una acción o marca el foco. No hay ornamentación: la jerarquía la hacen el peso tipográfico, el filete de 1 px y el espacio en blanco. Esa austeridad no es frialdad, es la forma que toma la trazabilidad cuando la interfaz tiene que ser creíble ante una auditoría.

El sistema nace de una aplicación operativa real: sesión única por tenant, series que se rastrean una por una, conciliaciones que se aprueban o rechazan completas, y un registro inmutable detrás de cada movimiento. La pantalla no persuade a nadie; permite que una persona con prisa haga un trabajo exacto y a prueba de error. Por eso la densidad es media-alta, la tabla es el ciudadano de primera y cada estado (error, aviso, conformidad) tiene color propio en lugar de un icono decorativo.

**Estado de este documento.** La interfaz ya tiene una **marca gráfica de trabajo** —monograma «L» con renglones de inventario— y un **sistema de iconos SVG** de trazo único. No es un manual de marca confirmado ni una identidad corporativa cerrada: es una propuesta coherente con «El libro de inventario» que puede reemplazarse sin tocar la estructura. Los tokens de aquí son **normativos**; el carácter visual sigue siendo **provisional** hasta que exista una dirección de marca definitiva. Desde la última revisión, el sistema cubre el shell autenticado, el inicio con accesos por rol, los formularios, las tablas, los botones, los buscadores, la paginación y los estados; lo que sigue sin regla propia se enumera en *Drift conocido*, no se presenta como inexistente.

**Key Characteristics:**
- Marca gráfica propia: monograma «L» dentro de un sello de esquina suave, con dos renglones que evocan el libro de inventario.
- Iconografía SVG de trazo único (`1.75px`), sin emoji, sin fuentes de iconos y sin rellenos.
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

## Marca e iconografía

### Marca gráfica

El símbolo es un cuadrado de esquina suave (`8px` sobre una caja de `32px`) con un trazo de `1.5px` al `40 %` de opacidad; dentro, una «L» de `2.25px` y dos renglones cortos al `55 %`. Se lee como una letra inicial sellada sobre una ficha de inventario, no como un isotipo tecnológico. El wordmark «Lari» va en `700`, `0.05em` de interletraje, con «Control de materiales» en versalitas de `0.625rem` y `0.12em`.

- **Shell:** símbolo blanco sobre Tapa, subtítulo en `--sobre-tapa-apagado`.
- **Acceso:** símbolo blanco a `2.5rem`, subtítulo en `--sobre-tapa-apagado`.
- **Cabecera pública:** símbolo en Grafito, subtítulo en Grafito tenue.
- **Favicon:** `static/img/marca.svg`, fondo Tapa y «L» blanca.
- **Regla:** la marca no se rellena con Azul sello, no se inclina, no se le añaden sombras ni se usa como patrón de fondo.

### Iconos

Un solo sprite inline en `templates/parciales/iconos.html`, con símbolos de `24px` y trazo `1.75px`, `currentColor`, extremos y uniones redondeados. Se usan en la navegación lateral, en los accesos rápidos, en los hechos del acceso y en los botones de menú y salida.

- **Tamaño:** `1.05rem` en navegación; `1rem` en botones y hechos; `2rem` de caja para los iconos de acceso.
- **Color:** heredan el texto; el icono activo de la sidebar usa `#9cc3df` como acento sobre Tapa.
- **Accesibilidad:** decorativos con `aria-hidden="true"` y `focusable="false"`; si un botón no lleva texto visible, conserva `aria-label`.
- **Regla:** no se usan emoji, glifos Unicode ni una librería externa como sustituto. Un icono nuevo se dibuja en el sprite y se documenta aquí en el mismo cambio.

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

## Motion

El movimiento es funcional, breve y con una sola intención por superficie. No hay bucles, parallax ni animaciones decorativas permanentes.

- **Entrada de acceso:** `.auth` aparece con `auth-entrada` (`420ms`, `translateY(10px)`, `scale(0.995)`, ease-out exponencial). Es el único gesto de bienvenida.
- **Entrada de accesos:** cada `.acceso` entra con `acceso-entrada` (`260ms`, `translateY(6px)`) y un retardo escalonado de `22ms` por fila, limitado a 7 pasos para que la última fila no supere `~414ms`.
- **Hover:** `160–180ms ease` para color, fondo y borde; el icono del acceso sube `1px`, el botón decorativo se desplaza `2px` y adopta Azul sello.
- **Pulsación:** `transform: translateY(1px)` durante `120ms` en botones y controles del shell.
- **Aviso flotante:** `aviso-entrada` (`220ms`, `translateY(8px)`).
- **Reduced motion:** con `prefers-reduced-motion: reduce` se desactivan todas las animaciones y transiciones anteriores; los estados y el foco siguen visibles.

**Reglas:** una entrada por vista; nada supera `420ms`; no se animan `width`, `height`, `top` ni `left`; el foco nunca depende del movimiento.

## Components

El sistema cubre el shell autenticado (sidebar, topbar, drawer móvil), los componentes de contenido (tabla, buscador, paginación, botones, formularios, etiquetas, detalle, mensajes y estados vacíos), las dos pantallas compuestas (recojos y asignación) y la superficie de acceso. Lo que aún no tiene regla propia —fragmentos de búsqueda y bloques internos de asignación— se enumera en *Drift conocido*.

### Buttons
- **Shape:** `0.4rem` de radio y borde de 1 px.
- **Neutral:** fondo Hoja, texto Grafito, `0.45rem 0.8rem`, altura mínima `2.25rem`. Es el botón por defecto de filtros y acciones secundarias.
- **Primary:** fondo Azul sello, texto blanco, `0.45rem 0.8rem`, peso 600. Se usa en `.boton` para crear, descargar o entrar. En acceso, ancho completo y altura mínima `2.75rem`.
- **Hover / Focus:** el hover del primario oscurece a Azul sello hundido (`#18496b`); el neutro cambia borde y texto a Azul sello. En acceso se añade `translateY(1px)` al pulsar. El foco es siempre `outline: 3px solid var(--acento)` con `outline-offset: 2px`.
- **Secondary:** blanco con filete, texto Grafito, hover Azul sello.
- **Ghost / enlace:** `.boton-enlace`, sin fondo ni borde, Azul sello subrayado, `padding: 0`. Se usa para «Cancelar», que nunca debe parecer primario.
- **En tabla:** `.boton-accion` es el botón compacto de las celdas de acción: altura mínima `1.9rem`, `0.22rem 0.6rem`, texto `0.8125rem`, filete de 1 px y radio `0.4rem`. En reposo es neutro; en hover toma borde y texto Azul sello con fondo Azul sello tenue. La acción destructiva añade `.boton-accion--peligro`: texto Rojo corrección y hover con fondo Rojo pálido. Nunca se usa el botón primario dentro de una fila.

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

Toda tabla con operaciones por fila reserva una última columna «Acciones» alineada a la izquierda, con `.boton-accion` (y `.boton-accion--peligro` para la baja). Los botones se separan `0.35rem`, caben en una sola línea y comparten la altura de la fila; la acción de lectura usa el mismo peso que las demás para no competir con la navegación.

### Detail list
`dl.detalle` en rejilla de dos columnas (`minmax(7rem, max-content)` y `minmax(0, 1fr)`), fondo Hoja, filete y padding `1rem 1.25rem`. Los `dt` van en versalitas de `0.75rem` y Grafito tenue; los `dd` en `0.9375rem` con `overflow-wrap: anywhere` para hashes y códigos largos.

### Messages and empty states
`.mensaje` usa borde completo, fondo tenue y color de estado; no hay franja lateral. `.mensaje-error` rojo, `.mensaje-success` verde y `.mensaje-aviso` ámbar. `.ayuda` es texto Grafito tenue; `.sin-resultados` es un bloque de borde discontinuo, fondo Hoja y texto centrado.

### Menu and summaries
`.menu-modulo` es una rejilla de enlaces/tarjetas para el módulo de registro de materiales; `.resumen-carga` es una rejilla de totales en Hoja con filete. `.fila-alerta` tiñe la fila de Rojo pálido para negativos del dashboard.

### Inicio y accesos rápidos
`templates/inicio.html` deja de ser una bienvenida y pasa a ser un panel de trabajo: `h1` «Inicio», una línea de sesión con correo y rol, y un único panel blanco con filete. Dentro, `.accesos` es una lista en dos columnas separada por filetes tenues, sin tarjetas repetidas ni sombras. Cada `.acceso` alinea un icono en caja de `2rem`, título y descripción breve, y un botón decorativo `.acceso__accion` de `2rem` con chevron al final. En hover la fila se tiñe con `--hoja-hover`, el icono toma borde y fondo de acento, y el botón decorativo se rellena de Azul sello y avanza `2px`. Si el rol tiene un número impar de accesos, el último ocupa las dos columnas. En móvil la lista pasa a una columna. Los enlaces se generan por rol: el tenant ve operación; el almacén, bandeja y traspasos; el administrador, plataforma y catálogo.

### Stock actual
`tecnicos/stock_actual.html` es el índice de custodia por técnico: `h1` «Stock actual», subtítulo de `62ch`, un `.buscador` por NIF o nombre y `.resumen-linea` con técnicos con stock, materiales y unidades. La tabla usa Técnico (enlazado a su detalle de stock), NIF, Estado, Materiales, Unidades y Acciones con el botón `Ver stock`. No muestra códigos de material: para eso se entra al técnico.

`tecnicos/stock_tecnico.html` es el detalle: cabecera con nombre, NIF y estado; botones «Volver a Stock actual» y «Ver ficha»; resumen de materiales y unidades; y tabla de Material, Descripción, Lote, Tipo y Cantidad. Debajo, la sección **«Series en custodia»** lista las series `ASIGNADA` del técnico con Material, Descripción, Lote, Serie y fecha de asignación; el número de serie va en monoespaciada. Los códigos van en monoespaciada y la cantidad se alinea a la derecha con `font-variant-numeric: tabular-nums`. Solo se listan filas con cantidad mayor que cero; si no hay, se muestra el estado vacío. La entrada vive en Operación como «Stock actual» y también como botón secundario en la lista de Técnicos.

### Registro de materiales
`registro_materiales/materiales.html` usa un `.buscador` con selector de técnico y periodo; al enviarlo muestra la tabla **«Órdenes por cargar»** con las órdenes pendientes de ese técnico y periodo, su fecha de creación y el botón `Registrar` de cada fila. El formulario de materiales solo aparece después de elegir una orden y ofrece «Volver a las órdenes». No se escribe el número de orden a mano en el flujo principal: la lista es la fuente de selección.

### Signature: shell autenticado
La estructura de todas las pantallas privadas. Sidebar de `15rem` en Tapa con la marca gráfica, grupos por rol, iconos de trazo único y «Mi perfil» al pie; topbar blanca de `3.5rem` con correo, rol y «Cerrar sesión» con icono; contenido sobre Papel con máximo `1100px`. No hay sombras: sidebar y topbar se separan del contenido por el cambio de superficie y el filete. En móvil la sidebar se convierte en drawer con overlay y el botón «Menú» queda en la topbar.

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
- **Do** resolver las acciones de fila con `.boton-accion` y reservar `.boton-accion--peligro` para lo que desactiva, da de baja o anula; nunca dejes un enlace suelto en la columna «Acciones».
- **Do** tratar el raíl de contexto como parte del patrón de pantalla de trabajo: fijo, pegajoso, con scroll propio y apilado solo en móvil.
- **Do** envolver las tablas nuevas en `.tabla-scroll` o confiar en la envoltura automática del shell para que el móvil no las corte.
- **Do** usar el sprite `parciales/iconos.html` y la marca `parciales/marca.html` antes de dibujar un símbolo nuevo.
- **Do** mantener el trazo de `1.75px`, `currentColor` y `stroke-linecap="round"` en cualquier icono nuevo.
- **Do** dar al último acceso de una lista impar el ancho completo para no dejar una celda vacía.
- **Do** usar `.resumen-linea` y `.columna-numero` en vistas de inventario en lugar de métricas grandes o tarjetas de totales.
- **Do** usar el botón decorativo `.acceso__accion` como affordance, no como acción independiente: toda la fila sigue siendo el enlace.
- **Do** respetar `prefers-reduced-motion` en cualquier animación nueva y mantenerla por debajo de `420ms`.

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
- **Don't** tratar el carácter visual como identidad confirmada. La marca y los iconos son una propuesta de trabajo: este documento se reescribe cuando exista dirección de identidad definitiva.
- **Don't** usar emoji, glifos Unicode, iconos rellenos o una fuente de iconos externa.
- **Don't** dejar un botón que solo lleva icono sin `aria-label`.
- **Don't** rellenar la marca con Azul sello ni usarla como patrón de fondo.
- **Don't** animar propiedades de layout ni encadenar más de una entrada por vista.
- **Don't** usar animaciones en bucle, parallax o movimiento que compita con la lectura de una tabla.

### Drift conocido
- Los fragmentos de búsqueda `.resultado-material` y `.resultado-tecnico` aún no tienen regla propia; heredan el estilo básico de lista. Es la siguiente pieza de UI pendiente.
- Los bloques internos del constructor de asignaciones y del recojo (`.constructor-bloque`, `.filas-bloque`, `.serie-opcion`, `.series-seleccionadas`, `.material-seleccionado`, `.resumen-series`, `.titulo-bloque`, `.material-fila`, `.agregar-fila`, `.quitar-fila`, `.quitar-bloque`) usan controles globales pero no un componente documentado. Funcionan; no están pulidos.
- `templates/inicio.html` ya es un panel de accesos por rol; un resumen de pendientes por rol sería el siguiente paso.
- La configuración 2FA no tiene QR; usa clave manual copiable. Añadirlo requiere una dependencia de generación de QR.
- `.impeccable/design.json` se generó antes del shell y de `componentes.css`; hay que regenerarlo cuando se cierre esta fase.
- Quedan literales por tokenizar: `#fafbfc` (hover de fila), `#f2f8f4` (fondo de éxito) y `#6b4e00` (texto de aviso). No introduzcas nuevos: formalízalos en `:root` cuando toques esas reglas.
- No hay tema oscuro. El sistema es claro por decisión; `color-scheme: light` es explícito.
- El sistema tiene microtransiciones de `160–180ms`, entradas de `220–420ms` en acceso e inicio, y el drawer móvil de `180ms`; todas se desactivan con `prefers-reduced-motion`. No hay animaciones en bucle ni decorativas permanentes.
