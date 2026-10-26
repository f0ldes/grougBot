#!/bin/sh
# Starts mangosd or realmd. Settings come from Mangosd_* / Realmd_* env vars (see docker-compose.yml).
set -e

ETC=/opt/cmangos/etc

case "$1" in
  mangosd|realmd)
    [ -f "$ETC/$1.conf" ] || cp "$ETC/$1.conf.dist" "$ETC/$1.conf"
    exec "/opt/cmangos/bin/$1" -c "$ETC/$1.conf"
    ;;
  *)
    exec "$@"
    ;;
esac
