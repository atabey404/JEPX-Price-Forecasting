# Kairo — Japan Power Observatory

[English](README.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

A Japanese/English research platform for JEPX day-ahead electricity price forecasting in Tokyo, Kansai and Kyushu. Original dark visual design, informed by Linear's information hierarchy, Mercury's financial-data clarity and Apple-inspired product presentation pacing.

## Included

- Overview: next-day outlook, 48-slot interactive curves, regional summaries and explicit publication status.
- Forecast explorer: original HGB, 50% correction and 28-day adaptive variants; previous-day and seven-day median baselines; signed interval errors and detail drawer.
- Evaluation: separate retrospective/prospective records, region/date filters, MAE/RMSE/bias and daily error history. Baseline improvement is computed on each method's own scored dates.
- Data: source hashes, receipt/issue timestamps, pre-auction provenance and UTF-8 CSV exports.
- Browser-local import of official JEPX Shift_JIS spot CSVs or the normalized template. Complete 48-slot days, unique slots, supported areas and finite prices are checked. Imports only fill missing outcomes for retained forecasts; existing outcomes and forecasts are never overwritten. Results cannot be added before the retained auction cutoff. Imported results are explicitly labeled and remain local to the browser.
- Responsive desktop/tablet/mobile layouts, English/Japanese language persistence, shareable filters, keyboard focus and Escape-to-close details.

## Current snapshot and limits

The retained snapshot is dated **10 November 2026**, with official prices through delivery **11 November** and forecasts through **12 November**. It covers 135 dates, 405 area-days. Historical evaluation starts 29 July; the dataset includes 1–28 July for context. Core model: 84-day rolling training, 12 historical-price/calendar features. Weather is not used in the retained candidate.

Only the original candidate's 11 November delivery has a scored prospective outcome. New variants have no scored prospective outcomes at this snapshot. Retrospective variant results were designed after outcomes were known and are exploratory. Model validation is still in progress.

This version is a functioning research workspace over retained data. It is **not a live feed**, does not run Python models on the server, does not generate new forecasts automatically, and has no background schedule. Browser imports are local, not shared cloud updates. A future forecast-generation service and shared ingestion can be connected separately, keeping immutable issue records. Do not infer current market coverage from the calendar date of a later visit.

## Development and checks

```sh
npm install
npm run dev
npx tsc --noEmit
python scripts/validate_dataset.py
npm run build
```

The project uses the supplied Vinext/Cloudflare Worker setup and preserves Sites integration. `public/data/market.json` is the packaged dataset. No external API keys or fonts are required to view it.

`prepare_dataset.py --input-root <extracted-research-root>` reconstructs the snapshot from the three research folders: JEPX_Model_Stability04, JEPX_Model_Experiment_03 and JEPX_Model_Experiment_01. The design direction and forward acceptance rules are versioned in `docs`. The original research archives are retained separately; source SHA256 values and issue evidence are embedded in the dataset.

Source artifacts: JEPX_Model_Stability04_20261110.zip, JEPX_Model_Experiment03_20261110.zip, JEPX_Model_Experiment01_20261109.zip. Official source: https://www.jepx.jp/electricpower/market-data/spot/ . Dataset round-trip validation reproduces six reference metric groups and checks 48-slot coverage and null pending outcomes.

## Visual and functional verification

Verified locally in the managed browser: desktop overview, Japanese/English switching, regional historical/prospective tables, interval drawer with Escape, mobile navigation at 390px, tablet layout at 768px, Shift_JIS source upload with no retained-result overwrite, and a real 49-line CSV download. Independent dataset metric checks and TypeScript checks pass. No synthetic market data is used.


## Introduction / 介绍页 / 紹介ページ

The root URL now opens a bilingual commercial-style introduction with a real-data interactive preview and a transparent data → forecast → evaluation animation. The final call to action opens `/workspace`, which retains the existing research dashboard. All display typography uses modern sans-serif fonts. Reduced-motion preferences are respected. Legacy root links with a `view` query parameter continue to open the workspace.


Dark visual update: larger type and stronger text contrast throughout, scroll-driven desktop product staging, reduced-motion and compact-display fallbacks, and introductory copy without sentence full stops. Financial decimals remain unchanged.
