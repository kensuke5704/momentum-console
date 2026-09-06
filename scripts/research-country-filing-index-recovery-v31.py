#!/usr/bin/env python3
from __future__ import annotations
import html,json,os,re,urllib.request
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/nq-hybrid-country-resolved-h1-2006.json'; MASTER=ROOT/'data/research/sec-issuer-master-rows-2005-2006.json'
UA={'User-Agent':'Kensuke Kawamura kensuke5704@gmail.com momentum-console research','Accept':'text/plain,text/html,*/*','Accept-Encoding':'identity'}
US={'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC','X1'}
FORMS={'10-K','10-K/A','10-Q','10-Q/A','8-K','8-K/A','DEF 14A','DEFA14A','PRE 14A','11-K','S-8','S-8 POS'}
ENTITY=re.compile(r'(?im)^\s*(?:[-*]\s*)?([^\n\r|]{2,180}?)\s+\((?:Filer|Issuer|Reporting|Filed by|Subject)\)\s+CIK:\s*(?:\*\*)?(?:\[)?(\d{1,10})')
STATE=re.compile(r'State\s+of\s+Inc(?:orp)?\.?\s*:\s*(?:\*\*)?([A-Z0-9]{2,3})(?:\*\*)?',re.I); PAGE={}

def clean(s):
 s=s or ''
 for p in [r'\s*\((?:[a-z]{1,3}|\d{1,3})\)\s*$',r'\s*\((?:CLASS|CL)\s+[A-Z0-9-]+(?:\s+SHARES?)?\)\s*$',r'\s+(?:CLASS|CL)\s+[A-Z0-9-]+(?:\s+SHARES?)?\s*$',r'\s*/[A-Z]{2}\s*$']:
  s=re.sub(p,'',s,flags=re.I).strip()
 return ' '.join(s.replace('’',"'").split()).strip(' .,-')
def norm(s):
 s=clean(s).upper().replace('&',' AND ');s=re.sub(r'\b(?:INCORPORATED|INC|CORPORATION|CORP|COMPANY|CO|LIMITED|LTD|PLC|AG|THE)\b',' ',s);s=re.sub(r'[^A-Z0-9]+',' ',s);return ' '.join(s.split())
def index_url(fn):
 m=re.search(r'edgar/data/(\d+)/(\d{10}-\d{2}-\d{6})\.txt$',fn or '',re.I)
 if not m:return None
 cik=str(int(m.group(1)));acc=m.group(2);return f'https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace("-","")}/{acc}-index.html'
def fetch(url):
 if url in PAGE:return PAGE[url]
 last=None
 for u in ('https://r.jina.ai/'+url,url):
  try:
   req=urllib.request.Request(u,headers=UA)
   with urllib.request.urlopen(req,timeout=10) as r:t=r.read(600000).decode('utf-8','replace')
   PAGE[url]=(t,u);return PAGE[url]
  except Exception as e:last=e
 raise RuntimeError(type(last).__name__ if last else 'fetch failed')
def parse(text,cik,target_names):
 text=html.unescape(re.sub(r'<[^>]*>','',text)).replace('\r','');zcik=str(cik).zfill(10);ms=list(ENTITY.finditer(text))
 for i,m in enumerate(ms):
  name=m.group(1).strip()
  if m.group(2).zfill(10)!=zcik or norm(name) not in target_names:continue
  end=ms[i+1].start() if i+1<len(ms) else min(len(text),m.end()+4000);states=list(dict.fromkeys(x.upper() for x in STATE.findall(text[m.start():end])))
  if len(states)==1:return states[0],name
 return None,None
def seed(row,masters):
 ciks={str(a.get('seedCik')).zfill(10) for a in row.get('attempts',[]) if a.get('seedCik')};forms=list(dict.fromkeys(a.get('issuerForm') for a in row.get('attempts',[]) if a.get('issuerForm')))
 if len(ciks)!=1 or not forms:return None,forms,[]
 cik=next(iter(ciks));date=row.get('asOfReportDate');targets={norm(x) for x in forms if norm(x)};cand=[]
 for r in masters:
  if str(r.get('cik') or '').zfill(10)!=cik or r.get('form') not in FORMS:continue
  if date and r.get('dateFiled') and r['dateFiled']>date:continue
  if norm(r.get('company') or '') not in targets:continue
  u=index_url(r.get('filename'))
  if u:cand.append({'indexUrl':u,'form':r.get('form'),'dateFiled':r.get('dateFiled'),'filename':r.get('filename')})
 cand.sort(key=lambda x:(x.get('dateFiled') or '',x.get('form') or '',x.get('filename') or ''),reverse=True);seen=set();out=[]
 for x in cand:
  if x['indexUrl'] not in seen:seen.add(x['indexUrl']);out.append(x)
 return cik,forms,out[:2]
def main():
 si=int(os.environ.get('SHARD_INDEX','0'));sn=int(os.environ.get('SHARD_COUNT','1'));data=json.loads(SRC.read_text());masters=json.loads(MASTER.read_text()).get('rows',[])
 allu=sorted([r for r in data.get('resolutionAudit',[]) if r.get('classification')=='UNKNOWN'],key=lambda r:(r.get('ticker') or '',r.get('securityId') or '',r.get('asOfReportDate') or ''))
 prepared=[];groups=defaultdict(list)
 for row in allu:
  cik,forms,fs=seed(row,masters);targets=tuple(sorted({norm(x) for x in forms if norm(x)}));urls=tuple(x['indexUrl'] for x in fs);g=(cik,targets,urls)
  prepared.append((row,cik,forms,fs,g));groups[g].append(row)
 group_keys=sorted(groups,key=lambda g:(g[0] or '',g[1],g[2]));owned={g for i,g in enumerate(group_keys) if i%sn==si}
 results=[];counts=Counter();errors=0;resolved_groups=0
 for gi,g in enumerate(group_keys):
  if g not in owned:continue
  cik,targets,urls=g;state=name=evidence=None
  if cik and targets:
   lookup={x['indexUrl']:x for row,c,forms,fs,gg in prepared if gg==g for x in fs}
   for url in urls:
    f=lookup[url]
    try:
     text,tr=fetch(url);st,nm=parse(text,cik,set(targets))
     if st:state,name,evidence=st,nm,{**f,'transport':tr};break
    except Exception:errors+=1
  if state:resolved_groups+=1
  for row,c,forms,fs,gg in prepared:
   if gg!=g:continue
   out={'ticker':row.get('ticker'),'securityId':row.get('securityId'),'asOfReportDate':row.get('asOfReportDate'),'historicalExactCik':c,'issuerForms':forms,'candidateFilingCount':len(fs),'classification':'UNKNOWN','attempts':[]}
   if state:
    out.update({'classification':'US' if state in US else 'NON_US','stateCode':state,'resolutionSource':'PIT_NEAREST_FILING_INDEX_ENTITY_STATE','historicalEntityName':name,'evidenceForm':evidence.get('form'),'evidenceDateFiled':evidence.get('dateFiled'),'evidenceFilename':evidence.get('filename'),'evidenceIndexUrl':evidence.get('indexUrl'),'evidenceTransport':evidence.get('transport')})
   counts[out['classification']]+=1;results.append(out)
  if (gi+1)%100==0:print('GROUP_PROGRESS',json.dumps({'shard':si,'groupsDone':gi+1,'ownedGroups':len(owned),'resolvedGroups':resolved_groups,'counts':dict(counts),'errors':errors,'pageCache':len(PAGE)}),flush=True)
 # exact shard partition is by evidence group, not original row position; output all rows owned by this shard.
 final={'purpose':'Same v30 PIT evidence rule, with identical evidence queries grouped before network access. All original UNKNOWN rows are assigned to exactly one shard by deterministic evidence-query key. No evidence or classification rule changes.','shardIndex':si,'shardCount':sn,'allInputUnknownCount':len(allu),'shardInputUnknownCount':len(results),'evidenceGroupCount':len(owned),'resolvedEvidenceGroupCount':resolved_groups,'resolvedUSCount':counts['US'],'resolvedNonUSCount':counts['NON_US'],'remainingUnknownCount':counts['UNKNOWN'],'fetchErrorCount':errors,'pageCacheCount':len(PAGE),'results':results}
 p=ROOT/f'data/research/country-filing-index-recovery-v31-shard-{si}.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(final,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in final.items() if k!='results'}),flush=True)
if __name__=='__main__':main()
