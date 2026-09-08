# H2 2007 Closed-History Candidate-Discovery Boundary Correction

Date: 2026-09-08 JST

## Status

This implementation correction is defined after the first H2 2007 source run failed the already-committed period-extension validation, and before any corrected source result is produced.

It does **not** relax or replace `docs/research/h2-2007-source-period-extension-validation-definition.md`. The original requirement that H1 2007 Jan-Jun source snapshots replay exactly remains authoritative.

## Observed failure

Initial strict-source run `34187436415` used the unchanged final Series evidence/binding grammar and passed every pre-defined source check except exact closed-history replay:

- H1 2007 June source Series: 433
- cumulative H2 replay for June: 447
- extra: 14
- missing: 0
- changed common Series: 0

Audit-only diagnostic run `34188080894`, artifact `10041208253`, established that all 14 extras:

- belong to one registrant, CIK `0001352853` (`HealthShares (TM) Inc.`);
- were **not** in the authoritative H1 2007 candidate-review set;
- were first admitted to candidate review only by the H2 2007 cumulative prefilter;
- already had source filings and issuer-own evidence dated before the closed June signal date, so the later candidate discovery caused a retroactive admission into a period that had already been validated and frozen.

No prior H1 Series disappeared and no common H1 Series record changed.

## Correction rule

Candidate prefilter evidence remains discovery-only and does not become final ETF evidence. However, discovery made in a later extension period must not rewrite an already closed prior-period source catalog.

Therefore:

1. The authoritative H1 2007 candidate-review set from artifact `10039881783` is the only candidate-review set permitted when reconstructing the closed Jan-Jun 2007 replay snapshots.
2. CIKs first discovered by the H2 2007 candidate prefilter may contribute to H2 Jul-Dec 2007 snapshots, subject to the unchanged strict issuer-own evidence, Series metadata/binding, complete-portfolio, and no-lookahead requirements.
3. A newly discovered H2 CIK is not allowed to contribute retroactively to Jan-Jun 2007 merely because a later discovery causes the strict scanner to find older filing evidence.
4. The cumulative H2 shard outputs are not altered. The boundary is applied only when the merge constructs the closed-history replay snapshots.
5. `positiveSeries`, `sourceOccurrences`, evidence grammar, structural binding, no-lookahead tests, and H2 Jul-Dec snapshot construction remain unchanged.
6. The corrected merge must still pass the original pre-defined validation unchanged, including exact H1 sourceFilings replay, prior Series identity/binding exactness, zero conflicts/errors, and H2 no-lookahead.

## Rationale

This is a period-extension closure invariant, not a source-selection threshold. Without it, a recall-oriented candidate discovery screen can use information discovered during a later extension to change an earlier closed reconstruction even though final Series evidence itself is PIT-dated. The boundary prevents that cross-period discovery lookback while preserving all strict evidence requirements for the new H2 period.

No Stage21 returns, ranks, trades, CAGR, MaxDD, Calmar, portfolio outcomes, or strategy outcomes were inspected or used in identifying or defining this correction.
