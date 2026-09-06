#!/usr/bin/env python3
from __future__ import annotations

import concurrent.futures
import html
import importlib.util
import json
import re
import threading
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'data/research/nq-hybrid-country-resolved-h1-2006.json'
OUT = ROOT / 'data/research/country-master-once-recovery-v29.json'


def load(path):
    spec = importlib.util.spec_from_file_location('country_base_once', path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

base = load(ROOT / 'scripts/research-country-index-headers-recovery-v29.py')
FOREIGN_FORMS = {'6-K','6-K/A','20-F','20-F/A','40-F','40-F/A'}
DETAIL_CACHE = {}
DETAIL_LOCK = threading.Lock()


def detail_url(filename):
    p = base.accession_parts(filename)
    if not p:
        return None
    cik, acc, ad = p
    return f'https://www.sec.gov/Archives/edgar/data/{cik}/{ad}/{acc}-index.htm'


def detail_page(filename):
    with DETAIL_LOCK:
        if filename in DETAIL_CACHE:
            return DETAIL_CACHE[filename]
    url = detail_url(filename)
    if not url:
        raise RuntimeError('no detail url')
    proxy = 'https://r.jina.ai/' + url
    req = urllib.request.Request(proxy, headers=base.UA)
    with urllib.request.urlopen(req, timeout=10) as r:
        result = (r.read(800_000).decode('latin-1', 'replace'), proxy)
    with DETAIL_LOCK:
        DETAIL_CACHE[filename] = result
    return result


def detail_entity_state(target, cik, text):
    cleaned = html.unescape(re.sub(r'<[^>]*>', ' ', text)).replace('\r', ' ')
    cleaned = re.sub(r'\s+', ' ', cleaned)
    zcik = str(cik).zfill(10)
    nt = base.normalize_company(target)
    for m in re.finditer(r'CIK:\s*0*' + re.escape(str(int(zcik))), cleaned, re.I):
        w = cleaned[max(0, m.start()-300):m.start()+900]
        sm = re.search(r'State\s+of\s+Incorp\.?:\s*([A-Z0-9]{2,3})', w, re.I)
        if sm and nt and nt in base.normalize_company(w):
            return sm.group(1).upper(), target
    return None, None


def query_forms(row):
    forms=[]
    for issuer in row.get('issuerVariants', []):
        for f in base.cleaned_forms(str(issuer)):
            if f and f not in forms:
                forms.append(f)
    return forms


def seed_from_strict(row):
    ciks=set()
    for a in row.get('attempts', []):
        if a.get('historicalExactCikCount') == 1 and a.get('seedSource') == 'HISTORICAL_MASTER_ISSUER_FORM_EXACT_NAME' and a.get('seedCik'):
            ciks.add(str(a['seedCik']).zfill(10))
    return next(iter(ciks)) if len(ciks)==1 else None


def resolve_one(row, seed, by_cik):
    report=row.get('asOfReportDate')
    forms=query_forms(row)
    rec={'ticker':row.get('ticker'),'securityId':row.get('securityId'),'asOfReportDate':report,'issuerVariants':row.get('issuerVariants',[]),'historicalExactCik':seed,'classification':'UNKNOWN','attempts':[]}
    candidates=sorted([r for r in by_cik.get(seed,[]) if report and r['dateFiled']<=report], key=base.filing_sort_key)

    # One-way PIT rule: an issuer filing a foreign-private-issuer form before the report date is NON_US.
    foreign=[r for r in candidates if r['form'] in FOREIGN_FORMS]
    if foreign:
        fr=foreign[0]
        rec.update({'classification':'NON_US','resolutionSource':'PIT_FOREIGN_PRIVATE_ISSUER_FORM','evidenceForm':fr['form'],'evidenceDateFiled':fr['dateFiled'],'evidenceFilename':fr['filename']})
        return rec

    # Otherwise inspect a bounded set of issuer filings for explicit historical incorporation state.
    for fr in candidates[:3]:
        try:
            text,tr=detail_page(fr['filename'])
        except Exception as e:
            rec['attempts'].append({'form':fr['form'],'dateFiled':fr['dateFiled'],'filename':fr['filename'],'error':type(e).__name__})
            continue
        for issuer in forms:
            st,name=detail_entity_state(issuer,seed,text)
            rec['attempts'].append({'form':fr['form'],'dateFiled':fr['dateFiled'],'filename':fr['filename'],'transport':tr,'stateCode':st,'historicalEntityName':name})
            if st:
                rec.update({'classification':'US' if st in base.US_CODES else 'NON_US','stateCode':st,'resolutionSource':'PIT_FILING_DETAIL_ENTITY_STATE','historicalEntityName':name,'evidenceForm':fr['form'],'evidenceDateFiled':fr['dateFiled'],'evidenceFilename':fr['filename'],'evidenceTransport':tr})
                return rec
    return rec


def main():
    data=json.loads(SRC.read_text())
    unknown=[r for r in data.get('resolutionAudit',[]) if r.get('classification')=='UNKNOWN']
    seeded=[]
    for r in unknown:
        seed=seed_from_strict(r)
        if seed:
            seeded.append((r,seed))
    years=sorted({int(r.get('asOfReportDate','0000')[:4]) for r,_ in seeded if r.get('asOfReportDate')})
    master,transports=base.load_master(years)
    by_cik=defaultdict(list)
    for r in master:
        by_cik[str(r['cik']).zfill(10)].append(r)

    results=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
        futs=[ex.submit(resolve_one,r,seed,by_cik) for r,seed in seeded]
        for i,f in enumerate(concurrent.futures.as_completed(futs),1):
            results.append(f.result())
            if i%200==0:
                print('PROGRESS',json.dumps({'done':i,'resolved':sum(x['classification']!='UNKNOWN' for x in results),'foreignFormResolved':sum(x.get('resolutionSource')=='PIT_FOREIGN_PRIVATE_ISSUER_FORM' for x in results),'detailCache':len(DETAIL_CACHE)}),flush=True)

    key=lambda r:((r.get('ticker') or ''),(r.get('securityId') or ''),(r.get('asOfReportDate') or ''))
    results=sorted(results,key=key)
    out={
      'purpose':'General return-independent PIT country recovery. Identity is frozen to strict historical exact issuer-form -> unique CIK. Foreign private issuer forms (6-K/20-F/40-F and amendments) provide one-way NON_US evidence when filed by that CIK on/before report date. Otherwise a bounded set of pre-report-date historical SEC filing-detail pages may provide explicit State of Incorp. No current ticker metadata, fuzzy matching, US default, ranks, returns or strategy outcomes.',
      'inputUnknownCount':len(unknown),
      'seededHistoricalExactUniqueCikQueryCount':len(seeded),
      'seededHistoricalExactUniqueCikCount':len({s for _,s in seeded}),
      'resolvedCount':sum(r['classification']!='UNKNOWN' for r in results),
      'resolvedUSCount':sum(r['classification']=='US' for r in results),
      'resolvedNonUSCount':sum(r['classification']=='NON_US' for r in results),
      'foreignFormResolvedCount':sum(r.get('resolutionSource')=='PIT_FOREIGN_PRIVATE_ISSUER_FORM' for r in results),
      'filingDetailResolvedCount':sum(r.get('resolutionSource')=='PIT_FILING_DETAIL_ENTITY_STATE' for r in results),
      'remainingSeededUnknownCount':sum(r['classification']=='UNKNOWN' for r in results),
      'masterYears':years,
      'masterIndexTransports':transports,
      'detailCacheCount':len(DETAIL_CACHE),
      'results':results,
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in {'results','masterIndexTransports'}}),flush=True)

if __name__=='__main__':
    main()
