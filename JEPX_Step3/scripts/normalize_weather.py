import json,gzip,datetime
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'data/processed';OUT.mkdir(parents=True,exist_ok=True)
points=json.loads((ROOT/'docs/weather_points.json').read_text())
selection_path=ROOT/'docs/forecast_gap_selections.json'
selections={x['delivery_date']:x for x in json.loads(selection_path.read_text()) if x.get('resolved')} if selection_path.exists() else {}
variables=['temperature_2m','relative_humidity_2m','wind_speed_10m','wind_speed_100m','shortwave_radiation','cloud_cover','precipitation']
checks=[];forecasts=[];reanalysis=[];grid=[]
for kind,target in [('forecast',forecasts),('reanalysis',reanalysis)]:
 paths=list((ROOT/'data/raw/weather'/kind).glob('*.json.gz'))
 if kind=='forecast':paths += [ROOT/x['original_file'] for x in selections.values() if not (ROOT/x['original_file']).exists()]
 for p in sorted(paths):
  selected=selections.get(p.name[:10],{}) if kind=='forecast' else {}
  actual_path=ROOT/selected['selected_file'] if selected else p
  docs=json.loads(gzip.decompress(actual_path.read_bytes()));assert len(docs)==len(points)
  for point,j in zip(points,docs):
   df=pd.DataFrame(j['hourly']);df=df.rename(columns={'time':'valid_time_jst'});df['valid_time_jst']=pd.to_datetime(df.valid_time_jst).dt.tz_localize('Asia/Tokyo')
   df['area']=point['area'];df['point_id']=point['point_id'];df['source_file']=str(actual_path.relative_to(ROOT));df['requested_latitude']=point['latitude'];df['requested_longitude']=point['longitude'];df['grid_latitude']=j['latitude'];df['grid_longitude']=j['longitude']
   df['weather_resolution_minutes']=60
   if kind=='forecast':
    delivery=p.name[:10];run=pd.Timestamp(delivery,tz='Asia/Tokyo')-pd.Timedelta(days=2+selected.get('extra_lag_days',0))+pd.Timedelta(hours=21);cutoff=pd.Timestamp(delivery,tz='Asia/Tokyo')-pd.Timedelta(days=1)+pd.Timedelta(hours=10)
    # Include 00:00 next day so the last target hour's radiation (hour-ending) can be used separately.
    valid=(df.valid_time_jst>=pd.Timestamp(delivery,tz='Asia/Tokyo'))&(df.valid_time_jst<=pd.Timestamp(delivery,tz='Asia/Tokyo')+pd.Timedelta(days=1))
    df=df[valid].copy();df['delivery_date']=delivery;df['extra_lag_days']=selected.get('extra_lag_days',0);df['run_initialization_time_jst']=run;df['bid_cutoff_jst']=cutoff;df['assumed_available_time_jst']=run+pd.Timedelta(hours=12);df['availability_status']='assumed_12h_processing_lag_not_historical_server_receipt';df['eligible_under_12h_lag_assumption']=df.assumed_available_time_jst<cutoff;df['strict_availability_verified']=False;df['model']='gfs_global';df['lead_time_hours']=(df.valid_time_jst-run).dt.total_seconds()/3600;df['target_day_hour']=df.valid_time_jst.dt.strftime('%Y-%m-%d')==delivery
   else:df['model']='era5';df['data_kind']='reanalysis_reference_only'
   checks.append(dict(kind=kind,file=p.name,source_file=str(actual_path.relative_to(ROOT)),point_id=point['point_id'],rows=len(df),missing={v:int(df[v].isna().sum()) for v in variables}))
   df['is_complete_weather_row']=df[variables].notna().all(axis=1)
   target.append(df)
  if p.name==sorted(x.name for x in (ROOT/'data/raw/weather'/kind).glob('*.json.gz'))[0]:
   for point,j in zip(points,docs):grid.append(point|{'model':('gfs_global' if kind=='forecast' else 'era5'),'returned_latitude':j['latitude'],'returned_longitude':j['longitude'],'elevation':j['elevation'],'units':j['hourly_units']})
for kind,parts in [('forecast',forecasts),('reanalysis',reanalysis)]:
 df=pd.concat(parts,ignore_index=True).sort_values(['point_id','valid_time_jst']);df.to_csv(OUT/f'weather_{kind}_hourly.csv.gz',index=False,encoding='utf-8-sig')
 keys=['point_id','valid_time_jst']+(['delivery_date'] if kind=='forecast' else [])
 assert not df.duplicated(keys).any()
 if kind=='forecast':assert df.eligible_under_12h_lag_assumption.all()
 else:df.loc[~df.is_complete_weather_row,['point_id','valid_time_jst']+variables].to_csv(ROOT/'docs/reanalysis_incomplete_rows.csv',index=False,encoding='utf-8-sig')
 summary=dict(kind=kind,rows=len(df),start=str(df.valid_time_jst.min()),end=str(df.valid_time_jst.max()),point_count=int(df.point_id.nunique()),missing={v:int(df[v].isna().sum()) for v in variables},duplicate_keys=int(df.duplicated(keys).sum()))
 (ROOT/'docs'/f'{kind}_quality_summary.json').write_text(json.dumps(summary,indent=2))
 if kind=='forecast':
  counts=df[df.target_day_hour].groupby(['delivery_date','point_id']).size();assert (counts==24).all();assert not df[variables].isna().any().any()
  # One row per target hour and region, retaining individual point columns rather than inventing weighted regional weather.
  d=df[df.target_day_hour].copy();wide=d.pivot(index=['delivery_date','valid_time_jst','area','run_initialization_time_jst','bid_cutoff_jst','assumed_available_time_jst','extra_lag_days','availability_status','eligible_under_12h_lag_assumption','strict_availability_verified','weather_resolution_minutes'],columns='point_id',values=variables);wide.columns=[a+'__'+b for a,b in wide.columns];wide.reset_index().to_csv(OUT/'weather_forecast_features_hourly.csv.gz',index=False,encoding='utf-8-sig')
  calendar_columns=['delivery_date','run_initialization_time_jst','bid_cutoff_jst','assumed_available_time_jst','extra_lag_days','availability_status','eligible_under_12h_lag_assumption','strict_availability_verified']
  d[calendar_columns].drop_duplicates().sort_values('delivery_date').to_csv(OUT/'forecast_delivery_calendar.csv',index=False,encoding='utf-8-sig')
  for area,area_df in wide.reset_index().groupby('area'):
   area_df.dropna(axis=1,how='all').to_csv(OUT/f'{area.lower()}_weather_forecast_features_hourly.csv.gz',index=False,encoding='utf-8-sig')
 print(summary,flush=True)
(ROOT/'docs/weather_quality_by_file_point.json').write_text(json.dumps(checks,indent=2));(ROOT/'docs/weather_grids.json').write_text(json.dumps(grid,indent=2))
