#!/usr/bin/env python3
from __future__ import annotations

import importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data'/'research'/'ncsr-schedule-diagnostic-2020.json'
spec=importlib.util.spec_from_file_location('full',ROOT/'scripts'/'research-ncsr-nport-overlap-2020.py')
full=importlib.util.module_from_spec(spec);spec.loader.exec_module(full)

TARGET_NAMES=('SELECT SECTOR SPDR TRUST','SPDR SERIES TRUST','INVESCO EXCHANGE-TRADED FUND TRUST')

def wanted(name):
    u=(name or '').upper()
    return any(x in u for x in TARGET_NAMES)

def main():
    filings=[x for x in full.master_2020() if wanted(x.get('company',''))]
    latest={}
    for x in sorted(filings,key=lambda r:(r['dateFiled'],r['filename'])):latest[x['cik']]=x
    chosen=[latest[k] for k in sorted(latest)]
    out_rows=[]
    for i,x in enumerate(chosen,1):
        try:
            method,submission=full.seg.meta.fetch_prefix(full.seg.meta.sec_url(x['filename']))
            rm=full.REPORT_DATE.search(submission); report=full.iso8(rm.group(1) if rm else None)
            series=[s for s in full.seg.meta.parse_series_contracts(submission,x['company']) if s.get('isEtf') and s.get('seriesId')]
            text=full.embedded_csr(submission);markers=list(full.seg.SCHEDULE.finditer(text)); blocks=[]
            for j,m in enumerate(markers):
                start=m.start();end=markers[j+1].start() if j+1<len(markers) else min(len(text),start+300000)
                parse_block=text[start:end]; context=text[max(0,start-5000):min(end,start+2500)]
                s,score=full.seg.map_schedule_to_series(context,series)
                pm,holdings,total=full.pit.normalized_holdings(parse_block)
                blocks.append({'index':j,'mappedSeriesId':s.get('seriesId') if s else None,'mappedSeriesName':s.get('seriesName') if s else None,
                    'mappingScore':score,'parseMethod':pm,'holdingCount':len(holdings),'top10Weight':sum(h['weight'] for h in holdings[:10]) if holdings else 0,
                    'parsedMarketValueTotal':total,'sampleDescriptions':[h.get('description') for h in holdings[:8]]})
            row={'company':x['company'],'cik':x['cik'],'filingDate':x['dateFiled'],'reportDate':report,'transport':method,
                 'registeredEtfSeries':len(series),'scheduleMarkers':len(markers),'blocks':blocks}
            print(f"{i}/{len(chosen)} {x['company'][:45]} transport={method} series={len(series)} schedules={len(markers)}",flush=True)
            for b in blocks[:30]:
                print(' BLOCK',json.dumps({k:v for k,v in b.items() if k!='sampleDescriptions'}),flush=True)
        except Exception as e:
            row={'company':x.get('company'),'cik':x.get('cik'),'filingDate':x.get('dateFiled'),'error':repr(e)}
            print(f"{i}/{len(chosen)} FAIL {x.get('company')} {e!r}",flush=True)
        out_rows.append(row)
    out={'year':2020,'purpose':'Structural diagnosis of N-CSR schedule detection, series mapping and holdings parsing. No returns/performance used.',
         'sampleRule':'Latest 2020 filing per predeclared high-density ETF registrant CIK.','results':out_rows}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')

if __name__=='__main__':main()
