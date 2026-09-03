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

FOOT=re.compile(r'\s*\([^)]{1,12}\)\s*$')
NUM=re.compile(r'^\$?\(?[\d,]+(?:\.\d+)?\)?(?:\s*\*)?$')
STOP=re.compile(r'\b(SHORT[- ]TERM INVESTMENTS?|MONEY MARKET|REPURCHASE|TOTAL INVESTMENTS|NET ASSETS|STATEMENT OF ASSETS)\b',re.I)
MARKUP=re.compile(r'[*_]+')
MONTHS={'JANUARY','FEBRUARY','MARCH','APRIL','MAY','JUNE','JULY','AUGUST','SEPTEMBER','OCTOBER','NOVEMBER','DECEMBER'}

def clean(s):return re.sub(r'\s+',' ',s or '').strip()
def plain(s):return clean(MARKUP.sub('',s or '').replace('\xa0',' '))
def norm(s):
 s=FOOT.sub('',s or '').upper().replace('&',' AND ')
 s=re.sub(r'/[A-Z]{2}\b',' ',s)
 s=re.sub(r'\b(?:CLASS\s+[A-Z]|NON[- ]?VOTING|VOTING)\s+SHARES?\b',' ',s)
 s=re.sub(r'\bSHARES?\b',' ',s)
 s=re.sub(r'\b(?:INCORPORATED|INC|CORPORATION|CORP|COMPANY|CO|LIMITED|LTD|PLC)\b',' ',s)
 s=re.sub(r'[^A-Z0-9]+',' ',s)
 s=' '.join(s.split())
 parts=s.split();out=[];i=0
 while i<len(parts):
  if len(parts[i])==1 and i+1<len(parts) and len(parts[i+1])==1:
   acc=parts[i];i+=1
   while i<len(parts) and len(parts[i])==1:acc+=parts[i];i+=1
   out.append(acc)
  else:out.append(parts[i]);i+=1
 return ' '.join(out)

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
 for i,x in enumerate(lines):
  if not re.search(r'SCHEDULE OF INVESTMENTS|PORTFOLIO OF INVESTMENTS',x,re.I):continue
  window='\n'.join(lines[i:min(len(lines),i+20)])
  if series.lower() in window.lower() and re.search(r'COMMON STOCK|SECURITY\s+SHARES\s+VALUE|SHARES\s+SECURITY DESCRIPTION',window,re.I):
   return lines[i:min(len(lines),i+5000)]
 starts=[i for i,x in enumerate(lines) if series.lower() in x.lower()]
 return lines[starts[-1] if starts else 0:min(len(lines),(starts[-1] if starts else 0)+5000)]

def parse_compact_inline(seg):
 rows=[];in_common=False
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
  if (desc and re.search(r'[A-Za-z]',desc) and desc.upper() not in MONTHS and len(desc)>2
      and not re.match(r'^(TOTAL|COMMON STOCK|SECURITY)',desc,re.I)):
   rows.append(desc)
 return rows

def parse_four_line(seg):
 rows=[];in_common=False;i=0
 while i<len(seg):
  line=plain(seg[i])
  if re.search(r'\bCOMMON STOCKS?\b',line,re.I):in_common=True;i+=1;continue
  if in_common and STOP.search(line):break
  if not in_common:i+=1;continue
  if re.fullmatch(r'\d[\d,]*',line):
   j=i+1;nonempty=[]
   while j<len(seg) and len(nonempty)<6:
    q=plain(seg[j]);j+=1
    if q:nonempty.append(q)
   if nonempty:
    issuer=nonempty[0]
    later=[q for q in nonempty[1:] if q!='$']
    value_found=any(re.fullmatch(r'\$?\d[\d,]*',q) for q in later)
    if (value_found and re.search(r'[A-Za-z]',issuer)
        and not re.search(r'\d+(?:\.\d+)?\s*%$|^(TOTAL|COMMON STOCK|SHARES|SECURITY DESCRIPTION)',issuer,re.I)):
     rows.append(issuer);i=j;continue
  i+=1
 return rows

def parse_nearby_vertical(seg):
 """Rendered SEC vertical tables: issuer text has a shares integer shortly before and market value shortly after."""
 rows=[];in_common=False
 cleaned=[plain(x) for x in seg]
 for i,line in enumerate(cleaned):
  if re.search(r'\bCOMMON STOCKS?\b',line,re.I):in_common=True;continue
  if in_common and STOP.search(line):break
  if not in_common or not line or not re.search(r'[A-Za-z]',line):continue
  if (re.search(r'\d+(?:\.\d+)?\s*%$',line) or re.match(r'^(TOTAL|COMMON STOCK|SHARES|SECURITY DESCRIPTION|VALUE|SCHEDULE OF INVESTMENTS)',line,re.I)):
   continue
  prev=' '.join(x for x in cleaned[max(0,i-4):i] if x)
  foll=' '.join(x for x in cleaned[i+1:min(len(cleaned),i+5)] if x)
  if re.search(r'\b\d[\d,]*\b',prev) and re.search(r'\b\d[\d,]*\b',foll):rows.append(line)
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
   if desc and re.search(r'[A-Za-z]',desc) and not re.match(r'^(TOTAL|COMMON STOCK)',desc,re.I):rows.append(desc)
 return rows

def parse_rows(text,series):
 seg=schedule_segment(text,series)
 candidates=[('compact_inline',parse_compact_inline(seg)),('four_line',parse_four_line(seg)),('nearby_vertical',parse_nearby_vertical(seg)),('spaced',parse_spaced(seg))]
 scored=[]
 for grammar,rows in candidates:
  unique=list(dict.fromkeys(x for x in rows if norm(x)))
  alpha=sum(bool(re.search(r'[A-Za-z]',x)) for x in unique)
  bad=sum(bool(re.search(r'\d+(?:\.\d+)?\s*%$|^(TOTAL|COMMON STOCK|SHARES|SECURITY DESCRIPTION|VALUE)',x,re.I)) for x in unique)
  quality=(alpha-bad)/len(unique) if unique else 0
  plausible=5<=len(unique)<=250 and quality>=.90
  scored.append((plausible,len(unique),quality,grammar,unique))
 plausible=[x for x in scored if x[0]]
 _,_,_,grammar,rows=max(plausible or scored,key=lambda x:(x[0],x[1],x[2]))
 return grammar,rows

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
 out={'purpose':'Source-fidelity audit for already verified complete pre-Production holdings reports of actual 2020-01 Production source series. Source selection was frozen before overlap results. Parser grammars are structural and based on observed SEC rendering. Identity normalization removes legal suffixes, explicit share-class labels, SEC issuer jurisdiction suffixes, and dotted-initial punctuation only; no fuzzy similarity is accepted. No strategy returns used.','rows':outrows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
