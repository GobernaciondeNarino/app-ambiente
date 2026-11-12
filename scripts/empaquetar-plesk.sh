#!/usr/bin/env bash
# Genera el paquete para subir a Plesk (u otro hosting con PHP y MySQL):
#   dist/geoportal-plesk-<versión>.zip               →  carpeta «geoportal/» lista para extraer en httpdocs
#   dist/geoportal-plesk-<versión>-con-geolibre.zip  →  además, el Estudio SIG (GeoLibre) ya incluido,
#                                                       para servidores que no pueden descargarlo
# Uso: scripts/empaquetar-plesk.sh [--con-geolibre] [versión]
set -euo pipefail
cd "$(dirname "$0")/.."
CON_GEOLIBRE=0
if [ "${1:-}" = "--con-geolibre" ]; then CON_GEOLIBRE=1; shift; fi
VERSION="${1:-$(sed -n "s/^const GP_VERSION = '\(.*\)';/\1/p" portal/api/lib/nucleo.php)}"
DESTINO="dist/geoportal-plesk-${VERSION}$([ "$CON_GEOLIBRE" = 1 ] && echo -con-geolibre).zip"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p dist "$TMP/geoportal"
# Solo los archivos versionados de portal/ (sin config.php, datos ni archivos locales)
git archive --format=tar HEAD portal | tar -x -C "$TMP"
cp -a "$TMP/portal/." "$TMP/geoportal/"
rm -rf "$TMP/portal"
if [ "$CON_GEOLIBRE" = 1 ]; then
  scripts/descargar-geolibre.sh "$TMP/geoportal/geolibre"
fi
cat > "$TMP/geoportal/LEAME-INSTALACION.txt" <<TXT
Geoportal Ambiental — Gobernación de Nariño · versión ${VERSION}

1. En Plesk cree una base de datos MySQL (Sitios web y dominios → Bases de datos).
2. Suba este ZIP con el Administrador de archivos a httpdocs (o a la subcarpeta que
   prefiera) y use «Extraer archivos». Se crea la carpeta «geoportal».
   Puede renombrarla o mover su contenido a httpdocs para instalar en la raíz.
3. Abra https://<su-dominio>/geoportal/instalar/ y siga el asistente.
4. Estudio SIG (GeoLibre integrado): $([ "$CON_GEOLIBRE" = 1 ] && echo "ya viene en la carpeta «geolibre»." || echo "instálelo desde Administrador → Estudio SIG
   (descarga ≈56 MB de PyPI), o use el paquete «-con-geolibre».")

Guía completa: docs/instalacion-plesk.md en el repositorio.
TXT
rm -f "$DESTINO"
(cd "$TMP" && zip -qr -X "$OLDPWD/$DESTINO" geoportal)
echo "Paquete generado: $DESTINO ($(du -h "$DESTINO" | cut -f1))"
