# Gate B Progress — 2026-09-04

Structural validation only. No Stage21 returns, CAGR, MaxDD, Calmar, or 2006–2018 performance outcomes were used.

## Confirmed transition evidence

- Gate A mechanics: PASS.
- 2020-01 legacy three-series aggregate shadow: 8/9 Production names, Spearman 0.842, Production Top2 2/2 retained.
- Transition source fidelity: LRGE 92.9% count / 95.9% weight; GFIN 94.2% / 97.4%; PPTY 93.9% / 98.0%.
- Transition CORP check: among EC+US holdings in first Production N-PORT filings, 226/226 were issuerCat=CORP.

## 2006 source-series discovery

The fixed three 2006 N-Q filing index pages expose SEC `Series and Classes/Contracts Information` through r.jina transport when parsed according to the rendered grammar:

- `Series [S#########](...)Fund Name`
- `Class/Contract [C#########](...)Fund Name TICKER`

The corrected metadata parser recovered 49 registered series from the three filings. Comparing those SEC filing-index Series IDs against the corrected 2006 PIT artifact shows **20/20 PIT series are contained in the independently parsed filing-index series set**.

This establishes that series identity within the frozen source submissions can be recovered from SEC metadata without holdings-name matching or Production ranks. It does **not yet** prove independent discovery of the three registrant/source submissions themselves.

## 2006 mapping and country state

- Explicit COMMON_EQUITY bridge accepted: 936 EC holdings.
- Baseline N-PX mapping: 69.95% count / 78.98% weight.
- Structural-only mapping extension: 73.90% count / 82.49% weight; no fuzzy/edit-distance auto-acceptance.
- Baseline mapped-country UNKNOWN retry raised all-EC resolved weight to 50.97%.
- Country attribution on structural mapping additions contributed 27.53 resolved weight; combined all-EC resolved-weight coverage is approximately **52.35%**.

Rejected country routes after fixed tests:
- current ticker CIK seed + historical COMPANY CONFORMED NAME exact validation: 0/50 additional resolutions.
- deterministic complete-submission `.txt` + historical COMPANY CONFORMED NAME + STATE-OF-INCORPORATION: 0/30 additional resolutions.

Active next route:
- use current ticker metadata only as an exact ticker+issuer CIK seed;
- obtain country evidence only from the historical SEC filing **index page** available by the legacy report date;
- parse `State of Incorp.` / `STATE OF INCORPORATION` from that PIT index metadata;
- UNKNOWN remains UNKNOWN.

Intel's 2005 10-K filing index demonstrates that this metadata can be exposed on the filing index even when the individual filing document / complete submission route fails to expose it reliably.

## Gate status

Universe reconstruction is **not yet confirmed**.

Remaining blockers:
1. materially raise conservative 2006 issuer-country resolved-weight coverage above ~52.35% without coercing UNKNOWN to US;
2. independently discover the historical ETF registrant/source-submission population, not merely the Series IDs within already-fixed submissions;
3. build a full aggregate legacy Universe from independently discovered sources and rerun Gate B metrics;
4. only then implement the historical Universe builder;
5. broad 2006–2018 Stage21 performance remains unopened until bridge rules are frozen.
