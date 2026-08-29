# MaxDD + strategy-selection audit — 2026-08-29

Strategy: `momentum-dynamic-2026-08-v1`

Production remains unchanged. This file records the conclusions of Actions run `33227987100` plus the pre-freeze PR-history audit.

## 1. Standard global MaxDD re-audit

All values below recompute standard investment drawdown directly from the equity curve as global peak-to-trough drawdown. The legacy `backtest.stats.maxDrawdown` is retained only as an engine-episode diagnostic because the state-machine risk peak resets on recovery re-entry.

| Family | Variant | CAGR | Global MaxDD | Legacy episode DD | Global Calmar |
|---|---|---:|---:|---:|---:|
| baseline | Production | 55.25% | -31.53% | -21.93% | 1.75 |
| stop | 15.0% | 56.55% | -31.53% | -20.46% | 1.79 |
| stop | 20.0% | 53.04% | -34.32% | -26.90% | 1.55 |
| circuit | 12.5% | 52.74% | -31.17% | -19.17% | 1.69 |
| circuit | 17.5% | 58.44% | -32.45% | -22.50% | 1.80 |
| recovery | 5 days | 48.50% | -39.01% | -21.93% | 1.24 |
| recovery | 15 days | 42.73% | -39.92% | -24.10% | 1.07 |
| QQQ MA | 6M | 49.72% | -31.53% | -21.93% | 1.58 |
| QQQ MA | 8M | 49.72% | -31.53% | -21.93% | 1.58 |
| QQQ MA | 12M | 54.61% | -31.53% | -21.93% | 1.73 |
| momentum | 15/85 | 56.37% | -31.53% | -21.93% | 1.79 |
| momentum | 25/75 | 57.38% | -31.53% | -21.93% | 1.82 |

### What changes versus the old interpretation

- **Production risk:** standard MaxDD is `-31.53%`, not `-21.93%`.
- **Stop17.5:** still sits in a smooth neighborhood. The old claim that Stop15 had materially better DD was overstated; Stop15 and Production have the same global MaxDD in this sample.
- **Circuit15:** the old episode-DD table made Circuit12.5 look best on Calmar. With global DD, Circuit12.5 Calmar is `1.69`, below Production `1.75`. Circuit15 remains a reasonable middle risk/return choice.
- **Recovery10:** support becomes materially stronger. Recovery5 was previously shown with the same `-21.93%` DD as Production, but its true global DD is `-39.01%`. Recovery15 is `-39.92%`. Production Recovery10 therefore dominates both coarse alternatives on this historical sample in CAGR, global DD and global Calmar. Exact-10-day selection bias is still possible because this is same-history evidence.
- **QQQ MA and momentum weights:** local-plateau conclusions remain. The global DD is essentially unchanged across the tested nearby values, while CAGR changes smoothly.

The previously corrected 27-point parameter plateau and execution-robustness studies already use global equity-curve DD and remain valid under this definition.

## 2. Strategy-selection / multiple-testing audit

### Direct Git evidence before the current Dynamic Top2 freeze

The project history contains explicit optimization/search work before the current strategy was frozen:

- PR #2: temporary portfolio optimization and combined cap backtests.
- PR #3: combination backtest / robustness work.
- PR #5: a dedicated parameter-search script.
- PR #12: robustness search plus targeted TopN tests.
- PR #13: Production changed TopN `10 -> 9` and Momentum weights `20/40/40 -> 10/40/50` after that research sequence.
- PR #35: current strategy then migrated to a structurally different SEC N-PORT PIT Dynamic Universe, `0/20/80`, Top2, adaptive allocation and daily risk state machine.

PR #5 is especially important. Its retained script explicitly swept:

- TopN: 8 values (`5..12`)
- QQQ MA: 7 values (`7..13`)
- surge limit: 8 values
- Momentum weights: 35 unique 0.1-grid triples
- genre/frontier cap variants: 15 variants

It then selected values by best historical CAGR and Calmar and formed a second-stage combination search, with an upper-bound Cartesian candidate set of `3 x 3 x 3 x 5 x 5 = 675` before deduplication, followed by best-CAGR / best-Calmar finalists.

This establishes that the project history contains substantial data-driven strategy selection. Therefore the realized historical CAGR must not be treated as an unbiased estimate of future CAGR.

### Why the raw old search count is NOT the trial count for current Production

The large PR #5 / #12 searches were performed on the older fixed-Ticker strategy. The current Production introduced a different Universe construction, Top2 selection, 0/20/80 ranking, allocation logic and risk state machine in PR #35.

Consequently:

1. old trials demonstrate **project-level data reuse / research degrees of freedom**;
2. some design choices may carry over (e.g. Momentum philosophy, QQQ gate, surge concept);
3. but counting every old fixed-Ticker variant as an independent trial of the current Dynamic Top2 strategy would overstate current-strategy multiplicity;
4. post-freeze `research/*` robustness branches must not be charged as selection trials because they were created after Production was frozen and did not change Production.

The exact effective number of independent pre-selection trials for the current Production is therefore **not recoverable from Git alone**. Deleted branches, local work, chat-only experiments and the research process that led directly to PR #35 are not fully observable.

### Multiplicity sensitivity, not a fake correction

Using the current 80-month Production return history, the audit estimated the Newey-West (lag 3) standard error of mean monthly log return as `0.01111`. If one *hypothetically* assumes `N_eff` independent equal-noise candidate strategies and chooses the best, the expected best-noise uplift is:

| Effective independent trials | Expected best-noise z | Annual log-growth optimism | Equivalent growth multiplier |
|---:|---:|---:|---:|
| 2 | 0.59 | 7.86% | 1.08x |
| 5 | 1.18 | 15.74% | 1.17x |
| 10 | 1.55 | 20.63% | 1.23x |
| 25 | 1.96 | 26.20% | 1.30x |
| 50 | 2.24 | 29.92% | 1.35x |
| 100 | 2.50 | 33.33% | 1.40x |

This table is **not a corrected CAGR table**. The tested strategies are highly correlated, the real `N_eff` is unknown, and the current Production was not selected from a clean set of independent candidates. In particular, do not subtract these percentages mechanically from 55.25% CAGR.

## Final assessment

- **MaxDD reporting problem:** material and now quantified. Use `-31.53%` as Production standard historical MaxDD.
- **Parameter-point fragility:** still low-to-moderate after correction. The local plateau survives.
- **Recovery10 evidence:** stronger after correct MaxDD treatment, though exact-value selection bias remains.
- **Strategy-selection bias:** definitely present at project level and cannot be assumed negligible. Historical 55% should be treated as upward-biased as an expected-return estimate.
- **Magnitude of current-strategy selection bias:** not identifiable from Git history with defensible precision. An exact “corrected CAGR” would be false precision.
- **True resolution:** frozen Forward OOS after 2026-08-25 is the clean evidence that will eventually separate persistent edge from historical selection effects.
