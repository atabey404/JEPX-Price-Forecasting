"""Score an immutable issued forecast only after a newly supplied official price file contains its outcomes."""
from pathlib import Path
import argparse,json,hashlib,datetime
import numpy as np,pandas as pd
from advance_candidate import load_prices,summarize
R=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--price-csv',type=Path,required=True);ap.add_argument('--forecast-id');args=ap.parse_args()
entries=[json.loads(x) for x in (R/'docs/forward_registry.jsonl').read_text().splitlines() if x.strip()]
if args.forecast_id:entries=[e for e in entries if e['forecast_id']==args.forecast_id]
assert entries,'No matching retained forecast'
prices=load_prices(args.price_csv);scores=[]
for e in entries:
 p=R/e['file'];assert hashlib.sha256(p.read_bytes()).hexdigest()==e['sha256'],'Forecast changed since issue'
 if e['delivery_date'] not in set(prices.delivery_date):print('PENDING',e['forecast_id']);continue
 assert pd.Timestamp(e['issued_at_utc'])<pd.Timestamp(e['bid_cutoff_jst'])
 f=pd.read_csv(p);f['dt']=pd.to_datetime(f.datetime_jst,utc=True).dt.tz_convert('Asia/Tokyo');parts=[]
 for area,a in f.groupby('area'):
  actual=prices[area].reindex(pd.DatetimeIndex(a.dt)).to_numpy();assert len(actual)==48 and np.isfinite(actual).all()
  for method,col in [('issued_candidate','prediction_jpy_kwh'),('issued_previous_day','baseline_previous_day_jpy_kwh'),('issued_seven_day_median','baseline_seven_day_median_jpy_kwh')]:parts.append(pd.DataFrame(dict(area=area,delivery_date=e['delivery_date'],actual=actual,prediction=a[col].to_numpy(),method=method)))
 result=summarize(pd.concat(parts),['area','method']);result['forecast_id']=e['forecast_id'];scores.append(result)
if scores:
 out=pd.concat(scores,ignore_index=True);name='forward_scores_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ');p=R/'data/processed'/(name+'.csv');assert not p.exists();out.to_csv(p,index=False,encoding='utf-8-sig');(R/'docs'/(name+'.json')).write_text(json.dumps(dict(scored_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),outcome_file_sha256=hashlib.sha256(args.price_csv.read_bytes()).hexdigest(),forecast_ids=out.forecast_id.unique().tolist(),prediction_files_modified=False),indent=2));print(out.to_string(index=False))
