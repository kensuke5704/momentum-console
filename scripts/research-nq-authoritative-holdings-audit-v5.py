#!/usr/bin/env python3
from __future__ import annotations
import json,re
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; r=ROOT/'data/research'
raw=json.loads((r/'nq-pit-holdings-hybrid-h1-2006.json').read_text()); catalog=json.loads((r/'sec-hybrid-etf-source-catalog-h1-2006.json').read_text())
zero={}; ng={}; bad=[]; summary_agg=[]; methods=Counter(); months=[]; amb=[]; temporal=[]
bad_re=re.compile(r'RESPECTIVELY|CAPITAL SHARE TRANSACTIONS|NET INCREASE|BEGINNING OF PERIOD|END OF PERIOD|TAX COST|UNREALIZED|NET REALIZED AND UNREALIZED|NET CHANGE IN UNREALIZED|NET INVESTMENT INCOME|SHAREHOLDER EXPENSES|ACCOUNT VALUE|EXPENSE RATIO|EXPENSES PAID|SPECIAL MEETING OF SHAREHOLDERS|DATE OF REPORTING PERIOD',re.I)
temporal_re=re.compile(r'^(?:JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)$|^SIX MONTHS ENDED\b',re.I)
cat_keys={(m['signalMonth'],s['canonicalIdentity'],s['filename'],s['filingDate']) for m in catalog['monthSnapshots'] for s in m['sourceFilings']}; out_keys=set()
for snap in raw['monthSnapshots']:
  stat=Counter(x.get('parseStatus') for x in snap['sourceFilings']); common=0; common_sources=0
  for f in snap['sourceFilings']:
    out_keys.add((snap['signalMonth'],f.get('canonicalIdentity'),f.get('sourceFilename'),f.get('filingDate')))
    if f.get('parseMethod'): methods[f['parseMethod']]+=1
    if f.get('parseStatus')=='PARSED_ZERO_HOLDINGS': zero[(f.get('canonicalIdentity'),f.get('sourceFilename'))]=f
    if f.get('parseStatus')=='NO_GROUPED_SCHEDULE': ng[(f.get('canonicalIdentity'),f.get('sourceFilename'))]=f
    c=sum(h.get('legacyAssetSection')=='COMMON_EQUITY' for h in f.get('holdings',[])); common+=c; common_sources+=bool(c)
    for h in f.get('holdings',[]):
      desc=str(h.get('description') or '')
      if bad_re.search(desc): bad.append({'identity':f.get('canonicalIdentity'),'description':desc})
      if temporal_re.search(desc): temporal.append({'identity':f.get('canonicalIdentity'),'description':desc})
      if re.match(r'^\s*(?:OTHER|OTHER\s+SECURITIES)\b',desc,re.I): summary_agg.append({'identity':f.get('canonicalIdentity'),'description':desc})
  months.append({'signalMonth':snap['signalMonth'],'catalogSourceSeriesCount':snap.get('catalogSourceSeriesCount'),'outputSourceSeriesCount':len(snap['sourceFilings']),'parseStatusCounts':dict(stat),'commonEquityHoldingCount':common,'commonEquitySourceCount':common_sources})
for filing in raw.get('filingAudit',[]):
  for e in filing.get('legacyAssignmentAudit') or []:
    if 'AMBIG' in str(e.get('assignmentRule') or '').upper() and e.get('assignedIdentity') is not None: amb.append({'accession':filing.get('accession'),'entry':e})
  for e in filing.get('seriesIdAssignmentAudit') or []:
    if 'AMBIG' in str(e.get('assignmentRule') or '').upper() and (e.get('seriesId') is not None or e.get('assignedIdentity') is not None): amb.append({'accession':filing.get('accession'),'entry':e})
missing=sorted(cat_keys-out_keys); extra=sorted(out_keys-cat_keys)
audit={'uniqueSourceFilingCount':raw.get('uniqueSourceFilingCount'),'filingFetchSuccessCount':raw.get('filingFetchSuccessCount'),'filingFetchErrorCount':raw.get('filingFetchErrorCount'),'uniqueParsedHoldingCount':raw.get('uniqueParsedHoldingCount'),'assetSectionCounts':raw.get('legacyAssetSectionCounts'),'parseMethodCountsAcrossSnapshots':dict(methods),'catalogKeyCount':len(cat_keys),'outputKeyCount':len(out_keys),'missingCurrentSourceKeyCount':len(missing),'extraOutputSourceKeyCount':len(extra),'uniqueZeroHoldingTargetCount':len(zero),'uniqueNoGroupedTargetCount':len(ng),'ambiguousAssignedMarkerCount':len(amb),'badFinancialTextHoldingCount':len(bad),'temporalLabelHoldingCount':len(temporal),'summaryAggregateHoldingCount':len(summary_agg),'zeroTargets':[{'canonicalIdentity':x.get('canonicalIdentity'),'seriesName':x.get('seriesName'),'sourceFilename':x.get('sourceFilename')} for x in zero.values()],'noGroupedTargets':[{'canonicalIdentity':x.get('canonicalIdentity'),'seriesName':x.get('seriesName'),'sourceFilename':x.get('sourceFilename')} for x in ng.values()],'badExamples':bad[:20],'temporalExamples':temporal[:20],'summaryAggregateExamples':summary_agg[:20],'missingKeys':missing[:20],'extraKeys':extra[:20],'months':months}
(r/'momentum-v2-9-authoritative-holdings-audit-v5-h1-2006.json').write_text(json.dumps(audit,indent=2)+'\n')
print('HOLDINGS_AUDIT_V5',json.dumps({k:v for k,v in audit.items() if k not in {'zeroTargets','noGroupedTargets','badExamples','temporalExamples','summaryAggregateExamples','missingKeys','extraKeys','months'}}),flush=True)
for m in months: print('MONTH',json.dumps(m),flush=True)
for x in audit['zeroTargets']: print('ZERO',json.dumps(x),flush=True)
for x in audit['noGroupedTargets']: print('NO_GROUPED',json.dumps(x),flush=True)
assert raw.get('uniqueSourceFilingCount')==38
assert raw.get('filingFetchErrorCount')==0
assert not missing and not extra and not zero and not ng and not amb and not bad and not temporal and not summary_agg
