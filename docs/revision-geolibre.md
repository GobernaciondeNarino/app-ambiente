# Revisión detallada de GeoLibre

Revisión de [GeoLibre](https://github.com/opengeos/GeoLibre) para decidir qué se ofrece en el
Geoportal Ambiental, dónde y con qué interfaz. De aquí salen el
[plan de implementación](plan-implementacion.md) y el
[plan de interfaz minimalista](plan-interfaz-minimalista.md).

| | |
| --- | --- |
| Qué se revisó | Repositorio `opengeos/GeoLibre`, rama `main` en el commit `646b530` (12 de noviembre de 2026) |
| Versión publicada | 3.7.0 (PyPI), la misma que el geoportal tiene fijada en `portal/api/geolibre-version.json`; `main` lleva cambios sin publicar |
| Fuentes | `docs/features.md`, las 30 guías de `docs/user-guide/`, `ui-profiles.md`, `deployment-policy.md`, `deployment-capabilities.md`, `network-endpoints.md`, `data-formats.md`, `self-hosting.md` y, donde la documentación no alcanza, el código de `apps/` y `packages/` |
| Comprobado en la práctica | Lo marcado «probado» se ejecutó en el geoportal con la compilación web 3.7.0 (Plesk simulado y edición Docker) |
| Inventario completo | [Anexo: inventario de funciones de GeoLibre](anexo-inventario-geolibre.md), con la fuente de cada dato |

## 1. Qué es GeoLibre

Un SIG libre (MIT) que corre en el cliente: el mapa, las capas y el análisis se ejecutan en el
navegador o en la aplicación de escritorio. No aloja ni cataloga datos: los lee de donde se le
indique y guarda los mapas como proyectos `.geolibre` que referencian esos datos. Se distribuye
como aplicación web, de escritorio (Tauri), móvil, paquete de Python y de R, e imagen Docker con un
*sidecar* de Python opcional.

Eso define el reparto de papeles: **el geoportal pone el catálogo, la ingesta, la publicación y los
proyectos; GeoLibre pone el SIG**.

## 2. Hallazgos que importan al geoportal

1. **Hay un modo de solo lectura ya hecho.** `layout=viewer` conserva capas, mapas base, búsqueda,
   identificar y filtros rápidos, y quita edición, datos, procesamiento, complementos y ajustes
   (probado: modo «Solo consulta»).
2. **La interfaz se reduce con parámetros de URL**, sin tocar el código: `maponly` (solo el mapa),
   `toolbar=none|icons`, `panels=collapsed|none`, `layout=compact`, `theme`, `locale`,
   `lat`/`lon`/`zoom` (probado: `panels=collapsed`, `theme`, `locale`, `lat`/`lon`/`zoom`).
3. **Un archivo de interfaz (`?settingsUrl=`) fija idioma, acento, disposición y perfil** para esa
   visita, restringido a campos de presentación. Su sección `layout` controla el texto de la barra,
   la lista compacta y qué paneles existen (probado: barra de iconos, lista compacta, sin paneles
   Explorador ni Comentarios).
4. **Tres niveles de interfaz** (`beginner`, `intermediate`, `advanced`) sembrados desde
   `deployment.json`, más listas explícitas de lo oculto: 8 menús, 109 elementos de menú, 44
   fuentes de datos y 72 complementos. El nivel inicial oculta el menú de procesamiento entero.
5. **Seis capacidades** (`project:edit`, `data:add`, `processing:run`, `export:data`,
   `plugins:install`, `settings:manage`) quitan menús, atajos y comandos. Son puertas de la
   interfaz, **no seguridad**: lo que no deba ser público no se publica.
6. **La paleta de comandos (`Ctrl` + `K`)** es el recurso de GeoLibre para tener pocas cosas a la
   vista y todas a mano. El visor del geoportal adopta el mismo patrón.
7. **API de incrustación `postMessage` v2**, apagada salvo que el despliegue declare sus orígenes.
   Permite a la página anfitriona mover la vista, encender capas, filtrar y leer el encuadre
   (probado: `listLayers`, `getViewport`, `setView`, `setLayerVisibility`).
8. **El mismo origen simplifica todo:** sin CORS, las cookies viajan y los GeoTIFF se leen por
   rangos. Es el despliegue que GeoLibre recomienda y el que usa el Estudio SIG.
9. **Lo que ve el visitante se diseña en el proyecto:** ventanas emergentes, leyenda, grupos y
   filtros por capa. El geoportal ya genera el proyecto con simbología, emergentes, metadatos y
   carpetas por categoría.
10. **Límites:** la barra de estado solo se oculta con `maponly`; el menú de ajustes no se puede
    ocultar por perfil (solo con `layout=viewer` o sin `settings:manage`).

## 3. Cobertura en el geoportal

«Estudio SIG» es GeoLibre integrado (todo lo que trae su compilación web). «Visor» es el mapa
propio del geoportal, pensado para la consulta pública.

| Área de GeoLibre | Qué ofrece | Estudio SIG | Visor del geoportal |
| --- | --- | --- | --- |
| Interfaz | Barra de 9 menús, paneles Capas/Explorador/Estilo/Comentarios, barra de estado, paleta de comandos, atajos, claro/oscuro, 6 acentos, 21 idiomas, niveles | Completo; presentación y nivel desde el administrador | Tarjeta única, un menú, paleta de comandos, atajos `N` `U` `R` `?` `Ctrl`+`K`, claro/oscuro, español |
| Mapa y mapas base | 4 motores (MapLibre, Mapbox, Cesium, ArcGIS), globo, terreno, vista partida, CRS a medida, decenas de mapas base | Completo | MapLibre, 7 mapas base, terreno 3D con sombreado, rumbo e inclinación |
| Añadir datos | Más de 40 fuentes: archivos, servicios OGC y ArcGIS, formatos de nube, 3D, bases de datos, arrastrar y soltar | Completo (las bases de datos externas piden escritorio o *sidecar*) | Archivos propios sin subirlos (GeoJSON, Shapefile, GeoPackage, KML/KMZ, GPX, CSV, GeoTIFF), GeoJSON por URL, WMS y XYZ; arrastrar al mapa |
| Capas | Visibilidad, opacidad, orden, grupos, renombrar, exportar, refresco en vivo | Completo | Visibilidad, opacidad, orden, categorías, ficha de metadatos, descarga |
| Estilo y etiquetas | Símbolo único, graduado, categorizado, por reglas, mapas de calor, agrupación, diagramas, extrusión, etiquetas, ráster | Completo | Simbología definida en el administrador (símbolo único, etiquetas, rampas ráster) |
| Atributos y SQL | Tabla con edición, cálculo, estadísticas, gráficos, formularios; expresiones; SQL con DuckDB, PGlite y Sedona | Completo | Tabla con filtro, orden, páginas, ubicar, CSV y filtro aplicado al mapa |
| Herramientas | Medir, dibujar, anotar, marcadores, búsqueda y geocodificación, identificar, deslizar, análisis rápido, rutas, tablero | Completo | Medir distancia y área, buscar lugares, coordenadas y entidades, identificar, mi ubicación |
| Imprimir y exportar | Composición de impresión con atlas, PNG, vídeo, HTML autónomo | Completo | Hoja A4 con encabezado institucional, norte, escala, leyenda y fuente; PNG |
| Procesamiento | Más de 1 000 herramientas Whitebox en WebAssembly, caja de herramientas propia, constructor de modelos, lotes, Python | Completo en el navegador | No aplica: es tarea del Estudio |
| Proyectos y compartir | Proyectos, historial, importar QGIS y ArcGIS Pro, compartir, galería, colaboración, mapas narrativos, campo | Completo; compartir en línea apagado por defecto | Enlace permanente, insertar el mapa (`<iframe>`), descarga del proyecto `.geolibre` |
| Complementos | 72 integrados y marcado externo | Completo; lista blanca, bloqueo y registro desde el administrador | No aplica |
| IA, Python y automatización | Asistente con clave propia, consola Python, cuadernos, paquetes de Python y R, servidor MCP | Lo que corre en el navegador; la ruta de IA del servidor, apagada | No aplica |
| Despliegue | `deployment.json`, capacidades, parámetros de URL, API de incrustación | Todos los campos editables en el administrador | Parámetros con los mismos nombres: `maponly`, `panels=collapsed`, `theme`, `lat`/`lon`/`zoom` |

## 4. Lo que no llega a la compilación web

| Función | Dónde existe | Consecuencia |
| --- | --- | --- |
| Conexión a PostGIS y SQL Server, File Geodatabase | Escritorio o *sidecar* de Python | En la edición Docker puede levantarse la imagen oficial con *sidecar* (perfil `geolibre-separado`) |
| Procesamiento ráster con rasterio y GDAL completo (reproyectar, remuestrear, curvas de nivel…) | *Sidecar* | El navegador cubre sombreado, pendiente, orientación, recorte, calculadora e índices |
| Lectura de archivos locales por ruta, guardado directo en disco, recarga al cambiar un archivo | Escritorio | En la web se elige el archivo y se descarga el proyecto |
| Ruta de IA del servidor (`/ai`) | Solo en la imagen Docker de GeoLibre, con claves | Apagada (`ai.enabled: false`); cada usuario puede usar su propia clave |
| Actualizaciones, llavero del sistema, mTLS | Escritorio | No aplican |

## 5. Mecanismos de GeoLibre para una interfaz reducida

| Mecanismo | Efecto | Uso en el geoportal |
| --- | --- | --- |
| `layout=viewer` | Solo consulta | Modo «Solo consulta» del Estudio |
| `panels=collapsed` | Capas y Estilo plegados en sus rieles | Activo por defecto («Empezar con los paneles plegados») |
| `settingsUrl` → `layout` | Barra con iconos, lista compacta, paneles visibles | Activo por defecto (disposición minimalista) |
| `interface.level` | Qué menús, fuentes y complementos aparecen | Por defecto `intermediate`; preajustes Esencial, Estándar y Completo |
| `interface.hidden*` | Oculta menús, elementos, fuentes y complementos concretos | Editable en *Interfaz y menús* |
| `capabilities` | Quita familias de funciones | Editable en *Permisos* |
| `maponly`, `toolbar=none` | Solo el mapa; sin barra superior | Disponibles en el enlace; el visor propio implementa su `maponly` |
| `theme`, `locale` | Tema e idioma | Siguen al portal |

## 6. Observaciones y riesgos

- **La documentación va por detrás del código en algunos puntos.** `network-endpoints.md` dice
  reflejar la versión 3.6.1; `data-formats.md` aún da MBTiles como exclusivo de escritorio cuando
  la web lo abre en memoria; el código acepta parámetros sin documentar (`add`, `serviceUrl`,
  `collab`, `role`).
- **GeoLibre contacta servicios públicos** cuando se usan ciertas funciones: OpenFreeMap (mapas
  base), el registro de complementos, extensiones de DuckDB, geocodificación, rutas y Pyodide desde
  una red de distribución. No recoge analítica en despliegues propios.
- **`main` avanza rápido.** La versión se fija por SHA-256; actualizar es cambiar un archivo y
  volver a comprobar la matriz de la sección 3.
- **Las capacidades y los niveles no protegen datos.** Son presentación.

## 7. Conclusión

GeoLibre ya resuelve el SIG completo y trae sus propios mecanismos para simplificarse. La
estrategia es no reimplementarlo: integrarlo tal cual como Estudio SIG, **presentarlo en su forma
más sobria por defecto**, y dar al visor público una interfaz mínima que tome de GeoLibre los
patrones que funcionan (paleta de comandos, atajos, parámetros de URL, divulgación progresiva) y
las funciones que un visitante usa sin ser especialista.
