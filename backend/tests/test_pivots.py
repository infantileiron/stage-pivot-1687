from conftest import perf
from src.config.database import Session
from src.models.entities import Pivot
def _pivot(client,name='透视'):
 r=client.post('/pivots',json={'name':name,'row_dim':'venue','col_dim':'channel'},headers=client.analyst)
 assert r.status_code==200,r.text
 return r.json()
def test_split_channel_pivot_money_adds_but_seats_dedupe(client):
 # 同场两个渠道：金额相加，座位与场次只计一次，核验相加
 client.post('/performances',json=perf('P-1',seats=100,channels=[
  {'channel':'剧院直营','gross_cents':6000,'refund_cents':0,'fee_cents':0,'checked':60},
  {'channel':'票务合作','gross_cents':4000,'refund_cents':0,'fee_cents':0,'checked':20},
 ]),headers=client.analyst)
 client.post('/performances',json=perf('P-2',seats=300,day='2026-11-16',channels=[
  {'channel':'剧院直营','gross_cents':9000,'refund_cents':0,'fee_cents':0,'checked':150},
 ]),headers=client.analyst)
 p=_pivot(client);d=client.get('/pivots/%d'%p['id'],headers=client.analyst).json()
 assert d['state']=='done',d
 t=d['result']['total']
 assert t['net_cents']==6000+4000+9000
 assert t['count']==2 and t['seats']==400
 assert t['checked']==230 and abs(t['occupancy']-230/400)<1e-12
 assert d['result']['conserved'] is True
 assert d['result']['conservation']=={'money_additive':True,'performance_dedupe':True,'checked_within_seats':True}
 cell=next(c for c in d['result']['cells'] if c['row_key']=='云幕大剧场' and c['col_key']=='剧院直营')
 assert cell['count']==2 and cell['seats']==400 and cell['checked']==210
 # 各渠道列的座位按该列覆盖的场次去重：直营覆盖两场=400，合作仅覆盖 P-1=100
 cols={c['key']:c for c in d['result']['col_totals']}
 assert cols['剧院直营']['seats']==400 and cols['票务合作']['seats']==100
 # 单元格座位直接相加会重复计 P-1 的 100 座，正好证明不能按单元座位相加
 assert sum(c['seats'] for c in d['result']['cells'])==500>t['seats']
 assert d['result']['row_totals'][0]['seats']==400 and d['result']['row_totals'][0]['count']==2
 assert sum(c['net_cents'] for c in d['result']['cells'])==t['net_cents']
def test_drill_shows_each_channel_row(client):
 client.post('/performances',json=perf('P-1',seats=100,channels=[
  {'channel':'剧院直营','gross_cents':6000,'refund_cents':0,'fee_cents':0,'checked':60},
  {'channel':'票务合作','gross_cents':4000,'refund_cents':0,'fee_cents':0,'checked':20},
 ]),headers=client.analyst)
 p=_pivot(client)
 d=client.get('/pivots/%d/drill'%p['id'],params={'row_key':'云幕大剧场','col_key':'剧院直营'},headers=client.analyst)
 body=d.json()
 assert {r['channel'] for r in body['rows']}=={'剧院直营'}
 assert body['cell']['checked']==60
def test_pivot_snapshot_versioned_and_immutable_after_split(client):
 p=client.post('/performances',json=perf('P-1',seats=100),headers=client.analyst).json()
 old=_pivot(client,'拆分前')
 assert client.get('/pivots/%d'%old['id'],headers=client.analyst).json()['result']['total']['count']==1
 draft=client.post('/performances/%d/splits'%p['id'],headers=client.analyst,json={'base_version':1,'channels':[
  {'channel':'剧院直营','gross_cents':4000,'refund_cents':0,'fee_cents':0,'checked':40},
  {'channel':'票务合作','gross_cents':1000,'refund_cents':0,'fee_cents':0,'checked':10},
 ]}).json()
 client.post('/splits/%d/confirm'%draft['id'],headers=client.analyst)
 new=_pivot(client,'拆分后')
 after=client.get('/pivots/%d'%new['id'],headers=client.analyst).json()['result']
 assert after['total']['count']==1 and after['total']['seats']==100
 assert after['total']['checked']==50 and after['total']['net_cents']==5000
 before=client.get('/pivots/%d'%old['id'],headers=client.analyst).json()['result']
 assert before['total']['net_cents']==5000 and len(before['snapshot'])==1
 assert before['checksum']!=after['checksum']
def test_pivot_forbidden_for_viewer_submit(client):
 assert client.post('/pivots',json={'name':'x xx','row_dim':'venue','col_dim':'channel'},headers=client.viewer).status_code==403
def test_pivot_fails_if_channel_snapshot_has_duplicate_channel_rows(client):
 from src.services.analysis import pivot
 rows=[{'code':'P-1','day':'2026-11-15','venue':'云幕大剧场','play':'x','channel':'剧院直营','gross_cents':1,'refund_cents':0,'fee_cents':0,'seats':10,'checked':1},
       {'code':'P-1','day':'2026-11-15','venue':'云幕大剧场','play':'x','channel':'剧院直营','gross_cents':1,'refund_cents':0,'fee_cents':0,'seats':10,'checked':1}]
 try:
  pivot(rows,'venue','channel');assert False
 except ValueError as e:assert '渠道重复' in str(e)
def test_pivot_fails_if_checked_exceeds_seats_in_snapshot(client):
 from src.services.analysis import pivot
 rows=[{'code':'P-1','day':'2026-11-15','venue':'云幕大剧场','play':'x','channel':'剧院直营','gross_cents':1,'refund_cents':0,'fee_cents':0,'seats':10,'checked':8},
       {'code':'P-1','day':'2026-11-15','venue':'云幕大剧场','play':'x','channel':'票务合作','gross_cents':1,'refund_cents':0,'fee_cents':0,'seats':10,'checked':8}]
 try:
  pivot(rows,'venue','channel');assert False
 except ValueError as e:assert '超过座位' in str(e)
