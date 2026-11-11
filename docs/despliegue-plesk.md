# Despliegue en Plesk (dominio, subdominio o subdirectorio)

El geoportal funciona en cualquiera de estas ubicaciones sin cambiar código:

| Ubicación | Ejemplo |
| --- | --- |
| Raíz de un dominio | `https://geoportal-ambiental.narino.gov.co/` |
| Raíz de un subdominio | `https://sig.narino.gov.co/` |
| Subdirectorio de otro sitio | `https://www.narino.gov.co/geoportal/` |
| Subcarpeta anidada | `https://www.narino.gov.co/secretarias/ambiente/geoportal/` |

Así se logra:

- el sitio (`portal/`) usa solo rutas relativas (`api/…`, `assets/…`, `../api` en el administrador);
- la API deduce su URL pública de la petición (`Host`, `X-Forwarded-Proto` y `X-Forwarded-Prefix`),
  o usa `GEOPORTAL_PUBLIC_URL` si se define;
- `/geoportal` sin barra final redirige a `/geoportal/`;
- la documentación de la API carga `openapi.json` con ruta relativa;
- la sesión del administrador es propia de cada instalación, aunque compartan dominio.

## Elegir el modo

| | **Modo A — Docker** | **Modo B — sin Docker** |
| --- | --- | --- |
| Requisitos | Plesk Obsidian con la extensión **Docker** | Acceso SSH root y Python 3.10 o superior |
| Sitio estático | Lo sirve el contenedor `web` | Archivos en `httpdocs/` del dominio |
| API | Contenedor `api` | Servicio systemd en `127.0.0.1:8000` |
| GeoLibre propio | Sí (contenedor `geolibre`) | Use la instancia oficial o un subdominio con Docker |
| Directivas nginx | `despliegue/plesk/A-docker-*.conf` | `despliegue/plesk/B-sin-docker-*.conf` |

En ambos modos active **SSL/TLS** (Let's Encrypt) en el dominio: GeoLibre solo se conecta a sitios `https`.

---

## Modo A — con Docker

1. Copie el repositorio al servidor, por ejemplo en `/opt/geoportal`.
2. Prepare la configuración:

   ```bash
   cd /opt/geoportal
   ```

   ```bash
   cp .env.example .env
   ```

   Edite `.env`: `GEOPORTAL_SECRET_KEY`, `GEOPORTAL_ADMIN_PASSWORD`, `GEOPORTAL_PUBLIC_URL`
   (con el subdirectorio, si aplica) y `GEOLIBRE_PUBLIC_URL`.
3. Arranque los contenedores, que quedan escuchando en `127.0.0.1:8080` (geoportal) y `127.0.0.1:8081` (GeoLibre):

   ```bash
   docker compose up -d --build
   ```

   En Plesk también puede hacerlo desde **Docker → Stacks → Add Stack** con el `docker-compose.yml`.
   Ponga `GEOPORTAL_IP=127.0.0.1` en `.env` para que los puertos solo sean accesibles desde el nginx de Plesk.
4. Enlace el dominio:
   - **Raíz de dominio o subdominio:** *Sitios web y dominios → dominio → Docker Proxy Rules →
     Añadir regla*, con URL `/`, contenedor `…-web-1` y puerto `80`. Después pegue
     [`A-docker-raiz.conf`](../despliegue/plesk/A-docker-raiz.conf) en *Configuración de Apache y nginx →
     Directivas adicionales de nginx*. En este modo `GEOPORTAL_PUBLIC_URL` es obligatoria, porque la regla
     de Plesk no reenvía el esquema `https` al contenedor.
   - **Subdirectorio:** pegue [`A-docker-subdirectorio.conf`](../despliegue/plesk/A-docker-subdirectorio.conf)
     en *Directivas adicionales de nginx*, cambiando `/geoportal` por la ruta elegida en las líneas marcadas `◄`.
5. GeoLibre en su propio subdominio (por ejemplo `visor-sig.narino.gov.co`): cree el subdominio en
   Plesk, añada una *Docker Proxy Rule* `/` → contenedor `…-geolibre-1`, puerto `80`, y active SSL.

## Modo B — sin Docker

1. API como servicio (como root):

   ```bash
   useradd --system --home /opt/geoportal --shell /usr/sbin/nologin geoportal
   ```

   ```bash
   git clone <repositorio> /opt/geoportal/src && ln -s /opt/geoportal/src/api /opt/geoportal/api
   ```

   ```bash
   python3 -m venv /opt/geoportal/venv && /opt/geoportal/venv/bin/pip install -r /opt/geoportal/api/requirements.txt
   ```

   ```bash
   mkdir -p /opt/geoportal/datos && chown geoportal: /opt/geoportal/datos
   ```

   Cree `/opt/geoportal/geoportal.env` con las variables de `.env.example` más
   `GEOPORTAL_DATA_DIR=/opt/geoportal/datos`, y protéjalo con `chmod 600`.

   ```bash
   cp /opt/geoportal/src/despliegue/systemd/geoportal-api.service /etc/systemd/system/
   ```

   ```bash
   systemctl daemon-reload && systemctl enable --now geoportal-api
   ```

   Las ruedas de `pyogrio`, `rasterio` y `pyproj` incluyen GDAL y PROJ, así que no hace falta instalar GDAL
   en el sistema. En AlmaLinux o Rocky 8 instale antes `python3.11`.
2. Sitio estático: copie `portal/` a la carpeta pública del dominio.
   - Raíz: `/var/www/vhosts/<dominio>/httpdocs/`
   - Subdirectorio: `/var/www/vhosts/<dominio>/httpdocs/geoportal/`

   ```bash
   rsync -a --delete /opt/geoportal/src/portal/ /var/www/vhosts/<dominio>/httpdocs/geoportal/
   ```

   Después asigne los archivos al usuario de la suscripción
   (`chown -R <usuario>:psacln …`), o use el Administrador de archivos de Plesk.
3. Directivas: pegue en *Configuración de Apache y nginx → Directivas adicionales de nginx*
   [`B-sin-docker-raiz.conf`](../despliegue/plesk/B-sin-docker-raiz.conf) o
   [`B-sin-docker-subdirectorio.conf`](../despliegue/plesk/B-sin-docker-subdirectorio.conf),
   ajustando la ruta. Funciona con el modo proxy de nginx activado o desactivado, y convive con otro
   sitio (por ejemplo WordPress) en la raíz: las rutas `^~ /geoportal/api/` se resuelven en nginx antes
   que las reglas de Apache o `.htaccess`.
4. GeoLibre: defina `GEOLIBRE_PUBLIC_URL=https://web.geolibre.app` (sin instalar nada) o un subdominio
   con Docker (paso 5 del Modo A).

## GeoLibre: dónde publicarlo

| Opción | `GEOLIBRE_PUBLIC_URL` | Comentario |
| --- | --- | --- |
| Subdominio propio (recomendada) | `https://visor-sig.narino.gov.co` | Imagen oficial sin modificaciones |
| Instancia oficial | `https://web.geolibre.app` | Sin instalar nada. La aplicación se carga desde geolibre.app y el navegador descarga los datos directamente del geoportal |
| Subdirectorio del mismo dominio | `https://www.narino.gov.co/visor-sig` | Requiere construir la imagen de GeoLibre con `--build-arg GEOLIBRE_APP_BASE=/visor-sig/`. No se verificó en este repositorio |

GeoLibre exige que el geoportal se sirva con `https`. La API ya responde con CORS al origen definido en
`GEOLIBRE_PUBLIC_URL`.

## Verificación después de instalar

Reemplace `BASE` por la URL de su instalación, por ejemplo `https://www.narino.gov.co/geoportal`.

```bash
curl -sI BASE | head -1
```

Debe responder `301` hacia `BASE/` (en un subdirectorio).

```bash
curl -s BASE/api/salud
```

Debe responder `{"estado":"ok"}`.

```bash
curl -s BASE/api/config
```

`proyecto_url` debe empezar por `BASE/api/` con `https`.

Luego, en el navegador:

1. `BASE/admin/` → ingrese, cargue un geodato pequeño y publíquelo.
2. `BASE/` → encienda la capa, abra su ficha, descárguela y pulse **Abrir en GeoLibre**.
3. `BASE/api/docs` → la documentación debe cargar.

## Problemas frecuentes

| Síntoma | Causa probable | Solución |
| --- | --- | --- |
| `413 Request Entity Too Large` al cargar | Límite de nginx de Plesk | `client_max_body_size` en las directivas (incluido en los archivos) |
| `502 Bad Gateway` en `/api/` | API detenida | `systemctl status geoportal-api` o `docker compose ps` |
| `403` en el sitio | Permisos de `httpdocs` | Asignar los archivos al usuario de la suscripción |
| Página sin estilos en `/geoportal` | Falta la barra final | Ya se redirige; revise que no haya reglas que eliminen la barra |
| GeoLibre: «Could not fetch the project» | Sitio sin `https`, URL pública incorrecta o CORS | Active SSL, revise `GEOPORTAL_PUBLIC_URL` y `GEOLIBRE_PUBLIC_URL` |
| Enlaces `http://` en un sitio `https` | El proxy no envía `X-Forwarded-Proto` | Defina `GEOPORTAL_PUBLIC_URL` con `https://` |

## Verificación realizada

Se simuló Plesk con nginx 1.24 usando los archivos de `despliegue/plesk/` tal como se entregan, la
configuración real del contenedor `web` (`proxy/nginx.conf`) y una sola API sin `GEOPORTAL_PUBLIC_URL`.
El escenario 4 usó la ruta anidada en lugar de `/geoportal`.

| Escenario | Redirección sin barra | Ingreso y carga | Visor y datos | Descarga | Proyecto GeoLibre | Docs API |
| --- | :---: | :---: | :---: | :---: | :---: | :---: |
| 1. Raíz de dominio, Modo B | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| 2. Subdominio, Modo A | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| 3. `/geoportal/` junto a otro sitio, Modo B | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| 4. `/secretarias/ambiente/geoportal/`, Modo A | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |

Además se comprobó que `web.geolibre.app` abre un proyecto servido desde
`https://…/geoportal/api/proyecto.geolibre`. Lo que no se pudo probar fue un servidor Plesk real:
la interfaz de *Docker Proxy Rules* y la inclusión de las directivas se describen según la documentación
de Plesk, y conviene seguir la verificación anterior en el servidor de la Gobernación.
