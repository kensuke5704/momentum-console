# Gate B PASS — 2026-09-07 JST

Status: **PASS** for the preregistered legacy-Universe structural/source-fidelity gate. This conclusion uses no Stage21 returns, CAGR, MaxDD, Calmar, trades, or 2006–2018 strategy outcomes.

## Frozen authoritative H1 2006 lineage

- branch: `research/nq-npx-mapping-2006-20260903`
- pre-Series-ID source artifact: `9972690542`
- post-Series-ID source artifact: `9963958301`
- authoritative hybrid catalog SHA256: `e2405277fe03a4208e163a43d724fd7364e139ad229caa70251b151f1d53b801`
- hybrid holdings run/artifact: `34089965073` / `10006530879`
- deterministic structural mapping run/artifact: `34090287022` / `10006580498`
- strict PIT country Gate B run/artifact: `34104858455` / `10012280475`
- mapping extreme sensitivity run/artifact: `34125899895` / `10020057970`

Production remains frozen; `main` was not modified.

## Source and holdings integrity

Hybrid source population:
- legacy positive identities: 192
- post-ID positive Series: 198
- exact same-CIK + exact-normalized-name unique bridges: 111
- ambiguous bridges: 0
- monthly source counts Jan–Jun: 192 / 204 / 267 / 270 / 273 / 279

Raw holdings:
- unique source filings: 50
- filing fetch success: 50 / 50
- unique parsed holdings: 17,353
- explicit `COMMON_EQUITY`: 11,339
- missing parsed Series: 0 in every month

## Frozen mapping semantics

Primary mapping remains deterministic only:
- exact normalized issuer;
- ADR base only when unique;
- exact match after accepted trailing presentation/share-class/jurisdiction cleanup;
- >=20-character prefix only when the union of candidate identities is exactly one.

No fuzzy/edit-distance candidate is auto-accepted.

Raw mapping uncertainty remains visible and is not hidden:
- monthly unique-mapped COMMON_EQUITY weight rates are approximately 65.01%, 69.21%, 79.10%, 79.10%, 76.59%, 74.83%;
- ambiguity is non-zero.

## PIT country and CORP bridge

Country classification is causal:
- evidence must satisfy `evidenceDateFiled <= signal date`;
- current ticker metadata may seed a CIK only;
- current state/country is never historical classification evidence;
- unresolved remains `UNKNOWN` in the primary Universe.

CORP evidence remains structural/materiality evidence rather than a silently generalized 2006 rule:
- transition EC+US cohort: 226 / 226 CORP;
- old 2006 COMMON_EQUITY materiality sample: zero explicit non-CORP-name hits;
- authoritative hybrid COMMON_EQUITY materiality audit: zero explicit non-CORP-name hits.

Production eligibility order remains `COMMON_EQUITY -> US -> CORP -> source eligibility`.

## Preregistered practical thresholds

Gate B uses the same practical thresholds as Gate A:
- median TopK/Top80 overlap >= 0.80;
- minimum monthly TopK/Top80 overlap >= 0.70;
- median Spearman >= 0.75;
- Production/primary Top2 individual retention >= 0.80;
- both Top2 retained in >= 0.70 of evaluated months.

## Direct transition evidence

Accepted transition source fidelity remains:
- LRGE: 92.9% constituent / 95.9% weight retention;
- GFIN: 94.2% / 97.4%;
- PPTY: 93.9% / 98.0%;
- 2020-01 aggregate shadow: 8 / 9 common, Spearman 0.842, Top2 2 / 2.

## H1 2006 country upper-bound sensitivity

Run `34104858455`, artifact `10012280475`:
- median TopK overlap: **0.8855357143**
- minimum TopK overlap: **0.8695652174**
- median Spearman: **0.9564368674**
- Top2 individual retention: **0.9166666667**
- both Top2 monthly retention: **0.8333333333**
- result: **PASS**

This upper bound treats only already mapped `UNKNOWN` country identities optimistically as US; it does not change the primary country rule.

## H1 2006 mapping extreme sensitivity

Run `34125899895`, artifact `10020057970`.

This deliberately overstates mapping uncertainty without assigning guessed tickers:
- every unresolved positive COMMON_EQUITY row is optimistically assumed US/CORP for source eligibility;
- unresolved holdings are grouped only by exact frozen issuer normalization;
- each unresolved exact issuer group is treated as an entirely new anonymous security, even though in reality some may duplicate an already mapped security;
- all such anonymous securities are allowed to compete in the breadth ranking simultaneously.

Both raw-normalized-exact and accepted-cleaned-exact variants produced the same aggregate result:
- median TopK overlap: **0.825**
- minimum TopK overlap: **0.7258064516**
- median Spearman: **0.9523245110**
- Top2 individual retention: **1.0**
- both Top2 monthly retention: **1.0**
- result: **PASS**

Source eligibility itself was also stable under this extreme assumption: relative to the country upper bound, only SPDR O-STRIP ETF in Jan/Feb and Utilities Select Sector SPDR Fund in Jun became newly eligible; Mar–May had no additional eligibility flip.

## Gate B conclusion

The direct transition comparison clears the preregistered fidelity thresholds, the strict PIT country upper-bound sensitivity clears them, and a deliberately stronger assignment-free mapping residual sensitivity also clears them. The remaining unresolved mapping/country rows therefore do not have enough demonstrated aggregate ranking capacity to invalidate the reconstructed breadth Universe under the preregistered practical thresholds.

**Gate B = PASS. Universe reconstruction is confirmed at the structural/source-fidelity gate level.**

This does **not** authorize changing Production parameters, and it does not authorize using 2006–2018 strategy outcomes to retune source, parser, mapping, country, eligibility, or ranking rules.

Next allowed step: freeze this bridge and implement the historical Universe builder from the accepted rules. Do not immediately run broad 2006–2018 Stage21 performance until the next validation step is explicitly defined and passed.
