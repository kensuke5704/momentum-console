#!/usr/bin/env python3
from __future__ import annotations

import gzip
import html
import importlib.util
import json
import re
import tempfile
import time
import urllib.request
import zipfile
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRIVE = 'https://drive.usercontent.google.com/download?id=1yfQxR45DZ_vM5pkFvgyexc10NNqbxpFN&export=download&confirm=t'
UA = {'User-Agent':'momentum-console research kensuke5704@users.noreply.github.com','Accept':'*/*'}
BOOTSTRAP = ROOT / 'data' / 'sec-nport' / 'bootstrap.json.gz'
OUT = ROOT / 'data' / 'research' / 'ncsr-nport-overlap-2020.json'
TARGET = re.compile(r'ISHARES|SELECT SECTOR SPDR|STREETTRACKS|SPDR|POWERSHARES|INVESCO|VANGUARD|PROSHARES|RYDEX', re.I)
FORMS = {'N-CSR','N-CSRS'}
DOCUMENT_BLOCK = re.compile(r'(?is)<DOCUMENT>(.*?)</DOCUMENT>')
TYPE_CSR = re.compile(r'(?im)^\s*<TYPE>\s*N-(?:CSR|CSRS)\b')
TEXT_BLOCK = re.compile(r'(?is)<TEXT>(.*)</TEXT>')
REPORT_DATE = re.compile(r'(?im)^\s*CONFORMED PERIOD OF REPORT:\s*(\d{8})\s*$')
SCHEDULE_HTML = re.compile(
    r'SCHEDULE(?:\s|&nbsp;|&#160;|<[^>]+>)+OF(?:\s|&nbsp;|&#160;|<[^>]+>)+INVESTMENTS', re.I
)

sspec = importlib.util.spec_from_file_location('seg', ROOT / 'scripts' / 'research-nq-series-segmentation-2006.py')
seg = importlib.util.module_from_spec(sspec); sspec.loader.exec_module(seg)
pspec = importlib.util.spec_from_file_location('pit', ROOT / 'scripts' / 'research-nq-pit-holdings-2006.py')
pit = importlib.util.module_from_spec(pspec); pspec.loader.exec_module(pit)


def download(path: Path):
    req = urllib.request.Request(DRIVE, headers=UA)
    with urllib.request.urlopen(req, timeout=600) as r, open(path, 'wb') as f:
        while True:
            b = r.read(1024*1024)
            if not b: break
            f.write(b)


def master_2020():
    with tempfile.TemporaryDirectory() as td:
        zp = Path(td) / 'master.zip'; download(zp)
        hits = []
        with zipfile.ZipFile(zp) as z:
            qfiles = [n for n in z.namelist() if any(f'master_2020_QTR{q}.idx' in n for q in range(1,5))]
            for name in sorted(qfiles):
                text = z.read(name).decode('latin-1','replace')
                for line in text.splitlines():
                    p = line.split('|')
                    if len(p) < 5: continue
                    cik, company, form, date_filed, filename = [x.strip() for x in p[:5]]
                    if form.upper() in FORMS and TARGET.search(company):
                        hits.append({'cik':cik,'company':company,'form':form.upper(),'dateFiled':date_filed,'filename':filename})
        return hits


def fetch_full_filing(url: str) -> tuple[str,str]:
    """Fetch enough of a modern shareholder report to include all ETF series.

    The earlier 1.5MB metadata probe is intentionally not used here because
    multi-series N-CSR filings commonly exceed that size. This transport choice
    is structural and independent of parser success or investment outcomes.
    """
    last=None
    for attempt in range(3):
        try:
            req=urllib.request.Request('https://r.jina.ai/'+url,headers=UA)
            with urllib.request.urlopen(req,timeout=60) as r:
                return 'jina-full',r.read(12_000_000).decode('utf-8','replace')
        except Exception as e:
            last=e;time.sleep(4*(attempt+1))
    # Reuse the authoritative SEC fallback in the metadata transport as a last resort.
    try:
        return seg.meta.fetch_prefix(url)
    except Exception as e:
        last=e
    raise last


def embedded_csr(submission: str) -> str:
    for m in DOCUMENT_BLOCK.finditer(submission):
        block = m.group(1)
        if not TYPE_CSR.search(block): continue
        tm = TEXT_BLOCK.search(block)
        return tm.group(1) if tm else block
    return submission


def iso8(raw: str | None):
    return f'{raw[:4]}-{raw[4:6]}-{raw[6:8]}' if raw and len(raw)==8 else None


def norm_issuer(raw: str) -> str:
    s = html.unescape(raw or '').upper().replace('&',' AND ')
    s = re.sub(r'\bTHE\b',' ',s)
    s = re.sub(r'\b(INCORPORATED|INCORPORATION)\b','INC',s)
    s = re.sub(r'\bCORPORATION\b','CORP',s)
    s = re.sub(r'\bCOMPANY\b','CO',s)
    s = re.sub(r'\bLIMITED\b','LTD',s)
    s = re.sub(r'\s+(?:ADR|GDR)\s*$','',s)
    s = re.sub(r'\s*\((?:[A-Z]{1,3}|\d{1,3})\)\s*$','',s)
    return ' '.join(re.sub(r'[^A-Z0-9]+',' ',s).split())


def days(a: str, b: str):
    return abs((date.fromisoformat(a)-date.fromisoformat(b)).days)


def ratio(n: float, d: float):
    return n / d if d else None


def visible(raw: str) -> str:
    s=re.sub(r'(?is)<BR\s*/?>',' ',raw)
    s=re.sub(r'(?is)<[^>]+>',' ',s)
    return ' '.join(html.unescape(s).replace('\xa0',' ').split())


def modern_series_segments(text: str, series: list[dict]) -> list[dict]:
    """Locate the primary schedule for each filing-time ETF series exactly.

    Legacy schedule-marker inference is not reused. We require the exact series
    name from SEC SGML metadata and a Schedule of Investments shortly after that
    heading. A primary (non-continued) schedule is preferred. The segment ends
    at the next primary series schedule, so continuation pages remain attached.
    """
    candidates=[]
    for s in series:
        name=str(s.get('seriesName') or '').strip()
        if not name:continue
        occurrences=list(re.finditer(re.escape(name),text,re.I))
        schedule_options=[]
        for om in occurrences:
            window_end=min(len(text),om.end()+80_000)
            for sm in SCHEDULE_HTML.finditer(text,om.end(),window_end):
                label=visible(text[sm.start():min(window_end,sm.end()+500)]).upper()
                continued='CONTINUED' in label[:160]
                schedule_options.append((continued,sm.start(),om.start()))
                break
        if not schedule_options:continue
        # Prefer a primary schedule; then earliest occurrence in filing order.
        continued,start,heading_start=sorted(schedule_options,key=lambda x:(x[0],x[1]))[0]
        candidates.append({'series':s,'start':start,'headingStart':heading_start,'continued':continued})
    candidates.sort(key=lambda x:x['start'])
    out=[]
    for i,c in enumerate(candidates):
        end=candidates[i+1]['start'] if i+1<len(candidates) else min(len(text),c['start']+1_000_000)
        segment=text[c['start']:end]
        # Affiliate/fair-value tables follow the actual holdings and should not be
        # interpreted as portfolio rows. Cut only after the main schedule starts.
        cut=len(segment)
        for pat in (r'Affiliate Table',r'The following table summarizes the value',r'Fair Value Hierarchy'):
            m=re.search(pat,segment,re.I)
            if m and m.start()>1000:cut=min(cut,m.start())
        segment=segment[:cut]
        out.append({'series':c['series'],'segment':segment,'primarySchedule':not c['continued']})
    return out


def mapped_modern_series(text: str, series: list[dict]) -> dict[str,dict]:
    mapped={}
    for item in modern_series_segments(text,series):
        s=item['series']; segment=item['segment']
        # Seed one synthetic table row so the legacy HTML-table parser knows the
        # already-segmented content is inside a Schedule of Investments.
        parse_input='<TR><TD>SCHEDULE OF INVESTMENTS</TD></TR>'+segment
        method,holdings,total=pit.normalized_holdings(parse_input)
        if not holdings or total<=0:continue
        count=len(holdings);top10=sum(h['weight'] for h in holdings[:10])
        if not (10<=count<=120 and top10>=25):continue
        mapped[s['seriesId']]={'seriesId':s['seriesId'],'seriesName':s.get('seriesName'),'tickers':s.get('etfTickers',[]),
            'score':1.0,'method':method,'holdings':holdings,'top10Weight':top10,'primarySchedule':item['primarySchedule']}
    return mapped


def main():
    filings = master_2020()
    latest_by_cik = {}
    for x in sorted(filings,key=lambda r:(r['dateFiled'],r['filename'])):
        latest_by_cik[x['cik']] = x
    chosen = [latest_by_cik[cik] for cik in sorted(latest_by_cik)]

    with gzip.open(BOOTSTRAP,'rt',encoding='utf-8') as f:
        bp=json.load(f)
    nport=bp.get('snapshots') or bp.get('filings') or []
    by_series=defaultdict(list)
    for f in nport:
        if f.get('seriesId') and f.get('reportDate'):
            by_series[f['seriesId']].append(f)
    for rows in by_series.values(): rows.sort(key=lambda r:(r.get('reportDate',''),r.get('filingDate','')))

    comparisons=[]; filing_results=[]
    for i,x in enumerate(chosen,1):
        try:
            transport,submission=fetch_full_filing(seg.meta.sec_url(x['filename']))
            rm=REPORT_DATE.search(submission); report=iso8(rm.group(1) if rm else None)
            series=[s for s in seg.meta.parse_series_contracts(submission,x['company']) if s.get('isEtf') and s.get('seriesId')]
            text=embedded_csr(submission)
            mapped=mapped_modern_series(text,series)
            matched_series=0
            for sid,row in mapped.items():
                candidates=by_series.get(sid,[])
                if not report or not candidates: continue
                nearest=min(candidates,key=lambda f:days(report,f['reportDate']))
                gap=days(report,nearest['reportDate'])
                if gap>45: continue
                matched_series+=1
                ncsr_names=defaultdict(float)
                for h in row['holdings']:
                    k=norm_issuer(h.get('description',''))
                    if k: ncsr_names[k]+=float(h.get('weight') or 0)
                nport_names=defaultdict(float)
                for h in nearest.get('holdings',[]):
                    k=norm_issuer(h.get('issuerName','')) if h.get('issuerName') else ''
                    if k: nport_names[k]+=float(h.get('weight') or 0)
                common=set(ncsr_names)&set(nport_names)
                ncsr_total=sum(ncsr_names.values());nport_total=sum(nport_names.values())
                ncsr_common=sum(ncsr_names[k] for k in common);nport_common=sum(nport_names[k] for k in common)
                comparisons.append({
                    'seriesId':sid,'seriesName':row.get('seriesName'),'tickers':row.get('tickers',[]),
                    'ncsrReportDate':report,'nportReportDate':nearest.get('reportDate'),'reportDateGapDays':gap,
                    'ncsrHoldingCount':len(ncsr_names),'nportHoldingCount':len(nearest.get('holdings',[])),'nportNamedHoldingCount':len(nport_names),
                    'issuerOverlapCount':len(common),
                    'ncsrTotalWeight':ncsr_total,'nportNamedTotalWeight':nport_total,
                    'ncsrCommonWeight':ncsr_common,'nportCommonWeight':nport_common,
                    'ncsrWeightCoverageRate':ratio(ncsr_common,ncsr_total),'nportNamedWeightCoverageRate':ratio(nport_common,nport_total),
                    'parseMethod':row.get('method')})
            filing_results.append({'company':x['company'],'cik':x['cik'],'filingDate':x['dateFiled'],'reportDate':report,'transport':transport,
                'registeredEtfSeries':len(series),'usableMappedSeries':len(mapped),'matchedToNportSeries':matched_series})
            print(f"{i}/{len(chosen)} {x['company'][:40]} transport={transport} etf={len(series)} usable={len(mapped)} nport={matched_series}",flush=True)
        except Exception as e:
            filing_results.append({'company':x.get('company'),'cik':x.get('cik'),'error':repr(e)})
            print(f"{i}/{len(chosen)} FAIL {x.get('company')} {e!r}",flush=True)

    usable_named=[c for c in comparisons if c['nportNamedHoldingCount']>0 and c['ncsrWeightCoverageRate'] is not None and c['nportNamedWeightCoverageRate'] is not None]
    left=sorted(c['ncsrWeightCoverageRate'] for c in usable_named);right=sorted(c['nportNamedWeightCoverageRate'] for c in usable_named)
    summary={
        'year':2020,'purpose':'Direct structural overlap validation of legacy N-CSR/N-CSRS ETF schedule parsing against N-PORT for the same SEC seriesId. No return or strategy-performance data used.',
        'sampleRule':'Latest 2020 N-CSR/N-CSRS filing per target ETF-family CIK; deterministic by filing date and CIK; no parser-success or performance selection.',
        'segmentationRule':'Exact filing-time SEC series name followed by its primary Schedule of Investments; continuation pages retained until the next series; no fuzzy schedule-to-series assignment.',
        'matchingRule':'Same SEC seriesId; nearest N-PORT report date within 45 calendar days; exact conservative normalized issuer-name overlap only.',
        'coverageRule':'N-CSR common issuer weight divided by normalized N-CSR series weight; N-PORT common issuer weight divided by total named N-PORT holding weight.',
        'targetFilings':len(filings),'sampledRegistrants':len(chosen),'filingsSucceeded':sum('error' not in r for r in filing_results),
        'seriesComparisons':len(comparisons),'seriesWithNportIssuerNames':len(usable_named),
        'medianNcsrWeightCoverageRate':left[len(left)//2] if left else None,'medianNportNamedWeightCoverageRate':right[len(right)//2] if right else None,
        'comparisons':comparisons,'filingResults':filing_results}
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(summary,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in summary.items() if k not in {'comparisons','filingResults'}}),flush=True)

if __name__=='__main__': main()
