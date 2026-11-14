#!/usr/bin/env bash
# Gera paper/overleaf-tcc-2026.zip, importável no Overleaf (New Project → Upload Project).
# Inclui fontes, figuras, TikZ, tabelas/macros geradas e o .bib já pré-processado.
set -euo pipefail
cd "$(dirname "$0")/../paper"
python3 tools/prep_bib.py references/referencias.bib referencias.bib >/dev/null
rm -f overleaf-tcc-2026.zip
zip -qr overleaf-tcc-2026.zip main.tex sbc-template.sty sbc.bst referencias.bib \
  sections tikz figures resultados -x '*.aux' -x '*.log'
unzip -l overleaf-tcc-2026.zip | tail -1
echo "paper/overleaf-tcc-2026.zip (compilador: pdfLaTeX; arquivo principal: main.tex)"
