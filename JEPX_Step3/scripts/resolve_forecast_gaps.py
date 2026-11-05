import json,gzip,datetime,urllib.request,urllib.parse,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];pts=json.loads((ROOT/'docs/weather_points.json').read_text());variables=['temperature_2m','relative_humidity_2m','wind_speed_10m','wind_speed_100m','shortwave_radiation','cloud_cover','precipitation'];selections=[]
old_path=ROOT/'docs/forecast_gap_selections.json'
old={x['delivery_date']:x for x in json.loads(old_path.read_text()) if x.get('resolved')} if old_path.exists() else {}
def has_gap(docs,day):
 for j in docs:
  h=j['hourly'];ix=[i for i,t in enumerate(h['time']) if day<=t[:10] and t<=str(datetime.date.fromisoformat(day)+datetime.timedelta(days=1))+'T00:00']
  if len(ix)!=25:return True
  if any(h[v][i] is None for v in variables for i in ix):return True
 return False
day_list=[datetime.date(2026,4,4)+datetime.timedelta(days=i) for i in range((datetime.date(2026,11,6)-datetime.date(2026,4,4)).days+1)]
for day_value in day_list:
 p=ROOT/'data/raw/weather/forecast'/(str(day_value)+'.json.gz')
 day=p.name[:10];docs=json.loads(gzip.decompress(p.read_bytes())) if p.exists() else None
 if docs is not None and not has_gap(docs,day):continue
 if day in old and (ROOT/old[day]['selected_file']).exists():
  selections.append(old[day]);continue
 selection={'delivery_date':day,'original_file':str(p.relative_to(ROOT)),'original_file_exists':p.exists(),'reason':'missing weather value(s) in target day or auxiliary midnight; choose earlier run without looking at realized outcomes','resolved':False}
 for back in [1,2]:
  run=datetime.date.fromisoformat(day)-datetime.timedelta(days=2+back);params={'latitude':','.join(str(x['latitude']) for x in pts),'longitude':','.join(str(x['longitude']) for x in pts),'models':'gfs_global','hourly':','.join(variables),'run':str(run)+'T12:00','forecast_hours':'126','timezone':'Asia/Tokyo','wind_speed_unit':'ms'};u='https://single-runs-api.open-meteo.com/v1/forecast?'+urllib.parse.urlencode(params);out=ROOT/'data/raw/weather/fallback'/f'{day}_earlier_{back}.json.gz';out.parent.mkdir(parents=True,exist_ok=True)
  try:
   if out.exists():b=gzip.decompress(out.read_bytes())
   else:
    b=urllib.request.urlopen(u,timeout=90).read()
    with gzip.open(out,'wb') as f:f.write(b)
   if not has_gap(json.loads(b),day):
    selection.update(resolved=True,selected_file=str(out.relative_to(ROOT)),extra_lag_days=back,run_initialization_utc=str(run)+'T12:00:00+00:00',url=u,uncompressed_sha256=hashlib.sha256(b).hexdigest(),retrieved_at_utc=datetime.datetime.fromtimestamp(out.stat().st_mtime,datetime.timezone.utc).isoformat());break
  except Exception as e:selection['last_error']=str(e)
 selections.append(selection);print(selection,flush=True)
(ROOT/'docs/forecast_gap_selections.json').write_text(json.dumps(selections,indent=2));print('GAPS',len(selections),'resolved',sum(x['resolved'] for x in selections))
