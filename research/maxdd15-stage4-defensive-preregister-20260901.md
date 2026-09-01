# Stage 4 — Defensive / Orthogonal Cash Replacement Preregistration

Date: 2026-09-01
Historical research end: 2026-08-25

## Objective
Replace part or all of P2's 40% cash sleeve with a positive-return diversifier while keeping historical MaxDD <= 17%. Primary stretch pass: CAGR >= 35% and MaxDD <= 17%.

## Locked base
P2 = 42% Fixed60 + 18% frozen G + 40% cash.
No changes to Fixed60 or G rules.

## Defensive candidates
D1 Gold trend: GLD held when GLD close > 200DMA, otherwise cash.
D2 Treasury trend: TLT held when TLT close > 200DMA, otherwise cash.
D3 Defensive rotation: monthly choose the stronger positive 6M momentum asset between GLD and TLT, provided it is above 200DMA; otherwise cash. Close signal -> next open.
D4 Multi-asset trend basket: equal 25% risk sleeves across GLD, TLT, DBC, UUP; each sleeve invested only when its asset is above its own 200DMA, otherwise that sleeve is cash. Close signal -> next open.

## Portfolio tests
For each D1-D4, replace 20%, 30%, or all 40% of P2 cash with the candidate sleeve. Residual is cash. These are round architecture tests, not a fine-grained weight search.

## Decision rules
- Reject if historical MaxDD exceeds 17% in every tested replacement size.
- Reject as cash replacement if CAGR fails to improve on P2 (29.20%) at comparable MaxDD.
- Strong pass if any preregistered architecture has CAGR >=35% and MaxDD <=17%.
- Do not tune DMA, momentum horizon, or replacement weights after results are observed.
