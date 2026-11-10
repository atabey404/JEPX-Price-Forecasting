"""Derive the research-candidate summary without refitting or selecting deployment models."""
from pathlib import Path
import importlib.util,json
import pandas as pd
R=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('experiment',R/'scripts/run_experiment.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
m=pd.read_csv(R/'data/metrics_overall.csv');daily=pd.read_csv(R/'data/metrics_daily.csv');monthly=pd.read_csv(R/'data/metrics_monthly.csv');rows=[]
for area in ['Tokyo','Kansai','Kyushu']:
 a=m[m.area==area].set_index('method');dd=daily[daily.area==area].pivot(index='delivery_date',columns='method',values='MAE');delta=dd.hgb_core-dd.previous_day;ci=mod.block_ci(delta);mm=monthly[(monthly.area==area)&monthly.month.isin(['2026-07','2026-08','2026-09','2026-10'])].pivot(index='month',columns='method',values='MAE')
 rows.append(dict(area=area,previous_day_MAE=a.loc['previous_day','MAE'],hgb_core_MAE=a.loc['hgb_core','MAE'],gain_pct=(1-a.loc['hgb_core','MAE']/a.loc['previous_day','MAE'])*100,mean_daily_delta=delta.mean(),CI_low=ci[0],CI_high=ci[1],full_months_beating_baseline=int((mm.hgb_core<mm.previous_day).sum()),negative_predictions=int(a.loc['hgb_core','negative_predictions'])))
pd.DataFrame(rows).to_csv(R/'data/core_vs_baseline.csv',index=False)
status=dict(status='research_candidate_not_deployed',candidate='hgb_core',reason='simpler candidate retained for further confirmation; weather increment not established',selected_after_this_retrospective_comparison=True,production_ready=False,forward_validation_days=0,verified_first_input_availability=False,official_price_bound_constraints_configured=False,platform_implementation_started=False)
(R/'docs/CANDIDATE_STATUS.json').write_text(json.dumps(status,indent=2));print(pd.DataFrame(rows).to_string(index=False))
