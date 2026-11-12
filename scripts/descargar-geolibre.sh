#!/usr/bin/env bash
# Descarga la compilación web oficial de GeoLibre (versión fijada en portal/api/geolibre-version.json),
# verifica su SHA-256 y la instala en portal/geolibre/ («Estudio SIG» del geoportal).
# No ejecuta código del paquete: solo descarga, verifica y descomprime archivos estáticos.
# Uso: scripts/descargar-geolibre.sh
set -euo pipefail
cd "$(dirname "$0")/.."
leer() { python3 -I -c "import json,sys; print(json.load(open('portal/api/geolibre-version.json'))[sys.argv[1]])" "$1"; }
VERSION="$(leer version)"; URL="$(leer paquete)"; SHA="$(leer sha256)"; DENTRO="$(leer carpeta_en_paquete)"
DESTINO="portal/geolibre"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
echo "Descargando GeoLibre ${VERSION}…"
curl -fsSL -o "$TMP/geolibre.whl" "$URL"
echo "${SHA}  $TMP/geolibre.whl" | sha256sum -c - >/dev/null || { echo "La suma SHA-256 no coincide: descarga rechazada." >&2; exit 1; }
mkdir -p "$TMP/x"
unzip -q "$TMP/geolibre.whl" "${DENTRO}*" -d "$TMP/x"
# Conserva la política y los ajustes que genera el geoportal, si ya existían
for f in deployment.json geoportal-ajustes.json; do [ -f "$DESTINO/$f" ] && cp "$DESTINO/$f" "$TMP/$f"; done
rm -rf "$DESTINO"
mv "$TMP/x/${DENTRO%/}" "$DESTINO"
for f in deployment.json geoportal-ajustes.json; do [ -f "$TMP/$f" ] && cp "$TMP/$f" "$DESTINO/$f"; done
echo "$VERSION" > "$DESTINO/.version-geoportal"
echo "GeoLibre ${VERSION} instalado en ${DESTINO} ($(du -sh "$DESTINO" | cut -f1), $(find "$DESTINO" -type f | wc -l) archivos)."
