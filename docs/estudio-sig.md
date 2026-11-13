# Estudio SIG: GeoLibre integrado en el geoportal

El **Estudio SIG** es [GeoLibre](https://github.com/opengeos/GeoLibre) (SIG libre, licencia MIT)
servido por el propio geoportal, en la carpeta `geolibre/` de la instalación y en el **mismo
origen** (dominio, subdominio, subdirectorio o subcarpeta). Se abre desde el menú **Estudio SIG**
con todas las capas publicadas ya cargadas, organizadas por categoría, y ofrece **toda la
interfaz y las herramientas de la versión web de GeoLibre**: edición, estilos, etiquetas, tabla
de atributos, expresiones, SQL, geoprocesamiento (Whitebox y la caja de herramientas de GeoLibre),
vista 3D y globo (Cesium), impresión de mapas, mapas narrativos, complementos, exportación y
guardado de proyectos `.geolibre`.

No es una copia ni una modificación: se instala la **compilación web oficial** que GeoLibre
publica en su paquete de Python (PyPI), con la suma SHA-256 verificada, y se configura solo con
sus mecanismos oficiales:

| Archivo | Qué es | Lo genera |
| --- | --- | --- |
| `geolibre/deployment.json` | [Política de despliegue](https://github.com/opengeos/GeoLibre/blob/main/docs/deployment-policy.md): marca, nivel de interfaz, menús, permisos, complementos, servicios, compartir | Administrador → Estudio SIG |
| `geolibre/geoportal-ajustes.json` | Archivo de interfaz para `?settingsUrl=`: idioma y color de acento | Administrador → Estudio SIG |
| `api/geolibre-version.json` | Versión fijada de GeoLibre: URL del paquete en PyPI, SHA-256 y tamaño | Repositorio |

Así se sigue la recomendación de GeoLibre para despliegues propios: la aplicación y los datos en
el mismo origen, sin CORS que configurar y sin que los datos salgan de la infraestructura de la
Gobernación.

## Instalación

Hay cuatro formas, según el servidor:

1. **Desde el administrador (recomendada en Plesk).** *Administrador → Estudio SIG → Instalar
   GeoLibre*. El servidor descarga el paquete oficial (≈56 MB), verifica su SHA-256, extrae solo
   la aplicación web (≈200 MB, 1 038 archivos) y la deja en `geolibre/`. Requiere la extensión
   `zip` de PHP, salida HTTPS hacia `files.pythonhosted.org` y permiso de escritura en la carpeta
   del geoportal. En el Plesk de prueba tardó 12 s. Si el servidor no lo permite, el
   administrador lo indica y ofrece las alternativas.
2. **Paquete «con GeoLibre».** `geoportal-plesk-<versión>-con-geolibre.zip` (en *Releases* o con
   `scripts/empaquetar-plesk.sh --con-geolibre`) trae la carpeta `geolibre/` incluida: se sube y
   se extrae igual que el paquete normal.
3. **Script.** `scripts/descargar-geolibre.sh [carpeta]` descarga, verifica e instala en
   `portal/geolibre/` (o en la carpeta indicada). No ejecuta código del paquete.
4. **Docker.** El volumen `geolibre` se monta en la API (`/geolibre`, escritura) y en nginx
   (`/srv/geolibre`, lectura, publicado en `/geolibre/`). Se instala desde el administrador.

Para **actualizar GeoLibre** se cambia `portal/api/geolibre-version.json` (versión, URL del
paquete `.whl` de PyPI, `sha256` y `tamano_bytes`) y se pulsa *Actualizar* en el administrador.
Los ajustes se conservan.

## Configuración (Administrador → Estudio SIG)

Solo los administradores ven esta sección. Cada cambio se guarda en la base de datos y se escribe
en `deployment.json` y `geoportal-ajustes.json`; se aplica la próxima vez que se abre el Estudio.
La pestaña **deployment.json** muestra la política generada.

| Pestaña | Ajuste | Campo de GeoLibre |
| --- | --- | --- |
| ¿Qué GeoLibre se usa? | Estudio integrado o instancia externa (URL) | — (el geoportal decide qué enlace abre) |
| Apariencia e idioma | Nombre de la aplicación | `branding.appName` |
| | Pantalla de bienvenida | `branding.welcome` |
| | Modo completo o visor (solo consulta) | parámetro `layout=viewer` |
| | Idioma (21 idiomas de GeoLibre) | `language` de `?settingsUrl=` |
| | Color de acento (azul, violeta, esmeralda, rosa, ámbar o personalizado, por defecto el verde institucional `#10A13B`) | `theme.scheme` / `theme.customColor` |
| Interfaz y menús | Preajustes de presentación: Esencial, Estándar (por defecto), Completo y Solo consulta | Rellenan los campos siguientes |
| | Empezar con los paneles plegados | parámetro `panels=collapsed` |
| | Barra con iconos o con texto, nombre del proyecto, lista de capas compacta, paneles Estilo, Explorador y Comentarios | `layout` de `?settingsUrl=` (`toolbarLabels`, `showProjectInfo`, `compactLayerList`, `stylePanelVisible`, `browserPanelVisible`, `commentsPanelVisible`) |
| | Nivel inicial, intermedio (por defecto) o avanzado; bloquearlo | `interface.level` / `interface.lock` |
| | Menús ocultos (Proyecto, Editar, Ver, Añadir datos, Procesamiento, Controles, Complementos, Ayuda) | `interface.hiddenMenus` |
| | Elementos de menú y fuentes de datos ocultos | `interface.hiddenMenuItems` / `interface.hiddenDataSources` |
| Permisos | Editar proyectos, añadir datos, geoprocesamiento, exportar, instalar complementos, preferencias | `capabilities` |
| Complementos | Permitir instalar desde archivo o URL | `plugins.sideload` |
| | Registro de complementos propio | `plugins.registryUrl` |
| | Lista de complementos externos permitidos (vacía = ninguno) | `plugins.allowed` |
| | Activos por defecto, bloqueados, ocultos, panel que abre al iniciar | `plugins.defaultActive` / `blocked` / `interface.hiddenPlugins` / `plugins.openPanel` |
| Servicios y mapas base | Servicios predeterminados de GeoLibre | `services.builtins` |
| | Catálogo institucional: WMS, WFS, WMTS, XYZ, ArcGIS, CSW (p. ej. IDEAM, IGAC, SIAC) | `services.catalog` |
| | Mapas base regionales servidos desde China continental | `basemaps.regional` |
| Compartir y conexiones | Compartir y Galería en el servicio público (desactivado por defecto) | `sharing.shareUrl` (`off` o `https://share.geolibre.app`) |
| | Servidor propio de proyectos | `sharing.shareUrl` |
| | Relé de colaboración en tiempo real (`wss://`) | `sharing.collabUrl` |
| | Servidor Overpass (descargas de OpenStreetMap) | `osm.overpassUrl` |
| | GeoLens (`off`, `same-origin` o URL) | `geolens.url` |

El geoportal fija además `sharing.embedOrigins` con su propio origen (para controlar el Estudio
desde el visor) y `ai.enabled: false` (no hay ruta propia de asistente de IA en el servidor).

Las capacidades de GeoLibre **limitan la interfaz y los comandos de incrustación**, no son un
control de acceso: los datos que el Estudio muestra son los mismos que publica la API pública.
Lo que no deba ser público no se publica en el geoportal.

## Integración con el visor

- **Menú «Estudio SIG»**: abre GeoLibre dentro del geoportal, en la vista y con el mapa base del
  visor, el tema claro u oscuro del portal, el idioma y el acento configurados.
- **«Ver en Estudio SIG»** (ficha de una capa): enciende la capa en el Estudio y la encuadra.
- **«Traer vista del visor»**: lleva al Estudio la vista y las capas encendidas en el visor.
- **Nueva ventana**: abre el mismo Estudio a pantalla completa.
- La comunicación usa la [API de incrustación v2 de GeoLibre](https://github.com/opengeos/GeoLibre/blob/main/docs/user-guide/embedding.md#talking-to-the-map-at-runtime)
  (`setView`, `setLayerVisibility`, `listLayers`, `getViewport`…), limitada al origen del portal.
  Los identificadores de capa son estables (UUID v5 del slug, campo `geolibre_id` de `/api/capas`).
- El proyecto acepta `?base=calles|claro|oscuro|fiord|brillante` para abrir con ese mapa base.
- Un ráster cuyo GeoTIFF publicado no se puede transmitir por rangos (no teselado o fuera de
  EPSG:4326/3857, por ejemplo uno demasiado grande para convertirlo en el navegador) entra al
  proyecto como **imagen georreferenciada** con su vista previa, en lugar de una capa que GeoLibre
  no podría abrir.

Si el Estudio no está instalado, o el administrador elige una instancia externa, el geoportal
muestra el botón «Abrir en GeoLibre» hacia esa instancia (por defecto `https://web.geolibre.app`)
y la API responde con CORS solo para su origen.

## Funciones del visor del geoportal

Además del Estudio, el visor propio incorpora las funciones de uso frecuente de GeoLibre con una
interfaz mínima: una tarjeta (búsqueda y capas), tres controles de navegación y un botón de
herramientas. El diseño está en el [plan de interfaz minimalista](plan-interfaz-minimalista.md).

| Función | Cómo |
| --- | --- |
| Modo oscuro | Botón de tema en la barra superior: automático (sigue al sistema), claro u oscuro. Se aplica al visor, catálogo, administrador, asistente de instalación, mapa base y Estudio SIG. |
| Búsqueda y paleta de comandos | Una sola caja (`Ctrl` + `K`): acciones, capas por nombre (las enciende o apaga), mapas base, coordenadas decimales o sexagesimales, entidades de las capas encendidas y lugares de OpenStreetMap (Photon, con Nominatim de respaldo) priorizando Nariño. |
| Capas | Una línea por capa; «⋯» abre opacidad, acercar, ficha, tabla, Estudio SIG y orden. Categorías plegables. |
| Herramientas | Un botón (`H`) con mapas base, medir, terreno 3D, mi ubicación, añadir datos, copiar enlace, insertar, imagen, imprimir, pantalla completa, solo el mapa y atajos. |
| Añadir datos | GeoJSON, Shapefile (.zip), GeoPackage, KML/KMZ, GPX, CSV y GeoTIFF desde el equipo, o GeoJSON, WMS y XYZ por dirección; también arrastrando el archivo al mapa. Se leen en el navegador: no se suben ni se publican, y no viajan en los enlaces. |
| Coordenadas | Píldora con clic para cambiar el formato: grados decimales, GMS, grados y minutos, UTM y MAGNA-SIRGAS Origen Nacional (EPSG:9377); zoom, escala, rumbo e inclinación. |
| Medición | Distancia y área geodésicas (`M`, `A`; doble clic o `Enter` termina, `Esc` cancela). |
| Terreno 3D | Relieve con sombreado (`T`); arrastre con clic derecho para inclinar y girar. |
| Tabla de atributos | Filtro, orden por columna, páginas de 100 filas, clic para ubicar y resaltar, exportación a CSV y «Filtrar también el mapa». |
| Enlace permanente | La dirección guarda vista, capas, mapa base y terreno; «Copiar enlace de esta vista». |
| Insertar el mapa | Código `<iframe>` de la vista actual, con ancho, alto y «solo el mapa». |
| Imprimir e imagen | Hoja A4 horizontal con encabezado institucional, norte, escala gráfica, leyenda y fuente (`P`); descarga PNG con título, capas y fecha. |
| Solo el mapa | `F` oculta la interfaz; `?maponly=1` en la dirección la abre así para incrustarla. |
| Parámetros de la dirección | Los de GeoLibre: `maponly`, `panels=collapsed`, `theme=dark\|light`, `lat`, `lon`, `zoom`; y sus equivalentes `solomapa`, `paneles=plegados`, `tema=oscuro\|claro`. Además `capas=`, `mapa=`, `base=` y `3d=1`. |
| Atajos de teclado | `N` norte, `U` sin inclinación, `R` vista de Nariño, `L` lista de capas, `H` herramientas, `F` solo el mapa, `P` imprimir, `?` ayuda. |

## Qué no incluye y por qué

| Función de GeoLibre | Situación en el geoportal |
| --- | --- |
| *Sidecar* de Python (Whitebox, conversiones y ML del lado del servidor, conexiones PostGIS y SQL Server) | La versión web ejecuta Whitebox y el resto del análisis en el navegador (WebAssembly y Pyodide). El *sidecar* solo existe en la imagen Docker de GeoLibre: en la edición Docker puede levantarse con `docker compose --profile geolibre-separado up -d` y `GEOLIBRE_DISABLE_SIDECAR=0`. |
| Asistente de IA | La ruta de IA del servidor no se ofrece (`ai.enabled: false`) porque requiere claves de proveedores. Cada usuario puede configurar su propia clave en *Configuración* de GeoLibre (queda en su navegador); para impedirlo, oculte el complemento o el menú correspondiente. |
| Funciones de escritorio | Diálogos de archivos locales, lectura de MBTiles y rásteres locales y guardado directo en disco son de la aplicación de escritorio. En la web se guardan y abren proyectos `.geolibre` descargándolos. |
| `plugins.fileAccess` | Solo se respeta desde un archivo de política del sistema en la aplicación de escritorio. |
| Compartir en línea | Desactivado por defecto para no publicar proyectos fuera de la infraestructura de la Gobernación; se activa en *Compartir y conexiones* o con un servidor propio. |

GeoLibre contacta algunos servicios públicos cuando se usan sus funciones (mapas base de
OpenFreeMap, geocodificación, rutas, Pyodide desde jsDelivr). La lista completa y cómo
reemplazarlos por servicios internos está en
[network-endpoints](https://github.com/opengeos/GeoLibre/blob/main/docs/network-endpoints.md).
GeoLibre no recoge analítica.

## Problemas frecuentes

| Síntoma | Causa y solución |
| --- | --- |
| No aparece «Estudio SIG» en el menú | GeoLibre no está instalado o se eligió una instancia externa: *Administrador → Estudio SIG*. |
| «Este servidor no puede instalar GeoLibre automáticamente» | Falta la extensión `zip`, la salida HTTPS o el permiso de escritura: use el paquete «con GeoLibre» o suba la carpeta `geolibre/` por FTP o el Administrador de archivos. |
| El Estudio abre pero «Traer vista del visor» no hace nada | El origen del portal cambió (otro dominio o `http`/`https`): guarde de nuevo los ajustes del Estudio para regenerar `embedOrigins`, o fije la URL pública en *Configuración*. |
| Un ráster aparece como imagen en el Estudio | Su GeoTIFF no está teselado o está en otro sistema de referencia: súbalo como COG en EPSG:4326 o 3857 para analizar sus valores. |
| Cambios del administrador que no se ven | El Estudio lee la política al abrir: use «Recargar». |

## Verificación realizada

En el Plesk simulado (nginx → Apache → PHP-FPM con `open_basedir`, MySQL 8):

- instalación de GeoLibre 3.7.0 con el botón del administrador en `/geoportal/` (12 s, 1 038
  archivos) y mensaje de instalación manual en un subdominio con raíz no escribible;
- Estudio SIG en subcarpeta anidada (`/secretarias/ambiente/geoportal/`), en español, con el
  acento institucional, modo oscuro, mapa base oscuro y menú «Ayuda» oculto desde el
  administrador;
- API de incrustación: `listLayers`, `getViewport`, `setLayerVisibility` y `setView` desde el
  visor; diagnóstico de GeoLibre sin errores;
- pruebas automáticas de ambas ediciones (`api/tests/test_estudio.py` y
  `pruebas/edicion_php/test_edicion_php.py::test_estudio_sig`).
