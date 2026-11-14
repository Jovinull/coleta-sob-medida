import sys, json, urllib.request, urllib.parse
for doi in sys.argv[1:]:
    url="https://api.openalex.org/works/doi:"+doi
    try:
        d=json.load(urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"bib-verifier/1.0"}),timeout=30))
    except Exception as e:
        print(doi,"ERR",e); continue
    inv=d.get("abstract_inverted_index") or {}
    pos=[]
    for w,ps in inv.items():
        for p in ps: pos.append((p,w))
    ab=" ".join(w for p,w in sorted(pos))
    oa=d.get("open_access",{})
    print(f"## {doi} | cited {d.get('cited_by_count')} | OA {oa.get('is_oa')} {oa.get('oa_url')}")
    print(ab[:1600]); print()
