# Forward Evidence Ledger — 2026-08-30

## Purpose

This ledger separates historical backtest improvements from evidence that can reasonably change the Forward planning view. It is research-only. Production/main remains unchanged.

The pre-existing Production Forward planning center was approximately 25%. That number is a subjective planning judgment, not a calibrated posterior mean. Historical CAGR must not be inserted directly into Forward expectations.

The project target is approximately 40% after-tax Forward CAGR. Prior planning work indicated that this would likely require roughly 50% gross Forward CAGR.

## Candidate evidence

### Fixed60 allocation

Historical Production-aligned Fixed60 results:

- Gross CAGR: ~61.998%.
- Gross MaxDD: ~-31.13%.
- After-tax approximation: ~50.647% CAGR.
- Historical gross increment versus Production: ~+6.75 percentage points.

Direct next-calendar-year pseudo-OOS transferability versus Production was weak. The training-Calmar selected allocation rule produced wins 2, tie 1, losses 2; median after-tax increment 0 and mean increment about -3.12 points. Fixed60 also materially lagged Production in 2024 and 2026 partial.

**Forward credit: none automatically.** Fixed60 remains a research/shadow candidate, but its full-sample historical increment is not treated as transferable until post-freeze observations accumulate.

### Recovery QQQ50 K1 bridge

Historical W70 comparison:

- W70 gross CAGR ~58.97%.
- W70 + QQQ50 K1 bridge gross CAGR ~62.11%.
- W70 after-tax ~48.18%.
- W70 + bridge after-tax ~50.77%.

The historical after-tax increment is about +2.59 points, but K1 timing sensitivity is material and K3/K5 do not preserve the improvement. 2022 bridge behavior was also adverse relative to cash.

Run `33307173895` integrated the exact Recovery bridge lifecycle with Production-momentum Fixed60, cash carry, the same tax approximation, and K1/K3/K5 timing falsification. At 50% of historical BIL carry:

- Fixed60 without bridge: after-tax CAGR ~51.434%.
- Fixed60 + K1 bridge: after-tax CAGR ~53.409%.
- Fixed60 + K3 bridge: after-tax CAGR ~50.419%.
- Fixed60 + K5 bridge: after-tax CAGR ~49.619%.

At 100% of historical BIL carry:

- Fixed60 without bridge: after-tax CAGR ~52.227%.
- K1: ~54.040%.
- K3: ~51.083%.
- K5: ~50.306%.

The K1 advantage therefore remains strongly timing-dependent; cash carry does not cure the K1/K3/K5 instability. In 2022, K1 remained negative even with carry: approximately -3.79% after tax at 50% carry and -3.33% at 100% carry, while Fixed60 cash carry without bridge was positive.

**Forward credit: heavily discounted / unproven.** The bridge has a frozen True Forward operating specification, but historical improvement is not added mechanically to the Forward center. Cash carry on the bridge's unused 50% is economically sensible if the bridge is operated, but it does not validate K1 itself.

### Cash carry on idle strategy cash

Run `33306949835` applied BIL adjusted total return only to the actual cash balance of Production-momentum Fixed60, without changing security selection, timing, risk thresholds, or exposure limits.

Historical gross:

- 0% cash carry: CAGR ~61.998%, MaxDD ~-31.127%.
- Historical BIL carry: CAGR ~64.084%, MaxDD ~-30.851%.
- Gross CAGR increment: ~+2.086 points.

The increment was positive in every reported calendar slice from 2022 through 2026 partial.

Run `33307069862` added a simplified 20.315% tax approximation and a predeclared rate-level stress:

- 0% of historical BIL carry: after-tax CAGR ~50.647%.
- 50% of historical BIL carry: after-tax CAGR ~51.434–51.454% depending on the independent rerun implementation, increment about +0.79–0.81 points.
- 100% of historical BIL carry: after-tax CAGR ~52.227–52.267%, increment about +1.58–1.62 points.

The independent integrated rerun reproduces the no-carry baseline exactly and the carry result to within implementation-level cash-income timing differences, supporting the conclusion that the effect is not an artifact of one script.

The cash-income tax model is intentionally simplified and does not model US withholding, Japanese account type, distribution timing, tax lots, or broker-specific money-market mechanics.

**Forward credit: positive but small and rate-dependent.** Unlike the rejected alpha factors, this is primarily a correction of the zero-return cash assumption. A reasonable planning treatment is to credit only a fraction of the historical increment, with 50% historical-rate stress as a more conservative reference than the full-history rate path. It is not sufficient to close the gap to the 40% after-tax Forward target.

## Rejected or blocked independent alpha paths

The following were tested under diagnostic-first or fixed-rule procedures and did not establish stable early/late or long-history evidence: Overnight Momentum, Information Gap, fixed regime entry gate, nonleveraged dynamic exposure, N-PORT institutional persistence, Fundamental SALES_ACCEL rerank, MARGIN_DELTA, SEC post-filing drift, Form 4 insider cluster buying, FINRA short-sale volume, fresh Schedule 13D, Form 424B5 issuance events, simple GLD/IEF defensive sleeves, and a predeclared GLD/DBC/IEF/BIL cross-asset Risk-Off sleeve.

SEC 13F accumulation was not rejected on signal quality; it is blocked because the available free research mirror does not retain reliable historical `filed_at` before late 2024, preventing a 2020–2023 PIT test.

## Residual Forward gap

The existing ~25% Forward planning center is a judgmental center, not an estimate that can be arithmetically updated. Still, the scale of the gap is informative:

- Target after-tax Forward CAGR: ~40%.
- Prior planning center: ~25%.
- Gap: ~15 percentage points.
- The most defensible new operational effect, cash carry, contributes only about +0.8 points historically under the 50%-rate stress after tax.
- Fixed60's historical allocation increment receives no automatic Forward credit because direct transferability evidence is weak.
- Recovery K1 receives no automatic Forward credit because K3/K5 timing perturbations erase or reverse its advantage.

Thus the evidence added on 2026-08-30 does not materially close the ~15-point planning gap. If one chooses to recognize some cash-carry benefit in planning, a center in roughly the **25–26%** area is more defensible than a jump toward 40%, but this range remains a planning judgment, not a fitted expected-return model.

## Current Forward conclusion

The 40% after-tax Forward target is **not evidence-supported yet**.

Fixed60 improves historical results but lacks direct transferability evidence. Recovery K1 adds historical performance but is timing-fragile. Cash carry is a credible operational enhancement and survives tax/rate stress, but its plausible Forward contribution is only on the order of a small number of percentage points, not the roughly 15-point gap from the existing ~25% planning center.

Further work should not reopen local allocation weights, momentum weights, Stop/Circuit/Recovery thresholds, SEC form variants, or rejected factor inversions merely to force the target. The next admissible work is either (a) operational implementation/shadow validation of cash carry and the frozen bridge, or (b) a genuinely independent, free-PIT alpha source with a predeclared hypothesis and sufficient historical coverage.
