# Momentum Research Audit — 2026-08-25

Status vocabulary:
- **VALID** — may be used as a primary reported result for the stated question.
- **DIAGNOSTIC ONLY** — mechanically useful, but not a calibrated estimate of Production forward CAGR.
- **INVALIDATED** — superseded or discarded because of implementation/design defects.

## Current Production reference

Strategy ID: `momentum-dynamic-2026-08-v1`

Production config on `main`:
- Universe: SEC N-PORT breadth Top80, PIT
- Momentum: 1M=0, 3M=20%, 6M=80%
- TopN=2
- Allocation: 50/50, conditionally 70/30 at z-gap >= 0.25
- QQQ 10M MA market gate
- Individual stop: -17.5%
- Portfolio circuit: -15%
- Recovery: QQQ > 100DMA, QQQ 20D momentum > 0, 10 consecutive closes
- Execution: next-session open, 10bp/side

Primary historical reference:
- CAGR: **55.3601%**
- MaxDD: **-21.9290%**
- Final wealth: **18.5913x**
- Period: 2020-01-02 to 2026-08-21

## Experiment registry

| Experiment | Status | Key result | What it can answer | Main caveat |
|---|---|---:|---|---|
| Production historical backtest | **VALID** | CAGR 55.36%, MaxDD -21.93% | What happened on the realized 2020–2026 path | Not a forward expectation |
| Distributional return bootstrap, 50k paths | **DIAGNOSTIC ONLY** | Median CAGR 55.73% | Sampling uncertainty of the already-realized strategy return stream | Does not re-run selection/risk state machine |
| Structural MC v1, shuffled source chronology | **DIAGNOSTIC ONLY** | Median CAGR ~7–8% | Stress sensitivity when market/Universe chronology is disrupted | Destroys time-directional information; not a Production expected CAGR |
| Structural MC Ablation V1 | **INVALIDATED** | — | None | Incorrect no-gate implementation using 1M MA |
| Structural MC Ablation V2 | **INVALIDATED** | — | None | Same-day execution after close signal introduced look-ahead |
| Structural MC Ablation V3, 100 common paths | **DIAGNOSTIC ONLY** | Full Production median CAGR 7.71%, median DD -46.16% | Coarse relative rule sensitivity | A–E simplified engine; chronology-shuffled stress model; only 100 paths |
| Chronology-Preserving Conditional MC (CPCM), 100 paths | **SUPERSEDED** | Median CAGR 31.33% | Early CPCM validation | Too few paths; upward sampling noise |
| CPCM, 500 paths | **VALID** | Median CAGR 26.37% | Robustness of Production under chronology-preserving conditional resampling | Model-dependent; not calibrated future probability |
| CPCM, 1,000 paths | **VALID** | Median CAGR **26.04%**, p05 -4.26%, p95 71.13%, median DD -41.33% | Primary counterfactual robustness distribution | Depends on donor-window/regime/block assumptions |
| CPCM Recovery 5d, 3 seeds × 1,000 paths | **VALID research comparison** | Median CAGR ~31.13% vs ~25.91% baseline average | Whether shorter recovery helps across CPCM seeds | Conflicts with realized chronology; do not adopt from MC alone |
| Allocation scan + 3 seeds × 1,000 | **VALID research comparison** | Adaptive 50/70 retained; equal 50/50 lowers CAGR ~1pt but improves median DD ~2pt | Allocation robustness | Research comparison, not forward CAGR calibration |
| Rank persistence Top3/4/5, 300 paths | **DIAGNOSTIC ONLY** | All buffers lower median CAGR vs Top2 | Whether turnover buffer is promising | 300-path coarse screen only |
| Momentum quality IC diagnostic | **VALID diagnostic** | Baseline momentum IC +0.147; added quality features unstable / insignificant | Whether extra ranking features have stable predictive evidence | 78 months; observational, not a full strategy backtest |
| Alpha-loss decomposition, official-stat aligned | **VALID** | Production 55.36/-21.93 exactly reproduced; no-stop 45.63%; no-circuit 54.96%; no-gate 64.47%; Recovery5 49.03% | Actual-chronology one-rule-off opportunity cost | Counterfactual deltas are non-additive |
| Alpha-loss initial run without full warmup | **INVALIDATED** | — | None | Truncated pre-start history changed Momentum/10M MA initialization |
| Alpha-loss intermediate DD calculation | **INVALIDATED** | — | None | DD recomputed differently from official `state.drawdown` |
| Market Gate initial crisis run | **INVALIDATED** | — | None | Repo QQQ history began 2018 and crisis warmup was lost |
| Market Gate long-history crisis study | **VALID diagnostic** | Gate materially reduces Dot-com/GFC/2022 QQQ drawdowns | Gate's defensive role in long bear markets | QQQ-only overlay before 2020; not full Dynamic Universe strategy |
| Market Gate QQQ-only structural MC | **DIAGNOSTIC ONLY** | Production gate median CAGR ~5.21% | Relative gate trade-off on QQQ synthetic paths | **Must never be called Production CPCM CAGR** |

## Authoritative numbers to use going forward

### 1. Realized historical Production
- CAGR: **55.36%**
- MaxDD: **-21.93%**

### 2. Primary structural robustness estimate
Use **CPCM 1,000-path Production baseline**:
- Median 5Y CAGR: **26.04%**
- CAGR p05: **-4.26%**
- CAGR p95: **71.13%**
- P(CAGR >= 50%): **18.7%**
- P(CAGR < 0): **7.9%**
- Median MaxDD: **-41.33%**
- Adverse p05 MaxDD: **-61.67%**
- Median 5Y final wealth: **3.18x**
- Median individual-stop count: **4**
- Median portfolio-circuit count: **7**
- Median cash share: **58.06%**

### 3. Results that must not be mixed with the primary CPCM number
- ~7–8% median CAGR = chronology-shuffled Structural MC stress result.
- ~5.2% median CAGR = QQQ-only Market Gate structural diagnostic.
- ~31% median CAGR = Recovery 5-day research variant, **not current Production**.

## Current research decisions

- Keep Production Universe / Top2 / 0-20-80 momentum unchanged.
- Keep conditional 50/70 allocation.
- Keep -17.5% individual stop for now.
- Keep -15% portfolio circuit.
- Keep QQQ 10M market gate.
- Keep Recovery 10 days in Production.
- Do **not** adopt Recovery 5 days despite CPCM improvement, because realized chronology deteriorated from 55.36% to 49.03%.
- Do not adopt rank-persistence or additional momentum-quality features.
- Do not tune parameters to target a specific MC median such as 50%.

## Provenance / notable workflow runs

- Distributional MC 50k: run `32793602056` — success.
- Structural MC v1 500: run `32794229954` — success.
- Structural Ablation V3: run `32798558220` — success.
- CPCM robustness / Recovery 5d multi-seed research: latest workflow family on `research/structural-monte-carlo-20260825`; run `32809796118` completed successfully for the fixed-seed validation series.
- Alpha-loss official-stat-aligned: run `32819477915` — success.
- Market Gate corrected long-history study: run `32826709074` — success.

## Interpretation rule

No future report should use the phrase **"current median CAGR"** without naming the experiment. Preferred wording:
- "Production historical CAGR: 55.36%"
- "Production CPCM 1,000-path median CAGR: 26.04%"
- "Recovery-5d CPCM median CAGR: ~31%"
- "QQQ-only gate diagnostic median CAGR: ~5.2%"

This naming convention is mandatory for avoiding cross-experiment confusion.
