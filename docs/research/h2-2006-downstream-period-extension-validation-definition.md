# H2 2006 Downstream Period-Extension Validation — Definition

Defined: 2026-09-08 JST  
Scope: Jul–Dec 2006 historical-Universe reconstruction only  
Branch: `research/strict-series-source-h2-2006-20260908`

This document defines the downstream period-extension validation required before any broad 2006–2018 Stage21 performance evaluation. It is **not** a new named gate and must not be used to tune reconstruction rules.

## Purpose

Confirm that the already-validated H2 strict source population can pass through the frozen H1 holdings, mapping, country, and historical-Universe semantics without implementation drift or point-in-time lookahead.

No Stage21 returns, ranks, trades, CAGR, MaxDD, Calmar, or strategy outcomes may be read by this validation.

## Fixed lineage

- authoritative H2 strict Series source artifact: `10038284691`
- H2 source SHA256: `f79f8d9e6d7fe45cb115a9c7f087dcca00622ff602cc0147e70e860f3528417d`
- authoritative H1 holdings run/artifact: `34089965073` / `10006530879`
- H2 raw holdings run/artifact: `34179821383` / `10038557328`
- explicit H1↔H2 parser-invariance run/artifact: `34181393477` / `10039022796`
- authoritative H1 mapping run/artifact: `34090287022` / `10006580498`
- H2 structural mapping run/artifact: `34180122700` / `10038597826`
- frozen N-PX security master artifact: `9876020712`
- authoritative H1 strict PIT country run/artifact: `34104858455` / `10012280475`
- frozen historical-Universe builder: `scripts/research-historical-universe-builder.py`, git blob `1357402f34dfea1c1dbdcaac7de5078b680eb5c3`

The H2 country run/artifact and H2 builder-validation run/artifact are intentionally unspecified here because this definition is committed before those executions complete.

## Required checks

### 1. Holdings parser invariance

The explicit invariance artifact must report:

- overlapping H1/H2 Series-ID source-filing records: exactly 120;
- parser-semantic mismatches: exactly 0;
- differences caused solely by the H1 hybrid `legacyIdentity` bridge metadata are permitted because the H2 strict Series-ID adapter deliberately sets that non-parser field to null.

Any holdings/parser semantic mismatch is an immediate failure.

### 2. Frozen mapping semantics

The H2 mapping artifact must retain the authoritative H1 mapping lineage and frozen N-PX master. Accepted mapping methods must be a subset of:

- `BASELINE_EXACT`
- `BASELINE_ADR_BASE_UNIQUE`
- `STRUCTURAL_SUFFIX_EXACT`
- `UNIQUE_LONG_PREFIX`

No fuzzy/edit-distance repair or outcome-dependent mapping is permitted.

### 3. Strict PIT country

The H2 country stage must reuse the authoritative H1 strict PIT country implementation unchanged apart from period/input/output wiring.

For each Jul–Dec signal snapshot:

- signal month/date must be exactly the frozen schedule;
- source-Series and mapped COMMON_EQUITY counts must match the H2 structural-mapping input;
- country classifications are only `US`, `NON_US`, or `UNKNOWN`;
- every dated country evidence item satisfies `evidenceDateFiled <= signal date`;
- no country evidence later than `2006-12-29` is admitted;
- UNKNOWN is never imputed US in the primary reconstruction;
- positive non-CORP-name exceptions in the frozen CORP bridge remain zero, otherwise stop for audit.

### 4. Frozen builder exact parity

Run `scripts/research-historical-universe-builder.py` unchanged on the resolved H2 country snapshots.

For all six Jul–Dec signal months, compare its output against the independent primary-Universe path already present in the frozen H1 country/structural diagnostic implementation extended to H2 inputs.

Required result: **exact equality**, not a threshold, for each month on:

- signal month;
- as-of date;
- source-Series count;
- eligible source-Series count;
- complete ordered primary Universe rows, including symbol, rank, score, `etfCount`, aggregate weight, maximum weight, and recency weight.

All 6/6 months must match exactly.

### 5. Period cardinality and lineage

The downstream result must retain the validated H2 source counts exactly:

- 2006-07: 199
- 2006-08: 221
- 2006-09: 242
- 2006-10: 242
- 2006-11: 245
- 2006-12: 251

The frozen signal dates are:

- 2006-07-31
- 2006-08-31
- 2006-09-29
- 2006-10-31
- 2006-11-30
- 2006-12-29

## PASS condition

This H2 downstream period-extension validation passes only when every check above passes and frozen-builder exact parity is 6/6 months.

A failure must be investigated as source, parser, mapping, country, or builder drift. Rules must not be relaxed based on Stage21 performance or strategy outcomes.

## Explicit exclusions

This validation does not authorize broad 2006–2018 Stage21 performance yet. It validates only the Jul–Dec 2006 historical-Universe reconstruction extension and its frozen semantics.
