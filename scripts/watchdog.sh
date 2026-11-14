#!/usr/bin/env bash
# Vigia o broker MQTT local (127.0.0.1:1883) e o painel (127.0.0.1:8050) e os
# reinicia se ficarem fora do ar por 3 verificações seguidas (~60 s). A
# tolerância evita reagir a reinícios intencionais (teste T3 do E6).
# Pausa: crie o arquivo .watchdog-pause na raiz do projeto.
# Uso: nohup setsid scripts/watchdog.sh >/dev/null 2>&1 &
set -uo pipefail
cd "$(dirname "$0")/.."
LOG=logs/watchdog.log
mkdir -p logs
up() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }
log() { echo "$(date '+%F %T') $*" >> "$LOG"; }
fb=0; fd=0
log "watchdog iniciado (pid $$)"
while true; do
  if [ ! -e .watchdog-pause ]; then
    if up 1883; then fb=0; else fb=$((fb + 1)); fi
    if up 8050; then fd=0; else fd=$((fd + 1)); fi
    if [ "$fb" -ge 3 ]; then
      log "broker fora do ar; reiniciando"
      scripts/broker.sh start >> "$LOG" 2>&1 || log "falha ao iniciar o broker"
      fb=0
    fi
    if [ "$fd" -ge 3 ]; then
      log "painel fora do ar; reiniciando"
      nohup ./.venv/bin/uvicorn dashboard.app:app --host 127.0.0.1 --port 8050 >> logs/painel.log 2>&1 &
      fd=0
    fi
  fi
  sleep 20
done
