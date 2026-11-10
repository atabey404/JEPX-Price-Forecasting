"""Replay lower-bound guard, evaluate frozen specs on new archive dates, and issue an unpriced-day research forecast."""
import os
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ.setdefault(k,'2')
from pathlib import Path
import argparse,json,hashlib,datetime,gzip,csv,io
import numpy as np,pandas as pd,joblib
from sklearn.ensemble import HistGradientBoostingRegressor
from threadpoolctl import threadpool_limits
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

AREAS=['Tokyo','Kansai','Kyushu'];POSITIONS={'Tokyo':8,'Kansai':11,'Kyushu':14};FLOOR=.01
R=Path(__file__).resolve().parents[1]

def csvout(df,p):
 b=df.to_csv(index=False).encode('utf-8-sig');p.write_bytes(gzip.compress(b,mtime=0,compresslevel=6) if str(p).endswith('.gz') else b)

def load_prices(p):
 rows=list(csv.reader(io.StringIO(p.read_bytes().decode('cp932'))));header=rows[0]
 assert '東京' in header[8] and '関西' in header[11] and '九州' in header[14]
 out=[]
 for x in rows[1:]:
  if not x or not x[0]:continue
  day=pd.Timestamp(x[0]);slot=int(x[1]);assert 1<=slot<=48;dt=day.tz_localize('Asia/Tokyo')+pd.Timedelta(minutes=30*(slot-1));out.append({'datetime_jst':dt,'delivery_date':str(day.date()),'time_slot':slot}|{a:float(x[pos]) for a,pos in POSITIONS.items()})
 d=pd.DataFrame(out).set_index('datetime_jst').sort_index();assert d.index.is_unique and d[AREAS].notna().all().all();assert (d.groupby('delivery_date').size()==48).all();assert (d[AREAS]>=FLOOR).all().all();return d

def features(s,idx):
 lag={i:s.reindex(idx-pd.Timedelta(days=i)).to_numpy() for i in range(1,29)}
 d=pd.DataFrame({'price_lag_1d':lag[1],'price_lag_7d':lag[7],'price_same_slot_mean_4weeks':np.mean(np.column_stack([lag[x] for x in [7,14,21,28]]),axis=1),'price_same_slot_median_7days':np.median(np.column_stack([lag[x] for x in range(1,8)]),axis=1)},index=idx)
 d['time_slot']=idx.hour*2+idx.minute//30+1;d['hour']=idx.hour;d['minute']=idx.minute;d['weekday']=idx.weekday;d['is_weekend']=(idx.weekday>=5).astype(int);d['month']=idx.month;d['slot_sin']=np.sin(2*np.pi*(d.time_slot-1)/48);d['slot_cos']=np.cos(2*np.pi*(d.time_slot-1)/48);assert d.notna().all().all();return d

def summarize(d,groups):
 out=[]
 for keys,g in d.groupby(groups,sort=False):
  if not isinstance(keys,tuple):keys=(keys,)
  e=g.prediction-g.actual;out.append(dict(zip(groups,keys))|dict(n=len(g),days=g.delivery_date.nunique(),MAE=float(e.abs().mean()),RMSE=float(np.sqrt((e**2).mean())),bias=float(e.mean()),below_floor=int((g.prediction<FLOOR).sum())))
 return pd.DataFrame(out)

def fit_predict(prices,area,day,freeze):
 idx=pd.date_range(day,day+pd.Timedelta(days=1)-pd.Timedelta(minutes=30),freq='30min');train_idx=pd.date_range(day-pd.Timedelta(days=84),day-pd.Timedelta(minutes=30),freq='30min')
 X=features(prices[area],train_idx);y=prices[area].reindex(train_idx)-X.price_lag_1d;assert len(X)==4032 and y.notna().all();te=features(prices[area],idx);cols=freeze['features']
 model=HistGradientBoostingRegressor(**freeze['estimator']);model.fit(X[cols],y.to_numpy());raw=model.predict(te[cols])+te.price_lag_1d.to_numpy();return idx,te,raw,model

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--experiment1-root',type=Path,default=R.parent/'JEPX_Model_Experiment_01');ap.add_argument('--stage4-root',type=Path,default=R.parent/'JEPX_Step4');ap.add_argument('--issue-forward',action='store_true');args=ap.parse_args()
 if args.issue_forward and (R/'docs/forward_registry.jsonl').exists():
  raise RuntimeError('An issued forecast already exists in this snapshot. Use a new run directory; never overwrite issued forecasts.')
 freeze=json.loads((R/'docs/frozen_candidate.json').read_text());receipt=json.loads((R/'docs/new_price_receipt.json').read_text());raw_path=R/receipt['path'];prices=load_prices(raw_path);csvout(prices.reset_index(),R/'data/processed/fresh_price_30min.csv.gz')
 old=pd.read_csv(args.experiment1_root/'data/rolling_predictions_30min.csv.gz');old['guarded']=np.maximum(old.prediction,FLOOR);assert (np.abs(old.guarded-old.actual)<=np.abs(old.prediction-old.actual)+1e-12).all()
 affected=old[old.prediction<FLOOR];csvout(affected,R/'data/processed/old_affected_predictions.csv');variants=[]
 for variant,col in [('raw','prediction'),('floor_guard','guarded')]:
  p=old.drop(columns=['prediction']).rename(columns={col:'prediction'}) if variant=='floor_guard' else old.copy();p['variant']=variant;variants.append(p)
 csvout(summarize(pd.concat(variants),['area','method','variant']),R/'data/processed/boundary_guard_metrics.csv')
 # Check whether the new source revised the previously retained target prices.
 master=pd.read_csv(args.stage4_root/'data/master_research_30min.csv.gz');master['datetime_jst']=pd.to_datetime(master.datetime_jst,utc=True).dt.tz_convert('Asia/Tokyo');revision=[];feature_checks=[]
 for area in AREAS:
  a=master[master.area==area];current=prices[area].reindex(pd.DatetimeIndex(a.datetime_jst)).to_numpy();diff=current-a.target_area_price_jpy_kwh.to_numpy();changed=np.abs(diff)>1e-9
  revision.append(dict(area=area,overlap_rows=len(a),changed_target_prices=int(changed.sum()),max_abs_change=float(np.abs(diff).max())))
  ix=pd.DatetimeIndex(a[a.delivery_date=='2026-10-15'].datetime_jst);new=features(prices[area],ix);old_features=a[a.delivery_date=='2026-10-15'][freeze['features']].to_numpy();same=bool(np.allclose(new[freeze['features']].to_numpy(),old_features,rtol=0,atol=1e-9));feature_checks.append(dict(area=area,reference_day='2026-10-15',features_match_stage4=same))
 csvout(pd.DataFrame(revision),R/'data/processed/revision_audit.csv')
 new_preds=[];audit=[]
 with threadpool_limits(limits=2):
  for day in pd.date_range(freeze['new_date_evaluation'][0],freeze['new_date_evaluation'][1],tz='Asia/Tokyo'):
   assert str(day.date()) in set(prices.delivery_date)
   for area in AREAS:
    idx,te,raw,model=fit_predict(prices,area,day,freeze);actual=prices[area].reindex(idx).to_numpy()
    for method,values in [('previous_day',te.price_lag_1d.to_numpy()),('seven_day_median',te.price_same_slot_median_7days.to_numpy()),('frozen_hgb_raw',raw),('frozen_hgb_guarded',np.maximum(raw,FLOOR))]:
     new_preds.append(pd.DataFrame(dict(datetime_jst=idx,delivery_date=str(day.date()),area=area,time_slot=te.time_slot.to_numpy(),method=method,actual=actual,prediction=values,evaluation_type='retrospective_new_archive_dates')))
    audit.append(dict(area=area,delivery_date=str(day.date()),train_first=str((day-pd.Timedelta(days=84)).date()),train_last=str((day-pd.Timedelta(days=1)).date()),train_rows=4032,forecast_rows=48))
 result=pd.concat(new_preds,ignore_index=True);assert len(result)==3*3*48*4;csvout(result,R/'data/processed/new_date_predictions.csv.gz');csvout(summarize(result,['area','method']),R/'data/processed/new_date_metrics.csv');csvout(summarize(result,['delivery_date','area','method']),R/'data/processed/new_date_metrics_daily.csv');csvout(pd.DataFrame(audit),R/'data/processed/new_training_audit.csv')
 # Actual receipt evidence is sufficient for a newly issued core-only forecast, but cannot reconstruct old first-availability times.
 latest=pd.Timestamp(prices.delivery_date.max(),tz='Asia/Tokyo');target=latest+pd.Timedelta(days=1);deadline=target-pd.Timedelta(days=1)+pd.Timedelta(hours=10);now=pd.Timestamp.now(tz='UTC').tz_convert('Asia/Tokyo');received=pd.Timestamp(receipt['retrieved_at_utc']).tz_convert('Asia/Tokyo')
 eligibility=dict(latest_price_delivery_date=str(latest.date()),next_unpriced_delivery_date=str(target.date()),bid_cutoff_jst=str(deadline),checked_at_jst=str(now),source_received_at_jst=str(received),source_receipt_before_cutoff=bool(received<deadline),current_time_before_cutoff=bool(now<deadline),target_price_absent=bool(str(target.date()) not in set(prices.delivery_date)),weather_used=False)
 (R/'docs/forward_eligibility.json').write_text(json.dumps(eligibility,indent=2))
 forward_status='not_requested';issued_file=None
 if args.issue_forward:
  assert received<=now<deadline,'Cannot issue a pre-cutoff forecast now';assert eligibility['target_price_absent']
  forward=[];input_frames=[]
  with threadpool_limits(limits=2):
   for area in AREAS:
    idx,te,raw,model=fit_predict(prices,area,target,freeze)
    forward.append(pd.DataFrame(dict(datetime_jst=idx,delivery_date=str(target.date()),area=area,time_slot=te.time_slot.to_numpy(),prediction_raw_jpy_kwh=raw,prediction_jpy_kwh=np.maximum(raw,FLOOR),baseline_previous_day_jpy_kwh=te.price_lag_1d.to_numpy(),baseline_seven_day_median_jpy_kwh=te.price_same_slot_median_7days.to_numpy(),model_id='hgb_core_84d_floor001_v1')))
    x=te.reset_index(names='datetime_jst');x['area']=area;input_frames.append(x)
    joblib.dump(dict(estimator=model,features=freeze['features'],offset='price_lag_1d',lower_guard=FLOOR,trained_through=str(latest.date()),forecast_delivery_date=str(target.date()),research_only=True),R/'models'/f'{area.lower()}_forward_{target.strftime("%Y%m%d")}.joblib')
  issued=pd.Timestamp.now(tz='UTC');assert issued.tz_convert('Asia/Tokyo')<deadline
  filename=f'forward_{target.strftime("%Y%m%d")}_{issued.strftime("%Y%m%dT%H%M%SZ")}.csv';issued_file=R/'data/processed'/filename;assert not issued_file.exists();f=pd.concat(forward,ignore_index=True);f['issued_at_utc']=issued.isoformat();f['bid_cutoff_jst']=str(deadline);csvout(f,issued_file);csvout(pd.concat(input_frames),R/'data/processed/forward_features.csv.gz')
  entry=dict(forecast_id=filename.removesuffix('.csv'),file=str(issued_file.relative_to(R)),sha256=hashlib.sha256(issued_file.read_bytes()).hexdigest(),issued_at_utc=issued.isoformat(),delivery_date=str(target.date()),bid_cutoff_jst=str(deadline),source_receipt_sha256=receipt['sha256'],source_received_at_utc=receipt['retrieved_at_utc'],frozen_spec_sha256=hashlib.sha256((R/'docs/frozen_candidate.json').read_bytes()).hexdigest(),rows=len(f),areas=AREAS,forecast_type='pre-auction_research_prediction',input_receipt_verified_before_cutoff=True,outcome_known_at_issue=False,weather_used=False,evaluated=False,price_policy='research lower guard 0.01; no upper clipping')
  registry=R/'docs/forward_registry.jsonl'
  if registry.exists():assert filename not in registry.read_text()
  with registry.open('a') as fp:fp.write(json.dumps(entry)+'\n')
  forward_status='issued_before_auction_cutoff'
  fig,axes=plt.subplots(3,1,figsize=(11,7),sharex=True)
  for ax,area in zip(axes,AREAS):
   a=f[f.area==area];ax.plot(a.time_slot,a.prediction_jpy_kwh,label='Frozen candidate',color='#217a8b');ax.plot(a.time_slot,a.baseline_previous_day_jpy_kwh,label='Previous-day baseline',color='#9aa5b1',ls='--');ax.set_ylabel(area+'\nJPY/kWh');ax.grid(alpha=.2)
  axes[0].legend();axes[-1].set_xlabel('Half-hour slot (1 = 00:00–00:30 JST)');fig.suptitle('Unpriced delivery day: '+str(target.date())+' | research forecast, no outcomes yet');fig.tight_layout();fig.savefig(R/'figures/forward_forecast.png',dpi=160);plt.close(fig)
 validation=dict(status='passed_with_research_limitations',old_raw_negative_count=int((old.prediction<0).sum()),old_predictions_below_floor=int((old.prediction<FLOOR).sum()),old_guarded_negative_count=0,new_date_rows=len(result),new_date_days=3,new_date_type='retrospective_new_archive_dates_not_prospective',source_revisions=revision,feature_reconstruction_checks=feature_checks,frozen_parameters_unchanged=True,future_date_outcome_absent_at_issue=eligibility['target_price_absent'],forward_status=forward_status,forward_file=str(issued_file.relative_to(R)) if issued_file else None,completed_prospective_days=0,platform_ready=False)
 (R/'docs/validation.json').write_text(json.dumps(validation,indent=2));print(summarize(result,['area','method']).to_string(index=False));print(json.dumps(validation,indent=2))

if __name__=='__main__':main()
