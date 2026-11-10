"""Verify exported metrics, train/predict separation, and saved estimator replay."""
from pathlib import Path
import argparse,json,math,gzip
import numpy as np,pandas as pd,joblib
from threadpoolctl import threadpool_limits
R=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--stage4-root',type=Path,default=R.parent/'JEPX_Step4');args=ap.parse_args()
p=pd.read_csv(R/'data/rolling_predictions_30min.csv.gz');a=pd.read_csv(R/'data/training_audit.csv');m=pd.read_csv(R/'data/metrics_overall.csv');d=pd.read_csv(args.stage4_root/'data/master_research_30min.csv.gz');d['day']=pd.to_datetime(d.delivery_date)
assert len(p)==111456 and p.notna().all().all();assert not p.duplicated(['area','method','datetime_jst']).any();assert (p.groupby(['area','method','delivery_date']).size()==48).all();assert len(a)==387
assert (pd.to_datetime(a.train_end)<pd.to_datetime(a.delivery_date)).all();assert (a.train_rows==4032).all();assert (a.predict_rows==48).all()
for _,r in m.iterrows():
 g=p[(p.area==r.area)&(p.method==r.method)];e=[float(x)-float(y) for x,y in zip(g.prediction,g.actual)];assert len(e)==6192;assert abs(sum(abs(x) for x in e)/len(e)-r.MAE)<1e-10;assert abs(math.sqrt(sum(x*x for x in e)/len(e))-r.RMSE)<1e-10
with threadpool_limits(limits=2):
 for file in (R/'models').glob('*.joblib'):
  obj=joblib.load(file);area=file.name.split('_')[0].capitalize();method=file.stem[len(area)+1:];te=d[(d.area==area)&(d.delivery_date==obj['last_evaluated_delivery_date'])].sort_values('time_slot');cols=obj['feature_columns'];actual_prediction=obj['estimator'].predict(te[cols])+te.price_lag_1d.to_numpy();saved=p[(p.area==area)&(p.method==method)&(p.delivery_date==obj['last_evaluated_delivery_date'])].sort_values('time_slot').prediction.to_numpy();assert np.allclose(actual_prediction,saved,rtol=0,atol=1e-10)
  assert not any(c.startswith('target_') for c in cols)
  if method.startswith('ridge'):
   tr=d[(d.area==area)&(d.day<pd.Timestamp('2026-11-06'))&(d.day>=pd.Timestamp('2026-11-06')-pd.Timedelta(days=84))];nums=[x for x in cols if x not in ['time_slot','weekday','month']];mean=obj['estimator'].named_steps['preprocess'].named_transformers_['num'].mean_;assert np.allclose(mean,tr[nums].mean().to_numpy())
for file in (R/'data').glob('*.gz'):gzip.decompress(file.read_bytes())
checks=dict(status='passed',independent_MAE_RMSE_groups=len(m),saved_estimator_replay_models=12,training_label_and_prediction_date_separation=True,ridge_scaler_training_mean_check=True,negative_predictions_preserved=int((p.prediction<0).sum()),model_stability_claim=False)
(R/'docs/independent_verification.json').write_text(json.dumps(checks,indent=2));print(json.dumps(checks,indent=2))
