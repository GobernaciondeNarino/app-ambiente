# Inventario de la interfaz y las funciones de web.geolibre.app (GeoLibre 3.9.0)

> Investigación de solo lectura hecha el 17 de noviembre de 2026 sobre la aplicación pública <https://web.geolibre.app/>,
> para reproducir en el Geoportal Ambiental la misma interfaz y las mismas funciones usando la compilación web oficial de
> GeoLibre. Contrasta el [anexo de la 3.7.0](anexo-inventario-geolibre.md)
> (GeoLibre 3.7.0, commit `646b530`) con lo que sirve hoy la web.

> **Evidencia.** Las capturas, los JSON de red y del DOM y las salidas de REA citadas entre paréntesis
> se generaron en el entorno de trabajo y no se versionan (pesan cientos de megabytes); los nombres de
> archivo se conservan como referencia. REA está instalado en el proyecto (ver `.claude/REA-PROCEDENCIA.md`)
> y el inventario se puede repetir con las mismas herramientas.
>
> **Actualización posterior (mismo día).** La fila «Menú Proyecto» de la comparación (§10) describe el
> estado observado antes de alojar el servicio de compartir: con el servicio propio
> (`<geoportal>/api/compartir`) y el geoportal servido por HTTPS, **Galería…** y **Compartir…** quedan
> habilitados y funcionan (ver [GeoLibre: el mapa del geoportal](estudio-sig.md#compartir-y-galería)).
> GeoLibre solo acepta un servicio de compartir en `https` (o en `localhost`), por eso en el Plesk
> simulado por `http` aparecían deshabilitados.

**Método y evidencia.** Navegador Chromium 153 sin interfaz (Playwright), contexto `locale: es-CO`, ventanas de 1857×982
(como la captura del usuario) y 1440×900. Todo lo que se afirma aquí sale de una de estas fuentes, citadas entre paréntesis:

| Marca | Fuente | Carpeta (relativa a este archivo) |
| --- | --- | --- |
| (DOM) | Texto y atributos accesibles (`aria-label`, `title`, `role`) leídos del DOM en vivo | `menus/`, `menus-en/`, `paneles/`, `dialogos/`, `funciones/`, `capa/`, `parametros/` (JSON + PNG) |
| (red) | Peticiones registradas por Playwright durante cada acción, o por REA `capture-browser-scenario` | `*.json` de cada carpeta, `rea/escenario-evidence.json` |
| (cap.) | Captura de pantalla PNG | misma carpeta que el JSON |
| (paquete) | Análisis estático del paquete JavaScript descargado (sin ejecutarlo) y REA `analyze-web-bundle` | `rea/bundle-evidence.json`, `i18n/diff-es-370-390.json`, `red/hosts-estaticos.txt` |

Para cada acción de menú se abrió la app limpia (o se recargó), se pulsó el elemento, se esperó 2,5–9 s y se guardaron el
diálogo (título, texto, botones, campos), el texto nuevo de la página, las peticiones de red y las ventanas emergentes.
No se inició sesión, no se subió ni compartió nada, no se configuraron claves de IA y no se ejecutó ninguna herramienta de
procesamiento.

## 1. Versión servida

| Dato | Valor | Evidencia |
| --- | --- | --- |
| Versión | **GeoLibre v3.9.0** | Ayuda → Acerca de muestra «Versión v3.9.0» (DOM, `dialogos/dlg-ayuda-acerca-de.png`); el paquete emite `geolibre:ready` con `version:"3.9.0"` (`App-ZrgZbNEI.js`) y declara `appVersion:"3.9.0"` (paquete) |
| Publicación | GitHub Pages (página 404 de GitHub Pages para rutas inexistentes) | (red) `https://web.geolibre.app/version.json` → 404 de GitHub Pages |
| Configuración del despliegue | `deployment.json` = `null`, `admin-profile.json` = `null`, `geolibre-runtime-config.js` = `window.__GEOLIBRE_DEPLOYMENT_ENV__ = {}` | (red) descargados en `descarga/` |
| Manifiesto PWA | `name: GeoLibre`, `display: standalone`, `theme_color: #2f8f85`, iconos 192/512 y *maskable* | (red) `manifest.webmanifest` |
| Tamaño | 586 recursos en `assets/` (189 MB con WASM: DuckDB, Whitebox, GDAL/`geolibre-cli`, ONNX, DGGAL…); 265 scripts observados en la carga | (paquete) recorrido recursivo de `__vite__mapDeps`; REA |
| Bienvenida | En esta web no aparece ningún asistente de bienvenida al cargar sin parámetros (1857×982 y 1440×900) | (cap.) `crudo/carga-1857x982.png`, `parametros/param-sin-parametros.png` |
| Última versión publicada | Etiquetas `v3.7.0`, `v3.8.0` y `v3.9.0` en `opengeos/GeoLibre`; no hay etiqueta posterior a la 3.9.0 | `git ls-remote --tags` |

## 2. Disposición general de la pantalla (1857×982, sin capas)

| Zona | Qué se ve (DOM) |
| --- | --- |
| Barra superior | Logotipo «GeoLibre» (icono de mapa), 9 botones de menú con icono y texto: **Proyecto, Editar, Ver, Añadir datos, Procesamiento, Controles, Complementos, Configuración, Ayuda**; a la derecha, botón de tema (luna/sol, `aria-label` «Cambiar a modo oscuro» / «Cambiar a modo claro») y campo de texto «Nombre del proyecto» con marcador «Proyecto sin título» |
| Riel izquierdo | Pestañas verticales **EXPLORADOR** («Expandir Explorador») y **CAPAS** («Contraer Capas») |
| Panel izquierdo | Panel «Capas» (320 px, variable CSS `--layer-panel-width`) con barra de 8 iconos, lista de capas (fila «Fondo») y buscador al pie |
| Mapa | Globo MapLibre con mapa base OpenFreeMap Liberty, cielo estrellado (Efectos atmosféricos), 4 controles arriba a la derecha, escala abajo a la izquierda y atribución compacta (ⓘ) abajo a la derecha |
| Riel derecho | Pestañas verticales **COMENTARIOS** y **ESTILO** (aparecen otras al abrir paneles acoplables, p. ej. **MAPAS BASE**) |
| Barra de estado | `Coords.: — · Zoom: 2.00 · Alt. cámara: 20.438 km · Rumbo: 0.0° · Inclinación: 0.0° · BBox: -180.0000, -36.2526, 180.0000, 90.0000` y, a la derecha, «⛭ Diagnóstico: 0» |

Tipografía IBM Plex Sans/Mono servida desde el propio origen (`ibm-plex-sans-*.woff2`), sin Google Fonts (red).
Componentes Radix (menús `role=menu`, `menuitem`, `menuitemradio`, `menuitemcheckbox`) e iconos Lucide (DOM).

## 3. Barra superior: menús y elementos

Recorrido automático de todos los menús y submenús (abriendo cada ruta desde cero) en español y en inglés (`?locale=en`).
La columna «Clave visible en inglés» es el texto que muestra la misma posición con `locale=en`; los identificadores internos
(`project.new`, etc.) no se ven en el DOM y están en el §1.7 del anexo. Capturas: `menus/menu-*.png`; datos completos:
`menus/menus-es.json`, `menus-en/menus-en.json` y los árboles de texto `menus-es-arbol.txt` / `menus-en-arbol.txt`.

**Recuento (DOM):** 9 menús · 174 entradas de primer nivel · 1 438 hojas (de ellas 1 068 son herramientas Whitebox).

| Menú | Entradas de 1.er nivel | Hojas | Submenús de 1.er nivel |
| --- | --- | --- | --- |
| Proyecto | 15 | 20 | Abrir desde, Abrir reciente (deshabilitado sin recientes), Importar, Exportar |
| Editar | 8 | 8 | — (todo deshabilitado sin capas ni selección) |
| Ver | 11 | 23 | Restablecer orientación (deshabilitado con rumbo e inclinación 0), Vista dividida, Vista previa de visión del color, Motor de renderizado |
| Añadir datos | 44 (en 5 grupos con rótulo) | 44 | — |
| Procesamiento | 21 | 1 159 | 9 categorías Whitebox, Caja de herramientas de GeoLibre |
| Controles | 35 | 41 | Logotipos, Efectos atmosféricos, Clima |
| Complementos | 19 | 81 | GeoEditor, Anotaciones, Acotaciones, Servicios web (36), Vista de calle, Mapillary, DGGS (8) |
| Configuración | 12 | 53 | Idioma (24 + paquetes), Diseño, Apariencia, Interfaz |
| Ayuda | 9 | 9 | — |

Caja de herramientas de Whitebox (submenús de Procesamiento, hojas contadas en el DOM): Vectorial 313 · Ráster 256 ·
Teledetección 154 · Hidrología 100 · Terreno 99 · LiDAR 67 · Conversión 49 · Red 26 · Proyección 4 = **1 068**. El diálogo
«Caja de herramientas de Whitebox» dice «Todas (1069)» y «Ejecutando localmente con WebAssembly. No se requiere sidecar.»
(DOM, `funciones/pr-pr-caja-de-herramientas-de-whitebox.png`). Los nombres de las herramientas Whitebox y sus subcategorías
(«GeoLibre (WASM)», «Flow Routing», …) **no están traducidos** en español.

### 3.1 Tablas de menús (español → inglés)

Tercer nivel no incluido en las tablas: Controles → Clima → Nubes → «Mostrar nubes» y → Precipitación → «Mostrar
precipitación»; las hojas Whitebox, en `menus-es-arbol.txt`. En Controles, la marca «✓» forma parte del texto del elemento
(no es `menuitemcheckbox`) e indica que el control está activo por defecto. En «Efectos atmosféricos», los rótulos «Color del
halo», «Extensión del halo 2.80×», «Intensidad del halo 100%» y «Color del espacio» acompañan selectores de color y
deslizadores dentro del propio menú.

#### Proyecto (`Project`): 15 entradas de primer nivel, 20 hojas

| Elemento (es) | Clave visible en inglés | Tipo | Estado / contenido |
| --- | --- | --- | --- |
| **Proyecto** (rótulo) | Project | rótulo | |
| Nuevo... | New… | acción |  |
| Abrir desde | Open from | submenú | 3 entradas |
| ↳ Archivo... | File… | acción |  |
| ↳ URL... | URL… | acción |  |
| ↳ Galería... | Gallery… | acción |  |
| Abrir reciente | Open recent | submenú | deshabilitado al inicio |
| Historial... | History… | acción |  |
| Importar | Import | submenú | 3 entradas |
| ↳ Importar proyecto de QGIS… | Import QGIS project… | acción |  |
| ↳ Importar proyecto de ArcGIS Pro… | Import ArcGIS Pro project… | acción |  |
| ↳ Importar estilos de capa… | Import layer styles… | acción |  |
| Guardar | Save | acción |  |
| Guardar como... | Save as… | acción |  |
| Duplicar proyecto | Duplicate project | acción |  |
| Guardar como plantilla... | Save as template… | acción |  |
| Compartir... | Share… | acción |  |
| Exportar | Export | submenú | 3 entradas |
| ↳ Exportar como HTML... | Export as HTML… | acción |  |
| ↳ Exportar estilos de capa… | Export layer styles… | acción |  |
| ↳ Exportar capas… | Export layers… | acción |  |
| Colaborar... | Collaborate… | acción |  |
| Diseño de impresión... | Print layout… | acción |  |
| Mapa base sin conexión... | Offline basemap… | acción |  |
| Mapa narrativo... | Story map… | acción |  |

#### Editar (`Edit`): 8 entradas de primer nivel, 8 hojas

| Elemento (es) | Clave visible en inglés | Tipo | Estado / contenido |
| --- | --- | --- | --- |
| **Editar** (rótulo) | Edit | rótulo | |
| Deshacer Ctrl/Cmd+Z | Undo Ctrl/Cmd+Z | acción | deshabilitado al inicio |
| Rehacer Ctrl/Cmd+Shift+Z / Ctrl+Y | Redo Ctrl/Cmd+Shift+Z / Ctrl+Y | acción | deshabilitado al inicio |
| Seleccionar por expresión... | Select by expression… | acción | deshabilitado al inicio |
| Seleccionar por ubicación... | Select by location… | acción | deshabilitado al inicio |
| Acercar a la selección | Zoom to selection | acción | deshabilitado al inicio |
| Invertir selección | Invert selection | acción | deshabilitado al inicio |
| Borrar selección | Clear selection | acción | deshabilitado al inicio |
| Exportar entidades seleccionadas como capa | Export selected features as layer | acción | deshabilitado al inicio |

#### Ver (`View`): 11 entradas de primer nivel, 23 hojas

| Elemento (es) | Clave visible en inglés | Tipo | Estado / contenido |
| --- | --- | --- | --- |
| **Ver** (rótulo) | View | rótulo | |
| Acercar | Zoom in | acción |  |
| Alejar | Zoom out | acción |  |
| Vista anterior | Previous view | acción | deshabilitado al inicio |
| Vista siguiente | Next view | acción | deshabilitado al inicio |
| Restablecer orientación | Reset orientation | submenú | deshabilitado al inicio |
| Establecer vista… | Set view… | acción |  |
| Vista dividida | Split view | submenú | 7 entradas |
| ↳ Mapa único | Single map | opción (radio) · marcada |  |
| ↳ Dos columnas | Two columns | opción (radio) |  |
| ↳ Dos filas | Two rows | opción (radio) |  |
| ↳ Cuadrícula 2 × 2 | 2 × 2 grid | opción (radio) |  |
| ↳ Cuadrícula 2 × 3 | 2 × 3 grid | opción (radio) |  |
| ↳ Cuadrícula 3 × 3 | 3 × 3 grid | opción (radio) |  |
| ↳ Sincronizar vistas | Sync views | casilla · marcada | deshabilitado al inicio |
| Vista previa de visión del color | Color vision preview | submenú | 5 entradas |
| ↳ Desactivada | Off | opción (radio) · marcada |  |
| ↳ Protanopía (ceguera al rojo) | Protanopia (red-blind) | opción (radio) |  |
| ↳ Deuteranopía (ceguera al verde) | Deuteranopia (green-blind) | opción (radio) |  |
| ↳ Tritanopía (ceguera al azul) | Tritanopia (blue-blind) | opción (radio) |  |
| ↳ Acromatopsia (sin color) | Achromatopsia (no color) | opción (radio) |  |
| Motor de renderizado | Rendering engine | submenú | 4 entradas |
| ↳ MapLibre | MapLibre | opción (radio) · marcada |  |
| ↳ Mapbox | Mapbox | opción (radio) |  |
| ↳ ArcGIS | ArcGIS | opción (radio) |  |
| ↳ Cesium | Cesium | opción (radio) |  |
| Ver en Google Maps | View in Google Maps | acción |  |
| Ver en Google Earth | View in Google Earth | acción |  |

#### Añadir datos (`Add data`): 44 entradas de primer nivel, 44 hojas

| Elemento (es) | Clave visible en inglés | Tipo | Estado / contenido |
| --- | --- | --- | --- |
| **Añadir datos** (rótulo) | Add data | rótulo | |
| **Archivos** (rótulo) | Files | rótulo | |
| Capa vectorial | Vector layer | acción |  |
| Capa ráster | Raster layer | acción |  |
| Capa de texto delimitado | Delimited text layer | acción |  |
| Capa CAD (DXF/DWG) | CAD (DXF/DWG) layer | acción |  |
| Geodatabase de archivos (GDB) | File geodatabase (GDB) | acción |  |
| Capa VTPK/TPKX de ArcGIS | ArcGIS VTPK/TPKX layer | acción |  |
| Fotos geoetiquetadas | Geotagged photos | acción |  |
| Capa GPX | GPX layer | acción |  |
| Capa LandXML | LandXML layer | acción |  |
| Capa IndoorGML | IndoorGML layer | acción |  |
| Polilínea codificada | Encoded polyline | acción |  |
| Capa MBTiles | MBTiles layer | acción |  |
| Capa OSM PBF | OSM PBF layer | acción |  |
| ICESat-2 / GEDI | ICESat-2 / GEDI | acción |  |
| **Servicios web** (rótulo) | Web services | rótulo | |
| Capa XYZ | XYZ layer | acción |  |
| Capa WCS | WCS layer | acción |  |
| Capa WMS | WMS layer | acción |  |
| Catálogo CSW | CSW catalog | acción |  |
| Capa WFS | WFS layer | acción |  |
| Capa WMTS | WMTS layer | acción |  |
| OGC API - Features | OGC API - Features | acción |  |
| Teselas vectoriales OGC | OGC vector tiles | acción |  |
| Capa de ArcGIS | ArcGIS layer | acción |  |
| Capa GeoRSS | GeoRSS layer | acción |  |
| Límites administrativos | Administrative boundaries | acción |  |
| Capa STAC | STAC layer | acción |  |
| Capa de vídeo | Video layer | acción |  |
| Capa Deck.gl | Deck.gl layer | acción |  |
| **Formatos en la nube** (rótulo) | Cloud formats | rótulo | |
| Capa GeoParquet | GeoParquet layer | acción |  |
| Capa FlatGeobuf | FlatGeobuf layer | acción |  |
| Capa PMTiles | PMTiles layer | acción |  |
| Capa Zarr | Zarr layer | acción |  |
| NetCDF / HDF | NetCDF / HDF | acción |  |
| **Capas 3D** (rótulo) | 3D layers | rótulo | |
| Capa LiDAR | LiDAR layer | acción |  |
| Gaussian splatting | Gaussian splatting | acción |  |
| Capa 3D Tiles | 3D Tiles layer | acción |  |
| Recurso de Cesium Ion | Cesium Ion asset | acción | deshabilitado al inicio |
| Escena 3D dinámica CZML | CZML dynamic 3D scene | acción | deshabilitado al inicio |
| KML / KMZ | KML / KMZ | acción |  |
| Modelo 3D (glTF) | 3D model (glTF) | acción |  |
| **Bases de datos** (rótulo) | Databases | rótulo | |
| Capa DuckDB | DuckDB layer | acción |  |
| Capa de PostgreSQL | PostgreSQL layer | acción |  |
| Capa de SQL Server | SQL Server layer | acción |  |
| Capa Apache Iceberg | Apache Iceberg layer | acción |  |

#### Procesamiento (`Processing`): 21 entradas de primer nivel, 1159 hojas

| Elemento (es) | Clave visible en inglés | Tipo | Estado / contenido |
| --- | --- | --- | --- |
| **Procesamiento** (rótulo) | Processing | rótulo | |
| Asistente de IA | AI assistant | acción |  |
| Caja de herramientas de Whitebox | Whitebox toolbox | acción |  |
| Conversión | Conversion | submenú | 4 entradas, 49 hojas |
| Hidrología | Hydrology | submenú | 8 entradas, 100 hojas |
| LiDAR | LiDAR | submenú | 5 entradas, 67 hojas |
| Red | Network | submenú | 26 entradas |
| Proyección | Projection | submenú | 4 entradas |
| Ráster | Raster | submenú | 7 entradas, 256 hojas |
| Teledetección | Remote sensing | submenú | 10 entradas, 154 hojas |
| Terreno | Terrain | submenú | 7 entradas, 99 hojas |
| Vectorial | Vector | submenú | 10 entradas, 313 hojas |
| Caja de herramientas de GeoLibre | GeoLibre toolbox | submenú | 11 entradas, 80 hojas |
| ↳ Conversión | Conversion | submenú | 9 entradas |
| ↳ ↳ Vectorial a vectorial · Vectorial a GeoParquet · Vectorial a FlatGeobuf · Vectorial a Shapefile · Vectorial a GeoPackage · CSV a GeoParquet · Vectorial a PMTiles · Ráster a PMTiles · Ráster a COG | | lista | |
| ↳ Vectorial | Vector | submenú | 35 entradas |
| ↳ ↳ **Geometría:** · Búfer · Centroides · Envolvente convexa · Disolver · Cuadro delimitador · Simplificar · Decodificar polilínea · Codificar líneas como polilíneas · Reproyectar · Explosionar · Agregar por atributo · Suavizar · Extraer vértices · Puntos a lo largo de la geometría · Cuadrícula regular · Voronoi / Delaunay · Cobertura de sitios celulares · **Superposición:** · Recortar · Intersección · Diferencia · Unión · **Unión:** · Unión espacial · Resumir dentro · Unión de atributos · **Selección:** · Seleccionar por valor · Seleccionar por ubicación · Extracción aleatoria · **Movimiento y tiempo:** · Velocidad de trayectoria · Detectar paradas · Proximidad espacio-temporal · **Gestión de datos:** · Fusionar capas · **Calidad de datos:** · Comprobar validez · Corregir geometrías · Comprobar reglas de topología · Corregir topología | | lista | |
| ↳ Red | Network | submenú | 3 entradas |
| ↳ ↳ Isócrona / área de servicio · Matriz de costos OD · Ruta secuencial (direcciones) | | lista | |
| ↳ Estadísticas espaciales | Spatial statistics | submenú | 7 entradas |
| ↳ ↳ I de Moran global · I de Moran local (LISA) · Puntos calientes Getis-Ord Gi* · Vecino más cercano promedio · Densidad de kernel (mapa de calor) · Puntos calientes emergentes (cubo espacio-temporal) · Puntuación compuesta (índice de aptitud) | | lista | |
| ↳ Ráster | Raster | submenú | 18 entradas |
| ↳ ↳ Descargar DEM global · **Terreno:** · Sombreado de relieve · Pendiente · Orientación · **Reproyectar:** · Reproyectar · Remuestrear · **Recortar:** · Recortar por extensión · Recortar por capa de máscara · **Ráster a vectorial:** · Poligonizar · Curvas de nivel · **Vectorial a ráster:** · Interpolación (IDW / Kriging) · **Análisis:** · Estadísticas zonales · Calculadora ráster · Índice espectral · Reclasificar · Mosaico / fusión · Estadísticas focales · Georreferenciación | | lista | |
| ↳ DGGS | DGGS | submenú | 3 entradas |
| ↳ ↳ Generador DGGS · Agrupación DGGS · Compactación DGGS | | lista | |
| ↳ Geocodificar direcciones | Geocode addresses | acción |  |
| ↳ Herramientas por lotes | Batch tools | acción |  |
| ↳ Segmentación con IA | AI segmentation | acción |  |
| ↳ Detección de objetos | Object detection | acción |  |
| ↳ Segmentar todo | Segment everything | acción |  |
| Constructor de modelos | Model builder | acción |  |
| Análisis basado en objetos | Object-based analysis | acción |  |
| Espacio de trabajo SQL | SQL workspace | acción |  |
| Consola de Python | Python console | acción |  |
| Cuaderno Jupyter | Jupyter notebook | acción |  |
| Panel de control | Dashboard | acción |  |
| Historial | History | acción |  |
| Planetary Computer | Planetary Computer | acción |  |
| Earth Engine | Earth Engine | acción |  |

#### Controles (`Controls`): 35 entradas de primer nivel, 41 hojas

| Elemento (es) | Clave visible en inglés | Tipo | Estado / contenido |
| --- | --- | --- | --- |
| **Controles del mapa** (rótulo) | Map controls | rótulo | |
| Control de capas ✓ | Layer control ✓ | acción |  |
| Navegación | Navigation | acción |  |
| Pantalla completa ✓ | Fullscreen ✓ | acción |  |
| Brújula ✓ | Compass ✓ | acción |  |
| Geolocalizar | Geolocate | acción |  |
| Globo ✓ | Globe ✓ | acción |  |
| Terreno | Terrain | acción |  |
| Escala ✓ | Scale ✓ | acción |  |
| Atribución ✓ | Attribution ✓ | acción |  |
| Exageración del terreno | Terrain exaggeration | acción |  |
| Logotipos | Logos | submenú | 2 entradas |
| ↳ Logotipo de MapLibre | MapLibre logo | acción |  |
| ↳ Logotipo de Maptoolkit | Maptoolkit logo | acción | deshabilitado al inicio; ayuda: «Añade un mapa base de Maptoolkit para mostrar su logotipo.» |
| Efectos atmosféricos ✓ | Atmospheric effects ✓ | submenú | 5 entradas |
| ↳ Activado ✓ | Enabled ✓ | acción |  |
| ↳ *Color del halo* (rótulo) | Halo color | rótulo | |
| ↳ *Extensión del halo 2.80×* (rótulo) | Halo extent 2.80× | rótulo | |
| ↳ *Intensidad del halo 100%* (rótulo) | Halo strength 100% | rótulo | |
| ↳ *Color del espacio* (rótulo) | Space color | rótulo | |
| ↳ Estrellas ✓ | Stars ✓ | acción |  |
| ↳ Vía Láctea ✓ | Milky Way ✓ | acción |  |
| ↳ Líneas de constelaciones | Constellation lines | acción |  |
| ↳ Restablecer valores predeterminados | Reset to defaults | acción |  |
| Clima | Weather | submenú | ayuda: «Superponga capas meteorológicas casi en tiempo real que puede animar.»; 2 entradas |
| ↳ Nubes | Clouds | submenú | ayuda: «Superpone nubes satelitales de la NASA casi en tiempo real, como Google Earth. Añade una capa que puede animar día a día.»; 1 entradas |
| ↳ Precipitación | Precipitation | submenú | ayuda: «Radar meteorológico RainViewer casi en tiempo real. Anime las últimas ~2 horas.»; 1 entradas |
| Sol | Sun | acción | ayuda: «Simula la posición del sol y el terminador día/noche para cualquier fecha y hora.» |
| Animación de ruta | Route animation | acción | ayuda: «Anima un marcador a lo largo de una capa de líneas, con reproducir/pausar, velocidad, un rastro y seguimiento de cámara.» |
| Simulador de vuelo | Flight simulator | acción | ayuda: «Vuela sobre el terreno con los controles del teclado, como un simulador de vuelo.» |
| Globo giratorio | Spinning globe | acción |  |
| Cuadrícula | Gridlines | acción |  |
| Elevación | Elevation | acción | ayuda: «Mostrar la elevación del terreno bajo el puntero en la barra de estado. Sin terreno 3D se consulta un servicio público de elevación.» |
| Direcciones | Directions | acción | ayuda: «El enrutamiento envía sus waypoints al servidor de demostración público de OSRM (router.project-osrm.org).» |
| Navegación paso a paso... | Turn-by-turn navigation… | acción | ayuda: «Navegación paso a paso: planifique una ruta y sígala con guía por voz.» |
| Geocodificación inversa | Reverse geocode | acción | ayuda: «Haga clic en el mapa para buscar una dirección. Las coordenadas donde hace clic se envían al proveedor de geocodificación configurado (Nominatim público de forma predeterminada; cámbielo en Configuración → Geocodificación).» |
| Buscar | Search | acción |  |
| Barra de color | Colorbar | acción |  |
| Leyenda | Legend | acción |  |
| HTML | HTML | acción |  |
| Imagen | Image | acción |  |
| Medir | Measure | acción |  |
| Marcador | Bookmark | acción |  |
| Minimapa | Minimap | acción |  |
| Estado de vista | View state | acción |  |
| Recolección de campo... | Field collection… | acción |  |
| Seguimiento GPS... | GPS tracking… | acción |  |
| Grabar recorrido del mapa... | Record map tour… | acción |  |
| Grabar vídeo... | Record video… | acción |  |

#### Complementos (`Plugins`): 19 entradas de primer nivel, 81 hojas

| Elemento (es) | Clave visible en inglés | Tipo | Estado / contenido |
| --- | --- | --- | --- |
| **Activar complemento** (rótulo) | Activate plugin | rótulo | |
| GeoEditor | GeoEditor | submenú | 5 entradas |
| ↳ Activar | Activate | acción |  |
| ↳ *Posición* (rótulo) | Position | rótulo | |
| ↳ Superior izquierda | Top left | opción (radio) · marcada |  |
| ↳ Superior derecha | Top right | opción (radio) |  |
| ↳ Inferior izquierda | Bottom left | opción (radio) |  |
| ↳ Inferior derecha | Bottom right | opción (radio) |  |
| Anotaciones | Annotations | submenú | 5 entradas |
| ↳ Activar | Activate | acción |  |
| ↳ *Posición* (rótulo) | Position | rótulo | |
| ↳ Superior izquierda | Top left | opción (radio) · marcada |  |
| ↳ Superior derecha | Top right | opción (radio) |  |
| ↳ Inferior izquierda | Bottom left | opción (radio) |  |
| ↳ Inferior derecha | Bottom right | opción (radio) |  |
| Acotaciones | Dimensions | submenú | 5 entradas |
| ↳ Activar | Activate | acción |  |
| ↳ *Posición* (rótulo) | Position | rótulo | |
| ↳ Superior izquierda | Top left | opción (radio) · marcada |  |
| ↳ Superior derecha | Top right | opción (radio) |  |
| ↳ Inferior izquierda | Bottom left | opción (radio) |  |
| ↳ Inferior derecha | Bottom right | opción (radio) |  |
| Servicios web | Web services | submenú | 36 entradas |
| ↳ ArcGIS Hub | ArcGIS Hub | acción (abre panel) | |
| ↳ Catálogos STAC | STAC catalogs | acción (abre panel) | |
| ↳ CKAN | CKAN | acción (abre panel) | |
| ↳ Datos abiertos de Planet | Planet Open Data | acción (abre panel) | |
| ↳ Datos abiertos de Vantor | Vantor Open Data | acción (abre panel) | |
| ↳ Descargador de OSM | OSM downloader | acción (abre panel) | |
| ↳ Dynamical | Dynamical | acción (abre panel) | |
| ↳ Earthdata GIS | Earthdata GIS | acción (abre panel) | |
| ↳ Embeddings satelitales | Satellite embeddings | acción (abre panel) | |
| ↳ Explorador de Sentinel-2 | Sentinel-2 explorer | acción (abre panel) | |
| ↳ Explorador S3 | S3 browser | acción (abre panel) | |
| ↳ FEMA NFHL | FEMA NFHL | acción (abre panel) | |
| ↳ Fields of the World | Fields of the World | acción (abre panel) | |
| ↳ GeoLens | GeoLens | acción (abre panel) | |
| ↳ Hugging Face | Hugging Face | acción (abre panel) | |
| ↳ IGN LiDAR HD | IGN LiDAR HD | acción (abre panel) | |
| ↳ JAXA Earth | JAXA Earth | acción (abre panel) | |
| ↳ NASA Earthaccess | NASA Earthaccess | acción (abre panel) | |
| ↳ NASA Earthdata | NASA Earthdata | acción (abre panel) | |
| ↳ Natural Earth | Natural Earth | acción (abre panel) | |
| ↳ Ocean Data Platform | Ocean Data Platform | acción (abre panel) | |
| ↳ OpenAerialMap | OpenAerialMap | acción (abre panel) | |
| ↳ Portal de ArcGIS | ArcGIS Portal | acción (abre panel) | |
| ↳ Portolan | Portolan | acción (abre panel) | |
| ↳ SIG de estados de EE. UU. | US state GIS | acción (abre panel) | |
| ↳ SIG de India | India GIS | acción (abre panel) | |
| ↳ SIG federales de EE. UU. | US federal GIS | acción (abre panel) | |
| ↳ SIG locales de EE. UU. | US local GIS | acción (abre panel) | |
| ↳ Socrata | Socrata | acción (abre panel) | |
| ↳ Source Cooperative | Source Cooperative | acción (abre panel) | |
| ↳ Tennessee GIS | Tennessee GIS | acción (abre panel) | |
| ↳ US EPA EnviroAtlas | US EPA EnviroAtlas | acción (abre panel) | |
| ↳ USGS 3DEP | USGS 3DEP | acción (abre panel) | |
| ↳ USGS LiDAR | USGS LiDAR | acción (abre panel) | |
| ↳ USGS National Map | USGS National Map | acción (abre panel) | |
| ↳ USGS NLDI | USGS NLDI | acción (abre panel) | |
| Vista de calle | Street View | submenú | 5 entradas |
| ↳ Activar | Activate | acción |  |
| ↳ *Posición* (rótulo) | Position | rótulo | |
| ↳ Superior izquierda | Top left | opción (radio) |  |
| ↳ Superior derecha | Top right | opción (radio) · marcada |  |
| ↳ Inferior izquierda | Bottom left | opción (radio) |  |
| ↳ Inferior derecha | Bottom right | opción (radio) |  |
| Mapillary | Mapillary | submenú | 5 entradas |
| ↳ Activar | Activate | acción |  |
| ↳ *Posición* (rótulo) | Position | rótulo | |
| ↳ Superior izquierda | Top left | opción (radio) · marcada |  |
| ↳ Superior derecha | Top right | opción (radio) |  |
| ↳ Inferior izquierda | Bottom left | opción (radio) |  |
| ↳ Inferior derecha | Bottom right | opción (radio) |  |
| DGGS | DGGS | submenú | 8 entradas |
| ↳ Cuadrícula H3 | H3 | acción |  |
| ↳ S2 | S2 | acción |  |
| ↳ A5 | A5 | acción |  |
| ↳ DGGRID | DGGRID | acción |  |
| ↳ DGGAL | DGGAL | acción |  |
| ↳ OLC | OLC | acción |  |
| ↳ Geohash | Geohash | acción |  |
| ↳ Tilecode | Tilecode | acción |  |
| Mapas base | Basemaps | acción |  |
| Imágenes históricas | Historical imagery | acción |  |
| Control de tiempo | Time slider | acción |  |
| Timelapse | Timelapse | acción |  |
| Overture Maps | Overture Maps | acción |  |
| GeoAgent | GeoAgent | acción |  |
| Perfil de elevación | Elevation profile | acción |  |
| Comparador de capas | Layer swipe | acción |  |
| Simulador de vuelo | Flight simulator | acción |  |
| Vista de Dios | God's eye view | acción |  |
| SamGeo | SamGeo | acción |  |
| Anotación de nubes de puntos | Point cloud annotation | acción |  |

#### Configuración (`Settings`): 12 entradas de primer nivel, 53 hojas

| Elemento (es) | Clave visible en inglés | Tipo | Estado / contenido |
| --- | --- | --- | --- |
| **Configuración** (rótulo) | Settings | rótulo | |
| Idioma | Language | submenú | 25 entradas |
| ↳ English | English | opción (radio) |  |
| ↳ العربية (Arabic) | العربية (Arabic) | opción (radio) |  |
| ↳ Azərbaycanca (Azerbaijani) | Azərbaycanca (Azerbaijani) | opción (radio) |  |
| ↳ 简体中文 (Chinese (Simplified)) | 简体中文 (Chinese (Simplified)) | opción (radio) |  |
| ↳ 繁體中文（香港） (Chinese (Traditional, Hong Kong)) | 繁體中文（香港） (Chinese (Traditional, Hong Kong)) | opción (radio) |  |
| ↳ 繁體中文（澳門） (Chinese (Traditional, Macau)) | 繁體中文（澳門） (Chinese (Traditional, Macau)) | opción (radio) |  |
| ↳ 繁體中文（台灣） (Chinese (Traditional, Taiwan)) | 繁體中文（台灣） (Chinese (Traditional, Taiwan)) | opción (radio) |  |
| ↳ Nederlands (Dutch) | Nederlands (Dutch) | opción (radio) |  |
| ↳ Français (French) | Français (French) | opción (radio) |  |
| ↳ ქართული (Georgian) | ქართული (Georgian) | opción (radio) |  |
| ↳ Deutsch (German) | Deutsch (German) | opción (radio) |  |
| ↳ עברית (Hebrew) | עברית (Hebrew) | opción (radio) |  |
| ↳ हिन्दी (Hindi) | हिन्दी (Hindi) | opción (radio) |  |
| ↳ Bahasa Indonesia (Indonesian) | Bahasa Indonesia (Indonesian) | opción (radio) |  |
| ↳ Italiano (Italian) | Italiano (Italian) | opción (radio) |  |
| ↳ 日本語 (Japanese) | 日本語 (Japanese) | opción (radio) |  |
| ↳ 한국어 (Korean) | 한국어 (Korean) | opción (radio) |  |
| ↳ فارسی (Persian) | فارسی (Persian) | opción (radio) |  |
| ↳ Português (Portuguese) | Português (Portuguese) | opción (radio) |  |
| ↳ Русский (Russian) | Русский (Russian) | opción (radio) |  |
| ↳ Español (Spanish) | Español (Spanish) | opción (radio) · marcada |  |
| ↳ ไทย (Thai) | ไทย (Thai) | opción (radio) |  |
| ↳ Türkçe (Turkish) | Türkçe (Turkish) | opción (radio) |  |
| ↳ Tiếng Việt (Vietnamese) | Tiếng Việt (Vietnamese) | opción (radio) |  |
| ↳ Gestionar paquetes de idioma | Manage language packs | acción |  |
| Preferencias del mapa | Map preferences | acción |  |
| Diseño | Layout | submenú | 8 entradas |
| ↳ Mostrar etiquetas de la barra de herramientas | Show toolbar labels | casilla · marcada |  |
| ↳ Mostrar información del proyecto | Show project info | casilla · marcada |  |
| ↳ Mostrar panel de capas | Show Layers panel | casilla · marcada |  |
| ↳ Mostrar panel de estilo | Show Style panel | casilla · marcada |  |
| ↳ Mostrar panel del explorador | Show Browser panel | casilla · marcada |  |
| ↳ Mostrar panel de comentarios | Show Comments panel | casilla · marcada |  |
| ↳ Mantener los paneles inferiores bajo el mapa | Keep bottom panels under the map | casilla · marcada |  |
| ↳ Configuración de diseño | Layout settings | acción |  |
| ↳ *Los parámetros de diseño de la URL anulan la configuración guardada.* (rótulo) | URL layout parameters override saved settings. | rótulo | |
| Apariencia | Appearance | submenú | 7 entradas |
| ↳ *Color de acento* (rótulo) | Accent color | rótulo | |
| ↳ Azul | Blue | opción (radio) · marcada |  |
| ↳ Violeta | Violet | opción (radio) |  |
| ↳ Esmeralda | Emerald | opción (radio) |  |
| ↳ Rosa | Rose | opción (radio) |  |
| ↳ Ámbar | Amber | opción (radio) |  |
| ↳ Personalizado | Custom | opción (radio) |  |
| ↳ Configuración de apariencia | Appearance settings | acción |  |
| Interfaz | Interface | submenú | 5 entradas |
| ↳ *Nivel de experiencia* (rótulo) | Experience level | rótulo | |
| ↳ Principiante | Beginner | opción (radio) |  |
| ↳ Intermedio | Intermediate | opción (radio) |  |
| ↳ Avanzado | Advanced | opción (radio) · marcada |  |
| ↳ Personalizado | Custom | opción (radio) |  |
| ↳ Configuración de interfaz | Interface settings | acción |  |
| Geocodificación | Geocoding | acción |  |
| Proveedores de IA | AI providers | acción |  |
| Variables de entorno | Environment variables | acción |  |
| Almacenamiento en la nube | Cloud storage | acción |  |
| Configuración de inicio | Startup settings | acción |  |
| Administrar complementos | Manage plugins | acción |  |
| Administrador de estilos | Style manager | acción |  |

#### Ayuda (`Help`): 9 entradas de primer nivel, 9 hojas

| Elemento (es) | Clave visible en inglés | Tipo | Estado / contenido |
| --- | --- | --- | --- |
| **Ayuda** (rótulo) | Help | rótulo | |
| Paleta de comandos | Command palette | acción |  |
| Atajos de teclado | Keyboard shortcuts | acción |  |
| Simplificar interfaz... | Simplify interface… | acción |  |
| Sitio web | Website | acción |  |
| Repositorio de GitHub | GitHub repository | acción |  |
| Diagnóstico | Diagnostics | acción |  |
| Enviar comentarios | Give feedback | acción |  |
| Buscar actualizaciones | Check for updates | acción |  |
| Acerca de | About | acción |  |

### 3.2 Botón de tema y título del proyecto

| Elemento | Comportamiento observado |
| --- | --- |
| Botón luna/sol | `aria-label` y `title` «Cambiar a modo oscuro»; al pulsarlo, toda la interfaz pasa a oscuro y el icono a sol; el mapa base no cambia (cap. `paneles/pan-tema-oscuro.png`). Por defecto sigue al sistema; `?theme=dark` o `?theme=light` lo fijan (§8) |
| Nombre del proyecto | `input` con `aria-label` «Nombre del proyecto» y marcador «Proyecto sin título», editable en línea. Con «Mostrar información del proyecto» (Configuración → Diseño, activo) se muestra a la derecha de la barra; nuestra integración añade la URL del proyecto (§10) |
| Paleta | `Ctrl+K` (Ayuda → Paleta de comandos) |

### 3.3 Diálogos del menú Proyecto (DOM, `dialogos/dlg-proyecto-*.png`)

| Elemento | Resultado al pulsarlo | Contenido del diálogo | Red al abrir |
| --- | --- | --- | --- |
| Nuevo... | Diálogo «Nuevo proyecto» | «Elija un mapa base de OpenFreeMap o Protomaps, un fondo en blanco o una URL de estilo de MapLibre.» Campo *Nombre del proyecto*; botón **Ejemplos**; selector de mapa base igual que «Cambiar fondo» (§5.2) con «URL personalizada»; **Cancelar / Crear** | ninguna externa |
| Abrir desde → Archivo... | Selector de archivos del navegador (sin diálogo propio) | — | — |
| Abrir desde → URL... | «Abrir proyecto desde URL» | «Carga un proyecto `.geolibre.json` y lo añade a los proyectos recientes.» Campo *URL del proyecto* (`https://example.com/project.geolibre.json`); **Cancelar / Abrir** | — |
| Abrir desde → Galería... | «Galería de proyectos» | «Explore los proyectos públicos compartidos en share.geolibre.app…». Pestañas **Destacados · Todos los proyectos · Colecciones**; filtro de texto; aviso de token; botón «Iniciar sesión en share.geolibre.app»; tarjetas (p. ej. *Nepal-Flash-Floods*, *3D Tiles*, *Mars*, *NYC Buildings and Subways*, *Maritime Piracy*) con **Abrir · Abrir una copia · Ver en la web** | `share.geolibre.app/api/projects` y `/api/thumbnails/<id>` |
| Abrir reciente | Submenú deshabilitado (sin recientes) | — | — |
| Historial... | «Historial del proyecto» | «Explore las instantáneas autoguardadas en este dispositivo.» / «Todavía no hay instantáneas autoguardadas.» | — |
| Importar → QGIS / ArcGIS Pro / estilos de capa | Selector de archivos del navegador | — | — |
| Guardar / Guardar como... / Duplicar proyecto | Sin diálogo visible en el navegador automatizado (descarga o selector de archivos) | — | — |
| Guardar como plantilla... | «Guardar como plantilla» | *Nombre de la plantilla* (por defecto «Untitled Project (copy)»), *Descripción (opcional)*, casilla **Quitar capas de datos** (marcada); **Guardar en la biblioteca de plantillas** | — |
| Compartir... | «Compartir proyecto» | «Suba el proyecto actual a share.geolibre.app y obtenga un enlace para compartir.» Botones **Iniciar sesión en share.geolibre.app**, **Obtener token de API**, **Configurar token local** (pasos 1-2 con token en Configuración → Variables de entorno) | solo el *chunk* del diálogo |
| Exportar → Exportar como HTML... | Descarga directa, sin diálogo | — | — |
| Exportar → Exportar estilos de capa… / Exportar capas… | Sin capas: diálogo de error «Algo salió mal» con «Este proyecto no tiene capas con un estilo que exportar.» / «…no tiene capas que exportar.» | **Descartar** | — |
| Colaborar... | «Colaboración en vivo» | *Su nombre*, *Su color* (8 muestras: blue, red, green, amber, purple, cyan, pink, lime), *Quién puede editar* (Cualquiera puede editar / Solo usted puede editar), **Iniciar sesión**; «Unirse a una sesión» con código y **Unirse** | `collab.geolibre.app/health` |
| Diseño de impresión... | «Diseño de impresión» | Título, Subtítulo, Ubicación del título, Alineación, Tamaño (A4, A3, Letter, Legal, Tabloid, Full HD, HD, 4K UHD, Square, Personalizado…), Orientación, Margen, Fondo de página/mapa, Paneles del mapa (Claro/Oscuro), marco, Escala 1:N y preajustes (1:500 … 1:100.000), Extensión de impresión (dibujar), **Atlas (serie de mapas)**, 15 elementos activables (título, subtítulo, leyenda, escala gráfica, flecha de norte, agrupar norte+escala, fecha, atribución de GeoLibre, pie, borde, bloque de información, barra de color, leyenda personalizada, tabla de atributos, gráfico), editor de leyenda; **Volver a capturar el mapa · Copiar al portapapeles · Exportar SVG · Exportar PNG · Exportar PDF** | — |
| Mapa base sin conexión... | Panel «Extraer mapa base sin conexión» | URL del mapa base; Dibujar en el mapa / Usar la vista; N/S/O/E; zoom mín./máx.; estilo (Claro, Oscuro, Blanco, Escala de grises, Negro, Ninguno); **Extraer**; «Mapas base guardados», **Abrir archivo…** (`.pmtiles`) | — |
| Mapa narrativo... | «Mapa narrativo» | Título, Subtítulo, Autoría, Tema del panel (Oscuro/Claro), Pie; casillas Mostrar marcadores, Minimapa incrustado, Ocultar lista de capítulos, Activar vista inicial, Activar diapositiva de cierre; Capítulos (0) con **Importar · Exportar · Añadir capítulo · Restablecer**; **Cargar historia de ejemplo · Exportar HTML · Folleto (PDF) · Presentar** | — |

Elemento oculto: el catálogo de Configuración → Interfaz incluye **«Imprimir...»** (`project.print`) entre los ítems de
Proyecto, pero no aparece en el menú de la web (DOM).

### 3.4 Diálogos del menú Ver

| Elemento | Resultado |
| --- | --- |
| Acercar / Alejar | Zoom ±1 |
| Vista anterior / siguiente | Deshabilitados hasta mover el mapa (atajos `[` y `]`) |
| Restablecer orientación ▶ | Deshabilitado con rumbo e inclinación 0. El catálogo de Interfaz lista sus tres hijos: Restablecer inclinación, Restablecer rumbo, Restablecer inclinación y rumbo |
| Establecer vista… | Diálogo «Establecer vista»: Pegar coordenadas, formato DD/DMS/DDM, Longitud (-100), Latitud (40), Zoom (2), Inclinación, Rumbo; **Cancelar / Ir** |
| Vista dividida ▶ | Mapa único, Dos columnas, Dos filas, Cuadrícula 2×2, 2×3, 3×3; casilla Sincronizar vistas |
| Vista previa de visión del color ▶ | Desactivada, Protanopía, Deuteranopía, Tritanopía, Acromatopsia |
| Motor de renderizado ▶ | MapLibre (marcado), Mapbox, ArcGIS, Cesium |
| Ver en Google Maps / Google Earth | Abren pestaña: `https://www.google.com/maps/@40.000000,-100.000000,2z` y `https://earth.google.com/web/@0,0,0a,…` (red: ventana emergente) |

### 3.5 Diálogos del menú Ayuda (DOM, `dialogos/dlg-ayuda-*.png`)

| Elemento | Resultado | Contenido / red |
| --- | --- | --- |
| Paleta de comandos | Diálogo «Paleta de comandos» con buscador «Buscar comandos…» | Grupos Proyecto (Nuevo proyecto Ctrl+N, Abrir ejemplos iniciales, Abrir desde archivo Ctrl+O, Abrir desde URL, Guardar Ctrl+S, Guardar como Ctrl+Shift+S, Compartir, Colaborar, Diseño de impresión) y Añadir datos (Añadir capa vectorial, ráster, OSM PBF, VTPK/TPKX, texto delimitado, CAD, GPX, LandXML, IndoorGML, MBTiles…), más los que siguen al desplazar |
| Atajos de teclado | Diálogo «Atajos de teclado» | General: Ctrl+K paleta, `?` atajos; Proyecto: Ctrl+N, Ctrl+O, Ctrl+S, Ctrl+Shift+S; Añadir datos: `C` comentario de revisión; Ver: `[`, `]`, `N` rumbo, `U` inclinación, `R` ambos; Navegación: `+`, `−`, flechas, ⇧←/→ rotar, ⇧↑/↓ inclinar |
| Simplificar interfaz... | Abre Configuración en la sección **Interfaz** (§6) | — |
| Sitio web | Pestaña `https://geolibre.app/` | — |
| Repositorio de GitHub | Pestaña `https://github.com/opengeos/GeoLibre` | — |
| Diagnóstico | Diálogo «Diagnóstico» (§5.5) | — |
| Enviar comentarios | Pestaña `https://github.com/opengeos/GeoLibre/issues` | — |
| Buscar actualizaciones | Diálogo «Acerca de GeoLibre» con la comprobación; en la prueba: «No se pudieron buscar actualizaciones. Se superó el límite de solicitudes de GitHub.» y botones **Reintentar · Ver descargas** | `api.github.com/repos/opengeos/GeoLibre/releases/latest` |
| Acerca de | «Acerca de GeoLibre»: «GeoLibre es una plataforma SIG ligera y nativa de la nube.», **Versión v3.9.0**, botón **Buscar actualizaciones**, enlaces Página de inicio (geolibre.app), Repositorio de GitHub, Licencias de terceros (`docs/third-party-licenses.md`) | — |

Si el navegador bloquea la ventana emergente, la app registra «[GeoLibre] failed to open external link (popup blocked?)» en
Diagnóstico (DOM).

### 3.6 Diálogos del menú Añadir datos (44 fuentes)

Captura de cada elemento en `dialogos/ad-ad-*.png`; datos en `dialogos/ad.json` y resumen en `anadir-datos-dialogos.txt`.
Casi todos los diálogos propios comparten la cabecera *Nombre de la capa · Insertar debajo (Parte superior de la lista de
capas) · Mostrar capas de mapa base (avanzado)* y el selector **Datos de ejemplo / Cargar datos de ejemplo…**. Las que abren
un **panel flotante de complemento** (no un diálogo) muestran su interfaz **en inglés** aunque la app esté en español.

| Grupo | Fuente (es / en) | Qué abre | Campos o contenido principal | Red al abrir |
| --- | --- | --- | --- | --- |
| Archivos | Capa vectorial / Vector layer | Panel flotante «Add Vector Layer» (inglés) | Drop file or click to browse; URL + **Load**; Load sample data...; casilla Stream GeoParquet (no copy); Source CRS override (e.g. EPSG:28992); lista LAYERS | — |
| Archivos | Capa ráster / Raster layer | Panel «Add Raster Layer» (inglés) | RENDERING ENGINE: maplibre-gl-raster (GPU) · cog-tiler-wasm (WASM) · titiler (server); arrastrar `.tif`, `.vrt`, `.json`; URL de COG | — |
| Archivos | Capa de texto delimitado / Delimited text layer | Diálogo | Tipo de fuente (URL/archivo), **Recuperar columnas**, Importar como (Coordenadas / Direcciones (geocodificar)), Delimitador, campos lon/lat, Sistema de coordenadas | — |
| Archivos | Capa CAD (DXF/DWG) | Diálogo | Elegir archivo, Capa CAD, CRS de origen (+ comunes), Representar valores Z en 3D | — |
| Archivos | Geodatabase de archivos (GDB) | Diálogo con aviso | «Las capas de geodatabase de archivos solo están disponibles en GeoLibre Desktop…» | — |
| Archivos | Capa VTPK/TPKX de ArcGIS | Diálogo | Ejemplos (Condado de Leon VTPK, Mundo VTPK, San Francisco TPKX, Estados Unidos TPKX), URL con rangos HTTP + CORS, Elegir archivo local…, Cargar desde URL | — |
| Archivos | Fotos geoetiquetadas | Diálogo | Elegir fotos (JPEG, PNG, TIFF, HEIC con GPS EXIF) | — |
| Archivos | Capa GPX | Diálogo | URL/archivo; tipos Waypoints, Tracks, Puntos de track, Rutas, Puntos de ruta; ejemplo «Ruta Fells Loop» | — |
| Archivos | Capa LandXML | Diálogo | URL/archivo; Superficies TIN, Ejes en planta y perfil, Puntos topográficos; CRS de origen | — |
| Archivos | Capa IndoorGML | Diálogo | URL/archivo; CRS de origen; «Coordenadas locales: colocar el edificio en el centro del mapa» | — |
| Archivos | Polilínea codificada | Diálogo | Pegar texto / archivo; Precisión 5 (Google/OSRM) o 6 (Valhalla/Mapbox); delimitador; geometría de salida; quitar escapes | — |
| Archivos | Capa MBTiles | Diálogo | Elegir archivo | — |
| Archivos | Capa OSM PBF | Diálogo | Ejemplo «Las Vegas», URL (CORS), Elegir archivo local… | — |
| Archivos | ICESat-2 / GEDI | Diálogo | Archivo de gránulo HDF5 (ATL06, ATL08, L2A, L2B, L4A) leído en el navegador | — |
| Servicios web | Capa XYZ | Diálogo | Servicios guardados (OpenStreetMap, USGS Imagery integrados), Plantilla XYZ o TileJSON, Tamaño de tesela, URL corta | — |
| Servicios web | Capa WCS | Diálogo «Capa WCS» | WCS 1.0.0: URL, **Obtener coberturas**, Cobertura, extensión (vista/cobertura), CRS de la solicitud, ancho/alto | — |
| Servicios web | Capa WMS | Diálogo | Servicios guardados (USGS NAIP Imagery, GEBCO Ocean Bathymetry, NLCD 2021 Land Cover integrados), URL, **Recuperar capas**, Capas, Estilos, Formato, Tamaño, Versión, Fondo transparente | — |
| Servicios web | Catálogo CSW | Diálogo «Buscar en catálogo CSW» | URL, Palabra clave, **Buscar**; ejemplos Open Canada, European Environment Agency (SDI), geocat… | — |
| Servicios web | Capa WFS | Diálogo | Servicio integrado US States (GeoServer demo); URL, **Recuperar tipos**, Tipo de entidad, Versión (2.0.0/1.1.0/1.0.0), Formato de salida, SRS, Máximo de entidades | — |
| Servicios web | Capa WMTS | Diálogo | Integrado Sentinel-2 cloudless (EOX); Plantilla de URL, Tamaño | — |
| Servicios web | OGC API - Features | Diálogo | URL, **Recuperar colecciones**, Colección, Máximo de entidades, Cuadro delimitador, Fecha y hora | — |
| Servicios web | Teselas vectoriales OGC | Diálogo | URL de teselas (TileJSON o plantilla MVT), URL de estilo, Capas de origen | — |
| Servicios web | Capa de ArcGIS | Diálogo | Integrado USA Major Cities; Tipo de capa (entidades, teselas vectoriales, mapa, imagen…), Tipo de fuente (servicio/portal), URL, URL del portal, Autenticación, registros por solicitud, máximo | — |
| Servicios web | Capa GeoRSS | Diálogo | URL/archivo; ejemplo «Terremotos de USGS (último día)» | — |
| Servicios web | Límites administrativos | Diálogo | geoBoundaries: País, Nivel administrativo (0–5), geometría simplificada | `www.geoboundaries.org/api/current/gbOpen/ALL/ADM0/` |
| Servicios web | Capa STAC | Panel «Catálogos STAC» | Buscar un catálogo público en STAC Index; lista de catálogos (estáticos/API) | `stacindex.org/api/catalogs` |
| Servicios web | Capa de vídeo | Diálogo | URL MP4 principal y alternativa, 4 esquinas (lng, lat) | — |
| Servicios web | Capa Deck.gl | Diálogo | Tipo: Diagrama de dispersión, Mapa de calor, Hexágonos 3D, Cuadrícula 3D, Cuadrícula de pantalla, Contornos, Arcos, Líneas, Círculo máx.…; datos de ejemplo o URL; color; tamaño | — |
| Formatos en la nube | Capa GeoParquet | Mismo panel «Add Vector Layer» (inglés) | — | — |
| Formatos en la nube | Capa FlatGeobuf | Panel (inglés) | URL / GeoJSON Text; Vector URL «Supports GeoJSON, GeoParquet, and FlatGeobuf»; Format; colores; Opacity; Pickable; Layer Name; Before Layer ID; **Add Layer** | — |
| Formatos en la nube | Capa PMTiles | Panel «PMTiles Layer» (inglés) | PMTiles URL, Local file..., Enable feature picking, Source Layers + **Fetch**, Before Layer ID | — |
| Formatos en la nube | Capa Zarr | Panel «Zarr Layer» (inglés) | Zarr URL, Browse folder..., Variable, CRS, proj4, Colormap (24 rampas), Clim Min/Max, Selector (JSON), opacidad, Pickable | — |
| Formatos en la nube | NetCDF / HDF | Diálogo | Fuente: Optimizado para la nube (URL de kerchunk) o Archivo local (NetCDF/HDF5) | — |
| Capas 3D | Capa LiDAR | Panel «Add LiDAR layer» (inglés) | LAS/LAZ, Sample data, COPC/EPT por URL; estilo (Color By, Colormap, rango, tamaño, opacidad, 3D Terrain, picking, filtro de elevación, Z Offset); CROSS-SECTION | — |
| Capas 3D | Gaussian splatting | **No abrió interfaz**; dejó 1 entrada en Diagnóstico | — | — |
| Capas 3D | Capa 3D Tiles | Panel «Add 3D Tiles layer» (inglés) | Tileset URL, Layer name, Request headers (`${NAME}`), Before layer ID, Altitude offset, Fly to tileset, Visible on load, **Add tileset** | — |
| Capas 3D | Recurso de Cesium Ion | Deshabilitado con MapLibre (solo motor Cesium) | — | — |
| Capas 3D | Escena 3D dinámica CZML | Deshabilitado con MapLibre (solo motor Cesium) | — | — |
| Capas 3D | KML / KMZ | Diálogo «KML / KMZ» | URL o Elegir archivo | — |
| Capas 3D | Modelo 3D (glTF) | Diálogo «Añadir capa Deck.gl» con tipo modelo 3D | Conjunto de ejemplo, URL glTF/GLB, Colocación, Longitud, Latitud, Escala, Rumbo°, Altitud m | — |
| Bases de datos | Capa DuckDB | Panel «Add DuckDB layer» (inglés) | Load sample data..., DuckDB URL, SQL query, Geometry column/format, Source/Target CRS, Layer name, before_id, **Run query** | — |
| Bases de datos | Capa de PostgreSQL | Diálogo con aviso | «Las capas PostgreSQL solo están disponibles en GeoLibre Desktop y en las aplicaciones móviles…»; Cargar como, Cadena de conexión, SRID | — |
| Bases de datos | Capa de SQL Server | Diálogo con aviso | «…solo están disponibles en GeoLibre Desktop.»; servidor, puerto, base, autenticación, cifrado, usuario, contraseña | — |
| Bases de datos | Capa Apache Iceberg | Diálogo | Origen Iceberg, Ubicación de los metadatos de la tabla, Límite de filas (v3+) | — |

**En la web no funcionan** (lo dicen los propios diálogos): Geodatabase de archivos, PostgreSQL y SQL Server (requieren
escritorio o servidor local); Cesium Ion y CZML están deshabilitados con el motor MapLibre.

## 4. Panel izquierdo

### 4.1 Riel y pestañas

Riel vertical con dos pestañas de texto girado: **EXPLORADOR** (`aria-label` «Expandir Explorador») y **CAPAS**
(«Contraer Capas» cuando está abierto). Al abrir Explorador se pliega Capas (uno a la vez en el lado izquierdo) (cap.
`paneles/pan-explorador.png`). Cabecera de los paneles acoplados: **Separar como panel móvil · Contraer panel · Cerrar
panel** (DOM, `extra/extra.json`).

### 4.2 Panel «Capas»

| Parte | Elementos (nombre accesible exacto, DOM) |
| --- | --- |
| Barra de iconos (8) | **Cuerpo celeste** (menú de casillas: Tierra, Luna, Marte, Calisto, Caronte, Europa, Ganímedes, Ío, Mercurio, Plutón, Titán, Venus) · **Mapas base** (abre el complemento de mapas base, §5.2) · **GeoEditor** (activa el editor de dibujo; aparece la barra de geometrías y el formulario «Propiedades de la entidad») · **Nuevo grupo** · **Vista compacta** (`title`: «Vista compacta: mostrar la opacidad y los botones de capa solo en la capa seleccionada») · **Ocultar todas las capas** (pasa a «Mostrar todas las capas») · **Identificar capas visibles** (`title`: «Haga clic en el mapa para identificar entidades y valores de píxel de todas las capas consultables visibles.») · **Contraer capas** |
| Mensaje sin datos | «No hay capas de datos. Añada datos desde la barra de herramientas.» |
| Fila «Fondo» | asa de arrastre · ojo **Ocultar fondo** · icono de capas · nombre «Fondo» · distintivo **FONDO** · botón «⋯» = **Cambiar fondo** (abre el diálogo de §5.2) · deslizador **Opacidad** con valor `1.00` (botón «1.00 — Editar valor de Opacidad del fondo», `title` «Doble clic para introducir un valor exacto») |
| Fila de una capa de datos (probado con un GeoJSON local de 3 puntos) | asa · ojo **Ocultar capa** · muestra de simbología · nombre («Doble clic para cambiar el nombre») · distintivo **VECTOR** · Opacidad con valor editable · segunda fila de iconos: **Subir · Bajar · Ajustar zoom a la capa · Identificar entidades · Abrir panel de estilo · Acciones de capa (⋯) · Metadatos · Quitar capa** (papelera roja) (cap. `capa/estilo-capa.png`) |
| Menú «⋯ Acciones de capa» | Cambiar el nombre · — · Abrir panel de estilo · Nuevo grupo a partir de la capa · — · Editar geometría · Cargar entidades en el editor… · Abrir tabla de atributos · **Análisis rápido ▶** (Búfer de 500 m / 1 km / 5 km en todas las entidades · Centroides · Envolvente convexa · Cuadro delimitador · Abrir en Procesamiento…) · **Seleccionar entidades ▶** · Seleccionar por expresión... · Seleccionar por ubicación... (deshabilitado con una sola capa) · Vincular al control deslizante de tiempo… · **Exportar ▶** (GeoJSON, GeoParquet, GeoPackage, KML, KMZ, Shapefile (zipped), CSV) · **Estilos ▶** · — · Guardar en Mis datos · — · Copiar estilo · Pegar estilo (deshab.) · Actualizar (deshab.) · Actualización automática (deshab.) con la nota «Solo URL de WFS y GeoJSON» (DOM, `capa/capa.json`, `capa/capa-menu-1.png`) |
| Buscador al pie | `input` `role=combobox`, `aria-label` «Buscar lugares», marcador «Buscar lugares, coordenadas o celda H3...». Resultados: «Pasto» → «Perímetro Urbano Pasto, Pasto, Centro, Nariño, RAP Pacífico, Colombia» y «Pasto, Centro, Nariño, RAP Pacífico, Colombia» (consulta a `nominatim.openstreetmap.org/search?q=Pasto&format=jsonv2&addressdetails=1&limit=6`); `1.2136, -77.2811` → «Ir a 1.2136, -77.2811»; DMS `1°12'49"N 77°16'52"W` → «Ir a 1.213611, -77.281111»; UTM `18N 247880 134247` → «Ir a 18N 247880 134247 (1.213617, -77.26565)»; H3 `8a66a4a1b4dffff` → «Ir a la celda H3 8a66a4a1b4dffff (res. 10)». Coordenadas y H3 se resuelven sin red (red, `extra/extra.json`) |

El anexo 3.7.0 citaba una casilla «Hover tooltips» en el panel; en la web sin capas no aparece. En nuestro geoportal (con
proyecto cargado) sí aparece como «Información emergente al pasar el cursor» (§10).

### 4.3 Panel «Explorador»

Buscador «Buscar fuentes de datos» y árbol: **Mis datos** (iconos de subir/descargar; «Vacío») · **Servicios** (8: XYZ 2,
WMS 3, WFS 1, WMTS 1, ArcGIS 1, cada uno con «+») · **Recientes** («Vacío») · **Bases de datos** (PostgreSQL, SQL Server,
con «+»; «Vacío»). No aparecen «Favoritos» ni «Archivos» (este último es solo de escritorio) (cap. `paneles/pan-explorador.png`).

## 5. Panel derecho y mapa

### 5.1 Pestañas laterales derechas

| Pestaña | Contenido observado (DOM) |
| --- | --- |
| **COMENTARIOS** | Cabecera «Comentarios 0» y botón **+ Añadir comentario** (tecla `C`, `title` «Colocar un nuevo comentario de revisión en el mapa»); autor «Sin nombre definido — los comentarios aparecerán como «Autor»» (lápiz para editar); **Iniciar sesión en vivo**; campo «Introduzca el código» + **Conectar**; estado «Sin conexión / Espacio de trabajo privado»; filtros **Abiertos (0) · Resueltos (0) · Todos (0)**; vacío: «No hay comentarios abiertos…» (cap. `paneles/pan-comentarios.png`) |
| **ESTILO** | Sin capa: «Seleccione una capa para editar su estilo.» Con capa: «Estilo - puntos» y secciones Insertar debajo, Zoom mínimo/máximo, Fusión (Normal, Multiplicar, Trama, Aclarar, Añadir), Visualización (2D / Extrusión 3D), **Sugerencias de estilo** (Categorizar por nombre, Graduar por valor), Tipo de estilo (Simbología única, Graduada, Categorizada, Basada en reglas, Expresión avanzada) + **Aplicar tipo de estilo**, Renderizador de puntos (Símbolo único, Mapa de calor, Agrupado), colores de relleno/contorno con cuentagotas y «Transparente», ancho y opacidades, radio, Tamaño proporcional, Marcador, **Diagramas** (circular, anillo, barras, barras apiladas), **Generador de geometría** (centroides, cuadros delimitadores, envolventes, zonas de influencia), **Etiquetas**, **Filtros rápidos**, **Selector de plantas**, **Uniones**, **Campos virtuales**, **Formulario de atributos**, **Ventana emergente** (clic e información al pasar el cursor, campo/expresión de título y cuerpo); pie «Los cambios se aplican en vivo a las propiedades de pintura de MapLibre.» (cap. `capa/estilo-capa.png`) |
| Paneles acoplados | Al abrir un complemento con panel (p. ej. **Mapas base**) aparece otra pestaña vertical en este riel (**MAPAS BASE**) (cap. `paneles/pan-mapas-base-plugin.png`) |

### 5.2 Mapa base: tres selectores

| Selector | Dónde | Contenido (DOM) |
| --- | --- | --- |
| **Cambiar fondo** | «⋯» de la fila Fondo | Diálogo: «Elija un fondo de OpenFreeMap o Protomaps, un fondo vacío o una URL de estilo de MapLibre.» **OpenFreeMap**: Liberty (activo), Liberty 3D, Positron, Bright, Dark, Fiord · **Protomaps**: Light, Dark, White, Grayscale, Black · **Regional** (plegable) · **La Luna**: Hillshaded Albedo, OPM Basemap v0.1 · **Marte**: Colour MOLA Elevation, Viking MDIM2.1, Hillshade, OPM Basemap v0.2, Shaded Colour MOLA Elevation, Shaded Grayscale MOLA Elevation · **Otros cuerpos celestes** (plegable) · **Otro**: Blank · **URL personalizada** (`https://example.com/style.json or …/basemap.pmtiles`) + **Aplicar** (cap. `paneles/pan-cambiar-fondo.png`) |
| **Mapas base** (complemento) | Icono de la barra de Capas o Complementos → Mapas base | Panel acoplado a la derecha (textos en inglés): icono de llave (claves), «Search basemaps», «before_id: none», casilla «Add basemaps (stack instead of replace)», filtros «All providers» y «All categories», «**142 basemaps**», tarjetas con miniatura, nombre, proveedor/categoría, tipo (RASTER/STYLE/OVERLAY) y atribución. Proveedores vistos: OpenStreetMap, Google, Amazon Location, Mapbox, MapTiler, Carto, CyclOSM, ESRI, EOX, NASA GIBS, OpenRailwayMap, OpenTopoMap, Stadia Maps, Swiss Federal Geoportal, Tianditu, Amap, Tencent Maps, TopPlusOpen, USGS, Waymarked Trails, Openbasiskaart, OpenFreeMap, Protomaps, Maptoolkit, TomTom, HERE. Categorías: Street, Regional, Imagery, Terrain, Light, Outdoor, Dark, Navigation, Artistic, Marine, Labels, Cycling, Transport, Vector, Traffic. Las miniaturas se piden en vivo a cada proveedor (red: `a.tile.openstreetmap.org`, `a.tile.openstreetmap.fr`, `tile.openstreetmap.de`, `tile.osm.ch`, `mt1.google.com`…) |
| **Cuerpo celeste** | Icono de la barra de Capas | Casillas: Tierra, Luna, Marte, Calisto, Caronte, Europa, Ganímedes, Ío, Mercurio, Plutón, Titán, Venus |

### 5.3 Controles del mapa (esquina superior derecha, de arriba abajo)

| Control | Nombre accesible (DOM) | Nota |
| --- | --- | --- |
| Pantalla completa | «Enter fullscreen» | **sin traducir** |
| Brújula / norte | «Restablecer inclinación y rumbo» (letra N) | — |
| Globo | `title` «Disable globe» (sin `aria-label`) | **sin traducir**; alterna globo/plano |
| Control de capas | «Layer Control» | Panel en inglés: «Layers · Show All · Hide All · Background · ⚙» (DOM, `paneles/pan.json`) |
| Escala | `1000 km` (abajo a la izquierda) | unidades en Configuración → Mapa |
| Atribución | `<details>` compacta «ⓘ» abajo a la derecha | Desplegada: «OpenFreeMap © OpenMapTiles Data from OpenStreetMap», enlaces a openfreemap.org, openmaptiles.org y openstreetmap.org/copyright (cap. `paneles/mapa-atribucion.png`) |

Los demás controles (Navegación, Geolocalizar, Terreno, Exageración del terreno, Logotipos, Minimapa, Leyenda, etc.) se
activan desde el menú Controles (§7.3).

### 5.4 Barra de estado

| Campo | Texto (1857×982) | Comportamiento |
| --- | --- | --- |
| Coords. | `Coords.: —` (con el puntero sobre el mapa: `Coords.: -115.59050, 38.80841`) | Botón; `title` «Formato de coordenadas: Grados decimales. Haga clic para cambiar.» Ciclo observado: Grados decimales → Grados, minutos, segundos (`38°49'57.29"N 115°24'46.07"W`) → Grados, minutos decimales → UTM (`11S 668490mE 4305257mN`) → MGRS (`11SPD8383008183`) → USNG (`11S PD 99157 11108`) → Proyectadas (EPSG:3857) (`-12748878.71, 4714370.51 (EPSG:3857)`) → vuelve a DD (DOM, `capa/capa.json`) |
| Zoom | `Zoom: 2.00` | — |
| Alt. cámara | `Alt. cámara: 20.438 km` | — |
| Rumbo | `Rumbo: 0.0°` | — |
| Inclinación | `Inclinación: 0.0°` | — |
| BBox | `BBox: -180.0000, -36.2526, 180.0000, 90.0000` | Se oculta con `layout=compact` y `layout=viewer` (1440×900) |
| Diagnóstico | `⛭ Diagnóstico: N` a la derecha | Botón que abre el diálogo de §5.5; el contador sube con cada aviso o error |
| Abreviaturas | Con `layout=compact`/`viewer`: `XY: — · Zoom · Alt. cámara · Rumbo · Inclinación · Diag: 0` | (DOM, `parametros/parametros.json`) |

### 5.5 Qué hace «Diagnóstico»

Diálogo «Diagnóstico»: «Peticiones de red recientes, errores de MapLibre, advertencias de consola y excepciones en tiempo
de ejecución.» Filtros-contadores **N en total · N errores · N advertencias · N errores de red**; casilla **Registrar todas
las peticiones de red** (desmarcada: solo guarda las fallidas); **Copiar JSON**; **Limpiar**; lista de entradas con nivel,
origen y hora (p. ej. «WARNING · CONSOLE · 5:26:31 p. m. · [GeoLibre] failed to open external link (popup blocked?)»). No envía
nada a la red al abrirlo (red) (cap. `dialogos/dlg-ayuda-diagno-stico.png`, `paneles/pan-diagnostico.png`).

## 6. Configuración

### 6.1 Diálogo «Configuración» (secciones)

Diálogo único «Configuración — Configure las preferencias del proyecto y los ajustes de tiempo de ejecución.» con navegación
lateral de **10 secciones**: Idioma · Mapa · Diseño · Apariencia · Interfaz · Geocodificación · Proveedores de IA · Entorno ·
Almacenamiento en la nube · Inicio, y botones **Cancelar / Guardar configuración**. En las secciones con secretos aparece el
aviso «Los tokens y claves de API que guarde aquí se almacenan en el almacenamiento local de este navegador, donde los scripts
que se ejecutan en este sitio pueden leerlos.» (DOM, `dialogos/dlg-configuracio-n-*.png`). No hay sección de actualizaciones
en la web.

| Sección (entrada de menú) | Opciones observadas |
| --- | --- |
| Idioma (Idioma → Gestionar paquetes de idioma) | *Idioma de la interfaz* (24 idiomas); **Paquetes de idioma** de Whitebox: «No hay ningún paquete de idioma de Whitebox instalado», **Descargar paquete · Importar archivo**, «Al descargar un paquete se envía el código de idioma a languages.geolibre.app, pero ningún dato del proyecto.» |
| Mapa (Preferencias del mapa) | **Restricciones del mapa**: Restringir límites (Usar la vista actual; O/S/E/N −180/−85/180/85), Zoom mínimo 0, Zoom máximo 24, Inclinación máxima 85, Renderizar copias del mundo, **Ajustar zoom a las capas recién añadidas**; Cuerpo celeste (Earth WGS 84, Moon, Mars IAU 2000, Mercury, Venus, Io, Europa, Ganymede, Callisto, Titan, Pluto, Charon); Unidades de la barra de escala (Métricas, Imperiales, Náuticas); **Sistema de referencia de coordenadas del mapa** (Web Mercator/globo, EPSG:3413, EPSG:3031, EPSG:4326, Luna y Marte cilíndrica y polares IAU_2015, Mercurio, Venus, Ío, Europa, Ganímedes, Calisto, Titán, Plutón, Caronte, «Código EPSG personalizado…»); **Proyección del mapa de ArcGIS** (Web Mercator, Spilhaus 54099, Equal Earth 8857, Robinson 54030, Winkel Tripel 54042, Mollweide 54009, Plate Carrée 4326, polares 3995 y 3031, «WKID personalizado…»); Formato de coordenadas (7 notaciones de §5.4) |
| Diseño (Diseño → Configuración de diseño) | BARRA DE HERRAMIENTAS: Mostrar etiquetas; Mostrar información del proyecto. PANELES: Mostrar panel de capas, de estilo, del explorador, de comentarios; **Panel de capas compacto**; Mantener los paneles inferiores bajo el mapa. Nota: «Los parámetros de diseño de la URL siguen aplicándose…» |
| Apariencia | MODO: Claro / Oscuro. COLOR DE ACENTO: Azul, Violeta, Esmeralda, Rosa, Ámbar, Personalizado |
| Interfaz (Interfaz → Configuración de interfaz, o Ayuda → Simplificar interfaz...) | **Perfil de interfaz** con **Restablecer**; **Archivo de interfaz**: Exportar… / Importar… / Importar desde URL + Cargar («Un archivo exportado también funciona como enlace settingsUrl=»); NIVEL DE EXPERIENCIA: Principiante, Intermedio, Avanzado (activo), Personalizado; casillas por **Fuentes de datos** (44), **Complementos** (67, ver §7.4) y **Menús** (8 menús + 109 ítems de menú, incluido «Imprimir...»): 228 casillas en total |
| Geocodificación | Proveedor: Nominatim (OpenStreetMap), Pelias, ArcGIS World Geocoder, ArcGIS GeocodeServer (organization), Mapbox, Google, CartoCiudad (IGN España); «Este proveedor funciona sin clave de API.»; Punto de conexión directo e inverso (opcionales, por defecto `https://nominatim.openstreetmap.org/search` y `/reverse`); Correo de contacto (opcional) |
| Proveedores de IA | «Proveedores del asistente de IA», «0 perfiles», **Añadir perfil** |
| Entorno (Variables de entorno) | Cuenta de Share.GeoLibre (**Iniciar sesión**); Token de API de Share.GeoLibre (`glb_…`); Token de Cesium Ion; Token de Mapbox (`pk.…`); Clave de API de ArcGIS (`AAPT…`); **Variables de entorno** (0) con **Añadir** y uso `${NAME}` en encabezados de capa |
| Almacenamiento en la nube | **Conexiones S3** (Amazon S3 y compatibles: MinIO, Cloudflare R2, Wasabi) con **Añadir conexión** y requisito de CORS; Ubicación predeterminada del Explorador S3 (`s3://bucket/prefix/`) |
| Inicio (Configuración de inicio) | Proyecto de inicio («…al iniciarse la aplicación nativa»); Activar el globo 3D de forma predeterminada; Abrir el explorador de S3 al iniciar; Vista del mapa predeterminada (lon −100, lat 40, zoom 2, Usar la vista actual); Estilos de capa predeterminados (Elegir archivo); Capas predeterminadas (Elegir archivo) |

### 6.2 Otras entradas del menú Configuración

| Entrada | Qué abre |
| --- | --- |
| Idioma ▶ | 24 idiomas como opciones radio: English, العربية, Azərbaycanca, 简体中文, 繁體中文（香港）, 繁體中文（澳門）, 繁體中文（台灣）, Nederlands, Français, ქართული, Deutsch, עברית, हिन्दी, Bahasa Indonesia, Italiano, 日本語, 한국어, فارسی, Português, Русский, **Español** (marcado), ไทย, Türkçe, Tiếng Việt; y «Gestionar paquetes de idioma» |
| Diseño ▶ | 7 casillas (las de §6.1) + «Configuración de diseño» y el rótulo «Los parámetros de diseño de la URL anulan la configuración guardada.» |
| Apariencia ▶ | Color de acento (6 opciones) + «Configuración de apariencia» |
| Interfaz ▶ | Nivel de experiencia (Principiante, Intermedio, Avanzado, Personalizado) + «Configuración de interfaz» |
| Administrar complementos | Diálogo «Administrar complementos»: «Explore, instale, actualice y elimine complementos externos…»; pestañas **Todos (29) · Instalados (0) · No instalados (29) · Actualizables (0)**; **Configuración · Actualizar**; buscador; tarjetas con versión, descripción, autor, categorías y **Instalar** (red: `plugins.geolibre.app/plugin-registry.json`) |
| Administrador de estilos | Panel «Administrador de estilos» con etiquetas (basemap, boundary, hydrology, labels, marker, point, polygon, ramp, selection) y AJUSTES PREESTABLECIDOS INTEGRADOS (Boundary outline, Boundary outline (bold), Muted polygon, Highlight, Water, Pin marker, Labels (dark on light halo), Viridis 5 clases, Blues 5 clases, Spectral 7 clases) con **Aplicar** |

## 7. Fuentes de datos, procesamiento, controles y complementos

### 7.1 Fuentes de «Añadir datos» (lista completa, 44)

| Grupo | Fuentes (es) | N.º |
| --- | --- | --- |
| Archivos | Capa vectorial · Capa ráster · Capa de texto delimitado · Capa CAD (DXF/DWG) · Geodatabase de archivos (GDB) · Capa VTPK/TPKX de ArcGIS · Fotos geoetiquetadas · Capa GPX · Capa LandXML · Capa IndoorGML · Polilínea codificada · Capa MBTiles · Capa OSM PBF · ICESat-2 / GEDI | 14 |
| Servicios web | Capa XYZ · Capa WCS · Capa WMS · Catálogo CSW · Capa WFS · Capa WMTS · OGC API - Features · Teselas vectoriales OGC · Capa de ArcGIS · Capa GeoRSS · Límites administrativos · Capa STAC · Capa de vídeo · Capa Deck.gl | 14 |
| Formatos en la nube | Capa GeoParquet · Capa FlatGeobuf · Capa PMTiles · Capa Zarr · NetCDF / HDF | 5 |
| Capas 3D | Capa LiDAR · Gaussian splatting · Capa 3D Tiles · Recurso de Cesium Ion (deshab.) · Escena 3D dinámica CZML (deshab.) · KML / KMZ · Modelo 3D (glTF) | 7 |
| Bases de datos | Capa DuckDB · Capa de PostgreSQL · Capa de SQL Server · Capa Apache Iceberg | 4 |

Coincide uno a uno con los 44 identificadores del anexo 3.7.0 (§1.7 `hiddenDataSources`). Detalle de cada diálogo en §3.6.
También se añaden datos arrastrando archivos al mapa, desde el Explorador y con `?data=` (no probado).

### 7.2 Paneles del menú Procesamiento (DOM y red, `funciones/pr-pr-*.png`, `funciones/pr.json`)

| Elemento | Qué abre | Red observada al abrir |
| --- | --- | --- |
| Asistente de IA | Panel inferior «Asistente de IA → Configurar el asistente de IA»: lista de proveedores con su variable (Google Gemini `GEMINI_API_KEY`, Anthropic `ANTHROPIC_API_KEY`, OpenAI `OPENAI_API_KEY`, OpenRouter `OPENROUTER_API_KEY`, Vercel AI Gateway `AI_GATEWAY_API_KEY`, TrustedRouter `TRUSTEDROUTER_API_KEY`, Ollama (local) `OLLAMA_BASE_URL`, Amazon Bedrock `AWS_ACCESS_KEY_ID`+`AWS_SECRET_ACCESS_KEY`, Custom (OpenAI-compatible) `OPENAI_COMPATIBLE_BASE_URL`+`…_MODEL`) y **Abrir Configuración → Proveedores de IA** | ninguna (sin clave no habla con ningún proveedor) |
| Caja de herramientas de Whitebox | Diálogo «Ejecutando localmente con WebAssembly. No se requiere sidecar.», «Todas (1069)» y categorías | mismo origen: `whitebox-catalog-snapshot.json` (1,0 MB), `whitebox-wasm-manifests.json` (2,1 MB) |
| Conversión, Hidrología, LiDAR, Red, Proyección, Ráster, Teledetección, Terreno, Vectorial ▶ | Abren el mismo diálogo Whitebox con la herramienta elegida | ídem |
| Caja de herramientas de GeoLibre → Vectorial/Red/Estadísticas/DGGS (p. ej. Búfer) | Diálogo «Herramientas vectoriales» con todas las categorías | mismo origen: `GET /sidecar/vector/status` (sonda de *sidecar*; en la web responde 503) |
| … → Ráster (p. ej. Sombreado de relieve) | Diálogo «Herramientas ráster»: «…en el sidecar de Python (rasterio/GDAL), o en su navegador cuando no haya sidecar disponible»; Motor: Cliente (navegador) / Sidecar | — |
| … → Ráster → Descargar DEM global | Abre la caja Whitebox | mismo origen (catálogo Whitebox) |
| … → Geocodificar direcciones | Diálogo: Elegir archivo CSV; Proveedor (los 7 de §6.1); **Iniciar geocodificación** | — |
| … → Herramientas por lotes | Diálogo: herramienta vectorial (Búfer, Centroides, …, Resumir dentro, …, DGGS, Velocidad de trayectoria…) sobre varias capas | — |
| … → Segmentación con IA | Diálogo con aviso «La segmentación con IA no está disponible en el navegador. Use la aplicación de escritorio…» | mismo origen: `GET /sidecar/ml/status` (404) |
| … → Detección de objetos | Panel: YOLO ONNX en el navegador; modelos integrados YOLOv8n y YOLOv5n (COCO, «se descarga y almacena en caché una vez») o archivo local | ninguna al abrir (los pesos se piden al ejecutar; no probado) |
| … → Segmentar todo | Panel: SlimSAM en el navegador sobre un GeoTIFF; Cuadrícula, Calidad, Tamaño mín. | ninguna al abrir |
| Constructor de modelos | Panel con barra **Nuevo · Guardar · Organizar · Ejemplos · Importar · Exportar · Copiar script de Python · Ejecutar**, nodos «+ Entrada / + Salida», FLUJO DE CONTROL (Iterar ent., Iterar rást., Si/Si no, Unir ramas, Recopilar) y catálogo de herramientas | mismo origen (catálogo Whitebox) |
| Análisis basado en objetos | Panel: «1. SEGMENTAR — Añada primero una capa ráster GeoTIFF», IMPORTAR DESDE OTRO SOFTWARE | mismo origen: `GET /sidecar/obia/status` (503) |
| Espacio de trabajo SQL | Panel inferior: Motor **DuckDB · PostGIS · Apache Sedona**; Consultas de ejemplo (Países con geometría…); Ejecutar, Borrar, Añadir como capa, Exportar CSV, Exportar GeoParquet | ninguna externa al abrir (DuckDB-WASM desde el propio origen) |
| Consola de Python | Panel inferior: «Consola de Python lista. Use el objeto `geolibre`…», campo con Ctrl/Cmd+Intro | **`cdn.jsdelivr.net/pyodide/v0.27.7/full/`** (`pyodide.js`, `pyodide.asm.js`, `pyodide.asm.wasm`, `python_stdlib.zip`, `pyodide-lock.json`) |
| Cuaderno Jupyter | Panel «Cuaderno» con JupyterLite | mismo origen: `/jupyterlite/` (`api/contents/all.json`, `api/translations/*.json`, `build/*.js`) |
| Panel de control | Panel «Panel de control · 0 widgets · Añadir widget» | — |
| Historial | Diálogo «Historial de procesamiento» (0 ejecuciones; Borrar historial) | — |
| Planetary Computer | Panel (inglés) «Collections · Layers (0)» con el catálogo | `planetarycomputer.microsoft.com/api/stac/v1/collections` |
| Earth Engine | Panel (inglés) con pestañas Browse/Catalog, Search, Load, Layers, Inspector, Code, Auth; «Result count: 5310» | `accounts.google.com/gsi/client`, `raw.githubusercontent.com/opengeos/Earth-Engine-Catalog/master/gee_catalog.json`, `raw.githubusercontent.com/samapriya/awesome-gee-community-datasets/master/community_datasets.json` |

### 7.3 Controles (DOM y red, `funciones/ct-ct-*.png`, `funciones/ct.json`)

| Control | Resultado al pulsarlo | Red |
| --- | --- | --- |
| Control de capas ✓, Pantalla completa ✓, Brújula ✓, Globo ✓, Escala ✓, Atribución ✓ | Alternan el control (activos por defecto) | — |
| Navegación, Geolocalizar | Añaden los botones ± / ubicación (Geolocalizar usa la API del navegador) | — |
| Terreno | Activa el relieve 3D | **`s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png`** (+1 entrada en Diagnóstico) |
| Exageración del terreno | Diálogo: Exageración vertical; Fuente de terreno = COG de una banda EPSG:3857/4326 (CORS + rangos) o capa ráster cargada | — |
| Logotipos → Logotipo de MapLibre | Muestra el logotipo; Maptoolkit deshabilitado sin mapa base de Maptoolkit | — |
| Efectos atmosféricos ▶ | Activado, color/extensión/intensidad del halo, color del espacio, Estrellas, Vía Láctea, Líneas de constelaciones, Restablecer | — |
| Clima → Nubes → Mostrar nubes | Capa XYZ «Clouds» (0.85); en la prueba falló: «No se encontraron teselas para la capa «Clouds»» y 50 entradas en Diagnóstico | **`gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_SNPP_CorrectedReflectance_TrueColor/default/<fecha>`** |
| Clima → Precipitación → Mostrar precipitación | Capa XYZ «Precipitation» (0.80) | **`api.rainviewer.com/public/weather-maps.json`**, **`tilecache.rainviewer.com/v2/radar/…`** |
| Sol | Panel: fecha (21/06/2024), hora, Ahora, velocidad de animación, sombreado nocturno 55 % | — |
| Animación de ruta | Panel: capa de ruta, progreso, velocidad, marcador (Flecha/Punto/Ninguno), Seguir, Rastro, Guardar como MP4 | — |
| Simulador de vuelo | Panel con velocímetro, altitud, rumbo, acelerador y ayuda de teclado | — |
| Globo giratorio | Panel (inglés) «Spin Globe · Speed 10 °/s · Start» | — |
| Cuadrícula | Panel: Geográfica / UTM / MGRS-USNG, espaciado, estilo, etiquetas | glifos de `tiles.openfreemap.org/fonts/…` |
| Elevación | **Diálogo de consentimiento** «La elevación se obtiene de un servicio público… Sin relieve 3D se consulta la API pública de Open-Meteo…» **Cancelar / Continuar** | (no se continuó) |
| Direcciones | **Consentimiento**: envía waypoints a `router.project-osrm.org` («solo admite conducción») | (no se continuó) |
| Navegación paso a paso... | **Consentimiento**: inicio/paradas/destino y posición a `valhalla1.openstreetmap.de`; servidor propio con «Servidor de enrutamiento (Valhalla)» o `VITE_ROUTING_ENDPOINT` | (no se continuó) |
| Geocodificación inversa | **Consentimiento**: coordenadas al geocodificador configurado (Nominatim) | (no se continuó) |
| Buscar | Control de búsqueda en el mapa | — |
| Barra de color, Leyenda, HTML, Medir, Marcador, Estado de vista | Paneles de `maplibre-gl-components`, **en inglés** («Colorbar», «Legend», «HTML Control», «Measure» Distance/Area/Circle, «Bookmarks», «Center/Zoom/Pitch/Bearing/Projection/Bounds/Draw BBox») | — |
| Imagen | Diálogo «Imagen» (Título, URL, tamaño, posición) en español | — |
| Minimapa | Minimapa con el estilo base | glifos de `tiles.openfreemap.org` |
| Recolección de campo... | Diálogo: capa de recolección, geometría, campos (Texto, Número, Fecha, Elección), Obligatorio; Crear capa | — |
| Seguimiento GPS... | Diálogo: fuente (Este dispositivo / Receptor NMEA serie o Bluetooth), Iniciar GPS, Grabar track, Capturar punto, filtros | — |
| Grabar recorrido del mapa... | Panel de fotogramas clave (cargar/guardar configuración, generar desde ruta) | — |
| Grabar vídeo... | Panel: Todo el mapa / Seleccionar área…, fps, rótulo, Grabar | — |

### 7.4 Complementos integrados (lista completa y estado)

El catálogo de Configuración → Interfaz enumera **67 complementos** con casilla (todos activados en el nivel Avanzado por
defecto) más el grupo «Componentes»; el anexo cuenta 72 porque añade 5 que el perfil no gobierna (Control de capas, Efectos
atmosféricos, Direcciones, Geocodificación inversa y Capa Deck.gl, que se manejan desde Controles y Añadir datos). Ninguno
está «instalado» aparte: vienen en la compilación. Al cargar la app solo están activos por defecto los controles marcados
con ✓ (Control de capas, Efectos atmosféricos…) (DOM).

Prueba: cada entrada del menú Complementos se pulsó en una carga limpia (61 acciones; `funciones/cp.json`,
`funciones/cp-cp-*.png`). «Abre» resume la primera línea del panel; «Red» son los hosts externos pedidos al abrirlo
(sin contar `tiles.openfreemap.org` ni Google Analytics). Los nombres entre comillas en inglés son textos sin traducir.

| Complemento (es) | Menú | Abre | Red al abrir |
| --- | --- | --- | --- |
| GeoEditor | Complementos → GeoEditor → Activar (+ posición en 4 esquinas) | Barra de dibujo y formulario «Propiedades de la entidad» (botones «Cancel», «Save» sin traducir) | — |
| Anotaciones | → Anotaciones → Activar (+ posición) | Barra de anotaciones en el mapa | — |
| Acotaciones | → Acotaciones → Activar (+ posición) | Barra de cotas con unidades «Meters, Kilometers, Feet, US Survey Feet, Yards, Miles, Nautical Miles» | — |
| ArcGIS Hub | → Servicios web | Búsqueda de conjuntos públicos, «Buscar en el área actual del mapa» | — (busca al escribir) |
| Catálogos STAC | → Servicios web | «Buscar un catálogo público en STAC Index» | `stacindex.org` |
| CKAN | → Servicios web | Catálogo CKAN del Humanitarian Data Exchange | — |
| Datos abiertos de Planet | → Servicios web | Panel de catálogos STAC con los datos de Planet | `data.source.coop`, `stacindex.org` |
| Datos abiertos de Vantor | → Servicios web | Lista de eventos (p. ej. «Colombia-Earthquake-Aug-2026») | `vantor-opendata.s3.amazonaws.com` |
| Descargador de OSM | → Servicios web | «…usando la API pública de Overpass» | — (Overpass al descargar) |
| Dynamical | → Servicios web | Pronósticos de dynamical.org | `stac.dynamical.org` |
| Earthdata GIS | → Servicios web | Buscar · Todos/Imágenes/Mapas/Entidades/Mapas web | `gis.earthdata.nasa.gov` |
| Embeddings satelitales | → Servicios web | AlphaEarth Foundations, Tessera, Earth Index… | — |
| Explorador de Sentinel-2 | → Servicios web | Teselas MGRS coloreadas por estadísticas | `data.source.coop` |
| Explorador S3 | → Servicios web | «Introduzca s3://bucket/prefix/» | — |
| FEMA NFHL | → Servicios web | «32 layers · Insert before…» (inglés) | `hazards.fema.gov` |
| Fields of the World | → Servicios web | Año 2017–2025 | — |
| GeoLens | → Servicios web | «Connect to a GeoLens server…» (inglés): GeoLibre datasets, GeoLens demo, origen actual | — |
| Hugging Face | → Servicios web | Explorar · Subir; conjuntos sugeridos | `huggingface.co` |
| IGN LiDAR HD | → Servicios web | Cobertura de teselas LiDAR HD (Francia) | — |
| JAXA Earth | → Servicios web | Conjunto, banda, fecha | `data.earth.jaxa.jp` |
| NASA Earthaccess | → Servicios web | Búsqueda CMR de gránulos (ICESat-2, GEDI) | — |
| NASA Earthdata | → Servicios web | «Loading NASA GIBS layer catalog…» (inglés) | `gibs.earthdata.nasa.gov` |
| Natural Earth | → Servicios web | «opengeos/natural-earth» | `data.source.coop`, `tiles.geolibre.app` |
| Ocean Data Platform | → Servicios web | Colecciones de HUB Ocean | `api.hubocean.earth` |
| OpenAerialMap | → Servicios web | Vista del mapa / Dibujar cuadro / Coordenadas | — |
| Portal de ArcGIS | → Servicios web | Inicio de sesión en ArcGIS Online/Enterprise | — |
| Portolan | → Servicios web | «Buscar un catálogo público en Portolan Registry» | `raw.githubusercontent.com` |
| SIG de estados de EE. UU. | → Servicios web | Título «US State GIS» (inglés), 50 estados | — |
| SIG de India | → Servicios web | Título «India GIS» | — |
| SIG federales de EE. UU. | → Servicios web | Título «US Federal GIS», departamentos y agencias | — |
| SIG locales de EE. UU. | → Servicios web | Título «US Local GIS» | — |
| Socrata | → Servicios web | Catálogos Socrata | — |
| Source Cooperative | → Servicios web | «Mostrando 50 de 50 productos» | `tiles.geolibre.app` |
| Tennessee GIS | → Servicios web | geodata.tn.gov, «Mostrando 20 de 97…» | `www.arcgis.com` |
| US EPA EnviroAtlas | → Servicios web | Capas WMS (inglés «Insert before») | `enviroatlas.epa.gov` |
| USGS 3DEP | → Servicios web | DEM por vista, cuadro, coordenadas o cuadrángulo 24K | — |
| USGS LiDAR | → Servicios web | Capa «3DEP LiDAR Coverage» y panel «SEARCH · COPC (Planetary Computer) · EPT (AWS Open Data)» (inglés) | `index.nationalmap.gov` |
| USGS National Map | → Servicios web | Capas de The National Map | `basemap.`, `carto.`, `elevation.`, `hydro.`, `imagery.`, `index.`, `partnerships.nationalmap.gov` |
| USGS NLDI | → Servicios web | Herramientas de red NLDI | — |
| Vista de calle | → Vista de calle → Activar (+ posición) | «Street View · Google · Mapillary · Keys» (inglés) | — |
| Mapillary | → Mapillary → Activar (+ posición) | Capa «Secuencias de Mapillary» y campo «Token de acceso» | `tiles.mapillary.com` |
| Cuadrícula H3 | → DGGS | Resolución automática/fija, colores, ids de celda | `raw.githubusercontent.com` |
| S2 · A5 · Geohash · Tilecode · OLC | → DGGS | Mismo panel de resolución y estilo | — |
| DGGRID | → DGGS | Tipo de celda (Hexágono, Rombo, Triángulo), proyección ISEA/FULLER | — |
| DGGAL | → DGGS | Tipo de DGGS (GNOSISGlobalGrid, ISEA4R, ISEA9R, ISEA3H, ISEA7H…) | — |
| Mapas base | Complementos → Mapas base | Panel de 142 mapas base (§5.2) | miniaturas de cada proveedor |
| Imágenes históricas | → Imágenes históricas | Capa «Esri Wayback 2026-10-29», línea de tiempo de versiones | `wayback.maptiles.arcgis.com`, `s3-us-west-2.amazonaws.com` |
| Control de tiempo | → Control de tiempo | Barra ⏮ ▶ ⏭ ↻ con años | — |
| Timelapse | → Timelapse | Capa «Timelapse: Sentinel-2 cloudless (EOX)»; también Landsat anual y NDVI (NASA GIBS), cobertura MODIS IGBP | `tiles.maps.eox.at` (+2 entradas en Diagnóstico) |
| Overture Maps | → Overture Maps | Capas «Overture Building», versiones 2026-10-21.0, 2026-09-23.1… | `overturemaps-extras-us-west-2.s3.us-west-2.amazonaws.com` |
| GeoAgent | → GeoAgent | «Setup required · Provider & model · OpenAI Responses · OpenAI API Key» (inglés) | `accounts.google.com` |
| Perfil de elevación | → Perfil de elevación | Dibujar línea, Usar selección, unidades | — |
| Comparador de capas | → Comparador de capas | «Swipe Enabled · ORIENTATION · LEFT/RIGHT LAYERS» (inglés) | — |
| Simulador de vuelo | → Simulador de vuelo (también en Controles) | Panel de vuelo | — |
| Vista de Dios | → Vista de Dios | «Eventos terrestres en vivo… Las fuentes en vivo se muestran en el globo de Cesium» | — (requiere motor Cesium) |
| SamGeo | → SamGeo | «Segmentación con SamGeo»: URL de la API de SamGeo + Comprobar conexión | — |
| Anotación de nubes de puntos | → Anotación de nubes de puntos | «Cargue primero una nube de puntos LiDAR…» | — (+1 entrada en Diagnóstico) |

Otros complementos del catálogo de Interfaz que no tienen entrada propia en el menú Complementos: Cuadrícula, Nubes,
Precipitación, Simulación solar y Animación de ruta (están en Controles) y «Componentes» (Buscar, Barra de color, Leyenda,
HTML, Imagen, Medir, Marcador, Minimapa, Estado de vista, también en Controles).

### 7.5 Registro de complementos externos (Configuración → Administrar complementos)

`https://plugins.geolibre.app/plugin-registry.json` (versión 1) lista **29** complementos, ninguno instalado
(`red/plugin-registry.json`); `blocklist.json` está vacío. Paquetes ZIP en `github.com/opengeos/geolibre-plugins/releases`.

| id | Nombre | Versión | Categorías |
| --- | --- | --- | --- |
| aorctodss | AORCtoDSS | 0.2.0 | Climate, Raster, Data |
| copernicus-ems | Copernicus EMS Rapid Mapping | 0.2.0 | Data, Imagery |
| embed-cd | EMBED-CD | 1.0.0 | Analysis, Imagery, Raster |
| epidbot | EpidBot | 0.2.2 | Data, Visualization, Analysis |
| geoenergy-catalog | Energy Data | 1.0.0 | Data |
| geolibre-contour | Contour Lines from DEM | 0.3.7 | Raster, Visualization |
| geolibre-d2s | Data to Science (D2S) | 0.2.0 | Data, Imagery |
| geolibre-flood-gauges | US Live Flood Gauges | 0.4.1 | Hydrology, Data |
| geolibre-gbif-data | GBIF Data | 1.1.1 | Data, Ecology |
| geolibre-hypercoast | HyperCoast | 0.1.0 | Data, Imagery |
| geolibre-inaturalist-extractor | iNaturalist Extractor | 1.5.1 | Data, Ecology |
| geolibre-mapterhorn | Mapterhorn Terrain | 0.2.2 | Terrain, Basemaps |
| geolibre-nasa-opera | NASA OPERA | 0.4.0 | Data, Imagery |
| geolibre-netcdf | NetCDF Loader | 0.5.9 | Climate, Raster, Data |
| geolibre-plugin-flowmaps | Flowmaps.gl | 0.1.0 | Visualization |
| geolibre-sample-plugin | Sample Plugin | 1.2.0 | Example |
| geolibre-spatialite | SpatiaLite Spatial SQL Engine | 0.1.2 | Analysis, Data, Vector, Utilities |
| ingv-geolibre | INGV Earthquakes | 0.5.0 | Data |
| kml-kmz-import | KML / KMZ Import | 0.3.1 | Data, Vector |
| layout-composer | Layout Composer | 1.11.0 | Cartography |
| movecost | movecost — least-cost analysis | 0.2.4 | Analysis, Archaeology, Terrain |
| open-climate-service | Open Climate Service | 0.3.8 | Climate, Raster, Vector, Data |
| openrndt-geolibre | RNDT catalogue | 0.5.3 | Data |
| overpass-turbo-plugin | Overpass Turbo Plugin | 0.1.5 | Data |
| plot-sampling | Plot Sampling | 0.3.2 | Analysis, Ecology, Vector |
| poster-studio | Poster Studio · 地图海报 | 0.5.0 | Cartography, Visualization |
| roadstyle | roadstyle | 0.21.0 | Cartography, Data, Visualization |
| streamsnap | StreamSnap | 0.1.3 | Hydrology |
| zarr-timeseries-viewer | Zarr Time Series Viewer | 0.7.9 | Raster, Visualization, Data |

## 8. Parámetros de URL

**Lista que reconoce el paquete 3.9.0** (conjunto de «parámetros del anfitrión» que ningún complemento puede apropiarse,
`usePlugins-C6cfS-5V.js`; idéntico al de `apps/geolibre-desktop/src/lib/live-url.ts` de la 3.7.0):
`lat, lon, zoom, crs, url, project, plugin, plugins, tool, add, serviceUrl, serviceStyle, serviceLayer, style, dataType, data,
stac, role, shareRole, embed, viewer, theme, lang, language, collab, code, state, error, error_description, session_state, conn,
schema, table, geom, srid, layout, panels, toolbar, draw, locale, uiProfile, projectUrl, project_url, settingsUrl, settingUrl,
screenshot, iframe, hidePanels, maponly, welcome, loading` (51 nombres). Además, el módulo de herramientas
(`raster-subset-kind-BCGidNvK.js`) trata `tool` y deja fuera del formulario de la herramienta
`layout, embed, iframe, toolbar, panels, hidePanels, maponly, draw, theme, welcome, locale, lang, collab, plugin`; el resto de
parámetros rellena el formulario. `code/state/error/error_description/session_state` son de retorno OAuth;
`conn/schema/table/geom/srid` abren una capa PostgreSQL (solo escritorio). (paquete; REA también los listó como candidatos de
baja confianza: `layout`, `panels`, `toolbar`, `tool`, `add`, `serviceUrl`, `serviceStyle`, `serviceLayer`, `lat`, `lon`, `zoom`,
`conn`, `schema`, `table`, `geom`, `srid`.)

**Pruebas en vivo** (1440×900, contexto limpio, 12 s de espera; `parametros/param-*.png`, `parametros/parametros.json`):

| Parámetro probado | Efecto observado |
| --- | --- |
| (ninguno) | App completa en el idioma del navegador (es-CO → español); **sin asistente de bienvenida** |
| `layout=compact` | Barra superior solo con iconos (sin nombre de la app ni del proyecto); paneles y barra de estado presentes, con `XY:` y `Diag:` abreviados y sin BBox |
| `layout=viewer` | Barra solo-iconos con **Ver, Controles y Ayuda** y el botón de tema; panel «Capas» de solo lectura (sin barra de iconos ni buscador); sin rieles de Explorador/Comentarios/Estilo; barra de estado abreviada |
| `layout=viewer&draw=1` | Igual que `viewer` sin capas (el efecto de `draw` necesita una capa editable; no comprobado) |
| `maponly=1` | Solo el mapa: sin barra superior, paneles ni barra de estado |
| `toolbar=none` | Sin barra superior; paneles y barra de estado completos |
| `toolbar=icons` | Menús con solo icono; se mantienen «GeoLibre» y el título |
| `panels=collapsed` | Capas, Explorador, Comentarios y Estilo plegados en sus rieles; sin buscador |
| `panels=none` | Sin paneles ni rieles laterales |
| `theme=dark` | `<html class="dark">`, `color-scheme: dark`; el botón pasa a «Cambiar a modo claro» |
| `lat=1.2136&lon=-77.2811&zoom=10` | Mapa centrado en Pasto, zoom 10, BBox `-77.6362, 0.9288, -76.9260, 1.4984` |
| `?10/1.2136/-77.2811` | Mismo resultado (forma compacta zoom/lat/lon) |
| `locale=en` · `lang=pt` | Interfaz en inglés (`<html lang="en">`) · en portugués |
| `plugin=h3-grid` | Abre el panel «Cuadrícula H3» (Resolución automática, Resolución, colores, opacidad, Mostrar los id de celda…) |
| `tool=adaptive_filter` | Abre la «Caja de herramientas de Whitebox» |
| `crs=EPSG:3413` | Mapa en estereográfica polar ártica; la app reescribe la dirección a `?locale=es&crs=EPSG%3A3413&lat=90&lon=-45&zoom=0.86` (la URL sigue a la vista) |
| `loading=1` | `<html data-geolibre-load-state="ready" data-geolibre-load-pending="[]" data-geolibre-load-errors="[]">` |
| `uiProfile=beginner` | **Sin efecto visible** (los 9 menús siguen; Procesamiento visible) |
| `welcome=1` | **Sin asistente de bienvenida** |
| Atributos fijos | Toda carga pone `data-geolibre-project-generation` y `data-geolibre-project-ready-generation` en `<html>` |

No probados en vivo (no cargan nada sin un recurso externo o sin sesión): `url`/`project`/`projectUrl`/`project_url`,
`data`/`style`/`dataType`, `stac`, `add`+`serviceUrl`/`serviceLayer`/`serviceStyle`, `settingsUrl`/`settingUrl` (sí funciona en
nuestro geoportal: §10), `collab`, `role`/`shareRole`, `embed`, `iframe`, `screenshot`, `hidePanels`, `viewer`, `language`,
`plugins`.

## 9. Red: hosts a los que llama la app (el «back»)

Clasificación: **Obligatorio** = sin él la función básica (abrir la app y ver el mapa por defecto) no funciona tal como en
la web; **Por defecto, sustituible** = se pide sin que el usuario haga nada, pero se puede cambiar por configuración;
**Opcional** = solo al usar esa función. «Observado» = petición vista en la red durante la prueba; «Anunciado» = el propio
diálogo de la app nombra el host pero no se pulsó Continuar; «Estático» = solo aparece como cadena en el paquete
(`red/hosts-estaticos.txt`, 465 hosts distintos, la mayoría de complementos de catálogos y documentación).

### 9.1 Mismo origen (lo que sirve nuestro propio servidor)

| Ruta | Para qué | Estado |
| --- | --- | --- |
| `/`, `/assets/*` (586 recursos, 189 MB con WASM), `/manifest.webmanifest`, iconos | La aplicación | Obligatorio |
| `/deployment.json`, `/admin-profile.json`, `/geolibre-runtime-config.js` | Política del despliegue (en la web: `null`, `null`, `{}`) | Obligatorio (se piden siempre al cargar) |
| `/whitebox-catalog-snapshot.json` (1,0 MB), `/whitebox-wasm-manifests.json` (2,1 MB) | Caja Whitebox, Constructor de modelos | Opcional (al abrirlos); observado |
| `/jupyterlite/…` (`api/contents/all.json`, `api/translations/*.json`, `build/*.js`) | Cuaderno Jupyter | Opcional; observado |
| `/sidecar/vector/status`, `/sidecar/obia/status`, `/sidecar/ml/status` | Sondas del *sidecar* de Python (herramientas vectoriales/ráster con motor servidor, OBIA, Segmentación con IA). En la web responden 503/404 y la app usa el motor del navegador o avisa de que no está disponible | Opcional; observado |
| `/ai` | Proxy de IA gestionado (documentado en el anexo) | No observado (no hay proxy en la web) |

### 9.2 Hosts externos

| Host | Función | Clasificación | Evidencia |
| --- | --- | --- | --- |
| `tiles.openfreemap.org` | Mapa base por defecto Liberty: estilo `/styles/liberty`, teselas `/planet/<versión>/{z}/{x}/{y}.pbf`, sprites, glifos `/fonts/…` (también para etiquetas de Cuadrícula y Minimapa), ráster `natural_earth/ne2sr` | **Obligatorio** con el fondo por defecto; sustituible por otro estilo, PMTiles propio o «Blank» | observado (64 peticiones en la carga) |
| `plugins.geolibre.app` | `blocklist.json` y `plugin-registry.json` en **cada carga**; Administrar complementos | Por defecto, sustituible (`plugins.registryUrl`); sin él no hay registro externo | observado |
| `www.googletagmanager.com`, `www.google-analytics.com` | Google Analytics 4 (`G-6W3EV109T9`) de la web hospedada | **No necesario**: no forma parte de la compilación que instalamos (nuestro geoportal no lo pide) | observado |
| `nominatim.openstreetmap.org` | Buscar lugares (`/search?…&format=jsonv2&addressdetails=1&limit=6`), Geocodificación inversa, Geocodificar direcciones, texto delimitado por direcciones | Opcional, configurable (Pelias, ArcGIS, Mapbox, Google, CartoCiudad o punto propio) | observado / anunciado |
| `share.geolibre.app` | Galería (`/api/projects`, `/api/thumbnails/<id>`), Compartir, inicio de sesión, token | Opcional (`sharing.shareUrl`, o `off`) | observado |
| `collab.geolibre.app` | Colaborar (`GET /health` al abrir) y sesión en vivo de Comentarios | Opcional (`sharing.collabUrl`) | observado |
| `api.github.com` | Ayuda → Buscar actualizaciones (`/repos/opengeos/GeoLibre/releases/latest`) | Opcional | observado |
| `geolibre.app`, `github.com`, `www.google.com/maps`, `earth.google.com` | Enlaces que abren pestaña (Sitio web, GitHub, Enviar comentarios, Ver en Google Maps/Earth) | Opcional (navegación) | observado |
| `languages.geolibre.app` | Paquetes de idioma de Whitebox | Opcional | anunciado en el diálogo |
| `www.geoboundaries.org` | Añadir datos → Límites administrativos | Opcional | observado |
| `stacindex.org` | Capa STAC, Catálogos STAC, Datos abiertos de Planet | Opcional | observado |
| `planetarycomputer.microsoft.com` | Procesamiento → Planetary Computer | Opcional | observado |
| `accounts.google.com`, `raw.githubusercontent.com` | Earth Engine (cliente de inicio de sesión de Google y catálogos); `accounts.google.com` también al abrir GeoAgent | Opcional | observado |
| `cdn.jsdelivr.net` | Pyodide v0.27.7 para la Consola de Python; según el paquete, también PGlite/PostGIS, CereusDB, gdal3.js y ONNX Runtime | Opcional | observado (Pyodide) / estático (resto) |
| `s3.amazonaws.com/elevation-tiles-prod` | Controles → Terreno (teselas Terrarium) | Opcional | observado |
| `gibs.earthdata.nasa.gov` | Clima → Nubes, NASA Earthdata, Timelapse (Landsat/NDVI) | Opcional | observado |
| `api.rainviewer.com`, `tilecache.rainviewer.com` | Clima → Precipitación | Opcional | observado |
| `api.open-meteo.com` | Controles → Elevación sin terreno 3D | Opcional (con consentimiento) | anunciado + estático |
| `router.project-osrm.org` | Controles → Direcciones | Opcional (con consentimiento) | anunciado + estático |
| `valhalla1.openstreetmap.de` | Navegación paso a paso; según el anexo, también las herramientas de Red (isócronas, matriz OD, ruta) | Opcional (con consentimiento; servidor propio con `VITE_ROUTING_ENDPOINT`) | anunciado + estático |
| `tiles.geolibre.app` | Relé de GeoLibre para Natural Earth y Source Cooperative (y, según el anexo, planetas, Overpass, CKAN, OpenAerialMap, Earthdata, feeds) | Opcional | observado |
| `data.source.coop` | Datos abiertos de Planet, Explorador de Sentinel-2, Natural Earth | Opcional | observado |
| `vantor-opendata.s3.amazonaws.com` · `stac.dynamical.org` · `gis.earthdata.nasa.gov` · `hazards.fema.gov` · `huggingface.co` · `data.earth.jaxa.jp` · `api.hubocean.earth` · `www.arcgis.com` · `enviroatlas.epa.gov` · `*.nationalmap.gov` (7 subdominios) · `index.nationalmap.gov` · `tiles.mapillary.com` · `wayback.maptiles.arcgis.com` + `s3-us-west-2.amazonaws.com` · `tiles.maps.eox.at` · `overturemaps-extras-us-west-2.s3.us-west-2.amazonaws.com` | Complementos de Servicios web y otros (§7.4) | Opcional | observado |
| `a.tile.openstreetmap.org`, `a.tile.openstreetmap.fr`, `tile.openstreetmap.de`, `tile.osm.ch`, `mt1.google.com` y demás proveedores del complemento Mapas base | Miniaturas y teselas de los 142 mapas base (CARTO, Esri, EOX, Stadia, MapTiler, Mapbox, TomTom, HERE… estos últimos con clave) | Opcional | observado (miniaturas) |
| `extensions.duckdb.org` | Extensión Spatial de DuckDB-WASM al abrir vectores locales (según el anexo) | Opcional | estático (no disparado) |
| `unpkg.com` | PostGIS para PGlite y otros módulos | Opcional | estático |
| `corsproxy.io` | Reintento CORS de `maplibre-gl-components` (según el anexo) | Opcional | estático |
| `titiler.d2s.org`, `titiler.hotosm.org` | Motor ráster «titiler (server)» y complementos | Opcional | estático |
| `js.arcgis.com`, `api.mapbox.com`, `ion.cesium.com`/`api.cesium.com` | Motores de render ArcGIS, Mapbox y Cesium (token) | Opcional | estático |
| `overpass-api.de`, `overpass.kumi.systems`, `overpass.openstreetmap.fr` | Descargador de OSM | Opcional (`osm.overpassUrl`) | estático |
| `cmr.earthdata.nasa.gov`, `api.openaerialmap.org`, `samgeo.gishub.org`, `assets.geolibre.app`, `datasets.geolibre.app` | Earthaccess, OpenAerialMap, SamGeo, ejemplos y proyectos iniciales, conjuntos de ejemplo | Opcional | estático |
| `api.anthropic.com`, `api.openai.com`, `generativelanguage.googleapis.com`, `openrouter.ai`, `ai-gateway.vercel.sh`, `api.trustedrouter.com`, `api.tavily.com`, `api.duckduckgo.com` | Asistente de IA y GeoAgent (con clave del usuario) y búsqueda web | Opcional | estático |
| `en.wikipedia.org`, `earthengine.googleapis.com`, `celestrak.org`, `earthquake.usgs.gov`, `aisstream.io` | «¿Qué hay aquí?» del menú contextual (según el anexo), Earth Engine, feeds en vivo de Vista de Dios | Opcional | estático |

**Mínimo para reproducir la web «tal cual»** sin depender de GeoLibre/OpenGeos: servir la compilación (incluidos
`/whitebox-*.json` y `/jupyterlite/`), permitir `tiles.openfreemap.org` (o alojar un estilo/PMTiles propio) y decidir qué
hacer con `plugins.geolibre.app` (se pide en cada carga). Todo lo demás es opcional y se activa por función; los servicios de
GeoLibre (`share.`, `collab.`, `tiles.`, `languages.`, `assets.`, `datasets.`, `plugins.`) son sustituibles o desactivables por
`deployment.json`.

## 10. Diferencias visuales con nuestro «Estudio SIG»

Capturas de `http://www.narino.test/geoportal/#estudio` (Plesk simulado, nginx en 127.0.0.1:8088) en 1857×982 y 1440×900:
`comparacion/estudio-1857x982.png`, `comparacion/estudio-1440x900.png`, `comparacion/estudio-menu-proyecto.png`; datos en
`comparacion/estudio.json`. Menús completos del iframe recorridos con el mismo script: `menus-integracion-plesk/` y
`menus-integracion-plesk-arbol.txt`.

> **Aviso de versión.** El encargo da por hecho que la versión integrada es la 3.7.0 en modo compacto. Lo observado es
> distinto: el Plesk simulado (`/var/www/vhosts/narino.test/httpdocs/geoportal/geolibre/`) sirve **GeoLibre 3.9.0** (su
> `App-*.js` emite `version:"3.9.0"` y `geoportal/api/geolibre-version.json` fija la 3.9.0), y la interfaz **no** está en
> `layout=compact`: muestra etiquetas en la barra (`geoportal-ajustes.json`: `toolbarLabels: true`, `compactLayerList:
> false`). La 3.7.0 solo está en la copia local sin versionar `portal/geolibre/` (copia local sin versionar) (su `App-*.js` emite
> `version:"3.7.0"`); para comparar con ella se sirvió en solo lectura en `127.0.0.1:8097` y se recorrieron sus menús
> (`menus-370-local/`, `menus-370-local-arbol.txt`, `diff-menus-370-vs-390.txt`).

| Aspecto | web.geolibre.app (3.9.0) | Nuestro Estudio SIG (Plesk simulado) |
| --- | --- | --- |
| Contenedor | Página completa | `iframe` bajo la cabecera del portal (GOV.CO + logotipo + menú Mapa/Catálogo/Acerca/Insertar/Nueva ventana): ocupa 1857×882 (y = 100 px) o 1440×800 |
| URL de arranque | `/` | `geolibre/?url=…/api/proyecto.geolibre&settingsUrl=…/geolibre/geoportal-ajustes.json&locale=es&theme=light&lat=1.522328&lon=-77.617685&zoom=6.73` |
| Nombre de la app | «GeoLibre» | «Geoportal Ambiental» (`branding.appName`) |
| Color de acento | Azul (predeterminado) | Verde `#10A13B` (esquema `custom` vía `settingsUrl`): botones, deslizadores, casillas e icono del logotipo en verde |
| Título del proyecto | «Proyecto sin título» | «Geoportal Ambiental — Gobernación…» y, a su derecha, la ruta `http://www.narino.test/geoportal/api/proyecto.geolibre` («Mostrar información del proyecto») |
| Tema | Sigue al sistema | Fijado claro (`theme=light`); el portal tiene su propio selector «Automático» fuera del iframe |
| Panel Capas | Vacío, solo «Fondo» | Casilla «Información emergente al pasar el cursor», 3 grupos (Recurso hídrico, Áreas protegidas y ecosistemas estratégicos, Cambio climático y gestión del riesgo) y 13 capas de prueba con su fila de 8 iconos por capa; icono «Mostrar todas las capas» (hay capas ocultas) |
| Vista inicial | Globo, zoom 2 | Nariño, zoom 6,73, escala 50 km |
| Menú Proyecto | Galería y Compartir activos; Colaborar presente | **Galería...** y **Compartir...** deshabilitados con el rótulo «No disponible: la dirección del servidor para compartir de esta implementación no es válida.» (`sharing.shareUrl` = `http://www.narino.test/geoportal/api/compartir`); **Colaborar... no aparece** (sin `sharing.collabUrl`) |
| Resto de menús | — | Idénticos a la web 3.9.0 (mismo recorrido: 0 diferencias fuera de Proyecto) |
| Mapas base regionales | «Regional» presente en Cambiar fondo | `basemaps.regional: false` (se quita Regional) |
| Bienvenida, IA, GeoLens | Sin bienvenida; IA sin proxy; GeoLens activo | `branding.welcome: false`, `ai.enabled: false`, `geolens.url: "off"` |
| Barra de estado | Español | Español en 1440×900; en una carga de 1857×982 salió en inglés («Coords:», «Bearing», «Pitch», «Diagnostics»): fallo intermitente de carga de traducciones, no reproducido en la web |
| Red | `web.geolibre.app`, `tiles.openfreemap.org`, `plugins.geolibre.app`, **Google Analytics** | `www.narino.test`, `tiles.openfreemap.org`, `plugins.geolibre.app`, `fonts.googleapis.com` + `fonts.gstatic.com` (tipografías del portal, no de GeoLibre). **Sin Google Analytics** |

**Diferencias reales 3.7.0 → 3.9.0 en los menús** (recorrido de la copia local 3.7.0 con nuestro `deployment.json` frente a
la web; `diff-menus-370-vs-390.txt`): (1) Caja de herramientas de GeoLibre → Vectorial pasa de 34 a 35 herramientas: nueva
**«Resumir dentro»** (*Summarize within*); (2) Configuración → Idioma pasa de 21 a 24 idiomas: «中文 (Chinese)» se sustituye
por **简体中文**, **繁體中文（香港）**, **繁體中文（澳門）** y **繁體中文（台灣）**; (3) en la copia 3.7.0 servida en
`127.0.0.1` no aparecen Galería, Compartir ni Colaborar (efecto de la configuración, no de la versión). Todo lo demás
(1 068 herramientas Whitebox incluidas) es idéntico.

## 11. Qué es nuevo, distinto o ausente respecto al anexo 3.7.0

| # | Hallazgo | Tipo | Evidencia |
| --- | --- | --- | --- |
| 1 | Versión pública **3.9.0** (el anexo describe la 3.7.0; existe también la 3.8.0) | nuevo | §1 |
| 2 | Herramienta **«Resumir dentro»** (cuenta entidades que intersecan cada polígono, resume un campo y mide cobertura) en GeoLibre → Vectorial y en Herramientas por lotes | nuevo | menú, `diff-menus-370-vs-390.txt`, i18n `processing.toolMeta.vector.summarize-within.*` |
| 3 | **24 idiomas** (no 21): chino tradicional de Taiwán, Hong Kong y Macao | nuevo | menú Idioma |
| 4 | 198 claves de interfaz nuevas en el catálogo español (`i18n/diff-es-370-390.json`): Galería con pestaña **Colecciones**; panel Planetary Computer con **recorte a GeoTIFF**, **barra de color**, **animar en el Control de tiempo** y **abrir en Catálogos STAC**; Catálogos STAC con **área de búsqueda dibujada o desde archivo**, búfer, nubes máx., orden por fecha, combinaciones de bandas e índices; estilo ráster «Representación de bandas»; Earthdata GIS con **funciones ráster**; Recolección de campo con **tablas sin geometría y registros vinculados**; formularios con **valores predeterminados** (expresiones QGIS) y widget Foto; notas de importación de QGIS (formularios y simbología); terreno «Rellenar fuera del DEM con terreno global»; filtros rápidos con muestra parcial; textos de la barra de estado traducidos (`statusBar.*`); IA: «Mantener como predeterminado», proxy del despliegue como predeterminado, TrustedRouter; GPS **NTRIP/RTK** y Bluetooth de Android, **inicio de sesión con ChatGPT** y avisos de Flatpak (estos tres solo en escritorio/Android) | nuevo (textos; no todas las pantallas se recorrieron) | paquete |
| 5 | Una clave retirada: `toolbar.item.embedEditedGeometryDesc` (sustituida por `embedEditedFeaturesDesc`, que cubre también atributos editados) | cambiado | paquete |
| 6 | Ayuda → Buscar actualizaciones **consulta `api.github.com` también en la web** (el anexo lo daba como solo escritorio) | distinto | red |
| 7 | La web hospedada carga **Google Analytics 4** (`googletagmanager.com/gtag/js?id=G-6W3EV109T9` y `POST google-analytics.com/g/collect`, también al usar funciones) | confirmado (el anexo citaba solo `googletagmanager.com`) | red |
| 8 | No aparece **asistente de bienvenida** ni sin parámetros ni con `welcome=1` | distinto / no observado | §8 |
| 9 | «Imprimir...» (`project.print`) existe en el catálogo de Interfaz pero **no se muestra** en el menú Proyecto | distinto | §3.3 |
| 10 | Complementos no muestra el submenú «Instalados» (no hay ninguno instalado); el anexo lo listaba | ausente en este estado | menú |
| 11 | El Explorador no muestra «Favoritos» (sí Mis datos, Servicios, Recientes, Bases de datos) | ausente en este estado | §4.3 |
| 12 | `?uiProfile=beginner` no cambia nada visible | no observado | §8 |
| 13 | Paneles de complementos **en inglés** dentro de la interfaz en español: Add Vector Layer, Add Raster Layer, FlatGeobuf, PMTiles Layer, Zarr Layer, Add LiDAR layer, Add 3D Tiles layer, Add DuckDB layer, Mapas base (*Search basemaps*, *All providers*…), Planetary Computer, Earth Engine, Layer Control («Layers · Show All · Hide All · Background»), Spin Globe, Colorbar, Legend, HTML Control, Measure, Bookmarks, View state; controles «Enter fullscreen» y «Disable globe»; nombres de herramientas Whitebox | observado (no está en el anexo) | DOM |
| 14 | «Gaussian splatting» no abrió interfaz y dejó una entrada en Diagnóstico; «Nubes» falló («No se encontraron teselas…», 50 entradas en Diagnóstico) | fallo observado | §3.6, §7.3 |
| 15 | Registro de complementos externos: **29** (no instalados), entre ellos GBIF Data, iNaturalist Extractor, Copernicus EMS, NASA OPERA, NetCDF Loader, Layout Composer, SpatiaLite, Overpass Turbo… | estado actual | §7.5 |
| 16 | Complemento Mapas base: **142** mapas base, 26 proveedores | cifra observada | §5.2 |
| 17 | La caja Whitebox cuenta 1 068 hojas en el menú y «Todas (1069)» en su diálogo | observado | §3 |

## 12. Uso de REA 6.9.0 (`npx -y rea-agents@6.9.0`)

Navegador para REA: Chromium de Playwright lanzado con `--remote-debugging-port=9333` (`scripts/05-cdp.js`). Evidencias en
`rea/`.

| Comando | Resultado |
| --- | --- |
| `list-browser-targets http://127.0.0.1:9333` | Correcto: 1 página `https://web.geolibre.app/?locale=es&welcome=0` (aviso: no pudo determinar el estado de *attach*) |
| `analyze-web-bundle … --view web-bundle` | **Error** `invalid_request`: «view must be valid JSON» |
| `analyze-web-bundle … --detail summary --evidence_output rea/bundle-evidence.json --view '{"kind":"web-bundle","collection":"endpoints","limit":200}' --observation-ms 3000 --analysis-timeout-ms 120000 --total-analysis-timeout-ms 500000 --max-heap-mb 4096` | Correcto (código 0), completitud **parcial**: 265 scripts observados, 264 analizados, 3 228 284 nodos AST; 1 script superó el plazo de 120 s. 409 inferencias: 373 «endpoint_candidate» (todas de confianza baja; casi todas propiedades de pintura de MapLibre y nombres de parámetros de URL como `layout`, `panels`, `toolbar`, `tool`, `add`, `serviceUrl`, `conn`, `schema`, `table`, `geom`, `srid`, `lat`, `lon`, `zoom`), 35 «bundle_runtime» (Vite) y 1 «vendor_fingerprint» (React). **0 URL absolutas** detectadas como *endpoint* y **0 rutas** de aplicación; la vista `endpoints` volvió vacía. Por eso los hosts del §9 salen de la red observada y del análisis estático propio (`red/hosts-estaticos.txt`) |
| `inspect-analysis-view` | **Error** `invalid_request` («Unknown flag: --view»; con JSON, «source: missing_argument»); se leyó la evidencia JSON directamente |
| `capture-browser-scenario rea/escenario.json` (modo *launch*) | 1.ª vez **error** «The selected browser could not start» («Running as root without --no-sandbox is not supported»); 2.ª con `REA_BROWSER_NO_SANDBOX=true`: correcta pero sin eventos (faltaba `capture.events`); 3.ª con `capture.events: ["network","websockets","popups","page-errors"]`: **correcta**, 8 pasos completados (cargar, esperar barra, esperar 10 s, escribir «Pasto» en el buscador, esperar, abrir Proyecto, Nuevo..., esperar), 1 041 eventos (347 peticiones). Orígenes: `web.geolibre.app`, `www.googletagmanager.com`, `www.google-analytics.com`, `plugins.geolibre.app`, `tiles.openfreemap.org` y, en el paso de búsqueda, `nominatim.openstreetmap.org/search?q=Pasto&format=jsonv2&addressdetails=1&limit=6` (`rea/escenario-evidence.json`) |
| `inspect-web-network-capture rea/carga-cdp.har har` | 1.ª vez **error**: «HAR schema validation failed: minimum (must be >= 0)» en `/log/entries/254/timings/receive` (Playwright escribe −1). Con una copia normalizada (4 tiempos negativos → 0): **correcta**, 1 025 registros: `web.geolibre.app` 956, `tiles.openfreemap.org` 64, `www.google-analytics.com` 2, `plugins.geolibre.app` 2, `www.googletagmanager.com` 1 (`rea/har-evidence.json`) |
| `discover-webmcp-tools` | Correcto: la página declara **0** herramientas WebMCP |
| `capture-web-screenshot` | Correcto: PNG 1440×900, sha256 `5e211e1b…` (`rea/captura-rea-1440x900.png`) |
| `guidance` | Usado para averiguar los formatos de `view` y del escenario |
| No usados | `inspect-web-page`, `observe-web-session`, `export-web-scripts` (los scripts se descargaron aparte en `descarga/assets/` para el análisis estático, sin ejecutarlos) |

## 13. Lo que no se pudo comprobar

- Funciones que exigen cuenta, clave o servidor propio: Compartir y Galería con sesión, Colaborar (no se inició ninguna
  sesión), Asistente de IA (sin claves), Earth Engine (sin iniciar sesión), Cesium Ion, Mapbox, ArcGIS con clave, S3 privado,
  PostgreSQL/SQL Server/GDB (solo escritorio), Segmentación con IA (sin *sidecar*).
- Servicios con consentimiento previo: no se pulsó «Continuar» en Elevación (Open-Meteo), Direcciones (OSRM), Navegación
  paso a paso (Valhalla) ni Geocodificación inversa, así que sus peticiones no se observaron (los hosts salen del propio texto
  del diálogo).
- Ejecución de herramientas (Whitebox, vectoriales, ráster, DGGS, detección de objetos, Segmentar todo): solo se abrieron sus
  diálogos; las descargas de pesos de modelos (YOLO, SlimSAM) y de extensiones (p. ej. DuckDB Spatial desde
  `extensions.duckdb.org`, PGlite o CereusDB desde `cdn.jsdelivr.net`) no se dispararon.
- Carga de datos remotos por URL, `?url=`, `?data=`, `?stac=`, `?add=`, `?collab=`, `?settingsUrl=` en la web pública
  (sí se observa `settingsUrl` funcionando en nuestro geoportal).
- Guardar, Guardar como, Duplicar, Exportar como HTML e Importar: el navegador automatizado no mostró ningún diálogo propio
  (selector de archivos o descarga del sistema).
- El asistente de bienvenida: no apareció en ninguna prueba, así que no se pudo inventariar.
- Submenús «Seleccionar entidades ▶» y «Estilos ▶» del menú de capa (no se capturó su contenido) y la tabla de atributos.
- La captura de la web en 1857×982 se hizo en Linux sin GPU (SwiftShader): las métricas de rendimiento no son representativas.

## 14. Contenido de la carpeta

| Carpeta / archivo | Contenido |
| --- | --- |
| `crudo/` | Primera carga (captura 1857×982, DOM, texto, red, consola) y `menus-tablas.md` generado |
| `menus/`, `menus-en/` | Árbol completo de menús en español e inglés (JSON) y 39 capturas de menús y submenús |
| `menus-integracion-plesk/`, `menus-370-local/` | Mismo recorrido en nuestro Estudio SIG (3.9.0) y en la copia local 3.7.0 |
| `menus-*-arbol.txt`, `diff-menus-370-vs-390.txt` | Árboles de texto y diferencias |
| `dialogos/` | Diálogos de Proyecto, Ayuda, Configuración, Ver (`dlg.json`) y de las 44 fuentes de Añadir datos (`ad.json`), con capturas |
| `paneles/`, `capa/`, `extra/` | Paneles laterales, controles del mapa, búsqueda, capa de prueba, menú de capa, Estilo, Diagnóstico, tema oscuro |
| `funciones/` | Procesamiento (`pr.json`), Controles (`ct.json`) y Complementos (`cp.json`) con capturas y red |
| `parametros/` | 20 pruebas de parámetros de URL (1440×900) |
| `comparacion/` | Capturas y datos de nuestro Estudio SIG |
| `red/` | `hosts-estaticos.txt`, `plugin-registry.json`, `blocklist.json`, `deployment.json`, `geolibre-runtime-config.js`, `manifest.webmanifest` |
| `i18n/diff-es-370-390.json` | Claves de interfaz nuevas y retiradas entre 3.7.0 y 3.9.0 (catálogo español) |
| `rea/` | Evidencias de REA (análisis del paquete, escenario, HAR, WebMCP, captura) |

Scripts usados (fuera de esta carpeta): `../scripts/01-carga.js` … `09-extra.js`, `gen_menus.py`, `i18n_diff.py`,
`resumen_cp.py`, `arbol.js`. Paquete descargado para análisis estático (no ejecutado): `../descarga/`.

## INFORME FINAL

- **Versión observada:** GeoLibre **v3.9.0** (Ayuda → Acerca de y paquete), publicada en GitHub Pages con `deployment.json`
  nulo. Es la última etiqueta del repositorio (v3.7.0, v3.8.0, v3.9.0).
- **Recuentos:** 9 menús; 174 entradas de primer nivel; 1 438 hojas (1 068 herramientas Whitebox, 80 de la caja GeoLibre);
  **44 fuentes** en Añadir datos (14 archivos, 14 servicios web, 5 nube, 7 3D, 4 bases de datos; 2 deshabilitadas con
  MapLibre y 3 que solo funcionan en escritorio); **67 complementos** en el catálogo de Interfaz (+5 gobernados por
  Controles/Añadir datos = 72 como en el anexo), de los que el menú Complementos ofrece 61 acciones (36 servicios web, 8 DGGS,
  5 con «Activar» y posición, 12 directos); **29 complementos externos** en el registro, ninguno instalado; 24 idiomas;
  10 secciones de Configuración; 142 mapas base en el complemento.
- **Hosts externos:** obligatorio con la configuración por defecto: `tiles.openfreemap.org` (mapa base). Por defecto y
  sustituible: `plugins.geolibre.app` (registro, en cada carga). Telemetría solo de la web hospedada: `googletagmanager.com` +
  `google-analytics.com`. Opcionales por función: `nominatim.openstreetmap.org` (búsqueda/geocodificación),
  `share.geolibre.app` (Galería/Compartir), `collab.geolibre.app` (Colaborar), `api.github.com` (actualizaciones),
  `languages.geolibre.app`, `tiles.geolibre.app`, `cdn.jsdelivr.net` (Pyodide), `planetarycomputer.microsoft.com`,
  `accounts.google.com` + `raw.githubusercontent.com` (Earth Engine, Portolan, H3), `s3.amazonaws.com/elevation-tiles-prod`
  (Terreno), `gibs.earthdata.nasa.gov`, `api.rainviewer.com`/`tilecache.rainviewer.com`, `api.open-meteo.com`,
  `router.project-osrm.org`, `valhalla1.openstreetmap.de`, `www.geoboundaries.org`, `stacindex.org`, `data.source.coop` y
  los de cada complemento (§9.2). Mismo origen: `/whitebox-*.json`, `/jupyterlite/`, sondas `/sidecar/*`.
- **Nuevo respecto al anexo 3.7.0:** herramienta «Resumir dentro»; 24 idiomas (chino tradicional de TW/HK/MO); 198 claves
  de interfaz nuevas (Galería por colecciones, Planetary Computer con recorte/barra de color/Control de tiempo, búsqueda STAC
  por área y combinaciones de bandas, funciones ráster en Earthdata GIS, formularios con valores predeterminados y registros
  vinculados, notas de importación QGIS, barra de estado traducida, perfiles de IA, NTRIP/ChatGPT solo en escritorio).
  Diferencias con lo que decía el anexo: Buscar actualizaciones también llama a `api.github.com` en la web; GA4 confirmado;
  sin asistente de bienvenida; «Imprimir...» oculto; sin submenú «Instalados» ni «Favoritos» en este estado; muchos paneles
  de complementos y tres controles del mapa siguen en inglés.
- **Nuestra integración:** el Plesk simulado ya sirve **3.9.0** (no 3.7.0) y **no** está en modo compacto; sus menús son
  idénticos a la web salvo Galería/Compartir deshabilitados («…la dirección del servidor para compartir… no es válida») y
  Colaborar ausente; cambia nombre, acento verde, proyecto y vista inicial; no carga Google Analytics. La copia 3.7.0 sin
  versionar solo difiere de la 3.9.0 en «Resumir dentro» y los idiomas.
- **REA:** `list-browser-targets` ✔; `analyze-web-bundle` ✔ tras corregir el formato de `--view` (parcial: 264/265 scripts;
  0 URL ni rutas detectadas, solo candidatos de baja confianza); `capture-browser-scenario` ✔ tras `REA_BROWSER_NO_SANDBOX=true`
  y `capture.events` (8 pasos, 347 peticiones); `inspect-web-network-capture` ✔ tras normalizar tiempos negativos del HAR;
  `discover-webmcp-tools` ✔ (0 herramientas); `capture-web-screenshot` ✔; `inspect-analysis-view` ✘ (errores de entrada).
- **No comprobado:** funciones con cuenta, clave o *sidecar* (Compartir, Colaborar, IA, Earth Engine, Cesium/Mapbox/ArcGIS,
  S3 privado, PostgreSQL/SQL Server/GDB, Segmentación con IA); servicios tras consentimiento (Open-Meteo, OSRM, Valhalla,
  geocodificación inversa); ejecución de herramientas y descarga de modelos/extensiones; parámetros `url`, `data`, `stac`,
  `add`, `collab`, `settingsUrl` en la web pública; asistente de bienvenida; submenús «Seleccionar entidades» y «Estilos» de
  la capa y la tabla de atributos.
