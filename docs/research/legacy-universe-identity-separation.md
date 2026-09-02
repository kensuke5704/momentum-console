# Legacy Universe Identity Separation

Last updated: 2026-09-03 JST

## Objective

Prevent historical ticker/security-resolution work from contaminating point-in-time ETF universe selection.

## Layer 1 — PIT universe identity

Universe construction must first operate on an identifier derived only from information present in the public filing at the as-of date.

`legacyIssuerKey` is a conservative normalized form of the holding issuer/security description. Normalization may remove punctuation, legal-suffix spelling variants, filing footnotes, and other structural formatting differences, but may not use future prices, future listing status, realized returns, or later universe membership.

The production economic inputs are then computed by `legacyIssuerKey`:
- distinct ETF-series count
- aggregate holding weight
- maximum ETF weight
- recency-weighted holding weight

The production universe formula and eligibility threshold are applied to these keys. The ranked PIT universe is frozen before ticker resolution.

## Layer 2 — archival security resolution

N-PX and other archival security metadata are used only after PIT rank/membership is known, to resolve a selected `legacyIssuerKey` to:
- historical ticker
- security ID / CUSIP-like identifier when available
- effective-date evidence
- mapping confidence tier

Later archival observations may be used as diagnostic evidence, but they may not cause a previously unselected issuer to enter the universe or cause an unresolved selected issuer to be replaced by another security.

## No-backfill rule

If a selected PIT universe member cannot be resolved to a sufficiently reliable historical security identity or price series:
- mark it unresolved
- reduce the usable universe/coverage for that date
- fail the data-quality gate if coverage is insufficient

Do not backfill from rank 81+, do not substitute a current ticker merely because it has price data, and do not use future survival/listing information to choose among ambiguous candidates.

## Effective-date requirement

Before historical performance is opened, selected-member ticker/security mappings must carry evidence sufficient to determine that the mapping applies to the historical evaluation date. A later N-PX filing by itself is not treated as proof that the later ticker was also the correct historical ticker.

## Consequence

N-PX mapping quality remains important, but it is no longer allowed to influence historical Universe rank or membership. This separates Universe reconstruction fidelity from historical market-data availability and reduces look-ahead/survivorship risk.
