# Stage21 Console Action Display

The first card on the overview screen is the operational source of truth for manual execution.

It must answer, in this order:
1. What action to take now (rebalance / hold).
2. When to execute it, shown in Japan time and tied to the next US market open.
3. What the post-trade target allocation must be across each symbol and cash.

The inner Fixed60 Top2 is displayed only as explanatory engine state and must never be presented as the final portfolio allocation.

If there is no pending trade, the screen must explicitly say `注文なし` and `現在の配分を維持` instead of showing an ambiguous blank execution time.
