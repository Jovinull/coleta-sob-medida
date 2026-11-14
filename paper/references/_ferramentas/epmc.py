import sys, json, urllib.request, urllib.parse, re
for doi in sys.argv[1:]:
    q=urllib.parse.quote(f'DOI:"{doi}"')
    url=f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={q}&format=json&resultType=core"
    try:
        r=json.load(urllib.request.urlopen(url,timeout=30))["resultList"]["result"]
    except Exception as e:
        print(doi,"ERR",e); continue
    if not r: print("##",doi,"NOT FOUND\n"); continue
    a=r[0]; ab=re.sub("<[^>]+>","",a.get("abstractText",""))
    print("##",doi,"|",a.get("title"),"|",a.get("pmid")); print(ab[:2000]); print()
