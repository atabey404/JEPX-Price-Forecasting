from pathlib import Path
import argparse,json,hashlib,gzip,math
import pandas as pd,numpy as np,joblib
from advance_candidate import load_prices,FLOOR
from threadpoolctl import threadpool_limits
R=Path(__file__).resolve().parents[1]
receipt=json.loads((R/'docs/new_price_receipt.json').read_text());raw=R/receipt['path'];assert hashlib.sha256(raw.read_bytes()).hexdigest()==receipt['sha256'];prices=load_prices(raw)
p=pd.read_csv(R/'data/processed/new_date_predictions.csv.gz');m=pd.read_csv(R/'data/processed/new_date_metrics.csv');assert len(p)==1728 and not p.duplicated(['area','method','datetime_jst']).any()
for _,r in m.iterrows():
 g=p[(p.area==r.area)&(p.method==r.method)];err=[abs(float(x)-float(y)) for x,y in zip(g.prediction,g.actual)];assert len(err)==144;assert abs(sum(err)/144-r.MAE)<1e-10
assert (p[p.method=='frozen_hgb_guarded'].prediction>=FLOOR).all()
old=pd.read_csv(R/'data/processed/old_affected_predictions.csv');assert len(old)==99 and (old.guarded>=FLOOR).all()
entries=[json.loads(x) for x in (R/'docs/forward_registry.jsonl').read_text().splitlines() if x.strip()];assert len(entries)==1;e=entries[0];fp=R/e['file'];assert hashlib.sha256(fp.read_bytes()).hexdigest()==e['sha256'];f=pd.read_csv(fp);assert len(f)==144 and not f.duplicated(['area','time_slot']).any();assert (f.groupby('area').size()==48).all();assert e['delivery_date'] not in set(prices.delivery_date)
assert pd.Timestamp(e['source_received_at_utc'])<=pd.Timestamp(e['issued_at_utc'])<pd.Timestamp(e['bid_cutoff_jst'])
freeze=json.loads((R/'docs/frozen_candidate.json').read_text());assert pd.Timestamp(freeze['frozen_at_utc'])<pd.Timestamp(receipt['retrieved_at_utc']);assert e['frozen_spec_sha256']==hashlib.sha256((R/'docs/frozen_candidate.json').read_bytes()).hexdigest()
features=pd.read_csv(R/'data/processed/forward_features.csv.gz')
with threadpool_limits(limits=2):
 for area,g in f.groupby('area'):
  g=g.sort_values('time_slot');x=features[features.area==area].sort_values('time_slot');obj=joblib.load(R/'models'/f'{area.lower()}_forward_{e["delivery_date"].replace("-","")}.joblib');pred=obj['estimator'].predict(x[obj['features']])+x.price_lag_1d.to_numpy();assert np.allclose(pred,g.prediction_raw_jpy_kwh,rtol=0,atol=1e-10);assert np.allclose(np.maximum(pred,FLOOR),g.prediction_jpy_kwh,rtol=0,atol=1e-10)
checks=dict(status='passed',new_date_metric_groups_verified=len(m),new_date_rows=len(p),forecast_rows=len(f),forecast_estimator_replay_models=3,source_receipt_before_issue_before_cutoff=True,forward_target_absent_from_source=True,prior_parameter_freeze_verified=True,forecast_sha256=e['sha256'],prospective_outcomes_evaluated=False,completed_prospective_delivery_days=0)
(R/'docs/independent_verification.json').write_text(json.dumps(checks,indent=2));print(json.dumps(checks,indent=2))
