# Design QA — Operational Terminal redesign

- source visual truth path: `/Users/kensuke_kawamura/.codex/generated_images/019fb1cf-5138-7740-ba6b-30b39d2c9664/exec-97a74b78-dce2-4b40-82cd-771608152113.png`
- implementation screenshot path: `/Users/kensuke_kawamura/Documents/Codex/2026-07-30/https-docs-google-com-spreadsheets-d/work/operational-overview-final.jpg`
- full-view comparison: `/Users/kensuke_kawamura/Documents/Codex/2026-07-30/https-docs-google-com-spreadsheets-d/work/design-qa-comparison-final.jpg`
- focused navigation comparison: `/Users/kensuke_kawamura/Documents/Codex/2026-07-30/https-docs-google-com-spreadsheets-d/work/design-qa-focus-navigation-final.jpg`
- viewport: 1440 × 1024 CSS px
- source pixels: 1487 × 1058, normalized to 1435 × 1024 for comparison
- implementation pixels: 1435 × 1024 at device scale factor 1
- density normalization: source scaled to the implementation capture dimensions; no device frame or browser chrome included
- state: desktop, light theme, overview tab, live July 2026 market data. The implementation intentionally shows `Cash` and omits the adopted-stock table because only 9 of the required 10 candidates currently qualify.

## Findings

No actionable P0, P1, or P2 differences remain.

- Fonts and typography: the condensed mono/technical hierarchy, Japanese UI scale, weight contrast, and compact data labels preserve the target direction. Exact glyph metrics differ slightly because the implementation uses the project's available Manrope and Roboto Mono stack; this is acceptable.
- Spacing and layout rhythm: black command bar, fixed left navigation, sharp graphite dividers, two-column evidence/return region, compact decision strip, and dense chart modules match the target composition. No desktop overflow was found.
- Colors and visual tokens: off-white workspace, near-black chrome, graphite rules, and restrained financial green/red match the source. Decorative gradients and elevated card shadows were removed.
- Image quality and asset fidelity: the target contains no raster product imagery. Navigation uses the existing Phosphor outline icon library; no placeholder art, emoji, handcrafted SVG, or CSS illustration was introduced.
- Copy and content: labels remain coherent with the live product. Differences from the mock values and adopted-stock section are dynamic data/rule outcomes, not design drift.
- Icons: all six navigation tabs have distinct, consistently sized outline icons and no numeric prefixes.
- Accessibility and interaction: active state, hover/focus treatment, semantic buttons and labels remain present. All six tabs, the screener search, and desktop layouts were exercised.

## Full-view comparison evidence

The combined comparison confirms the same major proportions and hierarchy: black top bar, pale left rail, sharp page rule, decision strip, evidence metrics, red/green monthly bars, and flat lower data region. The source shows a 10-stock table while the implementation shows the backtest panel because the current candidate count is below 10; this is the required live application behavior.

## Focused region comparison evidence

The navigation crop was compared separately because icon weight, label size, active-state treatment, and header typography are too small to judge reliably in the full-view image. The final pass confirms six icon-led tabs, a green active rule, no numbering, consistent alignment, and a denser technical header.

## Comparison history

- Pass 1: the navigation labels and icons were visually lighter and smaller than the selected target, and the command-bar metadata started too close to the brand. Classified P2.
- Fix: increased navigation label/icon scale, strengthened the terminal brand typography, and moved market metadata toward the right-side command controls.
- Post-fix evidence: `work/design-qa-comparison-final.jpg` and `work/design-qa-focus-navigation-final.jpg` show the corrected hierarchy. No actionable P0/P1/P2 finding remains.

## Primary interactions tested

- Switched through overview, screener, portfolio, backtest, candidate manager, and settings tabs.
- Filtered the screener with `NVDA` and confirmed one matching row, then cleared the filter.
- Verified each tab at 1440 px has `scrollWidth === innerWidth`.
- Confirmed six navigation buttons and six navigation icons.
- Checked browser console warnings/errors after the final render: none.

## Follow-up polish

- P3: if an exact font license and asset become available, the mock's narrower display mono could be matched more precisely.

final result: passed
