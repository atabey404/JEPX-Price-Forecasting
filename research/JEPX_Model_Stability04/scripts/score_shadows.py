"""Score all immutable new variants and the original issued forecast together."""
from pathlib import Path
import argparse,json,hashlib,datetime,zipfile
import numpy as np,pandas as pd
from core_model import load_prices
R=Path(__file__).resolve().parents[1];ap=argparse.ArgumentParser();ap.add_argument('--price-csv',type=Path,required=True);args=ap.parse_args();r=json.loads((R/'docs/shadow_registry.json').read_text());p=R/r['file'];assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'];prices=load_prices(args.price_csv)
if r['delivery_date'] not in set(prices.delivery_date):print('PENDING',r['delivery_date']);raise SystemExit(0)
s=pd.read_csv(p);archive=R/'inputs/JEPX_Model_Experiment03_20261110.zip'
with zipfile.ZipFile(archive) as z:b=z.read('JEPX_Model_Experiment_03/'+r['prior_original_forecast_file'])
assert hashlib.sha256(b).hexdigest()==r['prior_original_forecast_sha256'];import io
original=pd.read_csv(io.BytesIO(b));rows=[]
for method,col in [('original_hgb','prediction_jpy_kwh'),('previous_day','baseline_previous_day_jpy_kwh'),('seven_day_median','baseline_seven_day_median_jpy_kwh')]:
 f=original[['datetime_jst','delivery_date','area','time_slot']].copy();f['method']=method;f['prediction']=original[col];rows.append(f)
s=pd.concat([s,*rows],ignore_index=True);result=[]
for (area,method),a in s.groupby(['area','method']):
 assert len(a)==48 and a.time_slot.nunique()==48;actual=prices[area].reindex(pd.DatetimeIndex(pd.to_datetime(a.datetime_jst,utc=True)).tz_convert('Asia/Tokyo')).to_numpy();assert np.isfinite(actual).all();e=a.prediction-actual;result.append(dict(area=area,method=method,delivery_date=r['delivery_date'],n=48,MAE=float(e.abs().mean()),bias=float(e.mean()),RMSE=float(np.sqrt((e**2).mean()))))
t=datetime.datetime.now(datetime.timezone.utc);out=R/'data'/('shadow_scores_'+t.strftime('%Y%m%dT%H%M%SZ')+'.csv');assert not out.exists();pd.DataFrame(result).to_csv(out,index=False);out.with_suffix('.json').write_text(json.dumps(dict(scored_at_utc=t.isoformat(),outcome_source_sha256=hashlib.sha256(args.price_csv.read_bytes()).hexdigest(),forecast_sha256=r['sha256'],all_variants_reported=True,forecast_files_unchanged=True),indent=2));print(pd.DataFrame(result).to_string(index=False))
