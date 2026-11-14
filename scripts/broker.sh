#!/usr/bin/env bash
# Inicia/para o broker Mosquitto local (docker ou podman).
# Uso: scripts/broker.sh start|stop|restart|status
set -euo pipefail
cd "$(dirname "$0")/.."
ENGINE=$(command -v docker >/dev/null && echo docker || echo podman)
NAME=residuos-mosquitto
IMG=docker.io/library/eclipse-mosquitto:2.0.20
case "${1:-start}" in
  start)
    $ENGINE rm -f $NAME >/dev/null 2>&1 || true
    $ENGINE run -d --name $NAME -p 127.0.0.1:1883:1883 \
      -v "$PWD/mqtt/mosquitto.conf:/mosquitto/config/mosquitto.conf:ro,Z" $IMG >/dev/null
    for _ in $(seq 1 50); do
      (exec 3<>/dev/tcp/127.0.0.1/1883) 2>/dev/null && { echo "broker pronto em 127.0.0.1:1883"; exit 0; }
      sleep 0.2
    done
    echo "broker não respondeu" >&2; exit 1 ;;
  stop) $ENGINE rm -f $NAME >/dev/null && echo parado ;;
  restart) $ENGINE restart $NAME >/dev/null && echo reiniciado ;;
  status) $ENGINE ps --filter name=$NAME ;;
esac
