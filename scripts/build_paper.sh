#!/usr/bin/env bash
# Compila paper/main.tex com TeX Live 2026 em contêiner (docker ou podman).
set -euo pipefail
cd "$(dirname "$0")/.."
python3 paper/tools/prep_bib.py
rm -rf paper/build
ENGINE=$(command -v docker >/dev/null && echo docker || echo podman)
$ENGINE run --rm -v "$PWD/paper:/w:Z" -w /w docker.io/texlive/texlive:latest-full \
  latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=build main.tex > paper/build.log 2>&1 \
  || { tail -40 paper/build.log; grep -n "^!" -A5 paper/build/main.log | head -40; exit 1; }
cp paper/build/main.pdf paper/tcc-2026.pdf
grep -E "Warning|Overfull|Underfull" paper/build/main.log | sed 's/ on input line.*//' | sort | uniq -c | sort -rn | head -25
echo "PDF: paper/tcc-2026.pdf ($(python3 -c "import re;print(re.search(rb'/Count (\d+)', open('paper/tcc-2026.pdf','rb').read()).group(1).decode())" 2>/dev/null || echo '?') páginas)"
