# Forward40 Alpha Stage 1 — Decision Freeze (2026-08-31)

## Status

Research only. Production/main is unchanged.

The objective of this stage was to find a non-leveraged, free-data improvement that could materially strengthen the evidence for an approximately 40% after-tax Forward CAGR target without reopening broad parameter optimization on the 2020–2026 sample.

## Important configuration correction

The research branch `src/lib/config.ts` still contains the older dynamic Production allocation (50/70), while main Production was frozen to Fixed60 on 2026-08-30.

Therefore Fixed60 transfer studies must **not** import branch-local `PRODUCTION_STRATEGY`. They now import `scripts/lib/fixed60-config.ts`, an explicit copy of main strategy `momentum-fixed60-2026-08-v1`.

Any run labelled Fixed60 that produced approximately 55.25% gross CAGR from branch-local `PRODUCTION_STRATEGY` is invalid as a Fixed60 comparison. Correct Fixed60 control is approximately 61.998% gross CAGR through 2026-08-25.

## Candidates rejected in this stage

### Tax-aware hysteresis

Old-Production diagnostic only. Full-sample H3 and TAX_H4 improved headline results, but pseudo-OOS transfer was inconsistent: both underperformed in 2023 and 2025 and improved in 2024 and 2026. This is insufficient transfer evidence, so no Fixed60 migration was performed.

### Consensus75 / price refinements

Consensus75, 52-week-high, intermediate momentum, trend consistency, horizon ensemble, Rank2 quality, semi-monthly refresh, no-churn and partial-rebalance variants failed their predeclared gates or did not provide a robust Forward improvement.

### Early-Leader independent engine

Authoritative Fixed60 run: GitHub Actions run `33366751202`.

Fixed60 gross CAGR: 61.998%, MaxDD -31.13%.

Best standalone Early-Leader variant (`EL63_2`) gross CAGR: 38.62%, MaxDD -41.08%, daily-return correlation to Fixed60 about 0.394.

25% Early-Leader blend: CAGR 57.77%, MaxDD -27.57%.

Conclusion: useful diversification characteristics, but materially lowers CAGR. Reject as a return-enhancing Forward40 alpha engine. It may be reconsidered only for a separate lower-risk portfolio objective.

### Residual Momentum

Authoritative Fixed60 run: GitHub Actions run `33366934142`.

Fixed60: CAGR 61.998%, MaxDD -31.13%.

R25: CAGR 63.53%, MaxDD -27.20%, correlation to Fixed60 about 0.892.

R50: CAGR 61.13%, MaxDD -25.22%, correlation about 0.848.

R25's full-sample headline improvement did not transfer across calendar years: it lagged Fixed60 in 2020, 2021, 2023, 2024 and 2026 and improved materially only in 2025. Training-only Calmar selection stayed with BASE through 2025; when it selected R50 for 2026, R50 returned about 55.61% versus Fixed60 about 74.43%.

Conclusion: reject. Full-sample improvement is not supported by transfer behavior.

### Risk-Off Macro sleeve

Authoritative Fixed60 run: GitHub Actions run `33367176074`.

Rule: during monthly Fixed60 Risk-Off, hold the strongest positive 63-session return among GLD / IEF / UUP / DBC; otherwise cash.

2020–2026 gross result: Fixed60 61.998% CAGR versus Macro3 71.37%, but MaxDD worsened from -31.13% to -34.73%.

The apparent edge was fragile: retaining only 75% of positive macro-sleeve returns reduced CAGR to about 60.15%, below Fixed60.

Pre-2020 structural falsification (run `33367336672`) rejected transferability of the same 3M rule:

- 2008–2012 CAGR: -6.40%
- 2013–2019 CAGR: -0.72%
- 2020–2026 CAGR: +5.78%
- Full 2008–2026 standalone sleeve CAGR: about +0.27%

Conclusion: the positive Risk-Off macro contribution is concentrated in the recent observed sample and is not robust across earlier regimes. Reject before tax modeling.

## Stage decision

No candidate in this stage provides sufficiently robust evidence to replace or augment Fixed60 for the Forward40 objective.

Further mining of the same 2020–2026 sample should stop. Additional threshold searches, post-hoc inversion of failed factors, or renamed variants of previously rejected N-PORT / SEC / price factors would increase selection bias without adding independent evidence.

## Next evidence source

The primary next evidence is **True Forward OOS under the frozen Fixed60 rule** beginning with the 2026-08-31 signal close and first eligible execution at the next US open.

Historical Fixed60 results remain a retrospective diagnostic, not a calibrated Forward forecast. The approximately 40% after-tax Forward figure remains an objective / scenario target until genuine forward observations accumulate.
