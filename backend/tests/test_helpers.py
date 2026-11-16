from src.services.analysis import pivot,aggregate
def row(code,channel,seats,gross,checked,day='2026-11-15',venue='云幕大剧场',play='渡口来信'):
 return {'code':code,'day':day,'venue':venue,'play':play,'channel':channel,'gross_cents':gross,
         'refund_cents':0,'fee_cents':0,'seats':seats,'checked':checked}
def test_aggregate_dedupes_seats_and_counts_performances():
 a=aggregate([row('P-1','剧院直营',100,600,60),row('P-1','票务合作',100,400,20),row('P-2','剧院直营',300,900,150)])
 assert a['count']==2 and a['seats']==400 and a['checked']==230
 assert a['net_cents']==1900 and a['occupancy']==230/400
def test_month_bucket_uses_business_date_and_dedupes():
 r=pivot([row('P-1','剧院直营',100,600,60,day='2026-09-30'),row('P-2','票务合作',50,100,10,day='2026-10-01')],'month','channel')
 assert r['row_keys']==['2026-09','2026-10'];assert r['total']['count']==2 and r['total']['seats']==150
def test_zero_seats_occupancy_undefined():
 a=aggregate([row('P-1','剧院直营',0,100,0)])
 assert a['seats']==0 and a['occupancy'] is None
def test_dedupe_keeps_rows_smaller_than_total():
 # 三个渠道同场：每个单元 seats=100，但总计只计 100
 rows=[row('P-1',c,100,100,10) for c in ('剧院直营','票务合作','团体专场')]
 r=pivot(rows,'venue','channel')
 assert sum(c['seats'] for c in r['cells'])==300
 assert r['total']['seats']==100 and r['total']['count']==1
 assert r['total']['checked']==30 and r['conservation']['performance_dedupe']
def test_play_and_venue_dimensions_preserve_money():
 rows=[row('P-1','剧院直营',100,600,60,venue='云幕大剧场',play='渡口来信'),
       row('P-2','票务合作',100,400,20,venue='河畔小剧场',play='渡口来信')]
 r=pivot(rows,'play','venue')
 assert r['total']['net_cents']==1000 and r['row_keys']==['渡口来信']
 assert len(r['col_keys'])==2 and r['conservation']['money_additive']
