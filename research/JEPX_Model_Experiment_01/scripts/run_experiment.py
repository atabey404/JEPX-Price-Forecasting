"""Fixed-spec rolling residual regression and paired weather ablation.
Retrospective evaluation only; the previously examined July-November period is reused.
"""
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ.setdefault(key,'2')
from pathlib import Path
import argparse,json,hashlib,time,gzip
import numpy as np,pandas as pd,joblib,sklearn
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler,OneHotEncoder
from threadpoolctl import threadpool_limits
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

AREAS=['Tokyo','Kansai','Kyushu'];START='2026-07-01';END='2026-11-06';WINDOW=84
MODELS=['ridge_core','ridge_weather','hgb_core','hgb_weather']

def csvout(df,path):
 b=df.to_csv(index=False).encode('utf-8-sig');path.write_bytes(gzip.compress(b,mtime=0,compresslevel=6) if str(path).endswith('.gz') else b)

def estimator(kind,cols):
 if kind=='ridge':
  cats=['time_slot','weekday','month'];nums=[x for x in cols if x not in cats]
  prep=ColumnTransformer([('num',StandardScaler(),nums),('cat',OneHotEncoder(categories=[list(range(1,49)),list(range(7)),list(range(1,13))],handle_unknown='ignore',sparse_output=False),cats)])
  return Pipeline([('preprocess',prep),('model',Ridge(alpha=100.0))])
 return HistGradientBoostingRegressor(loss='absolute_error',learning_rate=.05,max_iter=60,max_leaf_nodes=7,min_samples_leaf=48,l2_regularization=10,early_stopping=False,random_state=42)

def summarize(df,groups):
 rows=[]
 for keys,g in df.groupby(groups,sort=False):
  if not isinstance(keys,tuple):keys=(keys,)
  e=g.prediction-g.actual;den=g.actual.abs().sum()
  rows.append(dict(zip(groups,keys))|dict(n=len(g),days=g.delivery_date.nunique(),MAE=float(e.abs().mean()),RMSE=float(np.sqrt((e**2).mean())),bias=float(e.mean()),WAPE_pct=float(e.abs().sum()/den*100),negative_predictions=int((g.prediction<0).sum())))
 return pd.DataFrame(rows)

def block_ci(values,seed=20261109):
 values=np.asarray(values);n=len(values);rng=np.random.default_rng(seed);starts=rng.integers(0,n,size=(3000,(n+6)//7));indices=(starts[:,:,None]+np.arange(7))%n;idx=indices.reshape(3000,-1)[:,:n];boot=values[idx].mean(axis=1);return [float(x) for x in np.quantile(boot,[.025,.975])]

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--stage4-root',type=Path,default=Path(__file__).resolve().parents[2]/'JEPX_Step4');ap.add_argument('--output-root',type=Path,default=Path(__file__).resolve().parents[1]);args=ap.parse_args();r=args.output_root
 for x in ['data','docs','figures','models']:(r/x).mkdir(parents=True,exist_ok=True)
 source=args.stage4_root/'data/master_research_30min.csv.gz';d=pd.read_csv(source);contract=json.loads((args.stage4_root/'docs/data_contract.json').read_text());d['day']=pd.to_datetime(d.delivery_date);d=d.sort_values(['area','day','time_slot']);core=contract['core_feature_allowlist'];weather=contract['feature_allowlist'];assert not any(x.startswith('target_') for x in weather)
 spec=dict(created_before_scoring=True,areas=AREAS,period=[START,END],training_window_days=WINDOW,daily_refit=True,target='target area price minus previous-day same-slot price',algorithms=dict(ridge=dict(alpha=100,scaling='fit on each training window only',categoricals=['time_slot','weekday','month']),hgb=dict(loss='absolute_error',learning_rate=.05,max_iter=60,max_leaf_nodes=7,min_samples_leaf=48,l2_regularization=10,early_stopping=False,random_state=42)),core_features=core,weather_features=weather,training_labels='prior delivery-day auction prices, already cleared under Stage4 timing assumptions',postprocessing='none; negative predictions retained and counted',selection_policy='fixed algorithms/parameters; no search or tuning using the evaluation period',limitations=['July-November baseline period was already inspected in Stage4; this is reused retrospective evaluation, not untouched prospective testing','12h weather availability assumption; historical first-availability unverified','No holiday table, regional pre-auction demand/renewable forecasts, interconnectors, outages or fuel features'],gates=dict(model_candidate='at least 5% MAE reduction versus previous-day in every area',weather_increment='at least 5% MAE gain in >=2 areas, no area degrades >2%, and paired 95% block-bootstrap upper bound <0 in every area',monthly_stability='at least 3 of 4 full months improve versus previous-day in every area',deployment='also requires verified source timing and 30 consecutive prospective delivery days; retrospective results alone cannot open platform deployment gate'))
 (r/'docs/experiment_spec.json').write_text(json.dumps(spec,indent=2));preds=[];audit=[];start=time.time();probe_errors=[]
 with threadpool_limits(limits=2):
  for area in AREAS:
   a=d[d.area==area].copy();dates=pd.date_range(START,END,freq='D')
   for n,day in enumerate(dates,1):
    tr=a[(a.day<day)&(a.day>=day-pd.Timedelta(days=WINDOW))];te=a[a.day==day];assert len(tr)==WINDOW*48 and len(te)==48
    cutoff=pd.Timestamp(day,tz='Asia/Tokyo')-pd.Timedelta(days=1)+pd.Timedelta(hours=10)
    assert (pd.to_datetime(tr.assumed_available_time_jst,utc=True)<cutoff).all();assert (pd.to_datetime(te.assumed_available_time_jst,utc=True)<cutoff).all()
    label_availability=tr.day.max().tz_localize('Asia/Tokyo')-pd.Timedelta(days=1)+pd.Timedelta(hours=12);assert label_availability<cutoff
    y=(tr.target_area_price_jpy_kwh-tr.price_lag_1d).to_numpy()
    for method in MODELS:
     kind,featureset=method.split('_');cols=weather if featureset=='weather' else core;model=estimator(kind,cols);model.fit(tr[cols],y);pr=model.predict(te[cols])+te.price_lag_1d.to_numpy()
     if n==1:
      # Predict with a radically changed target label and prove it cannot enter the allowlisted inputs.
      mutated=te.copy();mutated['target_area_price_jpy_kwh']=99999;mutated['target_system_price_jpy_kwh']=-99999
      assert np.array_equal(model.predict(te[cols]),model.predict(mutated[cols]))
     p=te[['datetime_jst','delivery_date','time_slot']].copy();p['area']=area;p['method']=method;p['actual']=te.target_area_price_jpy_kwh.to_numpy();p['prediction']=pr;preds.append(p)
     if n==len(dates):joblib.dump(dict(estimator=model,feature_columns=cols,prediction_offset='price_lag_1d',trained_until=str(tr.day.max().date()),last_evaluated_delivery_date=END,research_only=True),r/'models'/f'{area.lower()}_{method}.joblib')
    for method,col in [('previous_day','price_lag_1d'),('seven_day_median','price_same_slot_median_7days')]:
     p=te[['datetime_jst','delivery_date','time_slot']].copy();p['area']=area;p['method']=method;p['actual']=te.target_area_price_jpy_kwh.to_numpy();p['prediction']=te[col].to_numpy();preds.append(p)
    audit.append(dict(area=area,delivery_date=str(day.date()),train_start=str(tr.day.min().date()),train_end=str(tr.day.max().date()),train_days=tr.day.nunique(),train_rows=len(tr),predict_rows=len(te),latest_label_assumed_available=str(label_availability),bid_cutoff=str(cutoff)))
    if n%20==0 or n==len(dates):
     csvout(pd.concat(preds,ignore_index=True),r/'data/predictions_checkpoint.csv.gz');print(area,n,'/',len(dates),'elapsed_s',round(time.time()-start),flush=True)
 result=pd.concat(preds,ignore_index=True);assert len(result)==129*48*3*6 and not result.duplicated(['area','method','datetime_jst']).any();assert not result.isna().any().any()
 overall=summarize(result,['area','method']);monthly=summarize(result.assign(month=result.delivery_date.str[:7]),['area','month','method']);daily=summarize(result,['area','delivery_date','method'])
 comparisons=[]
 for area in AREAS:
  a=overall[overall.area==area].set_index('method');dd=daily[daily.area==area].pivot(index='delivery_date',columns='method',values='MAE')
  for algo in ['ridge','hgb']:
   c=algo+'_core';w=algo+'_weather';delta=dd[w]-dd[c];ci=block_ci(delta)
   full=monthly[(monthly.area==area)&(monthly.month.isin(['2026-07','2026-08','2026-09','2026-10']))].pivot(index='month',columns='method',values='MAE')
   comparisons.append(dict(area=area,algorithm=algo,core_MAE=a.loc[c,'MAE'],weather_MAE=a.loc[w,'MAE'],weather_gain_pct=(1-a.loc[w,'MAE']/a.loc[c,'MAE'])*100,weather_vs_previous_day_gain_pct=(1-a.loc[w,'MAE']/a.loc['previous_day','MAE'])*100,paired_daily_mean_delta=float(delta.mean()),paired_delta_CI_low=ci[0],paired_delta_CI_high=ci[1],weather_daily_win_rate_pct=float((delta<0).mean()*100),full_months_beating_previous_day=int((full[w]<full['previous_day']).sum()),full_months_weather_beating_core=int((full[w]<full[c]).sum())))
 cmp=pd.DataFrame(comparisons);gate={}
 for algo,g in cmp.groupby('algorithm'):
  candidate=bool((g.weather_vs_previous_day_gain_pct>=5).all());gain=bool((g.weather_gain_pct>=5).sum()>=2 and (g.weather_gain_pct>=-2).all() and (g.paired_delta_CI_high<0).all());stable=bool((g.full_months_beating_previous_day>=3).all());gate[algo]=dict(retrospective_candidate_gate=candidate,weather_increment_gate=gain,monthly_stability_gate=stable,retrospective_all_gates_passed=candidate and gain and stable,platform_ready=False)
 csvout(result,r/'data/rolling_predictions_30min.csv.gz');csvout(overall,r/'data/metrics_overall.csv');csvout(monthly,r/'data/metrics_monthly.csv');csvout(daily,r/'data/metrics_daily.csv');csvout(cmp,r/'data/weather_ablation.csv');csvout(pd.DataFrame(audit),r/'data/training_audit.csv')
 validations=dict(status='computed_with_documented_availability_assumptions',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),sklearn_version=sklearn.__version__,prediction_rows=len(result),daily_fits=129*3*4,training_rows_per_fit=4032,test_rows_per_fit=48,parameter_search=False,scalers_fit_on_training_only=True,early_stopping=False,target_label_perturbation_invariance=True,all_temporal_order_checks_passed=True,strict_weather_availability_verified=False,prospective_evaluation_completed=False,negative_prediction_count=int((result.prediction<0).sum()),gates=gate)
 (r/'docs/validation.json').write_text(json.dumps(validations,indent=2))
 colors=['#385574','#8c9aaa','#3870a6','#6ab2ce','#d08c32','#4a9a78'];order=['previous_day','seven_day_median']+MODELS
 fig,axes=plt.subplots(1,3,figsize=(12,4.6),sharey=True)
 for ax,area in zip(axes,AREAS):
  vals=overall[overall.area==area].set_index('method').loc[order,'MAE'];ax.bar(range(6),vals,color=colors);ax.set_title(area,fontweight='bold');ax.set_xticks(range(6),['Day -1','7-day\nmedian','Ridge\ncore','Ridge\nweather','HGB\ncore','HGB\nweather'],rotation=30,ha='right');ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
  for i,v in enumerate(vals):ax.text(i,v+.03,f'{v:.2f}',ha='center',fontsize=8)
 axes[0].set_ylabel('MAE (JPY/kWh)');fig.suptitle('Daily refit | 84-day window | 2026-07-01 to 2026-11-06',fontweight='bold');fig.text(.5,.01,'Same 129 days and 6,192 half-hours per area. Weather availability uses an unverified 12-hour lag assumption.',ha='center',fontsize=8);fig.tight_layout(rect=[0,.04,1,.94]);fig.savefig(r/'figures/model_comparison_mae.png',dpi=170);plt.close(fig)
 fig,axes=plt.subplots(1,3,figsize=(12,3.9),sharey=True)
 for ax,area in zip(axes,AREAS):
  a=cmp[cmp.area==area];x=np.arange(2);means=a.paired_daily_mean_delta.to_numpy();err=np.vstack([means-a.paired_delta_CI_low.to_numpy(),a.paired_delta_CI_high.to_numpy()-means]);ax.errorbar(x,means,yerr=err,fmt='o',capsize=6,color='#367d91');ax.axhline(0,color='gray',ls='--');ax.set_xticks(x,['Ridge','HGB']);ax.set_xlim(-.5,1.5);ax.set_title(area);ax.grid(axis='y',alpha=.2)
 axes[0].set_ylabel('Weather minus core daily MAE (JPY/kWh)');fig.suptitle('Weather increment | 95% circular 7-day block bootstrap intervals');fig.text(.5,.01,'Below zero favors weather. 3,000 resamples; conditional on this reused retrospective period.',ha='center',fontsize=8);fig.tight_layout(rect=[0,.04,1,.94]);fig.savefig(r/'figures/weather_increment_ci.png',dpi=170);plt.close(fig)
 print(overall.to_string(index=False));print(cmp.to_string(index=False));print(json.dumps(validations,indent=2))

if __name__=='__main__':main()
