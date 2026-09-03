#!/usr/bin/env python3
from __future__ import annotations
import gzip,json,math,re,statistics,urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BOOT=ROOT/'data/sec-nport/bootstrap.json.gz';HISTORY=ROOT/'data/universe-history.json';MAN=ROOT/'data/research/gate-b-production-source-manifest-2020.json';OUT=ROOT/'data/research/gate-b-aggregate-shadow-2020.json'
UA={'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'text/plain,text/html,*/*'}
MARKUP=re.compile(r'[*_]+')
NONUS={'AUSTRALIA','BRAZIL','CANADA','CHINA','FRANCE','GERMANY','HONG KONG','ISRAEL','JAPAN','LUXEMBOURG','NETHERLANDS','RUSSIA','SINGAPORE','SOUTH KOREA','SPAIN','SWITZERLAND','UNITED KINGDOM'}

def plain(s):return ' '.join(MARKUP.sub('',s or '').replace('\xa0',' ').split())
def fetch(url,limit=14_000_000):
 last=None
 for u in ('https://r.jina.ai/'+url,url):
  try:
   req=urllib.request.Request(u,headers=UA)
   with urllib.request.urlopen(req,timeout=50) as r:return r.read(limit).decode('utf-8','replace'),u
  except Exception as e:last=repr(e)
 raise RuntimeError(last or 'fetch failed')

def filing_date(src):
 if src.get('filingDate'):return src['filingDate']
 acc=src['sourceAccession'];digits=acc.replace('-','');cik=str(int(src['registrantCik']));base=f'https://www.sec.gov/Archives/edgar/data/{cik}/{digits}/'
 for name in (acc+'-index-headers.html',acc+'-index.htm'):
  try:
   txt,_=fetch(base+name,2_000_000)
   m=re.search(r'FILED AS OF DATE:\s*(\d{8})',txt,re.I)
   if m:
    x=m.group(1);return f'{x[:4]}-{x[4:6]}-{x[6:8]}'
   m=re.search(r'Filing Date\s*(?:<[^>]+>\s*)*(\d{4}-\d{2}-\d{2})',txt,re.I|re.S)
   if m:return m.group(1)
  except Exception:pass
 raise RuntimeError(f"{src['seriesId']}: filing date unresolved; aggregate scoring aborted")

def production_month(raw,month='2020-01'):
 def walk(x):
  if isinstance(x,dict):
   if x.get('signalMonth')==month:return x
   for v in x.values():
    r=walk(v)
    if r:return r
  elif isinstance(x,list):
   for v in x:
    r=walk(v)
    if r:return r
  return None
 r=walk(raw)
 if not r:raise RuntimeError('Production month not found')
 return r

# Exact Gate A issuer identity semantics.
def ga_norm(raw):
 s=(raw or '').upper().replace('&',' AND ');s=re.sub(r'\b(INCORPORATED|INCORPORATION)\b','INC',s);s=re.sub(r'\b(CORPORATION|CORPORA?TION)\b','CORP',s);s=re.sub(r'\bCOMPANY\b','CO',s);s=re.sub(r'\bLIMITED\b','LTD',s);s=re.sub(r'\bHLDGS\b','HOLDINGS',s);s=re.sub(r'\bPHARMACEUTICALS\b','PHARMACEUTICAL',s);return ' '.join(re.sub(r'[^A-Z0-9]+',' ',s).split())
def ga_aliases(raw):
 n=ga_norm(raw);out=[n] if n else []
 if n.startswith('THE '):out.append(n[4:])
 if n.endswith(' THE'):out.append(n[:-4])
 return list(dict.fromkeys(x for x in out if x))
def legacy_identity(raw):
 s=raw or ''
 # Structural security-class adapter only; issuer similarity is still Gate A exact aliasing.
 s=re.sub(r'\s*\((?:[a-z]|\d+)\)\s*$','',s,flags=re.I)
 s=re.sub(r'\s*\((?:Australia|Brazil|Canada|China|France|Germany|Hong Kong|Israel|Japan|Luxembourg|Netherlands|Russia|Singapore|South Korea|Spain|Switzerland|United Kingdom|United States)\)\s*$','',s,flags=re.I)
 s=re.sub(r',?\s*(?:Class\s+[A-Z0-9]+(?:\s+Shares?)?|(?:Non[- ]?Voting|Voting)\s+Shares?|Shares?)\s*$','',s,flags=re.I)
 return s.strip(' ,.')
def explicit_country(raw):
 m=re.search(r'\(([^()]*)\)\s*(?:\([a-z]\))?\s*$',raw or '',re.I)
 return m.group(1).strip().upper() if m else None

def build_master(filings,asof):
 by=defaultdict(lambda:defaultdict(set))
 for f in filings:
  if f.get('filingDate','')>asof:continue
  sid=f.get('seriesId','')
  for h in f.get('holdings',[]):
   sym=(h.get('symbol') or '').strip().upper();issuer=h.get('issuerName') or ''
   if not sym or not issuer:continue
   for a in ga_aliases(issuer):by[a][sym].add(sid)
 return by
def resolve(master,sid,raw):
 issuer=legacy_identity(raw)
 for a in ga_aliases(issuer):
  c=sorted({sym for sym,sids in master.get(a,{}).items() if any(x!=sid for x in sids)})
  if len(c)==1:return c[0]
  if len(c)>1:return ''
 return ''

def schedule_segment(text,series):
 # Reuse the verified source-fidelity structural rule: exact series title + nearby real schedule header.
 lines=text.splitlines();title_positions=[i for i,x in enumerate(lines) if series.lower() in x.lower()]
 for t in title_positions:
  for i in range(max(0,t-12),min(len(lines),t+20)):
   if not re.search(r'^\s*Schedule of Investments|^\s*Portfolio of Investments',plain(lines[i]),re.I):continue
   window='\n'.join(plain(x) for x in lines[min(t,i):min(len(lines),max(t,i)+40)])
   if re.search(r'COMMON STOCK',window,re.I) and re.search(r'\b(?:Security|Description)\b.*\b(?:Shares|Value)\b|\bShares\b.*\b(?:Security Description|Description)\b.*\bValue\b',window,re.I):
    return lines[min(t,i):min(len(lines),min(t,i)+5000)]
 for i,x in enumerate(lines):
  if not re.search(r'SCHEDULE OF INVESTMENTS|PORTFOLIO OF INVESTMENTS',x,re.I):continue
  window='\n'.join(lines[i:min(len(lines),i+25)])
  if series.lower() in window.lower() and re.search(r'COMMON STOCK',window,re.I):return lines[i:min(len(lines),i+5000)]
 st=title_positions[-1] if title_positions else 0;return lines[st:min(len(lines),st+5000)]

def extract_clearbridge(text,series):
 lines=schedule_segment(text,series);inside=False;rows=[];net=None
 pat=re.compile(r'^(.*?\D)(\d[\d,]*)\s*\$?\s*(\d[\d,]*)(?:\s*\*)?$')
 for raw in lines:
  line=plain(raw)
  if re.search(r'\bCommon Stocks\s*[—-]\s*98\.0%',line,re.I):inside=True;continue
  if inside and re.search(r'Total Investments before Short-Term|Short-Term Investments',line,re.I):inside=False
  if re.search(r'Total Net Assets\s*[—-]\s*100\.0%',line,re.I):
   nums=re.findall(r'\d[\d,]*',line);net=float(nums[-1].replace(',','')) if nums else net
  if not inside or re.search(r'\bTotal\b|\d+(?:\.\d+)?%$',line,re.I):continue
  m=pat.match(line)
  if m:
   desc=m.group(1).strip(' .');v=float(m.group(3).replace(',',''))
   if re.search(r'[A-Za-z]',desc) and v>0:rows.append((desc,v))
 return rows,net

def extract_ppty(text,series):
 lines=schedule_segment(text,series);cleaned=[plain(x) for x in lines];inside=False;rows=[];net=None
 for i,line in enumerate(cleaned):
  if re.search(r'^COMMON STOCKS\s*-\s*100\.0%',line,re.I):inside=True;continue
  if inside and re.search(r'^TOTAL COMMON STOCKS',line,re.I):inside=False
  if re.search(r'^NET ASSETS\s*-\s*100\.0%',line,re.I):
   scan=' '.join(x for x in cleaned[i:min(len(cleaned),i+8)] if x);nums=re.findall(r'\b\d[\d,]*\b',scan);net=float(nums[-1].replace(',','')) if nums else net
  if not inside or not line or not re.search(r'[A-Za-z]',line):continue
  if re.search(r'\d+(?:\.\d+)?\s*%$',line) or re.match(r'^(TOTAL|COMMON STOCK|SHARES|SECURITY DESCRIPTION|VALUE|SCHEDULE OF INVESTMENTS)',line,re.I):continue
  # PPTY rendering: shares occurs shortly before issuer; value occurs shortly after issuer, with optional standalone '$'.
  prev=[x for x in cleaned[max(0,i-5):i] if x];foll=[x for x in cleaned[i+1:min(len(cleaned),i+6)] if x]
  if not any(re.fullmatch(r'\d[\d,]*',x) for x in prev):continue
  value=None
  for x in foll:
   if re.search(r'[A-Za-z]',x):break
   if x=='$':continue
   if re.fullmatch(r'\$?\d[\d,]*',x):value=float(x.replace('$','').replace(',',''));break
  if value and value>0:rows.append((line,value))
 return rows,net

def extract_gfin(text,series):
 lines=schedule_segment(text,series);rows=[];net=None;inside=False;started=False
 for i,raw in enumerate(lines):
  line=plain(raw)
  if re.search(r'^Common Stocks?\s*[–—-]',line,re.I):inside=True;started=True;continue
  if inside and re.search(r'^(?:Repurchase Agreements?|Short-Term Investments?|Securities Lending|Total Investments)',line,re.I):inside=False
  if inside:
   m=re.match(r'^([\d,]+)\s+(.+?)\s+(?:\$\s*)?([\d,]+)\s*$',line)
   if m:
    desc=re.sub(r'\s*\([a-z]\)\s*$','',m.group(2),flags=re.I).strip();v=float(m.group(3).replace(',',''))
    if re.search(r'[A-Za-z]',desc) and not re.match(r'^(Total|Common Stocks)',desc,re.I):rows.append((desc,v))
  if started and re.search(r'^NET ASSETS\s*[–—-]\s*100\.0%\s*\$?\s*[\d,]+',line,re.I):
   nums=re.findall(r'\d[\d,]*',line);net=float(nums[-1].replace(',','')) if nums else net;break
  if started and re.search(r'^Total Investments\s*[–—-]\s*(\d+(?:\.\d+)?)%',line,re.I) and net is None:
   pct=float(re.search(r'(\d+(?:\.\d+)?)%',line).group(1));scan=' '.join(plain(x) for x in lines[i:min(len(lines),i+5)] if plain(x));vals=re.findall(r'\$\s*([\d,]+)',scan)
   if vals and pct>0:net=float(vals[-1].replace(',',''))/(pct/100.0)
 return rows,net

def source_from_legacy(src,text,master,asof):
 parser={'S000057700':extract_clearbridge,'S000063326':extract_gfin,'S000061208':extract_ppty}[src['seriesId']];rows,net=parser(text,src['seriesName'])
 if not net or len(rows)<10:raise RuntimeError(f"{src['seriesId']}: invalid extraction rows={len(rows)} net={net}")
 raw=[{'description':d,'value':v,'weight':100*v/net,'country':explicit_country(d)} for d,v in rows]
 total=sum(x['weight'] for x in raw);top10=sum(sorted((x['weight'] for x in raw),reverse=True)[:10]);eligible=10<=len(raw)<=120 and total>=50 and top10>=25
 mapped=[];mc=mw=0
 for h in raw:
  # Conditional EC+explicit-country bridge: only explicit NON-US is excluded; missing country is preserved as UNKNOWN, not asserted US.
  if h['country'] in NONUS:continue
  sym=resolve(master,src['seriesId'],h['description'])
  if sym:mc+=1;mw+=h['weight'];mapped.append({'symbol':sym,'issuerName':legacy_identity(h['description']),'weight':h['weight']})
 merged={}
 for h in mapped:
  r=merged.setdefault(h['symbol'],{'symbol':h['symbol'],'issuerName':h['issuerName'],'weight':0.0});r['weight']+=h['weight']
 return {'seriesId':src['seriesId'],'seriesName':src['seriesName'],'filingDate':src['filingDate'],'reportDate':src['sourceReportDate'],'holdings':list(merged.values())},{'seriesId':src['seriesId'],'rawCommonEquityCount':len(raw),'rawWeightTotal':total,'top10Weight':top10,'structuralEligible':eligible,'mappedCount':mc,'mappedCountRate':mc/len(raw) if raw else None,'mappedWeight':mw,'mappedWeightRate':mw/total if total else None,'mappedUniqueSymbols':len(merged),'explicitNonUsCount':sum(h['country'] in NONUS for h in raw),'derivedNetAssets':net}

def score(sources,asof):
 rows={}
 for f in sources:
  rec=math.exp(-max(0,(date.fromisoformat(asof)-date.fromisoformat(f['filingDate'])).days)/120)
  for h in f['holdings']:
   w=h['weight'];sym=h['symbol']
   if not sym or w<=0:continue
   r=rows.setdefault(sym,{'seriesIds':set(),'aggregateWeight':0.0,'maxWeight':0.0,'recencyWeight':0.0});r['seriesIds'].add(f['seriesId']);r['aggregateWeight']+=w;r['maxWeight']=max(r['maxWeight'],w);r['recencyWeight']+=w*rec
 out=[]
 for sym,r in rows.items():
  ec=len(r['seriesIds'])
  if ec<2 and r['maxWeight']<4:continue
  sc=3*math.log1p(ec)+.5*math.log1p(r['aggregateWeight'])+.5*math.log1p(r['recencyWeight']);out.append({'symbol':sym,'etfCount':ec,'aggregateWeight':r['aggregateWeight'],'maxWeight':r['maxWeight'],'recencyWeight':r['recencyWeight'],'universeScore':sc})
 out.sort(key=lambda x:(-x['universeScore'],-x['etfCount'],-x['aggregateWeight'],x['symbol']))
 for i,x in enumerate(out[:80],1):x['universeRank']=i
 return out[:80]
def corr(x,y):
 if len(x)<2:return None
 mx=statistics.mean(x);my=statistics.mean(y);dx=[a-mx for a in x];dy=[b-my for b in y];den=math.sqrt(sum(a*a for a in dx)*sum(b*b for b in dy));return sum(a*b for a,b in zip(dx,dy))/den if den else None

def main():
 man=json.loads(MAN.read_text());hist=production_month(json.loads(HISTORY.read_text()));asof=hist['asOf'];prod=[x['symbol'] for x in hist['symbols']]
 with gzip.open(BOOT,'rt',encoding='utf-8') as fh:b=json.load(fh)
 filings=b.get('snapshots',b) if isinstance(b,dict) else b;master=build_master(filings,asof)
 sources=[];mapping=[];resolved=[]
 for s0 in man['sources']:
  s=dict(s0);s['filingDate']=filing_date(s);text,tr=fetch(s['sourceDocumentUrl']);src,m=source_from_legacy(s,text,master,asof);sources.append(src);mapping.append(m);resolved.append({'seriesId':s['seriesId'],'filingDate':s['filingDate'],'transport':tr})
 if not all(m['structuralEligible'] for m in mapping):raise RuntimeError('At least one reconstructed source fails structural eligibility')
 candrows=score(sources,asof);cand=[x['symbol'] for x in candrows];common=set(prod)&set(cand);pr={s:i+1 for i,s in enumerate(prod)};cr={s:i+1 for i,s in enumerate(cand)};top2=prod[:2];hits=sum(s in set(cand) for s in top2)
 metrics={'productionK':len(prod),'candidateSize':len(cand),'topKOverlap':len(common)/len(prod),'commonNames':len(common),'spearmanCommonRanks':corr([pr[s] for s in common],[cr[s] for s in common]),'productionTop2':top2,'top2Hits':hits,'top2IndividualRetention':hits/len(top2)}
 out={'purpose':'Conditional 2020-01 Gate B aggregate shadow using the three source series known from Production. Tests legacy holdings -> PIT cross-series identity mapping -> canonical breadth scoring. This does NOT validate historical discovery of the source ETF series and therefore cannot by itself authorize historical builder implementation. No strategy returns used.','signalMonth':'2020-01','asOf':asof,'resolvedSources':resolved,'sourceMapping':mapping,'productionUniverse':prod,'candidateUniverse':cand,'candidateRows':candrows,'metrics':metrics,'limitations':['Source-series membership is conditioned on the exact three Production source series.','Explicit non-US country annotations are excluded; holdings with no country annotation remain UNKNOWN and are not asserted US.','General historical source discovery plus US/CORP filtering remains a separate Gate B requirement.']}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SOURCES',json.dumps(resolved),flush=True);print('MAPPING',json.dumps(mapping),flush=True);print('CANDIDATE',json.dumps(cand),flush=True);print('METRICS',json.dumps(metrics),flush=True)
if __name__=='__main__':main()
