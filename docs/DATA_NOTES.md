# Data notes

This snapshot is a data-preparation milestone, not a validated forecasting model.

## Time contract

- Delivery timezone: `Asia/Tokyo`, without daylight saving time.
- Prediction cutoff: delivery date minus one day, 10:00 JST.
- A publication described as "day-ahead" can still arrive after the auction cutoff.
- File download time and file update time are not necessarily original publication time.
- Run initialization time is not forecast availability time.

## Price archive

The 22 fiscal-year files contain 378,672 half-hour records from 2005-04-02 through 2026-11-06. Daily slot coverage and keys pass the original checks. Tokyo prices are missing for 78 historical days and Hokkaido for 20; missing prices remain empty. Block-order fields also have historical gaps. Bid volumes and contracted volumes are distinct fields.

## Supply and generation actuals

148 original CSV files yield 350,669 native-resolution rows. Older records are hourly. Half-hour coverage starts in February 2024 for Tokyo and March 2024 for Kansai and Kyushu. Hourly and half-hourly records remain separate. Kyushu March 2024 overlaps across these resolutions.

Normalized power is in MW. Half-hour energy is MW multiplied by 0.5 hours, in MWh. Do not directly sum power and call it energy. Net imports use positive signs; the modern Kyushu CSV sign is reversed according to the source definition. Small negative solar values in the source are preserved and recorded. The latest day is partial.

## Weather

Nine representative points provide temperature, humidity, 10 m/100 m wind speed, shortwave radiation, cloud cover, and precipitation. They are not capacity- or population-weighted regional averages. API outputs may include interpolation or derived heights.

ERA5 is retrospective reanalysis. Its 835,056 hourly rows extend through October 31, 2026, with 135 incomplete rows at the end of that day. Complete days end on October 30.

GFS forecasts cover 217 delivery dates. There are 46,872 target-day point/hour records plus 1,953 auxiliary midnight records. Seven variables are complete after documented earlier-run selection on nine dates. The nominal run is D-2 12:00 UTC. A 12-hour publication-lag assumption is recorded; historical first-server availability remains unverified. `strict_availability_verified` stays false.

Radiation at timestamp t is the mean over the preceding hour. It must not be assigned as though it described the hour beginning at t. Weather remains hourly; the final 48-slot feature-alignment policy is not yet implemented.

## TSO forecast audit

The October 2026 audit covers 93 files and 4,464 slots. All retained archive versions were updated after the respective bidding cutoff and are excluded from strict pre-bid inputs. This does not prove that earlier historical versions never existed. Wind and solar are combined in these files; do not fabricate separate components.

## Reproducibility

Release archives retain original bytes and source-specific language. Some scripts use source snapshots included only in those archives. Extract all archives into the repository root before running the transformations. Remote re-downloads can differ because sources revise their histories.
