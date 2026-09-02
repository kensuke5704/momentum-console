#!/usr/bin/env python3
from __future__ import annotations

import gzip
import importlib.util
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data'/'research'/'nport-series-gap-diagnostic-2020.json'
BOOTSTRAP=ROOT/'data'/'sec-nport'/'bootstrap.json.gz'
TARGET=re.compile(r'^(?:SELECT SECTOR SPDR TRUST|SPDR SERIES TRUST|INVESCO EXCHANGE-TRADED FUND TRUST|INVESCO EXCHANGE-TRADED FUND TRUST II)$',re.I)

spec=importlib.util.spec_from_file_location('ov',ROOT/'scripts'/'research-ncsr-nport-overlap-2020.py')
ov=importlib.util.module_from_spec(spec);spec.loader.exec_module(ov)


def main():
    filings=[x for x in ov.master_2020() if TARGET.match(str(x.get('company') or ''))]
    latest={}
    for x in sorted(filings,key=lambda r:(r['dateFiled'],r['filename'])):latest[x['cik']]=x
    chosen=[latest[k] for k in sorted(latest)]
    with gzip.open(BOOTSTRAP,'rt',encoding='utf-8') as f:bp=json.load(f)
    nport=bp.get('snapshots') or bp.get('filings') or []
    by_series=defaultdict(list)
    by_year=defaultdict(int)
    for f in nport:
        sid=f.get('seriesId');rd=f.get('reportDate')
        if sid and rd:by_series[sid].append(f);by_year[str(rd)[:4]]+=1
    for rows in by_series.values():rows.sort(key=lambda r:(r.get('reportDate',''),r.get('filingDate','')))
    rows=[]
    for x in chosen:
        try:
            transport,submission=ov.fetch_full_filing(ov.seg.meta.sec_url(x['filename']))
            rm=ov.REPORT_DATE.search(submission);report=ov.iso8(rm.group(1) if rm else None)
            series=[s for s in ov.seg.meta.parse_series_contracts(submission,x['company']) if s.get('isEtf') and s.get('seriesId')]
            mapped=ov.mapped_modern_series(ov.embedded_csr(submission),series)
            for sid,r in mapped.items():
                candidates=by_series.get(sid,[])
                nearest=None;gap=None
                if report and candidates:
                    nearest=min(candidates,key=lambda f:ov.days(report,f['reportDate']))
                    gap=ov.days(report,nearest['reportDate'])
                rows.append({'company':x['company'],'seriesId':sid,'seriesName':r.get('seriesName'),'legacyReportDate':report,
                    'nportSeriesPresent':bool(candidates),'nportSnapshotCount':len(candidates),'nearestNportReportDate':nearest.get('reportDate') if nearest else None,
                    'nearestNportFilingDate':nearest.get('filingDate') if nearest else None,'nearestGapDays':gap,'parseMethod':r.get('method')})
            print(x['company'],'mapped',len(mapped),flush=True)
        except Exception as e:
            rows.append({'company':x.get('company'),'error':repr(e)});print('FAIL',x.get('company'),repr(e),flush=True)
    present=[r for r in rows if r.get('nportSeriesPresent')]
    gaps=[r['nearestGapDays'] for r in present if r.get('nearestGapDays') is not None]
    out={'purpose':'Diagnose same-series availability and report-date gaps between 2020 legacy shareholder reports and the frozen N-PORT bootstrap. No prices/returns/performance used.',
        'nportSnapshotCount':len(nport),'nportSnapshotsByReportYear':dict(sorted(by_year.items())),
        'legacyMappedSeries':sum('seriesId' in r for r in rows),'legacySeriesPresentInNport':len(present),
        'presentWithin45Days':sum((r.get('nearestGapDays') or 10**9)<=45 for r in present),
        'minGapDays':min(gaps) if gaps else None,'medianGapDays':sorted(gaps)[len(gaps)//2] if gaps else None,'rows':rows}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='rows'}),flush=True)

if __name__=='__main__':main()
