# Momentum v2.9 pre-ID identity audit — 2026-09-06

Branch under audit: `research/nq-npx-mapping-2006-20260903`

## Gate result

Do **not** build the authoritative Jan–Jun 2006 hybrid catalog from pre-ID artifact `9972690542` yet.

The handoff requires the pre-ID artifact to be checked for mixed Vanguard conventional siblings and identity hygiene before hybridization. This audit found two concrete blockers.

## Blocker 1 — conventional Vanguard sibling false positive

`VANGUARD WORLD FUNDS / International Growth Fund` is present as `DIRECT_EXPLICIT_ETF_CLASS_ASSOCIATION` in artifact `9972690542`.

The production classifier scans 1–3 normalized lines. `TITLE_PHRASE_CARRIES_CLASS` currently accepts a phrase whenever the normalized Series title occurs and the remaining suffix merely contains `VIPER`, `ETF`, or `EXCHANGE-TRADED`. That permits a class token belonging to a following Series to bind to the preceding title.

Required tightening: the same phrase must also satisfy the existing `base.accepted_title_phrase(phrase, normalized_title)` rule. This restricts the suffix to the already-approved exact class suffix grammar instead of arbitrary intervening text.

Conceptual change:

```python
accepted = base.accepted_title_phrase(phrase, normalized_title)
if accepted:
    exact_hits.add(i)
...
if accepted and suffix and CLASS_TOKEN.search(suffix):
    direct.append((i, 'TITLE_PHRASE_CARRIES_CLASS'))
```

Keep the separate exact-title + immediate class-only-line branch unchanged until the rerun shows a reason to tighten it.

## Blocker 2 — deterministic Vanguard title aliases are double identities

Within the four direct-replacement Vanguard CIKs, the artifact contains 16 one-to-one pairs whose normalized names differ only by an exact leading `VANGUARD` token, for example:

- `Small-Cap Growth Index Fund` / `Vanguard Small-Cap Growth Index Fund`
- `Health Care Index Fund` / `Vanguard Health Care Index Fund`
- `Emerging Markets Stock Index Fund` / `Vanguard Emerging Markets Stock Index Fund`

All 16 collisions are pairs only; no group has more than two identities in the audited artifact.

The current hybrid bridge deliberately uses same-CIK + exact-normalized-name + uniqueness only. Therefore these aliases do not bridge to the same post-ID Series. Simulating the existing hybrid catalog logic with artifacts `9972690542` and `9963958301` yields cross-regime duplicate economic Series in 5 groups at 2006-02-28 and 17 groups at 2006-03-31.

Do not loosen the post-ID bridge with fuzzy or rename inference. Resolve aliases in the pre-ID layer only, using PIT evidence.

Candidate conservative alias rule for validation:

- same CIK;
- both identities have direct Series/class binding;
- names differ only by exact leading `VANGUARD`;
- the alias group is exactly one-to-one;
- no post-ID metadata is used to discover or select the pair;
- retain the original source-observed title for schedule parsing;
- canonicalize only the legacy identity used by the hybrid bridge.

This rule must be rerun/audited before acceptance; it is not yet frozen.

## Current counts from artifact inspection

- pre-ID positive identities: 192
- pre-ID source occurrences: 366
- direct-class identities: 39
- post-ID positive Series: 198
- current exact unique pre/post bridges: 111
- direct-class pre-ID identities with exact post-ID name match: 21
- direct-class pre-ID identities without exact post-ID name match: 18
  - 17 are the deterministic no-`Vanguard` aliases described above
  - 1 is `International Growth Fund`

Existing hybrid logic, without fixes:

- 2006-01-31: 192 source identities
- 2006-02-28: 204 source identities; 5 cross-regime Vanguard alias duplicates
- 2006-03-31: 267 source identities; 17 cross-regime Vanguard alias duplicates

## Next execution order

1. Tighten `TITLE_PHRASE_CARRIES_CLASS` in the direct pre-ID classifier and matching diagnostic.
2. Rerun the four mixed Vanguard CIK replacements and inspect every direct identity, especially `International Growth Fund`.
3. Validate a pre-ID-only exact-leading-`VANGUARD` alias-collapse rule; do not change the exact post-ID bridge.
4. Regenerate the authoritative pre-ID artifact and re-audit identity counts / trust-name contamination / alias collisions.
5. Only if that gate passes, combine it with post-ID artifact `9963958301` and audit 2006-01, 2006-02, 2006-03 before proceeding to raw holdings.

Broad 2006–2018 Stage21 performance remains blocked.
