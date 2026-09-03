#!/usr/bin/env python3
from __future__ import annotations
import json,re,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/sec-us-attribution-three-issuer-cik-audit-2006.json'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'application/json,text/html,text/plain,*/*'}
CASES=[
 {'ticker':'DIS','issuer':'Walt Disney Co.','reportDate':'2006-01-31','candidateCik':'0001001039','historicalName':re.compile(r'WALT\s+DISNEY',re.I)},
 {'ticker':'JDSU','issuer':'JDS Uniphase Corp.','reportDate':'2005-12-31','candidateCik':'0000912093','historicalName':re.compile(r'JDS\s+UNIPHASE',re.I)},
 {'ticker':'TWX','issuer':'Time Warner, Inc.','reportDate':'2005-12-31','candidateCik':'0001105705','historicalName':re.compile(r'TIME\s+WARNER',re.I)},
]
US_CODES={'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC','X1'}
STATE_PATS=[re.compile(r'STATE-OF-INCORPORATION:\s*([A-Z0-9]{2,3})',re.I),re.compile(r'State\s+of\s+Inc(?:orp(?:oration)?)?\.?\s*:?\s*(?:\*\*)?([A-Z0-9]{2,3})',re.I),re.compile(r'State or other jurisdiction of incorporation[^A-Z0-9]{0,100}([A-Z]{2})\b',re.I)]

def get(url,limit=5_000_000):
 last=None
 for u in ('https://r.jina.ai/'+url,url):
  try:
   req=urllib.request.Request(u,headers=UA)
   with urllib.request.urlopen(req,timeout=30) as r:return r.read(limit).decode('utf-8','replace'),u
  except Exception as e:last=repr(e)
 raise RuntimeError(last or 'fetch failed')

def json_get(url):
 text,tr=get(url,4_000_000)
 try:return json.loads(text),tr
 except Exception:
  m=re.search(r'\{.*\}',text,re.S)
  if not m:raise
  return json.loads(m.group(0)),tr

def state(text):
 for p in STATE_PATS:
  m=p.search(text)
  if m:return m.group(1).upper(),p.pattern
 return None,None

def filing_rows(block):
 forms=block.get('form',[]);dates=block.get('filingDate',[]);accs=block.get('accessionNumber',[]);docs=block.get('primaryDocument',[])
 for i,f in enumerate(forms):
  if i<len(dates) and i<len(accs) and i<len(docs):yield f,dates[i],accs[i],docs[i]

def main():
 out=[]
 for c in CASES:
  row={k:v for k,v in c.items() if k!='historicalName'};cik=c['candidateCik'];digits=str(int(cik))
  try:
   data,tr=json_get(f'https://data.sec.gov/submissions/CIK{cik}.json');row['currentSecName']=data.get('name');row['submissionsTransport']=tr
   blocks=[data.get('filings',{}).get('recent',{})]
   for fmeta in data.get('filings',{}).get('files',[]):
    name=fmeta.get('name')
    if not name:continue
    try:
     old,_=json_get('https://data.sec.gov/submissions/'+name);blocks.append(old)
    except Exception as e:row.setdefault('metadataErrors',[]).append(type(e).__name__)
   cand=[]
   for block in blocks:
    for form,fd,acc,doc in filing_rows(block):
     if form=='10-K' and fd<=c['reportDate']:cand.append((fd,acc,doc))
   cand=sorted(set(cand),reverse=True);row['historical10KCandidates']=len(cand)
   for fd,acc,doc in cand[:12]:
    url=f'https://www.sec.gov/Archives/edgar/data/{digits}/{acc.replace("-","")}/{doc}'
    try:
     text,t=get(url);name_ok=bool(c['historicalName'].search(text));st,pat=state(text)
     row.setdefault('attempts',[]).append({'filingDate':fd,'url':url,'historicalNameMatched':name_ok,'stateCode':st})
     if name_ok and st:
      row.update({'historicalIdentityValidated':True,'stateCode':st,'classification':'US' if st in US_CODES else 'NON_US','filingDate':fd,'filingUrl':url,'filingTransport':t,'pattern':pat});break
    except Exception as e:row.setdefault('errors',[]).append(type(e).__name__)
   row.setdefault('historicalIdentityValidated',False);row.setdefault('classification','UNKNOWN')
  except Exception as e:row.update({'classification':'UNKNOWN','historicalIdentityValidated':False,'error':repr(e)})
  out.append(row);print('CASE',json.dumps(row),flush=True)
 summary={'purpose':'Validate successor/renamed CIK candidates using only pre-report-date SEC 10-Ks: historical issuer name and state-of-incorporation must both occur in the historical filing. Current issuer name is not identity evidence. No Universe ranks or returns used.','resolved':sum(x['classification']!='UNKNOWN' for x in out),'unknown':sum(x['classification']=='UNKNOWN' for x in out),'rows':out}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(summary,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in summary.items() if k!='rows'}),flush=True)
if __name__=='__main__':main()
