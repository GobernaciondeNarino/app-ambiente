# Manual del administrador de geodatos

Geoportal Ambiental · Secretaría de Ambiente y Desarrollo Sostenible · Gobernación de Nariño

Este manual explica cómo cargar, documentar, simbolizar y publicar información
geográfica en el geoportal.

## 1. Ingreso y roles

Ingrese en `https://<dominio-del-geoportal>/admin/` con su usuario y contraseña.
La sesión dura 8 horas (configurable) y se cierra al cerrar la pestaña.

Tras 5 intentos fallidos con un mismo usuario desde un mismo equipo (o 20 desde un mismo equipo
con cualquier usuario) en 15 minutos, el ingreso se bloquea para ese equipo hasta que pasen esos
15 minutos; desde otro equipo se puede seguir entrando. Los intentos fallidos y bloqueados quedan
en la bitácora con la dirección IP.

| Acción | Editor | Administrador |
| --- | :---: | :---: |
| Cargar geodatos y reemplazar archivos | ✔ | ✔ |
| Editar metadatos y simbología | ✔ | ✔ |
| Publicar o retirar capas | | ✔ |
| Eliminar capas | | ✔ |
| Crear y editar categorías | | ✔ |
| Gestionar usuarios | | ✔ |
| Consultar la bitácora | | ✔ |

El primer administrador se crea al iniciar el sistema con las variables
`GEOPORTAL_ADMIN_USER` y `GEOPORTAL_ADMIN_PASSWORD`. Cámbiele la contraseña en
**Mi cuenta** después del primer ingreso.

## 2. Flujo de publicación

1. **Cargar** el geodato (sección *Cargar geodato*).
2. **Documentar** la ficha de metadatos.
3. **Simbolizar** colores, grosores y ventana emergente.
4. **Revisar** la vista previa y la pestaña *Datos*.
5. **Publicar** (administrador). Desde ese momento la capa aparece en el mapa,
   en el catálogo, en la API y en el proyecto de GeoLibre.

Toda capa nueva queda como **borrador**: no es visible al público hasta que un
administrador la publique.

## 3. Preparar los archivos

| Formato | Cómo cargarlo |
| --- | --- |
| **Shapefile** | Comprima en un `.zip` **un solo** Shapefile con todos sus archivos: `.shp`, `.shx`, `.dbf` y `.prj` (y `.cpg` si existe, para las tildes). |
| **GeoPackage** (`.gpkg`) | Directo. Si tiene varias capas, escriba el nombre de la deseada en *Opciones avanzadas → Capa interna* (por defecto se toma la primera). |
| **GeoJSON** | Directo. Se respeta el miembro `crs` (p. ej. archivos exportados de ArcGIS en MAGNA-SIRGAS). |
| **KML / KMZ** | Directo. |
| **CSV** | Columnas de coordenadas con nombres como `latitud`/`longitud`, `lat`/`lon`, `y`/`x`, o una columna `wkt`. Acepta separador `,` o `;` y decimales con coma. Si las coordenadas están en metros, indique el EPSG de origen. |
| **GML, FlatGeobuf, GeoParquet** | Directo. |
| **Ráster** (GeoTIFF, IMG, ASC, JP2) | Directo. Se convierte a COG y se genera una vista previa. Para rásteres muy grandes, prefiera GeoTIFF comprimido. |

Tamaño máximo por archivo: 500 MB (variable `GEOPORTAL_MAX_UPLOAD_MB`).

### Sistema de referencia

El sistema lo detecta automáticamente y **reproyecta a WGS 84 (EPSG:4326)** para
la publicación web. En la ficha queda registrado el sistema original.

Solo si el archivo no lo declara (Shapefile sin `.prj`, CSV en metros, ráster sin
georreferencia completa) elija el sistema en *Opciones avanzadas → Sistema de
referencia de origen*. Los más usados en Nariño:

| EPSG | Nombre |
| --- | --- |
| 9377 | MAGNA-SIRGAS / Origen Nacional (CTM12) — oficial desde 2020 (Res. IGAC 471/2020) |
| 3116 | MAGNA-SIRGAS / Colombia Bogotá |
| 3115 | MAGNA-SIRGAS / Colombia Oeste |
| 4686 | MAGNA-SIRGAS geográficas |
| 4326 | WGS 84 geográficas (GPS) |

### Validaciones automáticas

- Se descartan entidades sin geometría y se **reparan geometrías inválidas**; el
  sistema informa cuántas.
- Se verifica que la extensión reproyectada caiga en coordenadas válidas (si no,
  probablemente el EPSG de origen es incorrecto).
- Se rechazan ZIP con rutas peligrosas o que superen 4 GB descomprimidos.

## 4. Ficha de metadatos

Basada en el perfil básico de metadatos geográficos (ISO 19115 / NTC 4611):

| Campo | Recomendación |
| --- | --- |
| **Título** (obligatorio) | Claro y específico: «Red de drenaje doble — escala 1:100.000». |
| Categoría temática | Define la carpeta de la capa en el mapa (GeoLibre). |
| Palabras clave | Separadas por comas; mejoran la búsqueda. |
| Descripción | Qué representa, para qué sirve, limitaciones de uso. |
| Fuente / entidad productora | IGAC, IDEAM, Corponariño, Gobernación de Nariño… |
| Autor / correo de contacto | Responsable técnico del dato. |
| Fecha de la información | Fecha de producción o corte (`AAAA`, `AAAA-MM` o `AAAA-MM-DD`). |
| Escala | `1:25.000`, `1:100.000`… |
| Frecuencia de actualización | Única vez, anual, según necesidad… |
| Licencia | Por defecto CC BY 4.0 (datos abiertos con atribución). |
| Linaje | Insumos, métodos y procesos aplicados. |
| Permitir descarga pública | Desmárquelo para mostrar la capa sin permitir su descarga. |
| Encendida al abrir el mapa | La capa aparece encendida al cargar el geoportal. |

## 5. Simbología y ventana emergente

En la pestaña **Simbología** los cambios se ven en vivo en el mapa de vista previa:

- **Polígonos:** color de relleno, color y grosor del borde, opacidad del relleno.
- **Líneas:** color y grosor.
- **Puntos:** color, borde y radio.
- **Ráster:** rampa de color (terreno, vegetación, NDVI, agua, viridis, calor,
  grises), valores mínimo y máximo (por defecto los percentiles 2 y 98) y, para
  imágenes de 3 o más bandas, color verdadero o una sola banda.
- **Ventana emergente:** campo de título (también se usa como etiqueta en el
  mapa al acercarse) y campos visibles al hacer clic sobre una entidad.

Pulse **Guardar cambios**. Si sale sin guardar, el sistema le avisa.

## 6. Actualizar un geodato

Pestaña **Archivo → Reemplazar geodato**. Se conservan la ficha, la categoría, el
estado de publicación y el identificador (las URL de la capa no cambian). Si el
tipo de geometría cambia, la simbología vuelve a la predeterminada.

## 7. Publicar, retirar y eliminar

- **Publicar:** botón *Publicar* en la capa o en la lista de capas.
- **Retirar publicación:** la capa vuelve a borrador; sus datos dejan de servirse
  públicamente.
- **Eliminar:** borra la capa y sus archivos de forma definitiva.

Una capa publicada expone:

| Recurso | URL |
| --- | --- |
| Ficha (JSON) | `/api/capas/<identificador>` |
| Datos vectoriales | `/api/capas/<identificador>/datos.geojson` |
| Datos ráster (COG) | `/api/capas/<identificador>/datos.tif` |
| Descarga (procesado / original) | `/api/capas/<identificador>/descarga` · `?original=1` |
| Proyecto GeoLibre de la capa | `/api/capas/<identificador>/proyecto.geolibre` |
| Enlace directo en el mapa | `/?capa=<identificador>` |

## 8. Categorías

Las categorías temáticas son las carpetas del mapa (GeoLibre) y los filtros del catálogo.
El sistema inicia con siete: Recurso hídrico; Áreas protegidas y ecosistemas
estratégicos; Biodiversidad; Cambio climático y gestión del riesgo;
Ordenamiento territorial ambiental; Coberturas de la tierra y deforestación;
Límites y cartografía base. El campo **Orden** define su posición. No se puede
eliminar una categoría con capas asignadas.

## 9. Usuarios y bitácora

- **Usuarios:** cree cuentas personales (no comparta usuarios). Contraseña
  mínima de 10 caracteres combinando letras con números o símbolos. Para retirar
  a alguien, desactive su cuenta.
- **Bitácora:** registra ingresos (también los fallidos), cargas, ediciones,
  publicaciones, retiros, eliminaciones y cambios de categorías y usuarios.

## 10. El mapa del geoportal (GeoLibre)

La portada del geoportal es [GeoLibre](https://github.com/opengeos/GeoLibre), con la misma
interfaz y las mismas funciones que [web.geolibre.app](https://web.geolibre.app/) y con todas las
capas publicadas ya cargadas: las categorías aparecen como carpetas, con la simbología, ventanas
emergentes y metadatos definidos en el administrador. Desde ahí se puede editar, cambiar estilos,
consultar la tabla de atributos, hacer geoprocesamiento y consultas SQL, ver en 3D, componer mapas
para impresión, exportar, guardar el proyecto `.geolibre` y compartirlo.

La capa marcada **Encendida al abrir** aparece encendida en el mapa; las demás están en el panel
Capas, apagadas. El orden de las categorías (campo **Orden**) es el orden de las carpetas.

### Configurar el mapa (solo administradores)

En **Mapa (GeoLibre)** del administrador:

1. **GeoLibre en este servidor:** instala o actualiza GeoLibre (botón **Instalar GeoLibre**) y
   muestra la versión y los requisitos.
2. **¿Qué GeoLibre se usa?:** el instalado en este servidor o una instancia externa (por ejemplo
   `https://web.geolibre.app`).
3. **Pestañas de ajustes:** apariencia e idioma (nombre, idioma, color de acento, modo completo o
   solo consulta, bienvenida y **apariencia institucional**), interfaz y menús (preajustes
   **Completo** —el de web.geolibre.app, por defecto—, **Estándar**, **Esencial** y **Solo
   consulta**; disposición, nivel, menús y elementos ocultos), permisos, complementos, servicios
   institucionales (WMS, WFS, WMTS, XYZ, ArcGIS, CSW) y mapas base, compartir y conexiones
   (servicio de compartir del geoportal, servidor propio, colaboración, Overpass, GeoLens). La
   pestaña **deployment.json** muestra la política resultante.

Los cambios se aplican la próxima vez que se abre el mapa. La guía completa está en
[GeoLibre: el mapa del geoportal](estudio-sig.md).

### Publicar mapas con «Compartir»

Para que un usuario del administrador publique proyectos desde GeoLibre (*Proyecto → Compartir*):

1. En **Mi cuenta → Tokens para compartir desde GeoLibre**, cree un token con un nombre que lo
   identifique (por ejemplo «portátil de la oficina»). Cópielo: solo se muestra una vez.
2. En GeoLibre, abra *Configuración → Entorno*, péguelo en **Token de API** y pulse **Guardar
   configuración** (el diálogo *Proyecto → Compartir…* lo ofrece con «Configurar token local»). El
   geoportal debe servirse por HTTPS.
3. *Proyecto → Compartir* publica el proyecto en el geoportal; el enlace que entrega
   (`<geoportal>/?compartido=usuario/proyecto`) abre el mapa con ese proyecto. Los proyectos
   públicos aparecen en *Proyecto → Abrir desde la galería* para cualquier visitante.

Revoque los tokens que ya no use. Con la **apariencia institucional** activa GeoLibre no guarda el
token entre visitas: para publicar con frecuencia use **Nueva ventana**, donde sí se conserva.

## 11. La portada en pocas palabras

- **Mapa:** GeoLibre a toda la vista, bajo la barra GOV.CO y el encabezado de la Gobernación.
- **Catálogo:** una tarjeta por geodato con búsqueda y filtros; **Ver en el mapa** enciende y
  encuadra la capa, y **Ficha** muestra los metadatos y las descargas.
- **Insertar:** entrega el código `<iframe>` para mostrar el mapa, con la vista y las capas del
  momento, en otra página institucional.
- **Nueva ventana:** abre GeoLibre solo, a pantalla completa.

Los datos que un visitante añade en GeoLibre (*Añadir datos*) se quedan en su navegador: no
llegan al servidor ni aparecen en el catálogo. Para publicar un geodato use **Cargar geodato** en
el administrador.

## 12. Modo oscuro

El botón de tema de la barra superior (geoportal, administrador y asistente de instalación)
alterna entre **Automático** (sigue la preferencia del sistema), **Claro** y **Oscuro**. La
elección se recuerda en el navegador; el mapa (GeoLibre) la toma al recargarse, o con su propio
botón de tema sin recargar.
