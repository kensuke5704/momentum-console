# H2 2007 Strict Series Source — Period-Extension Validation Definition

Committed before observing any H2 2007 strict-Series-source result.

## Scope

This checkpoint validates only the Jul–Dec 2007 extension of the historical source catalog. It does not evaluate Stage21 returns, ranks, CAGR, MaxDD, Calmar, trades, portfolio outcomes, or any strategy performance.

## Fixed prior lineage

- closed H1 2007 strict Series source run: `34184083615`
- closed H1 2007 strict Series source artifact: `10040000632`
- H1 2007 source-catalog SHA256: `fcf8bd62ff1182f2d8a9dc99c2f6fd30bcf3b3a2974d04786d1a943f1c9fa21b`
- H1 2007 candidate-prefilter artifact: `10039881783`
- H2 2007 cumulative N-Q inventory run: `34187039092`
- H2 2007 cumulative N-Q inventory artifact: `10040860433`
- H2 2007 cumulative complete-portfolio inventory run: `34187049034`
- H2 2007 cumulative complete-portfolio inventory artifact: `10040863522`

## Frozen semantics

The strict Series-level acceptance and binding semantics must remain exactly the validated H1 2007 semantics. In particular:

- candidate-prefilter evidence is recall-oriented discovery only and is not final ETF evidence;
- a prior candidate CIK may be carried forward at the candidate layer, but prior Series acceptance is never inherited merely because of candidate carry-forward;
- final Series acceptance must be independently re-established using contemporaneously public issuer-own evidence and the frozen structural Series/Class binding rules;
- no trust-global sibling binding;
- no fuzzy/edit-distance identity repair;
- no holdings, ranking, return, or strategy-outcome inference in source identification;
- no future Series/Class backfill.

## Required checks for PASS

1. **Cumulative inventory replay**
   - the H2 2007 cumulative N-Q inventory must reproduce every H1 2007 cumulative N-Q row through `2007-06-29` exactly;
   - the H2 2007 cumulative complete-portfolio inventory must reproduce every H1 2007 cumulative complete-portfolio row through `2007-06-29` exactly.

2. **Candidate recall only**
   - every H1 2007 positive candidate CIK must remain in the merged H2 2007 candidate-review set;
   - carry-forward status may affect candidate review eligibility only, never final positive Series acceptance.

3. **Prior positive Series identity and binding retention**
   - every H1 2007 positive Series must remain present in the cumulative H2 2007 strict source catalog;
   - for every prior positive Series, its accepted Series identity and binding method must reproduce exactly.

4. **Prior snapshot replay**
   - the cumulative H2 2007 source catalog, when restricted to each H1 2007 Jan–Jun signal date, must reproduce the closed H1 2007 source snapshot exactly at the `sourceFilings` level.

5. **H2 period/cardinality**
   - exactly six signal months are required: `2007-07` through `2007-12`;
   - signal dates are fixed at `2007-07-31`, `2007-08-31`, `2007-09-28`, `2007-10-31`, `2007-11-30`, `2007-12-31`;
   - no source occurrence may rely on a filing after the applicable signal date.

6. **Strict-source integrity**
   - Series identity conflicts must be zero;
   - prospectus/source fetch or parse errors that would make the result incomplete must be zero;
   - any `sourceNoSchedule` record is audit-only and may not be admitted to `sourceOccurrences`;
   - newly accepted Series must satisfy the same issuer-own evidence and structural binding rules as the frozen H1 implementation.

## Failure handling

If any required check fails, stop and audit the lineage or implementation. Do not relax evidence grammar, binding rules, identity rules, thresholds, or PIT constraints after observing H2 2007 results.
