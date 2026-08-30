# Recovery QQQ50 K1 bridge — True OOS operating specification

Research-only specification frozen 2026-08-30.

## Scope

- Base strategy: W70 research candidate on top of the authoritative Production state machine.
- Bridge asset: QQQ.
- Bridge weight: 50% of total account equity; remaining 50% stays cash.
- Total exposure must remain within 0–100%. No leverage or margin.
- Transaction cost: 10 bp per side.
- Production/main remains unchanged unless separately approved.

## Entry rule

1. The authoritative state machine must be in `WAITING_RECOVERY` after a Stop/Circuit exit.
2. Monthly market regime must still be Risk-On.
3. A close must satisfy the Production Recovery conditions:
   - Monthly RiskOn,
   - QQQ > 100DMA,
   - QQQ 20D momentum > 0.
4. For K1, the first consecutive qualifying close schedules the bridge entry.
5. Buy QQQ at the next US trading-session open using 50% of account equity.
6. Do not enter the bridge if Top2 has already re-entered, a bridge is already active, or an exit is pending.

## Exit rules

### Top2 re-entry

- If the Production/W70 state machine re-enters Top2 at an open, liquidate the QQQ bridge at that same open before/alongside establishing the Top2 portfolio.
- There must be no overlapping exposure that pushes total exposure above 100%.

### Market Risk-Off

- If a monthly signal at close changes to Market Risk-Off while the bridge is active, schedule QQQ liquidation for the next US trading-session open.

## Risk-control interaction

- Bridge P&L does **not** feed back into Production Stop/Circuit state variables.
- Stop, Circuit and Recovery calculations remain those of the authoritative Production state machine.
- This separation is intentional: the bridge is a cash-deployment overlay during `WAITING_RECOVERY`, not a redefinition of the Production risk-control state machine.

## Exceptional conditions

- Missing/invalid required QQQ open or close data: do not synthesize a discretionary trade; halt the research/production pipeline for review and preserve an execution ledger entry.
- If Top2 re-entry occurs before a scheduled bridge entry can execute, cancel the bridge entry.
- If Market Risk-Off is already pending, do not schedule a new bridge entry.
- If the bridge is active and Top2 re-entry and a Risk-Off exit resolve on the same open, there is only one QQQ liquidation at that open.
- Overnight gaps are accepted as execution risk because all decisions are close-confirmed and executed at the next open.
- No discretionary override of Stop/Circuit/Recovery/bridge timing is allowed in True OOS tracking.

## Validation status

- Historical/pseudo-OOS evidence is research evidence only and is not true ex-ante OOS.
- True Forward OOS for the overall strategy begins 2026-08-25.
- K1 timing sensitivity remains the principal weakness; K3/K5 deterioration must remain part of the adoption decision.
