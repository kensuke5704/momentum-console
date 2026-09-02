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


def usable(series_name:str, holdings:list[dict], total:float)->bool:
    top10=sum(float(h.get('weight') or 0) for h in holdings[:10]) if holdings else 0
    return bool(seg.eligible_name(series_name or '') and 10<=len(holdings)<=120 and total>0 and top10>=25)


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

                # Raw established parser only, to diagnose whether the fallback was needed.
                raw_method,_,_,raw_parsed=seg.nqpilot.parse_holdings(block)
                raw_h,raw_total=pit._normalize(raw_parsed)
                raw_artifact=pit._year_header_artifact(raw_h,raw_total)

                # Composite production candidate: established parser first, HTML fallback
                # only for the explicitly recognized year-header artifact.
                method,holdings,total=pit.normalized_holdings(block)
                top10=sum(float(h.get('weight') or 0) for h in holdings[:10]) if holdings else 0
                composite_usable=usable(s.get('seriesName') or '',holdings,total)
                rec={**x,'seriesId':s.get('seriesId'),'seriesName':s.get('seriesName'),'tickers':s.get('etfTickers',[]),'mappingScore':score,
                     'rawMethod':raw_method,'rawCount':len(raw_h),'rawTotal':raw_total,'rawYearHeaderArtifact':raw_artifact,
                     'compositeMethod':method,'compositeCount':len(holdings),'compositeTotal':total,'compositeTop10Weight':top10,
                     'compositeUsable':composite_usable,
                     'sample':[{'description':h['description'],'quantity':h.get('quantityOrPrincipal'),'marketValue':h['marketValue']} for h in holdings[:5]]}
                records.append(rec)
            print(x['year'],x['company'],'mapped',sum(r['year']==x['year'] and r['cik']==x['cik'] for r in records),flush=True)
        except Exception as e:
            records.append({**x,'error':repr(e)});print('FAIL',x['year'],x['company'],repr(e),flush=True)

    valid=[r for r in records if 'seriesId' in r]
    ishares=[r for r in valid if 'ISHARES' in r['company'].upper()]
    spdr=[r for r in valid if 'SELECT SECTOR' in r['company'].upper()]
    by_year={}
    for year in YEARS:
        rows=[r for r in valid if r['year']==year]
        by_year[str(year)]={
            'mappedSeries':len(rows),
            'compositeUsable':sum(r['compositeUsable'] for r in rows),
            'fallbackUsed':sum(r['compositeMethod']=='html-year-artifact-fallback' for r in rows),
        }
    out={'purpose':'Structural validation of the composite legacy holdings parser. Established parser is preserved; HTML fallback is used only for the proven one-row year-header artifact. No prices/returns/performance used.',
         'acceptanceRules':{'establishedParserFirst':True,'fallbackOnlyForYearHeaderArtifact':True,'usableRule':'production name exclusion + 10..120 holdings + top10>=25'},
         'mappedSeries':len(valid),
         'compositeUsable':sum(r['compositeUsable'] for r in valid),
         'fallbackUsed':sum(r['compositeMethod']=='html-year-artifact-fallback' for r in valid),
         'isharesMappedSeries':len(ishares),'isharesCompositeUsable':sum(r['compositeUsable'] for r in ishares),'isharesFallbackUsed':sum(r['compositeMethod']=='html-year-artifact-fallback' for r in ishares),
         'spdrMappedSeries':len(spdr),'spdrCompositeUsable':sum(r['compositeUsable'] for r in spdr),'spdrFallbackUsed':sum(r['compositeMethod']=='html-year-artifact-fallback' for r in spdr),
         'byYear':by_year,'records':records}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='records'}),flush=True)

if __name__=='__main__':main()
