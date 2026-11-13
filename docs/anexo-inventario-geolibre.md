# Inventario de funciones de GeoLibre 3.7.0 (rama `main`)

> Anexo de la [revisión de GeoLibre](revision-geolibre.md). Compilado el 13 de noviembre de 2026 a partir del commit `646b530` del repositorio oficial, con la fuente de cada dato entre paréntesis. Los recuentos de menús, elementos y fuentes de datos se contrastaron con el código; lo que se probó en el geoportal se indica en la revisión.

Fuente: documentación oficial del repositorio `opengeos/GeoLibre` (`docs/`) y, donde dice «código», los fuentes bajo `apps/` y `packages/` (rutas de código relativas a `apps/geolibre-desktop/src/` salvo las que empiezan por `packages/` o `scripts/`). Citas: `(archivo § sección)`; `ug/` = `docs/user-guide/`, el resto cuelga de `docs/`. «no documentado» = no aparece en la documentación ni en el código revisado.
Marcas: **W** = compilación web (navegador, Docker, PWA) · **E** = solo app de escritorio (Tauri) · **S** = requiere sidecar de Python (FastAPI) · **C** = solo con el motor Cesium.

## 1. Interfaz
### 1.1 Estructura de la pantalla
| Zona | Contenido | Fuente |
| --- | --- | --- |
| Barra superior | Nombre de la app (renombrable con `branding.appName`), 9 menús, menús de plugins externos tras Help; a la derecha botón sol/luna y nombre editable del proyecto (más su ruta con «Show project info»). En ventanas estrechas pasa a solo iconos; los menús que no caben se desplazan en una sola fila | (ug/interface.md § The top toolbar; código: `components/layout/TopToolbar.tsx`) |
| Riel izquierdo | Pestañas **Browser** (Favorites, My Data, Services, Recent, Databases, Files [E]) y **Layers** (pila de capas, «Background», selector de planeta, «Hide all layers», casilla «Hover tooltips», caja «Search places» al pie) | (ug/interface.md § The side panels; ug/adding-data.md § The Browser panel; ug/layers.md) |
| Riel derecho | Pestañas **Comments** y **Style**; ahí se acoplan también los paneles de Web Services, OBIA y los paneles de plugins. El panel Style no se abre solo al seleccionar una capa | (ug/interface.md § The side panels; features.md § Layers; ug/web-services.md) |
| Zona inferior | Tabla de atributos; Dashboard, SQL Workspace, Python Console y AI Assistant se acoplan abajo; Notebook junto al mapa. Opción (activa por defecto) de mantenerlos bajo el mapa sin restar altura a los laterales | (ug/interface.md; features.md § Platforms; código: `useDesktopSettings.ts` `bottomPanelsUnderMap`) |
| Mapa | Lienzo central; controles en las esquinas; menú contextual con clic derecho; pastillas flotantes (sesión de colaboración, Field Collection, vista de daltonismo) | (ug/interface.md § The map; ug/map-controls.md) |
| Barra de estado | Coords (clic para ciclar: grados decimales, DMS, DDM, UTM, MGRS, USNG, proyectada EPSG), Elev (apagado por defecto, con consentimiento), GPS, Zoom, Eye alt, Bearing, Pitch, BBox (oculto en ventanas estrechas), botón «Diagnostics: N», aviso «Autosave paused» | (ug/interface.md § The status bar) |
| Notificaciones | Apiladas abajo sobre la barra de estado; máx. 4; éxito/info se cierran solas; errores persisten con «Report issue»; repetidas se agrupan (×3) | (ug/interface.md § Notifications) |
| Paleta de comandos | `Ctrl`/`Cmd`+`K` o Help → Command Palette: busca y ejecuta acciones de Add Data, Processing, Controls, Plugins y Help y cada herramienta de procesamiento; respeta el perfil de interfaz y las capacidades; no existe en `layout=viewer` | (ug/interface.md § Command palette; ug/embedding.md § Embedding in a page) |
| Pantallas pequeñas | Diseño adaptable y táctil; los paneles se autoocultan; en teléfonos Layers y Style son hojas deslizantes sobre el mapa | (features.md § Platforms and interface) |

### 1.2 Menús de la barra superior
| Menú (id) | Contenido | Fuente |
| --- | --- | --- |
| Project (`project`) | New, Open From (File/URL/Gallery), Open Recent, History, Import (QGIS, ArcGIS Pro, Layer Styles), Save, Save As, Duplicate project, Save as template, Share, Export (HTML, Layer Styles, Layers), Collaborate, Print, Print Layout, Offline Basemap, Story Map | (ug/projects.md; código: `lib/ui-profile.ts`) |
| Edit (`edit`) | Undo, Redo, Select by Expression, Select by Location, Zoom to / Invert / Clear selection, Export Selected Features as Layer | (ug/interface.md § The top toolbar) |
| View (`view`) | Rendering engine, Zoom in/out, Previous/Next view, Reset pitch / north / pitch+bearing, Set View, Split View, Color vision preview, View in Google Maps / Google Earth | (ug/interface.md § The top toolbar) |
| Add Data (`addData`) | Secciones Files, Web services, Cloud formats, 3D layers, Databases (ver §3) | (ug/adding-data.md) |
| Processing (`processing`) | AI Assistant; Whitebox Toolbox y sus 9 categorías; GeoLibre Toolbox; Model Builder; Object-Based Analysis; SQL Workspace; Python Console; Jupyter Notebook; Dashboard; History; Planetary Computer; Earth Engine (ver §7) | (ug/processing.md § Two toolboxes in one menu) |
| Controls (`controls`) | Layer control; controles del mapa; Sun, Weather, Gridlines, Spinning Globe, Route Animation, Flight Simulator, Atmospheric Effects, Directions, Navigation, Reverse Geocode; componentes Search, Colorbar, Legend, HTML, Image, Measure, Bookmark, Minimap, View State; Field Collection, GPS Tracking, Record Map Tour, Record Video | (ug/map-controls.md) |
| Plugins (`plugins`) | «Activate plugin»; submenús Web Services, DGGS e Installed (+ Manage Plugins); submenú de posición en 4 esquinas para GeoEditor, Annotations, Dimensions, Street View y Mapillary | (ug/plugins.md § The Plugins menu) |
| Settings (sin id; nunca ocultable) | Language, Map Preferences, Layout, Appearance, Interface, Geocoding, AI Providers, Environment Variables, Cloud Storage, Updates [E], Startup, Manage Plugins, Style Manager | (ug/settings.md; ui-profiles.md § Settings → Interface) |
| Help (`help`) | Command Palette, Keyboard Shortcuts, Simplify Interface… (no ocultable), Website, GitHub, Diagnostics, Feedback, Check for updates, About | (ug/interface.md § The top toolbar) |

### 1.3 Atajos de teclado (se ignoran al escribir en un campo de texto; `Cmd` en macOS)
| Tecla | Acción | Fuente |
| --- | --- | --- |
| `Ctrl`/`Cmd`+`K` · `?` | Paleta de comandos · chuleta de atajos | (ug/interface.md § Command palette and keyboard shortcuts) |
| `Ctrl`/`Cmd`+`N` · `+O` · `+S` · `+Shift`+`S` | Nuevo proyecto · abrir desde archivo · guardar · guardar como | (ídem; código: `toolbar/toolbar-commands.ts`) |
| `Ctrl`/`Cmd`+`Z` · `Ctrl`/`Cmd`+`Shift`+`Z` (o `Ctrl`+`Y`) | Deshacer · rehacer (capas y estilos) | (ídem) |
| `C` | Activa/desactiva la herramienta de comentario de revisión | (ídem) |
| `N` · `U` · `R` | Norte arriba · vista cenital · restablecer inclinación y rumbo | (ídem) |
| `[` · `]` | Vista anterior · vista siguiente | (ídem) |
| `Delete` | Eliminar la capa seleccionada (con confirmación) | (features.md § Platforms and interface) |
| `+`/`-` · flechas · `Shift`+`←`/`→` · `Shift`+`↑`/`↓` | Con foco en el mapa: zoom · desplazar · rotar · inclinar | (ug/interface.md; ug/map-controls.md § Map navigation basics) |
| Ratón | Arrastrar = desplazar; rueda = zoom; botón derecho + arrastrar = rotar; `Ctrl`/`Cmd` + arrastrar = inclinar | (ug/interface.md § The map) |
| `Ctrl`/`Cmd`+`Enter` · `Tab` o `Ctrl`+`Space` | Ejecutar en SQL Workspace y Python Console · autocompletar SQL | (ug/sql-workspace.md; ug/python-console.md) |
| `Space` · `Page Up`/`Page Down` · `Esc` | Presentación de story map: reproducir/pausar · navegar · salir | (ug/storymaps.md § Present) |
| `Shift` · `Alt` · `Shift`+`Alt` · `Esc` | Selección dibujada: añadir · quitar · intersecar · cancelar | (ug/layers.md § Per-layer actions) |
| En `layout=viewer` | Se desactivan `Ctrl`/`Cmd`+`N`/`O`/`S`/`K`; siguen `[`, `]`, `n`, `u`, `r` | (ug/embedding.md § Embedding in a page) |

### 1.4 Temas, idiomas y accesibilidad
| Elemento | Detalle | Fuente |
| --- | --- | --- |
| Modo claro/oscuro | Botón sol/luna; sigue al SO por defecto; `?theme=dark` o `light` | (ug/interface.md § Theme; código: `hooks/useThemeMode.ts`) |
| Acento | Settings → Appearance: Blue, Violet, Emerald, Rose, Amber o Custom (selector o hex) | (ug/settings.md § Appearance) |
| Tipografía y superficies | IBM Plex Sans/Mono autoalojadas; escala de elevación en modo oscuro; «map-glass» translúcido para el cromo flotante | (features.md § Platforms and interface) |
| Idiomas | 21 catálogos: `en` (base), `zh`, `es`, `fr`, `de`, `pt`, `it`, `nl`, `ja`, `ko`, `ru`, `tr`, `id`, `hi`, `th`, `vi`, `az`, `ka`, y RTL con interfaz reflejada `ar`, `he`, `fa`; paquetes de idioma Whitebox opcionales. Orden de detección: `?locale`/`?lang` → idioma guardado → `navigator.languages` → `en` | (i18n.md § How it works, § Language detection; ug/settings.md § Language) |
| Accesibilidad | Pantallas comprobadas con axe, navegación por teclado, etiquetas para lector de pantalla; View → Color vision preview (protanopia, deuteranopia, tritanopia, acromatopsia; solo sesión, no afecta a exportaciones) | (features.md § Platforms; ug/interface.md § The top toolbar) |

### 1.5 Niveles de interfaz (Settings → Interface, o Help → Simplify Interface…)
| Nivel | Qué muestra | Fuente |
| --- | --- | --- |
| **Beginner** | Solo los elementos de nivel «básico» (ver ids en §1.7): oculta el menú Processing entero, 35 de las 44 fuentes de Add Data, todos los plugins salvo Layer control, Basemaps, GeoEditor y Natural Earth, y los ítems de menú intermedios y avanzados | (ui-profiles.md § Onboarding; código: `lib/ui-profile.ts` `presetHiddenSets`) |
| **Intermediate** | Básico + intermedio: aparece Processing (AI Assistant, Conversion, Vector, Geocode, SQL Workspace, Dashboard, History); siguen ocultos lo «avanzado» (Whitebox, Raster, Model Builder, Python, Notebook, Story Map, Collaborate, grabación, GPS/campo, 3D, bases de datos externas, 24 plugins especializados) | (ídem) |
| **Advanced** (por defecto) | Todo. Un perfil desactivado (`enabled:false`) equivale a Advanced | (ui-profiles.md § Onboarding; código: `activeInterfaceProfile`) |
| **Custom** | Estado automático al marcar/desmarcar fuentes de datos, plugins, menús o ítems; «Reset» restaura | (ui-profiles.md § Settings → Interface; ug/settings.md § Interface) |
| Reglas | No destructivo y reversible; se guarda en el navegador/app, nunca en el proyecto; la paleta de comandos sigue el perfil; Settings y sus entradas Language/Layout/Interface siempre visibles; el administrador puede bloquearlo (`lock`); archivo de interfaz exportable/importable (idioma, disposición, acento, perfil) | (ui-profiles.md; ug/settings.md § Interface) |

### 1.6 Parámetros de URL (nombres exactos)
| Parámetro | Valores admitidos | Efecto | Fuente |
| --- | --- | --- | --- |
| `layout` | `viewer` · `compact` (alias `embed`, `iframe`) | `viewer`: cromo de solo lectura con Layers, View, Controls (sin Field Collection ni GPS Tracking), mapas base, búsqueda/identificar, Help (sin paleta ni atajos) y los quick filters de las capas; sin Project, Edit, Add Data, Processing, Plugins, Settings, panel Style ni tabla de atributos; soltar archivos no importa nada; GeoEditor, Annotations y GeoAgent no pueden activarse. `compact`: app completa con barra solo-iconos | (ug/embedding.md § URL parameters, § Embedding in a page; código: `hooks/useLayoutOptions.ts`, `packages/plugins/src/viewer-plugins.ts`) |
| `draw` | bandera sola o `true`, `1`, `yes`, `on` | Solo con `layout=viewer` y capacidad `project:edit`: deja funcionar el editor de geometrías (capa Sketches) | (ug/embedding.md § Drawing in a viewer embed) |
| `maponly` | bandera sola o `true`, `1`, `yes`, `on` | Oculta todo el cromo (barra superior, paneles y barra de estado): solo el mapa | (ug/embedding.md § URL parameters; código: `lib/layout-params.ts`) |
| `toolbar` | `none` (alias `hidden`, `hide`, `off`) · `icons` (alias `icon`, `icon-only`) | Oculta la barra superior conservando paneles y barra de estado · botones solo-icono | (ídem) |
| `panels` | `collapsed` · `none` (alias `hidden`, `hide`, `off`) | Layers y Style plegados en sus rieles de iconos · oculta todos los paneles laterales | (ídem) |
| `hidePanels` | `true` | Alternativa para ocultar los paneles | (ídem) |
| `theme` | `dark` · `light` | Tema inicial; anula la preferencia del SO; el botón sigue funcionando | (ug/embedding.md § URL parameters) |
| `locale` / `lang` | código de idioma con catálogo (§1.4) | Idioma de la interfaz; prevalece sobre el `language` de `settingsUrl` | (i18n.md § Language detection) |
| `welcome` | `0`, `false`, `off`, `no` | Oculta el asistente de bienvenida; ya lo suprimen `url=`, `data=`, un enlace de coordenadas, `embed=1`, `VITE_WELCOME_DISABLED=1` y `branding.welcome:false` | (ug/embedding.md; código: `lib/onboarding-suppression.ts`) |
| `lat`, `lon`, `zoom` | lat ±90, lon ±180, zoom 0–24 (14 si se omite); forma compacta `?zoom/lat/lon` (`?12/40.7128/-74.006`) | Abre el mapa en esa posición; la dirección web sigue la vista al navegar | (features.md § Deployment; código: `lib/coordinate-url.ts`) |
| `crs` | `EPSG:<código>` o preajuste: `earth-arctic`, `earth-antarctic`, `earth-cylindrical`, `moon-north-polar`, `moon-south-polar`, `mars-north-polar`, `mars-south-polar` y `<cuerpo>-cylindrical` (`moon`, `mars`, `mercury`, `venus`, `io`, `europa`, `ganymede`, `callisto`, `titan`, `pluto`, `charon`) | Dibuja el mapa MapLibre en otro CRS; anula el CRS guardado para esa visita; código desconocido = aviso | (ug/embedding.md § URL parameters; código: `packages/core/src/map-crs.ts`) |
| `settingsUrl` (alias `settingUrl`) | URL de un JSON público o del mismo origen (CORS) | Antes del primer render aplica solo `language`, `layout`, `theme` (acento) y `uiProfile`; ignora credenciales, plugins y rutas; dura solo esa página; espera máx. 10 s; sirve el archivo de Settings → Interface → Export | (ug/embedding.md § URL parameters; código: `lib/desktop-settings-url.ts`) |
| `url` | URL http(s) de un `.geolibre.json` (alias en código: `project`, `projectUrl`, `project_url`, o `?https://…` sin clave) | Carga el proyecto; con `tool=` pasa a ser la entrada de la herramienta | (ug/embedding.md § The live viewer; código: `lib/project-url.ts`) |
| `data` (repetible) | URL de GeoJSON, GeoParquet, PMTiles, COG, LAS/LAZ/COPC/EPT, ZIP de GeoJSON o endpoint REST | Carga datos remotos y encuadra una vez su extensión combinada; exige CORS (y rangos de bytes para COG/Parquet/PMTiles/COPC) | (ug/embedding.md § Open remote data) |
| `style` (posicional, repetible) | URL de estilo vectorial GeoLibre/MapLibre o JSON de estilo ráster (`mode`, `bands`, `rescale`, `colormap`, `reversed`, `nodata`, `opacity`, `gamma`, `stretch`, `index`) | Simbología del `data` en la misma posición; `style=` vacío como hueco | (ídem) |
| `dataType` (posicional) | `lidar` o un nombre declarado por un plugin | Formato de un `data` sin extensión | (ídem) |
| `stac` | URL de catálogo STAC, raíz de API o colección | Abre el panel STAC Catalogs conectado; sin efecto en `layout=viewer`; oculto con `maponly` o `panels=none` | (ug/embedding.md § Open a STAC catalog) |
| `tool` | id de herramienta del menú Processing (p. ej. `adaptive_filter`) | Abre el diálogo Whitebox con la herramienta; los demás parámetros rellenan su formulario | (ug/embedding.md § Deep-linking a Processing tool) |
| `plugin` (comas o repetido) | id completo, nombre corto (sin `maplibre-gl-`, `maplibre-`, `geolibre-`) o id del registro | Activa plugins integrados; Directions y Reverse Geocode solo desde el menú; los de dibujo quedan fuera en `layout=viewer` | (ug/embedding.md § Deep-linking a plugin; ug/plugins.md § Open a plugin from a link) |
| `loading` | bandera sola o `true`, `1`, `yes`, `on` | Expone en `<html>` `data-geolibre-load-state` (`loading`/`ready`/`error`), `data-geolibre-load-pending` y `data-geolibre-load-errors` para capturas automáticas | (ug/embedding.md § Waiting for a screenshot) |
| `embed` | `1`, `true` | Marca la app como incrustada (widget Jupyter/R, HTML exportado): puente de proyecto y sin bienvenida | (ug/embedding.md § Enabling it; código: `lib/onboarding-suppression.ts`) |
| Solo en código (no documentados en `docs/`) | `add` = `xyz`, `wms`, `wmts`, `wfs`, `wcs`, `ogc-features`, `ogc-vector-tiles`, `arcgis` + `serviceUrl`, `serviceLayer`, `serviceStyle`; `collab`; `role`/`shareRole` = `view`, `comment`, `edit` | Formulario Add Data precargado; unirse a una sesión; rol de un enlace compartido | (código: `lib/data-url.ts`, `lib/project-url.ts`, `lib/live-url.ts`, `hooks/desktop-shell/useCollabShareLinkAutoOpen.ts`) |

### 1.7 Sección `interface` de `deployment.json` / UI profiles (y `admin-profile.json` heredado, mismos campos en el nivel superior)
| Campo | Tipo / ids válidos (B = básico, I = intermedio, A = avanzado: nivel a partir del cual se muestra) | Fuente |
| --- | --- | --- |
| `enabled` | boolean (por defecto `true`): activa el filtrado | (ui-profiles.md § Interface fields) |
| `level` | `beginner`, `intermediate` o `advanced`: siembra las listas ocultas | (ídem) |
| `lock` | boolean: el usuario no puede cambiar el perfil en Settings | (ídem) |
| `hiddenMenus` | `project`, `edit`, `view`, `addData`, `processing` (I), `controls`, `plugins`, `help` (los demás B; Settings no se puede ocultar) | (ui-profiles.md; código: `lib/ui-profile.ts` `TOP_LEVEL_MENUS`) |
| `hiddenMenuItems` Project | B: `project.new`, `project.openFrom`, `project.openRecent`, `project.history`, `project.import`, `project.save`, `project.saveAs`, `project.duplicate`, `project.printLayout` · I: `project.saveAsTemplate`, `project.share`, `project.exportHtml`, `project.exportLayerStyles`, `project.exportLayers`, `project.print` · A: `project.collaborate`, `project.offlineRegion`, `project.storymap` | (código: `lib/ui-profile.ts` `MENU_ITEM_CATALOG`, 109 ids) |
| `hiddenMenuItems` Edit | B: `edit.undo`, `edit.redo`, `edit.zoomToSelection`, `edit.clearSelection` · I: `edit.selectByExpression`, `edit.selectByLocation`, `edit.invertSelection`, `edit.exportSelection` | (ídem) |
| `hiddenMenuItems` View | B: `view.zoomIn`, `view.zoomOut`, `view.previousView`, `view.nextView`, `view.resetPitch`, `view.resetNorth`, `view.resetPitchBearing`, `view.renderingEngine`, `view.googleMaps`, `view.googleEarth` · I: `view.setView`, `view.splitView`, `view.colorVision` | (ídem) |
| `hiddenMenuItems` Processing | I: `processing.assistant`, `processing.conversion`, `processing.vector`, `processing.geocode`, `processing.sqlWorkspace`, `processing.dashboard`, `processing.history` · A: `processing.whitebox`, `processing.network`, `processing.statistics`, `processing.raster`, `processing.batchTools`, `processing.modelBuilder`, `processing.obiaWorkbench`, `processing.segmentation`, `processing.objectDetection`, `processing.segmentEverything`, `processing.pythonConsole`, `processing.notebook`, `processing.planetaryComputer`, `processing.earthEngine` | (ídem) |
| `hiddenMenuItems` Controls | B: `controls.layerControl`, `controls.mapControl.navigation`, `controls.mapControl.fullscreen`, `controls.mapControl.compass`, `controls.mapControl.globe`, `controls.mapControl.scale`, `controls.mapControl.attribution`, `controls.atmosphereEffects`, `controls.search` · I: `controls.mapControl.geolocate`, `controls.mapControl.terrain`, `controls.sun`, `controls.routeAnimation`, `controls.flightSimulator`, `controls.spinGlobe`, `controls.graticule`, `controls.pointerElevation`, `controls.clouds`, `controls.directions`, `controls.navigation`, `controls.reverseGeocode`, `controls.colorbar`, `controls.legend`, `controls.measure`, `controls.bookmark`, `controls.minimap` · A: `controls.mapControl.logo`, `controls.mapControl.maptoolkit-logo`, `controls.html`, `controls.image`, `controls.viewState`, `controls.fieldCollection`, `controls.gpsTracking`, `controls.recordTour`, `controls.recordVideo` | (ídem) |
| `hiddenMenuItems` Settings y Help | Settings I: `settings.mapPreferences`, `settings.environment`, `settings.managePlugins`, `settings.styleManager` · A: `settings.geocoding`, `settings.cloudStorage`. Help B: `help.commandPalette`, `help.website`, `help.github`, `help.about` · I: `help.keyboardShortcuts`, `help.feedback`, `help.checkForUpdates` · A: `help.diagnostics` | (ídem) |
| `hiddenDataSources` Files | B: `vector`, `raster`, `delimited-text`, `mbtiles` · I: `cad`, `gdb`, `photos`, `gpx`, `polyline` · A: `vtpk`, `landxml`, `indoorgml`, `osm-pbf`, `spaceborne-lidar` | (código: `lib/ui-profile.ts` `DATA_SOURCE_CATALOG`, 44 ids) |
| `hiddenDataSources` Web services | B: `xyz`, `wcs`, `wms`, `geoboundaries` · I: `csw`, `wfs`, `wmts`, `ogc-features`, `ogc-vector-tiles`, `arcgis`, `georss` · A: `stac`, `video`, `deckgl-viz` | (ídem) |
| `hiddenDataSources` Cloud, 3D, Databases | Cloud B: `geoparquet` · I: `flatgeobuf`, `pmtiles` · A: `zarr`, `netcdf`. 3D (todos A): `lidar`, `splatting`, `3d-tiles`, `cesium-ion`, `czml`, `kml`, `gltf-model`. Databases I: `duckdb` · A: `postgres`, `mssql`, `iceberg` | (ídem) |
| `hiddenPlugins` | Ids completos de plugin (columna «id» de §9). B: `maplibre-layer-control`, `maplibre-gl-basemap-control`, `maplibre-gl-geo-editor`, `maplibre-gl-natural-earth`. A: `maplibre-gl-fema-wms`, `maplibre-gl-nasa-earthdata`, `maplibre-gl-enviroatlas`, `maplibre-gl-national-map`, `maplibre-gl-arcgis-hub`, `geolibre-tennessee-gis`, `geolibre-us-federal-gis`, `geolibre-us-state-gis`, `geolibre-us-local-gis`, `geolibre-india-gis`, `maplibre-gl-source-coop`, `geolibre-s3-browser`, `maplibre-gl-huggingface`, `maplibre-gl-vantor`, `maplibre-gl-usgs-dem`, `maplibre-gl-esri-wayback`, `maplibre-gl-geoagent`, `maplibre-samgeo`, `maplibre-gl-usgs-lidar`, `geolibre-point-cloud-annotation`, `maplibre-gl-overture-maps`, `maplibre-gl-time-slider`, `maplibre-gl-components`, `maplibre-gl-streetview`. El resto, I por defecto. Excluidos del perfil (se gobiernan desde Controls/Add Data): `maplibre-atmosphere-effects`, `maplibre-gl-directions`, `maplibre-reverse-geocode`, `maplibre-deckgl-viz`, `maplibre-layer-control` | (código: `lib/ui-profile.ts` `PLUGIN_TIERS`, `MENU_MANAGED_PLUGIN_IDS`) |
| Reglas | Las listas explícitas sustituyen al preajuste de `level`; un `interface` válido y no vacío reemplaza entero a `admin-profile.json`; ocultar es solo interfaz, no control de acceso | (ui-profiles.md; deployment-policy.md § Loading, § Validation) |

### 1.8 Otras palancas para una interfaz reducida
| Palanca | Efecto | Fuente |
| --- | --- | --- |
| Settings → Layout | Show toolbar labels, Show project info, Show Layers / Style / Browser / Comments panel; lista de capas compacta (`compactLayerList`, código) | (ug/settings.md § Layout; código: `useDesktopSettings.ts`) |
| Capacidades de despliegue (§11) | Quitar una capacidad elimina sus menús, entradas de la paleta, atajos y comandos del embed; con `capabilities: []` quedan desplazar/zoom, View, Controls, visibilidad y orden de capas, identificar, selección y Help | (deployment-capabilities.md § The capabilities) |
| `branding`, `sharing.shareUrl:"off"`, `services.builtins:false`, `basemaps.regional:false` | Renombra la app, quita bienvenida, Share y Gallery, servicios de ejemplo y mapas base regionales | (deployment-policy.md § Field reference) |
| Límites | La barra de estado solo se oculta con `maponly` (no hay ajuste ni parámetro propio); el menú Settings no se oculta por perfil: solo desaparece con `layout=viewer` o sin la capacidad `settings:manage`; ocultar elementos sueltos de la barra de estado: no documentado | (código: `hooks/useLayoutOptions.ts`, `components/layout/TopToolbar.tsx`; ui-profiles.md § Settings → Interface) |
| Menú Controls | Enciende/apaga cada control del mapa y cada panel de componente; los plugins con control eligen esquina | (ug/map-controls.md) |
| Export as HTML | Un único HTML autónomo, sin servidor y sin conexión | (ug/projects.md § Export as HTML) |

## 2. Mapa y mapas base
| Elemento | Detalle | Fuente |
| --- | --- | --- |
| Motores de render | 4 intercambiables en View → Rendering engine y por panel de Split View: **MapLibre GL JS** (por defecto, sin credencial, mayor compatibilidad de plugins; deck.gl para nubes de puntos, 3D Tiles y overlays), **Mapbox GL JS** (token obligatorio), **CesiumJS** (globo nativo; sin token usa el mapa base del proyecto y terreno Terrarium/COG; token ion añade World Terrain y assets; la web hospedada trae token demo), **ArcGIS Maps SDK** (sin clave; clave API añade estilos Esri; SDK desde `js.arcgis.com`). Se guarda en el proyecto; nombres `maplibre`, `mapbox`, `cesium`, `arcgis`; menús y plugins se filtran por motor | (ug/rendering-engines.md; features.md § Rendering engines and 3D globe) |
| Controles del mapa | Navigation (zoom ±), Compass, Fullscreen, Geolocate, Globe, Terrain (doble clic: exageración vertical), Scale (métrico, imperial, náutico), Elevation, Attribution, Logos; Layer Control en el mapa (activo por defecto) | (ug/map-controls.md § Map controls; ug/plugins.md) |
| Mapas base incluidos | OpenFreeMap: Liberty (por defecto), Liberty 3D, Positron, Bright, Dark, Fiord; Protomaps: Light, Dark, White, Grayscale, Black (solo con `VITE_PROTOMAPS_API_KEY`); EOX Sentinel-2 cloudless; Openbasiskaart; fondo en blanco con color propio; URL de estilo MapLibre o PMTiles a medida | (features.md § Map workspace and basemaps; ug/adding-data.md § Basemaps; getting-started.md § Optional basemap credentials) |
| Regionales y planetarios | Regional China sin clave: 高德地图, 高德卫星, 高德混合, 腾讯地图, 腾讯深色 (GCJ-02; piden confirmación al abrir un proyecto que los use); Luna y Marte (OpenPlanetaryMap), Mercurio, Venus, Ío, Europa, Ganímedes, Calisto, Titán, Plutón, Caronte (USGS, vía `tiles.geolibre.app`); elipsoide por proyecto | (features.md § Map workspace; getting-started.md § Basemaps in mainland China; deployment-policy.md § Regional basemaps) |
| Plugin Basemaps | Galería ampliada: CARTO, Esri, EOX, USGS, NASA GIBS, OSM, Protomaps, Mapbox, MapTiler, Stadia, TomTom, HERE, Amazon Location, Tianditu, Google, swisstopo, BKG, Waymarked Trails, OpenRailwayMap; apilado de rásteres; categoría Traffic (Google, TomTom, HERE con clave) | (network-endpoints.md § Opt-in: core features; getting-started.md § Optional traffic overlays) |
| Cambio de mapa base | Doble clic en «Background» → Change background, con miniaturas; se recuerda el último elegido; visibilidad y opacidad desde Layers | (ug/layers.md § The basemap; features.md § Map workspace) |
| 3D y terreno | Globo, terreno con exageración, DEM propio (COG EPSG:3857/4326 remoto o local, o una capa COG ya cargada), extrusión de polígonos, Z real; Cesium: modos 3D/2D/Columbus, 3D Tiles, CZML, I3S, KML nativo | (features.md § Map workspace, § Rendering engines) |
| CRS | Vectores reproyectados a EPSG:4326 al cargar; mapa MapLibre en otros CRS (polar ártico/antártico y Plate Carrée terrestres, Luna, Marte, otros cuerpos, EPSG a medida) desde Settings → Map o `?crs=`; ArcGIS: Spilhaus, Equal Earth, Robinson, Winkel Tripel, Mollweide, Plate Carrée, polares, WKID; lectura de coordenadas en cualquier EPSG | (ug/settings.md § Map Preferences; features.md § Rendering engines) |
| Preferencias del mapa | Restrict map bounds, Min/Max zoom (0–24), Max pitch (0–85°), Render world copies, Celestial body, CRS, Scale bar units, Coordinate format; se guardan en el proyecto. Startup: globo 3D por defecto y vista inicial (lon, lat, zoom) | (ug/settings.md § Map Preferences, § Startup) |
| Multi-mapa | Split View: rejilla de vistas sincronizadas o independientes, cada una con su motor | (features.md § Map workspace; ug/rendering-engines.md § Mix engines) |
| Menú contextual | Coordenada (copiar), What's here? (Wikipedia), Copy as GeoJSON, Center map here, Zoom in here, Quick analysis, View in Google Maps / Google Earth | (ug/map-controls.md § Right-click quick actions) |
| Capas ambientales | Timelapse (EOX Sentinel-2, NASA GIBS), Weather (Clouds, Precipitation), Sun, Atmospheric Effects, Gridlines (grados, UTM, MGRS/USNG), Spinning Globe | (features.md § Map workspace; ug/map-controls.md § Camera, overlay, and recording tools) |

## 3. Datos («Add Data» y otras entradas)
| Formato / fuente | Entrada (id) | Dispon. | Notas | Fuente |
| --- | --- | --- | --- | --- |
| GeoJSON, GeoParquet/Parquet, FlatGeobuf, Shapefile (ZIP en web), GeoPackage (selector de tablas), GML, MapInfo TAB, KML/KMZ, IMDF | Vector Layer (`vector`), archivo o URL | W·E | DuckDB-WASM Spatial en el navegador; reproyecta a EPSG:4326; ≥100 MB se lee por streaming; aviso al pasar de 100 000 entidades | (ug/adding-data.md § Files; data-formats.md § Vector and tabular files) |
| GeoTIFF / COG | Raster Layer (`raster`) | W (URL, selector o arrastrar) · E (lectura local por ruta) | Lectura parcial remota de COG | (ug/adding-data.md § Files; getting-started.md § On the web) |
| CSV/TSV/texto delimitado, Excel | Delimited Text Layer (`delimited-text`) | W·E | Columnas X/Y con CRS de origen o geocodificación de direcciones (servicio externo); CSV sin coordenadas = tabla | (ug/adding-data.md § Files; features.md § Adding data) |
| DXF/DWG · fotos geoetiquetadas · GPX · LandXML · IndoorGML · polilínea codificada · OSM PBF · ICESat-2/GEDI | `cad` · `photos` · `gpx` · `landxml` · `indoorgml` · `polyline` · `osm-pbf` · `spaceborne-lidar` | W·E (sin restricción documentada) | Selector de capas CAD y CRS; EXIF GPS; GPX en waypoints/tracks/rutas; PBF con osmix en el navegador | (ug/adding-data.md § Files; data-formats.md) |
| Esri File Geodatabase (`.gdb`) | File Geodatabase (`gdb`) | E+S | La lee el servidor local de GeoLibre | (ug/adding-data.md § Files) |
| MBTiles | MBTiles Layer (`mbtiles`) | E (disco) · W (en memoria con sql.js, <1 GB, no persiste) | `data-formats.md` aún dice «requires desktop filesystem access» | (ug/adding-data.md § Files; features.md § Adding data) |
| TPKX / VTPK | (`vtpk`) | no documentado | Paquetes de teselas ArcGIS | (features.md § Adding data; código: `lib/ui-profile.ts`) |
| XYZ, WMS, WMTS, WFS, WCS 1.0.0, OGC API Features, OGC API Tiles, GeoRSS, CSW 2.0.2 | `xyz`, `wms`, `wmts`, `wfs`, `wcs`, `ogc-features`, `ogc-vector-tiles`, `georss`, `csw` | W·E | En web el servicio debe permitir CORS; E usa HTTP nativo (WFS sin CORS; WMS en cualquier CRS ofrecido); capas vía GetCapabilities; GetFeatureInfo; WFS con refresco y GML de respaldo | (ug/adding-data.md § Web services; data-formats.md § Web services and catalogs) |
| ArcGIS FeatureServer, VectorTileServer, MapServer, ImageServer | ArcGIS Layer (`arcgis`) | W·E | Token manual o Sign in with ArcGIS (OAuth PKCE); subcapas y funciones ráster; escritura con `applyEdits` | (ug/adding-data.md § ArcGIS services; features.md § Attribute data) |
| geoBoundaries ADM0–ADM5 · STAC · vídeo georreferenciado · Deck.gl | `geoboundaries` · `stac` · `video` · `deckgl-viz` | W·E | — | (ug/adding-data.md § Web services) |
| GeoParquet, FlatGeobuf, PMTiles, Zarr/Icechunk, NetCDF/HDF (y kerchunk) | `geoparquet`, `flatgeobuf`, `pmtiles`, `zarr`, `netcdf` | W·E | Lectura por rangos HTTP; selectores de variable y dimensión | (ug/adding-data.md § Cloud formats; data-formats.md § Raster) |
| LiDAR (LAS/LAZ/COPC/EPT), Gaussian splats, 3D Tiles e I3S, glTF/GLB, KML/KMZ | `lidar`, `splatting`, `3d-tiles`, `gltf-model`, `kml` | W·E | deck.gl; LAS/LAZ plano >250 MB rechazado por URL | (ug/adding-data.md § 3D layers; ug/embedding.md § Open remote data) |
| Cesium ion asset · CZML | `cesium-ion` · `czml` | W·E, C | Deshabilitados en motores 2D | (ug/adding-data.md § 3D layers) |
| DuckDB / DuckDB Spatial · Apache Iceberg | `duckdb` · `iceberg` | W·E | En el navegador con DuckDB-WASM; Iceberg es instantánea sin auto-refresco | (ug/adding-data.md § Databases; features.md § SQL and databases) |
| PostgreSQL / PostGIS | PostgreSQL Layer (`postgres`) | E (+S) | Teselas vectoriales por servidor local (martin) o capa editable (hasta 1 000 000); no en Mac App Store; Android/iOS en proceso; Docker: `/sidecar/postgis` con `GEOLIBRE_POSTGIS_HOSTS` | (ug/adding-data.md § Databases; features.md § Deployment; getting-started.md § Bundled conversion sidecar) |
| SQL Server / Azure SQL | SQL Server Layer (`mssql`) | E+S | Capa editable; extra `mssql` del sidecar | (ug/adding-data.md § Databases; getting-started.md) |
| Arrastrar y soltar | Vectores, GeoTIFF/COG, GPX, OSM PBF, LAS/LAZ/COPC, fotos, `.geolibre.json` | W·E | Bloqueado en `layout=viewer` y sin `data:add` | (ug/adding-data.md § Drag and drop; deployment-capabilities.md) |
| Enlaces profundos | `?url=`, `?data=`, `?stac=` | W | Ver §1.6 | (ug/embedding.md) |
| Panel Browser | Favorites, My Data (Layer Library), Services (WMS, WFS, WMTS, XYZ, ArcGIS, CSW; catálogo del despliegue con distintivo *config*), Recent, Databases, Files | W·E; Files solo E | Biblioteca de servicios guardados y capas configuradas reutilizables | (ug/adding-data.md § The Browser panel) |
| S3 privado | Settings → Cloud Storage + S3 Browser | W·E | Claves, perfiles, SSO, roles; llavero del SO y STS solo en E | (features.md § Adding data; network-endpoints.md) |
| Catálogos y nubes | Plugins → Web Services, Planetary Computer, Earth Engine, Overture Maps | W·E | Ver §9 | (ug/web-services.md; ug/data-integrations.md) |
| Extensión de Chrome | «Open data in GeoLibre» | W | Recoge enlaces y servicios de una página y los abre juntos | (features.md § Adding data) |

## 4. Capas, estilo y etiquetas
| Función | Detalle | Fuente |
| --- | --- | --- |
| Panel de capas | Visibilidad, «Hide all layers», opacidad 0–100 %, reordenar (arrastrar o Move up/down), renombrar, Zoom to layer, Identify, abrir Style, Metadata (+ Export as STAC Item), eliminar; muestra de simbología por fila; estado de sincronización; lista compacta | (ug/layers.md § Layer order and visibility, § Per-layer actions; features.md § Layers; código: `hooks/useDesktopSettings.ts` `compactLayerList`) |
| Layer actions (`…`) | Rename, New group from layer, Edit geometry, Load features into editor, Open attribute table, Quick analysis, Select features, Select by Expression/Location, Bind to Time Slider, Export, Styles, Save to My Data, Copy/Paste style, Refresh / Auto refresh, Reload from disk / Watch file [E], Save edits to source [E], Materialize to editable layer, Edit query in SQL Workspace, Clear filters | (ug/layers.md § Per-layer actions; ug/styling.md § Quick filters) |
| Exportar capa | GeoJSON, GeoParquet, GeoPackage, KML, KMZ, Shapefile ZIP, CSV; ráster: GeoTIFF (COG) y Extract subset; LiDAR: LAS/LAZ/COPC; extrusión 3D: glTF (.glb), OBJ, STL | (ug/layers.md § Per-layer actions, § 3D model export) |
| Grupos | Anidados; crear (vacío, desde capa o selección), mover, opacidad de grupo, plegar, ordenar A–Z/Z–A, desagrupar o borrar; reflejados en el Layer Control | (ug/layers.md § Layer groups) |
| Capas en vivo | Refresco manual o automático (off, 15 s, 30 s, 1 min, 5 min, 15 min, personalizado) para WFS y GeoJSON URL; registro `connection` en el proyecto; capacidades por capa (solo lectura, crear/actualizar/borrar) | (ug/layers.md § Refreshing live layers; features.md § Layers) |
| Simbología vectorial | Single, Graduated (Equal interval, Quantile, Natural breaks, Standard deviation, Geometric interval, Manual; 2–12 clases), Categorized (1–12 o All), Rule-based (filtro, símbolo y escala por regla, anidadas), Advanced expression; relleno, trazo, opacidad, radio; estilo de línea (solid, dashed, dotted, dash-dot, long dash, custom) y blur; marcadores circle, square, triangle, diamond, star, cross, pin o imagen SVG/PNG/JPEG/GIF; patrones de relleno; símbolos proporcionales; zoom mín./máx.; se aplica con «Apply style type» | (ug/styling.md § Vector styling, § Style type; features.md § Layers, styling, and labels) |
| Puntos y otros renderizadores | Single symbol, Heatmap (radio, intensidad, rampa, peso), Clustered (radio, zoom máx.); Diagram (pie, donut, bar, stacked bar); extrusión 3D (campo de altura, base, pisos apilados); blend modes Normal, Multiply, Screen, Lighten, Add; máscaras de polígono invertido, líneas con flechas, generadores de geometría; sugerencias de estilo y color automático al añadir | (ug/styling.md § Point renderer, § Diagram symbology; ug/layers.md § Blend modes; features.md § Layers) |
| Etiquetas | Por atributo o expresión; color, tamaño, halo; ancla, desplazamiento X/Y, rotación, ancho de ajuste, mayúsculas/minúsculas; prioridad de colocación; duplicados / unique / concatenate; formato numérico | (features.md § Layers, styling, and labels; ug/styling.md § Vector styling) |
| Leyenda | Control Legend autogenerado desde las capas visibles (clases, gradientes, símbolos proporcionales, diagramas, RAT); modo edición (renombrar, ocultar, reordenar, esquina, plegar, exportar JSON); guardada en el proyecto y compartida con Print Layout; Colorbar; leyenda WMS en el panel Style | (features.md § Layers; ug/styling.md § Raster styling; ug/print-layout.md § Legend editor) |
| Ventanas emergentes | Diseñador por capa: campos, orden y etiquetas; formato Text, Number, Date, Link, Image; prefijo/sufijo; título por campo o expresión; cuerpo por expresión; interruptores independientes de clic y de hover; ancho e imagen; se guarda en el proyecto y es lo que ve `layout=viewer`; casilla global «Hover tooltips» | (ug/styling.md § Popups and hover tooltips; ug/layers.md § Hover tooltips) |
| Identificar | Por capa (botón Identify) o todas las visibles a la vez en un popup agrupado; valor de píxel en ráster; GetFeatureInfo en WMS; perfil espectral en multibanda | (ug/layers.md; features.md § Layers; ug/styling.md § Spectral profile) |
| Filtros | Quick filters (Values con recuento, Range, Dates, Text) guardados en el proyecto y disponibles en `layout=viewer`; filtro persistente por expresión; icono de embudo en la capa; ventana del Time Slider; `setFilter` del embed; Floor picker para interiores | (ug/styling.md § Quick filters, § Floor picker) |
| Ráster | Brightness, Saturation, Contrast, Hue Rotate; pseudocolor de una banda (colormap, clases), RGB, índice normalizado; stretch Linear/Logarithmic/Square root, gamma, nodata, histograma con tiradores, viewport stretch; cubo 3D para NetCDF/HDF | (ug/styling.md § Raster styling; features.md § Layers) |
| Intercambio de estilos | OGC SLD, QGIS QML, Mapbox GL JSON, GeoLibre URL style (`.geolibre.style.json`); importar desde archivo o texto; Style Manager; Export/Import Layer Styles por nombre de capa | (ug/layers.md § Importing and exporting styles; ug/projects.md § Layer styles) |

## 5. Atributos, expresiones y SQL
| Función | Detalle | Fuente |
| --- | --- | --- |
| Tabla de atributos | Barra: Edit/Save, Add field, Calculate, Fields, Explore, Statistics, Charts, Dashboard, Refresh, Export, Search attributes, Zoom to selection, Show All/Selected, Clear selection; filas virtualizadas; ordenar por cabecera; selección compartida con el mapa (`Ctrl`/`Shift`+clic) | (ug/attribute-table.md § The toolbar, § Selecting features) |
| Campos | Renombrar, borrar, ocultar, reordenar; Field calculator (incluye longitud y área geodésicas); campos virtuales; uniones persistentes; seguimiento de edición (creado/editado por y cuándo); explorador de columnas | (features.md § Attribute data and expressions; ug/attribute-table.md) |
| Formularios | Widgets Text, Number, Range, Checkbox, Date, Value map, Photo; alias, obligatorio, restricción, visibilidad condicional, valor por defecto | (ug/attribute-table.md § Attribute forms) |
| Estadísticas y gráficos | Count, Nulls, Unique, Min, Max, Mean, Median, Std dev, Sum; gráficos Histogram, Scatter, Bar, Line, Box plot, Pie (PNG/SVG); Raster Attribute Table | (ug/attribute-table.md § Field statistics, § Charts; features.md) |
| Exportar | GeoJSON, GeoParquet, GeoPackage, KML, KMZ, Shapefile ZIP, CSV; líneas como polilínea codificada; respeta campos ocultos | (ug/attribute-table.md § Exporting) |
| Expresiones | Expression Builder común (referencia de funciones, lista de campos, vista previa, variables `@map_zoom`, `@map_scale`, `@feature_count`, `@project_name`, `@layer_name`) para filtros, etiquetas, estilo, cálculo y selección; base: expresiones MapLibre | (features.md § Attribute data; ug/styling.md § Quick filters) |
| Selección | Select by Expression (selección o filtro persistente), Select by Location; dibujando: clic, rectángulo, polígono, mano alzada, radio | (ug/layers.md § Per-layer actions; features.md) |
| SQL Workspace | Motores DuckDB Spatial (por defecto), PostGIS (PGlite, ~19 MB) y Apache Sedona (CereusDB; sidecar SedonaDB opcional en E); consulta capas cargadas, archivos y URL (`s3://`, `gs://`, `az://`); autocompletado, consultas de ejemplo, historial; Add as layer, Add as query layer, Export CSV / GeoParquet | (ug/sql-workspace.md) |
| Escritura al origen | ArcGIS `applyEdits` (dominios, subtipos, adjuntos, registros relacionados) W·E; GeoJSON/GeoPackage, PostGIS y SQL Server solo E; GeoLens | (features.md § Attribute data, § SQL and databases; ug/layers.md) |

## 6. Herramientas del mapa, impresión y medios
| Herramienta | Detalle | Fuente |
| --- | --- | --- |
| Medir | Controls → Measure: Distance, Area, Circle; selector de unidad; Exact segment (longitud + rumbo); Heading y Final heading (ortodrómicos, rosa de 16 puntos); Terrain (3D) | (ug/map-controls.md § Measuring distance, area, and heading) |
| Dibujar y editar | GeoEditor (dibujo, vértices, snapping, borrado, digitalización topológica, masas de edificios; capa Sketches); Annotations: Text, Arrow, Rectangle/Ellipse/Freehand highlight, Pin marker, Sticky note, Placed image, con panel Elements; Dimensions (cotas lineales y angulares) | (ug/plugins.md; ug/map-controls.md § Annotations; features.md § Plugins) |
| Identificar | Botón Identify por capa o todas las visibles a la vez, valor de píxel y GetFeatureInfo (detalle en §4); se conserva en `layout=viewer` | (ug/layers.md § Per-layer actions; features.md § Layers; ug/embedding.md § URL parameters) |
| Marcadores y vistas | Pin marker; Bookmark (cámara + capas activas, carpetas, exportación, guardados en el proyecto); comentarios de revisión anclados (responder, resolver, filtrar) | (ug/map-controls.md § Component tools, § Review comments; features.md § Map tools) |
| Búsqueda y geocodificación | Search (control), «Search places» (lugares, coordenadas DD/DMS/DDM/UTM/MGRS, celda H3, atributos de capas), Reverse Geocode; Nominatim por defecto, Pelias, ArcGIS, Mapbox, Google, CartoCiudad | (features.md § Layers; ug/settings.md § Geocoding; network-endpoints.md) |
| Imprimir | Print Layout: título/subtítulo, tamaños A4, A3, Letter, Legal, Tabloid, Full HD, HD, 4K, Square o a medida; orientación, márgenes, fondo; escala 1:N; extensión dibujada; leyenda editable y personalizada, barra de escala, norte, fecha, atribución, pie, borde, bloque de información, colorbar, tabla de atributos, gráfico; Atlas (página por entidad o a lo largo de una línea, tokens `{atlas.*}`); exporta PNG, PDF (imagen 150 DPI), SVG editable, Copy to Clipboard. `project.print` («Print») sin detalle documentado | (ug/print-layout.md; deployment-capabilities.md) |
| Exportar imagen | PNG desde Print Layout o portapapeles; `exportImage()` del embed (PNG `data:` URL, los 4 motores); `to_image()` en Python; «map image export» se menciona sin guía propia | (ug/print-layout.md § Exporting; ug/embedding.md § Switching renderers; ug/interface.md) |
| Vídeo | Record Video (lienzo o recuadro, con leyenda/colorbar/HTML), Record Map Tour (fotogramas clave, JSON), Route Animation (MP4), Timelapse | (ug/map-controls.md § Camera, overlay, and recording tools; features.md § Map tools) |
| Deslizar y comparar | Layer swipe (`swipe`), Split View, Historical imagery (Esri Wayback), Time Slider, Timelapse | (ug/plugins.md; features.md § Map workspace) |
| Controles informativos | Colorbar, Legend, HTML, Image (hasta 20 por mapa), Minimap, View State | (ug/map-controls.md § Component tools) |
| Análisis rápido | Clic derecho: buffers (3 distancias), isócronas en coche y a pie (5/10/15 min, Valhalla externo), viewshed (2/5/15 km); por capa: buffer, centroides, envolvente convexa, bounding box; Line of sight; Elevation Profile | (ug/map-controls.md § Quick analysis; features.md § Map tools) |
| Rutas | Directions (OSRM público, solo coche), Navigation giro a giro (Valhalla: coche, bici, a pie, voz, simulación) | (features.md § Map tools; ug/map-controls.md) |
| Dashboard | Widgets Histogram, Scatter, Bar, Line, Box plot, Pie, Indicator, Selector (filtro cruzado), List; guardado en el proyecto | (ug/processing.md § Dashboard) |

## 7. Procesamiento y análisis
| Bloque | Detalle | Fuente |
| --- | --- | --- |
| Estructura del menú | Dos cajas en un menú: **Whitebox Toolbox** (ítem + 9 submenús de categoría) y **GeoLibre Toolbox** (Conversion, Vector, Network, Spatial Statistics, Raster, DGGS, Geocode Addresses, Batch tools, AI Segmentation, Object Detection, Segment Everything); después Model Builder, Object-Based Analysis, SQL Workspace, Python Console, Jupyter Notebook, Dashboard, History, Planetary Computer, Earth Engine | (ug/processing.md § Two toolboxes in one menu) |
| Whitebox Toolbox | 1 000+ herramientas (Whitebox Next Gen + geolibre-rust): Vector (~315), Raster (~255), Remote Sensing (~155), Hydrology (~100), Terrain (~100), LiDAR (~65), Conversion (~50), Network (~25), Projection (4); WASM en el navegador por defecto («Run locally (WASM)»), sidecar opcional en E; búsqueda, catálogo sin conexión, `?tool=` y Copy link | (ug/processing.md § Whitebox Toolbox; features.md § Processing and analysis) |
| GeoLibre → Vector | Geometry (Buffer, Centroids, Convex hull, Dissolve, Bounding box, Simplify, Reproject, Explode, Aggregate, Smooth, Extract vertices, Points along geometry, Regular grid, Voronoi/Delaunay, Cell-site coverage, Decode/Encode polyline), Overlay (Clip, Intersection, Difference, Union), Join (Spatial, Attribute), Select (by value, by location, Random extract), Movement & time, Data management (Merge layers), Data quality (validez, reparar, topología). Motores: Turf.js, GeoPandas (sidecar), Pyodide | (ug/processing.md § Vector, § Engines) |
| GeoLibre → Raster | Terrain, Reproject, Clip, Raster to Vector, Vector to Raster, Analysis + Download Global DEM y Georeferencing. Con motor cliente: Hillshade, Slope, Aspect, Clip by extent, Raster calculator, Spectral index, Reclassify, Focal statistics. Solo sidecar (rasterio): Reproject, Resample, Clip by mask layer, Polygonize, Contour, Interpolation, Zonal statistics, Mosaic | (ug/processing.md § Raster) |
| GeoLibre → Conversion | Vector to Vector / GeoParquet / FlatGeobuf / Shapefile / GeoPackage / PMTiles, CSV to GeoParquet, Raster to PMTiles, Raster to COG; todas con motor cliente (DuckDB-WASM, `geolibre-wasm`); en E usan el sidecar (cualquier formato GDAL) | (ug/processing.md § Conversion) |
| Network · Statistics · DGGS | Isochrone, OD cost matrix, Sequential route (Valhalla) · Moran global y local, Getis-Ord Gi*, vecino más próximo, Kernel density, Emerging Hot Spot, Composite score · DGGS Generator, Binning, Compact (H3, S2, A5, DGGRID, DGGAL) | (ug/processing.md § Network, § Spatial Statistics, § DGGS) |
| IA sobre imagen | AI Segmentation (SamGeo/SAM 3 en servidor `samgeo-api` vía sidecar), plugin SamGeo (directo, también web), Object Detection y Segment Everything (onnxruntime-web, cliente), OBIA (segmentación, jerarquía, random forest/reglas, importación eCognition; WASM o SLIC/Felzenszwalb en sidecar) | (ug/processing.md § AI Segmentation, § Object-Based Analysis; features.md § Processing) |
| Model Builder | Lienzo de nodos (herramientas vectoriales cliente + catálogo Whitebox), validación del grafo, Iterate Features/Rasters, Collect Results, Conditional Switch, Branch Merge; guardar en el proyecto, importar/exportar, Copy Python script; la IA puede generar modelos | (ug/processing.md § Model Builder; features.md § Processing) |
| Lotes e historial | Batch tools (Batch y Models); Processing History con Re-run, Edit & re-run, Copy JSON, Copy Python | (ug/processing.md § Geocode Addresses and Batch tools, § Finding and running a tool) |
| Motores | Whitebox WASM · Turf.js · Pyodide (GeoPandas/Shapely) · DuckDB-WASM Spatial · `geolibre-wasm` · geotiff.js · gdal3.js (exportación, CDN) · onnxruntime-web · PGlite · CereusDB · sidecar Python (rasterio, GeoPandas, GDAL/rio-cogeo, freestiler, whitebox-workflows) · servicios externos Valhalla y `samgeo-api` | (ug/processing.md § The Python sidecar; network-endpoints.md; getting-started.md § Optional extras) |

## 8. Proyectos, compartir, colaboración, mapas narrativos y campo
| Función | Detalle | Fuente |
| --- | --- | --- |
| Formato | `.geolibre` / `.geolibre.json`: vista, mapa base, capas con origen y estilo, preferencias, estado de plugins, variables de entorno; guarda referencias, no los datos | (ug/projects.md; features.md § Projects and sharing) |
| Ciclo de vida | New (con Examples y plantillas), Open From File/URL/Gallery, Open Recent, Save, Save As, Duplicate, Save as template (Strip data layers); en web se abre con el selector del navegador y se guarda con diálogo o descarga | (ug/projects.md § New, § Open, § Save and Save As, § Templates) |
| Historial | Autoguardado a IndexedDB 3 s tras cada cambio; History con Restore, Compare y Restore this layer; topes 20 instantáneas, 10 MB cada una, 50 MB en total; aviso de recuperación solo en navegador no incrustado | (ug/projects.md § Project history and crash recovery) |
| Importar | QGIS `.qgs`/`.qgz` (capas, grupos, estilos, vista, formularios QField) y ArcGIS Pro `.aprx`/`.mapx` (primer mapa 2D); informa de lo omitido | (ug/projects.md § Importing a QGIS project, § Importing an ArcGIS Pro project) |
| Compartir | Project → Share sube el proyecto a `share.geolibre.app` (o servidor propio) y devuelve una URL pública; comprobación previa de fuentes inaccesibles; roles view/comment/edit, caducidad, contraseña, revocación; inicio de sesión OAuth PKCE o token; Gallery | (ug/projects.md § Share; features.md § Deployment and platform builds) |
| Exportar | Export as HTML (autónomo), Export Layer Styles, Export Layers (capas de inicio) | (ug/projects.md § Export as HTML, § Layer styles, § Layers files) |
| Colaboración | Project → Collaborate: sesiones en vivo (MVP experimental) con instantáneas del proyecto, cursores, chat, modo view-only o co-edit y permisos por participante; apagada sin `sharing.collabUrl` / `VITE_GEOLIBRE_COLLAB_URL` | (collaboration.md; ug/projects.md § Collaborate) |
| Mapas narrativos | Project → Story Map: capítulos desde la vista actual (alineación, animación `flyTo`/`easeTo`/`jumpTo`, rotación, duración), efectos de opacidad de capas, portada y cierre, minimapa, presentación con autoplay y herramientas temporales, importar/exportar JSON y CSV, Handout PDF, Export HTML (carga MapLibre y scrollama por CDN) | (ug/storymaps.md) |
| Campo | Field Collection (puntos, líneas, polígonos con formulario y fotos; por GPS o toque), GPS Tracking (posición, track, GPX/GeoJSON; NMEA por Web Serial/Bluetooth solo Chromium; NTRIP en Android); sin sincronización con servidor; Offline Basemap precarga teselas | (ug/field-collection.md; ug/map-controls.md § GPS tracking; ug/projects.md § Offline basemap) |
| Inicio | Proyecto de inicio (E), capas y estilos por defecto, vista inicial | (ug/settings.md § Startup) |

## 9. Complementos integrados (72)
| Plugin | id completo · `?plugin=` | Dónde | Qué añade (ug/plugins.md § Built-in plugin reference; código: `scripts/plugin-reference.json`) |
| --- | --- | --- | --- |
| Layer control | `maplibre-layer-control` · `layer-control` | Controls | Lista de capas sobre el mapa; activo por defecto |
| GeoEditor | `maplibre-gl-geo-editor` · `geo-editor` | Plugins | Dibujo, edición de vértices, snapping y borrado en capas GeoJSON |
| Annotations | `maplibre-gl-annotations` · `annotations` | Plugins | Barra de anotaciones y panel Elements |
| Dimensions | `maplibre-gl-dimensions` · `dimensions` | Plugins | Cotas lineales y angulares tipo CAD |
| FEMA NFHL | `maplibre-gl-fema-wms` · `fema-wms` | Web Services | Capas WMS de riesgo de inundación de FEMA |
| NASA Earthdata | `maplibre-gl-nasa-earthdata` · `nasa-earthdata` | Web Services | Más de 1 100 capas globales NASA GIBS por fecha |
| US EPA EnviroAtlas | `maplibre-gl-enviroatlas` · `enviroatlas` | Web Services | Servicios ambientales de la EPA |
| USGS National Map | `maplibre-gl-national-map` · `national-map` | Web Services | Topografía, imagen, hidrografía y elevación del USGS |
| USGS NLDI | `maplibre-usgs-nldi` · `usgs-nldi` | Web Services | Trazado de cauces, cuencas y navegación de red |
| USGS 3DEP | `maplibre-gl-usgs-dem` · `usgs-dem` | Web Services | Modelos de elevación 3DEP |
| USGS LiDAR | `maplibre-gl-usgs-lidar` · `usgs-lidar` | Web Services | Recorta nubes 3DEP y descarga COPC |
| Vantor Open Data | `maplibre-gl-vantor` · `vantor` | Web Services | Imagen satelital de desastres (COG) |
| Planet Open Data | `geolibre-planet-open-data` · `planet-open-data` | Web Services | Datos de desastres de Planet vía STAC |
| Portolan | `geolibre-portolan` · `portolan` | Web Services | Registro Portolan de catálogos |
| Earthdata GIS | `maplibre-gl-earthdata-gis` · `earthdata-gis` | Web Services | Servicios ArcGIS de NASA EOSDIS |
| NASA Earthaccess | `geolibre-earthaccess` · `earthaccess` | Web Services | Búsqueda y descarga de gránulos CMR; ICESat-2 y GEDI |
| OpenAerialMap | `maplibre-gl-openaerialmap` · `openaerialmap` | Web Services | Imagen aérea y de dron abierta |
| OSM downloader | `geolibre-osm-downloader` · `osm-downloader` | Web Services | Descarga OSM por Overpass |
| IGN LiDAR HD | `geolibre-ign-lidar-hd` · `ign-lidar-hd` | Web Services | Nubes LiDAR HD de Francia |
| ArcGIS Portal | `geolibre-arcgis-portal` · `arcgis-portal` | Web Services | Contenido de ArcGIS Online/Enterprise con sesión |
| ArcGIS Hub | `maplibre-gl-arcgis-hub` · `arcgis-hub` | Web Services | Datos públicos de ArcGIS Hub |
| Tennessee GIS | `geolibre-tennessee-gis` · `tennessee-gis` | Web Services | Portal geodata.tn.gov |
| US federal GIS | `geolibre-us-federal-gis` · `us-federal-gis` | Web Services | Portales de 24 agencias federales |
| US state GIS | `geolibre-us-state-gis` · `us-state-gis` | Web Services | Portales de los 50 estados y DC |
| US local GIS | `geolibre-us-local-gis` · `us-local-gis` | Web Services | Unos 150 portales locales de EE. UU. |
| India GIS | `geolibre-india-gis` · `india-gis` | Web Services | Límites abiertos de India |
| Socrata | `maplibre-gl-socrata` · `socrata` | Web Services | Portales de datos abiertos Socrata |
| CKAN | `maplibre-gl-ckan` · `ckan` | Web Services | Humanitarian Data Exchange |
| STAC catalogs | `geolibre-stac-catalogs` · `stac-catalogs` | Web Services | Cualquier API o catálogo STAC |
| Source Cooperative | `maplibre-gl-source-coop` · `source-coop` | Web Services | Productos cloud-native de Source.coop |
| S3 browser | `geolibre-s3-browser` · `s3-browser` | Web Services | Explora buckets S3 públicos o privados |
| Natural Earth | `maplibre-gl-natural-earth` · `natural-earth` | Web Services | Temas vectoriales y ráster de Natural Earth |
| Hugging Face | `maplibre-gl-huggingface` · `huggingface` | Web Services | Archivos geoespaciales del Hub y subidas |
| Satellite embeddings | `geolibre-satellite-embeddings` · `satellite-embeddings` | Web Services | Embeddings AlphaEarth, Tessera, Earth Index |
| Fields of the World | `geolibre-fields-of-the-world` · `fields-of-the-world` | Web Services | Parcelas agrícolas globales 2017–2025 |
| Sentinel-2 explorer | `geolibre-sentinel2-explorer` · `sentinel2-explorer` | Web Services | Búsqueda y visor Sentinel-2 sin API |
| Ocean Data Platform | `geolibre-ocean-data-platform` · `ocean-data-platform` | Web Services | Datos oceánicos de HUB Ocean |
| Dynamical | `geolibre-dynamical` · `dynamical` | Web Services | Pronósticos meteorológicos como Zarr |
| JAXA Earth | `geolibre-jaxa-earth` · `jaxa-earth` | Web Services | Conjuntos de la JAXA Earth API |
| GeoLens | `maplibre-gl-geolens` · `geolens` | Web Services | Catálogo espacial GeoLens autoalojado |
| Street View | `maplibre-gl-streetview` · `streetview` | Plugins | Panoramas de Google Street View |
| Mapillary | `maplibre-gl-mapillary` · `mapillary` | Plugins | Imagen a pie de calle de Mapillary |
| H3 | `maplibre-h3-grid` · `h3-grid` | DGGS | Malla hexagonal H3 |
| S2 | `maplibre-s2-grid` · `s2-grid` | DGGS | Malla de celdas S2 |
| A5 | `maplibre-a5-grid` · `a5-grid` | DGGS | Malla pentagonal A5 |
| DGGRID | `maplibre-dggrid` · `dggrid` | DGGS | Mallas globales DGGRID |
| DGGAL | `maplibre-dggal` · `dggal` | DGGS | Mallas globales DGGAL |
| OLC | `maplibre-olc` · `olc` | DGGS | Malla Open Location Code |
| Geohash | `maplibre-geohash` · `geohash` | DGGS | Malla Geohash |
| Tilecode | `maplibre-tilecode` · `tilecode` | DGGS | Malla de teselas z/x/y |
| Basemaps | `maplibre-gl-basemap-control` · `basemap-control` | Plugins | Galería de mapas base |
| Historical imagery | `maplibre-gl-esri-wayback` · `esri-wayback` | Plugins | Imagen histórica Esri Wayback |
| Time slider | `maplibre-gl-time-slider` · `time-slider` | Plugins | Filtra o anima capas temporales |
| Timelapse | `geolibre-timelapse` · `timelapse` | Plugins | Anima mapas base anuales y graba vídeo |
| Overture Maps | `maplibre-gl-overture-maps` · `overture-maps` | Plugins | Temas de Overture Maps |
| GeoAgent | `maplibre-gl-geoagent` · `geoagent` | Plugins | Panel de agente de IA en el mapa |
| Elevation profile | `geolibre-elevation-profile` · `elevation-profile` | Plugins | Perfil del terreno sobre una línea |
| Layer swipe | `maplibre-gl-swipe` · `swipe` | Plugins | Barra deslizante para comparar dos capas |
| Gridlines | `maplibre-gl-graticule` · `graticule` | Controls | Retícula de coordenadas, UTM y MGRS/USNG |
| Clouds | `maplibre-gl-clouds` · `clouds` | Controls → Weather | Nubes NASA casi en tiempo real |
| Precipitation | `maplibre-gl-precipitation` · `precipitation` | Controls → Weather | Radar de RainViewer |
| Atmospheric effects | `maplibre-atmosphere-effects` · `atmosphere-effects` | Controls | Espacio, estrellas, cometas y halo; activo por defecto |
| Sun simulation | `geolibre-sun` · `sun` | Controls | Posición del sol y terminador día/noche |
| Route animation | `geolibre-route-animation` · `route-animation` | Controls | Anima un marcador sobre una línea |
| Flight simulator | `geolibre-flight-simulator` · `flight-simulator` | Plugins y Controls | Vuelo libre con teclado |
| God's eye view | `gods-eye-view` · `gods-eye-view` | Plugins | Feeds en vivo sobre el globo Cesium |
| SamGeo | `maplibre-samgeo` · `samgeo` | Plugins | Segmenta imagen a vectores (servidor SamGeo) |
| Point cloud annotation | `geolibre-point-cloud-annotation` · `point-cloud-annotation` | Plugins | Etiqueta puntos LiDAR y exporta LAS |
| Directions | `maplibre-gl-directions` · solo menú | Controls | Ruta por clics con OSRM público |
| Reverse geocode | `maplibre-reverse-geocode` · solo menú | Controls | Dirección del punto pulsado |
| Deck.gl layer | `maplibre-deckgl-viz` · `deckgl-viz` | Add Data | Overlay deck.gl; activo por defecto |
| Components | `maplibre-gl-components` · `components` | Controls | Search, Legend, Measure, Bookmark, Minimap, etc. |
| Externos | Registro `plugins.geolibre.app` (Settings → Manage Plugins: instalar, actualizar, quitar; hash verificado; lista de bloqueo), URL de manifiesto, ZIP, carpeta local [E], drop-ins en `public/plugins/<id>/`; API de plugins (paneles, menús, herramientas de IA, `dataType`) | — | (ug/plugins.md § Manage Plugins, § Where plugins come from; features.md § Plugins) |

## 10. IA, Python y automatización
| Función | Detalle | Fuente |
| --- | --- | --- |
| AI Assistant | Panel de chat (Processing → AI Assistant) sobre Strands Agents; apagado hasta configurar proveedor o proxy `/ai`; acciones auditables y deshacibles; SQL solo lectura; envía solo nombres de capas/campos y la vista. Herramientas: inspeccionar capas, NL→SQL, geoprocesos, Whitebox, Model Builder, simbología, añadir datos, Planetary Computer, control del mapa, búsqueda web, herramientas de plugins, código JS/Python | (ug/ai-assistant.md § What it can do, § Safety and privacy) |
| Proveedores | Google Gemini, Anthropic, OpenAI, OpenRouter, Vercel AI Gateway, TrustedRouter, UberLLM, Ollama local, Amazon Bedrock, OpenAI-compatible; perfiles con nombre; claves en el dispositivo o llavero; voz (Web Speech API; no en Firefox ni escritorio) | (ug/ai-assistant.md § Setup, § Limitations; ug/settings.md § AI Providers) |
| Python Console | Pyodide en el navegador (web y escritorio) con el objeto `geolibre`; hilo principal; sin acceso al sistema de archivos | (ug/python-console.md) |
| Notebook | JupyterLite + Pyodide en web; JupyterLab gestionado con `uv` en E; cliente `geolibre` precargado | (features.md § AI, Python, and automation; ug/processing.md § Jupyter Notebook) |
| Paquetes | Python `geolibre` (anywidget en Jupyter, `DashMap`, API tipo leafmap, `to_html`, Whitebox, Earth Engine, xarray); R `geolibre` (RStudio, Quarto, Shiny) | (features.md § AI, Python, and automation; getting-started.md § In Jupyter, § In R) |
| MCP y skill | Servidor `geolibre-mcp` (stdio; crea proyectos sin navegador; herramientas `live_*` sobre el escritorio abierto); skill de agente en `skills/geolibre/` | (features.md § AI, Python, and automation) |

## 11. Despliegue
| Tema | Detalle | Fuente |
| --- | --- | --- |
| Carga de `deployment.json` | Web y Jupyter: `<base>/deployment.json` antes del primer render (espera máx. 3 s; la plantilla contiene `null`); escritorio: archivo de máquina o de `<app_config_dir>`; Docker lo genera en cada arranque desde `GEOLIBRE_DEPLOYMENT_FILE` + variables `GEOLIBRE_*`. Precedencia: política final → `window.__GEOLIBRE_DEPLOYMENT_ENV__` → variables de compilación. Desde v3.3.0 | (deployment-policy.md § Loading, § Precedence between sources, § Docker, § Desktop) |
| `version` | `1` (obligatorio; otra versión se ignora) | (deployment-policy.md § Top level) |
| `capabilities` | Lista de `project:edit`, `data:add`, `processing:run`, `export:data`, `plugins:install`, `settings:manage`; omitido = todas; `[]` = ninguna | (deployment-policy.md § capabilities) |
| `interface` | `enabled`, `level`, `lock`, `hiddenDataSources`, `hiddenPlugins`, `hiddenMenus`, `hiddenMenuItems` (§1.7) | (deployment-policy.md § interface) |
| `plugins` | `registryUrl`, `allowed`, `blocked`, `sideload` (por defecto `true`), `defaultActive`, `openPanel`, `fileAccess` (solo política de máquina) | (deployment-policy.md § plugins, § Plugin precedence) |
| `services` | `builtins` (`false` oculta los de ejemplo), `catalog[]` con `id`, `name`, `kind` (`wms`, `wfs`, `wmts`, `xyz`, `arcgis`, `csw`), `category`, `fields` | (deployment-policy.md § services) |
| `basemaps` · `geolens` · `osm` | `regional` (`false` quita Amap/Tencent/Tianditu) · `url` (https, `same-origin` u `off`) · `overpassUrl` | (deployment-policy.md § basemaps, § geolens, § osm) |
| `sharing` | `shareUrl` (URL o `off`: quita Share y Gallery), `collabUrl` (`wss://`), `embedOrigins` (orígenes exactos o `*`; `[]` apaga la API) | (deployment-policy.md § sharing) |
| `ai` · `branding` | `enabled` (por defecto `false`), `model` · `appName` (máx. 60 caracteres), `welcome` | (deployment-policy.md § ai, § branding) |
| Variables Docker | `GEOLIBRE_CAPABILITIES`, `GEOLIBRE_SERVICES_FILE`, `GEOLIBRE_BUILTIN_SERVICES`, `GEOLIBRE_DISABLE_REGIONAL_BASEMAPS`, `GEOLIBRE_SHARE_URL`, `GEOLIBRE_COLLAB_URL`, `GEOLIBRE_EMBED_ORIGINS`, `GEOLIBRE_GEOLENS_URL`, `GEOLIBRE_OVERPASS_URL`, `GEOLIBRE_APP_NAME`, `GEOLIBRE_AI_URL`/`GEOLIBRE_AI_MODEL`; además `GEOLIBRE_AUTH_USER`/`GEOLIBRE_AUTH_PASSWORD` (Basic Auth), `GEOLIBRE_DISABLE_SIDECAR`, `GEOLIBRE_CONVERSION_ROOTS`, `GEOLIBRE_APP_BASE` y `VITE_WELCOME_DISABLED` (compilación) | (deployment-policy.md § Docker; getting-started.md § Run with Docker) |
| Capacidad `project:edit` | New, Open, Import, History, Save, Duplicate, Template, Collaborate, StoryMap, Undo/Redo, Export Selection, comentarios, `loadProject`, opción `draw` | (deployment-capabilities.md § The capabilities) |
| Capacidad `data:add` | Menú Add Data, arrastrar archivos, `addLayer`, `addData` | (ídem) |
| Capacidad `processing:run` | Menú Processing completo (Whitebox, SQL, Python, IA, geocodificación, Model Builder), `openTool` | (ídem) |
| Capacidad `export:data` | Share, Export HTML, Print, Print Layout, Offline Basemap, `exportImage`, `getLayerFeatures`, `getDrawnFeatures`, evento `featuresChanged` | (ídem) |
| Capacidades `plugins:install` · `settings:manage` | Menú Plugins, menús de plugins, activar/desactivar, marketplace · diálogo Settings y Style Manager | (ídem) |
| Alcance real | Son puertas del cliente, no autorización: no frenan las herramientas del navegador; solo el nginx del contenedor Docker impone rutas `/sidecar/*` y `/ai` | (deployment-capabilities.md; self-hosting.md § Container policy enforcement) |
| API `postMessage` | Apagada salvo `sharing.embedOrigins` / `GEOLIBRE_EMBED_ORIGINS`; sobre `{ "v": 2, "type", "payload", "requestId" }` (v1 aceptada); los mensajes de la app llevan `"source": "geolibre"`; cliente tipado `@geolibre/embed` (`connect(iframe, { origin, timeoutMs, requestTimeoutMs })`, `on`, `disconnect`) | (ug/embedding.md § Talking to the map at runtime, § The typed client, § Message shape) |
| Comandos sin privilegio | `setView` (`{bbox}` o `{center, zoom, bearing, pitch, duration}`), `highlightFeature` (`{layerId, featureId o featureIds o filter, fit}`), `setLayerVisibility` (`{layerId, visible}`), `listLayers`, `setFilter` (`{layerId, expression}`), `getViewport`, `setRenderer` (`{renderer}`), `getRenderer` | (ug/embedding.md § Host to GeoLibre, § Enabling it) |
| Comandos con capacidad | `loadProject` `{url}` (`project:edit`); `addLayer` `{spec}` y `addData` `{url, styleUrl?, dataType?, fit?}` (`data:add`); `openTool` `{id, params}` (`processing:run`); `exportImage`, `getLayerFeatures` `{layerId}`, `getDrawnFeatures` (`export:data`); denegado = «Missing <capability> capability» | (ídem) |
| Eventos | `ready` `{version}`, `ack` `{requestId, ok, error, result}`, `projectLoaded` `{url, name, layerIds}`, `selectionChanged` `{layerId, featureIds}`, `rendererchange` `{renderer}`, `viewChanged` `{bbox, center, zoom, bearing, pitch}` (~4/s), `toolCompleted` `{id, name, status, engine, durationMs, outputLayerNames}`, `serverFileWritten` `{path, toolId}`, `featuresChanged` `{layerId, featureCount, removed?}` (250 ms) | (ug/embedding.md § GeoLibre to host) |
| Peticiones por defecto | `tiles.openfreemap.org` (mapa base), `plugins.geolibre.app` (`blocklist.json` y registro), `extensions.duckdb.org` (extensión Spatial al abrir un vector local), `api.github.com` (actualizaciones, solo E), `www.googletagmanager.com` (solo webs hospedadas por OpenGeos). Sin telemetría ni informes de fallos | (network-endpoints.md § Default requests) |
| Hosts de GeoLibre | `tiles.geolibre.app` (relé: planetas, Overpass, CKAN, OpenAerialMap, Source Coop, Earthdata, PMTiles, feeds), `share.`, `collab.`, `ai.`, `plugins.`, `languages.`, `assets.`, `datasets.`, `web.geolibre.app` | (network-endpoints.md § GeoLibre-operated hosts) |
| Servicios externos opcionales | Mapas base (CARTO, Esri, EOX, USGS, NASA GIBS, OSM…), Nominatim y otros geocodificadores, Valhalla (`valhalla1.openstreetmap.de`), OSRM (`router.project-osrm.org`), Open-Meteo, terreno AWS (`s3.amazonaws.com/elevation-tiles-prod`), Wikipedia, geoBoundaries, proveedores de IA, Cesium ion, Mapbox, `js.arcgis.com`, `cdn.jsdelivr.net` (PGlite, CereusDB, gdal3.js, Pyodide, ONNX), `unpkg.com`, `huggingface.co`, `corsproxy.io` (reintento de `maplibre-gl-components`), `titiler.d2s.org`, PyPI/`astral.sh` (sidecar) | (network-endpoints.md § Opt-in: core features, § Opt-in: built-in plugins) |
| Reducir salidas | `GEOLIBRE_NO_EXTERNAL_CDN=1`, `VITE_PYODIDE_INDEX_URL`, `VITE_DUCKDB_SPATIAL_EXTENSION_PATH`, `VITE_ROUTING_ENDPOINT`, estilo de mapa base propio o fondo en blanco, `sharing.shareUrl:"off"`; la CSP permite cualquier `https:` en `connect-src` e `img-src` | (network-endpoints.md § Restricting network access; self-hosting.md § Reducing outbound requests; getting-started.md § Build-time flags) |
| Formas de publicación | Web estática (`apps/geolibre-desktop/dist/`), imagen Docker `ghcr.io/opengeos/geolibre` (nginx + sidecar opcional), PWA sin conexión, escritorio Windows/macOS/Linux, Android, iOS, widget Jupyter, paquete R; puertas de acceso opcionales Clerk y Auth0 | (getting-started.md; features.md § Deployment and platform builds; network-endpoints.md) |

## 12. Disponibilidad por compilación
| Área | Solo escritorio (E) | Requiere sidecar de Python (S) | Disponible en la compilación web (W) | Fuente |
| --- | --- | --- | --- | --- |
| Proyectos y archivos | Diálogos nativos, guardar en la ruta original, recientes persistentes, proyecto de inicio, Reload from disk / Watch file, Save edits to source file, sección Files del Browser, rutas locales de proyectos QGIS/ArcGIS | — | Abrir con el selector del navegador, guardar con diálogo o descarga, proyectos por URL, historial en IndexedDB, recuperación tras cierre (no incrustado), Export as HTML, Share | (ug/interface.md § Desktop and browser; ug/projects.md; ug/layers.md) |
| Datos | Lectura local por ruta de ráster y MBTiles grandes, WMS en cualquier CRS, WFS sin CORS (HTTP nativo), PostgreSQL/PostGIS vía martin, llavero del SO, mTLS | File Geodatabase, SQL Server/Azure SQL, endpoints PostGIS/MSSQL (en Docker: `/sidecar/postgis`, `/sidecar/mssql`) | Vectores con DuckDB-WASM, ráster por URL o arrastre, todos los servicios con CORS, formatos cloud, 3D, DuckDB, Iceberg, MBTiles en memoria (<1 GB), `?data=`/`?url=`/`?stac=` | (ug/adding-data.md; data-formats.md; getting-started.md § On the web) |
| Procesamiento | Lotes sobre carpetas del disco | Raster: Reproject, Resample, Clip by mask layer, Polygonize, Contour, Interpolation, Zonal statistics, Mosaic; motor GeoPandas; Vector to Vector a cualquier formato GDAL; Whitebox con rutas nativas; AI Segmentation; SedonaDB; SLIC/Felzenszwalb de OBIA | Whitebox WASM (1 000+), vector con Turf.js o Pyodide, toda la Conversion, 8 herramientas ráster cliente, Object Detection, Segment Everything, OBIA, Model Builder, History, Network (Valhalla) | (ug/processing.md § Raster, § Conversion, § The Python sidecar; getting-started.md § Bundled conversion sidecar) |
| SQL, Python, IA | JupyterLab local, claves de IA desde variables del SO | SedonaDB sidecar (extra `sedona`) | SQL Workspace (DuckDB, PGlite/PostGIS, CereusDB), Python Console y JupyterLite con Pyodide, AI Assistant con clave propia, comandos de voz | (ug/sql-workspace.md; ug/python-console.md; ug/ai-assistant.md) |
| Sistema | Comprobación de actualizaciones, `deployment.json` de máquina y `plugins.fileAccess`, carpetas locales de plugins | Docker incluye el sidecar en `/sidecar` si la política concede `processing:run` o `data:add` | Parámetros de URL, incrustación en iframe y API `postMessage`, PWA y Offline Basemap, NMEA por Web Serial/Bluetooth (Chromium) | (deployment-policy.md § Desktop; ug/embedding.md § What works in an embed; features.md § Deployment) |
| Excepciones (Mac App Store, Android, iOS) | Mac App Store pierde: motores del sidecar, PostgreSQL vía martin, Jupyter local, inicio de sesión de Earth Engine e instalación de plugins externos | Android/iOS ocultan lo que depende de un proceso local: Raster, Conversion por sidecar, AI Segmentation y PostgreSQL/Martin (PostGIS se sirve en proceso con `ST_AsMVT`) | La caja Whitebox WASM sigue disponible en web, escritorio, Android e iOS | (features.md § Deployment and platform builds; getting-started.md § On the desktop) |
