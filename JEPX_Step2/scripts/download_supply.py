import urllib.request,urllib.parse,re,json,concurrent.futures,hashlib,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
W=ROOT/'docs/source_snapshots'
jobs=[]
for i,area,base in [(0,'Tokyo','https://www.tepco.co.jp/forecast/html/area_jukyu-j.html'),(1,'Tokyo','https://www.tepco.co.jp/forecast/html/area_jukyu_p-j.html'),(3,'Kansai','https://www.kansai-td.co.jp/denkiyoho/area-performance/past.html'),(4,'Kyushu','https://www.kyuden.co.jp/td_area_jukyu/jukyu.html')]:
 for h in re.findall(r'href=[\"\']([^\"\']+\.csv)',(W/f'page{i}.html').read_text(),re.I):jobs.append((area,urllib.parse.urljoin(base,h)))
k=json.loads((W/'kansai_list.json').read_text())
for group in k['latest']+k['past']:
 for item in group['list']:jobs.append(('Kansai','https://www.kansai-td.co.jp/interchange/denkiyoho/area-performance/'+item['name']))
for name in re.findall(r'eria_jukyu_\d+_09.csv',(W/'kyushu_list.csv').read_text()):jobs.append(('Kyushu','https://www.kyuden.co.jp/td_area_jukyu/csv/'+name))
jobs=list(dict.fromkeys(jobs))
def get(job):
 area,u=job;p=ROOT/'data/raw'/area/Path(urllib.parse.urlparse(u).path).name;p.parent.mkdir(parents=True,exist_ok=True)
 try:
  if not p.exists():
   for attempt in range(3):
    try:b=urllib.request.urlopen(u,timeout=50).read();break
    except Exception:
     if attempt==2:raise
   if b[:200].lower().find(b'<html')>=0:raise ValueError('HTML instead of CSV')
   p.write_bytes(b)
  b=p.read_bytes();return dict(area=area,url=u,path=str(p.relative_to(ROOT)),size=len(b),sha256=hashlib.sha256(b).hexdigest(),downloaded_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
 except Exception as e:return dict(area=area,url=u,error=str(e))
results=[]
with concurrent.futures.ThreadPoolExecutor(8) as ex:
 for n,r in enumerate(ex.map(get,jobs),1):
  results.append(r)
  if n%20==0:print(n,'/',len(jobs),flush=True)
(ROOT/'docs/download_manifest.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
print('DONE',len(results),'errors',sum('error'in x for x in results),flush=True)
