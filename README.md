# Geoportal Ambiental — Gobernación de Nariño

Geoportal de la **Secretaría de Ambiente y Desarrollo Sostenible** para publicar,
consultar y descargar la información geográfica ambiental del departamento.
Usa [GeoLibre](https://github.com/opengeos/GeoLibre) (SIG libre, MIT) como
visor de análisis avanzado: cada capa publicada se puede abrir en GeoLibre con
un clic, y desde ahí usar sus más de mil herramientas de geoprocesamiento en el
navegador.

| Componente | Qué hace | Dónde |
| --- | --- | --- |
| **Visor público** | Mapa con capas por categoría, transparencia, leyenda, consulta de atributos, mapas base, ficha de metadatos, descarga y enlace a GeoLibre | `portal/index.html` |
| **Catálogo** | Tarjetas de geodatos con búsqueda y filtros | `portal/index.html#catalogo` |
| **Administrador** | Carga de geodatos, ficha de metadatos, simbología, publicación, categorías, usuarios y bitácora | `portal/admin/` |
| **API** | FastAPI: ingesta y conversión de formatos, catálogo, datos, proyectos `.geolibre` | `api/` |
| **GeoLibre** | SIG web para análisis; abre los proyectos que genera la API | servicio `geolibre` (imagen oficial) |

```mermaid
flowchart LR
  A[Administrador<br>/admin/] -- carga geodatos --> API
  API[API FastAPI<br>/api/] -- convierte y reproyecta --> D[(Volumen de datos<br>originales · GeoJSON · COG<br>SQLite/PostgreSQL)]
  V[Visor público<br>MapLibre] -- catálogo y datos --> API
  V -- «Abrir en GeoLibre» --> G[GeoLibre<br>?url=/api/proyecto.geolibre]
  G -- proyecto .geolibre, GeoJSON, COG por rangos --> API
```

## Dos ediciones, la misma interfaz

| | **Plesk / hosting PHP** | **Docker / servidor** |
| --- | --- | --- |
| Instalación | Subir la carpeta y completar el **asistente de instalación** (como WordPress) | `docker compose up` o servicio systemd |
| Backend | PHP 8.1+ (`portal/api/`) | Python FastAPI + GDAL (`api/`) |
| Base de datos | **MySQL / MariaDB** | MySQL, PostgreSQL o SQLite |
| Conversión de geodatos | En el navegador del administrador, con validación en el servidor | En el servidor (GDAL) |
| Guía | [Instalación en Plesk](docs/instalacion-plesk.md) | Ver abajo y [arquitectura](docs/arquitectura.md) |

Ambas exponen la misma API (`/api/...`), así que el visor, el catálogo, el administrador y la
integración con GeoLibre son idénticos.

## Instalación en Plesk (subiendo archivos)

1. Cree una base de datos MySQL en Plesk.
2. Genere el paquete con `scripts/empaquetar-plesk.sh` o descárguelo de *Releases*.
3. Súbalo con el Administrador de archivos y elija «Extraer».
4. Abra `https://su-dominio/geoportal/instalar/` y siga el asistente.

Los detalles, la solución de problemas y la verificación realizada están en
[docs/instalacion-plesk.md](docs/instalacion-plesk.md).

## Inicio rápido (Docker)

```bash
cp .env.example .env
```

Edite `.env`: como mínimo `GEOPORTAL_SECRET_KEY`, `GEOPORTAL_ADMIN_PASSWORD` y,
en un servidor, `GEOPORTAL_PUBLIC_URL` y `GEOLIBRE_PUBLIC_URL`.

```bash
docker compose up -d --build
```

- Geoportal: <http://localhost:8080>
- Administrador: <http://localhost:8080/admin/>
- Documentación de la API: <http://localhost:8080/api/docs>
- GeoLibre: <http://localhost:8081>

## Desarrollo sin Docker

```bash
cd api
pip install -r requirements-dev.txt
```

```bash
GEOPORTAL_ADMIN_PASSWORD=Clave-Local-2026 GEOPORTAL_PORTAL_DIR=../portal GEOPORTAL_PUBLIC_URL=http://localhost:8000 uvicorn app.main:app --reload
```

Con `GEOPORTAL_PORTAL_DIR` la API sirve también el sitio estático, así que el
geoportal queda en <http://localhost:8000> y el administrador en
<http://localhost:8000/admin/>.

Pruebas:

```bash
cd api && python -m pytest
```

Pruebas de la edición PHP (necesitan PHP 8.1+ con `pdo_mysql` y un MySQL accesible):

```bash
GP_MYSQL_USER=usuario GP_MYSQL_PASSWORD=clave python -m pytest pruebas/edicion_php
```

## Formatos que acepta el administrador

| Tipo | Formatos | Resultado publicado |
| --- | --- | --- |
| Vector | GeoJSON, Shapefile (`.zip` con `.shp`, `.shx`, `.dbf`, `.prj`), GeoPackage, KML/KMZ, GML, FlatGeobuf, GeoParquet, CSV (lat/lon o WKT) | GeoJSON RFC 7946 en EPSG:4326 |
| Ráster | GeoTIFF/COG, ERDAS IMG, ASCII Grid, JPEG 2000 | Cloud Optimized GeoTIFF (EPSG:3857) + vista previa PNG |

Los sistemas de referencia colombianos (MAGNA-SIRGAS Origen Nacional EPSG:9377,
orígenes Bogotá/Oeste/Este, ESRI:103599, etc.) se detectan y reproyectan
automáticamente. Si el archivo no declara su sistema (Shapefile sin `.prj`, CSV en
metros) el administrador permite indicar el EPSG de origen.

## Documentación

- [Manual del administrador](docs/manual-administrador.md): cómo cargar, documentar, simbolizar y publicar geodatos.
- [Arquitectura y despliegue](docs/arquitectura.md): componentes, API, integración con GeoLibre, producción y respaldos.
- [Instalación en Plesk subiendo archivos](docs/instalacion-plesk.md): edición PHP + MySQL con asistente de instalación.
- [Despliegue en Plesk con Docker o systemd](docs/despliegue-plesk.md): edición Python, en dominio, subdominio o subdirectorio.
- [Identidad visual](docs/identidad-visual.md): cómo se aplicaron los manuales de la Gobernación.

## Auditoría de seguridad

El repositorio incluye la skill [`security-audit`](.claude/skills/security-audit/) de Cloudflare
(MIT), revisada y fijada a un commit (ver [`PROCEDENCIA.md`](.claude/skills/security-audit/PROCEDENCIA.md)).
En Claude Code, dentro del repositorio, pida por ejemplo «haz una auditoría de seguridad de este
repositorio». Los informes se escriben fuera del repositorio.

## Licencia

La licencia del código del geoportal la define la Gobernación de Nariño.
GeoLibre es software de terceros con licencia MIT (© Qiusheng Wu y
colaboradores) y se usa sin modificaciones desde su imagen oficial. Los
geodatos publicados conservan la licencia indicada en su ficha.
