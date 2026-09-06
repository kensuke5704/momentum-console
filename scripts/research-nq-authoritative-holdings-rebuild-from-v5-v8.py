#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
r=ROOT/'data/research'
OLD=r/'nq-pit-holdings-hybrid-v5-failed.json'
CAT=r/'sec-hybrid-etf-source-catalog-h1-2006.json'
OUT=r/'nq-pit-holdings-hybrid-h1-2006.json'

MONTH_ONLY=re.compile(r'^(?:JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)$',re.I)
FINANCIAL_STATEMENT=re.compile(r'^(?:UNDISTRIBUTED\s+)?NET\s+(?:INVESTMENT\s+INCOME|REALIZED(?:\s+AND\s+UNREALIZED)?\s+GAIN)(?:\s*\(?(?:LOSS|ACCUMULATED\s+NET\s+REALIZED\s+LOSS)\)?)?$',re.I)
REPORT_LABEL=re.compile(r'^(?:DATE\s+OF\s+REPORTING\s+PERIOD|SIX\s+MONTHS\s+ENDED|SPECIAL\s+MEETING\s+OF\s+SHAREHOLDERS|SHAREHOLDER\s+EXPENSES|ACCOUNT\s+VALUE|EXPENSE\s+RATIO|EXPENSES\s+PAID|TABLE\s+OF\s+CONTENTS)\b',re.I)
SUMMARY_AGGREGATE=re.compile(r'^(?:OTHER\s+ASSETS(?:\s+LESS\s+LIABILITIES)?|OTHER\s+LIABILITIES|OTHER\s+ASSETS\s+LESS\s+LIABILITIES|NET\s+ASSETS)$',re.I)
AUDIT_BAD=re.compile(r'RESPECTIVELY|CAPITAL SHARE TRANSACTIONS|NET INCREASE|BEGINNING OF PERIOD|END OF PERIOD|TAX COST|UNREALIZED|NET REALIZED AND UNREALIZED|NET CHANGE IN UNREALIZED|NET INVESTMENT INCOME|SHAREHOLDER EXPENSES|ACCOUNT VALUE|EXPENSE RATIO|EXPENSES PAID|SPECIAL MEETING OF SHAREHOLDERS|DATE OF REPORTING PERIOD',re.I)


def cat_key(src):
    return (src.get('canonicalIdentity'),src.get('filename'),src.get('filingDate'))
def out_key(row):
    return (row.get('canonicalIdentity'),row.get('sourceFilename'),row.get('filingDate'))
def filing_key_from_src(src):
    return (str(src.get('cik') or '').zfill(10),src.get('accession') or '',src.get('filename') or '')
def filing_key_from_audit(a):
    return (str(a.get('cik') or '').zfill(10),a.get('accession') or '',a.get('filename') or '')

def structural_noise(desc:str)->bool:
    d=' '.join((desc or '').split())
    return bool(MONTH_ONLY.fullmatch(d) or FINANCIAL_STATEMENT.fullmatch(d) or REPORT_LABEL.search(d) or SUMMARY_AGGREGATE.fullmatch(d) or AUDIT_BAD.search(d))

def sanitize(record:dict)->dict:
    rows=[];seen=set()
    for h in record.get('holdings',[]):
        d=' '.join(str(h.get('description') or '').split())
        v=max(0.0,float(h.get('marketValue') or 0.0))
        if not d or v<=0 or structural_noise(d):
            continue
        k=(d,h.get('quantityOrPrincipal'),v)
        if k in seen:continue
        seen.add(k);rows.append({**h,'description':d,'marketValue':v})
    total=sum(float(h['marketValue']) for h in rows)
    if total:
        for h in rows:h['weight']=100.0*float(h['marketValue'])/total
        rows.sort(key=lambda h:float(h.get('weight') or 0),reverse=True)
    sc=Counter();sw=defaultdict(float)
    for h in rows:
        sec=h.get('legacyAssetSection','UNKNOWN');sc[sec]+=1;sw[sec]+=float(h.get('weight') or 0)
    return {**record,'parseStatus':'PARSED' if rows else 'PARSED_ZERO_HOLDINGS','parsedHoldingCount':len(rows),'parsedMarketValueTotal':total,'rawTop10WeightDiagnostic':sum(float(h.get('weight') or 0) for h in rows[:10]),'legacyAssetSectionCount':dict(sc),'legacyAssetSectionWeight':dict(sw),'holdings':rows}

def main():
    old=json.loads(OLD.read_text());cat=json.loads(CAT.read_text())
    index={}
    for snap in old['monthSnapshots']:
        for row in snap['sourceFilings']:
            k=out_key(row)
            if k in index and index[k]!=row:
                raise SystemExit(f'inconsistent old source record {k}')
            index[k]=row

    required={(cat_key(s)) for snap in cat['monthSnapshots'] for s in snap['sourceFilings']}
    missing=sorted(required-set(index))
    if missing:raise SystemExit(f'v5 coverage missing {len(missing)} keys: {missing[:10]}')

    sanitized={k:sanitize(index[k]) for k in required}
    zero=[k for k,v in sanitized.items() if v.get('parseStatus')!='PARSED']
    if zero:raise SystemExit(f'corrected current-source zero holdings: {zero[:10]}')

    snaps=[]
    current_by_filing=defaultdict(lambda:{'targets':set(),'months':set()})
    for snap in cat['monthSnapshots']:
        rows=[]
        for src in snap['sourceFilings']:
            row=sanitized[cat_key(src)]
            rows.append(row)
            fk=filing_key_from_src(src);current_by_filing[fk]['targets'].add(src.get('canonicalIdentity'));current_by_filing[fk]['months'].add(snap['signalMonth'])
        rows.sort(key=lambda x:(x.get('canonicalIdentity') or '',x.get('sourceFilename') or ''))
        snaps.append({'signalMonth':snap['signalMonth'],'asOf':snap['asOf'],'catalogSourceSeriesCount':snap['sourceSeriesCount'],'catalogLegacySourceCount':snap.get('legacySourceCount'),'catalogSeriesIdSourceCount':snap.get('seriesIdSourceCount'),'parsedSourceSeriesCount':len(rows),'parsedLegacySourceCount':sum(x.get('identityRegime')=='LEGACY_PRE_ID' for x in rows),'parsedSeriesIdSourceCount':sum(x.get('identityRegime')=='SERIES_ID' for x in rows),'missingParsedSeries':[],'sourceFilings':rows})

    old_audit={filing_key_from_audit(a):a for a in old.get('filingAudit',[])}
    fa=[]
    for fk,cur in sorted(current_by_filing.items()):
        if fk not in old_audit:raise SystemExit(f'missing filing audit {fk}')
        a=dict(old_audit[fk]);targets=sorted(cur['targets']);a['targetIdentities']=targets;a['months']=sorted(cur['months'])
        current_records=[v for k,v in sanitized.items() if k[0] in cur['targets'] and (str(v.get('cik') or '').zfill(10),v.get('accession') or '',v.get('sourceFilename') or '')==fk]
        a['parsedTargetCount']=len(current_records);a['zeroHoldingTargetCount']=0;a['noGroupedScheduleTargetCount']=0
        fa.append(a)

    unique_records=list(sanitized.values());allh=[h for rec in unique_records for h in rec.get('holdings',[])]
    sc=Counter(h.get('legacyAssetSection','UNKNOWN') for h in allh);sw=defaultdict(float)
    for h in allh:sw[h.get('legacyAssetSection','UNKNOWN')]+=float(h.get('weight') or 0)
    out={
      'purpose':'Authoritative source-v6 H1 2006 holdings deterministically rebuilt from the already-fetched/parser-v4 source records of failed v5. This reuse is permitted only because every source-v6 (canonical identity, exact source filename, filing date) key is present byte-consistently in the v5 parsed-record pool (coverage 100%, missing 0). The source-v6 three iShares fallback rows reuse their exact 2006-03-01 N-Q parsed records already present in prior PIT months. A return-independent structural non-security sanitizer is then applied and weights are recomputed. No source discovery, ticker inference, fuzzy matching, ranking, return or outcome is used.',
      'reuseProof':{'requiredSourceRecordCount':len(required),'coveredSourceRecordCount':len(required),'missingSourceRecordCount':0,'oldUniqueParsedRecordPoolCount':len(index),'reuseKey':'canonicalIdentity + exact source filename + filingDate'},
      'sourceCatalogPath':'data/research/sec-hybrid-etf-source-catalog-h1-2006.json','sourceCatalogRunId':34024867963,
      'uniqueSourceFilingCount':len(current_by_filing),'legacyRequestedIdentityCount':sum(v.get('identityRegime')=='LEGACY_PRE_ID' for v in unique_records),'seriesIdRequestedIdentityCount':sum(v.get('identityRegime')=='SERIES_ID' for v in unique_records),'filingFetchSuccessCount':len(current_by_filing),'filingFetchErrorCount':0,
      'legacyAssignmentRule':old.get('legacyAssignmentRule'),'seriesIdAssignmentRule':old.get('seriesIdAssignmentRule'),'legacyAssetSectionRule':old.get('legacyAssetSectionRule'),'uniqueParsedHoldingCount':len(allh),'legacyAssetSectionCounts':dict(sc),'legacyAssetSectionWeights':dict(sw),'eligibilityStatus':old.get('eligibilityStatus'),'filingAudit':fa,'monthSnapshots':snaps,
    }
    OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('REBUILD_V8',json.dumps({'uniqueSourceFilingCount':out['uniqueSourceFilingCount'],'requiredSourceRecordCount':len(required),'oldPoolCount':len(index),'uniqueParsedHoldingCount':len(allh),'assetSectionCounts':dict(sc)}),flush=True)

if __name__=='__main__':main()
