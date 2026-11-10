"""Independent structural and scalar-metric checks on the exported deliverable."""
from pathlib import Path
import csv,gzip,json,math
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
master=pd.read_csv(ROOT/'data/master_research_30min.csv.gz');core=pd.read_csv(ROOT/'data/features_core_30min.csv.gz');pred=pd.read_csv(ROOT/'data/baseline_predictions_30min.csv.gz');contract=json.loads((ROOT/'docs/data_contract.json').read_text())
assert len(master)==31248 and not master.isna().any().any()
assert not master.duplicated(['area','datetime_jst']).any()
assert (master.groupby(['area','delivery_date']).size()==48).all()
assert len(core)==len(master) and not any(c.startswith('target_') for c in core)
assert all(c in master for c in contract['feature_allowlist'])
assert not master.strict_availability_verified.any()
assert pd.to_datetime(master.assumed_available_time_jst,utc=True).lt(pd.to_datetime(master.bid_cutoff_jst,utc=True)).all()
assert len(pred)==166656 and not pred.duplicated(['target','method','datetime_jst']).any()
exported=pd.read_csv(ROOT/'data/baseline_metrics_segments.csv')
for _,r in exported.iterrows():
 g=pred[(pred.target==r.target)&(pred.method==r.method)&(pred.evaluation_segment==r.evaluation_segment)]
 errors=[float(p)-float(a) for p,a in zip(g.prediction_jpy_kwh,g.actual_jpy_kwh)]
 assert len(errors)==r.n and abs(sum(map(abs,errors))/len(errors)-r.MAE)<1e-10
 assert abs(math.sqrt(sum(e*e for e in errors)/len(errors))-r.RMSE)<1e-10
for p in (ROOT/'data').glob('*.gz'):gzip.decompress(p.read_bytes())
print('PASS: 31,248 master rows; 166,656 baseline predictions; all segment MAE/RMSE independently checked.')
