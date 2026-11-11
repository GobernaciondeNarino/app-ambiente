#!/usr/bin/env bash
# Genera el paquete para subir a Plesk (u otro hosting con PHP y MySQL):
#   dist/geoportal-plesk-<versión>.zip  →  carpeta «geoportal/» lista para extraer en httpdocs
# Uso: scripts/empaquetar-plesk.sh [versión]
set -euo pipefail
cd "$(dirname "$0")/.."
VERSION="${1:-$(sed -n "s/^const GP_VERSION = '\(.*\)';/\1/p" portal/api/lib/nucleo.php)}"
DESTINO="dist/geoportal-plesk-${VERSION}.zip"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p dist "$TMP/geoportal"
# Solo los archivos versionados de portal/ (sin config.php, datos ni archivos locales)
git archive --format=tar HEAD portal | tar -x -C "$TMP"
cp -a "$TMP/portal/." "$TMP/geoportal/"
rm -rf "$TMP/portal"
cat > "$TMP/geoportal/LEAME-INSTALACION.txt" <<TXT
Geoportal Ambiental — Gobernación de Nariño · versión ${VERSION}

1. En Plesk cree una base de datos MySQL (Sitios web y dominios → Bases de datos).
2. Suba este ZIP con el Administrador de archivos a httpdocs (o a la subcarpeta que
   prefiera) y use «Extraer archivos». Se crea la carpeta «geoportal».
   Puede renombrarla o mover su contenido a httpdocs para instalar en la raíz.
3. Abra https://<su-dominio>/geoportal/instalar/ y siga el asistente.

Guía completa: docs/instalacion-plesk.md en el repositorio.
TXT
rm -f "$DESTINO"
(cd "$TMP" && zip -qr -X "$OLDPWD/$DESTINO" geoportal)
echo "Paquete generado: $DESTINO ($(du -h "$DESTINO" | cut -f1))"
