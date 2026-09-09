# H2 2008 N-PX PIT Master Validation Definition

Defined: 2026-09-10 JST, before observing any H2-2008 N-PX PIT master result.

## Frozen base

- authoritative H1-2008 N-PX PIT run: `34320224950`
- authoritative H1-2008 N-PX PIT artifact: `10091573844`
- base for extension: the validated `2008-06` PIT master from that artifact
- frozen N-PX parser blob: `bc2d44dda6bfae00ebba22a81ba867a18bbd7ba5`
- frozen N-PX builder blob: `ad977557eb7f48fc0c0d71a2c369b0d61f6c1239`
- frozen structural mapping implementation blob: `690479017fc82dce2480ded5d1ffafbb76721722`

## H2-2008 signal dates

- `2008-07-31`
- `2008-08-29`
- `2008-09-30`
- `2008-10-31`
- `2008-11-28`
- `2008-12-31`

## Frozen extension rule

For each signal date, inspect only SEC N-PX evidence filed in calendar 2008 and public by that signal date. Primary `N-PX` filings are eligible for admission; `N-PX/A` is inventoried but is not independently admitted by the sampling rule.

Continue the exact validated H1-2008 source-admission process: among public primary 2008 N-PX filings, retain the earliest public filing per CIK as representative, sort representatives deterministically by CIK/date/filename, apply the same fixed 64-position equal-quantile sampling rule, and union the fixed broad-family CIK set when public. Admissions are monotone. The validated `2008-06` PIT master is immutable base content; H2 may append only unique records from newly admitted 2008 evidence.

Identity records use the same frozen N-PX parser and issuer normalization/build semantics as H1-2008. Duplicate suppression remains the frozen identity key `(normalizedIssuer, ticker, securityId)`.

## Required invariants

- all six H2 signal dates are produced in order;
- the exact validated `2008-06` base records are copied verbatim and are never deleted, altered, reordered, or retroactively repaired;
- active incremental source sets are monotone relative to the H1 base and across H2 signals;
- every incremental source satisfies `dateFiled <= asOf` and `admittedAtSignal <= asOf`;
- every incremental identity record used for a signal month has filing/admission dates no later than that signal date;
- no `N-PX/A` source is independently admitted;
- SEC index/filing fetch errors are zero for admitted sources;
- the same fixed 64-position quantile rule and fixed broad-family CIK set are used;
- no N-Q holding name, mapping success, country outcome, Universe outcome, ticker performance, rank, return, trade, or Stage21 result may affect N-PX source admission;
- outputs are monotone extensions of the exact validated H1 `2008-06` base;
- future H2 issuer variants must be blocked from earlier signal months.

Any failure is an implementation or data-transport issue. Selection, parser, normalization, deduplication, sampling, or PIT rules must not be changed after H2-2008 results are observed.

This definition does not authorize Stage21 performance analysis or any Production change.
