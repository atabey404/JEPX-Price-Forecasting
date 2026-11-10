# Future platform brief — requirements recorded before model acceptance

Status: requirements only. No platform has been built or deployed. Model evaluation comes first.

## User requirements

- Build the platform after the forecasting model becomes stable.
- Provide Japanese and English interface settings, covering navigation, charts, tooltips, validation messages, date formats, and exports.
- Retain the useful forecasting/review workflow of the Sichuan project, while creating a distinct visual design and interaction structure.
- Deliver a polished, original interface rather than reproducing the Sichuan layout or changing its colors.

## Proposed direction: JEPX Market Lens

A restrained market workstation with a light ivory/slate palette, teal forecast accents, generous typographic hierarchy, and compact analytical surfaces. Avoid copying the Sichuan dashboard or making glass effects the main design device. Use a custom 48-slot daily timeline as the primary canvas, with regional comparison and publication timing always visible.

## Proposed structure

1. Forecast: delivery date, area selector, 48-slot price trajectory, baseline comparison, peak/low-price windows, and a compact price heatmap. Show model run time, forecast issue time, data status, JST, and JPY/kWh consistently.
2. Review: immutable issued forecasts versus realized JEPX auction prices, rolling MAE/RMSE and baseline skill, daily/monthly inspection, and clearly separated historical reconstructions.
3. Regions: synchronized Tokyo/Kansai/Kyushu views, regional spreads, and optional later coverage of the other six areas once validated.
4. Data: coverage, freshness and unavailable inputs; preserve missing values rather than converting them to zero. A stale forecast must remain visibly stale.
5. Model status: region-specific acceptance status and selected version. Experimental models must not silently replace the accepted model.

Charts should explain the forecast, not expose internal training settings to ordinary viewers. Publish uncertainty bands only after a separate interval-calibration study; bootstrap confidence intervals on historical MAE are not future price prediction bands.

## Model acceptance before implementation

The present retrospective experiment has fixed comparison rules. Passing them is a candidate signal, not production stability. Before operational platform work, require:

- Improvement against a strong price-only baseline across relevant areas and full months.
- Paired day/block uncertainty analysis rather than one favorable aggregate MAE.
- Verified input publication/receipt timestamps and no target-day actual-data leakage.
- At least 30 consecutive prospective delivery days under a frozen specification, with the forecasts retained before the bidding cutoff.
- A reproducible data/forecast pipeline, missing-input behavior, and a separate evaluation store.

The timing and forward-validation requirements remain open. Do not treat this document as authorization to claim a stable model or a completed platform.

## Technical direction to refine after acceptance

Python forecast services with versioned models and immutable prediction records; a separate web front end with Japanese/English dictionaries and locale-aware formatting. Choose the storage and hosting setup when the validated update cadence, data rights, and access scope are known. No scheduled job or external deployment is created in this experiment.
