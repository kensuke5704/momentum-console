# H2 2007 PIT N-PX Master Validation Definition

Defined: 2026-09-08 JST before any H2-2007 N-PX period-extension master or structural-mapping result is evaluated.

This definition is subordinate to `docs/research/h2-2007-downstream-period-extension-validation-definition.md`. It is not a new named gate and does not authorize Stage21 performance analysis.

## Fixed inputs and frozen semantics

- frozen pre-2007 N-PX security-master artifact: `9876020712`
- frozen N-PX record parser: `scripts/research-npx-security-master-2006.py` blob `bc2d44dda6bfae00ebba22a81ba867a18bbd7ba5`
- frozen issuer normalization implementation: `scripts/research-npx-security-master-build-2006.py` blob `ad977557eb7f48fc0c0d71a2c369b0d61f6c1239`
- frozen accepted security-mapping implementation remains `scripts/research-nq-catalog-structural-mapping-h1-2006.py` blob `690479017fc82dce2480ded5d1ffafbb76721722`
- H2 signal dates are fixed at `2007-07-31`, `2007-08-31`, `2007-09-28`, `2007-10-31`, `2007-11-30`, and `2007-12-31`.

The 2006 frozen master is already closed evidence and may be present in every H2-2007 month. Its legacy broad-fund supplement contains year-level provenance (`"2006"`) rather than a full filing date, so it must be treated only as frozen pre-2007 evidence; it must not be used to infer any 2007 availability date.

## 2007 incremental source-selection rule

For each H2 signal date, independently from N-Q holdings, mapping misses, country labels, ranks, returns, or strategy outcomes:

1. Read the official SEC EDGAR 2007 quarterly `master.idx` inventory.
2. Retain primary Form `N-PX` filings only for incremental admission; `N-PX/A` is inventory/audit information but is not a new primary source candidate.
3. Restrict candidates to `dateFiled <= signal date`.
4. Within the public candidate set, take the earliest primary filing per CIK, matching the frozen 2006 builder's one-representative-per-CIK convention.
5. Apply the frozen 64-position deterministic equal-quantile CIK sample rule from `research-npx-security-master-build-2006.py`; if there are at most 64 representatives, retain all.
6. Also admit the same pre-fixed broad-fund-family CIK set used by the 2006 broad supplement, whenever that CIK has a primary 2007 N-PX filing public by the signal date. For each fixed CIK use its earliest public primary 2007 filing. This source rule is independent of H2 mapping outcomes.
7. Admission is monotone across H2 signals: once a 2007 source filing has been admitted from a public signal-date candidate set, it remains available to later H2 signals. A later signal may add sources but may not remove already-public admitted evidence.
8. Parse each admitted filing with the frozen N-PX parser and normalize issuer names with the frozen normalizer. No mapping-specific parser adaptation is permitted.
9. For each signal month, merge the frozen pre-2007 master with only admitted 2007 rows whose `sourceFilingDate <= signal date`. Deduplicate deterministically by `(normalizedIssuer, ticker, securityId)`, preserving the earliest available occurrence.

## Required PIT assertions

PASS requires all of the following before structural mapping is run:

- the 2007 SEC filing inventory is obtained without fetch/index errors;
- every admitted incremental source is primary Form `N-PX` and has `dateFiled <= admittedAtSignal`;
- every incremental security record in a monthly master has `sourceFilingDate <= that month's signal date`;
- no source first admitted after a signal date appears in that signal month's master;
- admitted source sets and incremental evidence are monotone across Jul-Dec;
- the frozen pre-2007 master is copied without source-selection mutation;
- parsing uses the frozen parser and issuer normalization implementations above;
- source selection uses no N-Q target names, mapping coverage, country result, Universe rank, return, or strategy outcome.

Fetch failures for an admitted source are a stop condition, not permission to replace the source after observing mapping results.

## Structural-mapping boundary

Only after this PIT master validation passes may H2-2007 structural mapping run. Mapping must then use the monthly PIT master corresponding to each signal date while reusing the frozen accepted mapping rules exactly. A 2007 identity first public after a signal date must never repair that earlier signal month.

## Prohibited

Do not use Stage21 returns, ranks, CAGR, MaxDD, Calmar, trades, portfolio outcomes, or other strategy performance. Do not use fuzzy/edit-distance ticker repair, current metadata repair, future Series/Class evidence, or later N-PX filings to rewrite earlier H2 months. Do not modify `main` or Production.
