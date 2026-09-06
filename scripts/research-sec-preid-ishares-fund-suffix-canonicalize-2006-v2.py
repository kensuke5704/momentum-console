#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from collections import Counter,defaultdict
from copy import deepcopy
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
INP=Path(os.environ.get('PREID_ISHARES_INPUT_PATH',str(ROOT/'data/research/sec-legacy-etf-series-source-preid-v29canonical-2006.json')))
OUT=Path(os.environ.get('PREID_ISHARES_OUTPUT_PATH',str(ROOT/'data/research/sec-legacy-etf-series-source-preid-v29canonical-ishares-2006.json')))
MONTHS=[('2006-01','2006-01-31'),('2006-02','2006-02-28')]


def filing_key(r): return (r.get('sourceAccession') or '',r.get('sourceFilename') or '',r.get('sourceFilingDate') or '')


def main():
    d=json.loads(INP.read_text()); positives=d['positiveIdentities'];occ=d['sourceOccurrences']
    by_key={(r['cik'],r['normalizedSeriesName']):r for r in positives}
    occ_by_id=defaultdict(list)
    for r in occ: occ_by_id[r['legacyIdentity']].append(r)
    id_map={r['legacyIdentity']:r['legacyIdentity'] for r in positives}; merges=[]

    for r in positives:
        if not r.get('registrant','').upper().startswith('ISHARES'): continue
        name=r['normalizedSeriesName']
        if name.endswith(' FUND'): continue
        peer=by_key.get((r['cik'],name+' FUND'))
        if not peer: continue
        shared=sorted({filing_key(x) for x in occ_by_id[r['legacyIdentity']]} & {filing_key(x) for x in occ_by_id[peer['legacyIdentity']]})
        if not shared: continue
        id_map[r['legacyIdentity']]=peer['legacyIdentity']
        merges.append({'cik':r['cik'],'canonicalLegacyIdentity':peer['legacyIdentity'],'canonicalNormalizedSeriesName':peer['normalizedSeriesName'],'mergedLegacyIdentity':r['legacyIdentity'],'mergedNormalizedSeriesName':name,'sameFilingEvidence':[{'accession':k[0],'filename':k[1],'filingDate':k[2]} for k in shared]})

    members=defaultdict(list)
    for r in positives: members[id_map[r['legacyIdentity']]].append(r)
    for cid,rows in members.items():
        if len(rows)<=1: continue
        canon=next(x['normalizedSeriesName'] for x in rows if x['legacyIdentity']==cid); names={x['normalizedSeriesName'] for x in rows}
        if len(rows)!=2 or not canon.endswith(' FUND') or names!={canon[:-5],canon}:
            raise RuntimeError(f'unsafe iShares collision {cid}: {sorted(names)}')

    new_pos=[]
    for cid,rows in sorted(members.items()):
        rep=deepcopy(next((x for x in rows if x['legacyIdentity']==cid),rows[0]))
        if len(rows)>1:
            rep['identityCanonicalizationRule']='ISHARES_SAME_CIK_SAME_FILING_EXACT_TRAILING_FUND'
            rep['identityObservedSeriesNames']=sorted({x['seriesName'] for x in rows})
            rep['identityObservedNormalizedSeriesNames']=sorted({x['normalizedSeriesName'] for x in rows})
        new_pos.append(rep)

    buckets=defaultdict(list)
    for r in occ:
        rec=deepcopy(r);old=r['legacyIdentity'];new=id_map[old]
        if new!=old:
            rec['sourceObservedLegacyIdentity']=old;rec['legacyIdentity']=new
        buckets[(new,)+filing_key(rec)].append(rec)
    new_occ=[];collapsed=0
    for key,rows in sorted(buckets.items()):
        # Collapse only the exact alias pair when both appear in one filing. Other
        # repeated observations are not silently merged.
        norm={x['normalizedSeriesName'] for x in rows}
        if len(rows)==2:
            fund=[x for x in rows if x['normalizedSeriesName'].endswith(' FUND')]
            if len(fund)==1 and norm=={fund[0]['normalizedSeriesName'][:-5],fund[0]['normalizedSeriesName']}:
                chosen=deepcopy(fund[0]);chosen['sourceObservedAliasTitles']=sorted({x['seriesName'] for x in rows});chosen['sourceObservedAliasNormalizedTitles']=sorted(norm);chosen['sourceAliasCollapseRule']='ISHARES_SAME_FILING_EXACT_TRAILING_FUND_PREFERRED';new_occ.append(chosen);collapsed+=1;continue
        if len(rows)>1 and len({(x['normalizedSeriesName'],x.get('sourceAccession'),x.get('sourceFilename')) for x in rows})>1:
            raise RuntimeError(f'unexpected duplicate canonical occurrence bucket {key}: {[x["normalizedSeriesName"] for x in rows]}')
        new_occ.append(rows[0])

    snaps=[]
    for month,asof in MONTHS:
        latest={}
        for r in new_occ:
            if r['sourceFilingDate']>asof or r['evidenceDateFiled']>asof: continue
            lid=r['legacyIdentity'];cur=latest.get(lid)
            if cur is None or (r['sourceFilingDate'],r.get('sourceAccession') or '')>(cur['sourceFilingDate'],cur.get('sourceAccession') or ''): latest[lid]=r
        rows=sorted(latest.values(),key=lambda x:(x['cik'],x['normalizedSeriesName'],x['legacyIdentity']))
        snaps.append({'signalMonth':month,'asOf':asof,'sourceSeriesCount':len(rows),'sourceFilings':rows})

    out={**d}
    out.update({'purpose':d.get('purpose','')+' Before complete-schedule qualification, exact iShares pre-ID aliases differing only by a trailing FUND token are canonicalized only when both titles occur under the same CIK in the same contemporaneous source filing. The FUND identity is the canonical label while source-observed titles remain available for exact schedule binding. No post-ID metadata, ticker, fuzzy matching, holdings, ranks, returns or strategy outcomes are used.','iSharesFundSuffixCanonicalizationRule':'SAME_CIK + EXACT_X_VS_X_FUND + SAME_SOURCE_FILING_COOCCURRENCE','iSharesFundSuffixMergeCount':len(merges),'iSharesFundSuffixMerges':merges,'preISharesCanonicalPositiveIdentityCount':len(positives),'positiveIdentityCount':len(new_pos),'positiveIdentities':new_pos,'preISharesCanonicalSourceOccurrenceCount':len(occ),'sourceOccurrenceCount':len(new_occ),'collapsedSameFilingAliasOccurrenceCount':collapsed,'sourceOccurrences':sorted(new_occ,key=lambda x:(x['legacyIdentity'],x['sourceFilingDate'],x.get('sourceAccession') or '')),'monthSnapshots':snaps,'bindingCounts':dict(sorted(Counter(r['binding'] for r in new_pos).items())),'sourceFormCounts':dict(sorted(Counter(r['sourceForm'] for r in new_occ).items()))})
    OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('ISHARES_CANON_V2',json.dumps({'preIdentityCount':len(positives),'identityCount':len(new_pos),'mergeCount':len(merges),'preOccurrenceCount':len(occ),'occurrenceCount':len(new_occ),'collapsedOccurrences':collapsed,'merges':merges}),flush=True)
    if len(merges)!=5: raise SystemExit(f'expected exactly 5 pre-ID iShares same-filing FUND alias pairs, got {len(merges)}')

if __name__=='__main__': main()
