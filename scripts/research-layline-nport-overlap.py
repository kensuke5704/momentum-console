#!/usr/bin/env python3
from __future__ import annotations
import csv, gzip, io, json, math, re, statistics, urllib.request, zipfile
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
META='https://dataverse.harvard.edu/api/datasets/:persistentId/?persistentId=doi:10.7910/DVN/TZM1QT'
UA={'User-Agent':'momentum-console research'}
YEAR=2020
SOURCE_YEARS=[2019,2020]
TOPN=80
OUT=ROOT/'data'/'research'/'layline13f-nport-overlap-2020.json'

def get(url:str)->bytes:
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=300) as r:return r.read()

def norm_name(s:str)->str:
    s=(s or '').upper().replace('&',' AND ')
    s=re.sub(r'\b(CLASS|CL)\s+[A-Z0-9]+\b',' ',s)
    s=re.sub(r'\b(COMMON STOCK|COM STK|COMMON|ORDINARY SHARES?|ORD SHS?)\b',' ',s)
    s=re.sub(r'\b(INCORPORATED|INCORPORATION|INC|CORPORATION|CORP|COMPANY|CO|LIMITED|LTD|PLC|HOLDINGS?|HLDGS?|GROUP)\b',' ',s)
    s=re.sub(r'[^A-Z0-9]+',' ',s)
    return ' '.join(s.split())

def aliases():
    names=defaultdict(set)
    boot=ROOT/'data'/'sec-nport'/'bootstrap.json.gz'
    with gzip.open(boot,'rt',encoding='utf-8') as f:obj=json.load(f)
    for filing in obj.get('snapshots') or obj.get('filings') or []:
        for h in filing.get('holdings',[]):
            sym=str(h.get('symbol') or '').strip().upper(); nm=norm_name(str(h.get('issuerName') or ''))
            if sym and nm:names[nm].add(sym)
    prof=ROOT/'public'/'data'/'company-profiles.json'
    if prof.exists():
        p=json.loads(prof.read_text())
        for sym,x in (p.get('profiles') or {}).items():
            nm=norm_name(str(x.get('companyName') or ''))
            if nm:names[nm].add(sym.upper())
    return {n:next(iter(v)) for n,v in names.items() if len(v)==1}

def nport_months():
    u=json.loads((ROOT/'data'/'universe-history.json').read_text())
    return {x['signalMonth']:{'asOf':x['asOf'],'symbols':[s['symbol'] for s in x.get('symbols',[])[:TOPN]]} for x in u.get('history',[]) if x['signalMonth'].startswith(f'{YEAR}-')}

def parse_accept(s:str)->str:
    s=(s or '').strip()
    return f'{s[:4]}-{s[4:6]}-{s[6:8]}' if len(s)>=8 else ''

def add_panel(filings:dict, payload:bytes, label:str):
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        fn=z.namelist()[0]
        with z.open(fn) as raw:
            rd=csv.DictReader(io.TextIOWrapper(raw,encoding='utf-8-sig',errors='replace',newline=''))
            for i,r in enumerate(rd,1):
                if (r.get('putCall') or '').strip():continue
                acc=r.get('accessionNumber') or ''; cik=r.get('cik') or ''; accepted=parse_accept(r.get('acceptanceDatetime') or '')
                if not acc or not cik or not accepted:continue
                try:v=float(r.get('value') or 0)
                except:continue
                if v<=0:continue
                f=filings.get(acc)
                if f is None:
                    f={'cik':cik,'accepted':accepted,'holdings':defaultdict(lambda:['',0.0]),'total':0.0};filings[acc]=f
                cusip=(r.get('cusip') or '').strip().upper(); issuer=(r.get('nameOfIssuer') or '').strip()
                if not cusip:continue
                f['total']+=v; h=f['holdings'][cusip]; h[0]=issuer; h[1]+=v
                if i%1000000==0:print(f'{label} rows={i:,} totalFilings={len(filings):,}',flush=True)

def main():
    a=aliases(); months=nport_months(); print(f'aliases={len(a)} months={len(months)}')
    meta=json.loads(get(META)); files=meta['data']['latestVersion']['files']; by={x['dataFile']['filename']:x['dataFile'] for x in files}
    filings={}
    for yr in SOURCE_YEARS:
        target=by[f'hr_panel_{yr}.zip']
        print(f'download {target["filename"]} {target["filesize"]} bytes',flush=True)
        add_panel(filings,get(f'https://dataverse.harvard.edu/api/access/datafile/{target["id"]}'),str(yr))
    print(f'parsed filings={len(filings):,}',flush=True)
    results=[]
    for month,m in sorted(months.items()):
        asof=m['asOf']; latest={}
        for acc,f in filings.items():
            if f['accepted']<=asof:
                cur=latest.get(f['cik'])
                if cur is None or (f['accepted'],acc)>(cur[1]['accepted'],cur[0]):latest[f['cik']]=(acc,f)
        rows=defaultdict(lambda:{'managers':set(),'agg':0.0,'max':0.0,'rec':0.0,'issuer':''})
        ad=date.fromisoformat(asof)
        for acc,f in latest.values():
            total=f['total']
            if total<=0:continue
            age=max(0,(ad-date.fromisoformat(f['accepted'])).days); rf=math.exp(-age/120)
            for cusip,(issuer,v) in f['holdings'].items():
                w=100*v/total; x=rows[cusip]; x['managers'].add(f['cik']);x['agg']+=w;x['max']=max(x['max'],w);x['rec']+=w*rf;x['issuer']=issuer
        ranked=[]
        for cusip,x in rows.items():
            cnt=len(x['managers'])
            if cnt<2 and x['max']<4:continue
            score=3*math.log1p(cnt)+.5*math.log1p(x['agg'])+.5*math.log1p(x['rec'])
            sym=a.get(norm_name(x['issuer']))
            ranked.append((score,cnt,x['agg'],cusip,x['issuer'],sym))
        ranked.sort(key=lambda x:(-x[0],-x[1],-x[2],x[3]))
        top=ranked[:TOPN]; syms=[x[5] for x in top if x[5]]; target_syms=m['symbols']; inter=set(syms)&set(target_syms)
        mapped_overlap=len(inter)/len(set(syms)) if syms else None
        results.append({'month':month,'asOf':asof,'latestManagers':len(latest),'raw13fTopCount':len(top),'mapped13fTopCount':len(syms),'mappingCoverageTop80':len(syms)/TOPN,'intersection':len(inter),'overlapVsNport':len(inter)/len(target_syms) if target_syms else None,'overlapAmongMapped13f':mapped_overlap,'jaccardOnMapped':len(inter)/len(set(syms)|set(target_syms)) if (set(syms)|set(target_syms)) else None,'mapped13fTopSymbols':syms,'nportSymbols':target_syms,'unmatchedTop13f':[{'cusip':x[3],'issuer':x[4],'managerCount':x[1]} for x in top if not x[5]][:20]})
        print(f'{month} managers={len(latest)} mapped={len(syms)}/80 overlap={len(inter)}/{len(target_syms)} conditional={(mapped_overlap if mapped_overlap is not None else 0):.3f}',flush=True)
    cov=[x['mappingCoverageTop80'] for x in results]; ov=[x['overlapVsNport'] for x in results if x['overlapVsNport'] is not None]; cond=[x['overlapAmongMapped13f'] for x in results if x['overlapAmongMapped13f'] is not None]
    summary={'source':'Layline Institutional Holding Reports / Harvard Dataverse DOI 10.7910/DVN/TZM1QT','year':YEAR,'sourceYears':SOURCE_YEARS,'method':'All-manager 13F breadth proxy; latest accepted filing per CIK; long non-option positions; production N-PORT score formula; conservative issuer-name mapping to ticker.','months':len(results),'mappingCoverageTop80':{'mean':statistics.mean(cov),'median':statistics.median(cov),'min':min(cov)},'overlapVsNport':{'mean':statistics.mean(ov),'median':statistics.median(ov),'min':min(ov),'max':max(ov)},'overlapAmongMapped13f':{'mean':statistics.mean(cond),'median':statistics.median(cond),'min':min(cond),'max':max(cond)},'results':results}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(summary,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in summary.items() if k!='results'}))

if __name__=='__main__':main()
