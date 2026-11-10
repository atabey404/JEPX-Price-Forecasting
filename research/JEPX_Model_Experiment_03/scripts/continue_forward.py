"""Continue the frozen core candidate, preserving all previously issued forecasts."""
from pathlib import Path
import json,hashlib
import numpy as np,pandas as pd,joblib
from threadpoolctl import threadpool_limits
from advance_candidate import load_prices,fit_predict,csvout,AREAS,FLOOR
R=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 receipt=json.loads((R/'docs/new_price_receipt.json').read_text());src=R/receipt['path'];assert sha(src)==receipt['sha256'];prices=load_prices(src)
 spec_path=R/'docs/frozen_candidate.json';spec=json.loads(spec_path.read_text());registry=R/'docs/forward_registry.jsonl';entries=[json.loads(x) for x in registry.read_text().splitlines() if x.strip()]
 for e in entries:assert sha(R/e['file'])==e['sha256']
 latest=pd.Timestamp(prices.delivery_date.max(),tz='Asia/Tokyo');target=latest+pd.Timedelta(days=1);cutoff=target-pd.Timedelta(days=1)+pd.Timedelta(hours=10);received=pd.Timestamp(receipt['retrieved_at_utc']);now=pd.Timestamp.now(tz='UTC')
 assert not any(e['delivery_date']==str(target.date()) for e in entries),'A forecast for this date already exists'
 assert received<=now<cutoff and str(target.date()) not in set(prices.delivery_date)
 frames=[];features=[]
 with threadpool_limits(limits=2):
  for area in AREAS:
   idx,x,raw,model=fit_predict(prices,area,target,spec);assert np.isfinite(raw).all()
   frames.append(pd.DataFrame(dict(datetime_jst=idx,delivery_date=str(target.date()),area=area,time_slot=x.time_slot.to_numpy(),prediction_raw_jpy_kwh=raw,prediction_jpy_kwh=np.maximum(raw,FLOOR),baseline_previous_day_jpy_kwh=x.price_lag_1d.to_numpy(),baseline_seven_day_median_jpy_kwh=x.price_same_slot_median_7days.to_numpy(),model_id='hgb_core_84d_floor001_v1')))
   f=x.reset_index(names='datetime_jst');f['area']=area;features.append(f)
   joblib.dump(dict(estimator=model,features=spec['features'],offset='price_lag_1d',lower_guard=FLOOR,trained_through=str(latest.date()),forecast_delivery_date=str(target.date()),research_only=True),R/'models'/f'{area.lower()}_forward_{target.strftime("%Y%m%d")}.joblib')
 issued=pd.Timestamp.now(tz='UTC');assert issued<cutoff;fid=f'forward_{target.strftime("%Y%m%d")}_{issued.strftime("%Y%m%dT%H%M%SZ")}';p=R/'data/processed'/(fid+'.csv');assert not p.exists();d=pd.concat(frames,ignore_index=True);d['issued_at_utc']=issued.isoformat();d['bid_cutoff_jst']=str(cutoff);csvout(d,p)
 fp=R/'data/processed'/f'forward_features_{target.strftime("%Y%m%d")}.csv.gz';csvout(pd.concat(features,ignore_index=True),fp)
 e=dict(forecast_id=fid,file=str(p.relative_to(R)),sha256=sha(p),issued_at_utc=issued.isoformat(),delivery_date=str(target.date()),bid_cutoff_jst=str(cutoff),source_receipt_sha256=sha(src),source_received_at_utc=received.isoformat(),frozen_spec_sha256=sha(spec_path),rows=len(d),areas=AREAS,forecast_type='pre-auction_research_prediction',input_receipt_verified_before_cutoff=True,outcome_known_at_issue=False,weather_used=False,evaluated=False,price_policy='research lower guard 0.01; no upper clipping',features_file=str(fp.relative_to(R)))
 with registry.open('a') as out:out.write(json.dumps(e)+'\n')
 print(json.dumps(e,indent=2))
if __name__=='__main__':main()
