#!/usr/bin/env python3
from __future__ import annotations
import json,re,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/sec-us-attribution-three-issuer-cik-audit-2006.json'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'application/json,text/html,text/plain,*/*'}
CASES=[
 {'ticker':'DIS','issuer':'Walt Disney Co.','reportDate':'2006-01-31','candidateCik':'0001001039','nameNeedle':'DISNEY'},
 {'ticker':'JDSU','issuer':'JDS Uniphase Corp.','reportDate':'2005-12-31','candidateCik':'0000912093','nameNeedle':'JDS UNIPHASE'},
 {'ticker':'TWX','issuer':'Time Warner, Inc.','reportDate':'2005-12-31','candidateCik':'0001105705','nameNeedle':'TIME WARNER'},
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

def state(text):
 for p in STATE_PATS:
  m=p.search(text)
  if m:return m.group(1).upper(),p.pattern
 return None,None

def main():
 out=[]
 for c in CASES:
  row=dict(c);cik=c['candidateCik'];digits=str(int(cik))
  try:
   sub,tr=get(f'https://data.sec.gov/submissions/CIK{cik}.json',2_000_000);row['submissionsTransport']=tr
   try:data=json.loads(sub)
   except Exception:
    m=re.search(r'\{.*\}',sub,re.S);data=json.loads(m.group(0)) if m else {}
   name=(data.get('name') or '').upper();row['secName']=data.get('name');row['nameValidated']=c['nameNeedle'] in name
   if not row['nameValidated']:
    row['classification']='UNKNOWN';row['reason']='candidate CIK name mismatch';out.append(row);print('CASE',json.dumps(row),flush=True);continue
   recent=data.get('filings',{}).get('recent',{});forms=recent.get('form',[]);dates=recent.get('filingDate',[]);accs=recent.get('accessionNumber',[]);docs=recent.get('primaryDocument',[])
   idx=[]
   for i,f in enumerate(forms):
    if f=='10-K' and i<len(dates) and dates[i]<=c['reportDate']:idx.append(i)
   urls=[]
   for i in idx[:5]:
    acc=accs[i];doc=docs[i];urls.append(f'https://www.sec.gov/Archives/edgar/data/{digits}/{acc.replace("-","")}/{doc}')
   import urllib.parse
   q=urllib.parse.urlencode({'action':'getcompany','CIK':cik,'type':'10-K','dateb':c['reportDate'].replace('-',''),'owner':'exclude','count':'40'})
   browse,btr=get('https://www.sec.gov/cgi-bin/browse-edgar?'+q,3_000_000);row['browseTransport']=btr
   urls += re.findall(r'https?://(?:www\.)?sec\.gov/Archives/edgar/data/\d+/[^\s\"\'<>\)]+',browse,re.I)
   urls=list(dict.fromkeys(urls));row['filingCandidates']=len(urls)
   for url in urls[:30]:
    try:
     text,t=get(url);st,pat=state(text)
     if st:
      row.update({'stateCode':st,'classification':'US' if st in US_CODES else 'NON_US','filingUrl':url,'filingTransport':t,'pattern':pat});break
    except Exception as e:row.setdefault('errors',[]).append(type(e).__name__)
   row.setdefault('classification','UNKNOWN')
  except Exception as e:row.update({'classification':'UNKNOWN','error':repr(e)})
  out.append(row);print('CASE',json.dumps(row),flush=True)
 summary={'purpose':'Validate fixed candidate historical CIKs for the three still-unresolved issuers against SEC submissions names before using PIT 10-K state-of-incorporation. No Universe ranks or returns used.','resolved':sum(x['classification']!='UNKNOWN' for x in out),'unknown':sum(x['classification']=='UNKNOWN' for x in out),'rows':out}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(summary,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in summary.items() if k!='rows'}),flush=True)
if __name__=='__main__':main()
# trigger 2026-09-03
