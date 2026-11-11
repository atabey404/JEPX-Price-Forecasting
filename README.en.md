# Japan JEPX Day-Ahead Price Forecasting

[简体中文](README.md) · [English](README.en.md) · [日本語](README.ja.md)

A research project for next-day electricity prices in Tokyo, Kansai and Kyushu, with 48 half-hour intervals per area. Current milestone: four model experiments and a bilingual Kairo platform, including its dark introduction, interactive charts, interval ledger, evaluation and data export.

[Open Kairo](https://atabey404.github.io/JEPX-Price-Forecasting/) · [Complete data archives](https://github.com/atabey404/JEPX-Price-Forecasting/releases/tag/v0.2.0-data-20261105) · [All artifact checksums](docs/ARTIFACTS.json)

## Current evidence — 10 November 2026

The core candidate uses historical prices and calendar features, with an 84-day rolling HGB residual model and 12 inputs. Weather was explored separately; the current core model is not a weather/supply/price integrated production system. Retained published prices cover delivery through 11 November and forecasts through 12 November. These are delivery dates, not the snapshot's wall-clock date.

On the 106-day shared historical comparison (29 July–11 November), core MAE is 3.686 / 4.162 / 3.454 JPY/kWh for Tokyo / Kansai / Kyushu. The previous-day baseline is 4.157 / 4.797 / 3.762. Conservative half-correction and adaptive 28-day variants did not improve the overall result, so the core candidate remains unchanged.

**The core candidate has only one scored prospective delivery day (11 November).** Its MAE was 5.311 / 3.700 / 5.526, against previous-day baseline 4.843 / 3.718 / 4.042. New variants have zero scored prospective days. The historical comparison is exploratory and does not establish future stability. All 12 November outcomes remain pending.

## Repository and data

| Path | Contents |
| --- | --- |
| `platform/` | Current React/Vinext source, Japanese/English UI, retained `public/data/market.json` |
| `artifacts/` | Five complete subsequent archives: master table/baselines and experiments 01–04, including data, scripts, audits, metrics and figures |
| `research/` | Directly browsable scripts, specifications and verification records from those archives |
| `JEPX_Project/`, `JEPX_Step2/`, `JEPX_Step3/` | Original data preparation code and selected validation outputs |
| `docs/ARTIFACTS.json` | All eight archive locations, byte sizes and SHA256 hashes |

The three large original price, supply/generation and weather datasets remain downloadable in the public release linked above. They are not missing from this update. Download those three and extract the five archives in `artifacts/` into the same directory, retaining their top-level names. This preserves the complete snapshot and stage dependencies. Original archive contents and source-language notes are preserved byte-for-byte.

Initial retained data include 22 fiscal-year JEPX price files, 148 supply/generation files, nine weather reference locations, run-specific GFS forecasts and a TSO publication audit. See [data notes](docs/DATA_NOTES.md), [sources](docs/SOURCES.md), and each archive's README for coverage, processing and assumptions. Verify downloaded files with the manifest before reproduction.

## Run the platform

```sh
cd platform
npm ci
npm run build:pages
npx vite preview --config vite.pages.config.mjs
```

Node 22.13+ is required. See [hosting notes](platform/HOSTING.md) for creating your own deployment. The original deployment identity, credentials, runtime state and dependencies are excluded from this public source copy. Python research uses each archive's requirements and scripts; extract dependencies before running them.

## Platform scope and next step

Kairo has a dark introductory site with smooth scroll-driven focus, Japanese/English switching and a bottom workspace entrance. The workspace supports area/day/model selection, 48-slot curves, historical versus prospective evaluation, source inspection, CSV export and browser-local actual-price imports. Imports do not overwrite retained predictions.

This version serves a retained research dataset: 135 delivery dates and 405 area-days. Live fetching, automatic model execution and cloud-persistent uploads are not connected. Historical first-publication timestamps are not fully reconstructed; retrospective actuals and reanalysis are not assumed available before bidding. Continue collecting unchanged, timestamped pre-auction forecasts and score every retained variant against simple baselines, targeting at least 28 prospective days before considering promotion.
