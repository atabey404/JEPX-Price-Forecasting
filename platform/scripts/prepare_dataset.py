"""Build the website snapshot from immutable research artifacts; no synthetic market data."""
from pathlib import Path
import json,hashlib,shutil
import numpy as np,pandas as pd
import argparse
ap=argparse.ArgumentParser();ap.add_argument('--input-root',type=Path,required=True);args=ap.parse_args()
W=args.input_root;R=Path(__file__).resolve().parents[1];S=W/'JEPX_Model_Stability04';E=W/'JEPX_Model_Experiment_03'
base=pd.read_csv(S/'data/source_prediction_panel.csv.gz');pred=pd.read_csv(S/'data/predictions.csv.gz');receipt=json.loads((E/'docs/new_price_receipt.json').read_text());raw=E/receipt['path'];assert hashlib.sha256(raw.read_bytes()).hexdigest()==receipt['sha256'];prices=pd.read_csv(raw,encoding='cp932');dates=pd.to_datetime(prices.iloc[:,0]).dt.strftime('%Y-%m-%d');areas={'Tokyo':8,'Kansai':11,'Kyushu':14};lookup={}
for area,col in areas.items():
 for date,g in prices.groupby(dates,sort=True):lookup[(date,area)]=g.sort_values(g.columns[1]).iloc[:,col].astype(float).to_numpy()
def vals(x):return [round(float(y),8) for y in x]
days={}
for (date,area),g in base.groupby(['delivery_date','area']):
 g=g.sort_values('time_slot');assert len(g)==48;sub=pred[(pred.delivery_date==date)&(pred.area==area)];v={'actual':vals(g.actual),'baseline':vals(g.baseline),'original':vals(np.maximum(g.raw_candidate,.01)),'half':vals(sub[sub.method=='shrink_50'].sort_values('time_slot').prediction),'adaptive':vals(sub[sub.method=='adaptive_28d'].sort_values('time_slot').prediction),'weight':float(sub[sub.method=='adaptive_28d'].weight.iloc[0])};prior=[lookup[((pd.Timestamp(date)-pd.Timedelta(days=i)).strftime('%Y-%m-%d'),area)] for i in range(1,8)];v['median']=vals(np.median(prior,axis=0));v['origin']='prospective' if date=='2026-11-11' else 'retrospective';days.setdefault(date,{})[area]=v
registry=[json.loads(s) for s in (E/'docs/forward_registry.jsonl').read_text().splitlines()];shadow=json.loads((S/'docs/shadow_registry.json').read_text());sh=pd.read_csv(S/shadow['file'])
for entry in registry:
 f=E/entry['file'];assert hashlib.sha256(f.read_bytes()).hexdigest()==entry['sha256']
 if entry['delivery_date'] in days:
  for a in areas:days[entry['delivery_date']][a]['issued']=entry['issued_at_utc']
  continue
 for area,g in pd.read_csv(f).groupby('area'):
  g=g.sort_values('time_slot');sub=sh[sh.area==area];days.setdefault(entry['delivery_date'],{})[area]={'actual':None,'baseline':vals(g.baseline_previous_day_jpy_kwh),'median':vals(g.baseline_seven_day_median_jpy_kwh),'original':vals(g.prediction_jpy_kwh),'half':vals(sub[sub.method=='shrink_50'].sort_values('time_slot').prediction),'adaptive':vals(sub[sub.method=='adaptive_28d'].sort_values('time_slot').prediction),'weight':float(sub[sub.method=='adaptive_28d'].weight.iloc[0]),'origin':'prospective','issued':entry['issued_at_utc'],'shadowIssued':shadow['issued_at_utc']}
provenance=json.loads((S/'docs/source_provenance.json').read_text());output={'version':1,'snapshotDate':'2026-11-10','priceThrough':'2026-11-11','forecastThrough':'2026-11-12','received':receipt['retrieved_at_utc'],'areas':list(areas),'days':days,'registry':registry,'shadowRegistry':shadow,'sourceHash':receipt['sha256'],'sourceUrl':'https://www.jepx.jp/electricpower/market-data/spot/','trainingDays':84,'featureCount':12,'studyStart':'2026-07-29','studyEnd':'2026-11-11','autoUpdates':False}
(R/'public/data/market.json').write_text(json.dumps(output,separators=(',',':'),allow_nan=False));(R/'docs/data-validation.json').write_text(json.dumps({'status':'passed','deliveryDates':len(days),'areaDays':sum(len(x) for x in days.values()),'historicalRows':len(base),'pendingForecastSlots':144,'allDaysHave48Slots':all(len(v['original'])==48 for day in days.values() for v in day.values()),'sourceHashVerified':True,'syntheticMarketData':False},indent=2));print((R/'docs/data-validation.json').read_text())
# Design direction is versioned separately in docs/DESIGN_DIRECTION.md.
shutil.copyfile(S/'docs/PROSPECTIVE_ACCEPTANCE.md',R/'docs/PROSPECTIVE_ACCEPTANCE.md')
