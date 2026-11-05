"""Download official fiscal-year JEPX spot files; retain bytes and provenance."""
import concurrent.futures, csv, datetime, hashlib, io, json, pathlib, time
import urllib.request, urllib.parse

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = 'https://www.jepx.jp'
PAGE = BASE + '/en/electricpower/market-data/spot/'
HEADERS = {'User-Agent': 'Mozilla/5.0', 'Referer': PAGE}

def fetch(year):
    name = f'spot_summary_{year}.csv'
    path = ROOT/'data/raw/jepx'/name
    payload = urllib.parse.urlencode({'dir':'spot_summary','file':name}).encode()
    for attempt in range(3):
        try:
            req = urllib.request.Request(BASE+'/_download.php', data=payload, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as response:
                data = response.read()
            rows = list(csv.reader(io.StringIO(data.decode('cp932'))))
            if len(rows)<2 or len(rows[0])<15:
                raise ValueError('Empty or unexpected CSV response')
            path.write_bytes(data)
            result = {'fiscal_year':year,'file':str(path.relative_to(ROOT)), 'url':BASE+'/_download.php',
                      'method':'POST','form':{'dir':'spot_summary','file':name},
                      'downloaded_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
                      'rows':len(rows)-1,'columns':rows[0]}
            print(year,len(rows)-1,len(data),flush=True)
            return result
        except Exception:
            if attempt==2: raise
            time.sleep(1)

if __name__=='__main__':
    req=urllib.request.Request(BASE+'/js/get_graph_year.php?dir=spot_summary',headers=HEADERS)
    with urllib.request.urlopen(req,timeout=60) as r: bounds=r.read().decode().strip()
    latest,earliest=map(int,bounds.split(','))
    (ROOT/'docs/official_year_bounds.txt').write_text(bounds)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(fetch, range(earliest,latest+1)))
    (ROOT/'docs/download_manifest.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
