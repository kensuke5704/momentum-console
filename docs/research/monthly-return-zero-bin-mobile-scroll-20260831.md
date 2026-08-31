# Monthly return histogram UI adjustment — 2026-08-31

Scope: presentation/binning only. No strategy, backtest equity, or monthly-return calculation changes.

- Exact 0% monthly returns use one dedicated `0%` histogram bin.
- Negative 5-point bins exclude zero; positive 5-point bins exclude zero.
- On <=520px viewports, the monthly-return chart gets a fixed minimum chart width and horizontal scrolling rather than compressing x-axis labels.
- PC layout remains responsive at full card width.
