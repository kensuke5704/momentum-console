# H2 2007 PIT Country Issuer-Variant Validation Definition

Defined: 2026-09-08 JST before any H2-2007 country-resolution result is produced.

This is a downstream validation definition under `docs/research/h2-2007-downstream-period-extension-validation-definition.md`. It is not a new named gate and does not authorize Stage21 performance analysis.

## Frozen country semantics

The authoritative country implementation remains:

- `scripts/research-nq-hybrid-pit-country-gate-b-h1-2006.py`
- git blob `7b830b0e851b0d5349a5c6049e8889f171b791e0`

The validated H1-2007 period extension remains the reference wrapper:

- `scripts/research-nq-series-id-pit-country-h1-2007.py`
- git blob `483c3ee8979c9ff38c5600b071e6bd489697a32a`

Its only SEC filing-period extension is master-index coverage through 2007. The frozen resolver itself filters candidate filing evidence to `dateFiled <= signal date` and independently hard-fails any accepted positive filing evidence with `evidenceDateFiled > signal date`.

Static classification order and semantics remain unchanged: explicit historical N-Q country when present, alphabetic CINS, ADR/GDR/ADS receipt semantics, frozen dated filing evidence, then strict PIT submission-header resolution; unresolved remains `UNKNOWN`. No current-country backfill is permitted. The CORP/non-corporate invariant remains unchanged.

## Fixed H2 upstream lineage

- strict Series source run `34188233028`
- strict Series source artifact `10041257985`
- source catalog SHA256 `9ffed81a42044f7388221a60450a24967ea61f108eb63f66464699ada1849631`
- holdings run `34188353154`
- holdings artifact `10041300366`
- authoritative H2 PIT N-PX run `34190105652`
- authoritative H2 PIT N-PX artifact `10041975282`
- frozen pre-2007 N-PX base artifact `9876020712`
- base country evidence artifact `9944538015`
- structural country evidence artifact `9944797581`

The country workflow must additionally pin the successful H2-2007 structural-mapping run/artifact produced under `docs/research/h2-2007-structural-mapping-validation-definition.md`. Mapping coverage may not be used to alter country rules.

## H2 N-PX issuer-variant PIT boundary

The frozen country implementation uses the N-PX security master only in its `unresolved()` preprocessing step to add issuer-name variants for already-mapped `(ticker, securityId)` identities. In H1-2007, the frozen pre-2007 N-PX master was public before every signal date. H2-2007 introduces incremental 2007 N-PX identity records, so passing a period-end master without row-date filtering could expose an earlier signal to a later issuer-name variant.

Therefore the only H2-specific adaptation permitted in this country stage is the following point-in-time filter inside the issuer-variant collection used by `unresolved()`:

1. Start from the authoritative cumulative December H2 N-PX master from artifact `10041975282`. Its source admissions are already validated as monotone and its record set is the cumulative union available by year-end.
2. For each mapped holding identity and each signal date independently, issuer variants from the N-PX master are eligible only when the record was public by that signal date.
3. A pre-2007 frozen-base row is always eligible in H2-2007. This includes legacy rows whose `sourceFilingDate` is a year-level value such as `"2006"`.
4. A 2007 incremental row is eligible only if both:
   - `sourceFilingDate <= signal date`; and
   - `admittedAtSignal <= signal date`.
5. The holding's own historical description remains an eligible issuer variant exactly as in the frozen implementation.
6. No later N-PX issuer variant may be carried backward. Once a country classification is positively resolved at an earlier signal date, the frozen resolver's existing forward carry semantics may continue to later dates exactly as before.

This adaptation changes only which N-PX issuer-name strings are visible to the frozen unresolved-identity preprocessing at a given signal date. It must not change mapped ticker/security identity, static-country semantics, name cleaning, SEC submission-header resolution, conflict handling, evidence-date rules, carry-forward direction, UNKNOWN handling, source eligibility, or Universe construction.

## Mechanical implementation requirement

The H2 wrapper must load the exact authoritative frozen H1-2006 country module and retain its `resolve_one`, `static_country`, `classify`, `resolve_shard`, `merge`, source-eligibility, and Universe functions. It may replace only the module's `unresolved(mapping, npx, base, struct)` function with a semantically identical copy whose N-PX issuer-variant lookup is signal-date aware under the rule above, plus the already-validated H1-2007 SEC master-index extension through 2007.

The H2 wrapper must use the authoritative December cumulative N-PX master only as a container for dated records. It must hard-fail if a 2007 incremental record lacks either `sourceFilingDate` or `admittedAtSignal`, or if either field is later than the record's first valid H2 signal inclusion implied by the PIT audit.

## Required PASS assertions

Before H2 country output is accepted:

- frozen H1-2006 country blob assertion passes;
- H1-2007 reference wrapper blob assertion passes;
- successful H2 mapping lineage is pinned and its six month/date/source-Series boundaries are Jul-Dec `465, 469, 499, 518, 531, 533`;
- authoritative N-PX PIT audit is `PASS`, has zero fetch errors, and zero PIT violations;
- country resolver master-index years are exactly `[2005, 2006, 2007]`;
- every accepted positive filing evidence date satisfies `evidenceDateFiled <= signal date`;
- every 2007 N-PX issuer variant exposed to a signal satisfies both N-PX PIT dates above;
- no N-PX issuer variant first available after a signal contributes to that signal's unresolved identity input;
- country classifications are only `US`, `NON_US`, or `UNKNOWN`;
- `UNKNOWN` remains present when evidence is insufficient and is not defaulted to US;
- `corpPositiveNonCorpNameCount == 0` for every month;
- source-Series and COMMON_EQUITY mapped-input boundaries match the structural mapping exactly.

Any mismatch is a stop condition before historical Universe builder parity.

## Prohibited

Do not use Stage21 returns, ranks, CAGR, MaxDD, Calmar, trades, portfolio outcomes, strategy outcomes, current country metadata, future Series/Class evidence, later N-PX issuer variants, fuzzy/edit-distance repair, or country coverage to tune these rules. Do not modify `main` or Production.
