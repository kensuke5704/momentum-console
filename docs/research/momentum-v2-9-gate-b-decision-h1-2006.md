# Momentum v2.9 — Gate B decision for H1 2006

Date: 2026-09-06

## Decision

**Gate B: FAIL**

`Universe reconstruction is confirmed` must **not** be declared yet.

Production Stage21 remains frozen. No broad 2006–2018 performance/backtest is authorized by this decision.

## Authoritative lineage

- Source qualification: source v6 — PASS
- Authoritative holdings: artifact `9986815485` — PASS
- Frozen N-PX master: artifact `9876020712`
- Mapping-only artifact: `9987093683`
- Final Gate execution: workflow run `34027854106`
- Final Gate artifact: `9987700449`
- Country execution: eight deterministic PIT country shards, exact-key merge coverage

## Structural checks that passed

- Source identity / boundary / bridge conflicts: none
- Filing fetch: 38 / 38 success
- Catalog/output source keys: 1190 / 1190; missing 0; extra 0
- Zero-holdings targets: 0
- Missing grouped schedules: 0
- Ambiguous source-marker assignment: 0
- Financial-text / temporal-label / summary-aggregate parser contamination: 0
- Allowed deterministic N-PX methods only
- Current-ticker country fallback: disabled; count 0
- Frozen accepted transition evidence: PASS
- Transition CORP semantic bridge: 226 / 226 EC+US holdings were CORP
- Primary H1 2006 Universe: non-empty, Top80 in all six months

## Strict PIT country result

Across 9,575 unresolved mapped identity/report-date queries after explicit same-filing/CINS/receipt evidence:

- US resolved: 6,216
- NON-US resolved: 33
- Remaining UNKNOWN: 3,326

UNKNOWN is excluded from the primary reconstruction. The upper-bound sensitivity changes only deterministically mapped UNKNOWN holdings to US; ambiguous and unmapped securities remain excluded.

## Gate blocker

The sole Gate conflict is:

`COUNTRY_UPPER_BOUND_MATERIAL`

Monthly primary-vs-country-upper-bound diagnostics:

| Month | Top80 overlap | Rank correlation | Primary Top2 retention |
|---|---:|---:|---:|
| 2006-01 | 77.5% | 0.5345 | 100% |
| 2006-02 | 81.25% | 0.6750 | 100% |
| 2006-03 | 77.5% | 0.8604 | 100% |
| 2006-04 | 73.75% | 0.8199 | 100% |
| 2006-05 | 73.75% | 0.8143 | 100% |
| 2006-06 | 77.5% | 0.8547 | 100% |

Gate sensitivity requires overlap >=70%, rank correlation >=0.75 where defined, and Top2 retention >=80% in every month. January and February fail the rank-correlation requirement.

## Additional diagnostic

A structural diagnostic tested whether remaining historical-country UNKNOWNs were caused by reading only flat SEC submission headers while missing SGML `<COMPANY-DATA>` / `<STATE-OF-INCORPORATION>` fields.

- Sample: 120 strict UNKNOWN queries already having historical exact issuer -> unique CIK and successful SEC submission retrieval
- SGML-only resolutions: 0

Therefore the current blocker is not fixed by adding an SGML parser fallback.

## Consequence

The H1 2006 source/holdings/mapping pipeline is structurally clean, but conservative country uncertainty is still material enough to change the Top80 ordering under the predefined upper-bound test. Gate B must remain FAIL unless additional **point-in-time, return-independent country evidence** reduces that uncertainty without current-data fallback or rule tuning.
