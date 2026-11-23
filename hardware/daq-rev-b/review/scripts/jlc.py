import json, subprocess, sys
UA="Mozilla/5.0"
def detail(code):
    out=subprocess.run(["curl","-s","-m","25","-A",UA,f"https://cart.jlcpcb.com/shoppingCart/smtGood/getComponentDetail?componentCode={code}"],capture_output=True,text=True).stdout
    try: d=json.loads(out)["data"]
    except Exception: return {"code":code,"err":out[:200]}
    if not d: return {"code":code,"err":"nodata"}
    keys={k:d.get(k) for k in ["componentCode","componentModelEn","componentBrandEn","componentSpecificationEn","stockCount","componentLibraryType","describe","preferredComponentFlag"]}
    pr=d.get("prices") or d.get("jlcPrices") or []
    keys["price1"]=pr[0].get("productPrice") if pr else None
    return keys
def search(kw, n=10):
    body=json.dumps({"keyword":kw,"currentPage":1,"pageSize":n,"searchType":2})
    out=subprocess.run(["curl","-s","-m","25","-A",UA,"-H","Content-Type: application/json","-X","POST","-d",body,"https://cart.jlcpcb.com/shoppingCart/smtGood/selectSmtComponentList"],capture_output=True,text=True).stdout
    try:
        lst=json.loads(out)["data"]["componentPageInfo"]["list"]
    except Exception: return out[:300]
    return [{k:x.get(k) for k in ["componentCode","componentModelEn","componentSpecificationEn","stockCount","componentLibraryType","describe"]} for x in lst]
if __name__=="__main__":
    if sys.argv[1]=="d":
        for c in sys.argv[2:]: print(json.dumps(detail(c)))
    else:
        for r in search(" ".join(sys.argv[2:])) if True else []: print(r)
