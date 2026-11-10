from pathlib import Path
import json,hashlib
import numpy as np,pandas as pd
R=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=pd.read_csv(R/'data/predictions.csv.gz');w=pd.read_csv(R/'data/weight_audit.csv');m=pd.read_csv(R/'data/metrics_overall.csv');assert len(p)==134*3*48*4 and not p.duplicated(['area','delivery_date','time_slot','method']).any();assert np.isfinite(p.prediction).all() and (p.prediction>=.01).all();assert np.allclose(p.prediction,np.maximum(p.baseline+p.weight*(p.raw_candidate-p.baseline),.01));assert (pd.to_datetime(w.prior_last.dropna())<pd.to_datetime(w.loc[w.prior_last.notna(),'delivery_date'])).all()
for row in m.itertuples():
 a=p[(p.area==row.area)&(p.method==row.method)&(p.delivery_date>='2026-07-29')];assert len(a)==5088;assert abs(np.abs(a.prediction-a.actual).mean()-row.MAE)<1e-10
r=json.loads((R/'docs/shadow_registry.json').read_text());f=R/r['file'];assert sha(f)==r['sha256'];q=pd.read_csv(f);assert len(q)==288 and not q.duplicated(['area','time_slot','method']).any();assert np.allclose(q.prediction,np.maximum(q.baseline+q.weight*(q.raw_candidate-q.baseline),.01));assert pd.Timestamp(r['issued_at_utc'])<pd.Timestamp(r['bid_cutoff_jst']);assert pd.Timestamp(json.loads((R/'docs/research_plan.json').read_text())['frozen_at_utc'])<pd.Timestamp(r['issued_at_utc']);assert sha(R/'docs/research_plan.json')==r['research_plan_sha256']
source=json.loads((R/'docs/source_provenance.json').read_text());W=R.parent/'stability_work';old=W/'JEPX_Model_Experiment_03'
for e in source['old_registry']:assert sha(old/e['file'])==e['sha256']
for name,digest in source['original_archives'].items():assert sha(R/'inputs'/name)==digest
from core_model import load_prices
receipt=source['price_receipt'];pricepath=old/receipt['path'];assert sha(pricepath)==receipt['sha256'];prices=load_prices(pricepath);assert r['delivery_date'] not in set(prices.delivery_date);assert pd.Timestamp(receipt['retrieved_at_utc'])<pd.Timestamp(r['issued_at_utc'])
# Adaptive selection never uses target-day errors. Recompute a sparse set including the final historical day.
base=pd.read_csv(R/'data/source_prediction_panel.csv.gz');base['date']=pd.to_datetime(base.delivery_date);checked=0
for area in base.area.unique():
 for date in ['2026-07-29','2026-08-15','2026-10-15','2026-11-11']:
  t=pd.Timestamp(date);a=base[(base.area==area)&(base.date<t)&(base.date>=t-pd.Timedelta(days=28))];observed=w[(w.area==area)&(w.delivery_date==date)].weight.iloc[0];loss={z:float(np.abs(np.maximum(a.baseline+z*(a.raw_candidate-a.baseline),.01)-a.actual).mean()) for z in [0,.25,.5,.75,1]};assert abs(loss[observed]-min(loss.values()))<1e-10;checked+=1
result=dict(status='passed',historical_prediction_rows=len(p),comparison_days=106,comparison_samples_per_area_method=5088,metric_groups_recalculated=12,adaptive_past_only_checks=checked,prior_issued_forecasts_unchanged=True,shadow_rows=288,shadow_outcomes_absent_at_issue=True,new_variants_prospective_scored_days=0,platform_ready=False)
(R/'docs/verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
