# Plan de implementación

Cómo se lleva al Geoportal Ambiental lo que la [revisión de GeoLibre](revision-geolibre.md)
recomienda, con la interfaz del [plan de interfaz minimalista](plan-interfaz-minimalista.md).

**Estado: fases 1 a 6 implementadas y verificadas.** Lo que queda para más adelante está en
[Siguientes pasos](#siguientes-pasos).

## Objetivo

Que cualquier persona consulte la información ambiental de Nariño en un mapa limpio, y que quien
necesite más tenga todo GeoLibre a un clic, sin instalar nada y sin que los datos salgan de la
infraestructura de la Gobernación.

## Decisiones de fondo

| Decisión | Motivo |
| --- | --- |
| GeoLibre no se reimplementa ni se modifica: se integra su compilación web oficial como **Estudio SIG** | Mantener más de mil herramientas al día cuesta un cambio de versión, no un desarrollo |
| El **visor propio** cubre la consulta pública con una interfaz mínima | Un visitante no debe aprender un SIG para ver una capa |
| El visor toma de GeoLibre patrones y nombres (paleta, atajos, parámetros de URL) | Quien pasa del visor al Estudio no cambia de costumbres |
| Todo cambio de la API va en las dos ediciones (Python y PHP) | Un solo contrato para el sitio estático |
| Sin paso de compilación en `portal/` | Se instala subiendo archivos a Plesk |

## Punto de partida

Ya existían: catálogo y administrador de geodatos, ingesta, proyectos `.geolibre`, Estudio SIG
integrado con su configuración (`deployment.json`), modo oscuro, y en el visor búsqueda, medición,
terreno 3D, tabla de atributos, enlace permanente e imagen PNG. La interfaz del visor tenía un
panel acoplado de 360 px y trece botones sobre el mapa.

## Fases

### Fase 1 · Interfaz minimalista del visor

| Entregable | Archivos | Criterio | Estado |
| --- | --- | --- | --- |
| Mapa a toda la vista con una tarjeta flotante (búsqueda + capas) | `portal/index.html`, `assets/css/visor.css` | Mapa ≥ 85 % de la ventana | ✔ 89 % |
| Capas de una línea con detalle desplegable («⋯») y categorías plegables | `assets/js/visor.js` | Filas ≤ 40 px; un detalle abierto a la vez | ✔ |
| Un único botón de herramientas con menú; solo acercar, alejar y brújula a la vista | `assets/js/visor-herramientas.js` | 4 botones sobre el mapa | ✔ |
| Leyenda plegada que recuerda la elección; coordenadas en una píldora | `visor.css`, `visor.js` | Leyenda plegada al abrir | ✔ |
| Encabezado más bajo; disposición de una fila en teléfono | `assets/css/institucional.css`, `visor.css` | Tarjeta ≤ 56 px en teléfono | ✔ |

### Fase 2 · Paleta de comandos

| Entregable | Archivos | Criterio | Estado |
| --- | --- | --- | --- |
| Registro único de acciones que alimenta el menú y la paleta | `visor-herramientas.js` (`ACCIONES`) | Una acción se define una vez | ✔ |
| La búsqueda encuentra acciones, capas, mapas base, coordenadas, entidades y lugares | `visor-herramientas.js` | «medir ar» + `Enter` mide; el nombre de una capa la enciende | ✔ |
| Acciones frecuentes al enfocar; `>` limita a acciones | `visor-herramientas.js` | Lista visible sin escribir | ✔ |
| Atajos nuevos: `H`, `F`, `P` | `visor-herramientas.js`, `index.html` | Documentados en el diálogo de atajos | ✔ |

### Fase 3 · Funciones de GeoLibre en el visor

| Función | Cómo queda | Archivos | Estado |
| --- | --- | --- | --- |
| Añadir datos propios | GeoJSON, Shapefile (.zip), GeoPackage, KML/KMZ, GPX, CSV y GeoTIFF se leen en el navegador y no se suben; GeoJSON por URL, WMS y XYZ; también arrastrando al mapa. Grupo «Mis datos» | `visor-herramientas.js`, `visor.js`, `ingesta-navegador.js` | ✔ |
| Filtrar el mapa desde la tabla | Casilla «Filtrar también el mapa» | `visor-herramientas.js` | ✔ |
| Imprimir | Hoja A4 horizontal con encabezado institucional, norte, escala gráfica, leyenda y fuente | `visor-herramientas.js`, `visor.css` | ✔ |
| Insertar el mapa | Diálogo con el código `<iframe>` de la vista actual | `visor-herramientas.js`, `index.html` | ✔ |
| Mi ubicación y pantalla completa | En el menú; en pantallas táctiles, además, el control de ubicación | `visor-herramientas.js` | ✔ |
| GPX | Lectura en el navegador; admitido también al cargar en el administrador (edición PHP) | `ingesta-navegador.js`, `portal/api/lib/geodatos.php`, `admin.js` | ✔ |
| Escala numérica correcta | MapLibre usa teselas de 512 px: la escala mostrada era el doble | `visor-herramientas.js` | ✔ corregido |

### Fase 4 · Parámetros de presentación e incrustación

| Entregable | Detalle | Archivos | Estado |
| --- | --- | --- | --- |
| `?maponly=1` (o `?solomapa=1`) | Solo el mapa, con zoom, leyenda y enlace al geoportal | `visor.js`, `visor.css` | ✔ |
| `?panels=collapsed` (o `?paneles=plegados`) | La lista de capas empieza plegada | `visor.js` | ✔ |
| `?theme=dark\|light` (o `?tema=oscuro\|claro`) | Tema para esa visita, sin guardarlo ni parpadeo al cargar | `institucional.js`, `index.html` | ✔ |
| `?lat=&lon=&zoom=` | Vista inicial, además de `?mapa=` | `visor-herramientas.js` | ✔ |
| Incrustar desde otro sitio | Docker: `X-Frame-Options` solo se omite con `maponly`. Plesk (PHP): el visor no envía esa cabecera; el administrador sí la deniega | `proxy/nginx.conf` | ✔ |
| Las capas del visitante no salen en enlaces, proyectos ni código para insertar | — | `visor.js`, `visor-herramientas.js` | ✔ |

### Fase 5 · Estudio SIG minimalista

| Entregable | Detalle | Archivos | Estado |
| --- | --- | --- | --- |
| Disposición en el archivo de interfaz | `layout`: barra con iconos, lista compacta, paneles visibles | `portal/api/lib/geolibre.php`, `api/app/services/estudio.py` | ✔ |
| Paneles plegados al abrir | `panels=collapsed` en los enlaces del servidor y del visor | `capas.php`, `estudio.py`, `visor.js` | ✔ |
| Preajustes Esencial, Estándar, Completo y Solo consulta | Botones que rellenan nivel, modo y disposición | `portal/admin/index.html`, `assets/js/admin.js` | ✔ |
| Valores por defecto sobrios | Nivel intermedio, iconos, paneles plegados, sin Explorador ni Comentarios | `geolibre.php`, `estudio.py` | ✔ |
| Instalaciones existentes | Si el archivo de interfaz es de una versión anterior, `/api/config` lo regenera | `geolibre.php`, `estudio.py` | ✔ |

Quien ya guardó ajustes del Estudio conserva su nivel; la disposición nueva se aplica con los
valores por defecto y se cambia en *Administrador → Estudio SIG → Interfaz y menús*.

### Fase 6 · Calidad y documentación

| Entregable | Detalle | Estado |
| --- | --- | --- |
| Pruebas de la API | `api/tests/` (27) y `pruebas/edicion_php/` (7): disposición, preajustes, `panels=collapsed`, regeneración del archivo de interfaz | ✔ |
| Prueba de extremo a extremo de la interfaz | 40 comprobaciones en Chromium contra el Plesk simulado: estructura, paleta, menú, datos propios, tabla, impresión, insertar, solo el mapa, parámetros, teléfono | ✔ |
| Prueba de extremo a extremo del Estudio | Preajustes en el administrador, archivo de interfaz, GeoLibre con barra de iconos y la API de incrustación respondiendo | ✔ |
| Documentación | Revisión, anexo con el inventario, los dos planes y las guías actualizadas | ✔ |

## Trazabilidad: de GeoLibre al geoportal

| En GeoLibre | En el geoportal |
| --- | --- |
| Paleta de comandos (`Ctrl` + `K`) | Búsqueda del visor |
| Atajos `N`, `U`, `R`, `?` | Los mismos, más `L`, `H`, `M`, `A`, `T`, `F`, `P` |
| `maponly`, `panels=collapsed`, `theme`, `lat`/`lon`/`zoom` | Los mismos parámetros en el visor |
| Añadir datos · arrastrar y soltar | «Añadir datos…» y arrastrar al mapa (sin subir) |
| Panel de capas: visibilidad, opacidad, orden, grupos | Tarjeta de capas con categorías |
| Tabla de atributos y filtros | Tabla con filtro aplicado al mapa y CSV |
| Medir, buscar lugares y coordenadas, identificar | En el visor |
| Composición de impresión · exportar imagen | «Imprimir…» y «Descargar imagen» |
| Compartir e incrustar | Enlace permanente y «Insertar el mapa…» |
| Niveles de interfaz, `layout`, `settingsUrl` | Preajustes del Estudio en el administrador |
| Todo lo demás (edición, estilos, SQL, geoprocesamiento, 3D, complementos) | Estudio SIG |

## Siguientes pasos

No forman parte de esta entrega. Hoy se resuelven en el Estudio SIG.

| Tema | Qué sería | Por qué queda para después |
| --- | --- | --- |
| Simbología graduada y categorizada | Definirla en el administrador y dibujarla en el visor | Cambia el modelo de datos y las dos API |
| Filtros rápidos por capa | Controles de valores, rangos y fechas en el visor | Depende del punto anterior |
| Dibujar y anotar | Bocetos del visitante exportables | El Estudio trae un editor completo |
| Comparar con cortinilla y marcadores de vista | Deslizar dos capas; guardar vistas con nombre | Uso menos frecuente en consulta pública |
| Interfaz del visor en inglés | Catálogo de textos y selector | El público objetivo es hispanohablante |
| Servicios OGC propios (WMS, WFS) | Publicar las capas para otros SIG | Requiere servidor de mapas |
| Uso sin conexión | Aplicación instalable con teselas guardadas | GeoLibre lo ofrece en su aplicación |

## Verificación

```bash
cd api && python -m pytest -q
```

```bash
GP_MYSQL_USER=usuario GP_MYSQL_PASSWORD=clave python -m pytest -q pruebas/edicion_php
```

```bash
for f in portal/assets/js/*.js; do node --check "$f"; done
```

Las pruebas de extremo a extremo usan Playwright contra una instalación en subcarpeta anidada
(`/secretarias/ambiente/geoportal/`) de un Plesk simulado: nginx delante de Apache, PHP-FPM con
`open_basedir` y MySQL 8.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| Una versión nueva de GeoLibre cambia parámetros o el archivo de interfaz | Versión fijada por SHA-256; la revisión y la prueba del Estudio se repiten al actualizar |
| Los servicios de lugares (Photon, Nominatim) fallan o limitan | Dos servicios con tiempo límite; coordenadas, capas y acciones funcionan sin ellos |
| Un archivo local muy grande bloquea el navegador | Límite de 200 MB y mensaje claro; no afecta al servidor |
| Servicios WMS o XYZ de terceros sin CORS o caídos | Solo afectan a la capa añadida por el visitante |
| Incrustación del visor en sitios ajenos | Solo en modo «solo el mapa», que es de lectura; el administrador nunca se puede enmarcar |
