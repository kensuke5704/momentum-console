# H1 2008 N-PX PIT Master Validation Definition

Defined 2026-09-09 JST after H1-2008 strict source validation PASS and before observing any H1-2008 N-PX PIT master result.

## Frozen base

- authoritative H2-2007 N-PX PIT run: `34190105652`
- authoritative H2-2007 N-PX PIT artifact: `10041975282`
- base for extension: the validated `2007-12` PIT master from that artifact
- frozen N-PX parser blob: `bc2d44dda6bfae00ebba22a81ba867a18bbd7ba5`
- frozen N-PX builder blob: `ad977557eb7f48fc0c0d71a2c369b0d61f6c1239`
- frozen structural mapping implementation blob remains `690479017fc82dce2480ded5d1ffafbb76721722`

## H1 2008 signal dates

- 2008-01-31
- 2008-02-29
- 2008-03-31
- 2008-04-30
- 2008-05-30
- 2008-06-30

## Frozen extension rule

For each signal date, inspect only SEC N-PX evidence filed in calendar 2008 and public by that signal date. Use primary `N-PX` filings for admission; `N-PX/A` is inventoried but is not independently admitted by the sampling rule.

For public primary 2008 N-PX filings, retain the earliest public filing per CIK as the representative, sort representatives deterministically by CIK/date/filename, select the same 64-position equal-quantile sample used by the validated H2-2007 process, and union the fixed broad-family CIK set when public. Admissions are monotone across H1-2008 signal dates. The validated 2007-12 PIT master is immutable base content; only unique records from newly admitted 2008 evidence may be appended.

Identity records use the same frozen N-PX parser and issuer normalization/build semantics as H2-2007. Duplicate suppression is by the frozen identity key `(normalizedIssuer, ticker, securityId)`.

## Required invariants

- all six signal dates are produced in order;
- base records are copied verbatim and are never deleted, altered, or reordered;
- active incremental source sets are monotone;
- every incremental source has `dateFiled <= asOf` and `admittedAtSignal <= asOf`;
- every incremental identity record used for a signal month has filing/admission dates no later than that signal date;
- no `N-PX/A` source is independently admitted;
- SEC index/filing fetch errors are zero for admitted sources;
- the same fixed 64-position quantile rule and fixed broad-family CIK set are used; no N-Q holding name, mapping success, country outcome, Universe outcome, ticker performance, rank, return, trade, or Stage21 result may affect N-PX source admission;
- output masters are monotone extensions of the exact validated 2007-12 base.

Any failure is an implementation/data transport issue. The selection, parser, normalization, deduplication, or PIT rules must not be changed after H1-2008 results are observed.
