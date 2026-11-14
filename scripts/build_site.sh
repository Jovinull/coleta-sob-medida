#!/usr/bin/env bash
# Monta o site do GitHub Pages em _site/ a partir de site/ e dos artefatos do
# repositório (figuras, animações, artigo e painel em modo estático).
# Uso: scripts/build_site.sh [destino]   (padrão: _site)
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="${1:-_site}"
rm -rf "$OUT"
mkdir -p "$OUT"
cp -r site/. "$OUT/"
mkdir -p "$OUT/assets/fig" "$OUT/assets/anim" "$OUT/assets/docs"
cp figures/*.png figures/screenshots/*.png "$OUT/assets/fig/"
cp animations/*.mp4 "$OUT/assets/anim/"
cp paper/tcc-2026.pdf paper/overleaf-tcc-2026.zip "$OUT/assets/docs/"

# Painel em modo estático: os endpoints /api/* viram arquivos JSON.
P="$OUT/painel"
mkdir -p "$P/static" "$P/api"
cp dashboard/static/app.js dashboard/static/style.css "$P/static/"
sed -e 's#<script src="static/app.js"></script>#<script>window.PAINEL_ESTATICO = true;</script>\n<script src="static/app.js"></script>#' \
    -e 's#<small>Plataforma de simulação#<small><a href="../" target="_top" style="color:inherit">← site do projeto</a> · Plataforma de simulação#' \
    dashboard/static/index.html > "$P/index.html"
cp data/aracaju/roads.json "$P/api/roads.json"
cp experiments/results/replay.json "$P/api/replay.json"
cp experiments/results/dashboard.json "$P/api/results.json"
cp live/state.json "$P/api/state.json"
echo "[]" > "$P/api/events.json"

touch "$OUT/.nojekyll"
du -sh "$OUT" | awk '{print "site montado em '"$OUT"' (" $1 ")"}'
