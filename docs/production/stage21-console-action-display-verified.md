# Stage21 Console Action Display Verification

Operational UI rule:
- The overview's first card is the manual-execution source of truth.
- It shows the required action, the execution time in Japan time, and the post-trade target allocation.
- When no order is pending, it explicitly shows `注文なし` and `現在の配分を維持`.
- Inner Fixed60 Top2 is explanatory only and is not the final portfolio allocation.
