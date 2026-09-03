#!/usr/bin/env python3
from __future__ import annotations
import gzip,json,re,time,urllib.request,statistics
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/research/transition-nearest-fidelity-2019.json'
BOOT=ROOT/'data/sec-nport/bootstrap.json.gz'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,text/html,*/*'}
# Frozen from report-date-only discovery run 33725924310 before holdings inspection.
CHOSEN={
'S000010977':('1329377','0001445546-19-003838','N-CSRS','2019-06-30'),
'S000017177':('1329377','0001445546-19-003838','N-CSRS','2019-06-30'),
'S000017178':('1329377','0001445546-19-003838','N-CSRS','2019-06-30'),
'S000033237':('1364608','0001445546-19-005018','N-CSR','2019-09-30'),
'S000050385':('1364608','0001445546-19-005018','N-CSR','2019-09-30'),
'S000044209':('1552740','0001445546-19-005047','N-CSR','2019-09-30'),
'S000053942':('1552740','0001445546-19-005049','N-CSRS','2019-09-30'),
'S000053943':('1552740','0001445546-19-005049','N-CSRS','2019-09-30'),
'S000053944':('1552740','0001445546-19-005049','N-CSRS','2019-09-30'),
'S000053945':('1552740','0001445546-19-005049','N-CSRS','2019-09-30'),
'S000053946':('1552740','0001445546-19-005049','N-CSRS','2019-09-30'),
'S000053947':('1552740','0001445546-19-005049','N-CSRS','2019-09-30'),
'S000053948':('1552740','0001445546-19-005049','N-CSRS','2019-09-30'),
'S000047480':('1467831','0000894189-18-004455','N-Q','2018-06-30'),
'S000050191':('1467831','0000894189-18-004455','N-Q','2018-06-30'),
'S000031813':('1408970','0001615774-19-003003','N-CSRS','2018-12-31'),
'S000055090':('1408970','0001615774-19-003003','N-CSRS','2018-12-31'),
'S000059263':('1408970','0001615774-19-003003','N-CSRS','2018-12-31'),
}
DOC_RE=re.compile(r'<TYPE>(N-Q|N-CSR|N-CSRS)\b.*?<FILENAME>\s*([^<\r\n]+)',re.I|re.S)

def get(url,timeout=45):
 last=None
 for u in ('https://r.jina.ai/'+url,url):
  try:
   req=urllib.request.Request(u,headers=UA)
   with urllib.request.urlopen(req,timeout=timeout) as r: raw=r.read(6_000_000)
   return raw.decode('utf-8','replace'),u
  except Exception as e:last=e;time.sleep(.5)
 raise last or RuntimeError('fetch failed')
def base(cik,acc):return f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace("-","")}'
def norm(s):
 s=(s or '').upper().replace('&',' AND ')
 s=re.sub(r'\([^)]*\)',' ',s)
 for a,b in [('INCORPORATED','INC'),('CORPORATION','CORP'),('COMPANY','CO'),('LIMITED','LTD')]:s=re.sub(rf'\b{a}\b',b,s)
 s=re.sub(r'\bTHE\b',' ',s)
 return ' '.join(re.sub(r'[^A-Z0-9]+',' ',s).split())
def earliest_nport(filings):
 out={}
 for f in sorted(filings,key=lambda x:(x.get('reportDate',''),x.get('filingDate',''),x.get('accession',''))):
  sid=f.get('seriesId')
  if sid and sid not in out:out[sid]=f
 return out
def docs(cik,acc,form):
 h,_=get(f'{base(cik,acc)}/{acc}-index-headers.html')
 return [f'{base(cik,acc)}/{fn.strip()}' for typ,fn in DOC_RE.findall(h) if typ.upper()==form]
def locate_doc(urls,series_name):
 hits=[]
 for u in urls:
  try:
   text,tr=get(u)
   score=(1 if series_name.lower() in text.lower() else 0)+(1 if re.search(r'Portfolio of Investments|Schedule of Investments|Portfolio Holdings',text,re.I) else 0)
   hits.append((score,len(text),u,text,tr))
  except Exception:pass
 hits.sort(key=lambda x:(x[0],x[1]),reverse=True)
 return hits[0] if hits and hits[0][0]>=2 else (hits[0] if hits else None)
def slice_series(text,name,all_names):
 ls=text.splitlines();hits=[i for i,x in enumerate(ls) if name.lower() in x.lower()]
 if not hits:return ''
 best=''
 for i in hits:
  if not any(re.search(r'Portfolio of Investments|Schedule of Investments|Portfolio Holdings',x,re.I) for x in ls[i:min(len(ls),i+20)]):continue
  end=min(len(ls),i+1200)
  for j in range(i+1,end):
   if any(n!=name and n.lower() in ls[j].lower() for n in all_names): end=j;break
  seg='\n'.join(ls[i:end])
  if len(seg)>len(best):best=seg
 return best or '\n'.join(ls[hits[0]:min(len(ls),hits[0]+1200)])
def parse_rows(seg):
 rows=[];in_common=False
 for raw in seg.splitlines():
  line=raw.replace('\u2009',' ').replace('\u2002',' ').replace('\xa0',' ')
  if re.search(r'\bCOMMON STOCKS?\b',line,re.I):in_common=True;continue
  if in_common and re.search(r'\b(?:TOTAL COMMON STOCKS?|MONEY MARKET|SHORT[- ]TERM|REPURCHASE|PREFERRED|BONDS?|TOTAL INVESTMENTS|NET ASSETS)\b',line,re.I):
   if not re.search(r'\bTOTAL COMMON STOCKS?\b',line,re.I):in_common=False
   continue
  if not in_common:continue
  cells=[c.strip() for c in re.split(r'\t+',line) if c.strip() and c.strip() not in {'$','—','-'}]
  if len(cells)<3 or not re.match(r'^\$?[\d,]+(?:\.\d+)?$',cells[0]):continue
  nums=[]
  for c in cells:
   if re.match(r'^\$?[\d,]+(?:\.\d+)?$',c):
    try:nums.append(float(c.replace('$','').replace(',','')))
    except:pass
  if len(nums)<2:continue
  desc=[]
  for c in cells[1:]:
   if not re.match(r'^\$?[\d,]+(?:\.\d+)?$',c) and c not in {'$'}:desc.append(c)
  d=' '.join(desc).strip()
  if d:rows.append({'raw':d,'name':norm(d),'value':nums[-1]})
 total=sum(r['value'] for r in rows)
 if total:
  for r in rows:r['weight']=100*r['value']/total
 return rows
def main():
 with gzip.open(BOOT,'rt',encoding='utf-8') as fh:b=json.load(fh)
 filings=b.get('snapshots',b) if isinstance(b,dict) else b;first=earliest_nport(filings)
 names={sid:(first.get(sid,{}).get('seriesName') or first.get(sid,{}).get('fundName') or '') for sid in CHOSEN}
 rows=[];aud=[];cache={}
 for sid,(cik,acc,form,rd) in CHOSEN.items():
  nf=first.get(sid)
  if not nf or not names[sid]:continue
  key=(cik,acc,form)
  if key not in cache:
   try:
    du=docs(cik,acc,form);hit=locate_doc(du,names[sid]);cache[key]=(du,hit)
   except Exception as e:cache[key]=([],None);aud.append({'sid':sid,'error':repr(e)})
  du,hit=cache[key]
  if not hit:continue
  score,nchars,url,text,tr=hit
  same_names=[names[x] for x,v in CHOSEN.items() if v[:3]==(cik,acc,form) and names.get(x)]
  seg=slice_series(text,names[sid],same_names);lh=parse_rows(seg)
  ph=[{'name':norm(h.get('issuerName') or ''),'weight':float(h.get('weight') or 0)} for h in nf.get('holdings',[]) if h.get('issuerName')]
  pnames={x['name'] for x in ph if x['name']};common=[h for h in lh if h['name'] in pnames]
  gap=(date.fromisoformat(nf['reportDate'])-date.fromisoformat(rd)).days
  rec={'seriesId':sid,'seriesName':names[sid],'ticker':(nf.get('fundTickers') or [nf.get('ticker')])[0] if (nf.get('fundTickers') or [nf.get('ticker')]) else None,'legacyForm':form,'legacyReportDate':rd,'nportReportDate':nf.get('reportDate'),'daysBetweenReports':gap,'legacyHoldings':len(lh),'nportHoldings':len(ph),'commonIssuerCount':len(common),'issuerCountOverlapRate':len(common)/len(lh) if lh else None,'legacyWeightOverlapRate':sum(x.get('weight',0) for x in common)/100 if lh else None,'documentUrl':url,'documentScore':score}
  rows.append(rec);print('PAIR',json.dumps(rec),flush=True)
 valid=[r for r in rows if r['issuerCountOverlapRate'] is not None and 10<=r['legacyHoldings']<=150]
 out={'purpose':'Gate B nearest-report fidelity. Legacy report selection was frozen from SEC series metadata/report dates before holdings inspection. No strategy returns used.','pairs':rows,'validPairs':len(valid),'medianDaysBetweenReports':statistics.median([r['daysBetweenReports'] for r in valid]) if valid else None,'medianIssuerCountOverlapRate':statistics.median([r['issuerCountOverlapRate'] for r in valid]) if valid else None,'minimumIssuerCountOverlapRate':min([r['issuerCountOverlapRate'] for r in valid]) if valid else None,'medianLegacyWeightOverlapRate':statistics.median([r['legacyWeightOverlapRate'] for r in valid]) if valid else None,'audits':aud}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in ('pairs','audits')}),flush=True)
if __name__=='__main__':main()
