# Despliegue en Plesk con Docker o systemd (edición Python)

> ¿Prefiere subir archivos y usar un asistente, sin SSH ni Docker? Use la
> [edición PHP + MySQL](instalacion-plesk.md). Esta página describe la edición Python
> (FastAPI + GDAL), que requiere la extensión Docker de Plesk o acceso SSH.

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
| Estudio SIG (GeoLibre integrado) | Volumen `geolibre`, servido en `/geolibre/` | Carpeta `geolibre/` dentro del sitio estático |
| Directivas nginx | `despliegue/plesk/A-docker-*.conf` | `despliegue/plesk/B-sin-docker-*.conf` |

En ambos modos active **SSL/TLS** (Let's Encrypt) en el dominio. El Estudio SIG integrado comparte
origen con el geoportal; una instancia externa de GeoLibre solo se conecta a sitios `https`.

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

   Edite `.env`: `GEOPORTAL_SECRET_KEY`, `GEOPORTAL_ADMIN_PASSWORD` y `GEOPORTAL_PUBLIC_URL`
   (con el subdirectorio, si aplica). Deje `GEOLIBRE_PUBLIC_URL=local` para el Estudio SIG integrado.
3. Arranque los contenedores, que quedan escuchando en `127.0.0.1:8080`:

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
5. Estudio SIG: *Administrador → Estudio SIG → Instalar GeoLibre*. Queda en el volumen `geolibre` y
   se publica en `…/geolibre/` del mismo dominio y ruta, sin reglas adicionales.
6. Opcional, GeoLibre con su *sidecar* de Python en su propio subdominio (por ejemplo
   `visor-sig.narino.gov.co`): `docker compose --profile geolibre-separado up -d`, cree el subdominio
   en Plesk, añada una *Docker Proxy Rule* `/` → contenedor `…-geolibre-1`, puerto `80`, active SSL y
   elija esa URL como instancia externa en *Administrador → Estudio SIG*.

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
   rsync -a --delete --exclude geolibre/ /opt/geoportal/src/portal/ /var/www/vhosts/<dominio>/httpdocs/geoportal/
   ```

   Después asigne los archivos al usuario de la suscripción
   (`chown -R <usuario>:psacln …`), o use el Administrador de archivos de Plesk.
3. Directivas: pegue en *Configuración de Apache y nginx → Directivas adicionales de nginx*
   [`B-sin-docker-raiz.conf`](../despliegue/plesk/B-sin-docker-raiz.conf) o
   [`B-sin-docker-subdirectorio.conf`](../despliegue/plesk/B-sin-docker-subdirectorio.conf),
   ajustando la ruta. Funciona con el modo proxy de nginx activado o desactivado, y convive con otro
   sitio (por ejemplo WordPress) en la raíz: las rutas `^~ /geoportal/api/` se resuelven en nginx antes
   que las reglas de Apache o `.htaccess`.
4. Estudio SIG: añada a `geoportal.env` la carpeta donde la API instalará GeoLibre, dentro del sitio
   estático, y dé permiso de escritura al usuario del servicio:

   ```ini
   GEOPORTAL_GEOLIBRE_DIR=/var/www/vhosts/<dominio>/httpdocs/geoportal/geolibre
   GEOLIBRE_PUBLIC_URL=local
   ```

   ```bash
   mkdir -p /var/www/vhosts/<dominio>/httpdocs/geoportal/geolibre && chown geoportal:psacln /var/www/vhosts/<dominio>/httpdocs/geoportal/geolibre && chmod 2775 /var/www/vhosts/<dominio>/httpdocs/geoportal/geolibre
   ```

   El servicio protege el sistema de archivos (`ProtectSystem=strict`): permita escribir en esa
   carpeta con `systemctl edit geoportal-api` y estas líneas:

   ```ini
   [Service]
   ReadWritePaths=/var/www/vhosts/<dominio>/httpdocs/geoportal/geolibre
   ```

   Reinicie el servicio e instale desde *Administrador → Estudio SIG*. Como alternativa, ejecute
   `scripts/descargar-geolibre.sh /var/www/vhosts/<dominio>/httpdocs/geoportal/geolibre`.
   Para no instalar nada, elija en el administrador la instancia externa `https://web.geolibre.app`.

## GeoLibre: dónde publicarlo

| Opción | Cómo | Comentario |
| --- | --- | --- |
| **Estudio SIG integrado (recomendada)** | `GEOLIBRE_PUBLIC_URL=local` e instalar desde el administrador | Mismo origen que el geoportal, en cualquier dominio, subdominio o subdirectorio; configurable desde el administrador y controlado desde el visor. Ver [Estudio SIG](estudio-sig.md) |
| Instancia oficial | Instancia externa `https://web.geolibre.app` en el administrador | Sin instalar nada. La aplicación se carga desde geolibre.app y el navegador descarga los datos del geoportal (CORS) |
| Subdominio propio con Docker | Perfil `geolibre-separado` e instancia externa `https://visor-sig.narino.gov.co` | Imagen oficial con *sidecar* de Python opcional |

Con una instancia externa el geoportal debe servirse con `https`; la API responde con CORS al
origen de esa instancia, y el cambio se aplica sin reiniciar.

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
2. `BASE/` → encienda la capa, abra su ficha, descárguela y pulse **Ver en Estudio SIG** (o
   **Abrir en GeoLibre** si usa una instancia externa).
3. `BASE/api/docs` → la documentación debe cargar.

## Problemas frecuentes

| Síntoma | Causa probable | Solución |
| --- | --- | --- |
| `413 Request Entity Too Large` al cargar | Límite de nginx de Plesk | `client_max_body_size` en las directivas (incluido en los archivos) |
| `502 Bad Gateway` en `/api/` | API detenida | `systemctl status geoportal-api` o `docker compose ps` |
| `403` en el sitio | Permisos de `httpdocs` | Asignar los archivos al usuario de la suscripción |
| Página sin estilos en `/geoportal` | Falta la barra final | Ya se redirige; revise que no haya reglas que eliminen la barra |
| GeoLibre externo: «Could not fetch the project» | Sitio sin `https`, URL pública incorrecta o CORS | Active SSL, revise `GEOPORTAL_PUBLIC_URL` y la instancia externa en el administrador |
| «Instalar GeoLibre» falla con permiso denegado | El usuario del servicio no puede escribir en `GEOPORTAL_GEOLIBRE_DIR` | Ver el paso 4 del Modo B, o use `scripts/descargar-geolibre.sh` |
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
