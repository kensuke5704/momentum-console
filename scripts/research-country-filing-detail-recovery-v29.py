#!/usr/bin/env python3
from __future__ import annotations
import html, importlib.util, json, os, re, urllib.request
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/nq-hybrid-country-resolved-h1-2006.json'

def load(path):
 spec=importlib.util.spec_from_file_location('base_recovery',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
base=load(ROOT/'scripts/research-country-index-headers-recovery-v29.py')
DETAIL_CACHE={}

def detail_url(filename):
 p=base.accession_parts(filename)
 if not p:return None
 cik,acc,ad=p
 return f'https://www.sec.gov/Archives/edgar/data/{cik}/{ad}/{acc}-index.htm'

def detail_page(filename):
 if filename in DETAIL_CACHE:return DETAIL_CACHE[filename]
 url=detail_url(filename)
 if not url:raise RuntimeError('no detail url')
 proxy='https://r.jina.ai/'+url
 req=urllib.request.Request(proxy,headers=base.UA)
 with urllib.request.urlopen(req,timeout=8) as r:
  result=(r.read(800_000).decode('latin-1','replace'),proxy)
 DETAIL_CACHE[filename]=result
 return result

def detail_entity_state(target,cik,text):
 cleaned=html.unescape(re.sub(r'<[^>]*>',' ',text)).replace('\r',' ')
 cleaned=re.sub(r'\s+',' ',cleaned)
 zcik=str(cik).zfill(10);nt=base.normalize_company(target)
 pat=re.compile(r'([^|]{2,180}?)\s*\((?:Filer|Issuer|Filed by|Subject)\)\s*CIK:\s*(\d{1,10}).{0,500}?State\s+of\s+Incorp\.?:\s*([A-Z0-9]{2,3})',re.I)
 for nm,ck,st in pat.findall(cleaned):
  name=re.sub(r'^.*?(?:Business Address|Mailing Address)\s+','',nm,flags=re.I).strip(' :-')
  if ck.zfill(10)==zcik and base.normalize_company(name)==nt:return st.upper(),name
 for m in re.finditer(r'CIK:\s*0*'+re.escape(str(int(zcik))),cleaned,re.I):
  w=cleaned[max(0,m.start()-240):m.start()+720]
  sm=re.search(r'State\s+of\s+Incorp\.?:\s*([A-Z0-9]{2,3})',w,re.I)
  if sm and nt and nt in base.normalize_company(w):return sm.group(1).upper(),target
 return None,None

def audited_candidates(row,cik):
 """Reuse only filing candidates already produced by strict PIT exact-name->unique-CIK resolution."""
 out=[];seen=set();report=row.get('asOfReportDate')
 for attempt in row.get('attempts',[]):
  if str(attempt.get('seedCik') or '').zfill(10)!=str(cik).zfill(10):continue
  if attempt.get('historicalExactCikCount')!=1:continue
  for fa in attempt.get('filingAttempts',[]):
   date=fa.get('dateFiled');url=fa.get('submissionUrl') or ''
   if not date or not report or date>report or '/Archives/' not in url:continue
   filename=url.split('/Archives/',1)[1]
   if filename in seen:continue
   seen.add(filename);out.append({'form':fa.get('form'),'dateFiled':date,'filename':filename,'sourceSubmissionUrl':url})
 return out[:2]

def main():
 shard_i=int(os.environ.get('SHARD_INDEX','0'));shard_n=int(os.environ.get('SHARD_COUNT','1'))
 data=json.loads(SRC.read_text())
 all_unknown=sorted([r for r in data.get('resolutionAudit',[]) if r.get('classification')=='UNKNOWN'],key=lambda r:(r.get('ticker') or '',r.get('securityId') or '',r.get('asOfReportDate') or ''))
 grouped=defaultdict(list)
 for r in all_unknown:
  c=base.seed_cik(r)
  if c:grouped[c].append(r)
 seeds=sorted(grouped);my_seeds=[c for i,c in enumerate(seeds) if i%shard_n==shard_i]
 results=[];resolved=us=nonus=errors=0;candidate_rows=0
 for gi,cik in enumerate(my_seeds):
  queries=grouped[cik];candidate_union={}
  for q in queries:
   for fr in audited_candidates(q,cik):candidate_union[fr['filename']]=fr
  pages={}
  for filename,fr in candidate_union.items():
   try:text,tr=detail_page(filename);pages[filename]=(text,tr)
   except Exception as e:errors+=1;pages[filename]=(None,type(e).__name__)
  for q in queries:
   forms=base.query_forms(q);candidates=audited_candidates(q,cik);candidate_rows+=bool(candidates)
   rec={'ticker':q.get('ticker'),'securityId':q.get('securityId'),'asOfReportDate':q.get('asOfReportDate'),'issuerVariants':q.get('issuerVariants',[]),'historicalExactCik':cik,'classification':'UNKNOWN','attempts':[]}
   for fr in candidates:
    text,tr=pages.get(fr['filename'],(None,'NOT_FETCHED'))
    if text is None:rec['attempts'].append({**fr,'error':tr});continue
    for issuer in forms:
     st,name=detail_entity_state(issuer,cik,text);rec['attempts'].append({**fr,'transport':tr,'stateCode':st,'historicalEntityName':name})
     if st:
      rec.update({'classification':'US' if st in base.US_CODES else 'NON_US','stateCode':st,'resolutionSource':'PIT_FILING_DETAIL_ENTITY_STATE','historicalEntityName':name,'evidenceForm':fr['form'],'evidenceDateFiled':fr['dateFiled'],'evidenceFilename':fr['filename'],'evidenceTransport':tr});break
    if rec['classification']!='UNKNOWN':break
   if rec['classification']!='UNKNOWN':resolved+=1;us+=rec['classification']=='US';nonus+=rec['classification']=='NON_US'
   results.append(rec)
  if (gi+1)%10==0:print('PROGRESS',json.dumps({'shard':shard_i,'ciksDone':gi+1,'queryRowsDone':len(results),'resolved':resolved,'errors':errors,'detailCache':len(DETAIL_CACHE)}),flush=True)
 shard_input=sum(len(grouped[c]) for c in my_seeds)
 out={'purpose':'Return-independent PIT recovery using historical SEC filing-detail pages. Reuse the exact unique historical CIK and pre-report-date filing candidates already recorded by the strict resolver; promote UNKNOWN only when the corresponding accession detail page shows the same historical entity/CIK and State of Incorp. No new identity search, current ticker metadata, fuzzy matching, US default, ranks, returns or strategy outcomes.','shardIndex':shard_i,'shardCount':shard_n,'allInputUnknownCount':len(all_unknown),'allHistoricalExactUniqueCikQueryCount':sum(len(v) for v in grouped.values()),'allHistoricalExactUniqueCikCount':len(seeds),'shardCikCount':len(my_seeds),'shardInputUnknownCount':shard_input,'queryWithAuditedCandidateCount':candidate_rows,'resolvedCount':resolved,'resolvedUSCount':us,'resolvedNonUSCount':nonus,'remainingUnknownCount':shard_input-resolved,'transportErrorCount':errors,'detailCacheCount':len(DETAIL_CACHE),'results':results}
 path=ROOT/f'data/research/country-filing-detail-recovery-v29-shard-{shard_i}.json';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='results'}),flush=True)
if __name__=='__main__':main()
