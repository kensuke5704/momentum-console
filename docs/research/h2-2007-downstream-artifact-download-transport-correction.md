# H2 2007 Downstream Artifact Download Transport Correction

Defined: 2026-09-08 JST after downstream validation run `34192565485` failed during fixed-artifact download and before the frozen historical-Universe builder or H2-2007 downstream validator executed.

## Observed failure

Run `34192565485` passed all frozen implementation-blob assertions, then failed in the first artifact-download step with HTTP 404 while attempting to download artifact ZIP bytes through `gh api /repos/kensuke5704/momentum-console/actions/artifacts/<artifact-id>/zip`.

No H2-2007 builder output was produced, no downstream parity comparison executed, and no Universe/parity/strategy result was observed. The failure is therefore transport-only.

## Correction

Replace only the artifact-byte transport in the workflow with the already validated GitHub Actions mechanism used elsewhere in this research lineage:

- `actions/download-artifact@v4`
- fixed repository `${{ github.repository }}`
- fixed authoritative `run-id`
- exact fixed artifact `name`

The parser-invariance input remains run `34188697692`, artifact `10041408799`, artifact name `nq-holdings-parser-invariance-h1-h2-2007`.

The H2-2007 PIT country input remains run `34190587649`, artifact `10042478228`, artifact name `nq-series-id-pit-country-h2-2007`.

No source, holdings, mapping, country, N-PX, eligibility, builder, parity, threshold, ranking, or strategy rule changes. The validator script remains frozen at blob `72ae7532458d35e09b4b98bf221fbd566970aa07`, and the historical builder remains frozen at blob `1357402f34dfea1c1dbdcaac7de5078b680eb5c3`.

No Stage21 returns, ranks, CAGR, MaxDD, Calmar, trades, portfolio outcomes, or strategy outcomes are used by this correction.