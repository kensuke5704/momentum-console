# Design QA

- Source visual truth:
  - `/var/folders/fs/c6jtr54d5578b7x83sgcy_300000gn/T/TemporaryItems/NSIRD_screencaptureui_OzpFQD/スクリーンショット 2026-08-25 0.08.41.png`
  - `/var/folders/fs/c6jtr54d5578b7x83sgcy_300000gn/T/TemporaryItems/NSIRD_screencaptureui_v3hbF8/スクリーンショット 2026-08-25 0.08.58.png`
  - `/var/folders/fs/c6jtr54d5578b7x83sgcy_300000gn/T/TemporaryItems/NSIRD_screencaptureui_UNInFQ/スクリーンショット 2026-08-25 0.10.49.png`
  - `/var/folders/fs/c6jtr54d5578b7x83sgcy_300000gn/T/TemporaryItems/NSIRD_screencaptureui_B1b7c2/スクリーンショット 2026-08-25 0.11.58.png`
  - `/var/folders/fs/c6jtr54d5578b7x83sgcy_300000gn/T/TemporaryItems/NSIRD_screencaptureui_oOe92m/スクリーンショット 2026-08-25 0.12.56.png`
  - `/var/folders/fs/c6jtr54d5578b7x83sgcy_300000gn/T/TemporaryItems/NSIRD_screencaptureui_eb3LKx/スクリーンショット 2026-08-25 0.17.05.png`
- Browser-rendered implementation screenshots:
  - `/tmp/momentum-qa-overview.png`
  - `/tmp/momentum-qa-risk.png`
  - `/tmp/momentum-qa-schedule.png`
  - `/tmp/momentum-qa-mobile-risk.png`
  - `/tmp/momentum-qa-mobile-schedule.png`
  - `/tmp/momentum-qa-mobile-header.png`
  - `/tmp/momentum-qa-desktop-header.png`
  - `/tmp/momentum-qa-action-modal.png`
  - `/tmp/momentum-qa-mobile-action-modal.png`
- Viewports: desktop `1280 x 720`; mobile `390 x 844`
- Density normalization: source and implementation reviewed at CSS pixel scale / device scale factor 1. Focused implementation crops were compared with the corresponding source regions.
- States: Overview, Risk, Operation Schedule, refresh success message, desktop and mobile navigation.

## Full-view comparison evidence

- Desktop Overview preserves the established flat bordered layout. Current Top2 now contains three equal columns without the zGap annotation.
- Desktop Risk uses `RECOVERY`, keeping the state value inside its metric column. Risk cells retain the existing type scale and border rhythm.
- Desktop Operation Schedule contains three items per list. Execution Contract is split into three equal-width cells.
- Mobile Risk is `390px` wide with `scrollWidth === 390`; no page-level horizontal overflow was found.
- The navigation contains seven tabs and no Watchlist tab.
- The header displays the generated-data timestamp in JST on desktop and mobile without horizontal overflow.
- The Next Action guide presents all six action types in a centered desktop dialog and a single-column mobile dialog.

## Focused region comparison evidence

- State metric: `WAITING_RECOVERY` was replaced by the shorter `RECOVERY`; it no longer collides with Portfolio Peak.
- Execution Contract: measured widths are `154.7 / 154.7 / 154.7px` at desktop width.
- Schedule lists: title and inside list marker share the same content inset; both lists contain exactly three items.
- Current Top2: zGap/threshold copy is absent; Allocation remains centered in the third cell.
- Persistent Risk Control: Japanese explanatory copy is absent. `10 bp / side` remains at the existing `22px` desktop type size and renders on one line.
- Refresh feedback appears immediately and is removed after four seconds.
- Header timestamp renders as `最終更新 2026.08.24 19:36` from the current local dashboard payload.
- Allocation contains only `50/50`; no zGap/threshold copy remains in Overview or Portfolio because both use the same Top2 component.

## Required fidelity surfaces

- Fonts and typography: existing Manrope/Roboto Mono system, weights, sizes, and line heights preserved. Only state copy was shortened; the execution-cost font size was not reduced.
- Spacing and layout rhythm: three-column Execution Contract is mathematically equal; list indentation and bordered-card rhythm are consistent.
- Colors and visual tokens: no token, color, border, or semantic-state changes.
- Image quality and asset fidelity: no raster or illustrative assets are involved in the affected UI; existing Phosphor navigation icons are preserved.
- Copy and content: all requested deletions and label changes are reflected, and the Watchlist surface is removed.

## Interaction and console checks

- Tab navigation checked for Overview, Risk, and Operation Schedule.
- Final-update timestamp checked at desktop and `390px` mobile widths.
- Refresh action checked: success message appears, then disappears after four seconds.
- Next Action modal checked: card activation, six definitions, current-action emphasis, close button, background containment, and Escape dismissal.
- Automatic refresh is scheduled every five minutes and when the page becomes visible again; it reuses the same cache-busted dashboard fetch without showing the manual-refresh notice.
- Browser console warnings/errors: none.

## Comparison history

- Earlier P1: raw `WAITING_RECOVERY` collided with the adjacent value. Fixed with a compact state-display label; post-fix capture shows clear separation.
- Earlier P2: Execution Contract left unused fourth-column space. Fixed with a dedicated equal three-column grid; post-fix widths are identical.
- Earlier P2: schedule markers began left of the header inset. Fixed with inside list positioning; post-fix capture aligns the content starts.
- Earlier P2: zGap detail and Japanese risk descriptions added unwanted wrapping/density. Removed as requested; post-fix captures show clean cells.
- Earlier P2: Watchlist remained in navigation after the feature was retired. Tab, component, data source, and CSS were removed; post-fix DOM contains no Watchlist entry.
- Added interaction: Next Action now opens a six-entry explanation dialog. Desktop and mobile post-fix captures show all content without page-level horizontal overflow.

## Findings

No actionable P0, P1, or P2 differences remain for the requested changes.

## Follow-up polish

None required for this scope.

final result: passed
