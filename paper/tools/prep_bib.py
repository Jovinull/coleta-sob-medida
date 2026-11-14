"""Gera paper/referencias.bib a partir de paper/references/referencias.bib.

O estilo sbc.bst ignora os campos doi e url. Para manter o estilo oficial
inalterado e ainda exibir identificadores verificáveis, este script copia o
DOI (ou, na falta dele, a URL) para o campo note de cada entrada.
"""
import re
import sys
from pathlib import Path

src = Path(sys.argv[1] if len(sys.argv) > 1 else "paper/references/referencias.bib")
dst = Path(sys.argv[2] if len(sys.argv) > 2 else "paper/referencias.bib")
# linhas de comentário são removidas: o BibTeX trata qualquer "@" como início
# de entrada, mesmo após "%"
text = "\n".join(l for l in src.read_text(encoding="utf-8").splitlines()
                 if not l.lstrip().startswith("%"))


def entries(t):
    i = 0
    while True:
        m = re.compile(r"@(\w+)\s*\{").search(t, i)
        if not m:
            return
        depth, j = 0, m.end() - 1
        while True:
            c = t[j]
            depth += c == "{"
            depth -= c == "}"
            j += 1
            if depth == 0:
                break
        yield t[i:m.start()], t[m.start():j]
        i = j


def field(e, name):
    m = re.search(rf"\b{name}\s*=\s*\{{", e)
    if not m:
        return None, None
    depth, j = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(e[j], 0)
        j += 1
    return e[m.end():j - 1], (m.start(), j)


out = ["% ARQUIVO GERADO por paper/tools/prep_bib.py — edite paper/references/referencias.bib\n"]
for pre, e in entries(text):
    out.append(pre)
    typ = re.match(r"@(\w+)", e).group(1).lower()
    doi, _ = field(e, "doi")
    url, _ = field(e, "url")
    how, _ = field(e, "howpublished")
    extra = None
    if doi:
        extra = f"\\doi{{{doi}}}"
    elif url and not how:
        extra = f"Dispon{{\\'\\i}}vel em: \\url{{{url}}}"
    if extra:
        note, span = field(e, "note")
        if note is None:
            e = e.rstrip()[:-1].rstrip().rstrip(",") + f",\n  note = {{{extra}}}\n}}"
        else:
            e = e[:span[0]] + f"note = {{{note}. {extra}}}" + e[span[1]:]
    out.append(e)
dst.write_text("".join(out) + "\n", encoding="utf-8")
print(f"{dst}: {sum(1 for _ in entries(text))} entradas")
