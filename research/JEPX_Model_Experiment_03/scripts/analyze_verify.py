"""Independently score issued predictions and verify the next frozen-model forecast."""
from pathlib import Path
import json,hashlib,gzip
import pandas as pd,numpy as np,joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from advance_candidate import load_prices,csvout
R=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
receipt=json.loads((R/'docs/new_price_receipt.json').read_text());src=R/receipt['path'];assert sha(src)==receipt['sha256'];prices=load_prices(src);spec=json.loads((R/'docs/frozen_candidate.json').read_text());entries=[json.loads(x) for x in (R/'docs/forward_registry.jsonl').read_text().splitlines()]
assert len(entries)==2;metrics=[];details=[];replays=0
for entry in entries:
 p=R/entry['file'];assert sha(p)==entry['sha256'];f=pd.read_csv(p);assert len(f)==144 and not f.duplicated(['area','time_slot']).any();assert (f.groupby('area').size()==48).all();assert (f.prediction_jpy_kwh>=.01).all();assert pd.Timestamp(entry['source_received_at_utc'])<=pd.Timestamp(entry['issued_at_utc'])<pd.Timestamp(entry['bid_cutoff_jst']);assert sha(R/'docs/frozen_candidate.json')==entry['frozen_spec_sha256']
 if entry['delivery_date'] in set(prices.delivery_date):
  for area,a in f.groupby('area'):
   idx=pd.DatetimeIndex(pd.to_datetime(a.datetime_jst,utc=True)).tz_convert('Asia/Tokyo');actual=prices[area].reindex(idx).to_numpy();err=a.prediction_jpy_kwh.to_numpy()-actual;base=a.baseline_previous_day_jpy_kwh.to_numpy()-actual;med=a.baseline_seven_day_median_jpy_kwh.to_numpy()-actual
   metrics.append(dict(area=area,n=48,candidate_MAE=np.abs(err).mean(),previous_day_MAE=np.abs(base).mean(),seven_day_median_MAE=np.abs(med).mean(),candidate_bias=err.mean(),gain_vs_previous_day_pct=(1-np.abs(err).mean()/np.abs(base).mean())*100,better_than_previous_day_slots=int((np.abs(err)<np.abs(base)).sum())))
   d=a.copy();d['actual']=actual;d['candidate_error']=err;d['previous_day_error']=base;d['absolute_error']=np.abs(err);d['absolute_error_difference_vs_previous_day']=np.abs(err)-np.abs(base);d['hour']=idx.hour;d['period']=np.select([idx.hour<6,idx.hour<12,idx.hour<18],['00-06','06-12','12-18'],default='18-24');details.append(d)
 else:
  x=pd.read_csv(R/entry['features_file'])
  for area,a in f.groupby('area'):
   z=x[x.area==area];model=joblib.load(R/'models'/f'{area.lower()}_forward_20261112.joblib');raw=model['estimator'].predict(z[spec['features']])+z.price_lag_1d.to_numpy();assert np.allclose(raw,a.prediction_raw_jpy_kwh,rtol=0,atol=1e-10);assert np.allclose(np.maximum(raw,.01),a.prediction_jpy_kwh,rtol=0,atol=1e-10);replays+=1
m=pd.DataFrame(metrics);d=pd.concat(details,ignore_index=True);csvout(m,R/'data/processed/first_forward_metrics.csv');csvout(d,R/'data/processed/first_forward_details.csv');csvout(d.groupby(['area','period'],as_index=False).agg(candidate_MAE=('absolute_error','mean'),mean_excess_absolute_error_vs_day1=('absolute_error_difference_vs_previous_day','mean')),R/'data/processed/period_diagnostics.csv');csvout(d.sort_values('absolute_error',ascending=False).groupby('area',sort=False).head(5),R/'data/processed/top_errors.csv')
for row in m.itertuples():
 s=pd.read_csv(next((R/'data/processed').glob('forward_scores_*.csv')));v=s[(s.area==row.area)&(s.method=='issued_candidate')].MAE.iloc[0];assert abs(v-row.candidate_MAE)<1e-10
fig,axes=plt.subplots(3,1,figsize=(11,8),sharex=True)
for ax,area in zip(axes,['Tokyo','Kansai','Kyushu']):
 a=d[d.area==area];ax.plot(a.time_slot,a.actual,label='Published day-ahead price',color='#233343',lw=2);ax.plot(a.time_slot,a.prediction_jpy_kwh,label='Issued candidate',color='#128d93',lw=1.8);ax.plot(a.time_slot,a.baseline_previous_day_jpy_kwh,label='Issued previous-day baseline',color='#b9966a',ls='--',alpha=.85);ax.set_ylabel(area+'\nJPY/kWh');ax.grid(alpha=.17);ax.spines[['top','right']].set_visible(False)
axes[0].legend(ncol=3,fontsize=9,frameon=False);axes[-1].set_xlabel('Half-hour slot (JST)');fig.suptitle('First prospective check: delivery 11 November 2026\nForecast issued 9 November; scored after auction publication on 10 November');fig.tight_layout();fig.savefig(R/'figures/first_forward_check.png',dpi=160);plt.close(fig)
validation=dict(status='passed',prior_forecast_hash_unchanged=True,completed_prospective_delivery_days=1,completed_physical_delivery_days=0,scored_slots=144,scored_method_area_groups=9,new_forecast_rows=144,new_forecast_models_replayed=replays,new_target_absent=True,next_delivery_date=entries[-1]['delivery_date'],same_frozen_spec=True,platform_ready=False)
assert entries[-1]['delivery_date'] not in set(prices.delivery_date);assert replays==3
(R/'docs/validation.json').write_text(json.dumps(validation,indent=2));print(m.to_string(index=False));print(pd.read_csv(R/'data/processed/period_diagnostics.csv').to_string(index=False));print(json.dumps(validation))
