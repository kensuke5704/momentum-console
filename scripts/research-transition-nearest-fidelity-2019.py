#!/usr/bin/env python3
from __future__ import annotations
import gzip,json,re,time,urllib.request,statistics
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'data/research/transition-nearest-fidelity-2019.json';BOOT=ROOT/'data/sec-nport/bootstrap.json.gz'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,text/html,*/*'}
# Frozen from report-date-only discovery run 33725924310 before holdings inspection.
CHOSEN={
'S000010977':('1329377','0001445546-19-003838','N-CSRS','2019-06-30'),'S000017177':('1329377','0001445546-19-003838','N-CSRS','2019-06-30'),'S000017178':('1329377','0001445546-19-003838','N-CSRS','2019-06-30'),
'S000033237':('1364608','0001445546-19-005018','N-CSR','2019-09-30'),'S000050385':('1364608','0001445546-19-005018','N-CSR','2019-09-30'),'S000044209':('1552740','0001445546-19-005047','N-CSR','2019-09-30'),
'S000053942':('1552740','0001445546-19-005049','N-CSRS','2019-09-30'),'S000053943':('1552740','0001445546-19-005049','N-CSRS','2019-09-30'),'S000053944':('1552740','0001445546-19-005049','N-CSRS','2019-09-30'),'S000053945':('1552740','0001445546-19-005049','N-CSRS','2019-09-30'),'S000053946':('1552740','0001445546-19-005049','N-CSRS','2019-09-30'),'S000053947':('1552740','0001445546-19-005049','N-CSRS','2019-09-30'),'S000053948':('1552740','0001445546-19-005049','N-CSRS','2019-09-30'),
'S000047480':('1467831','0000894189-18-004455','N-Q','2018-06-30'),'S000050191':('1467831','0000894189-18-004455','N-Q','2018-06-30'),'S000031813':('1408970','0001615774-19-003003','N-CSRS','2018-12-31'),'S000055090':('1408970','0001615774-19-003003','N-CSRS','2018-12-31'),'S000059263':('1408970','0001615774-19-003003','N-CSRS','2018-12-31')}
DOC_RE=re.compile(r'<TYPE>(N-Q|N-CSR|N-CSRS)\b.*?<FILENAME>\s*([^<\r\n]+)',re.I|re.S);NUM_RE=re.compile(r'^\$?\(?[\d,]+(?:\.\d+)?\)?$')
SCHED_RE=re.compile(r'Portfolio of Investments|Schedule of Investments|Portfolio Holdings',re.I)
STOP_RE=re.compile(r'\b(?:MONEY MARKET|SHORT[- ]TERM|REPURCHASE|PREFERRED|BONDS?|TOTAL INVESTMENTS|NET ASSETS|STATEMENTS? OF ASSETS)\b',re.I)
def get(url,timeout=45):
 last=None
 for u in ('https://r.jina.ai/'+url,url):
  try:
   req=urllib.request.Request(u,headers=UA)
   with urllib.request.urlopen(req,timeout=timeout) as r:raw=r.read(6_000_000)
   return raw.decode('utf-8','replace'),u
  except Exception as e:last=e;time.sleep(.5)
 raise last or RuntimeError('fetch failed')
def base(cik,acc):return f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace("-","")}'
def clean(s):return (s or '').replace('\u2009',' ').replace('\u2002',' ').replace('\xa0',' ').strip()
def num(s):
 try:return float(clean(s).replace('$','').replace(',','').replace('(','-').replace(')',''))
 except:return None
def norm(s):
 s=(s or '').upper().replace('&',' AND ');s=re.sub(r'\([^)]*\)',' ',s);s=s.replace('^',' ')
 for a,b in [('INCORPORATED','INC'),('CORPORATION','CORP'),('COMPANY','CO'),('LIMITED','LTD')]:s=re.sub(rf'\b{a}\b',b,s)
 s=re.sub(r'\bTHE\b',' ',s);return ' '.join(re.sub(r'[^A-Z0-9]+',' ',s).split())
def earliest_nport(filings):
 out={}
 for f in sorted(filings,key=lambda x:(x.get('reportDate',''),x.get('filingDate',''),x.get('accession',''))):
  sid=f.get('seriesId')
  if sid and sid not in out:out[sid]=f
 return out
def docs(cik,acc,form):
 h,_=get(f'{base(cik,acc)}/{acc}-index-headers.html');return [f'{base(cik,acc)}/{fn.strip()}' for typ,fn in DOC_RE.findall(h) if typ.upper()==form]
def locate_doc(urls,series_name):
 hits=[]
 for u in urls:
  try:
   text,tr=get(u);score=(2 if series_name.lower() in text.lower() else 0)+(1 if SCHED_RE.search(text) else 0)
   hits.append((score,len(text),u,text,tr))
  except Exception:pass
 hits.sort(key=lambda x:(x[0],x[1]),reverse=True);return hits[0] if hits else None
def structural_start(ls,name):
 hits=[i for i,x in enumerate(ls) if name.lower() in x.lower()]
 candidates=[]
 for i in hits:
  local='\n'.join(ls[max(0,i-15):min(len(ls),i+20)])
  if not SCHED_RE.search(local):continue
  # Distance to nearest schedule marker; exact title near marker outranks all other mentions.
  ds=[abs(j-i) for j in range(max(0,i-15),min(len(ls),i+20)) if SCHED_RE.search(ls[j])]
  candidates.append((min(ds) if ds else 99,i))
 if candidates:return min(candidates)[1]
 return None
def slice_series(text,name,all_names):
 ls=text.splitlines();i=structural_start(ls,name)
 if i is None:return ''
 start=max(0,i-15);end=min(len(ls),i+1600)
 for j in range(i+1,end):
  if any(n!=name and n.lower() in ls[j].lower() and structural_start(ls[max(0,j-5):min(len(ls),j+15)],n) is not None for n in all_names):end=j;break
  if j>i+40 and re.search(r'^\s*Statements? of Assets',ls[j],re.I):end=j;break
 return '\n'.join(ls[start:end])
def finish(rows):
 # Dedupe exact repeated rows from continuation/header rendering.
 seen=set();out=[]
 for r in rows:
  k=(r['name'],round(r['value'],4))
  if not r['name'] or k in seen:continue
  seen.add(k);out.append(r)
 total=sum(r['value'] for r in out)
 if total:
  for r in out:r['weight']=100*r['value']/total
 return out
def parse_tabular(seg):
 rows=[];in_common=False
 for raw in seg.splitlines():
  line=clean(raw)
  if re.search(r'\bCOMMON STOCKS?\b',line,re.I):in_common=True;continue
  if in_common and STOP_RE.search(line):in_common=False;continue
  if not in_common:continue
  cells=[clean(c) for c in re.split(r'\t+',raw) if clean(c) not in {'','$','—','-'}]
  if len(cells)<3 or not NUM_RE.match(cells[0]):continue
  ns=[num(c) for c in cells if NUM_RE.match(c)];ns=[x for x in ns if x is not None]
  if len(ns)<2:continue
  desc=' '.join(c for c in cells[1:] if not NUM_RE.match(c) and c!='$').strip()
  if desc and not desc.lower().startswith('total '):rows.append({'raw':desc,'name':norm(desc),'value':ns[-1]})
 return finish(rows)
def compact_tokens(seg):return [clean(x) for x in seg.splitlines() if clean(x) and clean(x) not in {'$','—','-','<PAGE>','<TABLE>','</TABLE>','<CAPTION>','</CAPTION>'}]
def parse_vertical(seg):
 toks=compact_tokens(seg);rows=[];in_common=False;i=0
 while i<len(toks):
  t=toks[i]
  if re.search(r'\bCOMMON STOCKS?\b',t,re.I):in_common=True;i+=1;continue
  if in_common and STOP_RE.search(t):in_common=False;i+=1;continue
  if not in_common:i+=1;continue
  # Headings / totals / notes are never holdings descriptions.
  if NUM_RE.match(t) or re.search(r'\s[-—–]\s*\(?\d+(?:\.\d+)?\)?%$',t) or t.lower().startswith(('total ','cost ','percentages ','shares','value')):
   i+=1;continue
  # Structural vertical row: description followed by the next two numeric tokens, allowing formatting tokens/headings only before first numeric.
  vals=[];idx=[]
  for j in range(i+1,min(len(toks),i+12)):
   if re.search(r'\bCOMMON STOCKS?\b',toks[j],re.I) or STOP_RE.search(toks[j]):break
   if NUM_RE.match(toks[j]):vals.append(num(toks[j]));idx.append(j)
   elif vals:break
   if len(vals)>=2:break
  if len(vals)>=2 and vals[0] is not None and vals[1] is not None:
   rows.append({'raw':t,'name':norm(t),'value':vals[1]});i=idx[1]+1;continue
  i+=1
 return finish(rows)
def parse_fixed(seg):
 rows=[];in_common=False
 for raw in seg.splitlines():
  line=clean(raw)
  if re.search(r'\bCOMMON STOCKS?\b',line,re.I):in_common=True;continue
  if in_common and STOP_RE.search(line):in_common=False;continue
  if not in_common or not line:continue
  # Fixed-width SEC text: shares / issuer / market value separated by 2+ spaces.
  cells=[clean(c) for c in re.split(r'\s{2,}',raw.strip()) if clean(c)]
  if len(cells)<3:continue
  ni=[k for k,c in enumerate(cells) if NUM_RE.match(c)]
  if len(ni)<2:continue
  q,v=ni[0],ni[-1]
  if q!=0 or v<=q+1:continue
  desc=' '.join(cells[q+1:v]).strip()
  vv=num(cells[v])
  if desc and vv and not desc.lower().startswith('total '):rows.append({'raw':desc,'name':norm(desc),'value':vv})
 return finish(rows)
def parse_rows(seg):
 candidates=[('tabular',parse_tabular(seg)),('vertical',parse_vertical(seg)),('fixed',parse_fixed(seg))]
 plausible=[x for x in candidates if 5<=len(x[1])<=250]
 if plausible:return max(plausible,key=lambda x:len(x[1]))
 return max(candidates,key=lambda x:len(x[1]))
def main():
 with gzip.open(BOOT,'rt',encoding='utf-8') as fh:b=json.load(fh)
 filings=b.get('snapshots',b) if isinstance(b,dict) else b;first=earliest_nport(filings);names={sid:(first.get(sid,{}).get('seriesName') or first.get(sid,{}).get('fundName') or '') for sid in CHOSEN}
 rows=[];aud=[];cache={}
 for sid,(cik,acc,form,rd) in CHOSEN.items():
  nf=first.get(sid)
  if not nf or not names[sid]:continue
  key=(cik,acc,form)
  if key not in cache:
   try:du=docs(cik,acc,form);cache[key]=(du,{u:locate_doc([u],names[sid]) for u in du})
   except Exception as e:cache[key]=([],{});aud.append({'sid':sid,'error':repr(e)})
  du,docmap=cache[key]
  # Select among form documents by structural series occurrence, not by holdings outcome.
  hits=[]
  for u in du:
   hit=docmap.get(u)
   if not hit:
    try:hit=locate_doc([u],names[sid]);docmap[u]=hit
    except:continue
   if hit and structural_start(hit[3].splitlines(),names[sid]) is not None:hits.append(hit)
  if not hits:
   # Some vertical filings have exact title + schedule but alternative punctuation; retain best exact-name document.
   hit=locate_doc(du,names[sid])
   if not hit:continue
  else:hit=sorted(hits,key=lambda x:(x[0],x[1]),reverse=True)[0]
  score,nchars,url,text,tr=hit;same_names=[names[x] for x,v in CHOSEN.items() if v[:3]==(cik,acc,form) and names.get(x)]
  seg=slice_series(text,names[sid],same_names)
  if not seg:
   # Vertical documents usually have exact title immediately before Schedule of Investments.
   ls=text.splitlines();hs=[i for i,x in enumerate(ls) if names[sid].lower() in x.lower()]
   for i in hs:
    if SCHED_RE.search('\n'.join(ls[i:min(len(ls),i+12)])):seg='\n'.join(ls[i:min(len(ls),i+1800)]);break
  grammar,lh=parse_rows(seg)
  ph=[{'name':norm(h.get('issuerName') or ''),'weight':float(h.get('weight') or 0)} for h in nf.get('holdings',[]) if h.get('issuerName')];pnames={x['name'] for x in ph if x['name']};common=[h for h in lh if h['name'] in pnames]
  gap=(date.fromisoformat(nf['reportDate'])-date.fromisoformat(rd)).days
  rec={'seriesId':sid,'seriesName':names[sid],'ticker':(nf.get('fundTickers') or [nf.get('ticker')])[0] if (nf.get('fundTickers') or [nf.get('ticker')]) else None,'legacyForm':form,'legacyReportDate':rd,'nportReportDate':nf.get('reportDate'),'daysBetweenReports':gap,'parserGrammar':grammar,'legacyHoldings':len(lh),'nportHoldings':len(ph),'commonIssuerCount':len(common),'issuerCountOverlapRate':len(common)/len(lh) if lh else None,'legacyWeightOverlapRate':sum(x.get('weight',0) for x in common)/100 if lh else None,'documentUrl':url,'documentScore':score}
  rows.append(rec);print('PAIR',json.dumps(rec),flush=True)
 valid=[r for r in rows if r['issuerCountOverlapRate'] is not None and 10<=r['legacyHoldings']<=150]
 out={'purpose':'Gate B nearest-report fidelity. Legacy report selection and parser grammars are structural and fixed independently of overlap/returns. No strategy returns used.','pairs':rows,'validPairs':len(valid),'medianDaysBetweenReports':statistics.median([r['daysBetweenReports'] for r in valid]) if valid else None,'medianIssuerCountOverlapRate':statistics.median([r['issuerCountOverlapRate'] for r in valid]) if valid else None,'minimumIssuerCountOverlapRate':min([r['issuerCountOverlapRate'] for r in valid]) if valid else None,'medianLegacyWeightOverlapRate':statistics.median([r['legacyWeightOverlapRate'] for r in valid]) if valid else None,'audits':aud}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in ('pairs','audits')}),flush=True)
if __name__=='__main__':main()
