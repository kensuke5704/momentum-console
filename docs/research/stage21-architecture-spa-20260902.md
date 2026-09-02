# Stage21 Architecture-Level SPA — 2026-09-02

対象: `momentum-stage21-sbi-2026-09-v1` / Stage21 rounded v1

## Purpose

Stage21の局所配分・ablation 32候補に対するSPAではQQQ比のselected family-wise p値が5%未満だった。一方、Stage21は2020–2026の同一標本上で多数の異なるarchitectureを検討した後に選ばれている。このarchitecture-selection biasをより広い候補集合で評価する。

## Candidate reconstruction

Research branch `research/cagr40-new-alpha-20260901` に残る `scripts/cagr40-*.ts` を再実行し、各スクリプトが `performanceStats()` に直接渡した全期間equity curveを一時captureした。

- Productionコードは変更していない。
- `src/lib/backtest.ts` へのcapture hookはGitHub Actions workspace内だけで適用。
- 同一の日次return seriesはSHA-256 signatureで重複除去。
- 対象期間: 2020-01-01〜2026-08-25
- 共通日数: 1,669 trading days
- raw `performanceStats()` calls: 492
- full-period eligible calls: 408
- unique full-period curves: **333**
- architecture script executions: 38
- successful: **36**
- failed/non-reproduced: **2**
  - `cagr40-sec-fundamental-stage6`: exit 1
  - `cagr40-putcall-stage17`: timeout (exit 124)

333候補には、成功した各research script内で実際に評価されたfull-period stress/variant curvesも含める。このため、最終採用候補だけを集めるより保守的な多重比較補正である。

## Method

- Hansen SPA-style consistent recentering
- stationary bootstrap
- shared bootstrap indices across candidates, preserving cross-model dependence
- HAC(10) studentization
- bootstrap repetitions: 5,000
- mean block lengths: 5 / 10 / 20 trading days
- benchmark: QQQ
- selected Stage21はfrozen reference statsとの距離0で正確に同定

Frozen Stage21 reproduction:

- CAGR: **48.6072%**
- MaxDD: **-16.8860%**
- annualized volatility: **25.1960%**
- final equity: **13.9048x**

## Architecture-level SPA result vs QQQ

| Mean block length | Family SPA p-value | Stage21 selected family-wise p-value | Stage21 t-stat |
|---:|---:|---:|---:|
| 5 | **0.1758** | **0.3455** | 2.0295 |
| 10 | **0.1608** | **0.3227** | 2.0295 |
| 20 | **0.1422** | **0.3127** | 2.0295 |

At conventional 5% significance, neither the complete captured family nor selected Stage21 rejects the null of no superior expected return over QQQ after architecture-level multiplicity adjustment.

The maximum test statistic in the captured family was 2.4039. The associated captured curve came from `cagr40-asymmetric-tqqq-btal-stage8` and reproduced the Fixed60-like raw-return profile:

- CAGR: **61.9981%**
- MaxDD: **-31.1272%**
- annualized volatility: **34.5776%**
- final equity: **24.6686x**

This reinforces that a raw-return SPA objective tends to favor less-defensive, higher-drawdown variants. It does not imply that such a variant satisfies the Stage21 risk objective.

## Interpretation

The earlier local 32-model SPA result remains valid for its stated scope: Stage21's QQQ excess return survived multiplicity adjustment across nearby allocation choices and major ablations.

However, once the candidate family is expanded to the broad historical architecture search, the Stage21 selected family-wise p-value rises to approximately **0.31–0.35**. Therefore the historical sample does **not** provide statistically significant evidence that Stage21's QQQ excess mean return is independent of the broader architecture-selection process.

Updated overfitting assessment:

- exact-parameter/local overfit risk: **low**
- local allocation/ablation data-snooping risk: **low**
- architecture-selection bias: **meaningful / medium-to-high**
- historical QQQ alpha after broad snooping correction: **not statistically established**
- True Forward evidence: **still required and decisive**

This does not invalidate Stage21's observed historical risk/return profile, plateau robustness, cost/lag stress, PIT correction, ablation evidence, or MaxDD reduction. It changes the interpretation of the 48.61% historical CAGR: it must not be treated as independently validated expected alpha after accounting for the broad research search.

## Limitations

1. Two historical scripts did not reproduce in the automated architecture capture. Their omission means this is not mathematically exhaustive over every experiment ever run.
2. Capturing every full-period curve passed to `performanceStats()` can include stress and intermediate variants, making the multiplicity correction deliberately conservative.
3. SPA here tests mean return superiority versus QQQ. Stage21 was designed around a joint return/drawdown objective; SPA does not directly test superiority on Calmar, utility, or a constrained MaxDD objective.
4. A risk-adjusted or constrained performance statistic would answer a different question and should be preregistered before testing to avoid introducing another same-sample optimization layer.

## Governance conclusion

No Stage21 parameter or architecture change is justified by this result. The frozen strategy and True Forward OOS clock remain unchanged.

The correct conclusion is not "Stage21 failed"; it is that broad same-sample architecture search removes statistical confidence in its historical QQQ mean-return alpha. Forward OOS is therefore the primary remaining validation mechanism.

## Reproduction

- branch: `research/cagr40-new-alpha-20260901`
- GitHub Actions run: **33597997508**
- analyzer commit: `fbafbbfc3d9fd351220572770eac34008eb9c4c6`
- workflow: `.github/workflows/research-architecture-spa.yml`
- analyzer: `scripts/architecture-spa-analyze.mjs`
