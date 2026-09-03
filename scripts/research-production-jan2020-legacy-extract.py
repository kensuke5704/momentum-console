#!/usr/bin/env python3
from __future__ import annotations
import json,re,urllib.request,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/production-jan2020-legacy-extract.json'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,text/html,*/*'}
SOURCES=[
 {'seriesId':'S000057700','seriesName':'ClearBridge Large Cap Growth ESG ETF','reportDate':'2019-02-28','filingDate':'2019-04-19','url':'https://www.sec.gov/Archives/edgar/data/1645194/000119312519113628/d717725dnq.htm','grammar':'name_shares_value'},
 {'seriesId':'S000061208','seriesName':'PPTY - U.S. Diversified Real Estate ETF','reportDate':'2019-08-31','filingDate':'2019-11-07','url':'https://www.sec.gov/Archives/edgar/data/1540305/000089853119000551/pptyusdreetf-ncsrs.htm','grammar':'shares_name_value'},
]

def get(url):
 last=None
 for u in ('https://r.jina.ai/'+url,url):
  try:
   req=urllib.request.Request(u,headers=UA)
   with urllib.request.urlopen(req,timeout=30) as r:return r.read(4_000_000).decode('utf-8','replace'),u
  except Exception as e:last=e;time.sleep(.4)
 raise last

def clean(s):
 s=s.replace('**','').replace('_','').replace('$',' ').replace('–','-').replace('—','-')
 s=re.sub(r'\*+$','',s.strip())
 return ' '.join(s.split())

def num(s):return float(s.replace(',',''))

def norm_desc(s):
 s=clean(s)
 s=re.sub(r'\s+Shares\s*$','',s,flags=re.I)
 s=re.sub(r'\s*\([a-z0-9 ]+\)\s*$','',s,flags=re.I)
 return s.strip(' .')

def parse_lrge(text):
 lines=text.splitlines();inside=False;rows=[];net_assets=None
 for raw in lines:
  line=clean(raw)
  if re.search(r'^COMMON STOCKS\s*-\s*99\.5%',line,re.I):inside=True;continue
  if inside and re.search(r'^SHORT-TERM INVESTMENTS\b|^TOTAL INVESTMENTS BEFORE SHORT-TERM',line,re.I):inside=False
  if re.search(r'TOTAL NET ASSETS\s*-\s*100\.0%',line,re.I):
   m=re.search(r'([\d,]+)\s*$',line);net_assets=num(m.group(1)) if m else net_assets
  if not inside or not line:continue
  if re.search(r'\s-\s*\d+(?:\.\d+)?%$',line) or line.upper().startswith('TOTAL '):continue
  # Last two numeric groups are shares and market value. Legal names may contain digits,
  # so anchor only from the right edge.
  m=re.match(r'^(.*?)([\d,]+)\s+([\d,]+)\s*$',line)
  if not m:
   # SEC rendering can place value immediately after shares with no whitespace around $.
   m=re.match(r'^(.*?)([\d,]+)\s*([\d,]+)\s*$',line)
  if not m:continue
  desc=norm_desc(m.group(1));shares=num(m.group(2));value=num(m.group(3))
  if not desc or shares<=0 or value<=0:continue
  rows.append({'description':desc,'shares':shares,'value':value})
 return dedupe(rows),net_assets

def parse_ppty(text):
 lines=text.splitlines();inside=False;rows=[];net_assets=None
 for raw in lines:
  line=clean(raw)
  if re.match(r'^COMMON STOCKS\s*-\s*99\.8%',line,re.I):inside=True;continue
  if inside and re.match(r'^TOTAL COMMON STOCKS\b',line,re.I):inside=False
  if re.match(r'^NET ASSETS\s*-\s*100\.0%',line,re.I):
   m=re.search(r'([\d,]+)\s*$',line);net_assets=num(m.group(1)) if m else net_assets
  if not inside or not line:continue
  if re.search(r'\s-\s*\d+(?:\.\d+)?%(?:\s*\(Continued\))?$',line,re.I):continue
  # Row starts with shares and ends with market value; everything in between is issuer description.
  m=re.match(r'^([\d,]+)\s+(.+?)([\d,]+)\s*$',line)
  if not m:continue
  shares=num(m.group(1));desc=norm_desc(m.group(2));value=num(m.group(3))
  if not desc or shares<=0 or value<=0:continue
  # Reject subtotal-only middle fragments which contain no alphabetic issuer text.
  if not re.search(r'[A-Za-z]',desc):continue
  rows.append({'description':desc,'shares':shares,'value':value})
 return dedupe(rows),net_assets

def dedupe(rows):
 # Different share classes are distinct descriptions; only exact duplicate rendered rows collapse.
 out=[];seen=set()
 for r in rows:
  k=(r['description'],r['shares'],r['value'])
  if k not in seen:seen.add(k);out.append(r)
 return out

def main():
 records=[]
 for src in SOURCES:
  text,tr=get(src['url'])
  rows,net=parse_lrge(text) if src['grammar']=='name_shares_value' else parse_ppty(text)
  if not net:raise RuntimeError(f"{src['seriesId']}: net assets not found")
  holdings=[{**r,'weight':100*r['value']/net} for r in rows]
  holdings.sort(key=lambda x:-x['weight'])
  total=sum(x['weight'] for x in holdings);top10=sum(x['weight'] for x in holdings[:10])
  eligible=10<=len(holdings)<=120 and total>=50 and top10>=25
  rec={**src,'transport':tr,'netAssets':net,'holdingCount':len(holdings),'holdingWeightTotal':total,'top10Weight':top10,'productionStructuralEligibility':eligible,'holdings':holdings}
  records.append(rec)
  print('EXTRACT',json.dumps({k:v for k,v in rec.items() if k!='holdings'}),flush=True)
  for h in holdings[:10]:print('TOP',json.dumps({'seriesId':src['seriesId'],**h}),flush=True)
 out={'purpose':'Structural extraction only for two metadata-preregistered nearest legacy sources used in the January 2020 hybrid transition shadow. Parser rules use document layout only; no Production holdings, overlap, universe ranks, or returns used.','records':records}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
