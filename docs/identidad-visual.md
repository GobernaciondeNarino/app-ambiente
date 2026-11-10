# Aplicación de la identidad visual

El diseño sigue los documentos institucionales:

- *Arquitectura de marca y directrices — Manual de Identidad Visual*, v1.0, junio 2024.
- *Manual de Usabilidad y Estructura de los Sitios Web*, v1.0, marzo 2025.

## Colores

| Uso | Color | Fuente |
| --- | --- | --- |
| Amarillo institucional | `#FFD500` (R255 G214 B5) | MIV, colores principales |
| Verde institucional | `#10A13B` (R16 G161 B59) | MIV, colores principales |
| Títulos | `#383838` | MIV, tipografía |
| Textos | `#4D4D4D` | MIV, tipografía |
| Verde para botones con texto blanco | `#0B7A2C` | Variante oscura del verde institucional, para cumplir contraste WCAG AA (el texto blanco sobre `#10A13B` no alcanza 4,5:1) |

El amarillo se usa como acento (botón «Abrir en GeoLibre», línea bajo la barra
GOV.CO, subrayado de títulos) y nunca como fondo de texto blanco. Los colores de
las categorías temáticas derivan de la paleta principal.

Todos los valores están como variables CSS en `portal/assets/css/institucional.css`.

## Tipografía

- **Hind Madurai** (principal): títulos, menús, botones y etiquetas.
- **Source Sans 3** (secundaria): textos corridos, tablas y formularios.

Ambas se cargan desde Google Fonts.

## Estructura (Manual de sitios web)

- **Barra superior GOV.CO** con enlace a gov.co, separada por una línea amarilla.
- **Encabezado** con el logotipo de la Gobernación de Nariño y el nombre de la
  dependencia, y menú de navegación a la derecha.
- **Pie de página** en tres columnas con líneas delgadas oscuras: logotipo,
  dirección y horario, redes sociales y políticas; información de la
  dependencia; correo institucional, notificaciones judiciales, líneas de
  atención y línea gratuita.
- **Hora legal de la República de Colombia** al final del pie (zona
  `America/Bogota`).

Los datos de contacto del pie se editan en
`portal/assets/js/config-institucional.js` (no requiere compilar). Allí también
se configuran las URL de las redes sociales oficiales: un ícono solo aparece si
su URL está definida.

## Logotipo

`portal/assets/img/logo-gobernacion-narino.png` se extrajo del manual de sitios
web. Para máxima nitidez, reemplácelo por el archivo vectorial oficial (SVG o PNG
de alta resolución) entregado por la Oficina de Comunicaciones, manteniendo el
mismo nombre de archivo. Respete el espacio libre y el tamaño mínimo del MIV.

El símbolo de la barra GOV.CO es un marcador genérico: sustitúyalo por el
logotipo oficial del kit GOV.CO de MinTIC.

## Accesibilidad

- Enlace «Saltar al contenido», foco visible (amarillo institucional) y
  navegación completa por teclado.
- Textos alternativos, etiquetas en todos los campos y regiones con `aria-label`.
- Respeta `prefers-reduced-motion`.
- Diseño adaptable: en móvil el mapa ocupa la pantalla y el panel de capas se
  abre con un botón.
