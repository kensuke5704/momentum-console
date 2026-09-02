#!/usr/bin/env python3
"""Compare a free SEC Form 13F institutional-breadth proxy with the frozen N-PORT Top80.

Research only. Downloads SEC's official structured 13F ZIPs, uses filing dates for
point-in-time availability, applies the production N-PORT breadth score formula to
13F manager holdings, then maps issuer names to tickers using the repository's
N-PORT issuer names / company profiles. No production files are modified.
"""
from __future__ import annotations
import csv,gzip,io,json,math,os,re,statistics,sys,time,urllib.request,zipfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
UA=os.environ.get("SEC_USER_AGENT","momentum-research/1.0 research@example.com")
START_YEAR=int(os.environ.get("OVERLAP_START_YEAR","2020")); END_YEAR=int(os.environ.get("OVERLAP_END_YEAR","2023")); TOP_N=int(os.environ.get("OVERLAP_TOP_N","80"))
CACHE=ROOT/".cache"/"sec-13f"; OUT=ROOT/"data"/"research"/"sec13f-nport-overlap.json"
BASE="https://www.sec.gov/files/structureddata/data/form-13f-data-sets"

def norm_name(s):
 s=(s or "").upper().replace("&"," AND "); s=re.sub(r"\b(CLASS|CL)\s+[A-Z0-9]+\b"," ",s); s=re.sub(r"\b(COMMON STOCK|COM STK|COMMON|ORDINARY SHARES?|ORD SHS?)\b"," ",s); s=re.sub(r"\b(INCORPORATED|INCORPORATION|INC|CORPORATION|CORP|COMPANY|CO|LIMITED|LTD|PLC|HOLDINGS?|HLDGS?|GROUP)\b"," ",s); s=re.sub(r"[^A-Z0-9]+"," ",s); return " ".join(s.split())
def req(url):
 r=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"*/*","Accept-Encoding":"identity"});
 with urllib.request.urlopen(r,timeout=120) as x:return x.read()
def sec_zip_links():
 # SEC structured 13F datasets use YYYYqN filenames through 2023. This pilot deliberately
 # stops there so it does not depend on scraping the SEC index page (which blocks some CI IPs).
 out=[]
 for y in range(max(2013,START_YEAR),min(2023,END_YEAR)+1):
  for q in range(1,5):
   if y==2013 and q<2:continue
   fn=f"{y}q{q}_form13f.zip"; out.append((f"{y} Q{q}",f"{BASE}/{fn}"))
 return out

def load_aliases():
 names=defaultdict(set); boot=ROOT/"data"/"sec-nport"/"bootstrap.json.gz"
 if boot.exists():
  with gzip.open(boot,"rt",encoding="utf-8") as f:obj=json.load(f)
  for filing in obj.get("snapshots") or obj.get("filings") or []:
   for h in filing.get("holdings",[]):
    sym=str(h.get("symbol") or "").strip().upper(); nm=norm_name(str(h.get("issuerName") or ""));
    if sym and nm:names[nm].add(sym)
 prof=ROOT/"public"/"data"/"company-profiles.json"
 if prof.exists():
  obj=json.loads(prof.read_text())
  for sym,p in (obj.get("profiles") or {}).items():
   nm=norm_name(str(p.get("companyName") or ""));
   if nm:names[nm].add(sym.upper())
 return {n:next(iter(s)) for n,s in names.items() if len(s)==1},{n:sorted(s) for n,s in names.items() if len(s)>1}
def open_tsv(z,wanted):
 found=next((n for n in z.namelist() if n.upper().endswith(wanted.upper())),None)
 if not found:raise RuntimeError(f"{wanted} not found; files={z.namelist()[:20]}")
 return io.TextIOWrapper(z.open(found),encoding="utf-8-sig",errors="replace",newline="")
def pick(row,*keys):
 u={k.upper():v for k,v in row.items()};
 for k in keys:
  if k.upper() in u:return u[k.upper()] or ""
 return ""
@dataclass
class Filing: accession:str; manager:str; filing_date:str; holdings:list

def parse_zip(path):
 with zipfile.ZipFile(path) as z:
  with open_tsv(z,"SUBMISSION.tsv") as f:
   meta={}
   for r in csv.DictReader(f,delimiter="\t"):
    acc=pick(r,"ACCESSION_NUMBER","ACCESSIONNUMBER");
    if not acc:continue
    cik=pick(r,"CIK","FILINGMANAGER_CIK","FILINGMANAGERCIK"); fd=pick(r,"FILING_DATE","FILINGDATE")[:10]; form=pick(r,"SUBMISSIONTYPE","FORM_TYPE","FORMTYPE").upper()
    if form and "13F" not in form:continue
    meta[acc]=(cik or acc,fd)
  hs=defaultdict(list)
  with open_tsv(z,"INFOTABLE.tsv") as f:
   for r in csv.DictReader(f,delimiter="\t"):
    acc=pick(r,"ACCESSION_NUMBER","ACCESSIONNUMBER")
    if acc not in meta or pick(r,"PUTCALL","PUT_CALL").strip():continue
    cusip=pick(r,"CUSIP").strip().upper(); issuer=pick(r,"NAMEOFISSUER","NAME_OF_ISSUER").strip()
    try:value=float(pick(r,"VALUE").replace(",","") or 0)
    except:value=0
    if cusip and issuer and value>0:hs[acc].append((cusip,issuer,value))
 return [Filing(acc,meta[acc][0],meta[acc][1],h) for acc,h in hs.items() if meta[acc][1]]
def history():return (json.loads((ROOT/"data"/"universe-history.json").read_text()).get("history") or [])
def build_13f(filings,asof,aliases):
 latest={}
 for f in filings:
  if f.filing_date<=asof:
   cur=latest.get(f.manager)
   if cur is None or (f.filing_date,f.accession)>(cur.filing_date,cur.accession):latest[f.manager]=f
 rows=defaultdict(lambda:{"managers":set(),"agg":0.,"max":0.,"rec":0.,"issuer":""}); asd=date.fromisoformat(asof)
 for f in latest.values():
  total=sum(v for _,_,v in f.holdings)
  if total<=0:continue
  rf=math.exp(-max(0,(asd-date.fromisoformat(f.filing_date)).days)/120); per=defaultdict(float); issuer={}
  for c,n,v in f.holdings:per[c]+=v; issuer[c]=n
  for c,v in per.items():
   w=100*v/total; r=rows[c]; r["managers"].add(f.manager); r["agg"]+=w; r["max"]=max(r["max"],w); r["rec"]+=w*rf; r["issuer"]=issuer[c]
 ranked=[]
 for c,r in rows.items():
  cnt=len(r["managers"])
  if cnt<2 and r["max"]<4:continue
  score=3*math.log1p(cnt)+.5*math.log1p(r["agg"])+.5*math.log1p(r["rec"]); nm=norm_name(r["issuer"])
  ranked.append({"cusip":c,"issuer":r["issuer"],"symbol":aliases.get(nm),"managerCount":cnt,"aggregateWeight":r["agg"],"maxWeight":r["max"],"recencyWeight":r["rec"],"score":score})
 ranked.sort(key=lambda x:(-x["score"],-x["managerCount"],-x["aggregateWeight"],x["cusip"])); top=ranked[:TOP_N]; return top,[x["symbol"] for x in top if x["symbol"]]
def main():
 CACHE.mkdir(parents=True,exist_ok=True); OUT.parent.mkdir(parents=True,exist_ok=True); aliases,amb=load_aliases(); print(f"aliases unique={len(aliases)} ambiguous={len(amb)}")
 links=sec_zip_links(); print(f"SEC datasets selected={len(links)}"); filings=[]
 for i,(label,url) in enumerate(links,1):
  p=CACHE/url.rsplit("/",1)[-1]
  if not p.exists():
   print(f"download {i}/{len(links)} {label}",flush=True)
   try:p.write_bytes(req(url))
   except Exception as e:print(f"WARN download failed {url}: {e}",file=sys.stderr);continue
   time.sleep(.15)
  try:
   fs=parse_zip(p); filings.extend(fs); print(f"parsed {p.name}: filings={len(fs)} total={len(filings)}",flush=True)
  except Exception as e:print(f"WARN parse failed {p.name}: {e}",file=sys.stderr)
 if not filings:raise RuntimeError("No SEC 13F filings could be downloaded/parsed")
 hist=history(); np={x["signalMonth"]:[s["symbol"] for s in x.get("symbols",[])[:TOP_N]] for x in hist}; results=[]
 for x in hist:
  y=int(x["signalMonth"][:4]);
  if not START_YEAR<=y<=END_YEAR:continue
  top,syms=build_13f(filings,x["asOf"],aliases); target=np[x["signalMonth"]]; a,b=set(syms),set(target); overlap=len(a&b)
  results.append({"month":x["signalMonth"],"asOf":x["asOf"],"nportCount":len(target),"raw13fTopCount":len(top),"mapped13fTopCount":len(syms),"mappingCoverageTop80":len(syms)/TOP_N,"intersection":overlap,"overlapVsNport":overlap/len(b) if b else None,"jaccardOnMapped":overlap/len(a|b) if a|b else None,"mapped13fTopSymbols":syms,"nportSymbols":target,"unmatched13fTop":[{k:t[k] for k in ("cusip","issuer","managerCount","score")} for t in top if not t["symbol"]][:20]}); print(f"{x['signalMonth']} mapped={len(syms)}/{TOP_N} overlap={overlap}/{len(target)}")
 cov=[r["mappingCoverageTop80"] for r in results]; ov=[r["overlapVsNport"] for r in results if r["overlapVsNport"] is not None]
 summary={"method":"Free SEC 13F institutional-breadth proxy vs production N-PORT Top80; filing-date point-in-time; same breadth score formula; issuer-name ticker mapping; unmapped top ranks are not promoted.","period":{"startYear":START_YEAR,"endYear":END_YEAR},"secDatasetCount":len(links),"filingsParsed":len(filings),"aliasCount":len(aliases),"months":len(results),"mappingCoverageTop80":{"mean":statistics.mean(cov) if cov else None,"median":statistics.median(cov) if cov else None,"min":min(cov) if cov else None},"overlapVsNport":{"mean":statistics.mean(ov) if ov else None,"median":statistics.median(ov) if ov else None,"min":min(ov) if ov else None,"max":max(ov) if ov else None},"results":results,"limitations":["13F manager population is broader than eligible thematic N-PORT ETF population.","Structured SEC 13F files begin in 2013; pre-2013 requires legacy EDGAR text parsing.","Ambiguous issuer names remain unmapped, making overlap estimates conservative when mapping coverage is incomplete."]}
 OUT.write_text(json.dumps(summary,indent=2)+"\n"); print("SUMMARY",json.dumps({k:v for k,v in summary.items() if k!="results"})); print(f"wrote {OUT}")
if __name__=="__main__":main()
