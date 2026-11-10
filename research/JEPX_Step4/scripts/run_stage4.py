"""Build a point-in-time research master and evaluate predeclared price-only baselines.
No target-day actuals, ERA5, current auction volumes, or fitted price model are inputs.
"""
from pathlib import Path
import argparse, json, hashlib, gzip, csv, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

AREAS=['Tokyo','Kansai','Kyushu']
VARIABLES=['temperature_2m','relative_humidity_2m','wind_speed_10m','wind_speed_100m','cloud_cover','shortwave_radiation','precipitation']
METHODS=['previous_day','previous_week','four_week_same_slot_mean','seven_day_same_slot_median']
START='2026-04-04'; END='2026-11-06'; HOLDOUT='2026-07-01'

def write_csv(df,path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    b=df.to_csv(index=False).encode('utf-8-sig')
    path.write_bytes(gzip.compress(b,compresslevel=6,mtime=0) if path.name.endswith('.gz') else b)

def price_features(series,idx):
    lag={i:series.reindex(idx-pd.Timedelta(days=i)).to_numpy() for i in range(1,29)}
    return pd.DataFrame({'price_lag_1d':lag[1],'price_lag_7d':lag[7],
        'price_same_slot_mean_4weeks':np.mean(np.column_stack([lag[x] for x in [7,14,21,28]]),axis=1),
        'price_same_slot_median_7days':np.median(np.column_stack([lag[x] for x in range(1,8)]),axis=1)},index=idx)

def weather_features(weather,area,idx):
    pieces=[];mapping={}; instant=VARIABLES[:5]
    for pos,point in enumerate(sorted(weather.loc[weather.area==area,'point_id'].unique()),1):
        mapping[f'p{pos}']=point
    days=pd.date_range(START,END,tz='Asia/Tokyo',freq='D')
    for day in days:
        ds=str(day.date());g=weather[(weather.area==area)&(weather.delivery_date==ds)]
        ix=idx[(idx>=day)&(idx<day+pd.Timedelta(days=1))]
        assert len(ix)==48
        part=pd.DataFrame(index=ix)
        for prefix,point in mapping.items():
            h=g[g.point_id==point].sort_values('valid_time_jst').set_index('valid_time_jst')
            assert len(h)==25 and h.index.is_unique
            hr=ix.floor('h');next_hr=hr+pd.Timedelta(hours=1);weight=(ix.minute.to_numpy()/60)
            for var in instant:
                v0=h[var].reindex(hr).to_numpy();v1=h[var].reindex(next_hr).to_numpy()
                part[f'weather_{prefix}_{var}']=v0+(v1-v0)*weight
            # These are source-hour quantities, repeated as known covariates for both half-hours.
            part[f'weather_{prefix}_shortwave_radiation_hour_mean']=h.shortwave_radiation.reindex(next_hr).to_numpy()
            part[f'weather_{prefix}_precipitation_hour_total']=h.precipitation.reindex(next_hr).to_numpy()
        for c in ['run_initialization_time_jst','assumed_available_time_jst','bid_cutoff_jst','extra_lag_days','strict_availability_verified']:
            assert g[c].nunique()==1;part[c]=g[c].iloc[0]
        pieces.append(part)
    result=pd.concat(pieces).sort_index()
    assert result.filter(like='weather_').notna().all().all()
    return result,mapping

def metrics(df,group_cols):
    rows=[]
    for key,g in df.groupby(group_cols,sort=False):
        if not isinstance(key,tuple):key=(key,)
        e=g.prediction_jpy_kwh-g.actual_jpy_kwh
        rows.append(dict(zip(group_cols,key))|dict(n=len(g),days=g.delivery_date.nunique(),MAE=float(e.abs().mean()),RMSE=float(np.sqrt((e**2).mean())),bias=float(e.mean()),median_AE=float(e.abs().median())))
    return pd.DataFrame(rows)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input-root',type=Path,default=Path(__file__).resolve().parents[2]);ap.add_argument('--output-root',type=Path,default=Path(__file__).resolve().parents[1]);args=ap.parse_args();r=args.output_root
    for d in ['data','docs','figures']:(r/d).mkdir(parents=True,exist_ok=True)
    price_path=args.input_root/'JEPX_Project/data/processed/price_30min.csv'
    weather_path=args.input_root/'JEPX_Step3/data/processed/weather_forecast_hourly.csv.gz'
    prices=pd.read_csv(price_path);prices['datetime_jst']=pd.to_datetime(prices.datetime_jst,utc=True).dt.tz_convert('Asia/Tokyo');prices=prices.set_index('datetime_jst').sort_index();assert prices.index.is_unique
    w=pd.read_csv(weather_path)
    for c in ['valid_time_jst','run_initialization_time_jst','assumed_available_time_jst','bid_cutoff_jst']:w[c]=pd.to_datetime(w[c],utc=True).dt.tz_convert('Asia/Tokyo')
    idx=pd.date_range(START,END+' 23:30',tz='Asia/Tokyo',freq='30min');dates=idx.strftime('%Y-%m-%d');cutoffs=idx.normalize()-pd.Timedelta(days=1)+pd.Timedelta(hours=10)
    core=[];weather_parts=[];targets=[];all_preds=[];mappings={};feature_lists={};tests={}
    for area in AREAS+['System']:
        series=prices['system_price_jpy_kwh' if area=='System' else area.lower()+'_price_jpy_kwh']
        pf=price_features(series,idx);assert pf.notna().all().all()
        actual=series.reindex(idx).to_numpy();assert not np.isnan(actual).any()
        preds=pd.DataFrame({'datetime_jst':idx,'delivery_date':dates,'target':area,'actual_jpy_kwh':actual})
        for method,col in zip(METHODS,pf.columns):
            pp=preds.copy();pp['method']=method;pp['prediction_jpy_kwh']=pf[col].to_numpy();pp['evaluation_segment']=np.where(pp.delivery_date<HOLDOUT,'development','holdout');all_preds.append(pp)
        # A real perturbation check: changes to the target day and later must not alter its predictors.
        probe=pd.Timestamp('2026-08-15',tz='Asia/Tokyo');probe_idx=idx[(idx>=probe)&(idx<probe+pd.Timedelta(days=1))]
        changed=series.copy();changed.loc[changed.index>=probe]=99999
        assert np.array_equal(price_features(series,probe_idx).to_numpy(),price_features(changed,probe_idx).to_numpy())
        if area=='System':continue
        c=pf.reset_index(names='datetime_jst');c['area']=area;c['delivery_date']=dates;c['time_slot']=idx.hour*2+idx.minute//30+1;c['hour']=idx.hour;c['minute']=idx.minute;c['weekday']=idx.weekday;c['is_weekend']=(idx.weekday>=5).astype(int);c['month']=idx.month;c['slot_sin']=np.sin(2*np.pi*(c.time_slot-1)/48);c['slot_cos']=np.cos(2*np.pi*(c.time_slot-1)/48);c['bid_cutoff_jst']=cutoffs
        c['latest_price_input_delivery_date']=(idx.normalize()-pd.Timedelta(days=1)).strftime('%Y-%m-%d');c['latest_price_assumed_available_at_jst']=idx.normalize()-pd.Timedelta(days=2)+pd.Timedelta(hours=12)
        assert (c.latest_price_assumed_available_at_jst<c.bid_cutoff_jst).all()
        wf,mapping=weather_features(w,area,idx);mappings[area]=mapping;wf=wf.reset_index(names='datetime_jst');wf['area']=area
        assert (wf.assumed_available_time_jst<wf.bid_cutoff_jst).all();assert (~wf.strict_availability_verified).all()
        assert (wf.run_initialization_time_jst<wf.assumed_available_time_jst).all()
        wf=wf.drop(columns=['bid_cutoff_jst']);core.append(c);weather_parts.append(wf)
        targets.append(pd.DataFrame({'datetime_jst':idx,'area':area,'delivery_date':dates,'time_slot':c.time_slot,'target_area_price_jpy_kwh':actual,'target_system_price_jpy_kwh':prices.system_price_jpy_kwh.reindex(idx).to_numpy()}))
    cf=pd.concat(core,ignore_index=True);wf=pd.concat(weather_parts,ignore_index=True);labels=pd.concat(targets,ignore_index=True)
    features=cf.merge(wf,on=['datetime_jst','area'],validate='one_to_one');master=features.merge(labels.drop(columns=['delivery_date','time_slot']),on=['datetime_jst','area'],validate='one_to_one')
    assert len(master)==217*48*3 and not master.duplicated(['area','datetime_jst']).any()
    assert (master.groupby(['area','delivery_date']).size()==48).all();assert not master.isna().any().any()
    price_cols=list(price_features(prices.tokyo_price_jpy_kwh,idx).columns);calendar_cols=['time_slot','hour','minute','weekday','is_weekend','month','slot_sin','slot_cos'];weather_cols=[c for c in features if c.startswith('weather_p')]
    allowed=price_cols+calendar_cols+weather_cols
    assert not any(any(s in c for s in ['target_','actual','volume','era5']) for c in allowed)
    # Independent spot checks for both instantaneous interpolation and hour-ending radiation.
    one=master[(master.area=='Tokyo')&(master.datetime_jst==pd.Timestamp('2026-08-15 12:30',tz='Asia/Tokyo'))].iloc[0];p=mappings['Tokyo']['p1'];h=w[(w.area=='Tokyo')&(w.point_id==p)&(w.delivery_date=='2026-08-15')].set_index('valid_time_jst')
    a=pd.Timestamp('2026-08-15 12:00',tz='Asia/Tokyo');b=a+pd.Timedelta(hours=1)
    assert np.isclose(one.weather_p1_temperature_2m,(h.loc[a,'temperature_2m']+h.loc[b,'temperature_2m'])/2)
    assert one.weather_p1_shortwave_radiation_hour_mean==h.loc[b,'shortwave_radiation']
    pred=pd.concat(all_preds,ignore_index=True);assert len(pred)==217*48*4*4
    overall=metrics(pred,['target','method']);seg=metrics(pred,['evaluation_segment','target','method']);monthly=metrics(pred.assign(month=pred.delivery_date.str[:7]),['month','target','method']);daily=metrics(pred,['delivery_date','target','method'])
    # Cross-check a consequential metric using scalar arithmetic independent of the aggregation helper.
    check=pred[(pred.target=='Tokyo')&(pred.method=='previous_day')&(pred.evaluation_segment=='holdout')]
    manual=sum(abs(float(a)-float(b)) for a,b in zip(check.prediction_jpy_kwh,check.actual_jpy_kwh))/len(check)
    reported=seg[(seg.target=='Tokyo')&(seg.method=='previous_day')&(seg.evaluation_segment=='holdout')].MAE.iloc[0];assert abs(manual-reported)<1e-10
    for name,df in [('features_core_30min.csv.gz',cf),('features_weather_30min.csv.gz',features),('targets_30min.csv.gz',labels),('master_research_30min.csv.gz',master),('baseline_predictions_30min.csv.gz',pred),('baseline_metrics_all.csv',overall),('baseline_metrics_segments.csv',seg),('baseline_metrics_monthly.csv',monthly),('baseline_metrics_daily.csv',daily)]:write_csv(df,r/'data'/name)
    contract=dict(snapshot_inputs='2026-11-05 archives; no new remote data downloaded',coverage=dict(start=START,end=END,days=217,areas=AREAS,master_rows=len(master)),feature_allowlist=allowed,core_feature_allowlist=price_cols+calendar_cols,targets=['target_area_price_jpy_kwh','target_system_price_jpy_kwh'],weather_point_mapping=mappings,weather_assumption='12h processing/publication lag; historical first-server availability unverified',price_assumption='prior delivery-day auction prices assumed available by preceding 12:00 JST; historical revisions not reconstructed',weather_alignment=dict(instantaneous='linear interpolation at :30 from the same run; exact value at :00',radiation='hour-ending t+1 source average repeated for both target half-hours [t,t+1)',precipitation='hour-ending t+1 source total as covariate; not a half-hour rainfall total'),holiday_feature='not included; no authoritative holiday table joined in this version',evaluation=dict(development=[START,'2026-06-30'],holdout=[HOLDOUT,END],methods=METHODS,note='predeclared deterministic price-only baselines; no method selected or tuned on holdout; later dates may use prior known auction prices'),system_weather='not assembled; regional points are not a nationwide weather proxy')
    (r/'docs/data_contract.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2))
    tests=dict(status='passed_with_documented_availability_assumptions',source_price_rows=len(prices),source_weather_rows=len(w),master_rows=len(master),baseline_prediction_rows=len(pred),duplicate_master_keys=0,missing_master_cells=0,days=217,slots_per_area_day=48,weather_points_per_area=3,complete_holdout_days=129,future_price_perturbation_invariance=True,weather_temporal_order_check=True,weather_radiation_alignment_spot_check=True,independent_MAE_recalculation=True,strict_weather_availability_verified=False,weather_assumption='12h lag',source_sha256={str(p.relative_to(args.input_root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [price_path,weather_path]})
    (r/'docs/validation.json').write_text(json.dumps(tests,indent=2))
    # Exact four-method comparisons, all on the same holdout rows.
    colors=['#2463a5','#38a195','#e7a23b','#8d6bb1'];fig,axes=plt.subplots(1,4,figsize=(13,4.4),sharey=True)
    for ax,target in zip(axes,['System']+AREAS):
        v=seg[(seg.evaluation_segment=='holdout')&(seg.target==target)].set_index('method').loc[METHODS]
        ax.bar(range(4),v.MAE,color=colors);ax.set_title(target,fontweight='bold');ax.set_xticks(range(4),['Day -1','Week -1','4-week\nmean','7-day\nmedian'],rotation=25,ha='right');ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
        for i,x in enumerate(v.MAE):ax.text(i,x+.035,f'{x:.2f}',ha='center',fontsize=9)
    axes[0].set_ylabel('MAE (JPY/kWh)');fig.suptitle('Price-only baselines | Holdout: 2026-07-01 to 2026-11-06',fontweight='bold');fig.text(.5,.01,'129 delivery days per target; 48 half-hours/day; lower is better. No weather-based price model evaluated.',ha='center',fontsize=9);fig.tight_layout(rect=[0,.04,1,.94]);fig.savefig(r/'figures/baseline_holdout_mae.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(3,1,figsize=(11,7.5),sharex=True)
    for ax,target in zip(axes,AREAS):
        for method,color in zip(METHODS,colors):
            d=monthly[(monthly.target==target)&(monthly.method==method)];ax.plot(d.month,d.MAE,label=method,color=color,marker='o',ms=3)
        ax.set_ylabel(target+'\nMAE (JPY/kWh)');ax.grid(alpha=.2)
    axes[0].legend(ncol=2,fontsize=8);axes[-1].set_xlabel('Delivery month (April and November are partial months)');fig.suptitle('Monthly baseline errors | identical evaluation coverage per method');fig.tight_layout();fig.savefig(r/'figures/baseline_monthly_mae.png',dpi=160);plt.close(fig)
    print(seg[seg.evaluation_segment=='holdout'].to_string(index=False));print(json.dumps(tests,indent=2))

if __name__=='__main__':main()
