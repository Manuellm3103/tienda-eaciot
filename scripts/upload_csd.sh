#!/usr/bin/env bash
# Sube el CSD (cer + key) UNA vez al volumen persistente del contenedor.
# Uso:
#   bash scripts/upload_csd.sh <contenedor> [dir_csd]
# Ejemplos:
#   Docker local:        bash scripts/upload_csd.sh tienda-smoke
#   Nixopus (vía SSH/terminal):  bash scripts/upload_csd.sh "$(docker ps -q --filter name=tienda)"
#
# El .env de producción apunta CSD_CERT_PATH/CSD_KEY_PATH a /data/csd/.
set -e

CONTAINER="${1:?Uso: bash scripts/upload_csd.sh <contenedor>}"
SRC="${2:-csd}"

CERT_SRC="$SRC/CSD EAC240318.cer"
KEY_SRC="$SRC/CSD_EMANUEL_AZUR_CORP_EAC2403183F0_20241019_012905.key"

if [ ! -f "$CERT_SRC" ]; then echo "No encuentro $CERT_SRC"; exit 1; fi
if [ ! -f "$KEY_SRC" ]; then echo "No encuentro $KEY_SRC"; exit 1; fi

docker exec "$CONTAINER" mkdir -p /data/csd
docker cp "$CERT_SRC" "$CONTAINER:/data/csd/CSD.cer"
docker cp "$KEY_SRC"  "$CONTAINER:/data/csd/CSD.key"
echo "CSD subido a $CONTAINER:/data/csd/ (persistente en el volumen /data)."
echo "Reinicia el contenedor para que la app relea la configuración:"
echo "  docker restart $CONTAINER"
