# CPCM Recovery Gap Attribution — 2026-08-25

Run: `32856437642` (success)

Design:
- Same 5-year evaluation horizon for Historical and CPCM.
- CPCM baseline generator: BLOCK20 / RADIUS126 / actual-target conditioning / seed 20260825.
- 200 CPCM paths.
- Full Production state machine.
- Compare Production Recovery10 vs Recovery5 on the same price path.
- Attribute only days when Recovery5 is invested while Production is still cash.

## Historical 5-year attribution

- Exclusive Recovery5 exposure days: **68**
- Mean daily return on those days: **-0.1777%**
- Median daily return: **-0.1830%**
- Positive-day rate: **48.53%**
- Cumulative log contribution of exclusive days: **-16.64%**
- Paired CAGR difference, Recovery5 - Production: **-4.61pt** on this common 5-year evaluation window.

By prior Production trigger:

| Trigger | Exclusive days | Mean daily return | Log contribution |
|---|---:|---:|---:|
| Market | 15 | +1.4075% | +20.13% |
| Stop | 25 | -0.5142% | -14.69% |
| Circuit | 28 | -0.7265% | -22.09% |

Historical faster recovery was beneficial after Market exits, but harmful after Stop and Circuit exits. Stop + Circuit dominate the total negative result.

## CPCM 200-path attribution

- Exclusive Recovery5 exposure days: p05 **64.0**, median **105.5**, p95 **176.1**.
- Mean daily return on exclusive days: p05 **-0.2845%**, median **+0.2087%**, p95 **+0.7832%**.
- Exclusive-day cumulative log contribution: p05 **-34.03%**, median **+15.14%**, p95 **+81.79%**.
- Paired CAGR difference, Recovery5 - Production: p05 **-9.27pt**, median **+4.93pt**, p95 **+24.06pt**.
- Recovery5 paired win rate: **68.5%**.

Median trigger attribution across CPCM paths:

| Trigger | Median exclusive days | Median log contribution |
|---|---:|---:|
| Market | 28.0 | +0.84% |
| Stop | 27.5 | +5.95% |
| Circuit | 45.0 | +8.36% |

The major Historical-vs-CPCM disagreement is therefore not Market recovery. It is the sign of returns earned during early re-entry after **Stop and Circuit** events: negative in Historical, positive at the CPCM median.

## Block-boundary test

Among CPCM exclusive Recovery5 days, the share falling in the first 5 days of a 20-day donor block was:
- p05 **15.5%**
- median **24.7%**
- p95 **34.4%**

A mechanically uniform distribution across a 20-day block would place 25% of days in the first 5 days. The observed median is essentially that benchmark. This does **not** support the hypothesis that Recovery5's CPCM advantage is mainly a donor-block boundary artifact.

## Interpretation

1. The CPCM-vs-Historical Recovery disagreement is real and survives a direct exposure attribution.
2. Block-boundary concentration is not the primary explanation.
3. CPCM systematically makes the first five eligible post-Stop / post-Circuit recovery days more favorable than the realized historical path did.
4. Therefore the next model-validity question is whether CPCM preserves the conditional path shape around endogenous risk triggers. Matching unconditional QQQ return/volatility statistics is insufficient.
5. The next audit should compare event windows around Stop/Circuit triggers: pre-trigger drawdown, trigger-day shock, days +1..+5, days +6..+10, and selected-portfolio returns, Historical vs CPCM.

Status: **VALID DIAGNOSTIC RESULT**. This does not justify changing Production Recovery10.