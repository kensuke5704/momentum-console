#!/usr/bin/env python3
from __future__ import annotations
import html,io,json,os,re,time,urllib.request,zipfile
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/research/nq-hybrid-country-resolved-h1-2006.json'
UA={'User-Agent':'Kensuke Kawamura kensuke5704@gmail.com momentum-console research','Accept':'text/plain,text/html,application/zip,*/*','Accept-Encoding':'identity'}
US_CODES={'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC','X1'}
FORM_PRIORITY={'10-K':0,'10-K/A':1,'10-Q':2,'10-Q/A':3,'8-K':4,'8-K/A':5,'DEF 14A':6,'DEFA14A':7,'PRE 14A':8,'11-K':9,'S-8':10,'S-8 POS':11}
ISSUER_FORMS=set(FORM_PRIORITY)
JURIS_RE=re.compile(r'\s*/[A-Z0-9]{2,3}/?\s*$',re.I)
HEADER_CACHE={}

def clean_issuer(s):
 s=re.sub(r'\s*\((?:[a-z]{1,3}|\d{1,3})\)\s*$','',s or '',flags=re.I)
 return ' '.join(s.replace('’',"'").split()).strip(' .,-')

def normalize_company(s):
 s=JURIS_RE.sub('',s or '');s=clean_issuer(s).upper().replace('&',' AND ')
 s=re.sub(r'\b(?:INCORPORATED|INC|CORPORATION|CORP|COMPANY|CO|LIMITED|LTD|PLC|AG|THE)\b',' ',s);s=re.sub(r'[^A-Z0-9]+',' ',s)
 return ' '.join(s.split())

def cleaned_forms(raw):
 vals=[raw];s=raw
 pats=[r'\s*\((?:[a-z]{1,3}|\d{1,3})\)\s*$',r'\s*\((?:CLASS|CL)\s+[A-Z0-9-]+(?:\s+SHARES?)?\)\s*$',r'\s+(?:CLASS|CL)\s+[A-Z0-9-]+(?:\s+SHARES?)?\s*$',r'\s*/[A-Z]{2}\s*$']
 changed=True
 while changed:
  changed=False
  for p in pats:
   ns=re.sub(p,'',s,flags=re.I).strip()
   if ns!=s:vals.append(ns);s=ns;changed=True
 return list(dict.fromkeys(v for v in vals if v))

def fetch_candidates(candidates,limit,timeout):
 last=None
 for candidate in candidates:
  try:
   req=urllib.request.Request(candidate,headers=UA)
   with urllib.request.urlopen(req,timeout=timeout) as r:return r.read(limit).decode('latin-1','replace'),candidate
  except Exception as e:last=e
 raise RuntimeError(repr(last))

def load_master(years):
 rows=[];transports={}
 for year in years:
  for q in range(1,5):
   base=f'https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{q}'
   try:
    req=urllib.request.Request(base+'/master.zip',headers=UA)
    with urllib.request.urlopen(req,timeout=35) as r:data=r.read(20_000_000)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
     name=next(n for n in z.namelist() if n.lower().endswith('master.idx'));text=z.read(name).decode('latin-1','replace');tr=base+'/master.zip'
   except Exception:
    text,tr=fetch_candidates(('https://r.jina.ai/'+base+'/master.idx',base+'/master.idx'),20_000_000,45)
   transports[f'{year}Q{q}']=tr
   for line in text.splitlines():
    p=line.split('|')
    if len(p)<5 or not p[0].strip().isdigit():continue
    cik,company,form,date,filename=[x.strip() for x in p[:5]];form=form.upper()
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}',date):rows.append({'cik':cik.zfill(10),'company':company,'normalizedCompany':normalize_company(company),'form':form,'dateFiled':date,'filename':filename})
 return rows,transports

def accession_parts(filename):
 m=re.search(r'edgar/data/(\d+)/(\d{10}-\d{2}-\d{6})\.txt$',filename,re.I)
 if not m:return None
 cik=str(int(m.group(1)));acc=m.group(2);return cik,acc,acc.replace('-','')

def header_index_url(filename):
 parts=accession_parts(filename)
 if not parts:return None
 cik,acc,ad=parts;return f'https://www.sec.gov/Archives/edgar/data/{cik}/{ad}/{acc}-index-headers.html'

def header_page(filename):
 if filename in HEADER_CACHE:return HEADER_CACHE[filename]
 url=header_index_url(filename)
 if not url:raise RuntimeError('no header index url')
 result=fetch_candidates(('https://r.jina.ai/'+url,url),500_000,12);HEADER_CACHE[filename]=result;return result

def flat_header_entity_state(target,cik,text):
 cleaned=html.unescape(re.sub(r'<[^>]*>','',text)).replace('\r','');nt=normalize_company(target);zcik=str(cik).zfill(10)
 for block in re.split(r'(?im)^\s*COMPANY\s+DATA\s*:\s*$',cleaned)[1:]:
  part=re.split(r'(?im)^\s*(?:FILING\s+VALUES|BUSINESS\s+ADDRESS|MAIL\s+ADDRESS|FORMER\s+COMPANY)\s*:\s*$',block,maxsplit=1)[0]
  nm=re.search(r'(?im)^\s*COMPANY\s+CONFORMED\s+NAME\s*:\s*(.+?)\s*$',part);ck=re.search(r'(?im)^\s*CENTRAL\s+INDEX\s+KEY\s*:\s*(\d{1,10})\s*$',part);st=re.search(r'(?im)^\s*STATE\s+OF\s+INCORPORATION\s*:\s*([A-Z0-9]{2,3})\s*$',part)
  if nm and ck and ck.group(1).zfill(10)==zcik and normalize_company(nm.group(1).strip())==nt and st:return st.group(1).upper(),nm.group(1).strip()
 return None,None

def filing_sort_key(r):return (FORM_PRIORITY.get(r['form'],50),-int(r['dateFiled'].replace('-','')),r['filename'])

def seed_cik(row):
 ciks=set()
 for a in row.get('attempts',[]):
  if a.get('historicalExactCikCount')==1 and a.get('seedCik'):ciks.add(str(a['seedCik']).zfill(10))
 return next(iter(ciks)) if len(ciks)==1 else None

def query_forms(row):
 out=[]
 for issuer in row.get('issuerVariants',[]):
  for f in cleaned_forms(str(issuer)):
   if f not in out:out.append(f)
 return out

def main():
 shard_i=int(os.environ.get('SHARD_INDEX','0'));shard_n=int(os.environ.get('SHARD_COUNT','1'))
 data=json.loads(SRC.read_text());all_unknown=sorted([r for r in data.get('resolutionAudit',[]) if r.get('classification')=='UNKNOWN'],key=lambda r:(r.get('ticker') or '',r.get('securityId') or '',r.get('asOfReportDate') or ''))
 grouped=defaultdict(list);no_seed=[]
 for r in all_unknown:
  c=seed_cik(r)
  if c:grouped[c].append(r)
  else:no_seed.append(r)
 seeds=sorted(grouped);my_seeds=[c for i,c in enumerate(seeds) if i%shard_n==shard_i];my_rows=[r for c in my_seeds for r in grouped[c]]
 years=sorted({int(r['asOfReportDate'][:4]) for r in my_rows if r.get('asOfReportDate')});master,transports=load_master(years);by_cik=defaultdict(list)
 for r in master:
  if r.get('form') in ISSUER_FORMS:by_cik[r['cik']].append(r)
 results=[];resolved=us=nonus=errors=0;filings_fetched=0
 for gi,cik in enumerate(my_seeds):
  queries=grouped[cik];candidate_union={}
  for q in queries:
   report=q.get('asOfReportDate');cand=sorted([r for r in by_cik.get(cik,[]) if report and r['dateFiled']<=report],key=filing_sort_key)[:6]
   for fr in cand:candidate_union[fr['filename']]=fr
  header_records=[]
  for fr in sorted(candidate_union.values(),key=filing_sort_key):
   try:
    text,tr=header_page(fr['filename']);filings_fetched+=1;header_records.append((fr,text,tr))
   except Exception as e:
    errors+=1;header_records.append((fr,None,type(e).__name__))
  for q in queries:
   forms=query_forms(q);report=q.get('asOfReportDate');rec={'ticker':q.get('ticker'),'securityId':q.get('securityId'),'asOfReportDate':report,'issuerVariants':q.get('issuerVariants',[]),'historicalExactCik':cik,'matchedIssuerForms':forms,'classification':'UNKNOWN','attempts':[]}
   eligible=sorted([x for x in header_records if x[0]['dateFiled']<=report],key=lambda x:filing_sort_key(x[0]))
   for fr,text,tr in eligible:
    if text is None:
     rec['attempts'].append({'form':fr['form'],'dateFiled':fr['dateFiled'],'filename':fr['filename'],'error':tr});continue
    for issuer in forms:
     st,name=flat_header_entity_state(issuer,cik,text);rec['attempts'].append({'form':fr['form'],'dateFiled':fr['dateFiled'],'filename':fr['filename'],'transport':tr,'stateCode':st,'historicalEntityName':name})
     if st:
      rec.update({'classification':'US' if st in US_CODES else 'NON_US','stateCode':st,'resolutionSource':'PIT_INDEX_HEADERS_COMPANY_DATA_STATE','historicalEntityName':name,'evidenceForm':fr['form'],'evidenceDateFiled':fr['dateFiled'],'evidenceFilename':fr['filename'],'evidenceTransport':tr});break
    if rec['classification']!='UNKNOWN':break
   if rec['classification']!='UNKNOWN':resolved+=1;us+=rec['classification']=='US';nonus+=rec['classification']=='NON_US'
   results.append(rec)
  if (gi+1)%20==0:print('PROGRESS',json.dumps({'shard':shard_i,'ciksDone':gi+1,'queryRowsDone':len(results),'resolved':resolved,'errors':errors,'headerCache':len(HEADER_CACHE)}),flush=True)
 out={'purpose':'Return-independent PIT recovery of strict-country UNKNOWN identities using official SEC accession index-headers pages. The already accepted historical exact issuer-form -> unique CIK seed is reused; each recovered country still requires a matching historical company name, same CIK and STATE OF INCORPORATION in a pre-report-date accession header. No current ticker metadata, fuzzy matching, US default, ranks, returns or strategy outcomes are used.','shardIndex':shard_i,'shardCount':shard_n,'allInputUnknownCount':len(all_unknown),'allHistoricalExactUniqueCikQueryCount':sum(len(v) for v in grouped.values()),'allHistoricalExactUniqueCikCount':len(seeds),'shardCikCount':len(my_seeds),'shardInputUnknownCount':len(my_rows),'resolvedCount':resolved,'resolvedUSCount':us,'resolvedNonUSCount':nonus,'remainingUnknownCount':len(my_rows)-resolved,'transportErrorCount':errors,'headerCacheCount':len(HEADER_CACHE),'filingFetchCount':filings_fetched,'masterYears':years,'masterIndexTransports':transports,'results':results}
 out_path=ROOT/f'data/research/country-index-headers-recovery-v29-shard-{shard_i}.json';out_path.parent.mkdir(parents=True,exist_ok=True);out_path.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in {'results','masterIndexTransports'}}),flush=True)
if __name__=='__main__':main()
