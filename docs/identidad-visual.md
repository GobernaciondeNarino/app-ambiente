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

## Modo oscuro

El tema oscuro conserva la identidad: el verde institucional `#10A13B` sigue en barras,
botones y acentos (los botones primarios usan `#0B7A2C` para mantener el contraste del texto
blanco) y el amarillo `#FFD500` en el foco y los resaltados. Solo cambian las superficies y los
textos, definidos como variables en `portal/assets/css/institucional.css`
(`:root[data-tema="oscuro"]`):

| Variable | Claro | Oscuro |
| --- | --- | --- |
| `--fondo` / `--superficie` | `#f5f7f5` / `#ffffff` | `#0f1411` / `#161c18` |
| `--gris-titulo` / `--gris-texto` | `#383838` / `#4d4d4d` | `#eef2ef` / `#c9d1cb` |
| `--verde-oscuro` (textos de acento) | `#0b7a2c` | `#5fd08a` (contraste AA sobre fondo oscuro) |
| `--enlace` | `#0b7a2c` | `#6fd896` |

En modo oscuro el logotipo se muestra sobre una placa blanca, para conservar sus colores
originales y su legibilidad sin alterarlo. El tema se elige con el botón de la barra GOV.CO (automático, claro
u oscuro), se aplica antes de pintar la página para evitar destellos y se comparte con el mapa
base del visor (OpenFreeMap Dark) y con el Estudio SIG (tema oscuro de GeoLibre con el acento
verde institucional).
