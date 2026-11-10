# Verification record — 10 November 2026

- Source dataset: 135 delivery dates, 405 area-days, 48 slots each.
- Independently reproduced archive core MAE for Tokyo/Kansai/Kyushu and first prospective-day MAE: six reference groups, tolerance 1e-6.
- Pending 12 November outcomes remain null and are excluded from accuracy metrics.
- New variants' known historical outcomes are labeled retrospective; their prospective scores are absent.
- Previous-day improvement uses the same scored days as the method being evaluated, including future local imports.
- Desktop browser inspected after local build; regional filters, 106-day metrics, first prospective-day metrics, Japanese/English, interval ledger and Escape-to-close checked.
- Responsive UI inspected using 390px and 768px iframe viewports in a temporary QA route, subsequently removed from source.
- Official Shift_JIS JEPX CSV uploaded; retained results were not overwritten and no duplicate outcomes were added.
- Download completed: 49 CSV lines, 48 interval rows; checked header and first data row for Kyushu / 2026-11-11.
- TypeScript checks and production build passed before final packaging; final source is built by the packaging workflow.
- Automated live feed, new model inference and cloud-persistent imports are not part of this version.

## Introduction and commercial typography update

Root introduction verified with real 12 November retained forecast values: Kyushu 19.51 average / 41.22 peak. Regional tabs, English/Japanese switching, three-step animated workflow and bottom entry navigation to /workspace were checked. 390px introduction and workspace viewed in temporary iframe QA, then removed. Workspace headings and introduction use sans-serif typography; removed personal block, sidebar edition card, footer edition line and K icon stay absent. Reduced-motion styles remove loop/reveal animations. Legacy root view links redirect to the workspace.

## Dark theme and readability update

Intro and workspace use a dark, high-contrast neutral/blue palette, with larger navigation, body text, labels and numerical metrics. Desktop intro supports scroll-driven product focus, surface lighting and real-curve reveal; 390px intro/workspace layouts inspected. Sentence full stops are removed from introductory copy and wordmarks; decimal forecast values remain intact. Deep links and the bottom workspace entrance are unchanged. Small/short displays and reduced-motion preferences disable sticky scroll staging.

## Screenshot cleanup and motion refinement — 10 November

Removed the snapshot caption, hero numerical caption, hero/platform metadata strip, feature-card counters, approach section label, footer snapshot paragraph and private-workspace entry message in both languages. Removed diagonal external-navigation symbols from the introduction and workspace; interval detail and share actions retain explicit text labels. Product staging now uses one requestAnimationFrame interpolation loop, a single GPU transform, no hover tilt or competing surface animation, and reduced-motion/small-viewport fallbacks. Desktop root DOM confirms the removed elements are absent and no horizontal overflow; bottom entrance reaches the retained-data workspace.
