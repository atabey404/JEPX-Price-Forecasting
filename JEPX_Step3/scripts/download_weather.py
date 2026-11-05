import threading
import urllib.request,urllib.parse,urllib.error,json,datetime,concurrent.futures,hashlib,gzip,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
POINTS=[('Tokyo','tokyo',35.68,139.76),('Tokyo','maebashi',36.39,139.06),('Tokyo','choshi',35.73,140.83),('Kansai','osaka',34.69,135.50),('Kansai','kyoto',35.01,135.77),('Kansai','wakayama',34.23,135.17),('Kyushu','fukuoka',33.59,130.40),('Kyushu','kumamoto',32.80,130.71),('Kyushu','kagoshima',31.60,130.56)]
VARS=['temperature_2m','relative_humidity_2m','wind_speed_10m','wind_speed_100m','shortwave_radiation','cloud_cover','precipitation']
COMMON={'latitude':','.join(str(x[2]) for x in POINTS),'longitude':','.join(str(x[3]) for x in POINTS),'hourly':','.join(VARS),'timezone':'Asia/Tokyo','wind_speed_unit':'ms'}
(ROOT/'docs/weather_points.json').write_text(json.dumps([dict(area=a,point_id=p,latitude=lat,longitude=lon) for a,p,lat,lon in POINTS],indent=2))
jobs=[]
for year in range(2016,2027):
 start=f'{year}-04-01' if year==2016 else f'{year}-01-01';end='2026-10-31' if year==2026 else f'{year}-12-31'
 jobs.append(('reanalysis',f'era5_{year}', 'https://archive-api.open-meteo.com/v1/archive',COMMON|{'models':'era5','start_date':start,'end_date':end}))
# Same fixed cycle for all delivery hours; initialization 13h before the D-1 10:00 JST bid deadline.
d=datetime.date(2026,4,4)
while d<=datetime.date(2026,11,6):
 run=d-datetime.timedelta(days=2)
 jobs.append(('forecast',d.isoformat(),'https://single-runs-api.open-meteo.com/v1/forecast',COMMON|{'models':'gfs_global','run':str(run)+'T12:00','forecast_hours':'78'}));d+=datetime.timedelta(days=1)
def fetch(job):
 kind,name,base,params=job;p=ROOT/'data/raw/weather'/kind/(name+'.json.gz');p.parent.mkdir(parents=True,exist_ok=True)
 url=base+'?'+urllib.parse.urlencode(params)
 try:
  if p.exists():b=gzip.decompress(p.read_bytes())
  else:
   for attempt in range(3):
    try:b=urllib.request.urlopen(url,timeout=100).read();break
    except urllib.error.HTTPError as e:
     if e.code in [403,429]:
      detail=e.read().decode(errors='replace');raise RuntimeError(str(e)+' '+detail)
     if attempt==2:raise
    except Exception:
     if attempt==2:raise
   if kind=='reanalysis':time.sleep(30)
   j=json.loads(b)
   if not isinstance(j,list) or len(j)!=len(POINTS):raise ValueError('Missing locations')
   with gzip.open(p,'wb') as f:f.write(b)
  return dict(kind=kind,name=name,url=url,path=str(p.relative_to(ROOT)),retrieved_at_utc=datetime.datetime.fromtimestamp(p.stat().st_mtime,datetime.timezone.utc).isoformat(),uncompressed_sha256=hashlib.sha256(b).hexdigest(),size_bytes=p.stat().st_size)
 except Exception as e:return dict(kind=kind,name=name,url=url,error=str(e))
results=[]
jobs.sort(key=lambda j:j[0]!='forecast')
for phase,workers in [('forecast',3),('reanalysis',1)]:
 with concurrent.futures.ThreadPoolExecutor(workers) as ex:
  for r in ex.map(fetch,[j for j in jobs if j[0]==phase]):
   results.append(r)
   if len(results)%10==0:
    (ROOT/'docs/weather_download_manifest.json').write_text(json.dumps(results,indent=2));print(len(results),'/',len(jobs),'errors',sum('error'in x for x in results),flush=True)
(ROOT/'docs/weather_download_manifest.json').write_text(json.dumps(results,indent=2));print('DONE',len(results),'errors',sum('error'in x for x in results),flush=True)
