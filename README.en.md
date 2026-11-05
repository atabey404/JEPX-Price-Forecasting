<div align="center">

# Japan JEPX Day-Ahead Price Forecasting

**From market fundamentals to traceable data and time-aware forecasting evaluation.**

[简体中文](README.md) · **English** · [日本語](README.ja.md)

[Download data](https://github.com/atabey404/JEPX-Price-Forecasting/releases/tag/v0.2.0-data-20261105) · [Data notes](docs/DATA_NOTES.md) · [Roadmap](docs/ROADMAP.md)

Electricity markets · Time series · Weather data · Reproducible research

</div>

## Overview

An incremental research project for forecasting Japan Electric Power Exchange (JEPX) day-ahead electricity prices. The eventual targets are **48 half-hourly System Prices and Area Prices per delivery day**. Initial regional work focuses on **Tokyo, Kansai, and Kyushu**, while the price archive retains all nine areas.

**The current milestone is data preparation. No price forecasting model has been trained or validated.** Historical outcomes are not presented as information known before bidding, and no forecasting accuracy is claimed.

## Current snapshot

Snapshot date: **2026-11-05**. Delivery times use `Asia/Tokyo`.

| Component | Coverage and size | Status |
| --- | --- | --- |
| JEPX prices and volumes | 2005-04-02–2026-11-06; 22 fiscal-year files; 378,672 half-hour records | Downloaded, merged, checked |
| Regional supply/generation actuals | From April 2016; 148 CSVs; 350,669 native-resolution records | Fields and units standardized |
| Historical weather reference | Nine locations; 835,056 hourly ERA5 rows | Complete days through 2026-10-30; 135 incomplete rows on October 31 |
| Run-specific weather forecasts | 217 delivery days, 2026-04-04–2026-11-06; 46,872 target-day hourly rows | Seven variables complete; nine days use earlier runs |
| TSO forecast-publication audit | October 2026; 93 daily files; 4,464 half-hour slots | Audited archive versions excluded from strict pre-bid features |

The forecast table also retains 1,953 auxiliary next-day-midnight records for aligning hourly mean radiation. These are additional to the 46,872 target-day rows.

## Data and source code

Three ZIP assets in the [release](https://github.com/atabey404/JEPX-Price-Forecasting/releases/tag/v0.2.0-data-20261105) contain raw sources, processed tables, checks, and scripts. Code and selected validation outputs are directly browsable here. [ARTIFACTS.json](docs/ARTIFACTS.json) lists download URLs, byte sizes, and SHA256 checksums.

| Directory | Purpose |
| --- | --- |
| `JEPX_Project/` | Official prices, wide/long tables, daily 48-slot checks |
| `JEPX_Step2/` | Tokyo, Kansai, and Kyushu demand/generation actuals |
| `JEPX_Step3/` | ERA5 references, GFS forecast runs, publication audit |
| `docs/` | Scope, limitations, sources, next steps |

## Local use

Use Python 3.11+:

```sh
git clone https://github.com/atabey404/JEPX-Price-Forecasting.git
cd JEPX-Price-Forecasting
python -m pip install -r requirements.txt
```

Download all three release archives and **extract them into the repository root, preserving their top-level directory names**. The archives contain raw data and source-page snapshots required by some scripts. Then reproduce the transformations and checks:

```sh
python JEPX_Project/scripts/process_validate.py
python JEPX_Step2/scripts/normalize_supply.py
python JEPX_Step2/scripts/validate_supply.py
python JEPX_Step3/scripts/normalize_weather.py
python JEPX_Step3/scripts/validate_step3.py
```

Download and forecast-gap scripts are included. External retrieval is subject to rate limits, coverage, and source revisions. Reprocessing the retained snapshot is different from downloading a newer version.

## Timing and limitations

- The bidding cutoff is **10:00 JST on the day before delivery**. A forecast published that evening is too late for that auction.
- GFS normally uses the 12:00 UTC run from two calendar days before delivery, with an explicit **12-hour processing/publication-lag assumption**. Historical first-server availability is not verified; this is not a fully proven leakage-free dataset.
- ERA5 is retrospective reanalysis, not an archived issued forecast. Target-day actuals are research/evaluation data, or lagged inputs only after availability constraints.
- Older supply data are hourly; recent files are half-hourly. Native resolutions remain separate. Kyushu has overlapping hourly/half-hourly coverage in March 2024; do not double-count it.
- Nine weather locations are preliminary point features, without load or installed-capacity weighting. They are not precise area-average weather.

## Next steps

Define field-level availability rules and assemble a first master table. Establish calendar/historical-price baselines, then evaluate weather features under the stated timing assumptions using daily rolling tests. Pre-auction regional demand and renewable forecasts remain to be sourced or modeled.

## Sources and use

Sources include JEPX, TEPCO, Kansai T&D, Kyushu T&D, and Open-Meteo access to NOAA GFS and ECMWF/Copernicus ERA5. See [sources](docs/SOURCES.md). Original fields and source languages are retained. Public availability here does not change third-party rights or terms. Existing Chinese instructions inside the original archives remain preserved; the project README is available in three separate languages.
