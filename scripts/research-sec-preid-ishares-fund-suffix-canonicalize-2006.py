#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
INP=ROOT/'data/research/sec-legacy-etf-series-source-preid-v29genuine-2006.json'
OUT=ROOT/'data/research/sec-legacy-etf-series-source-preid-v29genuine-ishares-canonical-2006.json'
MONTHS=[('2006-01','2006-01-31'),('2006-02','2006-02-28')]


def filing_key(r:dict)->tuple[str,str,str]:
    return (r.get('sourceAccession') or '',r.get('sourceFilename') or '',r.get('sourceFilingDate') or '')


def main()->None:
    d=json.loads(INP.read_text())
    positives=d['positiveIdentities']; occ=d['sourceOccurrences']
    by_cik_name={(r['cik'],r['normalizedSeriesName']):r for r in positives}
    occ_by_id=defaultdict(list)
    for r in occ: occ_by_id[r['legacyIdentity']].append(r)

    id_map={r['legacyIdentity']:r['legacyIdentity'] for r in positives}
    canonical_name={r['legacyIdentity']:r['normalizedSeriesName'] for r in positives}
    merges=[]

    for r in positives:
        if not r.get('registrant','').upper().startswith('ISHARES'):
            continue
        name=r['normalizedSeriesName']
        if name.endswith(' FUND'):
            continue
        fund_name=name+' FUND'
        peer=by_cik_name.get((r['cik'],fund_name))
        if not peer:
            continue
        left_keys={filing_key(x) for x in occ_by_id[r['legacyIdentity']]}
        right_keys={filing_key(x) for x in occ_by_id[peer['legacyIdentity']]}
        shared=sorted(left_keys & right_keys)
        if not shared:
            raise RuntimeError(f'iShares suffix pair lacks same-filing co-occurrence: {name} / {fund_name}')
        id_map[r['legacyIdentity']]=peer['legacyIdentity']
        canonical_name[r['legacyIdentity']]=fund_name
        merges.append({
            'cik':r['cik'],
            'canonicalLegacyIdentity':peer['legacyIdentity'],
            'canonicalNormalizedSeriesName':fund_name,
            'mergedLegacyIdentity':r['legacyIdentity'],
            'mergedNormalizedSeriesName':name,
            'sameFilingEvidence':[{'accession':k[0],'filename':k[1],'filingDate':k[2]} for k in shared],
        })

    # No canonical target may receive more than the exact X / X FUND pair.
    members=defaultdict(list)
    for r in positives: members[id_map[r['legacyIdentity']]].append(r)
    for cid,rows in members.items():
        if len(rows)<=1: continue
        names={x['normalizedSeriesName'] for x in rows}
        canon=next(x['normalizedSeriesName'] for x in rows if x['legacyIdentity']==cid)
        if len(rows)!=2 or names!={canon[:-5],canon} or not canon.endswith(' FUND'):
            raise RuntimeError(f'unsafe iShares canonical collision {cid}: {sorted(names)}')

    new_pos=[]
    for cid,rows in sorted(members.items()):
        rep=deepcopy(next((x for x in rows if x['legacyIdentity']==cid),rows[0]))
        if len(rows)>1:
            rep['identityCanonicalizationRule']='ISHARES_SAME_CIK_SAME_FILING_EXACT_TRAILING_FUND'
            rep['identityObservedSeriesNames']=sorted({x['seriesName'] for x in rows})
            rep['identityObservedNormalizedSeriesNames']=sorted({x['normalizedSeriesName'] for x in rows})
        new_pos.append(rep)

    # Remap, then collapse duplicate observations within the same filing. If both
    # exact aliases occur in that filing, retain the observed title ending FUND.
    buckets=defaultdict(list)
    for r in occ:
        rec=deepcopy(r); old=r['legacyIdentity']; new=id_map[old]
        if new!=old:
            rec['sourceObservedLegacyIdentity']=old
            rec['legacyIdentity']=new
        buckets[(new,)+filing_key(rec)].append(rec)
    new_occ=[]; collapsed=0
    for key,rows in sorted(buckets.items()):
        if len(rows)==1:
            new_occ.append(rows[0]); continue
        canonical_rows=[x for x in rows if x['normalizedSeriesName'].endswith(' FUND')]
        if len(canonical_rows)!=1:
            raise RuntimeError(f'unsafe same-filing alias collapse {key}: {[x["normalizedSeriesName"] for x in rows]}')
        chosen=deepcopy(canonical_rows[0])
        chosen['sourceObservedAliasTitles']=sorted({x['seriesName'] for x in rows})
        chosen['sourceObservedAliasNormalizedTitles']=sorted({x['normalizedSeriesName'] for x in rows})
        chosen['sourceAliasCollapseRule']='ISHARES_SAME_FILING_EXACT_TRAILING_FUND_PREFERRED'
        new_occ.append(chosen); collapsed+=len(rows)-1

    snapshots=[]
    for month,asof in MONTHS:
        latest={}
        for r in new_occ:
            if r['sourceFilingDate']>asof or r['evidenceDateFiled']>asof: continue
            lid=r['legacyIdentity']; cur=latest.get(lid)
            if cur is None or (r['sourceFilingDate'],r.get('sourceAccession') or '')>(cur['sourceFilingDate'],cur.get('sourceAccession') or ''):
                latest[lid]=r
        rows=sorted(latest.values(),key=lambda x:(x['cik'],x['normalizedSeriesName'],x['legacyIdentity']))
        snapshots.append({'signalMonth':month,'asOf':asof,'sourceSeriesCount':len(rows),'sourceFilings':rows})

    out={**d}
    out.update({
        'purpose':d.get('purpose','')+' Exact iShares pre-ID title aliases differing only by a trailing FUND token are collapsed only when both titles occur under the same CIK in the same source filing; the observed FUND title is retained for schedule binding. No post-ID metadata, ticker, fuzzy matching, holdings, ranks, returns, or strategy outcomes are used.',
        'iSharesFundSuffixCanonicalizationRule':'SAME_CIK + EXACT_X_VS_X_FUND + SAME_SOURCE_FILING_COOCCURRENCE',
        'iSharesFundSuffixMergeCount':len(merges),
        'iSharesFundSuffixMerges':merges,
        'preISharesCanonicalPositiveIdentityCount':len(positives),
        'positiveIdentityCount':len(new_pos),
        'positiveIdentities':new_pos,
        'preISharesCanonicalSourceOccurrenceCount':len(occ),
        'sourceOccurrenceCount':len(new_occ),
        'collapsedSameFilingAliasOccurrenceCount':collapsed,
        'sourceOccurrences':sorted(new_occ,key=lambda x:(x['legacyIdentity'],x['sourceFilingDate'],x.get('sourceAccession') or '')),
        'monthSnapshots':snapshots,
        'bindingCounts':dict(sorted(Counter(r['binding'] for r in new_pos).items())),
        'sourceFormCounts':dict(sorted(Counter(r['sourceForm'] for r in new_occ).items())),
    })
    OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({
        'preIdentityCount':len(positives),'identityCount':len(new_pos),'mergeCount':len(merges),
        'preOccurrenceCount':len(occ),'occurrenceCount':len(new_occ),'collapsedOccurrences':collapsed,
        'months':{x['signalMonth']:x['sourceSeriesCount'] for x in snapshots},
        'merges':merges,
    }),flush=True)

if __name__=='__main__': main()
