# Plan de interfaz minimalista

Cómo se ve y se usa el Geoportal Ambiental: el mapa primero, pocas cosas a la vista y todas a
mano. Parte de la [revisión de GeoLibre](revision-geolibre.md) y se ejecuta con el
[plan de implementación](plan-implementacion.md).

**Estado: implementado y verificado** (ver [criterios de aceptación](#criterios-de-aceptación)).

## Alcance

| Superficie | Qué cambia |
| --- | --- |
| Visor público | Rediseño completo |
| Estudio SIG (GeoLibre) | Presentación minimalista por defecto, con preajustes en el administrador |
| Encabezado institucional | Más bajo (60 px), en todas las páginas |
| Catálogo, «Acerca», administrador y asistente de instalación | Sin cambios de estructura: ya son sobrios y de una sola tarea por pantalla |

## Principios

1. **El mapa es el contenido.** Nada se acopla a su lado: todo flota sobre él y se puede plegar.
2. **Una cosa de cada tipo.** Una caja de búsqueda, una tarjeta, un botón de herramientas.
3. **Divulgación progresiva.** A la vista, lo que usa cualquier visitante; a un clic, lo de cada
   capa; en la paleta de comandos, todo lo demás.
4. **Texto antes que iconos sueltos.** Las herramientas se eligen en un menú con nombre y atajo,
   no en una columna de símbolos que hay que adivinar.
5. **Los mismos gestos que GeoLibre.** `Ctrl` + `K`, `N`, `U`, `R`, `?` y los parámetros
   `maponly`, `panels`, `theme`, `lat`/`lon`/`zoom` significan lo mismo en el visor y en el Estudio.
6. **La identidad no se negocia.** Barra GOV.CO, logotipo, verde `#10A13B`, amarillo `#FFD500`,
   Hind Madurai y Source Sans 3, pie institucional y modo oscuro, como en
   [identidad visual](identidad-visual.md).
7. **Accesible por defecto.** Teclado completo, foco visible, contraste AA, objetivos táctiles
   cómodos y respeto por `prefers-reduced-motion`.

## Antes y después

| Medida (ventana de 1440 × 900) | Antes | Después |
| --- | --- | --- |
| Parte de la ventana que ocupa el mapa | 66 % | 89 % |
| Botones sobre el mapa | 13 | 4 (acercar, alejar, brújula, herramientas) |
| Cajas de búsqueda | 2 | 1 |
| Botones por capa en la lista | 2 a 5 | 1 («⋯») |
| Alto de cada capa en la lista | Unos 50 px (90 px si está encendida) | 36 px |
| Leyenda | Abierta | Plegada (recuerda la elección) |
| Encabezado | 68 px | 60 px |

## Disposición

Escritorio:

```
┌ GOV.CO ───────────────────────────────────────────── narino.gov.co · Contacto · ◐ ┐
├ [logo] Geoportal Ambiental                    Visor  Catálogo  Estudio SIG  Acerca ┤ 60 px
│ ┌───────────────────────────┐                                              ┌───┐ │
│ │ 🔍 Buscar capas, lugares… │                                              │ + │ │
│ ├───────────────────────────┤                                              │ − │ │
│ │ ≋ Capas            3 de 9 ⌄│                                              │ ▲ │ │
│ │ • Recurso hídrico        3 │                 M A P A                      ├───┤ │
│ │ ☑ ━ Ríos principales    ⋯ │                                              │ ≡ │ │
│ │ ☐ ▭ Humedales           ⋯ │                                              └───┘ │
│ └───────────────────────────┘                                                    │
│ ▁▁ 30 km               Lat 1,2136  Lon -77,2811 · 1:50.000          [≣ Leyenda ›] │
└────────────────────────────────────────────────────────────────────────────────────┘
```

Teléfono: la tarjeta es una sola fila y la lista se abre debajo.

```
┌──────────────────────────┐
│ GOV.CO                 ◐ │
│ [logo] Geoportal      ☰  │
│ ┌──────────────┬─────┐ + │
│ │ 🔍 Buscar…   │≋ 3/9│ − │
│ └──────────────┴─────┘ ▲ │
│                        ≡ │
│         M A P A          │
│              [≣ Leyenda] │
└──────────────────────────┘
```

## Componentes

### Tarjeta del mapa

Una tarjeta translúcida de 320 px arriba a la izquierda, con dos partes:

- **Búsqueda y paleta de comandos.** Al enfocarla muestra las acciones frecuentes. Al escribir
  busca, en este orden: coordenadas, capas (enciende o apaga), acciones y mapas base, entidades de
  las capas encendidas y lugares de OpenStreetMap. Empezar con `>` limita a acciones. Un comando
  limpia la caja al ejecutarse; un lugar o una entidad dejan el texto.
- **Capas.** Cabecera «Capas · 3 de 9» que pliega la lista (`L`). Dentro, categorías plegables;
  con más de 12 capas solo se abren las que tienen algo encendido.

### Fila de capa

```
☑  ━  Ríos principales                                  ⋯
```

Casilla, muestra de símbolo, nombre en una línea y «⋯». Al pulsar «⋯» se abre debajo el detalle,
uno a la vez:

```
   Línea · 3 entidades
   Opacidad  ━━━━━━━━━●
   [Acercar] [Ficha] [Tabla] [Estudio SIG] [Subir] [Bajar]
```

Las capas añadidas por el visitante van en el grupo «Mis datos» y ofrecen «Quitar» en lugar de
«Ficha».

### Menú de herramientas

Un botón bajo los controles de navegación (`H`) abre un menú con nombre y atajo:

| Grupo | Elementos |
| --- | --- |
| Mapa base | Cuadrícula de 7 miniaturas |
| Medir y ver | Medir distancia (`M`), Medir área (`A`), Terreno 3D (`T`), Mi ubicación, Añadir datos… |
| Compartir | Copiar enlace de esta vista, Insertar el mapa…, Descargar imagen, Imprimir… (`P`) |
| Vista | Pantalla completa, Solo el mapa (`F`), Atajos de teclado (`?`) |

Solo en la paleta: cambiar tema, abrir el Estudio SIG, ir al catálogo, ver todo Nariño (`R`),
orientar al norte (`N`), apagar todas las capas, descargar el proyecto `.geolibre`.

### Leyenda, coordenadas y paneles a demanda

- **Leyenda:** ficha «Leyenda» abajo a la derecha; se despliega al pulsarla y recuerda la elección.
- **Coordenadas:** píldora centrada abajo; un clic cambia el formato (decimales, GMS, minutos
  decimales, UTM, MAGNA-SIRGAS). En teléfono no se muestra.
- **Medición y tabla de atributos:** aparecen solo mientras se usan. La tabla ocupa el 40 %
  inferior y puede filtrar también el mapa.

### Diálogos

Ficha de metadatos, «Añadir datos» (zona para soltar un archivo, o una dirección GeoJSON, WMS o
XYZ), «Insertar el mapa» (código `<iframe>` con ancho, alto y «solo el mapa») y atajos de teclado.
Uno a la vez, cerrables con `Esc`.

### Solo el mapa

- **Tecla `F`:** oculta barra GOV.CO, encabezado, tarjeta, coordenadas y menú. Queda el mapa con
  zoom, leyenda y una ficha «Mostrar la interfaz».
- **`?maponly=1` en la dirección:** lo mismo, pensado para incrustar el mapa en otra página; la
  ficha lleva al geoportal completo y los atajos que cambian la interfaz quedan apagados.

### Impresión

`P` o «Imprimir…» compone una hoja A4 horizontal: logotipo y título, mapa, norte, escala gráfica,
leyenda, coordenadas del centro, mapa base, fuente y fecha.

## Niveles de divulgación

| Nivel | Dónde | Qué hay |
| --- | --- | --- |
| 1. Siempre a la vista | Mapa | Buscar, capas (encender y apagar), acercar, alejar, brújula, herramientas, leyenda plegada |
| 2. A un clic | «⋯» de la capa y menú de herramientas | Opacidad, orden, ficha, tabla, mapas base, medir, 3D, ubicación, añadir datos, compartir, imprimir |
| 3. En la paleta (`Ctrl` + `K`) | Búsqueda | Todas las acciones, capas por nombre, mapas base, coordenadas, entidades y lugares |
| 4. En el Estudio SIG | Menú superior | Todo GeoLibre: edición, estilos, SQL, geoprocesamiento, 3D, composición de impresión |

## Reglas visuales

| Elemento | Regla |
| --- | --- |
| Superficies flotantes | Fondo `--vidrio` con desenfoque de 10 px, radio de 12 px, sombra `--sombra`; sin bordes |
| Color | Verde institucional solo para estado activo, foco y acento; el resto, grises del tema |
| Tipografía | Títulos y botones en Hind Madurai; texto en Source Sans 3; capas a 14,5 px |
| Iconos | Trazo de 1,8 px, 16 a 18 px, siempre con nombre accesible |
| Densidad | Filas de 36 px en escritorio; objetivos táctiles de 40 px o más en teléfono |
| Movimiento | Transiciones de 150 a 200 ms; ninguna si el sistema pide movimiento reducido |
| Tema | Claro y oscuro con las mismas reglas; el mapa base sigue al tema |

## Teclado

| Tecla | Acción |
| --- | --- |
| `Ctrl` + `K` | Buscar o ejecutar una acción |
| `L` · `H` | Plegar la lista de capas · abrir el menú de herramientas |
| `M` · `A` · `T` | Medir distancia · medir área · terreno 3D |
| `N` · `U` · `R` | Norte arriba · quitar inclinación · ver todo Nariño |
| `F` · `P` · `?` | Solo el mapa · imprimir · atajos |
| `Enter` · `Esc` | Terminar o cancelar la medición; `Esc` cierra menús, tabla y diálogos |

## Estudio SIG minimalista

GeoLibre se presenta con sus propios mecanismos (parámetros de URL y archivo de interfaz), sin
modificarlo. El administrador elige un preajuste en *Estudio SIG → Interfaz y menús* y puede
ajustar cada campo.

| Preajuste | Nivel | Barra superior | Paneles | Para quién |
| --- | --- | --- | --- | --- |
| Esencial | Inicial | Iconos | Capas, plegado | Consulta con algo de edición; sin menú de procesamiento |
| **Estándar** (por defecto) | Intermedio | Iconos | Capas y Estilo, plegados | Análisis vectorial, SQL y tablero con interfaz sobria |
| Completo | Avanzado | Con texto | Capas, Explorador, Estilo y Comentarios, abiertos | Especialistas: todas las herramientas a la vista |
| Solo consulta | Inicial | Ver, Controles y Ayuda | Capas | Mapa de solo lectura (`layout=viewer`) |

El visitante puede cambiar el nivel desde GeoLibre (*Ayuda → Simplificar la interfaz*) salvo que
el administrador lo bloquee. El tema, el idioma y el acento siguen al portal.

## Accesibilidad

- Orden de foco: búsqueda, capas, mapa con sus controles, leyenda.
- El menú de herramientas usa `role="menu"`, flechas para moverse y `Esc` para cerrar; las
  opciones con estado usan `menuitemcheckbox`.
- Los resultados de búsqueda son un `listbox` navegable con flechas.
- «⋯» anuncia la capa («Opciones de Ríos principales») y su estado con `aria-expanded`.
- Todo control con solo icono tiene nombre accesible y `title`.
- Contraste AA en ambos temas; el foco usa el amarillo institucional.

## Criterios de aceptación

Comprobados con una prueba de extremo a extremo en navegador (Chromium, Plesk simulado):

| Criterio | Resultado |
| --- | --- |
| El mapa ocupa al menos el 85 % de la ventana de escritorio | ✔ 89 % |
| Cuatro botones visibles sobre el mapa y una sola caja de búsqueda | ✔ |
| Capas de una línea (40 px o menos) y un solo detalle abierto a la vez | ✔ |
| La paleta ejecuta acciones, enciende capas y cambia el mapa base | ✔ |
| El menú abre con `H`, lista 7 mapas base y 12 acciones, y marca las activas | ✔ |
| Añadir GeoJSON, GPX y WMS sin subirlos; arrastrar un archivo al mapa | ✔ |
| El enlace permanente y el código para insertar no incluyen las capas del visitante | ✔ |
| El filtro de la tabla se aplica al mapa y se restaura al cerrarla | ✔ |
| La hoja de impresión lleva mapa, título, escala y fuente | ✔ |
| `F` y `?maponly=1` dejan solo el mapa; incrustado, `F` no hace nada | ✔ |
| `?theme=dark&panels=collapsed&lat=&lon=&zoom=` se respetan sin guardar el tema | ✔ |
| En teléfono la tarjeta es una fila y el menú cabe en la pantalla | ✔ |
| Preajustes del Estudio: Esencial, Estándar y Completo cambian nivel y disposición | ✔ |
| Sin errores de JavaScript en todo el recorrido | ✔ |
