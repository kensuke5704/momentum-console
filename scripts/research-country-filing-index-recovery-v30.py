#!/usr/bin/env python3
from __future__ import annotations
import html,json,os,re,urllib.request
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/nq-hybrid-country-resolved-h1-2006.json'
MASTER=ROOT/'data/research/sec-issuer-master-rows-2005-2006.json'
UA={'User-Agent':'Kensuke Kawamura kensuke5704@gmail.com momentum-console research','Accept':'text/plain,text/html,*/*','Accept-Encoding':'identity'}
US={'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC','X1'}
FORMS={'10-K','10-K/A','10-Q','10-Q/A','8-K','8-K/A','DEF 14A','DEFA14A','PRE 14A','11-K','S-8','S-8 POS'}
FORM_ORDER={x:i for i,x in enumerate(['10-K','10-K/A','10-Q','10-Q/A','8-K','8-K/A','DEF 14A','DEFA14A','PRE 14A','11-K','S-8','S-8 POS'])}
ENTITY=re.compile(r'(?im)^\s*(?:[-*]\s*)?([^\n\r|]{2,180}?)\s+\((?:Filer|Issuer|Reporting|Filed by|Subject)\)\s+CIK:\s*(?:\*\*)?(?:\[)?(\d{1,10})')
STATE=re.compile(r'State\s+of\s+Inc(?:orp)?\.?\s*:\s*(?:\*\*)?([A-Z0-9]{2,3})(?:\*\*)?',re.I)
PAGE={}

def clean(s):
 s=s or ''
 for p in [r'\s*\((?:[a-z]{1,3}|\d{1,3})\)\s*$',r'\s*\((?:CLASS|CL)\s+[A-Z0-9-]+(?:\s+SHARES?)?\)\s*$',r'\s+(?:CLASS|CL)\s+[A-Z0-9-]+(?:\s+SHARES?)?\s*$',r'\s*/[A-Z]{2}\s*$']:
  s=re.sub(p,'',s,flags=re.I).strip()
 return ' '.join(s.replace('’',"'").split()).strip(' .,-')

def norm(s):
 s=clean(s).upper().replace('&',' AND ')
 s=re.sub(r'\b(?:INCORPORATED|INC|CORPORATION|CORP|COMPANY|CO|LIMITED|LTD|PLC|AG|THE)\b',' ',s)
 s=re.sub(r'[^A-Z0-9]+',' ',s)
 return ' '.join(s.split())

def index_url(filename):
 m=re.search(r'edgar/data/(\d+)/(\d{10}-\d{2}-\d{6})\.txt$',filename or '',re.I)
 if not m:return None
 cik=str(int(m.group(1)));acc=m.group(2)
 return f'https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace("-","")}/{acc}-index.html'

def fetch(url):
 if url in PAGE:return PAGE[url]
 last=None
 for u in ('https://r.jina.ai/'+url,url):
  try:
   req=urllib.request.Request(u,headers=UA)
   with urllib.request.urlopen(req,timeout=12) as r:text=r.read(600000).decode('utf-8','replace')
   PAGE[url]=(text,u);return PAGE[url]
  except Exception as e:last=e
 raise RuntimeError(type(last).__name__ if last else 'fetch failed')

def parse(text,cik,forms):
 text=html.unescape(re.sub(r'<[^>]*>','',text)).replace('\r','')
 targets={norm(x) for x in forms if norm(x)};zcik=str(cik).zfill(10);ms=list(ENTITY.finditer(text))
 for i,m in enumerate(ms):
  name=m.group(1).strip()
  if m.group(2).zfill(10)!=zcik or norm(name) not in targets:continue
  end=ms[i+1].start() if i+1<len(ms) else min(len(text),m.end()+4000)
  states=list(dict.fromkeys(x.upper() for x in STATE.findall(text[m.start():end])))
  if len(states)==1:return states[0],name
 return None,None

def seed(row,masters):
 ciks={str(a.get('seedCik')).zfill(10) for a in row.get('attempts',[]) if a.get('seedCik')}
 forms=list(dict.fromkeys(a.get('issuerForm') for a in row.get('attempts',[]) if a.get('issuerForm')))
 if len(ciks)!=1 or not forms:return None,forms,[]
 cik=next(iter(ciks));date=row.get('asOfReportDate');targets={norm(x) for x in forms if norm(x)};cand=[]
 for r in masters:
  if str(r.get('cik') or '').zfill(10)!=cik or r.get('form') not in FORMS:continue
  if date and r.get('dateFiled') and r['dateFiled']>date:continue
  if norm(r.get('company') or '') not in targets:continue
  u=index_url(r.get('filename'))
  if u:cand.append({'indexUrl':u,'form':r.get('form'),'dateFiled':r.get('dateFiled'),'filename':r.get('filename')})
 cand.sort(key=lambda x:(-(int((x.get('dateFiled') or '0000-00-00').replace('-',''))),FORM_ORDER.get(x.get('form'),99),x.get('filename') or ''))
 seen=set();out=[]
 for x in cand:
  if x['indexUrl'] not in seen:seen.add(x['indexUrl']);out.append(x)
 return cik,forms,out

def main():
 si=int(os.environ.get('SHARD_INDEX','0'));sn=int(os.environ.get('SHARD_COUNT','1'))
 data=json.loads(SRC.read_text());masters=json.loads(MASTER.read_text()).get('rows',[])
 allu=sorted([r for r in data.get('resolutionAudit',[]) if r.get('classification')=='UNKNOWN'],key=lambda r:(r.get('ticker') or '',r.get('securityId') or '',r.get('asOfReportDate') or ''))
 rows=[r for i,r in enumerate(allu) if i%sn==si];res=[];c=Counter();errors=candidates=0
 for i,row in enumerate(rows,1):
  cik,forms,fs=seed(row,masters);candidates+=bool(fs)
  out={'ticker':row.get('ticker'),'securityId':row.get('securityId'),'asOfReportDate':row.get('asOfReportDate'),'historicalExactCik':cik,'issuerForms':forms,'candidateFilingCount':len(fs),'classification':'UNKNOWN','attempts':[]}
  for f in fs[:2]:
   try:
    text,tr=fetch(f['indexUrl']);st,nm=parse(text,cik,forms);out['attempts'].append({**f,'transport':tr,'stateCode':st,'historicalEntityName':nm})
    if st:
     out.update({'classification':'US' if st in US else 'NON_US','stateCode':st,'resolutionSource':'PIT_NEAREST_FILING_INDEX_ENTITY_STATE','historicalEntityName':nm,'evidenceForm':f.get('form'),'evidenceDateFiled':f.get('dateFiled'),'evidenceFilename':f.get('filename'),'evidenceIndexUrl':f.get('indexUrl'),'evidenceTransport':tr});break
   except Exception as e:errors+=1;out['attempts'].append({**f,'error':type(e).__name__})
  c[out['classification']]+=1;res.append(out)
  if i%50==0:print('PROGRESS',json.dumps({'shard':si,'done':i,'counts':dict(c),'candidateRows':candidates,'errors':errors,'pageCache':len(PAGE)}),flush=True)
 final={'purpose':'Return-independent PIT recovery of original strict-country UNKNOWN identities. Historical exact issuer-form -> unique CIK is inherited unchanged from the accepted strict resolver. Candidate accessions come only from frozen official 2005-2006 SEC master rows with the same CIK, exact normalized historical issuer name and filing date <= report date. The two temporally nearest eligible historical filing-detail pages are checked; recovery requires exact same CIK/name and exactly one State of Incorp. in the same entity block. No current ticker metadata, fuzzy matching, defaults, ranks, returns or strategy outcomes.','shardIndex':si,'shardCount':sn,'allInputUnknownCount':len(allu),'shardInputUnknownCount':len(rows),'candidateInputCount':candidates,'resolvedUSCount':c['US'],'resolvedNonUSCount':c['NON_US'],'remainingUnknownCount':c['UNKNOWN'],'fetchErrorCount':errors,'pageCacheCount':len(PAGE),'results':res}
 p=ROOT/f'data/research/country-filing-index-recovery-v30-shard-{si}.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(final,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in final.items() if k!='results'}),flush=True)
if __name__=='__main__':main()
