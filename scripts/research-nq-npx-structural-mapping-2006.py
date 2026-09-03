#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re
from collections import defaultdict,Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('base',ROOT/'scripts'/'research-nq-npx-mapping-2006.py')
base=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(base)
NQ=ROOT/'data/research/nq-pit-holdings-2006.json'; NPX=ROOT/'data/research/npx-security-master-2006.json'; OUT=ROOT/'data/research/nq-npx-structural-mapping-2006.json'

def cleaned_forms(raw:str):
    vals=[raw]
    s=raw
    # Remove only trailing presentation annotations, iteratively: N-Q footnotes, share-class labels, and SEC-style /ST jurisdiction suffixes.
    pats=[
      r'\s*\((?:[a-z]{1,3}|\d{1,3})\)\s*$',
      r'\s*\((?:CLASS|CL)\s+[A-Z0-9-]+(?:\s+SHARES?)?\)\s*$',
      r'\s+(?:CLASS|CL)\s+[A-Z0-9-]+(?:\s+SHARES?)?\s*$',
      r'\s*/[A-Z]{2}\s*$',
    ]
    changed=True
    while changed:
      changed=False
      for p in pats:
        ns=re.sub(p,'',s,flags=re.I).strip()
        if ns!=s:
          vals.append(ns);s=ns;changed=True
    return list(dict.fromkeys(v for v in vals if v))

def structural_aliases(raw:str):
    out=[]
    for v in cleaned_forms(raw):
      for a in base.aliases(v):
        if a not in out: out.append(a)
    return out

def main():
    nq,npx=json.loads(NQ.read_text()),json.loads(NPX.read_text())
    by=defaultdict(set)
    for row in npx['records']:
      t,s=row.get('ticker'),row.get('securityId')
      if not base.valid_identity(t,s): continue
      for key in base.edge_the_variants(base.norm(row['normalizedIssuer'])): by[key].add((t,s))
    names=sorted(by)
    details=[]; methods=Counter(); matched_c=matched_w=amb_c=amb_w=0.0; total_c=total_w=0.0
    for rec in nq['records']:
      for h in rec['holdings']:
        desc=h['description'];w=float(h.get('weight') or 0); total_c+=1;total_w+=w
        ids=[];ma=None;method=None
        if base.artifact(desc):
          status='PARSER_ARTIFACT'
        else:
          # Baseline conservative exact aliases first.
          for a in base.aliases(desc):
            f=by.get(a,set())
            if f: ids=sorted(f);ma=a;method='BASELINE_EXACT';break
          if not ids:
            aa,ai=base.unique_adr_base_alias(desc,by)
            if ai: ids=ai;ma=aa;method='BASELINE_ADR_BASE_UNIQUE'
          # New rule 1: exact match after trailing presentation/share-class cleanup.
          if not ids:
            base_set=set(base.aliases(desc))
            for a in structural_aliases(desc):
              if a in base_set: continue
              f=by.get(a,set())
              if f: ids=sorted(f);ma=a;method='STRUCTURAL_SUFFIX_EXACT';break
          # New rule 2: long unique prefix only; no edit distance. Require the union of candidate identities to be exactly one.
          if not ids:
            candidates=set(); prefix_names=[]
            for q in structural_aliases(desc):
              if len(q)<20: continue
              for n in names:
                if min(len(q),len(n))>=20 and (q.startswith(n) or n.startswith(q)):
                  candidates.update(by[n]);prefix_names.append(n)
            if len(candidates)==1:
              ids=sorted(candidates);ma=structural_aliases(desc)[-1] if structural_aliases(desc) else None;method='UNIQUE_LONG_PREFIX'
          if len(ids)==1: status='MATCHED_UNIQUE';matched_c+=1;matched_w+=w;methods[method]+=1
          elif len(ids)>1: status='AMBIGUOUS';amb_c+=1;amb_w+=w
          else: status='UNMAPPED'
        d={'seriesId':rec.get('seriesId'),'reportDate':rec.get('reportDate'),'description':desc,'weight':w,'status':status,'structuralAliases':structural_aliases(desc)}
        if ids:d['identities']=[{'ticker':t,'securityId':s} for t,s in ids]
        if method:d['matchMethod']=method
        if ma:d['matchedAlias']=ma
        details.append(d)
    eligible=[d for d in details if d['status']!='PARSER_ARTIFACT']; ew=sum(d['weight'] for d in eligible); ec=len(eligible)
    out={'year':2006,'purpose':'Return-independent deterministic sensitivity test of structural issuer identity rules. Adds only trailing share-class/jurisdiction cleanup and unique >=20-character prefix identity reconciliation; no edit-distance/fuzzy auto-match.','eligibleHoldingCount':ec,'eligibleHoldingWeight':ew,'uniqueMatchedCount':int(matched_c),'uniqueMatchedCountRate':matched_c/ec,'uniqueMatchedWeight':matched_w,'uniqueMatchedWeightRate':matched_w/ew,'ambiguousCount':int(amb_c),'ambiguousWeight':amb_w,'matchMethods':dict(methods),'newStructuralMatches':sum(v for k,v in methods.items() if k.startswith('STRUCTURAL') or k.startswith('UNIQUE')),'newStructuralWeight':sum(d['weight'] for d in details if d.get('matchMethod') in {'STRUCTURAL_SUFFIX_EXACT','UNIQUE_LONG_PREFIX'}),'details':details}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='details'}),flush=True)
    for d in sorted((x for x in details if x.get('matchMethod') in {'STRUCTURAL_SUFFIX_EXACT','UNIQUE_LONG_PREFIX'}),key=lambda x:x['weight'],reverse=True)[:50]:print('NEW',json.dumps(d),flush=True)
if __name__=='__main__':main()
