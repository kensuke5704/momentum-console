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
# Structural registrant-family hints only. FIRST TRUST / ETF MANAGERS / PACER / ARK
# were added after inspecting which ETF series are actually present in the frozen
# N-PORT bootstrap. This is source-coverage selection, not return/performance selection.
TARGET = re.compile(r'ISHARES|SELECT SECTOR SPDR|STREETTRACKS|SPDR|POWERSHARES|INVESCO|VANGUARD|PROSHARES|RYDEX|FIRST TRUST|ETF MANAGERS|PACER|ARK ETF', re.I)
FORMS = {'N-CSR','N-CSRS'}
DOCUMENT_BLOCK = re.compile(r'(?is)<DOCUMENT>(.*?)</DOCUMENT>')
TYPE_CSR = re.compile(r'(?im)^\s*<TYPE>\s*N-(?:CSR|CSRS)\b')
TEXT_BLOCK = re.compile(r'(?is)<TEXT>(.*)</TEXT>')
REPORT_DATE = re.compile(r'(?im)^\s*CONFORMED PERIOD OF REPORT:\s*(\d{8})\s*$')
# Shareholder reports use both labels. Treat them as equivalent structural section
# delimiters; this broadens document-format coverage only and does not depend on
# holdings, returns, ranks, or strategy results.
SCHEDULE_HTML = re.compile(
    r'(?:SCHEDULE|PORTFOLIO)(?:\s|&nbsp;|&#160;|<[^>]+>)+OF(?:\s|&nbsp;|&#160;|<[^>]+>)+INVESTMENTS', re.I
)

sspec = importlib.util.spec_from_file_location('seg', ROOT / 'scripts' / 'research-nq-series-segmentation-2006.py')
seg = importlib.util.module_from_spec(sspec); sspec.loader.exec_module(seg)
pspec = importlib.util.spec_from_file_location('pit', ROOT / 'scripts' / 'research-nq-pit-holdings-2006.py')
pit = importlib.util.module_from_spec(pspec); pspec.loader.exec_module(pit)


def download(path: Path):
    req = urllib.request.Request(DRIVE, headers=UA)
    with urllib.request.urlopen(req, timeout=600) as r, open(path,'wb') as f:
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
    """Fetch enough of a modern shareholder report to include all ETF series."""
    last=None
    for attempt in range(3):
        try:
            req=urllib.request.Request('https://r.jina.ai/'+url,headers=UA)
            with urllib.request.urlopen(req,timeout=60) as r:
                return 'jina-full',r.read(12_000_000).decode('utf-8','replace')
        except Exception as e:
            last=e;time.sleep(4*(attempt+1))
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
    s = re.sub(r'(?is)<script.*?</script>|<style.*?</style>', ' ', raw)
    s = re.sub(r'(?is)<[^>]+>', ' ', s)
    s = html.unescape(s).replace('\xa0',' ')
    return ' '.join(s.split())


def norm_series_text(raw: str) -> str:
    """Normalize display-only series-name differences, then require exact containment.

    Registered marks, punctuation, HTML entities and whitespace do not carry series
    identity. No token dropping, fuzzy matching, holdings overlap or performance data
    is used here.
    """
    s = html.unescape(raw or '').upper().replace('\xa0', ' ')
    return ' '.join(re.sub(r'[^A-Z0-9]+', ' ', s).split())


def _toc_href_heading(text: str, m: re.Match) -> bool:
    """True only when the heading text is wrapped by an HTML href anchor.

    The fixed 2020 First Trust report contains a table-of-contents link whose visible
    label is exactly "Portfolio of Investments". Treating that navigation link as a
    section delimiter created a false schedule block. Real section anchors may use
    id/name attributes; this filter rejects only an open <A ... href=...> wrapping
    the heading, so it does not exclude non-navigation anchors.
    """
    prefix = text[max(0, m.start() - 800):m.start()]
    open_a = prefix.upper().rfind('<A')
    close_a = prefix.upper().rfind('</A>')
    if open_a <= close_a:
        return False
    open_tag = prefix[open_a:]
    if not re.search(r'(?is)<A\b[^>]*\bHREF\s*=', open_tag):
        return False
    suffix = text[m.end():min(len(text), m.end() + 800)]
    return re.search(r'(?is)</A\s*>', suffix) is not None


def schedule_blocks(text: str):
    matches=[m for m in SCHEDULE_HTML.finditer(text) if not _toc_href_heading(text, m)]
    if not matches:
        matches=list(seg.SCHEDULE.finditer(text))
    return [(m.start(), matches[i+1].start() if i+1<len(matches) else min(len(text),m.start()+300000)) for i,m in enumerate(matches)]


def mapped_modern_series(text: str, series: list[dict]):
    mapped={}
    for start,end in schedule_blocks(text):
        block=text[start:end]
        context=text[max(0,start-10000):min(end,start+3000)]
        v=norm_series_text(visible(context))
        exact=[]
        for s in series:
            name=norm_series_text(s.get('seriesName') or '')
            if name and name in v: exact.append(s)
        if len(exact)!=1: continue
        s=exact[0]
        method,holdings,total=pit.normalized_holdings(block)
        count=len(holdings);top10=sum(h['weight'] for h in holdings[:10]) if holdings else 0
        if not (seg.eligible_name(s.get('seriesName') or '') and 10<=count<=120 and total>0 and top10>=25): continue
        candidate={'seriesId':s['seriesId'],'seriesName':s.get('seriesName'),'fundTickers':s.get('etfTickers',[]),'holdings':holdings,'method':method,'total':total,'top10':top10}
        cur=mapped.get(s['seriesId'])
        if cur is None or count>len(cur['holdings']): mapped[s['seriesId']]=candidate
    return mapped


def main():
    filings=master_2020()
    latest_by_cik={}
    for x in sorted(filings,key=lambda r:(r['dateFiled'],r['filename'])): latest_by_cik[x['cik']]=x
    chosen=[latest_by_cik[cik] for cik in sorted(latest_by_cik)]
    with gzip.open(BOOTSTRAP,'rt',encoding='utf-8') as f: bp=json.load(f)
    nport=bp.get('snapshots') or bp.get('filings') or []
    by_series=defaultdict(list)
    for f in nport:
        if f.get('seriesId') and f.get('reportDate'): by_series[f['seriesId']].append(f)
    for rows in by_series.values(): rows.sort(key=lambda r:(r.get('reportDate',''),r.get('filingDate','')))

    comparisons=[]; diagnostics=[]
    for i,x in enumerate(chosen,1):
        try:
            transport,submission=fetch_full_filing(seg.meta.sec_url(x['filename']))
            rm=REPORT_DATE.search(submission);report=iso8(rm.group(1) if rm else None)
            series=[s for s in seg.meta.parse_series_contracts(submission,x['company']) if s.get('isEtf') and s.get('seriesId')]
            mapped=mapped_modern_series(embedded_csr(submission),series)
            paired=0
            for sid,row in mapped.items():
                candidates=by_series.get(sid,[])
                if not report or not candidates: continue
                nearest=min(candidates,key=lambda f:days(report,f['reportDate']))
                gap=days(report,nearest['reportDate'])
                if gap>45: continue
                legacy_by={norm_issuer(h['description']):h['weight'] for h in row['holdings'] if norm_issuer(h['description'])}
                nport_by=defaultdict(float)
                for h in nearest.get('holdings',[]):
                    k=norm_issuer(str(h.get('issuerName') or ''))
                    if k:nport_by[k]+=float(h.get('weight') or 0)
                common=set(legacy_by)&set(nport_by)
                legacy_common=sum(legacy_by[k] for k in common);nport_named=sum(nport_by.values());nport_common=sum(nport_by[k] for k in common)
                comparisons.append({'company':x['company'],'seriesId':sid,'seriesName':row['seriesName'],'legacyReportDate':report,'nportReportDate':nearest['reportDate'],'reportGapDays':gap,
                    'legacyHoldingCount':len(legacy_by),'nportNamedCount':len(nport_by),'commonIssuerCount':len(common),
                    'legacyWeightCoverageRate':ratio(legacy_common,sum(legacy_by.values())),'nportNamedWeightCoverageRate':ratio(nport_common,nport_named),'parseMethod':row['method']})
                paired+=1
            diagnostics.append({'company':x['company'],'cik':x['cik'],'transport':transport,'registeredEtfSeries':len(series),'usableMappedSeries':len(mapped),'pairedSeries':paired})
            print(f"{i}/{len(chosen)} {x['company'][:45]} mapped={len(mapped)} paired={paired}",flush=True)
        except Exception as e:
            diagnostics.append({'company':x.get('company'),'cik':x.get('cik'),'error':repr(e)});print(f"{i}/{len(chosen)} FAIL {x.get('company')} {e!r}",flush=True)

    a=sorted(c['legacyWeightCoverageRate'] for c in comparisons if c['legacyWeightCoverageRate'] is not None)
    b=sorted(c['nportNamedWeightCoverageRate'] for c in comparisons if c['nportNamedWeightCoverageRate'] is not None)
    med=lambda x:x[len(x)//2] if x else None
    ma,mb=med(a),med(b)
    gate=bool(len(comparisons)>=10 and ma is not None and mb is not None and ma>=.8 and mb>=.8)
    out={'year':2020,'purpose':'Direct same-series N-CSR/N-CSRS vs N-PORT holdings overlap validation. Structural only; no prices, returns, trades or strategy performance.',
        'sampleRule':'Latest 2020 filing per deterministic ETF-family CIK from a predeclared structural source-coverage list; no parser-success or performance selection.',
        'matchingRule':'Same SEC seriesId; nearest N-PORT report <=45 days; exact conservative normalized issuer-name overlap.',
        'seriesComparisons':len(comparisons),'medianNcsrWeightCoverageRate':ma,'medianNportNamedWeightCoverageRate':mb,
        'gateBThresholds':{'minimumComparisons':10,'minimumMedianEachDirection':.8},'gateBPass':gate,'comparisons':comparisons,'diagnostics':diagnostics}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in {'comparisons','diagnostics'}},sort_keys=True),flush=True)

if __name__=='__main__':main()
