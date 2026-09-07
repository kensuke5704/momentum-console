# Stage21 Overlay Shadow Comparison — 2026-09-07

Status: research-only. Production `momentum-stage21-sbi-2026-09-v1` is unchanged.

## Scope

Re-ran four pre-existing overlay architectures on the frozen 2020-01-01 through 2026-08-25 research sample. This is not new OOS evidence and must not be used to tune Production Stage21. The purpose is only to decide whether a separate V5 overlay shadow is worth implementing.

Reference Production Stage21 rounded v1 (release-aware): CAGR 48.6072%, MaxDD -16.8860%, Calmar 2.8786.

## Re-run results

| Architecture | CAGR | MaxDD | Calmar | Planning proxy | Pass original 40% / -17% gate |
|---|---:|---:|---:|---:|---|
| Fast shock: M3 + core 5-session <= -8% | 47.9289% | -23.0589% | 2.0785 | 45.6831% | No |
| Shock quarantine: 5 sessions 100% cash | 44.9337% | -23.9060% | 1.8796 | 45.2286% | No |
| Vol guard AV: VIX9D/VIX >= 1.10 | 41.6702% | -18.8017% | 2.2163 | 38.5139% | No |
| Vol guard AW: VIX 5-session increase >= 50% | 44.7150% | -18.2825% | 2.4458 | 40.7256% | No (DD gate) |
| Vol guard AX: AV OR AW | 41.0612% | -18.7561% | 2.1892 | 38.3958% | No |
| Vol target 20% | 31.7651% | -16.9135% | 1.8781 | 29.9710% | No |
| Vol target 25% | 37.1601% | -18.1559% | 2.0467 | 35.5128% | No |

## Interpretation

None of the already-tested shock/volatility overlays dominates frozen Stage21 on the same research sample. Fast shock and cash quarantine materially worsen drawdown despite preserving substantial CAGR. Volatility guards reduce volatility but still produce worse drawdown than Stage21 and lower CAGR. Vol-targeting comes closest to the Stage21 drawdown ceiling at 20% target volatility, but sacrifices too much CAGR.

The strongest alternative by Calmar among these overlays is AW (VIX +50% over 5 sessions), Calmar 2.4458, still below frozen Stage21 Calmar 2.8786 and with worse MaxDD (-18.28% vs -16.89%). Therefore a new V5 overlay should not be promoted or added to Production based on the existing sample.

## Decision

1. Keep Production Stage21 unchanged.
2. Close the proposed generic V5 daily shock/volatility-overlay direction as redundant on the current research sample.
3. Do not optimize thresholds around -8%, VIX9D/VIX 1.10, VIX +50%, or vol targets 20/25%; doing so would add same-sample selection bias.
4. Treat True Forward OOS beginning 2026-09-02 as the primary evidence stream for Production Stage21.
5. Any future alternative must use a separate strategy ID and a separate OOS clock, and should be motivated by a failure mode observed in forward data rather than further in-sample tuning.

Reproduction run: GitHub Actions run `34071601980`, job `101589856669`, branch `research/stage21-overlay-shadow-20260907`.
