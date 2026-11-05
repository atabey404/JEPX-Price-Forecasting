"""Merge official files and audit keys, daily slots, missingness and ranges."""
import collections,csv,datetime,gzip,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
AREAS=['hokkaido','tohoku','tokyo','chubu','hokuriku','kansai','chugoku','shikoku','kyushu']
FIELDS=['sell_bid_volume_kwh','buy_bid_volume_kwh','total_volume_kwh','system_price_jpy_kwh']+[a+'_price_jpy_kwh' for a in AREAS]+['sell_block_bid_volume_kwh','sell_block_contract_volume_kwh','buy_block_bid_volume_kwh','buy_block_contract_volume_kwh']
HEADER=['datetime_jst','delivery_date','time_slot']+FIELDS

def main():
    allrows=[]; summary=[]; missing=collections.Counter(); ranges={}; seen=set(); duplicates=[]
    for p in sorted((ROOT/'data/raw/jepx').glob('*.csv')):
        with p.open(encoding='cp932',newline='') as f:
            reader=csv.reader(f); original=next(reader)
            if len(original)!=19: raise ValueError((p.name,original))
            current=[]
            for n,row in enumerate(reader,2):
                if not row:continue
                if len(row)!=19:raise ValueError((p.name,n,len(row)))
                date=datetime.datetime.strptime(row[0],'%Y/%m/%d').date();slot=int(row[1])
                if not 1<=slot<=48:raise ValueError((p.name,n,slot))
                key=(date.isoformat(),slot)
                if key in seen:duplicates.append(key)
                seen.add(key)
                dt=datetime.datetime.combine(date,datetime.time(),tzinfo=datetime.timezone(datetime.timedelta(hours=9)))+datetime.timedelta(minutes=30*(slot-1))
                record=[dt.isoformat(),date.isoformat(),slot]+row[2:]
                for field,value in zip(FIELDS,row[2:]):
                    if value.strip()=='':missing[field]+=1;continue
                    v=float(value)
                    if field not in ranges:ranges[field]=[v,v]
                    ranges[field]=[min(ranges[field][0],v),max(ranges[field][1],v)]
                allrows.append(record);current.append(date)
            summary.append({'file':p.name,'rows':len(current),'start':str(min(current)),'end':str(max(current))})
    allrows.sort(key=lambda r:(r[1],r[2]))
    counts=collections.Counter(r[1] for r in allrows)
    start=datetime.date.fromisoformat(allrows[0][1]);end=datetime.date.fromisoformat(allrows[-1][1])
    absent=[];d=start
    while d<=end:
        if d.isoformat() not in counts:absent.append(d.isoformat())
        d+=datetime.timedelta(days=1)
    bad={k:v for k,v in counts.items() if v!=48}
    with (ROOT/'data/processed/price_30min.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f);writer.writerow(HEADER);writer.writerows(allrows)
    with gzip.open(ROOT/'data/processed/price_30min_long.csv.gz','wt',encoding='utf-8',newline='') as f:
        writer=csv.writer(f);writer.writerow(['datetime_jst','delivery_date','time_slot','area','area_price_jpy_kwh','system_price_jpy_kwh'])
        for r in allrows:
            for i,area in enumerate(AREAS):writer.writerow(r[:3]+[area,r[7+i],r[6]])
    result={'rows_wide':len(allrows),'rows_long':len(allrows)*9,'delivery_start':str(start),'delivery_end':str(end),'days':len(counts),'duplicate_key_count':len(duplicates),'duplicate_key_examples':duplicates[:20],'missing_dates':absent,'days_not_48_slots':bad,'missing_values':{x:missing[x] for x in FIELDS},'numeric_ranges':ranges,'source_files':summary}
    (ROOT/'docs/data_quality.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    with (ROOT/'docs/data_dictionary.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f);writer.writerow(['field','source_column','unit','note'])
        writer.writerows([['datetime_jst','derived','ISO8601 UTC+09:00','interval start'],['delivery_date','受渡日','date','Japan delivery date'],['time_slot','時刻コード','1..48','1=00:00–00:30; 48=23:30–24:00']])
        for a,b in zip(FIELDS,original[2:]):writer.writerow([a,b,'JPY/kWh' if 'price' in a else 'kWh','National market volume; never sum repeated volumes across areas' if 'volume' in a else ''])
    print(json.dumps({k:v for k,v in result.items() if k not in ['source_files','numeric_ranges']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
