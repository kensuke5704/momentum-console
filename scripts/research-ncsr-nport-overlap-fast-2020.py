#!/usr/bin/env python3
from __future__ import annotations

# Fast deterministic Gate-B companion. It reuses the exact parser, matching,
# coverage definitions and N-PORT bootstrap used by the full validation, but
# limits network retrieval to historically high-density ETF registrants. The
# registrant list is defined from filing structure/ETF-family identity only;
# no parser success, returns or strategy outcomes are used.

import gzip
import importlib.util
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'research' / 'ncsr-nport-overlap-fast-2020.json'
BOOTSTRAP = ROOT / 'data' / 'sec-nport' / 'bootstrap.json.gz'

spec = importlib.util.spec_from_file_location('full', ROOT/'scripts'/'research-ncsr-nport-overlap-2020.py')
full = importlib.util.module_from_spec(spec); spec.loader.exec_module(full)

# Exact historical ETF-family registrant names, chosen before inspecting overlap.
# These families contain many ETF series per filing and therefore provide an
# efficient structural validation sample.
DENSE_FAMILIES = (
    'SELECT SECTOR SPDR',
    'SPDR SERIES TRUST',
    'STREETTRACKS SERIES TRUST',
    'POWERSHARES EXCHANGE TRADED FUND TRUST',
    'INVESCO EXCHANGE-TRADED FUND TRUST',
    'INVESCO EXCHANGE TRADED FUND TRUST',
    'RYDEX ETF TRUST',
)


def dense(company: str) -> bool:
    u = (company or '').upper()
    return any(x in u for x in DENSE_FAMILIES)


def main():
    filings = [x for x in full.master_2020() if dense(x.get('company',''))]
    latest_by_cik = {}
    for x in sorted(filings,key=lambda r:(r['dateFiled'],r['filename'])):
        latest_by_cik[x['cik']] = x
    chosen = [latest_by_cik[cik] for cik in sorted(latest_by_cik)]

    with gzip.open(BOOTSTRAP,'rt',encoding='utf-8') as f:
        bp=json.load(f)
    nport=bp.get('snapshots') or bp.get('filings') or []
    by_series=defaultdict(list)
    for row in nport:
        if row.get('seriesId') and row.get('reportDate'):
            by_series[row['seriesId']].append(row)

    comparisons=[]; filings_out=[]
    for i,x in enumerate(chosen,1):
        try:
            _,submission=full.seg.meta.fetch_prefix(full.seg.meta.sec_url(x['filename']))
            rm=full.REPORT_DATE.search(submission); report=full.iso8(rm.group(1) if rm else None)
            series=[s for s in full.seg.meta.parse_series_contracts(submission,x['company']) if s.get('isEtf') and s.get('seriesId')]
            text=full.embedded_csr(submission); markers=list(full.seg.SCHEDULE.finditer(text)); mapped={}
            for j,m in enumerate(markers):
                start=m.start(); end=markers[j+1].start() if j+1<len(markers) else min(len(text),start+300000)
                parse_block=text[start:end]
                context=text[max(0,start-5000):min(end,start+2500)]
                s,score=full.seg.map_schedule_to_series(context,series)
                if not s or not s.get('seriesId'): continue
                method,holdings,total=full.pit.normalized_holdings(parse_block)
                if not holdings or total<=0: continue
                top10=sum(h['weight'] for h in holdings[:10])
                if not (10<=len(holdings)<=120 and top10>=25): continue
                cand={'seriesId':s['seriesId'],'seriesName':s.get('seriesName'),'tickers':s.get('etfTickers',[]),'score':score,'method':method,'holdings':holdings}
                cur=mapped.get(s['seriesId'])
                if cur is None or (len(holdings),score)>(len(cur['holdings']),cur['score']): mapped[s['seriesId']]=cand

            matched=0
            for sid,row in mapped.items():
                candidates=by_series.get(sid,[])
                if not report or not candidates: continue
                nearest=min(candidates,key=lambda f:full.days(report,f['reportDate']))
                gap=full.days(report,nearest['reportDate'])
                if gap>45: continue
                matched+=1
                left=defaultdict(float); right=defaultdict(float)
                for h in row['holdings']:
                    k=full.norm_issuer(h.get('description',''))
                    if k:left[k]+=float(h.get('weight') or 0)
                for h in nearest.get('holdings',[]):
                    k=full.norm_issuer(h.get('issuerName','')) if h.get('issuerName') else ''
                    if k:right[k]+=float(h.get('weight') or 0)
                common=set(left)&set(right)
                lt=sum(left.values()); rt=sum(right.values())
                lc=sum(left[k] for k in common); rc=sum(right[k] for k in common)
                comparisons.append({'seriesId':sid,'seriesName':row.get('seriesName'),'tickers':row.get('tickers',[]),
                    'ncsrReportDate':report,'nportReportDate':nearest.get('reportDate'),'reportDateGapDays':gap,
                    'ncsrHoldingCount':len(left),'nportNamedHoldingCount':len(right),'issuerOverlapCount':len(common),
                    'ncsrWeightCoverageRate':full.ratio(lc,lt),'nportNamedWeightCoverageRate':full.ratio(rc,rt)})
            filings_out.append({'company':x['company'],'cik':x['cik'],'filingDate':x['dateFiled'],'reportDate':report,'registeredEtfSeries':len(series),'usableMappedSeries':len(mapped),'matchedToNportSeries':matched})
            print(f"{i}/{len(chosen)} {x['company'][:48]} series={len(series)} usable={len(mapped)} overlap={matched}",flush=True)
        except Exception as e:
            filings_out.append({'company':x.get('company'),'cik':x.get('cik'),'error':repr(e)})
            print(f"{i}/{len(chosen)} FAIL {x.get('company')} {e!r}",flush=True)

    usable=[c for c in comparisons if c['ncsrWeightCoverageRate'] is not None and c['nportNamedWeightCoverageRate'] is not None]
    l=sorted(c['ncsrWeightCoverageRate'] for c in usable); r=sorted(c['nportNamedWeightCoverageRate'] for c in usable)
    out={'year':2020,'purpose':'Fast deterministic direct N-CSR/N-PORT same-series overlap validation; no investment-performance data used.',
         'sampleRule':'Latest 2020 filing per exact high-density ETF-family CIK from a predeclared registrant-name list; no parser-success or performance selection.',
         'matchingRule':'Same SEC seriesId; nearest N-PORT report <=45 days; exact conservative normalized issuer-name overlap.',
         'sampledRegistrants':len(chosen),'seriesComparisons':len(usable),
         'medianNcsrWeightCoverageRate':l[len(l)//2] if l else None,
         'medianNportNamedWeightCoverageRate':r[len(r)//2] if r else None,
         'gateBThresholds':{'minimumComparisons':10,'minimumMedianEachDirection':0.80},
         'gateBPass':len(usable)>=10 and bool(l) and l[len(l)//2]>=.80 and r[len(r)//2]>=.80,
         'comparisons':comparisons,'filingResults':filings_out}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in {'comparisons','filingResults'}}),flush=True)

if __name__=='__main__':main()
