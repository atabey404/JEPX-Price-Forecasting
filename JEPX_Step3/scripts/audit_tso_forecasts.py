import urllib.request,urllib.parse,re,concurrent.futures,csv,io,zipfile,json,datetime,hashlib,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];S=ROOT/'docs/source_snapshots';RAW=ROOT/'data/raw/forecast_audit';RAW.mkdir(parents=True,exist_ok=True)
shutil.copyfile(S/'tokyo_sample',RAW/'Tokyo_202610.zip');shutil.copyfile(S/'kansai_sample.zip',RAW/'Kansai_202610.zip')
urls=list(dict.fromkeys(urllib.parse.urljoin('https://www.kyuden.co.jp/td_power_usages/jukyuHistory_202610.html',h) for h in re.findall(r'href=[\"\']([^\"\']*21110[^\"\']+\.csv[^\"\']*)',(S/'kyushu.html').read_text())))
def get(u):
 p=RAW/Path(urllib.parse.urlparse(u).path).name
 if not p.exists():p.write_bytes(urllib.request.urlopen(u,timeout=45).read())
 return dict(url=u,file=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
with concurrent.futures.ThreadPoolExecutor(6) as ex:manifest=list(ex.map(get,urls))
manifest+=[dict(url='https://www4.tepco.co.jp/forecast/html/images/AREA_202610.zip',file=str((RAW/'Tokyo_202610.zip').relative_to(ROOT))),dict(url='https://www.kansai-td.co.jp/interchange/denkiyoho/imbalance/202610_yosoku.zip',file=str((RAW/'Kansai_202610.zip').relative_to(ROOT)))]
rows=[];records=[]
def process(area,name,b):
 for enc in ['utf-8-sig','cp932']:
  try:s=b.decode(enc);break
  except:pass
 rs=list(csv.reader(io.StringIO(s,newline=None)));r=rs[1];parse=lambda x:datetime.datetime.strptime(x.replace('/','').replace('-',''),'%Y%m%d')
 d=parse(r[2]);updated=parse(r[0])+datetime.timedelta(hours=int(r[1].split(':')[0]),minutes=int(r[1].split(':')[1]),seconds=int(r[1].split(':')[2]));cutoff=d-datetime.timedelta(days=1)+datetime.timedelta(hours=10)
 data=[r for r in rs[3:] if len(r)>=7 and re.match(r'^20',r[0])]
 rows.append(dict(area=area,file=name,delivery_date=str(d.date()),file_updated_at_jst=updated.isoformat()+'+09:00',bid_cutoff_jst=cutoff.isoformat()+'+09:00',rows=len(data),file_timestamp_before_cutoff=updated<=cutoff,strict_backtest_eligible=False,reason='archive version updated after bid cutoff; earlier public version not retained here'))
 for r in data:
  records.append(dict(area=area,delivery_date=str(d.date()),time_slot=int(r[1]),demand_forecast_mw=float(r[4].replace(',',''))/500,generation_forecast_mw=float(r[5].replace(',',''))/500,wind_solar_forecast_mw=float(r[6].replace(',',''))/500,file_updated_at_jst=updated.isoformat()+'+09:00',strict_backtest_eligible=False,source_file=name))
for a in ['Tokyo','Kansai']:
 with zipfile.ZipFile(RAW/f'{a}_202610.zip') as z:
  for n in z.namelist():
   if n.lower().endswith('.csv') and ('YOSOKU'in n or 'yosoku'in n):process(a,n,z.read(n))
for p in RAW.glob('21110*.csv'):process('Kyushu',p.name,p.read_bytes())
for filename,data in [('forecast_publication_audit.csv',rows),('tso_forecasts_research_only_202610.csv',records)]:
 p=(ROOT/'docs'/filename) if 'audit'in filename else ROOT/'data/processed'/filename;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
(ROOT/'docs/tso_audit_manifest.json').write_text(json.dumps(manifest,indent=2))
print('AUDIT',len(rows),'files',len(records),'rows','eligible',sum(x['strict_backtest_eligible'] for x in rows))
