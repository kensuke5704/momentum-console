# H2 2007 N-PX Filing Transport Correction

Defined: 2026-09-08 JST after run `34189762843` fixed the quarterly-index transport and deterministically reached the pre-defined H2-2007 N-PX source-selection stage, but failed while fetching the selected filing bodies. No monthly H2-2007 N-PX master passed validation and no H2-2007 structural-mapping result was produced.

## Observed transport failure

Run `34189762843` successfully read all four official 2007 SEC `master.zip` indexes and produced the source-selection counts required by the already-defined rule:

- 2007 N-PX/N-PX-A inventory: 3,512 filings
- primary N-PX: 3,409
- N-PX/A: 103
- July signal: 64 selected / 64 cumulative admissions
- August signal: 75 selected / 139 cumulative admissions
- September signal: 75 selected / 181 cumulative admissions
- October signal: 75 selected / 205 cumulative admissions
- November signal: 75 selected / 205 cumulative admissions
- December signal: 75 selected / 205 cumulative admissions

The frozen helper's filing-body transport routes each SEC filing through `r.jina.ai`. During this run, 118 of the 205 already-admitted filing fetches failed, overwhelmingly with HTTP 429, plus one timeout. The pre-defined validator correctly stopped rather than replacing sources.

This correction is transport-only. It does **not** alter the H2-2007 N-PX inventory, source-selection rule, admitted CIK/filing semantics, parser, issuer normalization, signal dates, PIT rules, broad-family CIK set, deduplication, or downstream mapping semantics.

## Corrected filing-body transport

For every source selected by the unchanged base implementation:

1. fetch the exact official SEC Archives filing URL already determined by the selected `filename`;
2. send the compliant research User-Agent already used by the successful SEC `master.zip` transport;
3. pace requests conservatively;
4. retry the **same URL only** on transient HTTP 429/5xx errors, timeouts, resets, or other transient URL errors, using deterministic increasing backoff;
5. never substitute a different filing, CIK, accession, source family, or proxy after observing a fetch failure;
6. decode the official SEC filing bytes and pass them to the unchanged frozen `parse_records()` implementation;
7. if any of the fixed selected filings still fails after retries, stop the validation.

The source-selection counts above are asserted before filing-body parsing in the corrected wrapper so that a transport retry cannot silently change the already-observed selection boundary.

No mapping coverage, N-Q target name, country label, Universe rank, return, or strategy outcome may influence this correction.
