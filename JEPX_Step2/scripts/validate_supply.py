from pathlib import Path
import pandas as pd,json
ROOT=Path(__file__).resolve().parents[1]
df=pd.read_csv(ROOT/'data/processed/supply_generation_native.csv.gz')
assert len(list((ROOT/'data/raw').glob('*/*.csv')))==148
assert not df.duplicated(['area','datetime_jst','interval_minutes']).any()
assert not any(c.startswith(('extra_','unmapped_')) for c in df)
assert df[['demand_actual_mw','solar_actual_mw','wind_actual_mw']].notna().all().all()
assert df.interval_minutes.isin([30,60]).all()
results={'total_rows':len(df),'half_hour_rows':int((df.interval_minutes==30).sum()),'hour_rows':int((df.interval_minutes==60).sum()),'raw_files':148,'negative_solar_rows':df[df.solar_actual_mw<0][['area','datetime_jst','solar_actual_mw','source_file']].to_dict('records'),'balance_residual_mw':{}}
for a,g in df[df.interval_minutes==30].groupby('area'):
 cols=['nuclear_actual_mw','thermal_actual_mw','hydro_actual_mw','geothermal_actual_mw','biomass_actual_mw','solar_actual_mw','wind_actual_mw','pumped_storage_net_mw','battery_net_mw','interconnector_net_import_mw','other_actual_mw']
 residual=g[cols].sum(axis=1,min_count=len(cols))-g.demand_actual_mw
 results['balance_residual_mw'][a]={'median_abs':float(residual.abs().median()),'max_abs':float(residual.abs().max()),'p99_abs':float(residual.abs().quantile(.99))}
joined=pd.read_csv(ROOT/'data/processed/price_actuals_research_30min.csv.gz');assert len(joined)==results['half_hour_rows'];assert joined.area_price_jpy_kwh.notna().all()
results['price_join_missing']=int(joined.area_price_jpy_kwh.isna().sum())
(ROOT/'docs/validation_results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
dictionary=[]
for c in df:
 dictionary.append({'field':c,'unit':'MW' if c.endswith('_mw') else '', 'meaning':c.replace('_',' '),'availability':'post-delivery actual; historical publication vintages not reconstructed' if c.endswith('_mw') else 'metadata'})
pd.DataFrame(dictionary).to_csv(ROOT/'docs/data_dictionary.csv',index=False,encoding='utf-8-sig')
print(json.dumps(results,ensure_ascii=False,indent=2))
