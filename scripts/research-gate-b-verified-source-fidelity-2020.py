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
NUM=re.compile(r'^\$?\(?[\d,]+(?:\.\d+)?\)?(?:\s*\*)?$')
STOP=re.compile(r'\b(SHORT[- ]TERM INVESTMENTS?|MONEY MARKET|REPURCHASE|TOTAL INVESTMENTS|NET ASSETS|STATEMENT OF ASSETS)\b',re.I)
MARKUP=re.compile(r'[*_]+')

def clean(s):return re.sub(r'\s+',' ',s or '').strip()
def plain(s):return clean(MARKUP.sub('',s or ''))
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

def schedule_segment(text,series):
 lines=text.splitlines()
 # Start at the first real schedule marker that is followed by the exact series title and an investments header,
 # not the table-of-contents reference.
 for i,x in enumerate(lines):
  if not re.search(r'SCHEDULE OF INVESTMENTS|PORTFOLIO OF INVESTMENTS',x,re.I):continue
  window='\n'.join(lines[i:min(len(lines),i+20)])
  if series.lower() in window.lower() and re.search(r'COMMON STOCK|SECURITY\s+SHARES\s+VALUE|SHARES\s+SECURITY DESCRIPTION',window,re.I):
   return lines[i:min(len(lines),i+5000)]
 starts=[i for i,x in enumerate(lines) if series.lower() in x.lower()]
 return lines[starts[-1] if starts else 0:min(len(lines),(starts[-1] if starts else 0)+5000)]

def parse_compact_inline(seg):
 """ClearBridge r.jina grammar: issuer and two numeric cells compressed onto one line."""
 rows=[];in_common=False
 # Description can touch shares without whitespace: Walt Disney Co.35,446$4,680,290
 pat=re.compile(r'^(.*?\D)(\d[\d,]*)\s*\$?\s*(\d[\d,]*)(?:\s*\*)?$')
 for raw in seg:
  line=plain(raw)
  if re.search(r'\bCOMMON STOCKS?\b',line,re.I):in_common=True;continue
  if in_common and STOP.search(line):break
  if not in_common:continue
  if re.search(r'\bTOTAL\b|\d+(?:\.\d+)?\s*%$',line,re.I):continue
  m=pat.match(line)
  if not m:continue
  desc=clean(m.group(1)).strip(' .')
  if desc and len(desc)>2 and not re.match(r'^(TOTAL|COMMON STOCK|SECURITY)',desc,re.I):rows.append(desc)
 return rows

def parse_four_line(seg):
 """PPTY r.jina grammar: shares line -> issuer line -> optional $ line -> value line."""
 rows=[];in_common=False;i=0
 while i<len(seg):
  line=plain(seg[i])
  if re.search(r'\bCOMMON STOCKS?\b',line,re.I):in_common=True;i+=1;continue
  if in_common and STOP.search(line):break
  if not in_common:i+=1;continue
  if re.fullmatch(r'\d[\d,]*',line):
   shares=line;j=i+1;parts=[]
   while j<len(seg) and len(parts)<5:
    q=plain(seg[j]);j+=1
    if not q:continue
    parts.append(q)
   if parts:
    issuer=parts[0]
    rest=parts[1:]
    # issuer must be textual and a later token must be a numeric value; optional standalone '$' is ignored.
    value_found=any(re.fullmatch(r'\$?\d[\d,]*',q) for q in rest if q!='$')
    if (value_found and re.search(r'[A-Za-z]',issuer) and not re.search(r'\d+(?:\.\d+)?\s*%$|^(TOTAL|COMMON STOCK|SHARES|SECURITY DESCRIPTION)',issuer,re.I)):
     rows.append(issuer);i=j;continue
  i+=1
 return rows

def parse_spaced(seg):
 rows=[];in_common=False
 for raw in seg:
  line=plain(raw)
  if re.search(r'\bCOMMON STOCKS?\b',line,re.I):in_common=True;continue
  if in_common and STOP.search(line):break
  if not in_common:continue
  cells=[plain(c) for c in re.split(r'\t+|\s{3,}',raw) if plain(c) not in {'','$','—','-'}]
  nums=[i for i,c in enumerate(cells) if NUM.match(c)]
  if len(nums)>=2:
   first,last=nums[0],nums[-1]
   desc=' '.join(cells[1:last]) if first==0 else ' '.join(cells[:first])
   desc=clean(desc).strip(' .')
   if desc and not re.match(r'^(TOTAL|COMMON STOCK)',desc,re.I):rows.append(desc)
 return rows

def parse_rows(text,series):
 seg=schedule_segment(text,series)
 candidates=[('compact_inline',parse_compact_inline(seg)),('four_line',parse_four_line(seg)),('spaced',parse_spaced(seg))]
 plausible=[x for x in candidates if 5<=len(set(x[1]))<=250]
 grammar,rows=max(plausible or candidates,key=lambda x:len(set(x[1])))
 return grammar,list(dict.fromkeys(x for x in rows if norm(x)))

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
   text,tr=get(s['sourceDocumentUrl']);grammar,legacy=parse_rows(text,s['seriesName']);ln={norm(x) for x in legacy}
   nport=[h for h in nf.get('holdings',[]) if h.get('issuerName')]
   matched=[];unmatched=[]
   for h in nport:
    n=norm(h['issuerName']);ok=n in ln or any((len(n)>=8 and len(x)>=8 and (n.startswith(x) or x.startswith(n))) for x in ln)
    (matched if ok else unmatched).append(h)
   gap=(date.fromisoformat(nf['reportDate'])-date.fromisoformat(s['sourceReportDate'])).days
   totalw=sum(float(h.get('weight') or 0) for h in nport);mw=sum(float(h.get('weight') or 0) for h in matched)
   r.update({'status':'PARSED' if legacy else 'PARSE_EMPTY','parserGrammar':grammar,'transport':tr,'daysBetweenReports':gap,'legacyParsedHoldings':len(legacy),'nportFilteredHoldings':len(nport),'nportRetainedCount':len(matched),'nportRetentionRate':len(matched)/len(nport) if nport else None,'nportRetainedWeightRate':mw/totalw if totalw else None,'legacySample':legacy[:20],'unmatchedNport':[{'issuer':h.get('issuerName'),'symbol':h.get('symbol'),'weight':h.get('weight')} for h in unmatched]})
  except Exception as e:r.update({'status':'ERROR','error':repr(e)})
  outrows.append(r);print('PAIR',json.dumps(r),flush=True)
 out={'purpose':'Source-fidelity audit for already verified complete pre-Production holdings reports of actual 2020-01 Production source series. Source selection was frozen before overlap results. Parser grammars are structural and based on observed SEC rendering: compact inline issuer/shares/value, four-line shares/issuer/$/value, and fixed-width table. No strategy returns used.','rows':outrows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
