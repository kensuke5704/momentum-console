#!/usr/bin/env python3
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'data/research/sec-legacy-etf-series-source-preid-base-2006.json'
REPL=ROOT/'data/research/preid-direct-replacements'
OUT=ROOT/'data/research/sec-legacy-etf-series-source-preid-direct-2006.json'
MONTHS=[('2006-01','2006-01-31'),('2006-02','2006-02-28')]

def main():
    base=json.loads(BASE.read_text())
    shards=[]
    for p in sorted(REPL.glob('*.json')):shards.append(json.loads(p.read_text()))
    if len(shards)!=4:raise SystemExit(f'expected 4 replacement shards, got {len(shards)}')
    rciks=sorted({c for s in shards for c in s.get('assignedCiks',[])})
    if len(rciks)!=4:raise SystemExit(f'expected 4 replacement CIKs, got {rciks}')
    def repl_list(key):
        old=[x for x in base.get(key,[]) if x.get('cik') not in rciks]
        new=[x for s in shards for x in s.get(key,[])]
        return old+new
    positives=repl_list('positiveIdentities')
    occ=repl_list('sourceOccurrences')
    pros=repl_list('prospectusAudit')
    audit=repl_list('sourceAudit')
    # Rebuild identity uniqueness deterministically from replacement-aware occurrences.
    identities={}
    for r in sorted(occ,key=lambda x:(x['evidenceDateFiled'],x['legacyIdentity'],x['evidenceFilename'])):identities.setdefault(r['legacyIdentity'],r)
    positives=sorted(identities.values(),key=lambda x:x['legacyIdentity'])
    snaps=[]
    for month,asof in MONTHS:
        latest={}
        for r in occ:
            if r['sourceFilingDate']>asof or r['evidenceDateFiled']>asof:continue
            cur=latest.get(r['legacyIdentity'])
            if cur is None or (r['sourceFilingDate'],r.get('sourceAccession') or '')>(cur['sourceFilingDate'],cur.get('sourceAccession') or ''):latest[r['legacyIdentity']]=r
        src=sorted(latest.values(),key=lambda x:(x['cik'],x['normalizedSeriesName']))
        snaps.append({'signalMonth':month,'asOf':asof,'sourceSeriesCount':len(src),'sourceFilings':src})
    binding=Counter(r['binding'] for r in positives);forms=Counter(r['sourceForm'] for r in occ)
    out={**base}
    out.update({
      'purpose':'Strict pre-Series-ID complete-portfolio ETF source catalog with four mixed Vanguard trusts re-resolved using direct Series-level class association. Title-explicit ETF semantic and ETF-dedicated registrant bindings retain the prior exact-title rule; only the former generic <=6-line local-class branch is tightened. Direct local association requires the same title phrase to carry ETF/VIPER/Exchange-Traded class semantics or an exact title phrase to be immediately followed by a class-only line. No later Series IDs, holdings outcomes, ranks, returns or strategy results are used.',
      'directReplacementCiks':rciks,
      'positiveIdentityCount':len(positives),'positiveIdentities':positives,
      'sourceOccurrenceCount':len(occ),'sourceOccurrences':sorted(occ,key=lambda x:(x['legacyIdentity'],x['sourceFilingDate'],x.get('sourceAccession') or '')),
      'bindingCounts':dict(sorted(binding.items())),'sourceFormCounts':dict(sorted(forms.items())),
      'prospectusAudit':pros,'sourceAudit':audit,'monthSnapshots':snaps,
      'candidateSourceFilingCount':len(audit),'candidateRegistrantWithSourceFilingCount':len({x['cik'] for x in audit}),
      'operationalEvidenceFilingCount':sum(bool(x.get('creationIssuerOwnEvidence')) and bool(x.get('exchangeIssuerOwnEvidence')) for x in pros),
      'sourceNoScheduleCount':sum('error' not in x and not x.get('hasCompletePortfolioSchedule',False) for x in audit),
      'amendmentNoScheduleCount':sum(str(x.get('form','')).endswith('/A') and 'error' not in x and not x.get('hasCompletePortfolioSchedule',False) for x in audit),
      'prospectusErrorCount':sum('error' in x for x in pros),'sourceErrorCount':sum('error' in x for x in audit)
    })
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:out[k] for k in ('directReplacementCiks','positiveIdentityCount','sourceOccurrenceCount','bindingCounts','prospectusErrorCount','sourceErrorCount')},indent=2))
    print(json.dumps([{'month':x['signalMonth'],'sourceSeriesCount':x['sourceSeriesCount']} for x in snaps],indent=2))
if __name__=='__main__':main()
