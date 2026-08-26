# Live SEC N-PORT ingestion research

This path evaluates whether the Dynamic Universe can be reproduced with information actually available before the strategy's next-session-open execution. It does not change Production strategy rules or publish a Universe automatically.

## Confirmed infrastructure constraint

GitHub-hosted Ubuntu/macOS runners and Vercel functions receive HTTP 403 from SEC EDGAR Archives. A separate header audit also confirmed HTTP 403 from the quarterly `/files/dera/data/form-n-port-data-sets/*_nport.zip` endpoints on GitHub-hosted runners. Therefore neither individual EDGAR ingestion nor direct quarterly ZIP refresh should be promoted as a cloud Production dependency without a runtime whose SEC access has been proven.

A successful bootstrap-only rebuild is not proof that fresh SEC ingestion worked.

## SEC quarterly posting rule

SEC states that Form N-PORT data sets are updated quarterly and that documents filed after 5:30 PM Eastern on the last business day of a quarter are included in the subsequent quarterly posting. The SEC landing page listed 2026 Q2 and was last reviewed/updated on June 30, 2026.

For a strategy that trades at the next session open, the research audit therefore evaluates three information sets:

1. `prior-quarter`: only the previous completed quarter or earlier;
2. `strict-posting`: on Mar/Jun/Sep/Dec signals, the current-quarter posting is available for the next open, but filings dated on the final business day are excluded;
3. `inclusive-posting`: on quarter-end signals, filings dated on the final business day are also included.

`strict-posting` is the conservative operational bound when acceptance timestamps are unavailable. `inclusive-posting` is an upper bound. Non-quarter-end months use only the previous completed quarter in both modes.

## Availability-aware backtest result

Audit run: GitHub Actions `Research Quarterly Live-Compatible Backtest`, run 7, 2026-08-26.

Full period (2020-01 onward):

| Universe information set | CAGR | MaxDD | Final equity |
| --- | ---: | ---: | ---: |
| Published historical baseline | 55.25% | -21.93% | 18.59x |
| Prior-quarter only | 44.94% | -20.67% | 11.78x |
| Strict posting bound | 56.58% | -20.67% | 19.68x |
| Inclusive posting bound | 59.06% | -20.67% | 21.84x |

The bootstrap begins at 2020 Q1, so Jan-Feb 2020 do not contain the already-available 2019 Q4 data. To remove that initial-data bias, the audit also reports results from 2020-04-01:

| Universe information set | CAGR | MaxDD | Final equity |
| --- | ---: | ---: | ---: |
| Published historical baseline | 62.29% | -21.93% | 22.16x |
| Prior-quarter only | 48.25% | -20.67% | 12.42x |
| Strict posting bound | 60.64% | -20.67% | 20.75x |
| Inclusive posting bound | 63.27% | -20.67% | 23.03x |

The practically relevant conclusion is that once quarter-end posting availability is modeled, the Production strategy's performance is close to the historical baseline. The strict 2020-Q2-onward bound is only about 1.66 percentage points of CAGR below the corresponding baseline, while MaxDD is slightly smaller.

This supports the strategy logic against the N-PORT timing concern. It does not by itself solve the cloud ingestion infrastructure constraint.

## Fail-closed live-ingestion contract

The experimental individual-filing snapshot is accepted only when all of the following are true:

- at least one scanned daily index was available;
- at least one NPORT-P filing was discovered;
- every discovered accession was parsed or already present in the prior live snapshot;
- no parse failure remains;
- the snapshot reaches the required scan end date.

The snapshot is written through a temporary file and renamed only after checks pass. `REQUIRE_LIVE_NPORT=1` prevents `build-universe.ts` from silently falling back to the quarterly baseline.

## Production recommendation

Do not merge an SEC-live cloud dependency into Production yet. Keep the existing Production strategy frozen. A future Production data path must satisfy one of these conditions:

1. a self-hosted/runtime endpoint with demonstrated SEC access fetches and validates the data, or
2. a validated quarterly snapshot is ingested from a trusted artifact/source and committed before the monthly Universe build.

In either case, the Universe update must fail closed if the expected fresh snapshot is unavailable. The research results show that exact intra-quarter EDGAR ingestion is not required to preserve the strategy thesis; quarter-end posting availability is sufficient for close historical parity.
