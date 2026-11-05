import csv,io,re,json,datetime,unicodedata
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/processed';OUT.mkdir(parents=True,exist_ok=True)
frames=[];meta=[]
base=['demand_actual_mw','nuclear_actual_mw','thermal_actual_mw','hydro_actual_mw','geothermal_actual_mw','biomass_actual_mw','solar_actual_mw','solar_curtailment_mw','wind_actual_mw','wind_curtailment_mw','pumped_storage_net_mw','interconnector_net_import_mw']
for p in sorted((ROOT/'data/raw').glob('*/*.csv')):
 b=p.read_bytes()
 for enc in ['utf-8-sig','cp932']:
  try:s=b.decode(enc);break
  except UnicodeDecodeError:continue
 rows=list(csv.reader(io.StringIO(s,newline=None)));start=next(i for i,r in enumerate(rows) if r and re.match(r'^20\d\d(?:[/\-]|\d{4})',r[0]))
 modern=p.name.startswith('eria'); area=p.parent.name
 if modern:
  heads=rows[start-1];dates=[r[0]+' '+r[1] for r in rows[start:] if len(r)>2 and re.match(r'^20\d\d(?:[/\-]|\d{4})',r[0])];data=[r[2:] for r in rows[start:] if len(r)>2 and re.match(r'^20\d\d(?:[/\-]|\d{4})',r[0])];heads=heads[2:]
  mapping={'火力出力制御量':'thermal_curtailment_mw','バイオマス出力制御量':'biomass_curtailment_mw','エリア需要':'demand_actual_mw','原子力':'nuclear_actual_mw','火力(LNG)':'thermal_lng_actual_mw','火力(石炭)':'thermal_coal_actual_mw','火力(石油)':'thermal_oil_actual_mw','火力(その他)':'thermal_other_actual_mw','水力':'hydro_actual_mw','地熱':'geothermal_actual_mw','バイオマス':'biomass_actual_mw','太陽光発電実績':'solar_actual_mw','太陽光出力制御量':'solar_curtailment_mw','風力発電実績':'wind_actual_mw','風力出力制御量':'wind_curtailment_mw','揚水':'pumped_storage_net_mw','蓄電池':'battery_net_mw','連系線':'interconnector_net_import_mw','その他':'other_actual_mw','合計':'supply_total_reported_mw'}
  cols=[mapping.get(unicodedata.normalize('NFKC',h).strip(),'unmapped_'+str(i)) for i,h in enumerate(heads)];interval=30
  unit=' '.join(rows[0]);factor=10 if '万' in unit else 1
 else:
  if area=='Tokyo':
   dates=[r[0]+' '+r[1] for r in rows[start:] if len(r)>3 and re.match(r'^20\d\d/',r[0])];data=[r[2:] for r in rows[start:] if len(r)>3 and re.match(r'^20\d\d/',r[0])];cols=base+['supply_total_reported_mw'];factor=10
  else:
   dates=[r[0] for r in rows[start:] if len(r)>3 and re.match(r'^20\d\d/',r[0])];data=[r[1:] for r in rows[start:] if len(r)>3 and re.match(r'^20\d\d/',r[0])];cols=base;factor=1
  interval=60
 n=max(map(len,data));cols=cols[:n]+['extra_'+str(i) for i in range(len(cols),n)]
 df=pd.DataFrame(data,columns=cols)
 for c in df:df[c]=pd.to_numeric(df[c].str.replace(',','',regex=False).str.strip(),errors='coerce')*factor
 def parse_date(v):
  d,t=v.split();d=pd.Timestamp(d);parts=t.split(':');minutes=int(parts[0])*60+int(parts[1]);return d+pd.Timedelta(minutes=minutes-(30 if area=='Kyushu' and modern else 0))
 df['datetime_jst']=pd.DatetimeIndex([parse_date(v) for v in dates]).tz_localize('Asia/Tokyo')
 df['area']=area;df['interval_minutes']=interval;df['source_file']=str(p.relative_to(ROOT));df['source_unit']=','.join(rows[0]);df['data_kind']='actual'
 if area=='Kyushu' and modern:df['interconnector_net_import_mw']*=-1
 if modern:df['thermal_actual_mw']=df[['thermal_lng_actual_mw','thermal_coal_actual_mw','thermal_oil_actual_mw','thermal_other_actual_mw']].sum(axis=1,min_count=4)
 df['delivery_date']=df.datetime_jst.dt.strftime('%Y-%m-%d');df['time_slot']=df.datetime_jst.dt.hour*2+df.datetime_jst.dt.minute//30+1
 frames.append(df);meta.append(dict(file=str(p.relative_to(ROOT)),encoding=enc,rows=len(df),interval_minutes=interval,factor_to_mw=factor,columns=cols))
all=pd.concat(frames,ignore_index=True).sort_values(['area','datetime_jst','interval_minutes'])
all.to_csv(OUT/'supply_generation_native.csv.gz',index=False,encoding='utf-8-sig')
quality=[];issues=[]
for (area,interval),df in all.groupby(['area','interval_minutes']):
 dup=int(df.duplicated(['area','datetime_jst']).sum());counts=df.groupby('delivery_date').size();exp=1440//interval
 dates=pd.date_range(df.datetime_jst.min().normalize(),df.datetime_jst.max().normalize(),freq='D');missing=sorted(set(dates.strftime('%Y-%m-%d'))-set(counts.index))
 bad=counts[counts!=exp]
 quality.append(dict(area=area,interval_minutes=int(interval),rows=len(df),start=str(df.datetime_jst.min()),end=str(df.datetime_jst.max()),duplicate_keys=dup,missing_days=missing,incomplete_days={str(k):int(v) for k,v in bad.items()},nulls={c:int(df[c].isna().sum()) for c in df.columns if c.endswith('_mw')}))
 for d,c in bad.items():issues.append([area,int(interval),d,int(c),exp])
 df.to_csv(OUT/f'{area.lower()}_actual_{interval}min.csv.gz',index=False,encoding='utf-8-sig')
(ROOT/'docs/file_schemas.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2))
(ROOT/'docs/data_quality.json').write_text(json.dumps(quality,ensure_ascii=False,indent=2))
pd.DataFrame(issues,columns=['area','interval_minutes','date','observed','expected']).to_csv(ROOT/'docs/incomplete_days.csv',index=False)
# Keep the observation join separate from modeling features; never fill or broadcast hourly observations.
price_path=ROOT.parent/'JEPX_Project/data/processed/price_30min.csv'
if price_path.exists():
 price=pd.read_csv(price_path);price['datetime_jst']=pd.to_datetime(price.datetime_jst,utc=True).dt.tz_convert('Asia/Tokyo')
 pieces=[]
 for area,df in all[all.interval_minutes==30].groupby('area'):
  pr=price[['datetime_jst','system_price_jpy_kwh',area.lower()+'_price_jpy_kwh']].rename(columns={area.lower()+'_price_jpy_kwh':'area_price_jpy_kwh'})
  joined=df.merge(pr,on='datetime_jst',how='left',validate='one_to_one');pieces.append(joined)
 pd.concat(pieces).to_csv(OUT/'price_actuals_research_30min.csv.gz',index=False,encoding='utf-8-sig')
print(json.dumps([{k:v for k,v in q.items() if k not in ['nulls','incomplete_days','missing_days']}|{'incomplete_days':len(q['incomplete_days']),'missing_days':len(q['missing_days'])} for q in quality],ensure_ascii=False,indent=2))
