# Instalación en Plesk subiendo archivos (edición PHP + MySQL)

Esta es la forma más sencilla de publicar el geoportal: **se sube una carpeta y se
completa un asistente**, como en WordPress. No requiere SSH, Docker ni Python.

| Necesita | Detalle |
| --- | --- |
| Hosting con Plesk | Cualquier plan con PHP y MySQL |
| PHP 8.1 o superior | Con las extensiones `pdo_mysql` y `mbstring` (vienen por defecto en Plesk) |
| MySQL 5.7+ / 8.x o MariaDB 10.3+ | Una base de datos vacía |
| Apache activo | Configuración por defecto de Plesk (nginx delante de Apache) |
| Certificado SSL | Recomendado; GeoLibre solo abre proyectos de sitios `https` |

Funciona en la raíz de un dominio, en un subdominio o en cualquier subcarpeta
(`/geoportal/`, `/secretarias/ambiente/geoportal/`…).

## 1. Crear la base de datos

En Plesk: **Sitios web y dominios → *su dominio* → Bases de datos → Añadir base de datos**.

- Nombre de la base de datos: por ejemplo `geoportal`.
- Usuario y contraseña: anótelos; el asistente los pedirá.

## 2. Obtener los archivos

Opción recomendada, el **paquete listo para subir** `geoportal-plesk-<versión>.zip`:

- Desde la sección *Releases* del repositorio en GitHub, o
- generándolo usted mismo:

  ```bash
  scripts/empaquetar-plesk.sh
  ```

El ZIP contiene una única carpeta `geoportal/`, con todo lo necesario.

Si en su lugar usa **Code → Download ZIP** de GitHub, lo que se sube es el contenido de la carpeta
`portal/` del repositorio (el resto es la edición Docker y la documentación).

## 3. Subir los archivos

**Con el Administrador de archivos de Plesk (recomendado):**

1. Abra **Archivos** y entre a `httpdocs` (o a la carpeta del subdominio).
2. **Cargar** → elija `geoportal-plesk-<versión>.zip`.
3. Clic derecho sobre el ZIP → **Extraer archivos**. Se crea la carpeta `geoportal/`.
4. Para instalar en la raíz del dominio, mueva el contenido de `geoportal/` a `httpdocs/`.
   Para usar otra ruta, renombre o mueva la carpeta.
5. Puede borrar el ZIP.

**Con FTP:** suba el contenido de la carpeta, **incluidos los archivos ocultos** `.htaccess` y
`api/.user.ini`. Algunos programas de FTP los ocultan: actívelos en las preferencias. Sin ellos la
API no responde y el asistente lo indicará.

## 4. Ejecutar el asistente

Abra en el navegador `https://su-dominio/geoportal/instalar/` (o `https://su-dominio/instalar/`
si instaló en la raíz).

| Paso | Qué hace |
| --- | --- |
| **1. Requisitos** | Revisa la versión de PHP y las extensiones, los permisos, el tamaño de carga, HTTPS, que la API responda y que PHP reciba la cabecera de autorización |
| **2. Base de datos** | Pide servidor (casi siempre `localhost`), nombre, usuario, contraseña y prefijo de tablas (`gp_`). Prueba la conexión y explica el error en español si falla. Crea `config.php` con una clave secreta aleatoria |
| **3. Sitio y administrador** | Nombre del geoportal, URL pública (detectada), GeoLibre (`https://web.geolibre.app` por defecto) y la cuenta del administrador. En *Opciones avanzadas*, la carpeta de datos |
| **4. Listo** | Crea las tablas, las 7 categorías temáticas iniciales y el administrador. Comprueba que la carpeta de datos no sea accesible desde Internet |

Si PHP no puede crear `config.php` (carpeta sin permiso de escritura), el asistente muestra su
contenido para que lo cree a mano con el Administrador de archivos, igual que WordPress.

Terminada la instalación, **el asistente queda bloqueado**. Para reinstalar desde cero hay que
borrar `config.php` y las tablas.

**Carpeta de datos.** Por defecto se crea fuera de la raíz pública, junto a `httpdocs`
(`/var/www/vhosts/su-dominio/geoportal-datos-…`), que es la ubicación más segura. Si no es posible,
se crea dentro de la instalación con un nombre aleatorio y protegida con `.htaccess`.

## 5. Después de instalar

1. **SSL:** *Sitios web y dominios → SSL/TLS → Let's Encrypt*. Active «Redirigir de HTTP a HTTPS».
2. **Ingrese** a `…/geoportal/admin/` con el usuario creado y cargue los geodatos. Vea el
   [manual del administrador](manual-administrador.md).
3. **Configuración:** el administrador tiene la sección *Configuración* (nombre, URL pública,
   GeoLibre, tamaño máximo de carga, duración de la sesión).
4. **Tamaño de carga:** la API incluye un `.user.ini` que eleva los límites de PHP a 512 MB. Si su
   plan no lo permite, ajústelos en *Configuración de PHP* (`upload_max_filesize`, `post_max_size`)
   y, para archivos de más de 128 MB, en *Configuración de Apache y nginx*
   (`client_max_body_size 600m;` en las directivas adicionales de nginx).

## Cómo procesa los geodatos esta edición

Un hosting compartido no tiene GDAL, así que **la conversión se hace en el navegador** del
administrador, como en GeoLibre, y el servidor vuelve a validar el resultado:

| Archivo | Qué hace el navegador |
| --- | --- |
| GeoJSON, Shapefile (.zip), KML, KMZ, GeoPackage, CSV | Lo lee, lo reproyecta a WGS 84 (EPSG:4326) y sube el GeoJSON junto con el original |
| GeoTIFF | Calcula estadísticas y genera la vista previa del visor. Si no está en EPSG:4326/3857 o no está teselado, crea además una copia teselada en EPSG:4326 para GeoLibre (hasta unos 16 millones de celdas) |

Sistemas de referencia reconocidos: MAGNA-SIRGAS Origen Nacional (EPSG:9377 / ESRI:103599),
MAGNA-SIRGAS Colombia 3114–3118, MAGNA-SIRGAS geográficas (4686), WGS 84 (4326, 3857) y
UTM 17N–19N. Los Shapefile y GeoPackage con definición WKT también se reproyectan.

El servidor recalcula por su cuenta la extensión, el número de entidades, el tipo de geometría y los
atributos, y rechaza coordenadas fuera de rango. Los intentos fallidos no dejan capas a medias.

### Diferencias con la edición Docker (Python)

| | Plesk (PHP) | Docker (Python) |
| --- | --- | --- |
| Instalación | Subir archivos y usar el asistente | Docker Compose o servicio systemd |
| Base de datos | MySQL / MariaDB | SQLite, PostgreSQL o MySQL |
| Formatos | GeoJSON, Shapefile, KML/KMZ, GeoPackage, CSV, GeoTIFF | Los anteriores más GML, FlatGeobuf, GeoParquet, IMG, ASC y JP2 |
| Reparación de geometrías inválidas | No (se publican como llegan) | Sí (`make_valid`) |
| Rásteres grandes en GeoLibre | Hasta unos 16 millones de celdas, o subirlos ya como COG en EPSG:4326/3857 | Sin límite práctico (COG generado con GDAL) |

Los rásteres muy grandes se ven igual en el visor del geoportal. Para abrirlos en GeoLibre,
expórtelos desde QGIS como COG en EPSG:4326 o EPSG:3857.

## Actualizar a una nueva versión

1. Respalde la base de datos (*Bases de datos → Exportar volcado*) y la carpeta de datos.
2. Suba los archivos nuevos sobre los anteriores **sin borrar** `config.php` ni la carpeta de datos.
3. No hace falta volver a ejecutar el asistente.

## Respaldos

- **Base de datos:** *Bases de datos → Exportar volcado*, o el *Administrador de copias de seguridad*
  de Plesk, que incluye bases de datos y archivos.
- **Archivos:** la carpeta de datos (`geoportal-datos-…`) y `config.php`.

## Seguridad incluida

- Contraseñas con bcrypt y sesiones JWT firmadas con una clave aleatoria por instalación.
- `config.php`, `api/lib/` y `.user.ini` bloqueados por `.htaccess`.
- Carpeta de datos fuera de la raíz pública (o protegida y con nombre aleatorio). Los datos
  solo se sirven a través de la API, y los borradores no son públicos.
- Roles editor/administrador validados en el servidor y bitácora de acciones.
- CORS solo para la instancia de GeoLibre configurada.
- Asistente bloqueado después de instalar.

Recomendado: limitar el acceso a `/admin/` por IP desde *Configuración de Apache y nginx*.

## Problemas frecuentes

| Síntoma | Causa | Solución |
| --- | --- | --- |
| El asistente marca ✘ en «Rutas amigables de la API» | No se subió `api/.htaccess` o el sitio no usa Apache | Suba los archivos ocultos; en *Configuración de Apache y nginx* deje activo el modo proxy |
| ✘ en «Cabecera de autorización» | Falta `api/.htaccess` | Súbalo. Sin él no se puede ingresar al administrador |
| «No se pudo conectar con el servidor MySQL» | Servidor o puerto incorrectos | Use `localhost`. Si PHP no puede abrir el socket, el asistente reintenta con `127.0.0.1` |
| «La base de datos … no existe» | No se creó en Plesk | *Bases de datos → Añadir base de datos* |
| «El archivo supera el tamaño máximo» | Límites de PHP o nginx | Vea el punto 4 de «Después de instalar» |
| Página en blanco o error 500 | Error de PHP | *Registros* del dominio en Plesk (`error_log`) |
| GeoLibre: «Could not fetch the project» | Sitio sin `https` | Active SSL |
| GeoLibre no muestra un ráster | GeoTIFF muy grande en un sistema distinto de 4326/3857 o sin teselar | Expórtelo como COG en EPSG:4326 desde QGIS |

### Hosting solo con nginx (sin Apache)

Si el plan no usa Apache, los `.htaccess` no aplican. Añada en *Configuración de Apache y nginx →
Directivas adicionales de nginx* (ajuste `/geoportal` a su ruta). Esta variante no se verificó
en este repositorio.

```nginx
location ~ ^/geoportal/(config\.php|api/lib/|.*\.user\.ini) { deny all; }
location ^~ /geoportal/api/ { try_files $uri /geoportal/api/index.php$is_args$args; }
```

## Verificación realizada

Se simuló un servidor Plesk con la misma pila y restricciones:

- nginx delante de Apache 2.4, con «servir archivos estáticos directamente por nginx».
- PHP-FPM 8.3 ejecutándose con el usuario de la suscripción, `open_basedir` limitado al espacio
  web y límites de PHP por defecto (2 MB / 8 MB).
- `AllowOverride` restringido como en Plesk.
- MySQL 8.0 con el socket inaccesible para el usuario del sitio.

Los archivos se obtuvieron del ZIP del repositorio y del paquete `geoportal-plesk`, y se subieron
como lo haría un usuario.

| Escenario | Resultado |
| --- | --- |
| Subcarpeta `www.narino.test/geoportal/`, archivos del ZIP del repositorio | ✔ Asistente completo, `config.php` creado automáticamente |
| Raíz del subdominio `sig.narino.test/`, paquete extraído, carpeta **sin permiso de escritura** | ✔ El asistente mostró `config.php` para crearlo a mano y continuó |
| Ambas instalaciones en la misma base de datos con prefijos `gp_` y `sig_` | ✔ Independientes |
| Error de contraseña de MySQL | ✔ Mensaje claro en español |
| `.user.ini` elevando el límite de 2 MB por defecto | ✔ Límite efectivo de 200 MB (el configurado en el geoportal) |
| Asistente después de instalar | ✔ Bloqueado; `config.php` responde 403 |
| Carpeta de datos | ✔ Fuera de la raíz pública |

Formatos cargados desde el administrador y comparados con geopandas/rasterio:

| Archivo | Sistema de origen | Diferencia de la extensión |
| --- | --- | --- |
| Shapefile .zip con `.prj` | MAGNA-SIRGAS Origen Nacional (9377) | 0 |
| Shapefile .zip sin `.prj` (EPSG indicado) | 9377 | 0 |
| GeoPackage con 2 capas | MAGNA-SIRGAS Bogotá (3116) | 0 (con aviso de la segunda capa) |
| KML y KMZ | WGS 84 | 0 |
| CSV con `;` y coma decimal | WGS 84 | 0 |
| GeoJSON real de drenajes (17 MB, 453 polígonos) | ESRI:103599 | 0 (1,9 s) |
| GeoTIFF float32 | 9377 | < 0,0005° en la copia reproyectada para GeoLibre |

También se comprobaron:

- El visor, la ficha, las descargas y la lectura del GeoTIFF por rangos (HTTP 206).
- El proyecto GeoLibre: carpetas por categoría y URLs bajo la subcarpeta.
- Que `web.geolibre.app` abre las capas vectoriales y los rásteres, incluido el DEM en MAGNA
  reproyectado en el navegador.
- Los roles (editor sin permiso de publicar, eliminar ni gestionar usuarios).
- El cambio de la rampa de color de un ráster, con la vista previa regenerada.

Las pruebas automáticas de esta edición están en `pruebas/edicion_php/` y se ejecutan en GitHub
Actions con MySQL 8.
