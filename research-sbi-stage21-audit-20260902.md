# SBI Stage21 rounded v1 — post-freeze audit 2026-09-02

Production Fixed60 remains unchanged. This audit evaluates the frozen research candidate `research-sbi-stage21-rounded-v1`; it does not authorize Production changes or strategy retuning.

## 1. CFTC point-in-time availability audit

The initial historical implementation used a conservative seven-calendar-day lag from the CFTC report date. Normally this is conservative because COT/TFF data are generally positions as of Tuesday and are released Friday at 3:30 p.m. ET.

A material historical exception exists in late 2025: publication was interrupted by the federal appropriations lapse. Several report dates were not actually published until weeks later. Historical CFTC datasets identify the report date, not a complete historical release timestamp, so a fixed report-date lag can accidentally use data before it was actually public during this special period.

The audit therefore applied actual CFTC catch-up publication dates for the affected 2025 reports while retaining the existing seven-day lag rule. No strategy threshold, weight, participant class, or lookback was changed.

### Result

| Metric | Original report-date lag | Release-aware PIT |
|---|---:|---:|
| Historical CAGR | 49.3440% | **48.6072%** |
| Historical MaxDD | -16.8860% | **-16.8860%** |
| Annualized volatility | 25.4452% | **25.1960%** |
| Final equity | 14.3693x | **13.9048x** |
| 30bp-cost stress CAGR | 47.8176% | **47.1151%** |
| +1 lag CAGR | 47.3586% | **46.9589%** |
| +2 lag CAGR | 47.6861% | **47.2537%** |
| Start-2021 CAGR | 44.2329% | **43.3946%** |
| Stress median | 47.5224% | **47.0370%** |
| Rolling-36M median | 43.6573% | **43.6573%** |
| Planning proxy | 43.6573% | **43.6573%** |
| Combined 40% / 17% gate | PASS | **PASS** |

Interpretation:
- The initial implementation did contain a genuine PIT issue for the abnormal 2025 publication backlog.
- Correcting it reduces full-sample CAGR by about 0.74 percentage point.
- It does **not** alter historical MaxDD or the planning proxy, because the binding planning statistic remains rolling-36M median CAGR.
- The frozen candidate continues to pass both research gates after the correction.
- Historical evaluation should use the release-aware result from this audit going forward.

## 2. Drawdown episode decomposition

The rounded candidate's largest historical drawdown episodes were decomposed into state timing and recovery behavior.

| Peak | Trough | Recovery | MaxDD | First Yellow | First Deep |
|---|---|---|---:|---|---|
| 2020-09-01 | 2020-10-30 | 2020-12-18 | **-16.89%** | 2020-09-16 | 2020-10-22 |
| 2021-11-18 | 2023-03-07 | 2023-05-18 | **-16.68%** | 2022-01-11* | 2021-12-08 |
| 2021-02-11 | 2021-05-12 | 2021-08-03 | **-14.72%** | 2021-02-11 | 2021-03-10 |
| 2024-06-18 | 2024-07-25 | 2024-11-05 | **-13.90%** | 2024-06-20 | none |
| 2020-02-19 | 2020-03-19 | 2020-06-01 | **-13.45%** | 2020-02-19 | 2020-03-03 |
| 2026-03-02 | 2026-06-10 | 2026-06-15 | **-12.66%** | 2026-03-02 | 2026-05-19 |
| 2024-12-24 | 2025-02-28 | 2025-07-10 | **-11.75%** | 2024-12-26 | 2025-01-23 |

`*` The episode already entered DEEP before the first later Yellow observation; Deep has priority over Yellow.

Key diagnosis:
- CFTC Yellow typically acts before M3 Deep in abrupt risk deterioration, but not in every episode.
- M3 is still the primary deep-tail defense, consistent with the earlier ablation test.
- The 2024-06 episode never entered Deep; Yellow alone was used while MaxDD stayed around -13.9%.
- The global MaxDD remains the 2020 Sep-Oct episode, where Yellow began about two weeks after the peak and Deep much later on 2020-10-22. This remains the main historical weakness of the risk-state architecture.

## 3. State and turnover diagnostics

Initial diagnostic run over 2020-2026 showed approximately:
- NORMAL: 695 sessions (~41.6%)
- YELLOW: 699 sessions (~41.9%)
- DEEP: 276 sessions (~16.5%)
- state transitions: 100
- total portfolio turnover: ~34.1x capital over the sample
- annualized turnover: ~5.13x
- rebalance/trade days with nonzero turnover: 177

These figures were produced before applying the special late-2025 release-date override, so they are diagnostic rather than the final operational accounting for the backlog period. The important structural conclusion is unchanged: **Yellow is not a rare crash-only state. It is a frequently active regime filter.**

This matters for True Forward OOS monitoring: state parity, CFTC data timing, turnover, and execution cost should be monitored as first-class metrics, not only CAGR and MaxDD.

## 4. Contiguous rolling-window joint robustness

Chronology was preserved. No bootstrap or chronology-breaking simulation was used. For every contiguous 24M / 30M / 36M / 48M window, CAGR and MaxDD were evaluated jointly using the release-aware historical implementation.

| Window | Both gates pass | CAGR median | CAGR P10 | Worst CAGR | MaxDD gate pass |
|---|---:|---:|---:|---:|---:|
| 24M | **62.7%** | 47.62% | 26.82% | 11.52% | **100%** |
| 30M | **63.2%** | 48.43% | 29.65% | 18.43% | **100%** |
| 36M | **74.7%** | 44.18% | 35.19% | 23.42% | **100%** |
| 48M | **89.7%** | 47.83% | 39.82% | 32.12% | **100%** |

The pass-both share equals the return-gate share in these windows because every tested contiguous window stayed within the -17% MaxDD gate.

Important interpretation:
- The low-drawdown property is historically much more stable than the 40% CAGR property.
- A 43.66% planning proxy must **not** be interpreted as "CAGR should remain above 40% in every two- or three-year period."
- In the historical sample, roughly one quarter of 36-month windows and about one third of 24-30M windows were below 40% CAGR.
- The worst 36M CAGR was about 23.4%; the worst 48M CAGR was about 32.1%.
- Therefore a future 2-3 year CAGR materially below 40% would not by itself falsify the architecture if drawdown/state/execution behavior remained consistent with its historical envelope.

## 5. Updated research interpretation

After plateau, implementation, later-start, ablation, drawdown, PIT, and rolling-window audits, the most defensible same-sample description is:

- Release-aware historical CAGR: **~48.6%**.
- Historical MaxDD: **~16.9%**.
- Planning proxy: **~43.7%**, but this is a robustness statistic, not an expected-return estimator.
- 36M historical return distribution is wide: median ~44.2%, P10 ~35.2%, worst ~23.4%.
- Low historical DD is more stable than the 40% return threshold across contiguous windows.
- M3 is the primary deep-risk control; CFTC adds anticipatory de-risking; GLDM preserves return density while diversifying funded exposure.
- CFTC publication availability must be tracked by **actual availability**, not report date alone, whenever publication schedules are abnormal.

## 6. Governance

Do not use these audit findings to retune:
- CFTC lookback, magnitude threshold, or participant class,
- M3 thresholds or recovery rules,
- NORMAL/YELLOW/DEEP weights,
- GLDM allocation,
- G shadow-core weight,
- execution lag or cost assumptions.

The audit is intended to discover flaws and characterize the frozen candidate, not to reopen same-sample optimization.

The next highest-value evidence is True Forward / paper OOS with explicit logging of actual CFTC publication availability and state transitions.
