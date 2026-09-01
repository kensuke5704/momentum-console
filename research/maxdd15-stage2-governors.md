# MaxDD 15 — Stage 2 Risk Governors

The first screen showed that static 40% Fixed60 reaches MaxDD -13.57% with CAGR 23.02%, while 50% Fixed60 reaches -16.72% with CAGR 29.18%.

Stage 2 asks whether dynamic risk reduction can preserve more return without exceeding roughly 15% historical drawdown.

Two simple rules are fixed before testing:

1. `QQQ200 Regime Scaler`: use 100% of Fixed60 when QQQ close is above its 200-session SMA; use 40% of Fixed60 otherwise. The regime observed at today's close controls exposure to the next close-to-close Fixed60 return.
2. `Shadow-DD Scaler`: track the unmodified Fixed60 shadow NAV. If its drawdown at today's close is above -5%, next-day exposure is 100%; from -5% through -10%, exposure is 50%; at or below -10%, exposure is 25%. Residual is cash.

These are portfolio overlays only. Fixed60 mechanics are unchanged. No threshold tuning is allowed after viewing results.