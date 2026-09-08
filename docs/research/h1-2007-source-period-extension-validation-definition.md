# H1 2007 Source Period-Extension Validation Definition

Defined: 2026-09-08 JST, before the H1-2007 strict Series-source result is executed.

This is a period-extension validation, not a new named gate, and does not authorize Stage21 performance analysis.

## Fixed signal dates

- 2007-01-31
- 2007-02-28
- 2007-03-30
- 2007-04-30
- 2007-05-31
- 2007-06-29

## PASS requirements

- The cumulative N-Q inventory through 2007-06-29, restricted to `dateFiled <= 2006-12-29`, exactly reproduces artifact `10025455602` rows.
- The cumulative complete-portfolio inventory through 2007-06-29, restricted to `dateFiled <= 2006-12-29`, exactly reproduces artifact `10025472099` rows.
- Every candidate CIK in authoritative H2-2006 prefilter artifact `10038188212` remains in the H1-2007 candidate pool. Carry-forward is allowed only at the candidate-prefilter layer.
- Final Series acceptance is independently re-established with the unchanged issuer-own operational evidence and structural binding rules.
- Series-ID mandatory boundary remains 2006-02-06.
- Complete-portfolio forms, amendment handling, issuer-own operational grammar, and structural binding semantics remain unchanged.
- No trust-global sibling inheritance, fuzzy identity, ticker inference, holdings/rank/return/outcome inference, or strategy data is used.
- H2-2006 positive Series identity and binding from artifact `10038284691` remain exact.
- All six authoritative 2006 Jul-Dec `sourceFilings` snapshots from artifact `10038284691` are reproduced exactly from the cumulative H1-2007 strict catalog.
- The six H1-2007 signal months and dates match the fixed dates above exactly.
- Every source filing date and ETF operational evidence date used in a snapshot is `<= asOf`.
- Series identity conflicts = 0, prospectus errors = 0, source errors = 0.
- Monthly H1-2007 source-Series counts are nondecreasing.

Any closed-history replay or PIT failure is a stop condition and must be audited rather than accepted by changing rules after the result is known.

Stage21 returns, ranks, CAGR, MaxDD, Calmar, trades, portfolio outcomes, and other strategy performance are prohibited during this validation. `main` and Production remain unchanged.
