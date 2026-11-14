import sys, json, urllib.request, urllib.parse
def get(doi):
    url="https://api.crossref.org/works/"+urllib.parse.quote(doi)
    req=urllib.request.Request(url,headers={"User-Agent":"bib-verifier/1.0"})
    try:
        d=json.load(urllib.request.urlopen(req,timeout=30))["message"]
    except Exception as e:
        return f"{doi}: ERROR {e}"
    au="; ".join(f"{a.get('family','')}, {a.get('given','')}" if 'family' in a else a.get('name','') for a in d.get('author',[]))
    yr=(d.get('published-print') or d.get('published-online') or d.get('issued'))['date-parts'][0]
    return f"{doi} | {d.get('type')} | {au} | {d.get('title',[''])[0]} | {(d.get('container-title') or [''])[0]} | {yr} | v{d.get('volume','')} n{d.get('issue','')} p{d.get('page', d.get('article-number',''))} | {d.get('publisher','')}"
for doi in sys.argv[1:]:
    print(get(doi)); print()
