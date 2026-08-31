# Fixed60 Production / Backtest parity audit — 2026-09-01

## Objective
Verify that the live Production decision path and the historical/backtest decision path implement the same frozen Fixed60 contract, without using this audit to tune parameters.

## Frozen contract
- strategyId: `momentum-fixed60-2026-08-v1`
- PIT SEC N-PORT breadth universe, size 80
- momentum weights 0/20/80
- 1M surge exclusion at +80%
- require stock momentum score above QQQ score
- Top2 selection
- Fixed 60/40 target weights
- QQQ monthly 10M MA market gate
- individual stop 17.5%
- portfolio circuit 15%
- recovery: QQQ 100DMA, 20D momentum, 10 consecutive closes
- close confirmation -> next US open execution
- one-way transaction cost 10bp

## Audit dimensions
1. Configuration parity: Production config, backtest config, scripts and snapshots must identify the same Fixed60 strategy.
2. Universe parity: identical PIT as-of and filing admissibility rules for a given signal date.
3. Signal parity: identical candidate eligibility, ranks, Top2 and 60/40 weights.
4. Market-state parity: identical QQQ monthly gate and persistent lock behavior.
5. Risk-state parity: identical Stop, Circuit and Recovery transitions.
6. Execution parity: no same-close fills; identical next-session-open dates and cost treatment.
7. OOS isolation: no pre-freeze signal is admitted to Fixed60 True Forward OOS.
8. Display parity: dashboard labels and action instructions must not imply a different strategy or tax treatment than the underlying data.

## Decision rule
Any mismatch in items 1–7 is a blocking defect and must be corrected before interpreting True Forward OOS. Item 8 is a presentation defect unless it changes the user's action.

This audit is implementation verification only. It does not alter strategy parameters or invalidate the frozen OOS start date.
