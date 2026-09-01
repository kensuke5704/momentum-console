# Legacy production identity: momentum-fixed60-2026-08-v1

This document preserves the production specification that was active before Stage21. Git history and historical data files remain the authoritative audit trail.

Fixed60 mechanics are **not deleted**: Stage21 still uses the same frozen engine internally for Top2 selection and inner stop/circuit/recovery behavior. What changed is the funded portfolio wrapper and the production/OOS identity.

Legacy Fixed60 production specification:
- Dynamic Universe 80 from PIT SEC N-PORT breadth
- momentum 1M/3M/6M = 0/20/80
- 1M surge exclusion >= +80%
- require stock score > QQQ score
- Top2 fixed 60/40
- QQQ monthly 10M MA gate
- individual stop 17.5%
- portfolio circuit 15%
- recovery: QQQ 100DMA + positive 20D + 10 consecutive closes
- close confirmation -> next US open
- transaction cost 10bp/side
- historical backtest start 2020-01-01

Legacy True Forward OOS began 2026-08-31. That series belongs only to `momentum-fixed60-2026-08-v1` and must not be merged with Stage21 OOS.

Current production wrapper is documented in `docs/production/stage21-sbi-2026-09-v1.md`.
