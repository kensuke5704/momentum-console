#!/usr/bin/env python3
from __future__ import annotations
import gzip,json,re,urllib.request
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MAN=ROOT/'data/research/gate-b-production-source-manifest-2020.json'
BOOT=ROOT/'data/sec-nport/bootstrap.json.gz'
OUT=ROOT/'data/research/gate-b-verified-source-fidelity-2020.json'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,text/html,*/*'}

SUFFIX=re.compile(r'\b(INCORPORATED|INC|CORPORATION|CORP|COMPANY|CO|LIMITED|LTD|PLC|CLASS [A-Z])\b',re.I)
FOOT=re.compile(r'\s*\([^)]{1,12}\)\s*$')

def norm(s):
 s=FOOT.sub('',s or '').upper().replace('&',' AND ')
 s=SUFFIX.sub(' ',s);s=re.sub(r'[^A-Z0-9]+',' ',s)
 return ' '.join(s.split())

def get(url):
 last=None
 for u in ('https://r.jina.ai/'+url,url):
  try:
   req=urllib.request.Request(u,headers=UA)
   with urllib.request.urlopen(req,timeout=35) as r:return r.read(8_000_000).decode('utf-8','replace'),u
  except Exception as e:last=repr(e)
 raise RuntimeError(last or 'fetch failed')

def parse_rows(text,series):
 # Structural generic parser for rendered SEC tables: issuer description followed by shares/value,
 # or shares then description/value. Only explicit common-stock section is read.
 lines=text.splitlines();starts=[i for i,x in enumerate(lines) if series.lower() in x.lower()]
 start=starts[-1] if starts else 0
 # Prefer title occurrence followed by schedule/investments in nearby window.
 for i in starts:
  if re.search(r'SCHEDULE OF INVESTMENTS|PORTFOLIO OF INVESTMENTS', '\n'.join(lines[i:min(len(lines),i+35)]), re.I):start=i;break
 seg=lines[start:min(len(lines),start+4000)]
 rows=[];in_common=False
 for raw in seg:
  line=' '.join(raw.split())
  if re.search(r'\bCOMMON STOCKS?\b',line,re.I):in_common=True;continue
  if in_common and re.search(r'\b(PREFERRED|SHORT[- ]TERM|MONEY MARKET|REPURCHASE|TOTAL INVESTMENTS|NET ASSETS)\b',line,re.I):
   if not re.search(r'COMMON STOCK',line,re.I):in_common=False
  if not in_common:continue
  cells=[re.sub(r'\s+',' ',c).strip() for c in re.split(r'\t+|\s{3,}',raw) if c.strip() not in {'','$','—','-'}]
  nums=[(j,c) for j,c in enumerate(cells) if re.fullmatch(r'\$?\(?[\d,]+(?:\.\d+)?\)?',c)]
  if len(nums)>=2:
   # name-first or shares-first layouts
   if nums[0][0]>0:desc=' '.join(cells[:nums[0][0]])
   elif len(cells)>2:desc=' '.join(cells[1:nums[-1][0]])
   else:continue
   desc=desc.strip(' .')
   if len(desc)>2 and not re.match(r'^(TOTAL|COMMON STOCK)',desc,re.I):rows.append(desc)
 # Fallback for markdown table rendering: | issuer | shares | value |
 if len(rows)<5:
  rows=[];in_common=False
  for raw in seg:
   line=' '.join(raw.split())
   if re.search(r'\bCOMMON STOCKS?\b',line,re.I):in_common=True;continue
   if in_common and re.search(r'\b(PREFERRED|SHORT[- ]TERM|MONEY MARKET|REPURCHASE|TOTAL INVESTMENTS|NET ASSETS)\b',line,re.I):in_common=False
   if not in_common:continue
   cells=[c.strip() for c in raw.split('|') if c.strip()]
   nums=[i for i,c in enumerate(cells) if re.fullmatch(r'\$?\(?[\d,]+(?:\.\d+)?\)?',c)]
   if len(nums)>=2:
    desc=' '.join(cells[:nums[0]]).strip()
    if desc and not re.match(r'^(TOTAL|COMMON STOCK)',desc,re.I):rows.append(desc)
 return list(dict.fromkeys(x for x in rows if norm(x)))

def fuzzy_alias(n):
 # Conservative equivalence only: normalized exact or prefix relation caused by N-PORT issuer truncation.
 return n

def main():
 man=json.loads(MAN.read_text())
 with gzip.open(BOOT,'rt',encoding='utf-8') as fh:b=json.load(fh)
 filings=b.get('snapshots',b) if isinstance(b,dict) else b
 first={}
 for f in sorted(filings,key=lambda x:(x.get('reportDate',''),x.get('filingDate',''),x.get('accession',''))):
  sid=f.get('seriesId')
  if sid and sid not in first:first[sid]=f
 outrows=[]
 for s in man['sources']:
  if s.get('status')!='VERIFIED_COMPLETE_HOLDINGS':continue
  nf=first.get(s['seriesId']);r={'seriesId':s['seriesId'],'seriesName':s['seriesName'],'sourceReportDate':s['sourceReportDate'],'sourceForm':s['sourceForm']}
  try:
   text,tr=get(s['sourceDocumentUrl']);legacy=parse_rows(text,s['seriesName']);ln={norm(x) for x in legacy}
   nport=[h for h in nf.get('holdings',[]) if h.get('issuerName')]
   matched=[];unmatched=[]
   for h in nport:
    n=norm(h['issuerName']);ok=n in ln or any((len(n)>=8 and (n.startswith(x) or x.startswith(n))) for x in ln if len(x)>=8)
    (matched if ok else unmatched).append(h)
   gap=(date.fromisoformat(nf['reportDate'])-date.fromisoformat(s['sourceReportDate'])).days
   totalw=sum(float(h.get('weight') or 0) for h in nport);mw=sum(float(h.get('weight') or 0) for h in matched)
   r.update({'status':'PARSED' if legacy else 'PARSE_EMPTY','transport':tr,'daysBetweenReports':gap,'legacyParsedHoldings':len(legacy),'nportFilteredHoldings':len(nport),'nportRetainedCount':len(matched),'nportRetentionRate':len(matched)/len(nport) if nport else None,'nportRetainedWeightRate':mw/totalw if totalw else None,'unmatchedNport':[{'issuer':h.get('issuerName'),'symbol':h.get('symbol'),'weight':h.get('weight')} for h in unmatched]})
  except Exception as e:r.update({'status':'ERROR','error':repr(e)})
  outrows.append(r);print('PAIR',json.dumps(r),flush=True)
 out={'purpose':'Source-fidelity audit for the already verified complete pre-Production holdings reports of actual 2020-01 Production source series. Source selection was frozen before these overlap results. No strategy returns used.','rows':outrows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
