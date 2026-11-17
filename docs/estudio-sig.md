# GeoLibre: el mapa del geoportal

El mapa del Geoportal Ambiental es [GeoLibre](https://github.com/opengeos/GeoLibre) (SIG libre,
licencia MIT), con **la misma interfaz y las mismas funciones que [web.geolibre.app](https://web.geolibre.app/)**
y con todas las capas publicadas ya cargadas, organizadas por categoría. La portada lo muestra a
toda la vista, bajo la barra GOV.CO y el encabezado de la Gobernación:

- barra de menús **Proyecto, Editar, Ver, Añadir datos, Procesamiento, Controles, Complementos,
  Configuración y Ayuda**, con el nombre del proyecto;
- panel **Capas** con las carpetas por categoría, opacidad, orden, estilo, tabla de atributos y
  ficha de cada capa; rieles **Explorador**, **Estilo** y **Comentarios**;
- búsqueda de lugares, coordenadas o celdas H3; mapas base; 2D, 3D y globo (Cesium); barra de
  estado con coordenadas, zoom, altura de cámara, rumbo, inclinación, extensión y diagnóstico;
- edición, etiquetas, expresiones, SQL, más de mil herramientas de geoprocesamiento (Whitebox y la
  caja de herramientas de GeoLibre), más de cuarenta fuentes de datos, 72 complementos, impresión
  de mapas, mapas narrativos, exportación y proyectos `.geolibre`;
- **Compartir** y **Abrir desde la galería** con el servicio de compartir del propio geoportal.

El inventario completo, comprobado en web.geolibre.app con REA, está en el
[anexo de inventario](anexo-inventario-geolibre.md).

No es una copia ni una modificación: se instala la **compilación web oficial** que GeoLibre
publica en su paquete de Python (PyPI), con la suma SHA-256 verificada, en la carpeta `geolibre/`
de la instalación y en el **mismo origen** del geoportal (dominio, subdominio o subcarpeta). Se
configura solo con sus mecanismos oficiales:

| Archivo | Qué es | Lo genera |
| --- | --- | --- |
| `geolibre/deployment.json` | [Política de despliegue](https://github.com/opengeos/GeoLibre/blob/main/docs/deployment-policy.md): marca, nivel de interfaz, menús, permisos, complementos, servicios, compartir | Administrador → Mapa (GeoLibre) |
| `geolibre/geoportal-ajustes.json` | Archivo de interfaz para `?settingsUrl=`: idioma, color de acento y disposición | Administrador → Mapa (GeoLibre) |
| `api/geolibre-version.json` | Versión fijada de GeoLibre (hoy **3.9.0**): URL del paquete en PyPI, SHA-256 y tamaño | Repositorio |

Así se sigue la recomendación de GeoLibre para despliegues propios: la aplicación, los datos y el
servicio de compartir en el mismo origen, sin CORS que configurar y sin que los datos salgan de la
infraestructura de la Gobernación.

## La portada

| Elemento | Qué hace |
| --- | --- |
| **Mapa** | GeoLibre a toda la vista, con el proyecto `api/proyecto.geolibre` (todas las capas publicadas; encendidas las marcadas «Encendida al abrir»). Idioma, acento y tema del portal. Se carga la primera vez que se muestra. |
| **Catálogo** | Una tarjeta por geodato, con búsqueda y filtros. «Ver en el mapa» vuelve al mapa, enciende la capa y la encuadra con la API de incrustación de GeoLibre; «Ficha» abre los metadatos, las descargas (GeoJSON o COG, archivo original y proyecto `.geolibre`) y la URL del servicio de datos. |
| **Acerca del geoportal** | Qué se puede hacer, sistema de referencia, servicios para desarrolladores y condiciones de uso. |
| **Insertar** | Código `<iframe>` con la vista y las capas actuales, para mostrar el mapa en otra página institucional. |
| **Nueva ventana** | Abre GeoLibre solo, a pantalla completa, con el mismo proyecto y la misma vista. |
| **Tema** | El botón de la barra GOV.CO cambia el tema del portal; GeoLibre lo toma al recargarse (el aviso ofrece «Recargar ahora») o con su propio botón de tema, sin recargar. |

Parámetros de la dirección del geoportal (los nombres de GeoLibre y sus equivalentes en español):

| Parámetro | Efecto |
| --- | --- |
| `?capa=slug` | Abre el mapa con esa capa encendida, la encuadra y muestra su ficha |
| `?capas=a,b` | Capas encendidas al abrir (las demás quedan en el panel, apagadas) |
| `?base=calles\|claro\|oscuro\|fiord\|brillante` | Mapa base del proyecto |
| `?lat=&lon=&zoom=` (o el antiguo `?mapa=lat,lon,zoom`) | Vista inicial |
| `?maponly=1` (o `?solomapa=1`) | Solo el mapa, en el modo de consulta de GeoLibre, con el enlace «Ver en el geoportal»: es lo que usa el código de «Insertar» |
| `?panels=collapsed` (o `?paneles=plegados`) | Paneles de GeoLibre plegados al abrir |
| `?theme=dark\|light` (o `?tema=oscuro\|claro`) | Tema para esa visita |
| `?compartido=usuario/proyecto` | Abre un proyecto publicado con «Compartir» en este geoportal |

Los enlaces del visor anterior (`#visor`, `#estudio`) llevan al mapa.

## Instalación

Hay cuatro formas, según el servidor:

1. **Desde el administrador (recomendada en Plesk).** *Administrador → Mapa (GeoLibre) → Instalar
   GeoLibre*. El servidor descarga el paquete oficial (≈57 MB), verifica su SHA-256, extrae solo
   la aplicación web (≈212 MB, 1 060 archivos) y la deja en `geolibre/`. Requiere la extensión
   `zip` de PHP, salida HTTPS hacia `files.pythonhosted.org` y permiso de escritura en la carpeta
   del geoportal. Si el proxy de Plesk corta la espera (60 s), la instalación continúa en el
   servidor y el administrador comprueba cuándo terminó. Si el servidor no lo permite, el
   administrador lo indica y ofrece las alternativas.
2. **Paquete «con GeoLibre».** `geoportal-plesk-<versión>-con-geolibre.zip` (en *Releases* o con
   `scripts/empaquetar-plesk.sh --con-geolibre`) trae la carpeta `geolibre/` incluida.
3. **Script.** `scripts/descargar-geolibre.sh [carpeta]` descarga, verifica e instala en
   `portal/geolibre/` (o en la carpeta indicada). No ejecuta código del paquete.
4. **Docker.** El volumen `geolibre` se monta en la API (`/geolibre`, escritura) y en nginx
   (`/srv/geolibre`, lectura, publicado en `/geolibre/`). Se instala desde el administrador.

Mientras GeoLibre no esté instalado, la portada usa la instancia externa configurada (por defecto
`https://web.geolibre.app`) con el proyecto del geoportal; la API responde con CORS solo para ese
origen. Sin instancia externa, la portada explica que el mapa no está instalado y ofrece el catálogo.

Para **actualizar GeoLibre** se cambia `portal/api/geolibre-version.json` (versión, URL del
paquete `.whl` de PyPI, `sha256` y `tamano_bytes`) y se pulsa *Actualizar* en el administrador.
Los ajustes se conservan y los archivos de configuración se regeneran.

## Configuración (Administrador → Mapa (GeoLibre))

Solo los administradores ven esta sección. Cada cambio se guarda en la base de datos y se escribe
en `deployment.json` y `geoportal-ajustes.json`; se aplica la próxima vez que se abre el mapa.
La pestaña **deployment.json** muestra la política generada. Por defecto, el mapa se ve y funciona
como web.geolibre.app, en español y con el verde institucional.

| Pestaña | Ajuste | Campo de GeoLibre |
| --- | --- | --- |
| ¿Qué GeoLibre se usa? | Integrado o instancia externa (URL) | — (el geoportal decide qué enlace abre) |
| Apariencia e idioma | Nombre de la aplicación | `branding.appName` |
| | Pantalla de bienvenida | `branding.welcome` |
| | Modo completo o visor (solo consulta) | parámetro `layout=viewer` |
| | Idioma (24 idiomas de GeoLibre) | `language` de `?settingsUrl=` |
| | Color de acento (por defecto el verde institucional `#10A13B`) | `theme.scheme` / `theme.customColor` |
| | **Apariencia institucional** (por defecto activa) | Envía `?settingsUrl=`. Mientras se usa, GeoLibre no guarda los ajustes que cambie cada visitante (claves, tokens, preferencias); desactívela si los usuarios necesitan conservarlos |
| Interfaz y menús | Preajustes: **Completo** (por defecto, como web.geolibre.app), Estándar, Esencial y Solo consulta | Rellenan los campos siguientes |
| | Empezar con los paneles plegados | parámetro `panels=collapsed` |
| | Menús con texto o solo iconos, nombre del proyecto, lista de capas compacta, paneles Estilo, Explorador y Comentarios, paneles inferiores bajo el mapa | `layout` de `?settingsUrl=` (`toolbarLabels`, `showProjectInfo`, `compactLayerList`, `stylePanelVisible`, `browserPanelVisible`, `commentsPanelVisible`, `bottomPanelsUnderMap`) |
| | Nivel inicial, intermedio o avanzado (por defecto); bloquearlo | `interface.level` / `interface.lock` |
| | Menús, elementos de menú y fuentes de datos ocultos | `interface.hiddenMenus` / `hiddenMenuItems` / `hiddenDataSources` |
| Permisos | Editar proyectos, añadir datos, geoprocesamiento, exportar, instalar complementos, preferencias | `capabilities` |
| Complementos | Instalar desde archivo o URL, registro propio, lista de permitidos, activos, bloqueados, ocultos y panel inicial | `plugins.*`, `interface.hiddenPlugins` |
| Servicios y mapas base | Servicios predeterminados de GeoLibre y catálogo institucional (WMS, WFS, WMTS, XYZ, ArcGIS, CSW); mapas base regionales | `services.builtins`, `services.catalog`, `basemaps.regional` |
| Compartir y conexiones | **Compartir y galería con el servicio del geoportal** (por defecto) | `sharing.shareUrl` = `<URL pública>/api/compartir` |
| | Otro servidor de proyectos (opcional, tiene prioridad) | `sharing.shareUrl` |
| | Relé de colaboración en tiempo real (`wss://`) | `sharing.collabUrl` |
| | Servidor Overpass (descargas de OpenStreetMap) | `osm.overpassUrl` |
| | GeoLens (`off`, `same-origin` o URL) | `geolens.url` |

El geoportal fija además `sharing.embedOrigins` con su propio origen (para controlar el mapa desde
el catálogo) y `ai.enabled: false`.

Los ajustes guardados antes de que GeoLibre fuera la interfaz principal (presentación compacta)
se leen con la disposición completa; el resto (servicios, complementos, permisos) se conserva.

Las capacidades de GeoLibre **limitan la interfaz y los comandos de incrustación**, no son un
control de acceso: los datos que el mapa muestra son los mismos que publica la API pública. Lo que
no deba ser público no se publica en el geoportal.

## Compartir y galería

GeoLibre publica proyectos con un servicio HTTP (contrato v1). El servicio público
`share.geolibre.app` solo acepta peticiones de los dominios de GeoLibre, así que el geoportal
**aloja su propio servicio** en `api/compartir`, en las dos ediciones y en la base de datos del
geoportal:

- **Ver** los proyectos públicos en *Proyecto → Abrir desde la galería* no requiere cuenta.
- **Publicar** requiere un token personal: cada usuario del administrador (administrador o editor)
  lo crea en *Mi cuenta → Tokens para compartir desde GeoLibre* y lo pega en GeoLibre
  (*Configuración → Variables de entorno → shareToken*). Con la apariencia institucional activa,
  GeoLibre no guarda ese ajuste entre visitas: use **Nueva ventana** o desactive la opción si los
  usuarios publican con frecuencia.
- El enlace de un proyecto compartido es `<geoportal>/?compartido=usuario/proyecto`.

El detalle del contrato implementado está en [arquitectura](arquitectura.md#servicio-de-compartir).

## Qué no incluye y por qué

| Función de GeoLibre | Situación en el geoportal |
| --- | --- |
| Colaboración en tiempo real | Necesita un relé WebSocket propio: el público solo admite los dominios de GeoLibre. PHP en Plesk no mantiene WebSockets; en la edición Docker puede desplegarse el relé oficial (`workers/collab-node` de GeoLibre, Node + SQLite) detrás de nginx e indicarse su `wss://` en *Compartir y conexiones*. |
| Asistente de IA | `ai.enabled: false`: un proxy de IA requiere claves y costos de un proveedor. Cada usuario puede usar su propia clave en *Configuración* de GeoLibre (con la apariencia institucional activa no se guarda entre visitas). |
| *Sidecar* de Python (Whitebox del lado del servidor, PostGIS, SQL Server) | La versión web ejecuta Whitebox y el resto del análisis en el navegador (WebAssembly y Pyodide). El *sidecar* solo existe en la imagen Docker de GeoLibre y debe servirse en la raíz del dominio: en la edición Docker, `docker compose --profile geolibre-separado up -d` con `GEOLIBRE_DISABLE_SIDECAR=0`. |
| GeoLens | Es otro producto (FastAPI + PostGIS); se puede conectar uno existente en *Compartir y conexiones*. |
| Funciones de escritorio | Diálogos de archivos locales, MBTiles y rásteres locales y guardado directo en disco son de la aplicación de escritorio. En la web los proyectos `.geolibre` se descargan y se abren. |
| Claves de servicios de web.geolibre.app | Protomaps, Mapillary y el inicio de sesión de ArcGIS usan claves propias de web.geolibre.app que no vienen en el paquete oficial; cada usuario puede indicar las suyas en *Configuración*. |

GeoLibre contacta algunos servicios públicos cuando se usan sus funciones (mapas base de
OpenFreeMap, geocodificación, rutas, Overpass, Pyodide desde jsDelivr). La lista completa y cómo
reemplazarlos por servicios internos está en
[network-endpoints](https://github.com/opengeos/GeoLibre/blob/main/docs/network-endpoints.md).
GeoLibre no recoge analítica.

## Problemas frecuentes

| Síntoma | Causa y solución |
| --- | --- |
| La portada dice «El mapa interactivo no está instalado» | GeoLibre no está instalado y no hay instancia externa: *Administrador → Mapa (GeoLibre)*. |
| «Este servidor no puede instalar GeoLibre automáticamente» | Falta la extensión `zip`, la salida HTTPS o el permiso de escritura: use el paquete «con GeoLibre» o suba la carpeta `geolibre/` por FTP o el Administrador de archivos. |
| «Ver en el mapa» no enciende la capa | El origen del portal cambió (otro dominio o `http`/`https`): guarde de nuevo los ajustes del mapa para regenerar `embedOrigins`, o fije la URL pública en *Configuración*. |
| Compartir dice que falta el token | Cree uno en *Mi cuenta* del administrador y péguelo en *Configuración → Variables de entorno → shareToken* de GeoLibre. |
| Un ráster aparece como imagen | Su GeoTIFF no está teselado o está en otro sistema de referencia: súbalo como COG en EPSG:4326 o 3857 para analizar sus valores. |
| Cambios del administrador que no se ven | GeoLibre lee la política al abrir: recargue la página. |

## Verificación realizada

En el Plesk simulado (nginx → Apache → PHP-FPM con `open_basedir`, MySQL 8):

- instalación de GeoLibre 3.9.0 con la API del administrador en `/geoportal/` y en
  `/secretarias/ambiente/geoportal/` (1 060 archivos; la primera vez el proxy cortó a los 60 s y
  la instalación terminó en el servidor);
- portada con la interfaz completa: los nueve menús con texto, panel Capas con las categorías,
  barra de estado en español, versión 3.9.0, API de incrustación (`listLayers`,
  `setLayerVisibility`, `setView`), parámetros de la dirección, solo el mapa, insertar, tema y
  sitio sin GeoLibre o sin instalar, en 360, 390 (táctil), 768, 1024, 1440 y 1857 px de ancho,
  en claro y oscuro;
- pruebas automáticas de ambas ediciones (`api/tests/test_estudio.py`,
  `pruebas/edicion_php/test_edicion_php.py::test_estudio_sig` y las del servicio de compartir).
