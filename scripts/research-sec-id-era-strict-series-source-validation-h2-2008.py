#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data/research'
PRIOR=DATA/'sec-id-era-strict-series-source-h1-2008.json'; CURRENT=DATA/'sec-id-era-strict-series-source-h2-2008.json'; OUT=DATA/'sec-id-era-strict-series-source-h2-2008-validation.json'
EXPECTED=[('2008-07','2008-07-31'),('2008-08','2008-08-29'),('2008-09','2008-09-30'),('2008-10','2008-10-31'),('2008-11','2008-11-28'),('2008-12','2008-12-31')]
SHA='31ac8ca8df99093cbcf98b916e599969481a77fcfda7cea915b3f415f8c09fbc'; ART={'h1_2008_strict_series_source':10088832684}
def main():
 prior=json.loads(PRIOR.read_text()); cur=json.loads(CURRENT.read_text()); closed=list(prior.get('closedHistoryReplaySnapshots',[]))+list(prior.get('monthSnapshots',[])); replay=cur.get('closedHistoryReplaySnapshots',[]); months=cur.get('monthSnapshots',[])
 pp={x['seriesId']:x for x in prior.get('positiveSeries',[])}; cp={x['seriesId']:x for x in cur.get('positiveSeries',[])}; fields=('cik','registrant','seriesId','seriesName','classes','binding'); missing=sorted(set(pp)-set(cp)); mismatch=sorted(s for s in pp if s in cp and any(pp[s].get(k)!=cp[s].get(k) for k in fields))
 checks={'h1CatalogShaExact':hashlib.sha256(PRIOR.read_bytes()).hexdigest()==SHA,'priorArtifactExact':cur.get('priorSourceArtifacts')==ART,'closedPrefixIs30Months':len(closed)==30,'closedReplayExact':replay==closed,'closedSourceFilingsExact':len(replay)==30 and all(a.get('sourceFilings')==b.get('sourceFilings') for a,b in zip(replay,closed)),'exactH2Schedule':[(m.get('signalMonth'),m.get('asOf')) for m in months]==EXPECTED,'sixMonthCoverage':len(months)==6,'allPriorSeriesRetained':not missing,'priorIdentityBindingExact':not mismatch,'identityConflictsZero':cur.get('seriesIdentityConflictCount')==0,'prospectusErrorsZero':cur.get('prospectusErrorCount')==0,'sourceErrorsZero':cur.get('sourceErrorCount')==0,'noLookahead':all(f.get('filingDate','')<=m.get('asOf','') and f.get('evidenceDateFiled','')<=m.get('asOf','') for m in replay+months for f in m.get('sourceFilings',[]))}
 out={'purpose':'Pre-defined H2 2008 strict-Series-source period-extension validation; no strategy outcomes are read.','checks':checks,'priorSourceArtifacts':ART,'missingPriorSeries':missing,'identityBindingMismatchSeries':mismatch,'closedReplayMonthCount':len(replay),'passed':all(checks.values())}; OUT.write_text(json.dumps(out,indent=2)+'\n'); print('H2_2008_SOURCE_VALIDATION',json.dumps(out,separators=(',',':')),flush=True)
 if not out['passed']: raise SystemExit(1)
if __name__=='__main__':main()
