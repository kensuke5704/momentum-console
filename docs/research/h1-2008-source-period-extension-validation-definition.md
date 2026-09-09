# H1 2008 Strict Series Source — Period-Extension Validation Definition

Committed before observing any H1 2008 strict-Series-source result.

## Scope

This checkpoint validates only the Jan–Jun 2008 extension of the historical strict Series source catalog. It does not evaluate Stage21 returns, ranks, CAGR, MaxDD, Calmar, trades, portfolio outcomes, or any strategy performance.

The closed source prefix is 2006-01 through 2007-12. It must not be recomputed, re-optimized, or rewritten by evidence first discovered in H1 2008.

## Fixed prior and input lineage

Closed H2 2007 source:

- strict Series source run: `34188233028`
- strict Series source artifact: `10041257985`
- source-catalog SHA256: `9ffed81a42044f7388221a60450a24967ea61f108eb63f66464699ada1849631`

H1 2008 cumulative inventories and candidate discovery:

- cumulative N-Q inventory run: `34303684929`
- cumulative N-Q inventory artifact: `10085851582`
- cumulative complete-portfolio inventory run: `34303717315`
- cumulative complete-portfolio inventory artifact: `10085863572`
- candidate-prefilter shard run: `34303793542`
- candidate-prefilter merge run: `34304025116`
- candidate-prefilter merge artifact: `10085971852`
- candidate-prefilter artifact digest: `sha256:9fbc6a6fd0e806fa499b350d91d14b55e4644acf5010db0057c06de403196506`

The H1 2008 candidate merge is recall-oriented only. It contains 144 candidate CIKs after preserving all 133 H2 2007 candidate CIKs; this cardinality is not a target and must not be used to tune final Series acceptance.

## Frozen semantics

The strict Series-level acceptance and binding semantics remain exactly the validated H2 2007 semantics. In particular:

- candidate-prefilter evidence is recall-oriented discovery only and is not final ETF evidence;
- a prior candidate CIK may be carried forward at the candidate layer, but prior Series acceptance is never inherited merely because of candidate carry-forward;
- a CIK first discovered in H1 2008 may be reviewed for H1 2008, but must not alter any closed 2006-2007 source snapshot merely because later evidence exists;
- final Series acceptance must be independently re-established using contemporaneously public issuer-own operational ETF evidence and the frozen structural Series/Class binding rules;
- broad references to investments in third-party ETFs are not issuer-own operational evidence;
- no trust-global sibling binding;
- no registrant/trust name as Series identity;
- no fuzzy/edit-distance identity repair;
- no ticker, holdings, ranking, return, or strategy-outcome inference in source identification;
- no future Series/Class backfill;
- complete-portfolio and amendment-replacement semantics remain unchanged;
- conventional mutual-fund siblings, including Vanguard siblings, are not admitted unless that Series independently satisfies the frozen ETF evidence and binding rules;
- any `sourceNoSchedule` record is audit-only and may not enter `sourceOccurrences`.

## Required checks for PASS

1. **Cumulative inventory replay**
   - the H1 2008 cumulative N-Q inventory must reproduce every closed H2 2007 cumulative N-Q row through `2007-12-31` exactly;
   - the H1 2008 cumulative complete-portfolio inventory must reproduce every closed H2 2007 cumulative complete-portfolio row through `2007-12-31` exactly.
   - These upstream checks are already mechanically enforced by the H1 inventory workflows and remain part of the source validation lineage.

2. **Candidate recall only**
   - every H2 2007 positive candidate CIK must remain in the merged H1 2008 candidate-review set;
   - carry-forward status may affect candidate review eligibility only, never final positive Series acceptance;
   - a H1 2008 newly discovered candidate cannot be used to revise any 2006-2007 final Series acceptance or source snapshot.

3. **Prior positive Series identity and binding retention**
   - every H2 2007 positive Series must remain present when the cumulative H1 2008 implementation replays the same PIT evidence available by `2007-12-31`;
   - for every prior positive Series, its accepted Series identity, Series name used for binding, and binding method must reproduce exactly;
   - later H1 2008 Series/Class metadata or prospectus evidence may not repair or replace a closed-period identity.

4. **Closed source-snapshot replay**
   - all 24 closed signal snapshots from `2006-01` through `2007-12` must reproduce exactly at the `sourceFilings` level;
   - no H1 2008 source filing, Series identity, ETF evidence item, or newly discovered candidate may appear in any closed snapshot unless the identical item was already public and part of the authoritative closed lineage for that signal date;
   - failure of any one closed month is a hard stop.

5. **H1 2008 period/cardinality**
   - exactly six new signal months are required: `2008-01` through `2008-06`;
   - signal dates are fixed at `2008-01-31`, `2008-02-29`, `2008-03-31`, `2008-04-30`, `2008-05-30`, and `2008-06-30`;
   - no source occurrence may rely on a filing or operational-evidence item filed after the applicable signal date.

6. **Strict-source integrity**
   - Series identity conflicts must be zero;
   - prospectus/source fetch or parse errors that would make the catalog incomplete must be zero;
   - every accepted source occurrence must have a complete portfolio schedule under the frozen parser semantics;
   - every newly accepted Series must satisfy the same issuer-own evidence and structural binding rules as the frozen H2 2007 implementation;
   - amendment replacement is allowed only when the amendment itself contains a complete portfolio schedule;
   - `sourceNoSchedule` remains audit-only.

7. **No strategy leakage**
   - no Stage21 return, rank, CAGR, MaxDD, Calmar, trade, portfolio outcome, or later strategy behavior may be consulted to accept, reject, repair, or tune a Series, filing, binding, evidence rule, or source snapshot.

## Failure handling

If any required check fails, stop and audit lineage, transport, parsing, identity, or implementation. Do not relax evidence grammar, binding rules, identity rules, thresholds, PIT constraints, or closed-prefix invariants after observing the H1 2008 result.

This checkpoint does not authorize changes to `main` or Production and does not authorize broad 2006–2018 Stage21 performance analysis.
