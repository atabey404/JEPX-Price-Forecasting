"""Fetch a new official fiscal-year snapshot; never overwrite retained raw bytes."""
from pathlib import Path
import urllib.request,urllib.parse,json,datetime,hashlib,csv,io
R=Path(__file__).resolve().parents[1]
assert not (R/'docs/new_price_receipt.json').exists(), 'Use a new run directory; preserve the retained receipt'
now=datetime.datetime.now(datetime.timezone.utc);p=R/'data/raw'/('spot_summary_2026_'+now.strftime('%Y%m%dT%H%M%SZ')+'.csv')
u='https://www.jepx.jp/_download.php';body=urllib.parse.urlencode({'dir':'spot_summary','file':'spot_summary_2026.csv'}).encode();req=urllib.request.Request(u,data=body,headers={'User-Agent':'Mozilla/5.0','Referer':'https://www.jepx.jp/en/electricpower/market-data/spot/'})
b=urllib.request.urlopen(req,timeout=60).read();rows=list(csv.reader(io.StringIO(b.decode('cp932'))));assert len(rows[0])>=15 and len(rows)>2
p.write_bytes(b);receipt=dict(path=str(p.relative_to(R)),url=u,method='POST',form={'dir':'spot_summary','file':'spot_summary_2026.csv'},retrieved_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b),rows=len(rows)-1,header=rows[0]);(R/'docs/new_price_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in receipt.items() if k not in ['header']},indent=2));print('Last data row:',rows[-1][:3])
