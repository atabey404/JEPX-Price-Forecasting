from pathlib import Path
import json,hashlib,sys
import numpy as np,pandas as pd
from threadpoolctl import threadpool_limits
from core_model import fit_predict,load_prices,csvout
R=Path(__file__).resolve().parents[1];W=R.parent/'stability_work';P1=W/'JEPX_Model_Experiment_01';P2=W/'JEPX_Model_Experiment_02';P3=W/'JEPX_Model_Experiment_03'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert not (R/'docs/shadow_registry.json').exists(), 'Immutable issued snapshot: run a new experiment in a clean directory'
plan=json.loads((R/'docs/research_plan.json').read_text());spec=json.loads((P3/'docs/frozen_candidate.json').read_text());receipt=json.loads((P3/'docs/new_price_receipt.json').read_text());src=P3/receipt['path'];assert sha(src)==receipt['sha256'];prices=load_prices(src)
keys=['datetime_jst','delivery_date','time_slot','area'];a=pd.read_csv(P1/'data/rolling_predictions_30min.csv.gz');b=pd.read_csv(P2/'data/processed/new_date_predictions.csv.gz');b.method=b.method.replace({'frozen_hgb_raw':'hgb_core'});a=pd.concat([a[a.method.isin(['hgb_core','previous_day'])],b[b.method.isin(['hgb_core','previous_day'])]],ignore_index=True)
fills=[]
with threadpool_limits(limits=2):
 for area in ['Tokyo','Kansai','Kyushu']:
  day=pd.Timestamp('2026-11-10',tz='Asia/Tokyo');idx,x,raw,_=fit_predict(prices,area,day,spec)
  for method,pred in [('hgb_core',raw),('previous_day',x.price_lag_1d.to_numpy())]:fills.append(pd.DataFrame(dict(datetime_jst=idx.astype(str),delivery_date=str(day.date()),time_slot=x.time_slot.to_numpy(),area=area,method=method,actual=prices[area].reindex(idx).to_numpy(),prediction=pred)))
a=pd.concat([a,*fills],ignore_index=True)
oldentries=[json.loads(x) for x in (P3/'docs/forward_registry.jsonl').read_text().splitlines()];e=next(x for x in oldentries if x['delivery_date']=='2026-11-11');assert sha(P3/e['file'])==e['sha256'];f=pd.read_csv(P3/e['file'])
for method,col in [('hgb_core','prediction_raw_jpy_kwh'),('previous_day','baseline_previous_day_jpy_kwh')]:
 q=f[keys].copy();q['method']=method;q['prediction']=f[col];q['actual']=[prices.loc[pd.Timestamp(t),area] for t,area in zip(q.datetime_jst,q.area)];a=pd.concat([a,q],ignore_index=True)
assert not a.duplicated(keys+['method']).any();assert a.groupby(keys).actual.nunique().max()==1
v=a.pivot(index=keys+['actual'],columns='method',values='prediction').reset_index().rename(columns={'hgb_core':'raw_candidate','previous_day':'baseline'});v['date']=pd.to_datetime(v.delivery_date);assert v[['raw_candidate','baseline']].notna().all().all();assert len(v)==134*3*48
rows=[];weights=[]
for area,g in v.groupby('area'):
 for day,h in g.groupby('date',sort=True):
  past=g[(g.date<day)&(g.date>=day-pd.Timedelta(days=28))];losses=[]
  if past.date.nunique()>=14:
   for w in plan['parameters']['adaptive_grid']:
    y=np.maximum(past.baseline+w*(past.raw_candidate-past.baseline),.01);losses.append((float(np.abs(y-past.actual).mean()),w))
   minloss=min(t[0] for t in losses);weight=min(w for loss,w in losses if loss<=minloss+1e-12)
  else:weight=.5
  weights.append(dict(area=area,delivery_date=str(day.date()),weight=weight,prior_days=past.date.nunique(),prior_last=str(past.date.max().date()) if len(past) else None,prior_first=str(past.date.min().date()) if len(past) else None))
  for method,w in [('previous_day',0),('hgb_core_guarded',1),('shrink_50',.5),('adaptive_28d',weight)]:
   q=h[keys+['actual','baseline','raw_candidate']].copy();q['method']=method;q['weight']=w;q['prediction']=np.maximum(h.baseline+w*(h.raw_candidate-h.baseline),.01);q['error']=q.prediction-q.actual;q['abs_error']=q.error.abs();rows.append(q)
d=pd.concat(rows,ignore_index=True);csvout(d,R/'data/predictions.csv.gz');csvout(pd.DataFrame(weights),R/'data/weight_audit.csv');csvout(v.drop(columns='date'),R/'data/source_prediction_panel.csv.gz')
common=d[d.delivery_date>='2026-07-29'].copy();common['month']=common.delivery_date.str[:7]
def summarize(p,groups):
 out=[]
 for k,g in p.groupby(groups):
  if not isinstance(k,tuple):k=(k,)
  daily=g.groupby('delivery_date').abs_error.mean();out.append(dict(zip(groups,k))|dict(n=len(g),days=g.delivery_date.nunique(),MAE=g.abs_error.mean(),bias=g.error.mean(),RMSE=np.sqrt((g.error**2).mean()),daily_MAE_p90=daily.quantile(.9),worst_daily_MAE=daily.max()))
 return pd.DataFrame(out)
m=summarize(common,['area','method']);csvout(m,R/'data/metrics_overall.csv');csvout(summarize(common,['area','month','method']),R/'data/metrics_monthly.csv');daily=summarize(common,['area','delivery_date','method']);csvout(daily,R/'data/metrics_daily.csv');csvout(summarize(common[common.delivery_date<='2026-11-06'],['area','method']),R/'data/old_archive_metrics.csv');csvout(summarize(common[common.delivery_date>='2026-11-07'],['area','method']),R/'data/known_november_diagnostics.csv')
print(m.to_string(index=False));print('Monthly');print(pd.read_csv(R/'data/metrics_monthly.csv').pivot(index=['area','month'],columns='method',values='MAE').to_string())
# Paired day-level block bootstrap, descriptive only: selected specs use already-known historical outcomes.
rng=np.random.default_rng(42);cis=[]
for area in common.area.unique():
 a=daily[daily.area==area].pivot(index='delivery_date',columns='method',values='MAE').sort_index();n=len(a)
 starts=rng.integers(0,n,size=(2000,int(np.ceil(n/7))));ix=((starts[:,:,None]+np.arange(7))%n).reshape(2000,-1)[:,:n]
 for method in ['hgb_core_guarded','shrink_50','adaptive_28d']:
  diff=(a.previous_day-a[method]).to_numpy();boot=diff[ix].mean(axis=1);cis.append(dict(area=area,method=method,mean_MAE_advantage_vs_baseline=diff.mean(),ci_low=np.quantile(boot,.025),ci_high=np.quantile(boot,.975),daily_win_rate=float((diff>0).mean()),status='exploratory_descriptive_not_confirmatory'))
csvout(pd.DataFrame(cis),R/'data/descriptive_bootstrap.csv')
# Issue additional forecasts for the same future delivery date; keep prior version and both new variants.
entry=next(x for x in oldentries if x['delivery_date']=='2026-11-12');assert sha(P3/entry['file'])==entry['sha256'];future=pd.read_csv(P3/entry['file']);cutoff=pd.Timestamp(entry['bid_cutoff_jst']);now=pd.Timestamp.now(tz='UTC');assert now<cutoff;assert '2026-11-12' not in set(prices.delivery_date);assert not (R/'docs/shadow_registry.json').exists()
shadows=[];nextweights=[]
for area,h in future.groupby('area'):
 g=v[(v.area==area)&(v.date>=pd.Timestamp('2026-11-12')-pd.Timedelta(days=28))&(v.date<pd.Timestamp('2026-11-12'))];assert g.date.nunique()==28;ls=[(float(np.abs(np.maximum(g.baseline+w*(g.raw_candidate-g.baseline),.01)-g.actual).mean()),w) for w in plan['parameters']['adaptive_grid']];best=min(x[0] for x in ls);wa=min(w for loss,w in ls if loss<=best+1e-12);nextweights.append(dict(area=area,weight=wa,history_first=g.delivery_date.min(),history_last=g.delivery_date.max(),days=28))
 for method,w in [('shrink_50',.5),('adaptive_28d',wa)]:
  q=h[keys].copy();q['method']=method;q['weight']=w;q['baseline']=h.baseline_previous_day_jpy_kwh;q['raw_candidate']=h.prediction_raw_jpy_kwh;q['prediction']=np.maximum(q.baseline+w*(q.raw_candidate-q.baseline),.01);shadows.append(q)
s=pd.concat(shadows,ignore_index=True);issued=pd.Timestamp.now(tz='UTC');assert issued<cutoff;s['issued_at_utc']=issued.isoformat();s['bid_cutoff_jst']=str(cutoff);fp=R/'data'/f'shadow_20261112_{issued.strftime("%Y%m%dT%H%M%SZ")}.csv';csvout(s,fp)
registry=dict(issued_at_utc=issued.isoformat(),delivery_date='2026-11-12',file=str(fp.relative_to(R)),sha256=sha(fp),bid_cutoff_jst=str(cutoff),rows=len(s),methods=['shrink_50','adaptive_28d'],prior_original_forecast_sha256=entry['sha256'],prior_original_forecast_file=entry['file'],source_receipt_sha256=receipt['sha256'],research_plan_sha256=sha(R/'docs/research_plan.json'),outcome_available_at_issue=False,additional_variants_not_replacement=True,completed_prospective_days_for_new_variants=0,next_adaptive_weights=nextweights)
(R/'docs/shadow_registry.json').write_text(json.dumps(registry,indent=2));print('Next weights',nextweights)
source_info=dict(original_archives={p.name:sha(p) for p in (R.parent/'stability_inputs').glob('*.zip')},price_receipt=receipt,original_spec=spec,old_registry=oldentries);(R/'docs/source_provenance.json').write_text(json.dumps(source_info,indent=2))
