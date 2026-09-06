#!/usr/bin/env python3
from __future__ import annotations
import html, importlib.util, json, os, re
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
 r=base.fetch_candidates(('https://r.jina.ai/'+url,url),800_000,14)
 DETAIL_CACHE[filename]=r
 return r

def detail_entity_state(target,cik,text):
 # EDGAR filing detail page exposes historical filer identity and State of Incorp.
 cleaned=html.unescape(re.sub(r'<[^>]*>',' ',text)).replace('\r',' ')
 cleaned=re.sub(r'\s+',' ',cleaned)
 zcik=str(cik).zfill(10);nt=base.normalize_company(target)
 # Bound state to a nearby historical filer/issuer identity carrying the same CIK.
 pat=re.compile(r'([^|]{2,180}?)\s*\((?:Filer|Issuer|Filed by|Subject)\)\s*CIK:\s*(\d{1,10}).{0,500}?State\s+of\s+Incorp\.?:\s*([A-Z0-9]{2,3})',re.I)
 for nm,ck,st in pat.findall(cleaned):
  name=re.sub(r'^.*?(?:Business Address|Mailing Address)\s+','',nm,flags=re.I).strip(' :-')
  if ck.zfill(10)==zcik and base.normalize_company(name)==nt:return st.upper(),name
 # Jina text often inserts headings/newlines differently; require same CIK and exact normalized name in a narrow window.
 cikpos=[m.start() for m in re.finditer(r'CIK:\s*0*'+re.escape(str(int(zcik))),cleaned,re.I)]
 for pos in cikpos:
  w=cleaned[max(0,pos-220):pos+700]
  sm=re.search(r'State\s+of\s+Incorp\.?:\s*([A-Z0-9]{2,3})',w,re.I)
  if not sm:continue
  if any(base.normalize_company(f) and base.normalize_company(f) in base.normalize_company(w) for f in [target]):
   return sm.group(1).upper(),target
 return None,None

def main():
 shard_i=int(os.environ.get('SHARD_INDEX','0'));shard_n=int(os.environ.get('SHARD_COUNT','1'))
 data=json.loads(SRC.read_text())
 all_unknown=sorted([r for r in data.get('resolutionAudit',[]) if r.get('classification')=='UNKNOWN'],key=lambda r:(r.get('ticker') or '',r.get('securityId') or '',r.get('asOfReportDate') or ''))
 grouped=defaultdict(list)
 for r in all_unknown:
  c=base.seed_cik(r)
  if c:grouped[c].append(r)
 seeds=sorted(grouped);my_seeds=[c for i,c in enumerate(seeds) if i%shard_n==shard_i];my_rows=[r for c in my_seeds for r in grouped[c]]
 years=sorted({int(r['asOfReportDate'][:4]) for r in my_rows if r.get('asOfReportDate')});master,transports=base.load_master(years);by_cik=defaultdict(list)
 for r in master:
  if r.get('form') in base.ISSUER_FORMS:by_cik[r['cik']].append(r)
 results=[];resolved=us=nonus=errors=0
 for gi,cik in enumerate(my_seeds):
  queries=grouped[cik];candidate_union={}
  for q in queries:
   report=q.get('asOfReportDate')
   for fr in sorted([r for r in by_cik.get(cik,[]) if report and r['dateFiled']<=report],key=base.filing_sort_key)[:6]:candidate_union[fr['filename']]=fr
  pages=[]
  for fr in sorted(candidate_union.values(),key=base.filing_sort_key):
   try:text,tr=detail_page(fr['filename']);pages.append((fr,text,tr))
   except Exception as e:errors+=1;pages.append((fr,None,type(e).__name__))
  for q in queries:
   forms=base.query_forms(q);report=q.get('asOfReportDate');rec={'ticker':q.get('ticker'),'securityId':q.get('securityId'),'asOfReportDate':report,'issuerVariants':q.get('issuerVariants',[]),'historicalExactCik':cik,'classification':'UNKNOWN','attempts':[]}
   for fr,text,tr in sorted([x for x in pages if x[0]['dateFiled']<=report],key=lambda x:base.filing_sort_key(x[0])):
    if text is None:rec['attempts'].append({'filename':fr['filename'],'error':tr});continue
    for issuer in forms:
     st,name=detail_entity_state(issuer,cik,text);rec['attempts'].append({'form':fr['form'],'dateFiled':fr['dateFiled'],'filename':fr['filename'],'transport':tr,'stateCode':st,'historicalEntityName':name})
     if st:
      rec.update({'classification':'US' if st in base.US_CODES else 'NON_US','stateCode':st,'resolutionSource':'PIT_FILING_DETAIL_ENTITY_STATE','historicalEntityName':name,'evidenceForm':fr['form'],'evidenceDateFiled':fr['dateFiled'],'evidenceFilename':fr['filename'],'evidenceTransport':tr});break
    if rec['classification']!='UNKNOWN':break
   if rec['classification']!='UNKNOWN':resolved+=1;us+=rec['classification']=='US';nonus+=rec['classification']=='NON_US'
   results.append(rec)
  if (gi+1)%20==0:print('PROGRESS',json.dumps({'shard':shard_i,'ciksDone':gi+1,'queryRowsDone':len(results),'resolved':resolved,'errors':errors,'detailCache':len(DETAIL_CACHE)}),flush=True)
 out={'purpose':'Return-independent PIT recovery using SEC historical filing-detail pages. Reuse only the already accepted historical exact issuer-form -> unique CIK seed; promote UNKNOWN only when a pre-report-date accession detail page shows the same historical entity/CIK and State of Incorp. No current ticker metadata, fuzzy matching, US default, ranks, returns or strategy outcomes.','shardIndex':shard_i,'shardCount':shard_n,'allInputUnknownCount':len(all_unknown),'allHistoricalExactUniqueCikQueryCount':sum(len(v) for v in grouped.values()),'allHistoricalExactUniqueCikCount':len(seeds),'shardCikCount':len(my_seeds),'shardInputUnknownCount':len(my_rows),'resolvedCount':resolved,'resolvedUSCount':us,'resolvedNonUSCount':nonus,'remainingUnknownCount':len(my_rows)-resolved,'transportErrorCount':errors,'detailCacheCount':len(DETAIL_CACHE),'masterYears':years,'masterIndexTransports':transports,'results':results}
 path=ROOT/f'data/research/country-filing-detail-recovery-v29-shard-{shard_i}.json';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in {'results','masterIndexTransports'}}),flush=True)
if __name__=='__main__':main()
