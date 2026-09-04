# Momentum Research Handoff — Canonical Entry Point

This file is the stable entry point for new ChatGPT sessions and research agents.

## Read first

Current detailed handoff:
- Branch: `research/nq-npx-mapping-2006-20260903`
- Path: `docs/research/momentum-handoff-current.md`

Latest 2006 delta:
- Path: `docs/research/nq-npx-mapping-2006-20260903.md`

The detailed handoff is canonical. Read it first, then the delta.

## Objective and hard stop

Reconstruct a point-in-time historical ETF-holdings Universe for 2006 onward that is economically as close as possible to frozen Production N-PORT, without changing Production strategy `momentum-stage21-sbi-2026-09-v1`.

Do **not** implement the historical/legacy Universe builder until reproducibility is confirmed.  
Do **not** run broad 2006–2018 Stage21 performance yet.

## Current status — 2026-09-04

### Gate A — PASS

Production mechanics reproduce strongly over the first 12 Production Universe months:
- median Top-K overlap **93.75%**
- minimum **92.5%**
- median Spearman **0.9996**
- Production Top2 retention **100%**

### Transition Gate B — strong but not sufficient alone

Nearest complete pre-Production holdings reports for the actual three 2020-01 source series retain later N-PORT holdings at:
- LRGE: **92.9% count / 95.9% weight**
- GFIN: **94.2% / 97.4%**
- PPTY: **93.9% / 98.0%**

2020-01 aggregate legacy shadow:
- 8/9 Production names = **88.9%**
- Spearman **0.842**
- Production Top2 **2/2 retained**

This is strong direct transition evidence, but the run begins from the known Production source series.

### CORP bridge

Direct raw N-PORT transition checks show that among `EC+US` holdings:
- LRGE 42/42 CORP
- GFIN 69/69 CORP
- PPTY 115/115 CORP
- combined **226/226 = 100% CORP**

CORP is no longer the principal blocker for this bridge.

### 2006 EC / security identity

Accepted legacy EC rule: explicit `COMMON_EQUITY` only.
- 936 EC holdings across 20 corrected PIT series
- common-equity weight **99.63%**

Baseline EC-filtered N-PX mapping:
- 654 mapped
- **69.95% count / 78.98% weight**

Deterministic structural identity reconciliation only:
- share-class/jurisdiction cleanup
- long unique-prefix match only when candidate set is one
- no fuzzy/edit-distance auto-match

Structural result:
- 691 mapped
- **73.90% count / 82.49% weight**

### 2006 country bridge — current main blocker

Conservative country hierarchy:
- alphabetic CINS => NON_US
- explicit ADR/GDR => NON_US
- historical SEC filing-time state/country from deterministic CIK => US/NON_US
- current ticker metadata may seed CIK only
- UNKNOWN stays UNKNOWN

After full 12-shard country attribution and UNKNOWN retry:
- baseline mapped resolved: **59.17% count / 62.68% weight**
- all 936 EC holdings resolved: **42.95% count / 50.97% weight**

Country classification on new structural matches adds resolved weight 27.53, raising all-EC resolved weight to approximately **52.35%**.

This is still insufficient.

Rejected/low-value country routes:
- current ticker CIK + historical name validation: **0/50**
- complete-submission `.txt`: **0/30**

New active lead: historical SEC **filing index pages** can expose `State of Incorp.` directly. Validate this route next on high-weight UNKNOWN issuers.

### 2006 source-series discovery — major progress

Important correction: the earlier zero-series result was a parser defect, not missing SEC data and not a transport failure.

Historical SEC/r.jina filing index pages do preserve Series/Class/Ticker metadata. After fixing the concatenated rendered grammar, run `33842315528` / artifact `9925317298` extracted:
- **49 unique historical Series IDs** from the fixed three 2006 N-Q submissions
- valid historical tickers including XLY, XLP, XLE, XLF, XLV, XLI, XLB, XLK, XLU, XLG, RSP, TMW, DGT, RWR, MTK, XBI, XHB and XSD

Direct comparison to the corrected 2006 PIT confirms **20/20 = 100% series coverage** within those fixed source submissions.

What this proves:
- series identity within a known historical filing can be discovered from SEC filing metadata without holdings content or Production ranks.

What remains:
- the three historical source submissions/registrants were inherited from the fixed pilot;
- a scalable market-wide process still has to discover the relevant historical fund filings/registrants independently.

## Current gate

Universe reconstruction is **not yet confirmed**.

Continue in this order:
1. validate filing-index `State of Incorp.` PIT country resolution and improve resolved-weight coverage materially above ~52.35%;
2. create a scalable market-wide historical fund-filing discovery route using SEC Series/Class metadata;
3. build a full aggregate legacy Universe from independently discovered sources;
4. rerun Gate B overlap/rank/Top2 metrics;
5. only if Gate B passes, explicitly state `Universe reconstruction is confirmed` and implement the historical builder;
6. keep broad 2006–2018 Stage21 performance unopened until bridge rules are frozen.

## New-session protocol

When only the repository URL is provided:
1. read this file;
2. switch/read `docs/research/momentum-handoff-current.md` on `research/nq-npx-mapping-2006-20260903`;
3. read `docs/research/nq-npx-mapping-2006-20260903.md`;
4. do not revive the old nine-series sample, country-heading assumptions, fuzzy mapping, or missing-country=>US logic;
5. preserve frozen artifacts for apples-to-apples structural comparisons;
6. do not change Production parameters or tune reconstruction rules against older strategy returns.
