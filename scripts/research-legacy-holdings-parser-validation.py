#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import re
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRIVE = 'https://drive.usercontent.google.com/download?id=1yfQxR45DZ_vM5pkFvgyexc10NNqbxpFN&export=download&confirm=t'
UA = {'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'*/*'}
OUT = ROOT/'data'/'research'/'legacy-holdings-parser-validation.json'
YEARS=(2006,2008,2010)
TARGET=re.compile(r'^(?:I?SHARES (?:TRUST|INC)|SELECT SECTOR SPDR TRUST)$',re.I)

ss=importlib.util.spec_from_file_location('seg',ROOT/'scripts'/'research-nq-series-segmentation-2006.py')
seg=importlib.util.module_from_spec(ss);ss.loader.exec_module(seg)
ps=importlib.util.spec_from_file_location('pit',ROOT/'scripts'/'research-nq-pit-holdings-2006.py')
pit=importlib.util.module_from_spec(ps);ps.loader.exec_module(pit)
ls=importlib.util.spec_from_file_location('legacy',ROOT/'scripts'/'research-legacy-holdings-parser.py')
legacy=importlib.util.module_from_spec(ls);ls.loader.exec_module(legacy)


def download(path:Path):
    req=urllib.request.Request(DRIVE,headers=UA)
    with urllib.request.urlopen(req,timeout=600) as r,open(path,'wb') as f:
        while True:
            b=r.read(1024*1024)
            if not b:break
            f.write(b)


def choose():
    result=[]
    with tempfile.TemporaryDirectory() as td:
        zp=Path(td)/'master.zip';download(zp)
        with zipfile.ZipFile(zp) as z:
            names=z.namelist()
            for year in YEARS:
                rows=[]
                for name in sorted(n for n in names if re.search(rf'master_{year}_QTR[1-4]\.idx$',n)):
                    for line in z.read(name).decode('latin-1','replace').splitlines():
                        p=line.split('|')
                        if len(p)<5:continue
                        cik,company,form,date_filed,filename=[x.strip() for x in p[:5]]
                        if form.upper()=='N-Q' and date_filed.startswith(str(year)) and TARGET.match(company):
                            rows.append({'year':year,'cik':cik,'company':company,'dateFiled':date_filed,'filename':filename})
                seen=set()
                for x in sorted(rows,key=lambda r:(r['dateFiled'],r['cik'],r['filename'])):
                    if x['cik'] in seen:continue
                    seen.add(x['cik']);result.append(x)
    return result


def normalized(hs):
    positive=[h for h in hs if float(h.get('marketValue') or 0)>0 and h.get('description')]
    total=sum(float(h['marketValue']) for h in positive)
    if total:
        for h in positive:h['weight']=100*float(h['marketValue'])/total
        positive.sort(key=lambda h:h['weight'],reverse=True)
    return positive,total


def main():
    records=[]
    for x in choose():
        try:
            _,submission=seg.meta.fetch_prefix(seg.meta.sec_url(x['filename']))
            series=[s for s in seg.meta.parse_series_contracts(submission,x['company']) if s.get('isEtf') and s.get('seriesId')]
            _,text=seg.embedded_primary_nq(submission);markers=list(seg.SCHEDULE.finditer(text))
            for j,m in enumerate(markers):
                start=m.start();end=markers[j+1].start() if j+1<len(markers) else min(len(text),start+300000)
                block=text[start:end];context=text[max(0,start-5000):min(end,start+2500)]
                s,score=seg.map_schedule_to_series(context,series)
                if not s:continue
                old_method,old_h,old_total=pit.normalized_holdings(block)
                new_h,new_total=normalized(legacy.parse_html_table(block))
                top10=sum(h['weight'] for h in new_h[:10]) if new_h else 0
                new_usable=bool(seg.eligible_name(s.get('seriesName') or '') and 10<=len(new_h)<=120 and new_total>0 and top10>=25 and legacy.structural_sanity(new_h))
                old_suspicious=bool(len(old_h)==1 and float(old_total) in {2005,2006,2007,2008,2009,2010})
                rec={**x,'seriesId':s.get('seriesId'),'seriesName':s.get('seriesName'),'tickers':s.get('etfTickers',[]),'mappingScore':score,
                     'oldMethod':old_method,'oldCount':len(old_h),'oldTotal':old_total,'oldSuspiciousYearValue':old_suspicious,
                     'newCount':len(new_h),'newTotal':new_total,'newTop10Weight':top10,'newStructurallyUsable':new_usable,
                     'newSample':[{'description':h['description'],'quantity':h.get('quantityOrPrincipal'),'marketValue':h['marketValue']} for h in new_h[:5]]}
                records.append(rec)
            print(x['year'],x['company'],'mapped',sum(r['year']==x['year'] and r['cik']==x['cik'] for r in records),flush=True)
        except Exception as e:
            records.append({**x,'error':repr(e)});print('FAIL',x['year'],x['company'],repr(e),flush=True)
    valid=[r for r in records if 'seriesId' in r]
    ishares=[r for r in valid if 'ISHARES' in r['company'].upper()]
    spdr=[r for r in valid if 'SELECT SECTOR' in r['company'].upper()]
    out={'purpose':'Structural before/after validation of a legacy HTML holdings fallback. No prices/returns/performance used.',
         'acceptanceRules':{'rejectYearHeaderArtifact':True,'requireStructuralSanity':True,'usableRule':'production name exclusion + 10..120 holdings + top10>=25'},
         'mappedSeries':len(valid),'isharesMappedSeries':len(ishares),'isharesOldSuspicious':sum(r['oldSuspiciousYearValue'] for r in ishares),
         'isharesNewAtLeast10':sum(r['newCount']>=10 for r in ishares),'isharesNewUsable':sum(r['newStructurallyUsable'] for r in ishares),
         'spdrMappedSeries':len(spdr),'spdrNewUsable':sum(r['newStructurallyUsable'] for r in spdr),'records':records}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='records'}),flush=True)

if __name__=='__main__':main()
