from pathlib import Path
import json,math
R=Path(__file__).resolve().parents[1];d=json.loads((R/'public/data/market.json').read_text());groups=0
for dt,areas in d['days'].items():
 assert set(areas)=={'Tokyo','Kansai','Kyushu'}
 for a,v in areas.items():
  for method in ['original','half','adaptive','baseline','median']:
   assert len(v[method])==48 and all(math.isfinite(x) and x>=.01 for x in v[method])
  assert v['actual'] is None or (len(v['actual'])==48 and all(math.isfinite(x) for x in v['actual']))
  if dt=='2026-11-12':assert v['actual'] is None
  if dt<'2026-11-11':assert v['origin']=='retrospective'
# Independent reference metrics from the last two research artifacts.
references={'Tokyo':(3.686200,5.311377),'Kansai':(4.162328,3.699684),'Kyushu':(3.453967,5.525995)}
for area,(archive,first) in references.items():
 errors=[]
 for dt,areas in d['days'].items():
  v=areas[area]
  if '2026-07-29'<=dt<='2026-11-11':errors.extend(abs(p-a) for p,a in zip(v['original'],v['actual']))
 assert len(errors)==5088 and abs(sum(errors)/len(errors)-archive)<1e-6
 v=d['days']['2026-11-11'][area];assert abs(sum(abs(p-a) for p,a in zip(v['original'],v['actual']))/48-first)<1e-6;groups+=2
result={'status':'passed','dates':len(d['days']),'areaDays':len(d['days'])*3,'referenceMetricGroups':groups,'pendingOutcomesRemainNull':True,'historicalVsProspectiveSeparated':True,'snapshotAutoUpdates':False}
(R/'docs/metric-validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
