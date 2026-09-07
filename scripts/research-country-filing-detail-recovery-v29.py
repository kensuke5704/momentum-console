#!/usr/bin/env python3
from __future__ import annotations
import html,json,os,re,urllib.request
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SHARD=int(os.environ.get('SHARD_INDEX','0'))
SRC=ROOT/f'data/research/country-index-headers-recovery-v29-shard-{SHARD}.json'
DETAIL_CACHE={}
UA={'User-Agent':'Kensuke Kawamura kensuke5704@gmail.com momentum-console research','Accept':'text/plain,text/html,*/*','Accept-Encoding':'identity'}
US_CODES={'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC','X1'}
FORM_PRIORITY={'10-K':0,'10-K/A':1,'10-Q':2,'10-Q/A':3,'8-K':4,'8-K/A':5,'DEF 14A':6,'DEFA14A':7,'PRE 14A':8,'11-K':9,'S-8':10,'S-8 POS':11}

def normalize_company(s):
 s=(s or '').upper().replace('&',' AND ');s=re.sub(r'\s*/[A-Z0-9]{2,3}/?\s*$','',s);s=re.sub(r'\s*\((?:[A-Z]{1,3}|\d{1,3})\)\s*$','',s)
 s=re.sub(r'\b(?:INCORPORATED|INC|CORPORATION|CORP|COMPANY|CO|LIMITED|LTD|PLC|AG|THE)\b',' ',s);s=re.sub(r'[^A-Z0-9]+',' ',s);return ' '.join(s.split())

def accession_parts(filename):
 m=re.search(r'edgar/data/(\d+)/(\d{10}-\d{2}-\d{6})\.txt$',filename or '',re.I)
 if not m:return None
 cik=str(int(m.group(1)));acc=m.group(2);return cik,acc,acc.replace('-','')

def detail_urls(filename):
 p=accession_parts(filename)
 if not p:return []
 cik,acc,ad=p;base=f'https://www.sec.gov/Archives/edgar/data/{cik}/{ad}/{acc}-index';return [base+'.htm',base+'.html']

def detail_page(filename):
 if filename in DETAIL_CACHE:return DETAIL_CACHE[filename]
 last=None
 for url in detail_urls(filename):
  for candidate in ('https://r.jina.ai/'+url,url):
   try:
    req=urllib.request.Request(candidate,headers=UA)
    with urllib.request.urlopen(req,timeout=10) as r:result=(r.read(800_000).decode('utf-8','replace'),candidate)
    DETAIL_CACHE[filename]=result;return result
   except Exception as e:last=e
 raise RuntimeError(type(last).__name__ if last else 'FETCH_FAILED')

def detail_entity_state(targets,cik,text):
 cleaned=html.unescape(re.sub(r'<[^>]*>',' ',text)).replace('\r',' ');cleaned=re.sub(r'\s+',' ',cleaned)
 zcik=str(cik).zfill(10);nts={normalize_company(x) for x in targets if normalize_company(x)}
 # SEC filing detail pages render: NAME (Filer|Issuer) CIK: NNN ... State of Incorp.: XX.
 pat=re.compile(r'([^|]{2,220}?)\s*\((Filer|Issuer|Filed by|Subject)\)\s*CIK:\s*(?:\*\*)?(?:\[)?(\d{1,10}).{0,700}?State\s+of\s+Incorp(?:oration)?\.?:\s*(?:\*\*)?([A-Z0-9]{2,3})',re.I)
 matches=[]
 for nm,role,ck,st in pat.findall(cleaned):
  name=re.sub(r'^.*?(?:Business Address|Mailing Address)\s+','',nm,flags=re.I).strip(' :-')
  if ck.zfill(10)==zcik and normalize_company(name) in nts:matches.append((st.upper(),name,role.upper()))
 states=sorted({x[0] for x in matches})
 if len(states)>1:raise RuntimeError('MULTIPLE_STATE_CODES:'+','.join(states))
 if len(states)==1:
  x=next(x for x in matches if x[0]==states[0]);return x
 # Conservative fallback: same CIK within a bounded entity window plus normalized historical issuer name.
 for m in re.finditer(r'CIK:\s*(?:\*\*)?(?:\[)?0*'+re.escape(str(int(zcik)))+r'\b',cleaned,re.I):
  w=cleaned[max(0,m.start()-300):m.start()+900]
  if not any(nt and nt in normalize_company(w) for nt in nts):continue
  states=sorted(set(x.upper() for x in re.findall(r'State\s+of\s+Incorp(?:oration)?\.?:\s*(?:\*\*)?([A-Z0-9]{2,3})',w,re.I)))
  if len(states)==1:return states[0],next((t for t in targets if normalize_company(t) in normalize_company(w)),targets[0] if targets else None),'CIK_WINDOW'
  if len(states)>1:raise RuntimeError('MULTIPLE_STATE_CODES:'+','.join(states))
 return None,None,None

def candidates(row):
 report=row.get('asOfReportDate');seen=set();out=[]
 for a in row.get('attempts',[]):
  form=str(a.get('form') or '').upper();date=a.get('dateFiled');fn=a.get('filename')
  if form not in FORM_PRIORITY or not date or not fn or (report and date>report) or fn in seen:continue
  seen.add(fn);out.append({'form':form,'dateFiled':date,'filename':fn})
 out.sort(key=lambda r:(FORM_PRIORITY[r['form']],-int(r['dateFiled'].replace('-','')),r['filename']));return out[:6]

def main():
 data=json.loads(SRC.read_text());rows=data.get('results') or []
 grouped=defaultdict(list)
 for r in rows:
  c=str(r.get('historicalExactCik') or '').zfill(10)
  if c.strip('0'):grouped[c].append(r)
 pages_by_cik={};errors=0
 for cik,queries in grouped.items():
  union={}
  for q in queries:
   for fr in candidates(q):union[fr['filename']]=fr
  pages={}
  for fn,fr in union.items():
   try:text,tr=detail_page(fn);pages[fn]=(fr,text,tr)
   except Exception as e:errors+=1;pages[fn]=(fr,None,type(e).__name__)
  pages_by_cik[cik]=pages
 results=[];resolved=us=nonus=conflicts=0
 for i,q in enumerate(rows,1):
  cik=str(q.get('historicalExactCik') or '').zfill(10);targets=list(q.get('matchedIssuerForms') or q.get('issuerVariants') or [])
  rec={'ticker':q.get('ticker'),'securityId':q.get('securityId'),'asOfReportDate':q.get('asOfReportDate'),'issuerVariants':q.get('issuerVariants',[]),'matchedIssuerForms':targets,'historicalExactCik':cik if cik.strip('0') else None,'classification':'UNKNOWN','attempts':[]}
  positives=[]
  if cik.strip('0'):
   for fr in candidates(q):
    _fr,text,tr=pages_by_cik.get(cik,{}).get(fr['filename'],(fr,None,'NOT_FETCHED'))
    one={**fr}
    if text is None:one['error']=tr;rec['attempts'].append(one);continue
    try:
     st,name,role=detail_entity_state(targets,cik,text);one.update({'transport':tr,'stateCode':st,'historicalEntityName':name,'entityRole':role})
     if st:positives.append({'classification':'US' if st in US_CODES else 'NON_US','stateCode':st,'historicalEntityName':name,'entityRole':role,'evidenceForm':fr['form'],'evidenceDateFiled':fr['dateFiled'],'evidenceFilename':fr['filename'],'evidenceTransport':tr})
    except Exception as e:one['error']=type(e).__name__
    rec['attempts'].append(one)
  classes=sorted({p['classification'] for p in positives})
  if len(classes)>1:conflicts+=1;raise RuntimeError(f'filing-detail country conflict {rec["ticker"]} {rec["securityId"]} {rec["asOfReportDate"]}: {classes}')
  if len(classes)==1:
   p=next(x for x in positives if x['classification']==classes[0]);rec.update(p);rec['resolutionSource']='PIT_FILING_DETAIL_ENTITY_STATE';resolved+=1;us+=rec['classification']=='US';nonus+=rec['classification']=='NON_US'
  results.append(rec)
  if i%50==0:print('PROGRESS',json.dumps({'shard':SHARD,'done':i,'resolved':resolved,'errors':errors,'detailCache':len(DETAIL_CACHE)}),flush=True)
 out={'purpose':'Return-independent PIT recovery from historical SEC filing-detail pages. Input identity/date rows, unique historical CIKs and pre-report-date filing candidates are taken directly from the accepted historical-exact-CIK recovery artifacts. Promotion requires the same historical issuer name and CIK bound to exactly one State of Incorp. code on that exact accession detail page. No current ticker metadata, current state/country, fuzzy matching, US default, ranks, returns or strategy outcomes are used.','shardIndex':SHARD,'shardCount':8,'inputCount':len(rows),'historicalCikCount':len(grouped),'resolvedCount':resolved,'resolvedUSCount':us,'resolvedNonUSCount':nonus,'remainingUnknownCount':len(rows)-resolved,'transportErrorCount':errors,'detailCacheCount':len(DETAIL_CACHE),'conflictCount':conflicts,'results':results}
 path=ROOT/f'data/research/country-filing-detail-recovery-v29-shard-{SHARD}.json';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='results'}),flush=True)
if __name__=='__main__':main()
