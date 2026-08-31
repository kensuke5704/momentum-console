# Monthly return histogram UI adjustment — 2026-08-31

Scope: presentation/binning only. No strategy, backtest equity, or monthly-return calculation changes.

- Exact 0% monthly returns use one dedicated `0%` histogram bin.
- The adjacent bins are labeled `-5%–<0%` and `>0%–5%`, so zero cannot be counted in either side.
- Negative and positive bins otherwise remain 5 percentage points wide.
- On <=520px viewports, the monthly-return chart gets a 760px minimum chart width and horizontal scrolling rather than compressing or hiding x-axis labels.
- PC layout remains responsive at full card width.
- Regression tests assert one and only one `0%` bin and conservation of monthly observations.
