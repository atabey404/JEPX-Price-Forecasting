from pathlib import Path
import json,datetime,gzip,hashlib
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'docs/weather_download_manifest.json').read_text());errors=[x for x in manifest if 'error'in x]
selections=json.loads((ROOT/'docs/forecast_gap_selections.json').read_text());resolved={x['delivery_date']:x for x in selections if x.get('resolved')}
assert all(x['kind']=='forecast' and x['name'] in resolved for x in errors),errors
for r in [x for x in manifest if 'error' not in x]+list(resolved.values()):
 if 'selected_file' in r:r=r|{'path':r['selected_file']}
 b=gzip.decompress((ROOT/r['path']).read_bytes());assert hashlib.sha256(b).hexdigest()==r['uncompressed_sha256']
q=[]
for kind in ['reanalysis','forecast']:
 df=pd.read_csv(ROOT/f'data/processed/weather_{kind}_hourly.csv.gz');dt=pd.to_datetime(df.valid_time_jst,utc=True).dt.tz_convert('Asia/Tokyo');df['dt']=dt
 keys=['point_id','valid_time_jst']+(['delivery_date'] if kind=='forecast' else [])
 assert not df.duplicated(keys).any()
 if kind=='forecast':
  target=df[df.target_day_hour];days=pd.date_range('2026-04-04','2026-11-06');assert len(target)==len(days)*9*24
  assert (target.groupby(['delivery_date','point_id']).size()==24).all()
  assert not df.strict_availability_verified.any()
  assert df.eligible_under_12h_lag_assumption.all()
  runs=pd.to_datetime(df.run_initialization_time_jst,utc=True);cutoffs=pd.to_datetime(df.bid_cutoff_jst,utc=True);assert ((cutoffs-runs).dt.total_seconds()/3600==13+24*df.extra_lag_days).all()
 else:
  expected=len(pd.date_range('2016-04-01','2026-10-31 23:00',freq='h'));assert len(df)==expected*9
  assert (df.groupby('point_id').size()==expected).all()
  for p,g in df.groupby('point_id'):assert (g.dt.sort_values().diff().dropna()==pd.Timedelta(hours=1)).all()
 variables=['temperature_2m','relative_humidity_2m','wind_speed_10m','wind_speed_100m','shortwave_radiation','cloud_cover','precipitation']
 if kind=='forecast':assert not df[variables].isna().any().any()
 else:
  missing=df[df[variables].isna().any(axis=1)]
  assert (missing.dt>=pd.Timestamp('2026-10-31',tz='Asia/Tokyo')).all()
  assert len(missing)<=135
 assert df.relative_humidity_2m.dropna().between(0,100).all();assert (df.wind_speed_10m.dropna()>=0).all();assert (df.wind_speed_100m.dropna()>=0).all()
 q.append(dict(kind=kind,rows=len(df),points=int(df.point_id.nunique()),start=str(dt.min()),end=str(dt.max()),missing_cells=int(df[variables].isna().sum().sum()),incomplete_rows=int(df[variables].isna().any(axis=1).sum())))
audit=pd.read_csv(ROOT/'docs/forecast_publication_audit.csv');assert len(audit)==93;assert not audit.strict_backtest_eligible.any();assert (audit.groupby('area').size()==31).all()
research=pd.read_csv(ROOT/'data/processed/tso_forecasts_research_only_202610.csv');assert len(research)==4464
out=dict(weather=q,unavailable_original_runs=[x['name'] for x in errors],earlier_run_substitutions=[{'delivery_date':x['delivery_date'],'extra_lag_days':x['extra_lag_days']} for x in resolved.values()],weather_requests=len(manifest),forecast_daily_batches=sum(x['kind']=='forecast' for x in manifest),tso_audited_files=93,tso_rows=4464,strict_tso_eligible_files=0,status='passed; weather historical API first-availability remains unverified; 12h lag is an explicit assumption')
(ROOT/'docs/validation_results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False,indent=2))
